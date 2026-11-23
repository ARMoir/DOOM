"""Tests for source-aware, non-destructive Tandy Clean conversion."""
import struct
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean_textures import clean_patch,candidate_patches,make_clean_patches
from prepare import parse_patch_pixels

def solid_patch(width=5,height=5):
    # DOOM patch header, five columns with one full-height post each
    offsets=[]
    data=bytearray(struct.pack("<hhhh",width,height,0,0)+bytes(width*4))
    for x in range(width):
        offsets.append(len(data))
        column=[1]*(height)
        if x==2:column[2]=2
        data.extend(bytes([0,height,0]+column+[0,255]))
    for x,offset in enumerate(offsets):
        struct.pack_into("<I",data,8+x*4,offset)
    return bytes(data)

class TestClean(unittest.TestCase):
    def test_removes_only_isolated_pixel(self):
        source=solid_patch()
        output,n=clean_patch(source,parse_patch_pixels)
        self.assertEqual(n,1)
        self.assertEqual(output[0:28],source[0:28])
        self.assertEqual(parse_patch_pixels(output)[2][(2,2)][1],1)
        self.assertEqual(len(output),len(source))
    def test_does_not_touch_invalid_patch(self):
        self.assertEqual(clean_patch(b"invalid",parse_patch_pixels),
                         (b"invalid",0))
    def test_no_texture_directory_is_noop(self):
        self.assertEqual(make_clean_patches({},parse_patch_pixels),({},[]))
    def test_repeated_solid_pixels_are_unchanged(self):
        source=solid_patch()
        cleaned,n=clean_patch(source,parse_patch_pixels)
        unchanged,n2=clean_patch(cleaned,parse_patch_pixels)
        self.assertEqual(n2,0)
        self.assertEqual(unchanged,cleaned)
if __name__=="__main__":
    unittest.main()
