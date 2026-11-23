"""Test automatic/forced DOS video and sound using 96 game tics per mode."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

# Exercise the one user-facing EXE in auto and explicit modes.
TESTS = (
    # machine, command-line video/sound overrides, expected video, expected audio
    ("tandy", "-auto", "Tandy 16-color (fast) (auto)", "Tandy PSG"),
    ("vgaonly", "-auto", "VGA 256-color (auto)", "PC speaker"),
    ("cga", "-auto", "CGA 4-color (auto)", "PC speaker"),
    ("tandy", "-tandy", "Tandy 16-color (fast) (forced)", "Tandy PSG"),
    ("tandy", "-tandyhi", "Tandy 16-color (detail) (forced)", "Tandy PSG"),
    ("tandy", "-tandyhi -textures clean", "Tandy 16-color (detail) (forced)", "Tandy PSG"),
    ("tandy", "-tandy -textures clean", "Tandy 16-color (fast) (forced)", "Tandy PSG"),
    ("cga", "-cga", "CGA 4-color (forced)", "PC speaker"),
    ("vgaonly", "-vga", "VGA 256-color (forced)", "PC speaker"),
    # Audio must be independent of video and overridable on a Tandy.
    ("tandy", "-tandy -sound tandy", "Tandy 16-color (fast) (forced)", "Tandy PSG"),
    ("tandy", "-tandy -sound pc", "Tandy 16-color (fast) (forced)", "PC speaker"),
    ("tandy", "-tandy -nomusic", "Tandy 16-color (fast) (forced)", "effects only"),
    ("tandy", "-tandy -nosfx", "Tandy 16-color (fast) (forced)", "Tandy PSG"),
    ("tandy", "-tandy -nosound", "Tandy 16-color (fast) (forced)", "sound disabled"),
    ("vgaonly", "-vga -sound pc", "VGA 256-color (forced)", "PC speaker"),
)


def run_demo(emulator, game, machine, switch, selected, audio, quick=True):
    # Keep CI bounded. Real 7 MHz timings must be tested on actual hardware.
    cycles = 50000
    options = "-quick" if quick else ""
    # Keep the guest mount writable for DOS redirection and isolated per run.
    with tempfile.TemporaryDirectory(prefix="doom-test-") as suffix:
        temp = Path(suffix)
        config = temp / "test.conf"
        config.write_text(f"""[sdl]
showmenu=false
autolock=false
output=surface
[dosbox]
machine={machine}
memsize=1
[cpu]
core=normal
cputype=8086
cycles=fixed {cycles}
[dos]
xms=false
ems=false
umb=false
[mixer]
nosound=true
[autoexec]
mount c "{game}"
mount d "{temp}"
c:
DOOM {switch} -timedemo demo3 {options} -noems -noxms > D:\\DEMO.LOG
if not errorlevel 1 echo OK>D:\\PASS.TXT
exit
""", encoding="ascii")
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        try:
            subprocess.run([str(emulator), "-fastlaunch", "-nomenu", "-conf", str(config)],
                           cwd=temp, env=env, check=True, timeout=90)
        except subprocess.TimeoutExpired as error:
            output = temp / "DEMO.LOG"
            if output.exists():
                print(f"{switch} partial DOS log:\n" +
                      output.read_text(encoding="cp437", errors="replace"), flush=True)
            raise RuntimeError(f"{switch} timed out during DOS timedemo") from error
        log = (temp / "DEMO.LOG").read_text(encoding="cp437", errors="replace")
        print(f"{switch}, DOSBox-X fixed {cycles}\n{log}", flush=True)
        match = re.search(r"Timed (\d+) gametics in (\d+) realtics = [\d.]+ frames per second", log)
        expected = 96 if quick else 2134
        if (not (temp / "PASS.TXT").exists() or not match or
                int(match[1]) != expected or int(match[2]) < 1 or
                "Video: " + selected not in log or audio not in log):
            raise RuntimeError(switch + " did not finish the recorded game in DOS")
        return int(match[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulator", required=True, type=Path)
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--full", action="store_true",
                        help="Run the entire 2134-tic demo instead of the 96-tic smoke test")
    args = parser.parse_args()
    counts = [run_demo(args.emulator.resolve(), args.game.resolve(),
                       machine, switch, selected, audio, quick=not args.full)
              for machine, switch, selected, audio in TESTS]
    if len(set(counts)) != 1:
        raise SystemExit(f"Gameplay tic count differed by adapter: {counts}")
