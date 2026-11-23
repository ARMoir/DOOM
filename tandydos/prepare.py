"""Assemble a DOS game directory from verified Doom8088 shareware archives."""

import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import shutil
import struct
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile
from clean_textures import make_clean_patches

PORT = Path(__file__).resolve().parent
TAG = "v20260304"
BASE_URL = "https://github.com/FrenkelS/Doom8088/releases/download/" + TAG
# Archive, input WAD, executable and SHA-256 from the upstream release.
MODES = {
    "tandy": ("EGA", "DOOM16D.WAD", "DOOMTGA.EXE",
              "0790dde3f2e89558ee200ea5431d99653b52bee3c10b6416332b78735a9d5ddf"),
    "cga": ("CGA", "DOOM4.WAD", "DOOMCGA.EXE",
            "4d3517addae04c2b18f9665397bcf401e9078dfb64caab2540fe34d3d59f70b0"),
    "vga": ("VGA", "DOOM1.WAD", "DOOMVGA.EXE",
            "4b849d24b3eeda4d0cf89d43066fea4eebaf2b557ff91fef55d3a40afa6c24f2"),
}
RAW_SIZES = {b"TITLEPIC": 240 * 160, b"HELP2": 240 * 160,
             b"WIMAP0": 240 * 160, b"STBAR": 240 * 32, b"FLOOR4_8": 64 * 64}
HEADER = struct.Struct("<4sII")
ENTRY = struct.Struct("<II8s")


# IBM/Tandy 16-color RGBI palette, in the hardware's 0..15 order.
# Prepare on the modern host: no color mixing or palette lookup at 7 MHz.
TANDY_RGBI = (
    (0x00, 0x00, 0x00), (0x00, 0x00, 0xaa),
    (0x00, 0xaa, 0x00), (0x00, 0xaa, 0xaa),
    (0xaa, 0x00, 0x00), (0xaa, 0x00, 0xaa),
    (0xaa, 0x55, 0x00), (0xaa, 0xaa, 0xaa),
    (0x55, 0x55, 0x55), (0x55, 0x55, 0xff),
    (0x55, 0xff, 0x55), (0x55, 0xff, 0xff),
    (0xff, 0x55, 0x55), (0xff, 0x55, 0xff),
    (0xff, 0xff, 0x55), (0xff, 0xff, 0xff),
)

def wad_lumps(wad):
    """Preserve WAD directory indices; verify all lump spans."""
    if len(wad) < HEADER.size:
        raise ValueError("Truncated IWAD header")
    magic, count, directory = HEADER.unpack_from(wad)
    if magic != b"IWAD" or directory > len(wad) or count > (len(wad) - directory) // ENTRY.size:
        raise ValueError("Expected a complete Doom8088 IWAD")
    result = {}
    order = []
    for index in range(count):
        offset, size, name = ENTRY.unpack_from(wad, directory + index * ENTRY.size)
        if offset > len(wad) or size > len(wad) - offset:
            raise ValueError("Truncated WAD lump " + repr(name))
        key = name.rstrip(b"\0")
        order.append((name, offset, size))
        if key not in result:
            result[key] = wad[offset:offset + size]
    return order, result


def nearest_rgbi(red, green, blue):
    """Perceptually weighted integer nearest-color quantization."""
    best, best_error = 0, 1 << 30
    for index, (r, g, b) in enumerate(TANDY_RGBI):
        dr, dg, db = red-r, green-g, blue-b
        error = dr*dr*3 + dg*dg*4 + db*db*2
        if error < best_error:
            best_error, best = error, index
    return best


def quantize_raw_vga(raw, palette, width):
    """VGA indexed RGB 2:1 downsample to contiguous packed RGBI nibbles.

    The VGA image stores ONE palette index per pixel. EGA assets in
    Doom8088 are pre-dithered PAIRS of colors per byte; taking
    alternating nibbles there causes colored speckling/moire on Tandy.
    """
    if width % 4 or len(raw) % width:
        raise ValueError("VGA graphic width must be divisible by four")
    if len(palette) < 256 * 3:
        raise ValueError("VGA PLAYPAL is incomplete")
    rgb = tuple(tuple(palette[p:p+3]) for p in range(0, 256 * 3, 3))
    out = bytearray(len(raw) // 4)
    dest = 0
    for row_start in range(0, len(raw), width):
        row = raw[row_start:row_start + width]
        for x in range(0, width, 4):
            a, b, c, d = (rgb[row[x+i]] for i in range(4))
            left = nearest_rgbi((a[0]+b[0]+1)//2,
                                (a[1]+b[1]+1)//2,
                                (a[2]+b[2]+1)//2)
            right = nearest_rgbi((c[0]+d[0]+1)//2,
                                 (c[1]+d[1]+1)//2,
                                 (c[2]+d[2]+1)//2)
            out[dest] = (left << 4) | right
            dest += 1
    return bytes(out)



# The EGA Doom8088 WAD's lit wall/sprite colors are two four-bit dither
# samples per byte. On EGA those are displayed as separate subpixels.
# The Tandy 160x200 framebuffer cannot resolve that pattern well; at
# 120 logical pixels wide it becomes a pronounced pink/green checker.
# Blend each pair to ONE RGBI hue and repeat the nibble. This also
# keeps palette lookup out of the 7 MHz game's inner rendering loops.
def solid_rgbi_byte(value):
    high = value >> 4
    low = value & 15
    if high == low:
        return value
    a = TANDY_RGBI[high]
    b = TANDY_RGBI[low]
    blended = nearest_rgbi((a[0] + b[0] + 1) // 2,
                           (a[1] + b[1] + 1) // 2,
                           (a[2] + b[2] + 1) // 2)
    return (blended << 4) | blended


SOLID_RGBI = bytes(solid_rgbi_byte(value) for value in range(256))


def solidify_colormap(data):
    """Convert each lighting-level lookup result to a solid RGBI pixel."""
    if len(data) < 32 * 256 or len(data) % 256:
        raise ValueError("Unexpected EGA COLORMAP size")
    return data.translate(SOLID_RGBI)


def solidify_patch(data):
    """Convert UI patch posts, preserving headers and offsets.

    Only transform well-formed patch data. A patch starts with four
    signed shorts and width 32-bit column offsets, followed by
    column posts: topdelta, length, pad, pixels, pad, terminator FF.
    Game map lumps and raw resources must never be reinterpreted
    as patch data. Validate ALL columns before modifying any byte.
    """
    if len(data) < 13:
        return data
    width, height, _, _ = struct.unpack_from("<hhhh", data)
    if not (0 < width <= 320 and 0 < height <= 256):
        return data
    directory_end = 8 + 4 * width
    if directory_end >= len(data):
        return data
    spans = []
    visited = set()
    for column in range(width):
        pos = struct.unpack_from("<I", data, 8 + column * 4)[0]
        if pos < directory_end or pos >= len(data):
            return data
        if pos in visited:
            continue
        visited.add(pos)
        # Posts cannot exceed the source buffer.
        for _ in range(256):
            if pos >= len(data):
                return data
            top = data[pos]
            if top == 255:
                break
            if pos + 4 > len(data):
                return data
            length = data[pos + 1]
            if length == 0 or top >= height or top + length > height:
                return data
            end = pos + length + 4
            if end > len(data):
                return data
            spans.append((pos + 3, pos + 3 + length))
            pos = end
        else:
            return data
    if not spans:
        return data
    result = bytearray(data)
    for start, end in spans:
        result[start:end] = data[start:end].translate(SOLID_RGBI)
    return bytes(result)




def world_patch_names(wad_lumps_by_name, ega_order):
    """Identify patches used by lighting-mapped walls/sprites.

    Wall texture names come from PNAMES, while sprites live between
    S_START/S_END (or SS_START/SS_END) namespace markers. Those patches
    must retain the source EGA color-pair byte: the runtime indexes the
    COLORMAP table with that exact value before rendering its RGBI nibble.
    Rewriting source pixels first applies the conversion twice and
    produces incorrect wall shading.
    """
    world = set()
    pnames = wad_lumps_by_name.get(b"PNAMES")
    if pnames is not None:
        if len(pnames) < 4:
            raise ValueError("Truncated PNAMES")
        count = struct.unpack_from("<I", pnames)[0]
        if count > (len(pnames) - 4) // 8:
            raise ValueError("Truncated PNAMES patch directory")
        for index in range(count):
            name = pnames[4 + index * 8:12 + index * 8].rstrip(b"\0")
            if name:
                world.add(name)

    sprites = False
    for name, _, size in ega_order:
        key = name.rstrip(b"\0")
        if key in (b"S_START", b"SS_START"):
            sprites = True
        elif key in (b"S_END", b"SS_END"):
            sprites = False
        elif sprites and size:
            world.add(key)
    return world


def is_colormap_lump(name):
    """The gamma variants are called COLORMP1..COLORMP4 in this port."""
    return name == b"COLORMAP" or (
        len(name) == 8 and name.startswith(b"COLORMP") and
        name[-1] in b"0123456789"
    )


def parse_patch_pixels(data):
    """Return (width, height, {(x,y): (offset,index)}) for valid DOOM posts.

    EGA and VGA source patches can have different post offsets, so match
    pixels by original X/Y coordinates, never by the packed file offset.
    """
    if data is None or len(data) < 12:
        return None
    width, height, _, _ = struct.unpack_from("<hhhh", data)
    if not (0 < width <= 320 and 0 < height <= 256):
        return None
    directory_end = 8 + 4 * width
    if directory_end >= len(data):
        return None

    pixels = {}
    for x in range(width):
        pos = struct.unpack_from("<I", data, 8 + 4 * x)[0]
        if pos < directory_end or pos >= len(data):
            return None
        terminated = False
        for _ in range(257):
            if pos >= len(data):
                return None
            top = data[pos]
            if top == 255:
                terminated = True
                break
            if pos + 4 > len(data):
                return None
            length = data[pos + 1]
            end = pos + length + 4
            if (not length or top >= height or
                    top + length > height or end > len(data)):
                return None
            for y in range(length):
                pixels[x, top + y] = (pos + 3 + y, data[pos + 3 + y])
            pos = end
        if not terminated:
            return None
    return width, height, pixels


def collect_vga_examples(ega_lumps, vga_lumps, world_names):
    """Learn what each EGA 2x4bpp source code means in the original VGA art.

    Maps at identical texture coordinates, not between colormap output
    bytes. This avoids the pre-quantization / double-conversion bug.
    """
    hist = [[0] * 256 for _ in range(256)]
    matched_patches = 0
    matched_pixels = 0
    for name in sorted(world_names):
        ega = parse_patch_pixels(ega_lumps.get(name))
        vga = parse_patch_pixels(vga_lumps.get(name))
        if ega is None or vga is None or ega[:2] != vga[:2]:
            continue
        ep = ega[2]
        vp = vga[2]
        overlap = len(ep.keys() & vp.keys())
        if not ep or overlap * 4 < len(ep) * 3:
            # Not an equivalent source picture; never map mismatched art.
            continue
        matched_patches += 1
        for xy, (_offset, original_ega_byte) in ep.items():
            source_vga = vp.get(xy)
            if source_vga is not None:
                hist[original_ega_byte][source_vga[1]] += 1
                matched_pixels += 1
    return hist, {"matched_patches": matched_patches,
                  "matched_pixels": matched_pixels,
                  "source_codes": sum(any(row) for row in hist)}


def gamma_rgb(value, gamma):
    """Small, precomputed brightness lift like a DOS gamma lookup.

    Not a rendering operation on the Tandy. Gamma 0 is exact input.
    """
    if gamma <= 0 or value in (0, 255):
        return value
    # Integer-only and monotonic; gamma levels 1..4 increase midtones.
    # Approximate each higher EGA COLORMP1..4 variant, never overexpose.
    lift = (255 - value) * value * gamma
    return min(255, value + (lift + 255 * 12) // (255 * 24))


def make_native_colormap(ega_table, vga_table, vga_palette, histogram,
                         gamma=0):
    """Translate 34x256 VGA-colormap shades into one Tandy RGBI pixel.

    FastDoom's nearest-color palette LUT idea, adapted to source colors
    represented by Doom8088's two-EGA-color codes. The 256-way
    histogram is built from identical VGA/EGA texture coordinates.
    The table remains the same 34x256, byte-indexed data used by the
    8086 wall/sprite inner loop. Unobserved source codes fall back to
    the original EGA lighting output, avoiding invented colors.
    """
    if (len(ega_table) < 34 * 256 or len(ega_table) % 256 or
            vga_table is None or len(vga_table) < 34 * 256 or
            len(vga_palette) < 768):
        return solidify_colormap(ega_table)
    palette = [tuple(vga_palette[i * 3:i * 3 + 3]) for i in range(256)]
    source = []
    for code in range(256):
        counts = histogram[code]
        source.append([(i, amount) for i, amount in enumerate(counts)
                       if amount])
    out = bytearray(ega_table.translate(SOLID_RGBI))
    for light in range(34):
        base = light * 256
        for code, examples in enumerate(source):
            if not examples:
                continue
            total = red = green = blue = 0
            for vga_index, samples in examples:
                lookup = vga_table[base + vga_index]
                r, g, b = palette[lookup]
                total += samples
                red += r * samples
                green += g * samples
                blue += b * samples
            if not total:
                continue
            rgb = [int((value + total // 2) // total)
                   for value in (red, green, blue)]
            color = nearest_rgbi(*(gamma_rgb(value, gamma) for value in rgb))
            out[base + code] = (color << 4) | color
    return bytes(out)


def rgb_native_ui_patch(ega_blob, vga_blob, vga_palette):
    """Recolor UI posts using original VGA pixels, without altering EGA layout.

    The UI paths bypass COLORMAP, so these pixel bytes must already be
    packed repeated-nibble RGBI. If layouts differ, caller retains a
    de-dithered EGA patch instead of copying incompatible binary data.
    """
    ega = parse_patch_pixels(ega_blob)
    vga = parse_patch_pixels(vga_blob)
    if ega is None or vga is None or ega[:2] != vga[:2]:
        return None
    ep = ega[2]
    vp = vga[2]
    if ep.keys() != vp.keys():
        return None
    result = bytearray(ega_blob)
    pal = [tuple(vga_palette[i * 3:i * 3 + 3]) for i in range(256)]
    for xy, (offset, _byte) in ep.items():
        _voff, index = vp[xy]
        color = nearest_rgbi(*pal[index])
        result[offset] = (color << 4) | color
    return bytes(result)



def pack_tandy(ega_wad, vga_wad, stats=None, reconstruct_world=False, clean_world=False):
    """Preserve source EGA gameplay textures, recolor only static and HUD art.

    The experimental VGA RGBI reconstruction is deliberately opt-in.
    Physical Tandy gameplay tests showed its averaged world COLORMAP
    discarded too much texture contrast, despite successful DOS tests.
    The default must leave ALL source world colormaps untouched.
    

    Original lump numbering/order is preserved. Output raw sizes match
    the current 120px internal RGBI framebuffer (60 bytes per scanline).
    """
    ega_order, ega_lumps = wad_lumps(ega_wad)
    _, vga_lumps = wad_lumps(vga_wad)
    world_patches = world_patch_names(ega_lumps, ega_order)
    cleaned, clean_report = make_clean_patches(ega_lumps, parse_patch_pixels) if clean_world else ({}, [])
    if reconstruct_world:
        histogram, diagnostics = collect_vga_examples(
            ega_lumps, vga_lumps, world_patches)
    else:
        histogram = None
        diagnostics = {"matched_patches": 0, "matched_pixels": 0,
                       "source_codes": 0}
    palette = vga_lumps.get(b"PLAYPAL")
    if palette is None or len(palette) < 256 * 3:
        raise ValueError("VGA WAD is missing its PLAYPAL RGB palette")
    result = bytearray(HEADER.size)
    entries = []
    converted = set()
    ui_vga_count = 0
    vga_colormap = vga_lumps.get(b"COLORMAP")
    for name, offset, size in ega_order:
        key = name.rstrip(b"\0")
        data = ega_wad[offset:offset+size]
        if key in RAW_SIZES:
            vga_data = vga_lumps.get(key)
            if vga_data is None or len(vga_data) != RAW_SIZES[key]:
                raise ValueError("VGA picture missing or has wrong size: " + repr(key))
            width = 64 if key == b"FLOOR4_8" else 240
            data = quantize_raw_vga(vga_data, palette, width)
            if len(data) != RAW_SIZES[key] // 4:
                raise ValueError("Incorrect packed Tandy graphic " + repr(key))
            converted.add(key)
        elif key in cleaned:
            data = cleaned[key]
        elif is_colormap_lump(key):
            # By default keep the complete original EGA lighting lookup
            # byte-for-byte. Our Tandy screenshot proves that reducing each
            # 8-bit dithered texture code to one RGBI nibble loses detail.
            # Optional experimental conversion stays out of releases.
            if reconstruct_world:
                gamma = int(key[-1:]) if key.startswith(b"COLORMP") else 0
                data = make_native_colormap(data, vga_colormap, palette,
                                            histogram, gamma=gamma)
        elif key not in world_patches and key not in (
                b"PLAYPAL", b"TEXTURE1", b"TEXTURE2", b"PNAMES"):
            # UI and text are drawn directly, without a lighting lookup.
            # Prefer original VGA source at the same patch coordinates.
            native = rgb_native_ui_patch(data, vga_lumps.get(key), palette)
            if native is not None:
                data = native
                ui_vga_count += 1
            else:
                data = solidify_patch(data)
        entries.append(ENTRY.pack(len(result), len(data), name))
        result.extend(data)
    if converted != RAW_SIZES.keys():
        raise ValueError("Missing raw pictures in the EGA Doom8088 WAD")
    HEADER.pack_into(result, 0, b"IWAD", len(entries), len(result))
    result.extend(b"".join(entries))
    diagnostics["vga_ui_patches"] = ui_vga_count
    diagnostics["texture_profile"] = "clean" if clean_world else "classic"
    diagnostics["clean_patches"] = len(clean_report)
    diagnostics["clean_changed_pixels"] = sum(row[3] for row in clean_report)
    diagnostics["clean_patch_details"] = "; ".join("%s:%s:%s:%d"%r for r in clean_report)
    diagnostics["colormap_strategy"] = (
        "experimental_vga_rgb" if reconstruct_world and
        diagnostics["source_codes"] and vga_colormap is not None
        else "original_ega_unchanged")
    diagnostics["world_mode"] = (
        "experimental" if reconstruct_world else "original")
    diagnostics["world_colormaps_unchanged"] = not reconstruct_world
    if stats is not None:
        stats.update(diagnostics)
    return bytes(result)


def prepare(output, binaries, archives, modes):
    output.mkdir(parents=True, exist_ok=True)
    # Keep existing outputs intact if an archive is unavailable or invalid.
    with tempfile.TemporaryDirectory(dir=output) as tmp:
        stage = Path(tmp)
        # The Tandy WAD uses the EGA game's compact engine data, but
        # converts the five raw screen pictures from *VGA*, not from
        # the EGA release's noisy pre-dithered dual-pixel bytes.
        # Verify the upstream archives before trusting their contents.
        cached_wads = {}

        def load_wad(mode):
            if mode in cached_wads:
                return cached_wads[mode]
            video, wad_name, _, digest = MODES[mode]
            archive_name = f"DOOM8088-{video}-{TAG}.zip"
            if archives:
                archive = (archives / archive_name).read_bytes()
            else:
                print("Downloading", archive_name, flush=True)
                with urlopen(f"{BASE_URL}/{archive_name}", timeout=90) as response:
                    archive = response.read()
            if sha256(archive).hexdigest() != digest:
                raise ValueError("Checksum mismatch for " + archive_name)
            with ZipFile(BytesIO(archive)) as source:
                member, = [n for n in source.namelist()
                           if Path(n).name.upper() == wad_name]
                wad = source.read(member)
            cached_wads[mode] = wad
            return wad

        for mode in modes:
            video, wad_name, exe_name, digest = MODES[mode]
            wad = load_wad(mode)
            if mode == "tandy":
                stats = {}
                wad_name, wad = "DOOMT16.WAD", pack_tandy(
                    wad, load_wad("vga"), stats=stats)
                print("Tandy RGBI offline pipeline:", stats, flush=True)
                clean_stats = {}
                clean_wad = pack_tandy(wad, load_wad("vga"), stats=clean_stats, clean_world=True)
                (stage / "DOOMTC.WAD").write_bytes(clean_wad)
                print("Tandy Clean experiment:", clean_stats, flush=True)
                (stage / "CLEAN.TXT").write_text("\n".join("%s: %s"%(k,v) for k,v in sorted(clean_stats.items())) + "\n", encoding="ascii")
                (stage / "RGBI.TXT").write_text(
                    "Tandy RGBI WAD conversion\n" +
                    "\n".join(str(k) + ": " + str(v)
                              for k, v in sorted(stats.items())) + "\n",
                    encoding="ascii")
            (stage / wad_name).write_bytes(wad)
            shutil.copyfile(binaries / exe_name, stage / (Path(exe_name).stem + ".OVL"))
            if mode == "tandy":
                shutil.copyfile(binaries / "DOOMTGH.EXE", stage / "DOOMTGH.OVL")
                bat = (PORT / "BENCH.BAT").read_text(encoding="ascii")
                (stage / "BENCH.BAT").write_bytes(bat.replace("\n", "\r\n").encode("ascii"))
        shutil.copyfile(binaries / "DOOM.EXE", stage / "DOOM.EXE")
        shutil.copyfile(PORT / "RUN.TXT", stage / "RUN.TXT")
        shutil.copyfile(PORT / "engine" / "LICENSE", stage / "COPYING.TXT")
        for item in stage.iterdir():
            item.replace(output / item.name)
    print("DOS files ready in", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("DOOMDOS"))
    parser.add_argument("--bin", type=Path, default=PORT / "bin")
    parser.add_argument("--archives", type=Path, help="Read release ZIP files from this directory")
    parser.add_argument("--mode", choices=MODES, action="append", help="Prepare just this display")
    args = parser.parse_args()
    prepare(args.out.resolve(), args.bin, args.archives, args.mode or MODES)
