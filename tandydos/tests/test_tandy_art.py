"""Regression tests for VGA-source Tandy RGBI artwork conversion."""
import struct
import unittest

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare import (HEADER, ENTRY, RAW_SIZES, TANDY_RGBI,
                     nearest_rgbi, pack_tandy, quantize_raw_vga,
                     wad_lumps, is_colormap_lump, world_patch_names)


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


    def test_solid_colors_preserve_identity_pairs(self):
        from prepare import SOLID_RGBI, solid_rgbi_byte
        for i in range(16):
            byte = i * 17
            self.assertEqual(solid_rgbi_byte(byte), byte)
            self.assertEqual(SOLID_RGBI[byte], byte)

    def test_checkerboard_pair_collapses_to_one_hue(self):
        from prepare import solid_rgbi_byte
        for byte in range(256):
            value = solid_rgbi_byte(byte)
            self.assertEqual(value >> 4, value & 15,
                             f"source color pair {byte:02x}")

    def test_full_ega_colormap_converted_without_shifting_indices(self):
        from prepare import solidify_colormap, SOLID_RGBI
        source = bytes(range(256)) * 34
        converted = solidify_colormap(source)
        self.assertEqual(len(converted), len(source))
        self.assertEqual(converted[:256], SOLID_RGBI)
        self.assertEqual(converted[256:512], SOLID_RGBI)
        with self.assertRaisesRegex(ValueError, "COLORMAP"):
            solidify_colormap(source[:-1])

    def test_patch_posts_solidify_not_headers(self):
        from prepare import solidify_patch, SOLID_RGBI
        # 2 columns, each with one 2-pixel post, plus end marker.
        first = bytes([0, 2, 0, 0x1e, 0xf2, 0, 255])
        second = bytes([0, 2, 0, 0x36, 0x4b, 0, 255])
        header = struct.pack("<hhhhII", 2, 8, 1, 2, 16, 23)
        patch = header + first + second
        converted = solidify_patch(patch)
        self.assertEqual(len(converted), len(patch))
        self.assertEqual(converted[:19], patch[:19])
        self.assertEqual(converted[19:21], bytes([SOLID_RGBI[0x1e], SOLID_RGBI[0xf2]]))
        self.assertEqual(converted[23:26], patch[23:26])
        self.assertEqual(converted[26:28], bytes([SOLID_RGBI[0x36], SOLID_RGBI[0x4b]]))
        self.assertEqual(converted[28:], patch[28:])

    def test_invalid_binary_is_not_misclassified_as_patch(self):
        from prepare import solidify_patch
        binary = struct.pack("<hhhhI", 2, 8, 1, 2, 0xf0000000) + b"not-a-patch"
        self.assertEqual(solidify_patch(binary), binary)

    def test_full_wad_keeps_map_data_and_applies_both_transforms(self):
        from prepare import pack_tandy, wad_lumps, SOLID_RGBI
        mapdata = b"DOOMMAP" + bytes(range(64))
        post = struct.pack("<hhhhI", 1, 5, 0, 0, 12) + bytes([0, 1, 0, 0x19, 0, 255])
        cmap = bytes(range(256)) * 34
        ega = make_wad([("COLORMAP", cmap), ("DEMO1", mapdata),
                        ("TESTPATCH", post)] +
                       [(k.decode(), bytes([0x8e]) * length)
                        for k, length in RAW_SIZES.items()])
        vga = make_wad([("PLAYPAL", palette())] +
                       [(k.decode(), bytes([4]) * length)
                        for k, length in RAW_SIZES.items()])
        converted = pack_tandy(ega, vga)
        order, lumps = wad_lumps(converted)
        self.assertEqual([row[0].rstrip(b"\0") for row in order],
                         [b"COLORMAP", b"DEMO1", b"TESTPATC",
                          *RAW_SIZES.keys()])
        self.assertEqual(lumps[b"DEMO1"], mapdata)
        self.assertEqual(lumps[b"COLORMAP"][:256], SOLID_RGBI)
        self.assertEqual(lumps[b"TESTPATC"][15], SOLID_RGBI[0x19])


    def test_world_texture_and_sprite_samples_are_not_double_quantized(self):
        from prepare import SOLID_RGBI
        # A wall and a sprite with exactly the same pair of source colors
        # as a HUD face must keep their EGA input byte, because the game
        # first maps world textures through COLORMAP. UI is drawn raw.
        def patch():
            return (struct.pack("<hhhhI", 1, 5, 0, 0, 12) +
                    bytes([0, 1, 0, 0x1e, 0, 255]))
        pnames = struct.pack("<I8s", 1, b"WALLA\0\0\0")
        cmap = bytes(range(256)) * 34
        game = [
            ("PNAMES", pnames), ("COLORMAP", cmap),
            ("COLORMP1", cmap), ("WALLA", patch()),
            ("S_START", b""), ("SPRITA", patch()),
            ("S_END", b""), ("STFACE", patch()),
        ]
        ega = make_wad(game + [(k.decode(), bytes([0x8e]) * length)
                               for k, length in RAW_SIZES.items()])
        vga = make_wad([("PLAYPAL", palette())] +
                       [(k.decode(), bytes([4]) * length)
                        for k, length in RAW_SIZES.items()])
        packed = pack_tandy(ega, vga)
        _, converted = wad_lumps(packed)
        self.assertEqual(converted[b"WALLA"], patch())
        self.assertEqual(converted[b"SPRITA"], patch())
        self.assertEqual(converted[b"STFACE"][15], SOLID_RGBI[0x1e])
        self.assertEqual(converted[b"COLORMAP"][:256], SOLID_RGBI)
        self.assertEqual(converted[b"COLORMP1"][:256], SOLID_RGBI)

    def test_bad_patch_directory_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "PNAMES"):
            world_patch_names({b"PNAMES": struct.pack("<I", 2) + b"ONE\0\0\0\0\0"},
                              [])

    def test_gamma_colormap_name_match_is_exact(self):
        self.assertTrue(is_colormap_lump(b"COLORMAP"))
        self.assertTrue(is_colormap_lump(b"COLORMP1"))
        self.assertTrue(is_colormap_lump(b"COLORMP4"))
        self.assertFalse(is_colormap_lump(b"COLORM0P"))
        self.assertFalse(is_colormap_lump(b"COLORM"))

    def test_truncated_wad_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            wad_lumps(b"IW")


if __name__ == "__main__":
    unittest.main()
