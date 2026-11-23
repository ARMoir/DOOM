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
        self.assertEqual(lumps[b"COLORMAP"], cmap)
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
        self.assertEqual(converted[b"COLORMAP"], cmap)
        self.assertEqual(converted[b"COLORMP1"], cmap)

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


    def test_native_vga_light_table_tracks_source_color(self):
        from prepare import (make_native_colormap, collect_vga_examples,
                             rgb_native_ui_patch)
        # Source byte 0x6c is misleading: the matching original VGA
        # artwork actually contains solid deep red (palette index 4).
        # EGA output is deliberately green. Mapping must follow VGA.
        def post(index):
            return struct.pack("<hhhhI", 1, 5, 0, 0, 12) + (
                bytes([0, 1, 0, index, 0, 255]))
        ega = {b"WALL": post(0x6c)}
        vga = {b"WALL": post(4)}
        hist, stats = collect_vga_examples(ega, vga, {b"WALL"})
        self.assertEqual(stats["matched_pixels"], 1)
        self.assertEqual(stats["source_codes"], 1)
        egamap = bytearray([0x22] * (34 * 256))
        vgamap = bytearray(bytes(range(256)) * 34)
        vgamap[31 * 256 + 4] = 0  # 31 = darkest shade.
        out = make_native_colormap(bytes(egamap), bytes(vgamap),
                                   palette(), hist)
        self.assertEqual(out[0x6c], 0x44)
        self.assertEqual(out[31 * 256 + 0x6c], 0x00)
        self.assertEqual(out[0x12], 0x22)  # Unobserved => EGA fallback

    def test_vga_ui_patch_preserves_binary_layout(self):
        from prepare import rgb_native_ui_patch
        def post(index):
            return struct.pack("<hhhhI", 1, 5, 0, 0, 12) + (
                bytes([0, 1, 0, index, 0, 255]))
        ega = post(0x2a)
        vga = post(14)
        native = rgb_native_ui_patch(ega, vga, palette())
        self.assertEqual(native[:15], ega[:15])
        self.assertEqual(native[15], 0xee)
        self.assertEqual(native[16:], ega[16:])
        self.assertIsNone(rgb_native_ui_patch(ega, b"invalid", palette()))

    def test_native_rgb_pipeline_is_byte_aligned_for_every_shade(self):
        from prepare import make_native_colormap
        hist = [[0] * 256 for _ in range(256)]
        hist[0x1e][9] = 5
        pal = palette()
        egamap = bytes(range(256)) * 34
        vgamap = bytes(range(256)) * 34
        out = make_native_colormap(egamap, vgamap, pal, hist)
        self.assertEqual(len(out), len(egamap))
        self.assertTrue(all(v >> 4 == (v & 15) for v in out))
        self.assertEqual(out[0x1e], 0x99)

    def test_gamma_variant_lifts_midtones_without_extra_runtime_bytes(self):
        from prepare import gamma_rgb, make_native_colormap
        self.assertEqual(gamma_rgb(0, 4), 0)
        self.assertEqual(gamma_rgb(255, 4), 255)
        self.assertGreater(gamma_rgb(120, 4), gamma_rgb(120, 0))
        hist = [[0] * 256 for _ in range(256)]
        hist[17][6] = 1
        cmap = bytes(range(256)) * 34
        out = make_native_colormap(cmap, cmap, palette(), hist, gamma=4)
        self.assertEqual(len(out), 34 * 256)


    def test_default_wad_keeps_original_world_colors_and_better_hud(self):
        """Physical Tandy regression: never re-flatten the world colors.

        The title/HUD improvements are independent of the wall/sprite
        light-table conversion. The 34*256 COLORMAP, gamma variant,
        wall samples, and sprite samples must remain bit-identical.
        """
        from prepare import SOLID_RGBI
        def patch(byte):
            return struct.pack("<hhhhI", 1, 5, 0, 0, 12) + (
                bytes([0, 1, 0, byte, 0, 255]))
        cmap = bytes(range(256)) * 34
        gamma = cmap[::-1]
        wall = patch(0x1e)
        sprite = patch(0x28)
        hud = patch(0x36)
        pnames = struct.pack("<I8s", 1, b"WALLA\0\0\0")
        ega = make_wad([
            ("PNAMES", pnames), ("COLORMAP", cmap),
            ("COLORMP1", gamma), ("WALLA", wall),
            ("S_START", b""), ("SPRITA", sprite), ("S_END", b""),
            ("STFACE", hud), ("DEMO1", b"original-demodata"),
        ] + [(k.decode(), bytes([0x8e]) * length)
             for k, length in RAW_SIZES.items()])
        vga = make_wad([("PLAYPAL", palette())] +
                       [(k.decode(), bytes([4]) * length)
                        for k, length in RAW_SIZES.items()])
        stats = {}
        packed = pack_tandy(ega, vga, stats=stats)
        _order, lumps = wad_lumps(packed)
        self.assertEqual(lumps[b"COLORMAP"], cmap)
        self.assertEqual(lumps[b"COLORMP1"], gamma)
        self.assertEqual(lumps[b"WALLA"], wall)
        self.assertEqual(lumps[b"SPRITA"], sprite)
        self.assertEqual(lumps[b"DEMO1"], b"original-demodata")
        self.assertEqual(lumps[b"STFACE"][15], SOLID_RGBI[0x36])
        self.assertEqual(set(lumps[b"TITLEPIC"]), {0x88})
        self.assertEqual(stats["colormap_strategy"], "original_ega_unchanged")
        self.assertTrue(stats["world_colormaps_unchanged"])
        self.assertEqual(stats["world_mode"], "original")

    def test_experimental_world_reconstruction_only_on_explicit_opt_in(self):
        """Retain a controlled comparison path without shipping it by default."""
        cmap = bytes([0x1e] * (34 * 256))
        game = make_wad([("COLORMAP", cmap)] +
                        [(k.decode(), bytes([0x8e]) * length)
                         for k, length in RAW_SIZES.items()])
        vga = make_wad([("PLAYPAL", palette()), ("COLORMAP", cmap)] +
                       [(k.decode(), bytes([4]) * length)
                        for k, length in RAW_SIZES.items()])
        standard = pack_tandy(game, vga)
        experimental = pack_tandy(game, vga, reconstruct_world=True)
        self.assertEqual(wad_lumps(standard)[1][b"COLORMAP"], cmap)
        self.assertNotEqual(wad_lumps(experimental)[1][b"COLORMAP"], cmap)

    def test_truncated_wad_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            wad_lumps(b"IW")


if __name__ == "__main__":
    unittest.main()
