# DOOM for the Tandy 1000 EX

This fork builds single-player DOOM Episode 1 for real-mode DOS on an 8088, 8086 or NEC V20. On a Tandy 1000 EX with 640 KB installed, run **`DOOM`** and keep `DOOMT16.WAD` in the game directory. The new 8086 launcher detects VGA, then native Tandy RGBI video, otherwise falls back to CGA; `DOOM -tandy` forces the preferred 16-color Tandy renderer. The game includes monsters, weapons, the automap and PC speaker effects.

Download the newest **DOOM-DOS.zip** from [GitHub Releases](https://github.com/ARMoir/DOOM/releases/latest), unzip it to a single directory on the CompactFlash card, and run **`DOOM`**. The release contains one launchable `DOOM.EXE` and four internal `.OVL` renderer programs; DOS loads just the one it needs so the launcher does not remain in conventional memory. Each push to `master` compiles the selector and all four renderers, tests the automatic and manual display choices with **96-tic smoke tests** in DOSBox-X, and publishes a new downloadable DOS release. Only after the new ZIP is confirmed does the workflow delete older releases and obsolete DOOM-DOS Actions artifacts. For the longer emulator check, use `python tandydos/smoke.py --emulator PATH --game DIRECTORY --full`.

| DOS command | Renderer overlay | Video mode | Game data |
| --- | --- | --- | --- |
| `DOOM` | Auto-selected | Detects VGA, Tandy, or CGA | Matching WAD |
| `DOOM -tandy` | `DOOMTGA.OVL` | Fullscreen Tandy 160×200, 16 RGBI colors, fast 30-column renderer | `DOOMT16.WAD` |
| `DOOM -tandyhi` | `DOOMTGH.OVL` | Fullscreen Tandy 16-color, 60-column high-detail renderer | `DOOMT16.WAD` |
| `DOOM -cga` | `DOOMCGA.OVL` | CGA 320×200, four colors, F5 changes palette | `DOOM4.WAD` |
| `DOOM -vga` | `DOOMVGA.OVL` | VGA 320×200, 256 colors | `DOOM1.WAD` |

Use `DOOM -detect` to inspect autodetection, or `DOOM -video auto|tandy|tandyhi|cga|vga` to override it. Other DOOM arguments pass through unchanged.

To prepare the same folder on a modern PC with Python 3, run `python tandydos/prepare.py --out DOOMDOS` from a checkout. To prepare only the EX version, add `--mode tandy`. The script packages the [mode-specific executables](tandydos/bin) as `.OVL` files and includes the new `DOOM.EXE` selector, verifies the [upstream shareware archives](https://github.com/FrenkelS/Doom8088/releases/tag/v20260304), and packs the native Tandy artwork. With existing release ZIPs, pass `--archives DIRECTORY`.

Use the arrows to move, Ctrl to fire, Space to open doors, Tab for the automap, and F10 to return to DOS. To measure your EX, run `DOOM -tandy -timedemo demo3` and compare with `DOOM -cga -timedemo demo3`. The benchmark prints its frame rate at the DOS prompt. Episode 1 uses flat floors and ceilings. The port omits savegames, music, multiplayer and later episodes.

## Building

Install Open Watcom v2 and Python 3 on a modern host. Set `WATCOM` to the compiler installation directory and run `python tandydos/build.py` from the repository root. It builds the four DOS renderer programs with the medium memory model and 8086 instruction set, plus the small-model `DOOM.EXE` selector. The release renames the renderer MZ programs to `.OVL`, keeping only one user-facing executable. Each target has its own compile and link directory.

The port links the argument parser and deterministic random number generator directly from [id Software's Linux DOOM 1.10](linuxdoom-1.10). The segmented engine, Episode 1 game logic and low-detail renderers come from [Frenkel Smeijers' Doom8088](https://github.com/FrenkelS/Doom8088/tree/b3073a2eb2811cd14caba6549694fc3bfcd6dd29), through GBADoom and PrBoom. The Tandy backend follows [WolfensteinCGA](https://github.com/jhhoward/WolfensteinCGA) in selecting BIOS mode 08h and blitting packed scanlines to the two banks at B800h. DOOMTGA and DOOMCGA project 30 columns and shade two rows per texture sample. DOOMTGH projects 60 columns at full vertical detail. Both Tandy builds keep a 9,600-byte packed buffer, then stretch each 120-pixel RGBI row to 160 pixels and each 160-row frame to 200 rows as they copy it to the Tandy mode 08h interleaved video banks. This fills the physical CRT at the cost of extra copy work; the 3D renderer still processes only 30 or 60 columns. Each of the 16 palette registers is explicitly set to its canonical 4-bit RGBI value with Tandy BIOS INT 10h AX=1000h; damage/bonus border effects use AX=1001h without reducing in-game color depth. Experimental 8086 blit/texture-scaler assembly is retained in the source but disabled because it has not passed the 8086 smoke test. Run `BENCH.BAT` on your EX to compare the same 96 game tics in both native modes. The slower CI comparison uses DOSBox-X at 400 fixed cycles per millisecond. That setting measures relative speed and has no precise MHz equivalence. The desktop converter uses the clean VGA 256-color art and palette to precompute a sharp 16-color RGBI title, status bar, map and background images; the EGA archive supplies the remaining small 16-color engine data. This work happens on a modern host, so the EX's runtime CPU cost is unchanged. Source notices are retained in [tandydos/engine](tandydos/engine).

## WolfensteinCGA compatibility and hardware validation

The 8088-specific ideas already incorporated from
[WolfensteinCGA](https://github.com/jhhoward/WolfensteinCGA)
are native Tandy mode 08h, packed CGA/Tandy video access via B800h
with two interleaved banks, 16-bit real-mode support, low-column-count
rendering, preprocessed graphics, and repeatable timedemo benchmarking.
This is **Doom8088's BSP/sector renderer**, not Wolfenstein's grid-based
raycaster. Its `WL_DR_A.ASM` ray-tracing loop and wall-scaler code cannot
simply be dropped into DOOM. Wolfenstein's composite CGA and monochrome
LCD modes remain separate possible future display targets, not
implemented DOOM features. An emulated 8086 smoke test verifies that the
game terminates but **does not prove smooth gameplay at 7 MHz**.
Use `BENCH.BAT` on the physical Tandy EX to compare renderer speeds.

## Fullscreen Tandy 16-color mode

The Tandy EX's 16-color BIOS mode 08h has an 80-byte video row.
Previous builds centered the engine's 60-byte rows with unused borders.
The native Tandy builds now expand the 120 x 160 logical framebuffer to
160 x 200 at the video-copy stage. The pixels are nearest-neighbor
stretched (not newly rendered), so the fast build keeps the 30-column
projection for 7 MHz systems; the high-detail build uses 60.
All menus, status bar, title screens, and gameplay share the same scaling.
The Tandy 16 RGBI palette registers are initialized to the identity
mapping, avoiding accidental use of the CGA palette call. This does not
create more than 16 physical colors; existing converted EGA art may
still be dithered. We are not yet claiming a hardware-measured FPS for
this enlarged output.

## Automatic video selection and manual overrides

`DOOM.EXE` performs BIOS feature detection without entering a graphics
mode. It checks the VGA/MCGA display-combination code (INT 10h AH=1Ah),
then the Tandy 1000 ROM signature used by Doom8088, otherwise chooses
CGA. `DOOM -detect` reports the result without running the game;
`DOOM -tandy`, `-tandyhi`, `-cga`, and `-vga` override it.
`DOOM -video MODE` is an alternative syntax. Choosing a mode does not
emulate missing hardware; forcing VGA requires a compatible adapter.
The internal `.OVL` files are separate MZ DOS executables loaded via
DOS EXEC so the game can use memory that would otherwise belong to a
resident launcher. All `.OVL` files and WADs must stay alongside
`DOOM.EXE`.

## Native Tandy 1000 PSG sound

DOOM now detects audio hardware **independently from the video
adapter**. The Tandy ROM signature selects the PSG at I/O port
`0xC0`, even if VGA is installed. Other PCs default to the original
single-voice PC speaker. The same DOS executable supports:

| Switch | Sound output |
| --- | --- |
| `DOOM` or `DOOM -sound auto` | Tandy PSG on recognized Tandy 1000s; otherwise PC speaker |
| `DOOM -sound tandy` | Force Tandy 3-tone SN76489-compatible PSG plus noise |
| `DOOM -sound pc` | Force one-voice PC speaker using the old DOS driver |
| `DOOM -nomusic` | Sound effects only |
| `DOOM -nosfx` | Music only (when the Tandy PSG is enabled) |
| `DOOM -nosound` | Disable both music and effects |

The new PSG driver adapts TandyAMP's cached tone/attenuation/noise
register-writing strategy, converting the existing 140 Hz Muse
PC-speaker effect pitch tables to the PSG's 10-bit dividers. It can
play **up to three independent prioritized tone effects** with a
fourth noise channel for impacts, weapons and explosions. Tone and
noise changes are scheduled in the existing 140 Hz task service;
there is no PCM mixer, runtime MIDI parser or additional timer IRQ.

A small **original** repeating 3-part minor-key ambience is enabled
on Tandy unless `-nomusic` is supplied. It yields to sound effects
on every occupied tone voice and resumes when the voice is free.
It is a placeholder demonstration of the PSG music pipeline, **not
a transcription or licensed copy of DOOM's original score**. It uses
no additional music files or WAD data and is automatically disabled
on PC speaker.

Audio detection is based on the Tandy ROM signature, not a probing
write to an unknown I/O port. `-sound tandy` forces port `0xC0`;
use only when that PSG really exists. Sound output and real-world
performance require validation on physical 7 MHz Tandy hardware.


## Tandy title art color correction

The previous Tandy WAD reconstructed four-bit pixels by selecting
alternating nibbles from the upstream **pre-dithered EGA** full-screen
pictures, producing strong colored speckling when enlarged to 160x200.
The converted `DOOMT16.WAD` now retains its EGA gameplay resources and
lump ordering but constructs **TITLEPIC, HELP2, WIMAP0, STBAR, and
FLOOR4_8** from the verified upstream **VGA** shareware WAD instead.
The VGA pictures use direct 256-color palette indices. On the build
machine, neighboring source pixels are averaged in RGB and quantized
to the standard IBM/Tandy 16-color RGBI palette. The result is packed
into two four-bit Tandy pixels per byte. No extra work is done on the
7 MHz EX. Both original release archives are hash verified and
visual-data sizes and lump order are tested.

This change targets the title/intermission/status-bar artwork; the
game's wall/sprite shading still uses the original EGA-derived color
tables. If gameplay colors are also visibly incorrect on a physical
Tandy, those should be validated separately rather than assuming
the offline title-art conversion fixed them.


## Physical Tandy in-game de-dithering

The photographic test from the Tandy 1000 EX showed regular grey
checkerboard ceilings and floors, colorful wall columns and a
heavily dithered status bar in **DOOMTGH**. The title-only update in
build #14 did not change the world/sprite drawing data.

The new offline Tandy WAD conversion also changes the EGA 16-color
**COLORMAP** output values (all lighting levels) and verified DOOM
patch-column samples (including sprites, textures and HUD patches).
Each source dither color pair is averaged in RGB and mapped to the
nearest *single* RGBI color; this nibble is repeated so the game's
120-pixel internal framebuffer has no extra high-frequency
two-color EGA dither pattern. Headers, WAD lump numbers, map data,
post lengths, source dimensions and the original color lookup
indices are preserved. It also corrects the fallback flat sky
constant from `0x07` to `0x77`, because this
renderer interprets the value as **two packed colors**, not a
single 4-bit index. Otherwise the floor/sky filler alternates
the nibbles on successive scanlines and creates checkerboards.

**There is no runtime quantization or extra display processing.**
All of it runs in `tandydos/prepare.py` on the CI build
machine; the EX keeps the existing four-bit packed framebuffer and
140 Hz PSG audio. This intentionally trades some EGA micro-dither
detail for cleaner 160-color-position patterns on the Tandy's
actual 16-color output. The physical photo remains the final test:
DOSBox-X smoke tests verify program execution but cannot judge
CRT color quality.


## Tandy world-texture color pipeline correction

The first de-dithering attempt (DOS Build #15) unintentionally flattened
EGA wall and sprite **source bytes before lookup** and flattened the
`COLORMAP` **output bytes too**. This double conversion can change
the lookup index, producing excessive quantization and incorrect wall
shading even though the status bar and static artwork look cleaner.

The converter now uses the upstream `PNAMES` texture list and
sprite namespace markers to **preserve original source bytes** for all
world wall/sprite/weapon samples. Only the output of `COLORMAP`
and gamma tables is converted to one solid RGBI pixel pair. UI patches
that bypass the lighting lookup still receive their own offline pixel
conversion. The exact WAD lump order, offsets, source dimensions, DOS
overlay format, Tandy mode 08h framebuffer and PSG sound code remain
unchanged. Runtime overhead is zero.

This addresses a definite source-level color indexing inconsistency;
photographs of the physical Tandy are still necessary to judge whether
any other visual problems remain.


## Native Tandy RGBI pipeline (FastDoom-inspired)

FastDoom's EGA/CGA pipeline precomputes a closest-16-color lookup from
the original 256-color palette and uses a packed output nibble pair.
Doom8088, by contrast, ships EGA-dithered **source texture codes** that
can only be used correctly if their original *source* byte stays intact.

During the **build** (not on the XT), `tandydos/prepare.py` now:

1. Identifies wall patch names from `PNAMES` and sprite patch namespaces.
2. Matches their source pixels against the same named **VGA** wall/sprite
   patches by actual (x, y) within their original DOOM patch columns.
3. Collects the VGA palette colors represented by each 8-bit EGA source
   code. When a source value maps to several VGA colors, it uses their
   frequency-weighted average after applying the VGA light-level table.
4. Generates each 34×256 **Tandy RGBI COLORMAP**, and the gamma variants,
   by selecting the closest of 16 hardware colors per shade, packing
   the result as one repeated RGBI nibble. Unmatched values use the
   verified EGA pair-average fallback.
5. Recolors directly drawn HUD/UI patches from matching VGA patch
   coordinates, leaving EGA post headers/geometry unchanged. Incompatible
   or absent VGA patches fall back to de-dithered EGA UI.
6. Preserves the original EGA wall/sprite samples, WAD lump ordering and
   the DOS renderer; no new runtime tables, memory allocations, or
   per-pixel calculations are added on the Tandy.

`RGBI.TXT` in each release records actual source pixel and
patch match counts so that a missing VGA match is visible rather than
silently assumed. For standalone verification, run
`python -m unittest discover -s tandydos/tests -p 'test_*.py'`.
This is a source-aware lighting conversion, **not** a FastDoom 386/486
assembler transplant. Physical RGBI fidelity must be judged on the EX.


## RealDOOM 8086 math and texture-cache adaptation

The [RealDOOM](https://github.com/sqpat/RealDOOM) 16-bit port contains
hand-written 8086 multiply/divide routines and an EMS-backed, tiered
texture-cache working set. Our V20 Tandy EX DOS build already uses
split-word 16-bit products in `FixedMul` and
`FixedMul3216`; RealDOOM's full EMS paging and
self-modifying renderer cannot be dropped into a 640 KB non-EMS Tandy.

The **Tandy-only** `TANDY_XT_MATH_CACHE` build switch adds a
precise fast path when a 16.16 operand is an integer, and returns
immediately for zero-numerator reciprocal division. These cases
avoid redundant word multiplication/division while preserving the
existing fixed-point results. No new assembly is enabled.

The working-set cache continues using its **existing 128 resident
128-byte column slots = 16 KiB**. Borrowing RealDOOM's explicit
validity principle, a 16-byte tag bitmap now distinguishes empty
slots from a legitimate texture 0 / column 0, and partially covered
composite columns start with a cleared 128-byte scratch buffer.
Bounds checks prevent oversized composite columns from spilling
into adjacent slots. The tag bits and scratch clear affect only
Tandy builds; CGA/VGA remain as regression controls.

The emulator's 96-tic demo validates launch and gameplay, not
absolute V20 performance. For hardware numbers compare `BENCH.BAT`
on the physical EX. Any faster 8086 assembly or EMS paging is
deferred until the existing C baseline is stable, because earlier
experimental assembly paths timed out in DOSBox-X.


## Stable Tandy world graphics: retain the successful HUD, reset world shading

Physical Tandy 1000 EX screenshots of Builds #15–18 showed that
aggressive off-line reinterpretation of source world color codes made
walls into large orange/gray blocks. The newest release defaults to
**bit-for-bit original Doom8088 EGA world `COLORMAP` and
gamma table bytes**, while retaining our improved VGA-derived title,
help, intermission, status-bar pictures, and individual HUD/UI patches.
Wall and sprite patch source data also stay unchanged. The engine,
native 16-color video output, PSG sound, automatic launcher, and
Tandy-only 8086 math/cache changes remain intact.

The earlier reconstructed VGA RGBI world-colormap algorithm is retained
only as an opt-in **developer** function
`pack_tandy(..., reconstruct_world=True)`; it is not enabled
by the normal build or included as an alternate default WAD.
This gives a clean baseline and prevents reintroducing collapsed
texture shading while independently improving UI art.

The original world tables can still look dithered on a real Tandy;
this change is about **restoring recognizable textures**, not claiming
the final perfect RGBI graphics pipeline. Our future work will need
a different, more contrast-preserving world LUT and physical CRT
A/B testing before replacing this baseline.


## Tandy Clean: optional original-art wall experiment

Classic mode (`DOOM -tandyhi -textures classic`) retains the Build #20 world textures and original EGA lighting tables. **Clean** mode (`DOOM -tandyhi -textures clean`) loads the separate `DOOMTC.WAD`. This offline-only experiment picks five common wall-texture families through `TEXTURE1` and `PNAMES` and suppresses isolated pixels surrounded by at least three matching neighbors, keeping prominent edges and all existing color codes/lighting. Actual texture/patch names and changed-pixel counts are in `CLEAN.TXT`. It does not contain any Wolfenstein art. Both modes use the same improved title/HUD, fullscreen display and PSG. **Classic is always the default**, and neither mode needs more runtime memory or CPU work.
