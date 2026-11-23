"""Conservative wall-texture cleanup for Tandy 16-color DOOM.

Offline build-only process. Inspired by Wolfenstein's large clear shapes;
does not copy/repackage Wolfenstein assets.
"""
import struct

FAMILIES = (
    ("tech", ("STARTAN", "COMP", "TEKWALL")),
    ("stone", ("STONE", "GRAY", "SHAWN")),
    ("brown", ("BROWN", "BRICK", "WOOD")),
    ("door", ("DOOR", "BIGDOOR")),
    ("trim", ("SUPPORT", "METAL", "LITE")),
)

def candidate_patches(lumps):
    pnames, tex = lumps.get(b"PNAMES"), lumps.get(b"TEXTURE1")
    if not pnames or not tex or len(pnames)<4 or len(tex)<4:
        return []
    count=struct.unpack_from("<I",pnames)[0]
    if count>(len(pnames)-4)//8:
        raise ValueError("Invalid PNAMES directory")
    names=[pnames[4+8*i:12+8*i].rstrip(b"\0") for i in range(count)]
    n=struct.unpack_from("<I",tex)[0]
    if n>(len(tex)-4)//4:
        raise ValueError("Invalid TEXTURE1 directory")
    result=[]
    for i in range(n):
        off=struct.unpack_from("<I",tex,4+4*i)[0]
        if off+22>len(tex):
            raise ValueError("Truncated TEXTURE1")
        name=tex[off:off+8].rstrip(b"\0").decode("ascii","replace")
        patches=struct.unpack_from("<h",tex,off+20)[0]
        if patches<1 or off+22+10*patches>len(tex):
            raise ValueError("Invalid TEXTURE1 patch count")
        for p in range(patches):
            idx=struct.unpack_from("<h",tex,off+26+10*p)[0]
            if 0<=idx<len(names) and names[idx] in lumps:
                result.append((name,names[idx]))
    return result

def clean_patch(blob, parse_patch_pixels):
    parsed=parse_patch_pixels(blob)
    if parsed is None:
        return blob,0
    _,_,pixels=parsed
    if len(pixels)<16:
        return blob,0
    out=bytearray(blob)
    changes=0
    for (x,y),(off,val) in pixels.items():
        neighbor=[pixels[(x+dx,y+dy)][1] for dx,dy in
                  ((-1,0),(1,0),(0,-1),(0,1))
                  if (x+dx,y+dy) in pixels]
        if len(neighbor)<3:
            continue
        counts={}
        for code in neighbor:
            counts[code]=counts.get(code,0)+1
        dominant,n=max(counts.items(),key=lambda q:q[1])
        # Remove isolated pixels only. Never blur a bold outline.
        if n>=3 and dominant!=val:
            out[off]=dominant
            changes+=1
    return bytes(out),changes

def make_clean_patches(lumps, parse_patch_pixels):
    available=candidate_patches(lumps)
    used=set()
    replacements={}
    report=[]
    for label,patterns in FAMILIES:
        for texture,patch in available:
            if patch in used or not any(q in texture.upper() for q in patterns):
                continue
            if parse_patch_pixels(lumps[patch]) is None:
                continue
            output,count=clean_patch(lumps[patch],parse_patch_pixels)
            replacements[patch]=output
            report.append((label,texture,patch.decode("ascii","replace"),count))
            used.add(patch)
            break
    return replacements,report
