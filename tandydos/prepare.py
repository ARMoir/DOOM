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


def pack_tandy(wad):
    """Convert raw RGBI pictures to mode 08h. Preserve map lump indices."""
    magic, count, directory = HEADER.unpack_from(wad)
    if magic != b"IWAD" or directory + count * ENTRY.size > len(wad):
        raise ValueError("Expected a complete Doom8088 EGA IWAD")
    result = bytearray(HEADER.size)
    entries = []
    converted = set()
    for index in range(count):
        offset, size, name = ENTRY.unpack_from(wad, directory + index * ENTRY.size)
        if offset + size > len(wad):
            raise ValueError("Truncated WAD lump " + repr(name))
        data = wad[offset:offset + size]
        key = name.rstrip(b"\0")
        if key in RAW_SIZES:
            if size != RAW_SIZES[key]:
                raise ValueError("Unexpected dimensions for " + repr(key))
            # Four 240-wide source samples occupy two native Tandy pixels.
            # Each source sample already has two dithered RGBI colors.
            data = bytes((hi & 0xf0) | (lo & 0x0f) for hi, lo in zip(data[::4], data[2::4]))
            converted.add(key)
        entries.append(ENTRY.pack(len(result), len(data), name))
        result.extend(data)
    if converted != RAW_SIZES.keys():
        raise ValueError("Missing raw pictures in the Doom8088 EGA WAD")
    HEADER.pack_into(result, 0, magic, count, len(result))
    result.extend(b"".join(entries))
    return result


def prepare(output, binaries, archives, modes):
    output.mkdir(parents=True, exist_ok=True)
    # Keep existing outputs intact if an archive is unavailable or invalid.
    with tempfile.TemporaryDirectory(dir=output) as tmp:
        stage = Path(tmp)
        for mode in modes:
            video, wad_name, exe_name, digest = MODES[mode]
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
                member, = [n for n in source.namelist() if Path(n).name.upper() == wad_name]
                wad = source.read(member)
            if mode == "tandy":
                wad_name, wad = "DOOMT16.WAD", pack_tandy(wad)
            (stage / wad_name).write_bytes(wad)
            shutil.copyfile(binaries / exe_name, stage / exe_name)
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
