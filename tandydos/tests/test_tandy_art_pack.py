"""Original Tandy DOOM art asset generation and WAD integrity tests."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare import HEADER, ENTRY, wad_lumps, parse_patch_pixels
from tandy_art import (raster_patch, source_codes, draw_medkit, draw_armor,
                       draw_green_wall, draw_exit_door, build_tandy_art_wad)

def patch(w=24,h=24,value=0x22):
    out=bytearray(struct.pack("<hhhh",w,h,0,0)+b"\0"*(w*4))
    for x in range(w):
        struct.pack_into("<I",out,8+x*4,len(out))
        out.extend(bytes([0,h,0])+bytes([value])*h+bytes([0,255]))
    return bytes(out)

def wad(parts):
    out=bytearray(HEADER.size)
    entries=[]
    for k,data in parts:
        entries.append(ENTRY.pack(len(out),len(data),k.encode().ljust(8,b"\0")))
        out.extend(data)
    HEADER.pack_into(out,0,b"IWAD",len(entries),len(out))
    out.extend(b"".join(entries))
    return bytes(out)

class TestArt(unittest.TestCase):
    def setUp(self):
        self.mapping=source_codes(bytes(range(256))*(34))
    def test_16_source_color_choices(self):
        self.assertEqual(len(self.mapping),16)
        self.assertTrue(all(0<=c<256 for c in self.mapping.values()))
    def test_distinct_wall_and_exit_descriptions(self):
        wall={draw_green_wall(x,y) for x in range(64) for y in range(64)}
        door={draw_exit_door(x,y) for x in range(64) for y in range(64)}
        self.assertGreaterEqual(len(wall),5)
        self.assertGreaterEqual(len(door),5)
        self.assertNotEqual(wall,door)
    def test_medkit_cross_and_armor_silhouette(self):
        self.assertEqual(draw_medkit(31,36),12)
        self.assertIsNone(draw_medkit(0,0))
        self.assertNotEqual(draw_armor(20,30,False),draw_armor(20,30,True))
        self.assertIsNone(draw_armor(0,0))
    def test_patch_binary_valid_and_same_anchor(self):
        original=patch()
        created=raster_patch(original,draw_medkit,self.mapping,parse_patch_pixels)
        self.assertEqual(created[:8],original[:8])
        parsed=parse_patch_pixels(created)
        self.assertIsNotNone(parsed)
        self.assertTrue(0<len(parsed[2])<24*24)
        self.assertGreaterEqual(len({v for _,v in parsed[2].values()}),3)
    def test_wall_preserves_post_coverage(self):
        original=patch()
        created=raster_patch(original,draw_exit_door,self.mapping,parse_patch_pixels,
                             preserve_coverage=True)
        self.assertEqual(original[:8+4*24],created[:8+4*24])
        self.assertEqual(parse_patch_pixels(original)[2].keys(),
                         parse_patch_pixels(created)[2].keys())
    def test_art_wad_changes_only_five_targets(self):
        pnames=struct.pack("<I",2)+b"WALLP\0\0\0"+b"DOORP\0\0\0"
        # Doom8088 compact TEXTURE1: 14-byte header, 6-byte patch.
        def tex(name,idx):
            return (name.encode().ljust(8,b"\0")
                    +struct.pack("<HHH",64,64,1)
                    +struct.pack("<hhh",0,0,idx))
        t1=struct.pack("<III",2,12,32)+tex("STARTAN2",0)+tex("BIGDOOR1",1)
        original=wad([
            ("COLORMAP",bytes(range(256))*34),
            ("PNAMES",pnames),("TEXTURE1",t1),
            ("WALLP",patch()),("DOORP",patch()),
            ("S_START",b""),("MEDIA0",patch()),
            ("ARM1A0",patch()),("ARM2A0",patch()),("S_END",b""),
            ("TITLEPIC",b"title untouched"),
            ("DEMO1",b"gameplay untouched")
        ])
        final,stats=build_tandy_art_wad(original,wad_lumps,parse_patch_pixels,
                                        HEADER,ENTRY)
        old_order,old=wad_lumps(original)
        new_order,new=wad_lumps(final)
        self.assertEqual([x[0] for x in old_order],[x[0] for x in new_order])
        modified={k for k in old if old[k]!=new[k]}
        self.assertEqual(modified,{b"WALLP",b"DOORP",b"MEDIA0",b"ARM1A0",b"ARM2A0"})
        self.assertEqual(stats["modified_lumps"],5)
        for keep in (b"COLORMAP",b"TITLEPIC",b"DEMO1",b"TEXTURE1",b"PNAMES"):
            self.assertEqual(old[keep],new[keep])
        for name in modified:
            self.assertIsNotNone(parse_patch_pixels(new[name]))
if __name__=="__main__":
    unittest.main()
