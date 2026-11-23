"""Original low-detail Tandy art pass, generated at WAD packaging time.

No Wolfenstein graphics are included. Strong silhouettes, broad panels,
green technical walls, unmistakable exit doors, health, green/blue armor.
Preserves EGA COLORMAP and map data. Runtime cost: zero.
"""
import struct
from clean_textures import candidate_patches

RGBI = (
    (0,0,0),(0,0,170),(0,170,0),(0,170,170),
    (170,0,0),(170,0,170),(170,85,0),(170,170,170),
    (85,85,85),(85,85,255),(85,255,85),(85,255,255),
    (255,85,85),(255,85,255),(255,255,85),(255,255,255),
)

def source_codes(colormap):
    """Select pre-existing EGA source indices that light as desired RGBI.

    A texture pixel is NOT a final hardware color: the renderer indexes
    COLORMAP with its 8-bit source value. Find the best original index
    for the desired visible color, favoring low-dither outputs.
    """
    if colormap is None or len(colormap) < 256:
        raise ValueError("Missing original EGA COLORMAP")
    result = {}
    for desired, rgb in enumerate(RGBI):
        best = (10**12, 0)
        for code in range(256):
            shown = colormap[code]
            p, q = RGBI[shown >> 4], RGBI[shown & 15]
            error = sum((rgb[i]-p[i])**2 + (rgb[i]-q[i])**2
                        for i in range(3))
            # Prefer a solid-looking pair when two candidates are close.
            error += sum((p[i]-q[i])**2 for i in range(3)) // 5
            if error < best[0]:
                best = (error, code)
        result[desired] = best[1]
    return result


def draw_green_wall(x, y):
    """1960s/90s chunky industrial techbase: plates and signal stripes."""
    if y < 6 or y >= 58 or x < 3 or x >= 61:
        return 0
    if y < 10 or y >= 55:
        return 8
    if y in (10, 54) or x in (3, 60):
        return 15
    if y in (14, 46) or x in (9, 32, 54):
        return 0
    if y in (15, 45) or x in (10, 33, 53):
        return 8
    # large inset plates; bottom dark undercut.
    if y > 47:
        return 2
    if y >= 40:
        return 0 if (x//8)%2 else 14
    if 17 <= y < 35 and 14 <= x < 49:
        if y < 20 or x in (14, 48):
            return 10
        if x in (18, 45) or y == 33:
            return 0
        if 26 < x < 37 and 23 < y < 30:
            return 14 if y in (24,25) else 4
        return 2 if (x + y) % 9 else 10
    return 2 if (x // 12 + y // 18) % 3 else 10


def draw_exit_door(x, y):
    """Wolf-readable symmetry, DOOM-style exit, central seam and frame."""
    if x < 4 or x >= 60 or y < 2 or y >= 62:
        return 0
    if x < 9 or x >= 55 or y < 8 or y >= 57:
        return 7 if (x+y)%7 else 15
    if x in (9,54) or y in (8,56):
        return 14
    if y < 20:
        if 15 <= x < 49:
            # simple central green arrow (no tiny text glyphs)
            if 16 <= x < 47 and 11 <= y < 14:
                return 10
            if 28 <= x <= 35 and 14 <= y < 19:
                return 10
        return 0
    if x in (30,31,32,33):
        return 0
    if 22 <= y < 28:
        return 8
    if x in (13,49) or y >= 52:
        return 0
    if (x in (15,16,47,48) and 30 <= y < 46):
        return 14
    if y in (32, 50):
        return 10
    return 2 if x < 32 else 8


def draw_medkit(x, y):
    """High-contrast white field kit with large red cross and handle."""
    if 23 <= x <= 40 and 11 <= y < 22:
        return 0 if x in (23,40) or y == 11 else 7
    if not (7 <= x < 57 and 20 <= y < 57):
        return None
    if x in (7,56) or y in (20,56):
        return 0
    if y >= 50:
        return 8
    if x in (10,53) or y == 23:
        return 7
    if (26 <= x < 38 and 28 <= y < 47) or (18 <= x < 46 and 34 <= y < 41):
        return 12
    if (24 <= x < 40 and 27 <= y < 48) or (17 <= x < 47 and 33 <= y < 42):
        return 4
    return 15


def draw_armor(x, y, blue=False):
    """One bold chestplate silhouette, different green/blue armor grades."""
    bright = 9 if blue else 10
    body = 1 if blue else 2
    if y < 14 or y >= 57:
        return None
    # shoulders widen out; chest tapers toward the waist.
    if y < 23:
        left, right = 8, 56
    elif y < 40:
        left, right = 11, 53
    else:
        left = 11 + (y-40)//3
        right = 53 - (y-40)//3
    if not (left <= x < right):
        return None
    if x in (left, right-1) or y in (14, 56):
        return 0
    if y < 19 or x in (left+2, right-3):
        return bright
    if y in (26, 46) or x in (30,33):
        return 8 if blue else 0
    if 26 <= x < 38 and 32 <= y < 41:
        return 14 if blue else 7
    if y > 48:
        return 8
    return body


def raster_patch(original, pixel_func, source, parse_patch_pixels,
                 preserve_coverage=False):
    """Write valid DOOM column posts, keeping dimensions and sprite anchor.

    Sprite generation may change transparent silhouette. For wall patches
    preserve their original opacity/posts and only replace indexed bytes.
    """
    parsed = parse_patch_pixels(original)
    if parsed is None:
        raise ValueError("Target is not a valid patch")
    width, height, existing = parsed
    if height > 254:
        raise ValueError("Art height exceeds DOOM post format")
    if preserve_coverage:
        updated = bytearray(original)
        for (x,y),(offset,unused) in existing.items():
            color = pixel_func(x*64//max(1,width), y*64//max(1,height))
            if color is not None:
                updated[offset] = source[color]
        return bytes(updated)
    result = bytearray(original[:8] + b"\0"*(width*4))
    for x in range(width):
        struct.pack_into("<I", result, 8+x*4, len(result))
        y = 0
        while y < height:
            def pix(yy):
                return pixel_func(x*64//width, yy*64//height)
            if pix(y) is None:
                y += 1
                continue
            start = y
            colors = []
            while y < height and pix(y) is not None and len(colors) < 254:
                colors.append(source[pix(y)])
                y += 1
            result.extend(bytes([start,len(colors),0]))
            result.extend(bytes(colors))
            result.append(0)
        result.append(255)
    return bytes(result)


def build_tandy_art_wad(classic_wad, wad_lumps, parse_patch_pixels,
                        header, entry):
    """Replace precisely two world patches and pickup sprite families.

    No new texture names, sprite names, maps, colormaps, HUD, title or
    gameplay code. Output stays an IWAD with identical lump directory.
    Fail build if expected art targets are not found in source release.
    """
    order, lumps = wad_lumps(classic_wad)
    source = source_codes(lumps.get(b"COLORMAP"))
    available = candidate_patches(lumps)
    changes = {}
    details = {}

    targets = [
        ("green wall", ("STARTAN", "TEKWALL", "COMP", "GRAY"),
         draw_green_wall),
        ("exit door", ("EXITDOOR", "BIGDOOR", "DOOR"),
         draw_exit_door),
    ]
    used = set()
    for label, patterns, artist in targets:
        picked = None
        for pattern in patterns:
            for tex_name, patch_name in available:
                if (pattern in tex_name.upper() and
                        patch_name not in used and
                        parse_patch_pixels(lumps.get(patch_name)) is not None):
                    picked = (tex_name, patch_name)
                    break
            if picked:
                break
        if picked is None:
            raise ValueError("Art pack missing wall texture family: " + label)
        texture, name = picked
        changes[name] = raster_patch(lumps[name], artist, source,
                                     parse_patch_pixels,
                                     preserve_coverage=True)
        used.add(name)
        details[label] = texture + " -> " + name.decode("ascii","replace")

    sprite_names = set()
    in_sprites = False
    for rawname, _off, _size in order:
        name = rawname.rstrip(b"\0")
        if name in (b"S_START", b"SS_START"):
            in_sprites = True
            continue
        if name in (b"S_END", b"SS_END"):
            in_sprites = False
            continue
        if in_sprites:
            sprite_names.add(name)

    sprites = {
        "medkit": (b"MEDI", draw_medkit),
        "green armor": (b"ARM1", lambda x,y: draw_armor(x,y,False)),
        "blue armor": (b"ARM2", lambda x,y: draw_armor(x,y,True)),
    }
    for label,(prefix,artist) in sprites.items():
        matched = sorted(name for name in sprite_names
                         if name.startswith(prefix) and
                         parse_patch_pixels(lumps.get(name)) is not None)
        if not matched:
            raise ValueError("Art pack missing pickup sprite: " + label)
        for name in matched:
            changes[name] = raster_patch(lumps[name], artist, source,
                                         parse_patch_pixels)
        details[label] = ",".join(n.decode("ascii","replace") for n in matched)

    result = bytearray(header.size)
    directory = []
    modified = 0
    for name,off,size in order:
        key = name.rstrip(b"\0")
        new = changes.get(key)
        data = classic_wad[off:off+size] if new is None else new
        if new is not None:
            modified += 1
        directory.append(entry.pack(len(result),len(data),name))
        result.extend(data)
    header.pack_into(result,0,b"IWAD",len(directory),len(result))
    result.extend(b"".join(directory))
    if modified != len(changes):
        raise ValueError("Art changes did not correspond to actual WAD lumps")
    details["modified_lumps"] = modified
    details["color_codes"] = ",".join("%d=%02X"%(n,source[n]) for n in
                                    (0,1,2,4,7,8,9,10,12,14,15))
    details["original_colormap"] = "unchanged"
    return bytes(result), details
