# DOOM for the Tandy 1000 EX

This fork builds single-player DOOM Episode 1 for real-mode DOS on an 8088, 8086 or NEC V20. Start with the CGA build on a Tandy 1000 EX with expanded conventional RAM. The VGA build uses BIOS mode 13h and requires a VGA-compatible adapter. Both include the automap, monsters, weapons and PC speaker sound effects.

| DOS program | Video output | Required game data |
| --- | --- | --- |
| `DOOMCGA.EXE` | CGA 320×200, four colors. F5 cycles palettes. | `DOOM4.WAD` |
| `DOOMVGA.EXE` | VGA 320×200, 256 colors. | `DOOM1.WAD` |

Copy an executable from [tandydos/bin](tandydos/bin) and the matching **preprocessed** WAD into the same DOS directory. Get the WAD from the corresponding [Doom8088 CGA or VGA release archive](https://github.com/FrenkelS/Doom8088/releases/tag/v20260304). A stock DOOM shareware IWAD has a different internal layout.

Run `DOOMCGA` or `DOOMVGA`. Use the arrows to move, Ctrl to fire, Space to open doors, Tab for the automap, and F10 to return to DOS. For a repeatable measurement, run `DOOMCGA -timedemo demo3`. The benchmark prints its frame rate at the DOS prompt. Episode 1 uses flat floors and ceilings. Savegames, music, multiplayer and later episodes are outside this build.

## Building

Install Open Watcom v2 and Python 3 on a modern host. Set `WATCOM` to the compiler installation directory and run `python tandydos/build.py` from the repository root. It builds DOS MZ executables with the medium memory model and 8086 instruction set. Each target has its own compile and link directory.

The port links the argument parser and deterministic random number generator directly from [id Software's Linux DOOM 1.10](linuxdoom-1.10). The segmented engine, Episode 1 game logic and low-detail renderers come from [Frenkel Smeijers' Doom8088](https://github.com/FrenkelS/Doom8088/tree/b3073a2eb2811cd14caba6549694fc3bfcd6dd29), through GBADoom and PrBoom. [WolfensteinCGA](https://github.com/jhhoward/WolfensteinCGA) is the reference for the Tandy display layout and offline color preparation. Source notices are retained in [tandydos/engine](tandydos/engine).
