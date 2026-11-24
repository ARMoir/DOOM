"""Original Tandy DOOM art asset generation and WAD integrity tests."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare import HEADER, ENTRY, wad_lumps, parse_patch_pixels
from tandy_art import (raster_patch, source_codes, draw_medkit, draw_armor,
                       draw_green_wall, draw_exit_door, draw_pistol,
                       draw_shotgun, build_tandy_art_wad,
                       e1m1_wall_texture_uses, texture_art_style)

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
    def test_first_person_weapon_shape_is_bold(self):
        for painter in (draw_pistol, draw_shotgun):
            pix = {(x,y): painter(x,y,"A")
                   for x in range(64) for y in range(64)}
            visible = {c for c in pix.values() if c is not None}
            self.assertGreaterEqual(len(visible), 4)
            self.assertIn(0,visible)
            self.assertIn(15,visible)
            # Gun fills center lower half but not the whole screen.
            self.assertGreater(sum(v is not None for v in pix.values()), 250)
            self.assertIsNone(painter(0,0,"A"))
            self.assertIsNotNone(painter(32,35,"A"))

    def test_pistol_and_shotgun_animation_frames_differ(self):
        self.assertNotEqual(
            [draw_pistol(x,y,"A") for x in range(64) for y in range(64)],
            [draw_pistol(x,y,"B") for x in range(64) for y in range(64)])
        self.assertNotEqual(
            [draw_shotgun(x,y,"A") for x in range(64) for y in range(64)],
            [draw_shotgun(x,y,"C") for x in range(64) for y in range(64)])

    def test_generated_gun_posts_preserve_anchor_and_parse(self):
        original=patch(w=36,h=48)
        for painter in (draw_pistol,draw_shotgun):
            for frame in ("A","B","C"):
                def draw(x,y):
                    return painter(x,y,frame)
                created=raster_patch(original,draw,self.mapping,
                                     parse_patch_pixels)
                self.assertEqual(created[:8],original[:8])
                parsed=parse_patch_pixels(created)
                self.assertIsNotNone(parsed)
                self.assertTrue(parsed[2])
                self.assertTrue(all(0 <= v < 256
                                    for _,v in parsed[2].values()))

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

    def test_e1m1_sidedef_texture_frequency(self):
        def tex(name,idx):
            return (name.encode().ljust(8,b"\0") +
                    struct.pack("<HHH",64,64,1) +
                    struct.pack("<hhh",0,0,idx))
        # index 0 is no texture; 1 green, 2 brown, 3 stone
        names = ["-", "STARTAN1", "BROWN1", "GRAY4"]
        offsets = [4+4*len(names)+20*i for i in range(len(names))]
        texdata = struct.pack("<I",len(names)) + b"".join(
            struct.pack("<I",v) for v in offsets)
        for i,name in enumerate(names):
            texdata += tex(name,0)
        side = lambda a,b,c: struct.pack("<hBbbbB",0,0,a,b,c,0)
        source = wad([("TEXTURE1",texdata),
                      ("E1M1",b""),("THINGS",b""),("LINEDEFS",b""),
                      ("SIDEDEFS",side(1,2,0)*4+side(3,1,0)*3),
                      ("SEGS",b""),("SSECTORS",b"")])
        order,lumps=wad_lumps(source)
        found=e1m1_wall_texture_uses(source,order,lumps)
        self.assertEqual(found,{"STARTAN1":7,"BROWN1":4,"GRAY4":3})

    def test_semantic_materials_not_uniform_green(self):
        styles={texture_art_style(n)[0] for n in
                ("STARTAN1","COMP2","GRAY4","BROWN1","BIGDOOR1",
                 "SUPPORT2","LITE2","OTHER")}
        self.assertEqual(len(styles),8)

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
            ("E1M1",b""),("THINGS",b""),("LINEDEFS",b""),
            ("SIDEDEFS",struct.pack("<hBbbbB",0,0,1,1,1,0)),
            ("WALLP",patch()),("DOORP",patch()),
            ("S_START",b""),("MEDIA0",patch()),
            ("ARM1A0",patch()),("ARM2A0",patch()),
            ("PISGA0",patch()),("PISGB0",patch()),("PISGC0",patch()),
            ("SHTGA0",patch()),("SHTGB0",patch()),("SHTGC0",patch()),
            ("PISFA0",patch()),("SHTFA0",patch()),("S_END",b""),
            ("TITLEPIC",b"title untouched"),
            ("DEMO1",b"gameplay untouched")
        ])
        final,stats=build_tandy_art_wad(original,wad_lumps,parse_patch_pixels,
                                        HEADER,ENTRY)
        old_order,old=wad_lumps(original)
        new_order,new=wad_lumps(final)
        self.assertEqual([x[0] for x in old_order],[x[0] for x in new_order])
        modified={k for k in old if old[k]!=new[k]}
        self.assertEqual(modified,{
            b"WALLP",b"DOORP",b"MEDIA0",b"ARM1A0",b"ARM2A0",
            b"PISGA0",b"PISGB0",b"PISGC0",
            b"SHTGA0",b"SHTGB0",b"SHTGC0",
        })
        self.assertEqual(stats["modified_lumps"],11)
        # Current muzzle flashes deliberately stay unchanged.
        self.assertEqual(old[b"PISFA0"],new[b"PISFA0"])
        self.assertEqual(old[b"SHTFA0"],new[b"SHTFA0"])
        self.assertIn("pistol frames",stats)
        self.assertIn("shotgun frames",stats)
        for keep in (b"COLORMAP",b"TITLEPIC",b"DEMO1",b"TEXTURE1",b"PNAMES"):
            self.assertEqual(old[keep],new[keep])
        for name in modified:
            self.assertIsNotNone(parse_patch_pixels(new[name]))
if __name__=="__main__":
    unittest.main()
