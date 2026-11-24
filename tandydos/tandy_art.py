"""Original low-detail Tandy art pass, generated at WAD packaging time.

No Wolfenstein graphics are included. Strong silhouettes, broad panels,
green technical walls, unmistakable exit doors, health, green/blue armor.
Preserves EGA COLORMAP and map data. Runtime cost: zero.
"""
import struct
from clean_textures import candidate_patches

RGBI = (
    (0,0,0),(0,0,170),(0,170,0),(0,170,170),
    (170,0,0),(170,0,170),(170,85,0),(170,170,170),
    (85,85,85),(85,85,255),(85,255,85),(85,255,255),
    (255,85,85),(255,85,255),(255,255,85),(255,255,255),
)

def source_codes(colormap):
    """Select pre-existing EGA source indices that light as desired RGBI.

    A texture pixel is NOT a final hardware color: the renderer indexes
    COLORMAP with its 8-bit source value. Find the best original index
    for the desired visible color, favoring low-dither outputs.
    """
    if colormap is None or len(colormap) < 256:
        raise ValueError("Missing original EGA COLORMAP")
    result = {}
    for desired, rgb in enumerate(RGBI):
        best = (10**12, 0)
        for code in range(256):
            shown = colormap[code]
            p, q = RGBI[shown >> 4], RGBI[shown & 15]
            error = sum((rgb[i]-p[i])**2 + (rgb[i]-q[i])**2
                        for i in range(3))
            # Prefer a solid-looking pair when two candidates are close.
            error += sum((p[i]-q[i])**2 for i in range(3)) // 5
            if error < best[0]:
                best = (error, code)
        result[desired] = best[1]
    return result


def draw_green_wall(x, y):
    """1960s/90s chunky industrial techbase: plates and signal stripes."""
    if y < 6 or y >= 58 or x < 3 or x >= 61:
        return 0
    if y < 10 or y >= 55:
        return 8
    if y in (10, 54) or x in (3, 60):
        return 15
    if y in (14, 46) or x in (9, 32, 54):
        return 0
    if y in (15, 45) or x in (10, 33, 53):
        return 8
    # large inset plates; bottom dark undercut.
    if y > 47:
        return 2
    if y >= 40:
        return 0 if (x//8)%2 else 14
    if 17 <= y < 35 and 14 <= x < 49:
        if y < 20 or x in (14, 48):
            return 10
        if x in (18, 45) or y == 33:
            return 0
        if 26 < x < 37 and 23 < y < 30:
            return 14 if y in (24,25) else 4
        return 2 if (x + y) % 9 else 10
    return 2 if (x // 12 + y // 18) % 3 else 10


def draw_exit_door(x, y):
    """Wolf-readable symmetry, DOOM-style exit, central seam and frame."""
    if x < 4 or x >= 60 or y < 2 or y >= 62:
        return 0
    if x < 9 or x >= 55 or y < 8 or y >= 57:
        return 7 if (x+y)%7 else 15
    if x in (9,54) or y in (8,56):
        return 14
    if y < 20:
        if 15 <= x < 49:
            # simple central green arrow (no tiny text glyphs)
            if 16 <= x < 47 and 11 <= y < 14:
                return 10
            if 28 <= x <= 35 and 14 <= y < 19:
                return 10
        return 0
    if x in (30,31,32,33):
        return 0
    if 22 <= y < 28:
        return 8
    if x in (13,49) or y >= 52:
        return 0
    if (x in (15,16,47,48) and 30 <= y < 46):
        return 14
    if y in (32, 50):
        return 10
    return 2 if x < 32 else 8


def draw_medkit(x, y):
    """High-contrast white field kit with large red cross and handle."""
    if 23 <= x <= 40 and 11 <= y < 22:
        return 0 if x in (23,40) or y == 11 else 7
    if not (7 <= x < 57 and 20 <= y < 57):
        return None
    if x in (7,56) or y in (20,56):
        return 0
    if y >= 50:
        return 8
    if x in (10,53) or y == 23:
        return 7
    if (26 <= x < 38 and 28 <= y < 47) or (18 <= x < 46 and 34 <= y < 41):
        return 12
    if (24 <= x < 40 and 27 <= y < 48) or (17 <= x < 47 and 33 <= y < 42):
        return 4
    return 15


def draw_armor(x, y, blue=False):
    """One bold chestplate silhouette, different green/blue armor grades."""
    bright = 9 if blue else 10
    body = 1 if blue else 2
    if y < 14 or y >= 57:
        return None
    # shoulders widen out; chest tapers toward the waist.
    if y < 23:
        left, right = 8, 56
    elif y < 40:
        left, right = 11, 53
    else:
        left = 11 + (y-40)//3
        right = 53 - (y-40)//3
    if not (left <= x < right):
        return None
    if x in (left, right-1) or y in (14, 56):
        return 0
    if y < 19 or x in (left+2, right-3):
        return bright
    if y in (26, 46) or x in (30,33):
        return 8 if blue else 0
    if 26 <= x < 38 and 32 <= y < 41:
        return 14 if blue else 7
    if y > 48:
        return 8
    return body



def draw_pistol(x, y, frame="A"):
    """First-person chunky UAC pistol: readable muzzle, slide and gloved hand.

    Large silhouette uses only a handful of solid Tandy RGBI colors;
    no tiny noise or 2-color stipple. B/C firing frames have a short
    distinct recoil, but original DOOM muzzle-flash sprite stays intact.
    """
    y = y - (3 if frame in ("B", "C") else 0)
    if y < 15 or y >= 64:
        return None

    # Foreground glove wraps the grip on the bottom right.
    if 49 <= y and 40 <= x < 60:
        if x >= 57 or y == 49:
            return 0
        if x <= 45 and y < 58:
            return 6
        return 8 if y > 59 else 6
    if 53 <= y and 6 <= x < 25:
        if x < 9 or y == 53:
            return 0
        return 6 if y < 60 else 8

    # Grip and receiver: wide enough to read when scaled down.
    if 46 <= y and 24 <= x < 44:
        if x in (24, 43) or y == 46:
            return 0
        if x in (27, 28, 39) or y in (51, 60):
            return 8
        if x >= 36:
            return 6
        return 7 if y < 52 else 6
    if 38 <= y < 52 and 20 <= x < 48:
        if y in (38, 51) or x in (20, 47):
            return 0
        if 42 <= y < 46 and 27 <= x < 42:
            return 15 if x < 34 else 8
        if y == 40 and 22 <= x < 45:
            return 15
        return 8 if x > 41 else 7

    # Broad slide with dark muzzle & two stark highlight edges.
    if 27 <= y < 41 and 22 <= x < 45:
        if x in (22, 44) or y in (27, 40):
            return 0
        if y == 29 or x in (25, 26):
            return 15
        if 29 <= x < 37 and 32 <= y < 38:
            return 8
        return 7
    if 17 <= y < 29 and 28 <= x < 39:
        if x in (28, 38) or y == 17:
            return 0
        if y < 22 and 31 <= x <= 35:
            return 0  # unmistakable dark muzzle opening
        if x == 30 or y == 24:
            return 15
        return 8
    return None


def draw_shotgun(x, y, frame="A"):
    """Bolder Doom shotgun: squared barrel, pump, walnut grip and gloves."""
    # B is recoil, C/D are the pump frames; silhouette stays recognizable.
    y = y - (3 if frame == "B" else 0)
    pump = 3 if frame in ("C", "D") else 0
    if y < 10 or y >= 64:
        return None
    if y >= 51 and 5 <= x < 25:
        if x in (5, 24) or y == 51:
            return 0
        return 6 if y < 60 else 8
    if y >= 51 and 40 <= x < 59:
        if x in (40, 58) or y == 51:
            return 0
        return 6 if y < 59 else 8

    # Stock / central receiver at the bottom.
    if 43 <= y and 20 <= x < 46:
        if x in (20, 45) or y == 43:
            return 0
        if y < 48:
            return 15 if x in (24,25) else 8
        if 26 <= x < 39:
            return 6 if (y // 5) % 2 == 0 else 8
        return 7

    # Broad wooden pump: animated forearm slides during reload.
    if 33 + pump <= y < 49 + pump and 22 <= x < 44:
        if x in (22, 43) or y in (33 + pump, 48 + pump):
            return 0
        if y in (36 + pump, 40 + pump, 44 + pump):
            return 14
        return 6

    # Strong front-facing metal barrel and muzzle.
    if 14 <= y < 42 and 25 <= x < 40:
        if x in (25, 39) or y == 14:
            return 0
        if y < 22:
            if 30 <= x <= 35 and y <= 20:
                return 0
            return 15 if x in (27, 37) else 8
        if x in (27, 28) or y == 25:
            return 15
        if x in (37, 38) or y in (32, 39):
            return 0
        return 7
    return None



def draw_stone_wall(x, y, brown=False, salt=0):
    """Uncluttered industrial masonry with large staggered blocks."""
    base = 6 if brown else 8
    highlight = 14 if brown else 15
    shadow = 0
    face = 6 if brown else 7
    # 2 or 3 wide blocks per course, obvious at 30-column rendering.
    course = y // 17
    offset = 11 if (course & 1) else 0
    within = (x + offset + salt % 7) % 27
    if y % 17 in (0, 1, 16) or within in (0, 1):
        return shadow
    if y % 17 in (2, 3) or within in (2, 3):
        return highlight
    if y % 17 >= 13:
        return base
    if (course + (x+offset)//27) % 3 == 0:
        return face
    return base


def draw_control_wall(x, y, salt=0):
    """Big DOOM/UAC computer screens and clearly separated control banks."""
    if x < 3 or x >= 61 or y < 3 or y >= 60:
        return 0
    if x in (3, 60) or y in (3, 59):
        return 8
    # Main green console and blue diagnostic display.
    if 10 <= y < 38:
        if x in (8, 9, 31, 32, 54, 55) or y in (10, 37):
            return 15
        if 10 <= x < 30 or 34 <= x < 54:
            if y in (14, 15) or (x % 12 == 0 and y < 20):
                return 10
            if (x - (10 if x < 30 else 34)) % 9 <= 1 and y >= 25:
                return 2
            return 1 if x < 30 else 0
    if y in (41, 42, 56):
        return 0
    if 44 <= y < 55:
        # A few large indicator buttons, not tiny pixel noise.
        if 12 <= x < 20 or 27 <= x < 35 or 43 <= x < 51:
            return 14 if y < 48 else 4
        return 8
    return 2


def draw_support_wall(x, y, salt=0):
    """Heavy black/gray industrial beam with broad silver specular edges."""
    if x < 5 or x >= 59:
        return 0
    if x in (5, 6, 56, 57):
        return 15
    if x in (9, 10, 28, 29, 52, 53):
        return 0
    if x in (11, 12, 30, 31, 50, 51):
        return 8
    if y % 24 in (0, 1):
        return 0
    if y % 24 in (2, 3):
        return 7
    if y in (15, 47) and 16 < x < 49:
        return 14
    return 8 if (x // 11) % 2 else 7


def draw_warning_wall(x, y, salt=0):
    """Large DOOM hazard chevrons and thick steel guard rails."""
    if y < 12 or y >= 53:
        return 8
    if y in (12, 13, 50, 51, 52):
        return 0
    if 17 <= y < 36:
        return 14 if ((x // 10 + y // 10) & 1) else 0
    if y in (37, 38):
        return 15
    return 6 if (x//15)%2 else 8


def draw_industrial_wall(x, y, salt=0):
    """Bold, mostly blue-gray metal plates rather than noisy wallpaper."""
    if x % 32 in (0, 1) or y % 32 in (0, 1):
        return 0
    if x % 32 in (2, 3) or y % 32 in (2, 3):
        return 15
    if x % 32 >= 29 or y % 32 >= 29:
        return 8
    if x % 32 in (9, 10, 24, 25) and y % 32 in (10, 11, 23, 24):
        return 0
    return 7 if ((x//32 + y//32 + salt) % 3) else 8


def texture_art_style(name):
    """Keep Doom's material hierarchy; original pixels are newly drawn."""
    upper = name.upper()
    if "DOOR" in upper or "EXIT" in upper:
        return "exit", draw_exit_door
    if any(k in upper for k in ("COMP", "TEK", "COMPUT", "COMPS")):
        return "computer", draw_control_wall
    if any(k in upper for k in ("STARTAN", "STARG", "STAN", "GREEN")):
        return "green", draw_green_wall
    if any(k in upper for k in ("BRICK", "BROWN", "WOOD", "GSTONE")):
        return "brown", lambda x,y,s=0: draw_stone_wall(x,y,True,s)
    if any(k in upper for k in ("STONE", "GRAY", "SHAWN", "MARBLE", "ROCK")):
        return "stone", lambda x,y,s=0: draw_stone_wall(x,y,False,s)
    if any(k in upper for k in ("SUPPORT", "METAL", "PIPE", "SILVER")):
        return "support", draw_support_wall
    if any(k in upper for k in ("LITE", "LAMP", "SLAD", "HAZARD", "STEP")):
        return "warning", draw_warning_wall
    return "industrial", draw_industrial_wall


def e1m1_wall_texture_uses(wad, order, lumps):
    """Read the actual Doom8088 E1M1 compact SIDEDEFS (7 bytes each).

    Each sidedef holds three signed 8-bit texture indices matching the
    ordered TEXTURE1 directory (0 means no texture). This avoids
    guessing which wall material the real EX is currently drawing.
    """
    texture_data = lumps.get(b"TEXTURE1")
    if not texture_data or len(texture_data) < 4:
        raise ValueError("Art pack cannot locate TEXTURE1")
    total = struct.unpack_from("<I", texture_data)[0]
    if total > (len(texture_data)-4)//4:
        raise ValueError("Invalid TEXTURE1 directory")
    names = []
    for i in range(total):
        pos = struct.unpack_from("<I", texture_data, 4 + i*4)[0]
        if pos + 8 > len(texture_data):
            raise ValueError("Invalid TEXTURE1 name offset")
        names.append(texture_data[pos:pos+8].rstrip(b"\0").decode("ascii", "replace"))
    marker = next((i for i,(name,_,_) in enumerate(order)
                   if name.rstrip(b"\0") == b"E1M1"), None)
    if marker is None or marker + 3 >= len(order):
        raise ValueError("Cannot locate Doom shareware E1M1 SIDEDEFS")
    name, off, length = order[marker+3]
    if name.rstrip(b"\0") != b"SIDEDEFS" or length % 7:
        raise ValueError("E1M1 SIDEDEFS not in compact seven-byte format")
    used = {}
    for offset in range(off, off+length, 7):
        # int16 textureoffset, byte rowoffset, signed char top/bottom/mid,
        # byte sector index.
        for texture_id in struct.unpack_from("<bbb", wad, offset+3):
            if 0 < texture_id < len(names):
                name = names[texture_id]
                used[name] = used.get(name, 0) + 1
    if not used:
        raise ValueError("No valid E1M1 wall texture references found")
    return used


def redraw_e1m1_walls(wad, order, lumps, source, parse_patch_pixels,
                      already_changed, limit=36):
    """Redraw E1M1's most-used wall textures and every underlying patch.

    Skip shared previously converted patches; don't touch sprite lumps,
    raw HUD or COLORMAP. Max 36 texture names prevents scope creep.
    A separate ART.TXT lists exact map use and replacements for review.
    """
    frequency = e1m1_wall_texture_uses(wad, order, lumps)
    grouped = {}
    for texture, patch in candidate_patches(lumps):
        grouped.setdefault(texture, []).append(patch)
    changed = {}
    selected = []
    covered = 0
    for texture,count in sorted(frequency.items(),
                                key=lambda kv: (-kv[1],kv[0]))[:limit]:
        patches = grouped.get(texture, [])
        if not patches:
            continue
        style, artist = texture_art_style(texture)
        applied = []
        for patch in patches:
            if patch in already_changed or patch in changed:
                continue
            blob = lumps.get(patch)
            if parse_patch_pixels(blob) is None:
                continue
            # Draw simple, original art into pre-existing DOOM patch posts.
            # Unique, deterministic material variants across different
            # texture names without any on-device sampling or filters.
            salt = sum(texture.encode("ascii", "replace")) % 11
            def pixel(x,y,artist=artist,salt=salt):
                return artist(x,y,salt) if artist not in (
                    draw_green_wall, draw_exit_door) else artist(x,y)
            changed[patch] = raster_patch(
                blob, pixel, source, parse_patch_pixels,
                preserve_coverage=True)
            applied.append(patch.decode("ascii", "replace"))
        if applied or all(p in already_changed or p in changed for p in patches):
            covered += count
            selected.append("%s(%d,%s):%s" % (texture,count,style,
                            ",".join(applied) if applied else "shared"))
    return changed, {
        "e1m1_wall_uses": sum(frequency.values()),
        "e1m1_wall_textures": len(frequency),
        "e1m1_selected_textures": len(selected),
        "e1m1_rewritten_wall_patches": len(changed),
        "e1m1_sidedef_coverage_percent":
            round(100*covered/max(1,sum(frequency.values())),1),
        "e1m1_reworked": "; ".join(selected)
    }


def raster_patch(original, pixel_func, source, parse_patch_pixels,
                 preserve_coverage=False):
    """Write valid DOOM column posts, keeping dimensions and sprite anchor.

    Sprite generation may change transparent silhouette. For wall patches
    preserve their original opacity/posts and only replace indexed bytes.
    """
    parsed = parse_patch_pixels(original)
    if parsed is None:
        raise ValueError("Target is not a valid patch")
    width, height, existing = parsed
    if height > 254:
        raise ValueError("Art height exceeds DOOM post format")
    if preserve_coverage:
        updated = bytearray(original)
        for (x,y),(offset,unused) in existing.items():
            color = pixel_func(x*64//max(1,width), y*64//max(1,height))
            if color is not None:
                updated[offset] = source[color]
        return bytes(updated)
    result = bytearray(original[:8] + b"\0"*(width*4))
    for x in range(width):
        struct.pack_into("<I", result, 8+x*4, len(result))
        y = 0
        while y < height:
            def pix(yy):
                return pixel_func(x*64//width, yy*64//height)
            if pix(y) is None:
                y += 1
                continue
            start = y
            colors = []
            while y < height and pix(y) is not None and len(colors) < 254:
                colors.append(source[pix(y)])
                y += 1
            result.extend(bytes([start,len(colors),0]))
            result.extend(bytes(colors))
            result.append(0)
        result.append(255)
    return bytes(result)


def build_tandy_art_wad(classic_wad, wad_lumps, parse_patch_pixels,
                        header, entry):
    """Replace actual E1M1 wall textures, pickups and first-person weapons.

    No new texture names, sprite names, maps, colormaps, HUD, title or
    gameplay code. Output stays an IWAD with identical lump directory.
    Fail build if expected art targets are not found in source release.
    """
    order, lumps = wad_lumps(classic_wad)
    source = source_codes(lumps.get(b"COLORMAP"))
    available = candidate_patches(lumps)
    changes = {}
    details = {}

    targets = [
        ("green wall", ("STARTAN", "TEKWALL", "COMP", "GRAY"),
         draw_green_wall),
        ("exit door", ("EXITDOOR", "BIGDOOR", "DOOR"),
         draw_exit_door),
    ]
    used = set()
    for label, patterns, artist in targets:
        picked = None
        for pattern in patterns:
            for tex_name, patch_name in available:
                if (pattern in tex_name.upper() and
                        patch_name not in used and
                        parse_patch_pixels(lumps.get(patch_name)) is not None):
                    picked = (tex_name, patch_name)
                    break
            if picked:
                break
        if picked is None:
            raise ValueError("Art pack missing wall texture family: " + label)
        texture, name = picked
        changes[name] = raster_patch(lumps[name], artist, source,
                                     parse_patch_pixels,
                                     preserve_coverage=True)
        used.add(name)
        details[label] = texture + " -> " + name.decode("ascii","replace")

    # Redesign the walls the E1M1 level actually references, not
    # whichever STARTAN patch happens to appear first in TEXTURE1.
    # This is the central difference from the Build #25 tiny art test.
    world_changes, world_details = redraw_e1m1_walls(
        classic_wad, order, lumps, source, parse_patch_pixels,
        set(changes), limit=36)
    changes.update(world_changes)
    details.update(world_details)

    sprite_names = set()
    in_sprites = False
    for rawname, _off, _size in order:
        name = rawname.rstrip(b"\0")
        if name in (b"S_START", b"SS_START"):
            in_sprites = True
            continue
        if name in (b"S_END", b"SS_END"):
            in_sprites = False
            continue
        if in_sprites:
            sprite_names.add(name)

    sprites = {
        "medkit": (b"MEDI", draw_medkit),
        "green armor": (b"ARM1", lambda x,y: draw_armor(x,y,False)),
        "blue armor": (b"ARM2", lambda x,y: draw_armor(x,y,True)),
    }
    for label,(prefix,artist) in sprites.items():
        matched = sorted(name for name in sprite_names
                         if name.startswith(prefix) and
                         parse_patch_pixels(lumps.get(name)) is not None)
        if not matched:
            raise ValueError("Art pack missing pickup sprite: " + label)
        for name in matched:
            changes[name] = raster_patch(lumps[name], artist, source,
                                         parse_patch_pixels)
        details[label] = ",".join(n.decode("ascii","replace") for n in matched)

    # View weapons are separate from world pickup weapons. They use
    # PISG and SHTG four-letter sprite IDs in the original S_START
    # namespace. Replace ALL animation frames, not only their A frames.
    # Preserve original patch offset/anchor/dimensions for psprite
    # positioning; preserve PISF/SHTF muzzle flashes for compatibility.
    weapons = {
        "pistol": (b"PISG", draw_pistol),
        "shotgun": (b"SHTG", draw_shotgun),
    }
    for label, (prefix, painter) in weapons.items():
        matched = sorted(name for name in sprite_names
                         if name.startswith(prefix) and
                         parse_patch_pixels(lumps.get(name)) is not None)
        if not matched:
            raise ValueError("Art pack missing view weapon sprite: " + label)
        for name in matched:
            frame = chr(name[4]) if len(name) > 4 else "A"
            # Binding default args matters: the selected painter/frame
            # must be stable over all columns of this one sprite.
            def weapon_pixel(x, y, painter=painter, frame=frame):
                return painter(x, y, frame)
            changes[name] = raster_patch(lumps[name], weapon_pixel,
                                         source, parse_patch_pixels)
        details[label + " frames"] = ",".join(
            n.decode("ascii", "replace") for n in matched)

    result = bytearray(header.size)
    directory = []
    modified = 0
    for name,off,size in order:
        key = name.rstrip(b"\0")
        new = changes.get(key)
        data = classic_wad[off:off+size] if new is None else new
        if new is not None:
            modified += 1
        directory.append(entry.pack(len(result),len(data),name))
        result.extend(data)
    header.pack_into(result,0,b"IWAD",len(directory),len(result))
    result.extend(b"".join(directory))
    if modified != len(changes):
        raise ValueError("Art changes did not correspond to actual WAD lumps")
    details["modified_lumps"] = modified
    details["color_codes"] = ",".join("%d=%02X"%(n,source[n]) for n in
                                    (0,1,2,4,7,8,9,10,12,14,15))
    details["original_colormap"] = "unchanged"
    return bytes(result), details
