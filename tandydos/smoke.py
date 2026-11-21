"""Run the complete shareware demo on all three emulated DOS adapters."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

TESTS = (("DOOMTGA", "tandy"), ("DOOMTGH", "tandy"),
         ("DOOMCGA", "cga"), ("DOOMVGA", "vgaonly"))


def run_demo(emulator, game, program, machine, quick=True):
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
{program} -timedemo demo3 {options} -noems -noxms > D:\\DEMO.LOG
if not errorlevel 1 echo OK>D:\\PASS.TXT
exit
""", encoding="ascii")
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        subprocess.run([str(emulator), "-fastlaunch", "-nomenu", "-conf", str(config)],
                       cwd=temp, env=env, check=True, timeout=90)
        log = (temp / "DEMO.LOG").read_text(encoding="cp437", errors="replace")
        print(f"{program}, DOSBox-X fixed {cycles}\n{log}", flush=True)
        match = re.search(r"Timed (\d+) gametics in (\d+) realtics = [\d.]+ frames per second", log)
        expected = 96 if quick else 2134
        if not (temp / "PASS.TXT").exists() or not match or int(match[1]) != expected or int(match[2]) < 1:
            raise RuntimeError(program + " did not finish the recorded game in DOS")
        return int(match[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulator", required=True, type=Path)
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--full", action="store_true",
                        help="Run the entire 2134-tic demo instead of the 96-tic smoke test")
    args = parser.parse_args()
    counts = [run_demo(args.emulator.resolve(), args.game.resolve(), program, machine,
                       quick=not args.full)
              for program, machine in TESTS]
    if len(set(counts)) != 1:
        raise SystemExit(f"Gameplay tic count differed by adapter: {counts}")
