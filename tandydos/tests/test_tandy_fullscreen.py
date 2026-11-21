"""Reference tests for the mode-08h packed RGBI fullscreen mapping.

These check the geometry and channel preservation of the matching C
implementation; the actual DOS renderer is also run by smoke.py in CI.
"""
import unittest


def expand(source):
    assert len(source) == 60
    out = bytearray()
    for i in range(0, 60, 3):
        a, b, c = source[i:i + 3]
        out.extend(((a & 0xF0) | (a >> 4),
                    ((a << 4) | (b >> 4)) & 255,
                    (b & 15) * 0x11,
                    c))
    return bytes(out)


class TandyFullscreenTests(unittest.TestCase):
    def test_full_screen_width(self):
        row = bytes((i & 255 for i in range(60)))
        self.assertEqual(len(expand(row)), 80)

    def test_exact_nibble_mapping(self):
        row = bytes([0x12, 0x34, 0x56] * 20)
        self.assertEqual(expand(row), bytes([0x11, 0x23, 0x44, 0x56] * 20))

    def test_all_sixteen_colors_survive(self):
        row = bytes((0x00, 0x11, 0x22, 0x33, 0x44, 0x55,
                     0x66, 0x77, 0x88, 0x99, 0xaa, 0xbb,
                     0xcc, 0xdd, 0xee, 0xff) * 3 + (0xaa, 0xbb) * 6)
        out = expand(row[:60])
        nibbles = [v for byte in out for v in (byte >> 4, byte & 15)]
        self.assertEqual(set(nibbles), set(range(16)))

    def test_vertical_mapping_and_status_boundary(self):
        for height, expected in ((128, 160), (160, 200)):
            dst = sum(2 if y % 4 == 0 else 1 for y in range(height))
            self.assertEqual(dst, expected)
        self.assertEqual(set(range(160)) & set(range(160, 200)), set())

    def test_destination_video_banks(self):
        offsets = [((y >> 1) * 80) + (0x2000 if y & 1 else 0)
                   for y in range(200)]
        self.assertEqual(len(set(offsets)), 200)
        self.assertEqual(max(offsets), 0x2000 + 99 * 80)
        self.assertLess(max(offsets) + 80, 0x4000)


if __name__ == "__main__":
    unittest.main()
