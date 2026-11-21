# DOOM for the Tandy 1000 EX

This fork builds single-player DOOM Episode 1 for real-mode DOS on an 8088, 8086 or NEC V20. On a Tandy 1000 EX with 640 KB installed, start with `DOOMTGA` for native 16-color graphics. The game includes monsters, weapons, the automap and PC speaker effects.

Download the newest **DOOM-DOS.zip** from [GitHub Releases](https://github.com/ARMoir/DOOM/releases/latest), unzip it to a single directory on the CompactFlash card, and run the program for your adapter. Each push to `master` compiles all four executables from source, runs a **96-tic smoke test** in DOSBox-X for each adapter, and publishes a new downloadable DOS release. Only after the new ZIP is confirmed does the workflow delete older releases and obsolete DOOM-DOS Actions artifacts. For the longer emulator check, use `python tandydos/smoke.py --emulator PATH --game DIRECTORY --full`.

| DOS program | Video output | Required game data |
| --- | --- | --- |
| `DOOMTGA.EXE` | Tandy BIOS mode 08h, 160×200, 16 RGBI colors. | `DOOMT16.WAD` |
| `DOOMTGH.EXE` | Same Tandy mode, 60-column higher-detail view. | `DOOMT16.WAD` |
| `DOOMCGA.EXE` | CGA 320×200, four colors. F5 cycles palettes. | `DOOM4.WAD` |
| `DOOMVGA.EXE` | VGA 320×200, 256 colors. | `DOOM1.WAD` |

To prepare the same folder on a modern PC with Python 3, run `python tandydos/prepare.py --out DOOMDOS` from a checkout. To prepare only the EX version, add `--mode tandy`. The script copies the [prebuilt executables](tandydos/bin), verifies the [upstream shareware archives](https://github.com/FrenkelS/Doom8088/releases/tag/v20260304), and packs the native Tandy artwork. With existing release ZIPs, pass `--archives DIRECTORY`.

Use the arrows to move, Ctrl to fire, Space to open doors, Tab for the automap, and F10 to return to DOS. To measure your EX, run `DOOMTGA -timedemo demo3` and compare with `DOOMCGA -timedemo demo3`. The benchmark prints its frame rate at the DOS prompt. Episode 1 uses flat floors and ceilings. The port omits savegames, music, multiplayer and later episodes.

## Building

Install Open Watcom v2 and Python 3 on a modern host. Set `WATCOM` to the compiler installation directory and run `python tandydos/build.py` from the repository root. It builds DOS MZ executables with the medium memory model and 8086 instruction set. Each target has its own compile and link directory.

The port links the argument parser and deterministic random number generator directly from [id Software's Linux DOOM 1.10](linuxdoom-1.10). The segmented engine, Episode 1 game logic and low-detail renderers come from [Frenkel Smeijers' Doom8088](https://github.com/FrenkelS/Doom8088/tree/b3073a2eb2811cd14caba6549694fc3bfcd6dd29), through GBADoom and PrBoom. The Tandy backend follows [WolfensteinCGA](https://github.com/jhhoward/WolfensteinCGA) in selecting BIOS mode 08h and blitting packed scanlines to the two banks at B800h. DOOMTGA and DOOMCGA project 30 columns and shade two rows per texture sample. DOOMTGH projects 60 columns at full vertical detail. Both Tandy builds keep a 9,600-byte packed buffer and copy it to the interleaved display banks with an 8086 word-copy loop. Run `BENCH.BAT` on your EX to compare the same 96 game tics in both native modes. The slower CI comparison uses DOSBox-X at 400 fixed cycles per millisecond. That setting measures relative speed and has no precise MHz equivalence. The desktop converter prepares the title, status bar, intermission and finale pictures before they reach the XT. Source notices are retained in [tandydos/engine](tandydos/engine).

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
