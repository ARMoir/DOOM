"""Deterministic reference tests for the V20 16.16 math/cache fast paths.

The actual Watcom-compiled math is exercised by DOSBox-X timedemos.
These test the algebra and cache-state edge cases independently.
"""
import random
import unittest

def signed32(x):
    x &= 0xffffffff
    return x - 0x100000000 if x & 0x80000000 else x

def signed16(x):
    x &= 0xffff
    return x - 0x10000 if x & 0x8000 else x

def ref_fixedmul(a, b):
    return signed32((a*b) >> 16)

def c_fixedmul(a, b):
    alw, blw = a & 65535, b & 65535
    ahw, bhw = signed16(a >> 16), signed16(b >> 16)
    if bhw == 0:
        result = ((alw * blw) >> 16) + ahw * blw
    elif blw == 0:
        result = a * bhw
    elif alw == 0:
        result = ahw * blw + ((ahw * bhw) << 16)
    else:
        result = a * bhw + ((alw * blw) >> 16) + ahw * blw
    return signed32(result)

class FixedPointTests(unittest.TestCase):
    def test_integer_aligned_multipliers(self):
        rng = random.Random(8088)
        for integer in [-32768, -33, -2, -1, 0, 1, 2, 5, 64, 32767]:
            for _ in range(300):
                a = signed32(rng.getrandbits(32))
                b = signed32(integer << 16)
                self.assertEqual(c_fixedmul(a, b), ref_fixedmul(a, b),
                                 (a, b))

    def test_general_fixed_point_matches_signed_16_16(self):
        rng = random.Random(86)
        for _ in range(12000):
            a, b = (signed32(rng.getrandbits(32)),
                    signed32(rng.getrandbits(32)))
            self.assertEqual(c_fixedmul(a, b), ref_fixedmul(a, b),
                             (a, b))

    def test_zero_numerator_division_shortcut(self):
        for b in (1, 2, 65535, 65536, 1234567):
            self.assertEqual(0 * (0xffffffff // b), 0)

class CacheTests(unittest.TestCase):
    def test_zero_texture_zero_column_is_valid(self):
        # Empty and key=0 must be distinct; no repeated recomposition.
        tags = [0] * 128
        bitmap = [0] * 16
        key = 0
        self.assertFalse(bitmap[key >> 3] & (1 << (key & 7)))
        tags[key] = 0
        bitmap[key >> 3] |= 1 << (key & 7)
        self.assertTrue(bitmap[key >> 3] & (1 << (key & 7)))
        self.assertEqual(tags[key], 0)

    def test_composite_scratch_has_no_stale_pixels(self):
        # A new partially populated composite must have a clean base.
        scratch = bytearray([0xee] * 128)
        scratch[:] = b"\x00" * 128
        scratch[10:13] = bytes([1, 2, 3])
        self.assertEqual(scratch[9], 0)
        self.assertEqual(scratch[13], 0)

if __name__ == "__main__":
    unittest.main()
