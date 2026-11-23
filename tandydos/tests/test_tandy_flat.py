"""Tandy RGBI floor/ceiling regression tests.

The original EGA flat renderer flipped high/low nibbles every row:
on the IBM PCjr CRT this becomes a distracting checkerboard.
Tandy now chooses a single solid RGBI color per flat column.
The original wall and HUD byte paths are not changed.
"""
from pathlib import Path
import re
import unittest

HEADER = Path(__file__).resolve().parents[1] / "engine" / "tandy_flat_color.h"
COLORS = (
    (0,0,0),(0,0,170),(0,170,0),(0,170,170),
    (170,0,0),(170,0,170),(170,85,0),(170,170,170),
    (85,85,85),(85,85,255),(85,255,85),(85,255,255),
    (255,85,85),(255,85,255),(255,255,85),(255,255,255)
)

def rgbnearest(p):
    a,b=COLORS[p>>4],COLORS[p&15]
    target=tuple((a[i]+b[i]+1)//2 for i in range(3))
    def err(c):
        return sum((target[i]-c[i])**2 * (3,4,2)[i] for i in range(3))
    k=min(range(16), key=lambda i: err(COLORS[i]))
    return (k<<4)|k

class TestTandyFlat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text=HEADER.read_text(encoding="ascii")
        cls.lookup=[int(x,16) for x in
                    re.findall(r"0x[0-9a-f]{2}",text.split("= {",1)[1])]

    def test_256_codes(self):
        self.assertEqual(len(self.lookup),256)
    def test_all_solid_flat_pixels(self):
        self.assertTrue(all(x>>4 == x&15 for x in self.lookup))
    def test_fixed_palette_averaging(self):
        self.assertEqual(self.lookup,list(map(rgbnearest,range(256))))
    def test_identity_palette_is_stable(self):
        self.assertEqual([self.lookup[n*17] for n in range(16)],
                         [n*17 for n in range(16)])
    def test_old_checkerboard_pair_is_not_alternated(self):
        self.assertEqual(self.lookup[0xf0]>>4, self.lookup[0xf0]&15)

if __name__=="__main__":
    unittest.main()
