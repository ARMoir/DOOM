"""Regression tests for VGA-source Tandy RGBI artwork conversion."""
import struct
import unittest

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare import (HEADER, ENTRY, RAW_SIZES, TANDY_RGBI,
                     nearest_rgbi, pack_tandy, quantize_raw_vga,
                     wad_lumps)


def make_wad(parts):
    result = bytearray(HEADER.size)
    directory = []
    for name, blob in parts:
        directory.append((len(result), len(blob), name.encode("ascii").ljust(8, b"\0")))
        result.extend(blob)
    HEADER.pack_into(result, 0, b"IWAD", len(parts), len(result))
    result.extend(b"".join(ENTRY.pack(*row) for row in directory))
    return bytes(result)


def palette():
    colors = bytearray(768)
    # First 16 indices represent exactly the RGBI colors.
    for i, rgb in enumerate(TANDY_RGBI):
        colors[3*i:3*i+3] = bytes(rgb)
    return bytes(colors)


class TandyArtTests(unittest.TestCase):
    def test_nearest_rgb_identity(self):
        self.assertEqual([nearest_rgbi(*c) for c in TANDY_RGBI],
                         list(range(16)))

    def test_packed_two_pixels_correct_nibble_order(self):
        # Four 8-bit VGA pixels: red red blue blue.
        self.assertEqual(quantize_raw_vga(bytes([4, 4, 1, 1]),
                                           palette(), 4), b"\x41")

    def test_black_red_yellow_and_blue_groups(self):
        source = bytes([0, 0, 4, 4, 14, 14, 1, 1])
        self.assertEqual(quantize_raw_vga(source, palette(), 8),
                         b"\x04\xe1")

    def test_no_artificial_checkerboard(self):
        line = bytes([4] * 240)
        image = line * 160
        converted = quantize_raw_vga(image, palette(), 240)
        self.assertEqual(len(converted), 240 * 160 // 4)
        self.assertEqual(set(converted), {0x44})

    def test_floor_32_pixel_4bpp_tile(self):
        raw = bytes([2] * (64 * 64))
        converted = quantize_raw_vga(raw, palette(), 64)
        self.assertEqual(len(converted), 16 * 64)
        self.assertEqual(set(converted), {0x22})

    def test_preserve_engine_lump_order_and_binary_content(self):
        big = b"\x3a\x7f\x0b" * 17
        ega = make_wad([("DATA", big)] +
                       [(k.decode(), bytes([0x8e]) * length)
                        for k, length in RAW_SIZES.items()])
        vga = make_wad([("PLAYPAL", palette())] +
                       [(k.decode(), bytes([4]) * length)
                        for k, length in RAW_SIZES.items()])
        packed = pack_tandy(ega, vga)
        entries, contents = wad_lumps(packed)
        self.assertEqual([e[0].rstrip(b"\0") for e in entries],
                         [b"DATA", *RAW_SIZES.keys()])
        self.assertEqual(contents[b"DATA"], big)
        for k, length in RAW_SIZES.items():
            self.assertEqual(len(contents[k]), length // 4)
            self.assertEqual(set(contents[k]), {0x44})

    def test_missing_vga_picture_is_an_error(self):
        ega = make_wad([("TITLEPIC", b"\x00" * RAW_SIZES[b"TITLEPIC"])])
        vga = make_wad([("PLAYPAL", palette())])
        with self.assertRaisesRegex(ValueError, "VGA picture missing"):
            pack_tandy(ega, vga)

    def test_truncated_wad_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            wad_lumps(b"IW")


if __name__ == "__main__":
    unittest.main()
