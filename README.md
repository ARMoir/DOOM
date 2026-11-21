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

The port links the argument parser and deterministic random number generator directly from [id Software's Linux DOOM 1.10](linuxdoom-1.10). The segmented engine, Episode 1 game logic and low-detail renderers come from [Frenkel Smeijers' Doom8088](https://github.com/FrenkelS/Doom8088/tree/b3073a2eb2811cd14caba6549694fc3bfcd6dd29), through GBADoom and PrBoom. The Tandy backend follows [WolfensteinCGA](https://github.com/jhhoward/WolfensteinCGA) in selecting BIOS mode 08h and blitting packed scanlines to the two banks at B800h. DOOMTGA and DOOMCGA project 30 columns and shade two rows per texture sample. DOOMTGH projects 60 columns at full vertical detail. Both Tandy builds keep a 9,600-byte packed buffer, then stretch each 120-pixel RGBI row to 160 pixels and each 160-row frame to 200 rows as they copy it to the Tandy mode 08h interleaved video banks. This fills the physical CRT at the cost of extra copy work; the 3D renderer still processes only 30 or 60 columns. Each of the 16 palette registers is explicitly set to its canonical 4-bit RGBI value with Tandy BIOS INT 10h AX=1000h; damage/bonus border effects use AX=1001h without reducing in-game color depth. Experimental 8086 blit/texture-scaler assembly is retained in the source but disabled because it has not passed the 8086 smoke test. Run `BENCH.BAT` on your EX to compare the same 96 game tics in both native modes. The slower CI comparison uses DOSBox-X at 400 fixed cycles per millisecond. That setting measures relative speed and has no precise MHz equivalence. The desktop converter prepares the title, status bar, intermission and finale pictures before they reach the XT. Source notices are retained in [tandydos/engine](tandydos/engine).

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
