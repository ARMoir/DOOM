"""Run the complete shareware demo on all three emulated DOS adapters."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

TESTS = (("DOOMTGA", "tandy"), ("DOOMCGA", "cga"), ("DOOMVGA", "vgaonly"))


def run_demo(emulator, game, program, machine):
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
cycles=fixed 50000
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
{program} -timedemo demo3 -noems -noxms > D:\\DEMO.LOG
if not errorlevel 1 echo OK>D:\\PASS.TXT
exit
""", encoding="ascii")
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        subprocess.run([str(emulator), "-fastlaunch", "-nomenu", "-conf", str(config)],
                       cwd=temp, env=env, check=True, timeout=240)
        log = (temp / "DEMO.LOG").read_text(encoding="cp437", errors="replace")
        print(program + "\n" + log, flush=True)
        match = re.search(r"Timed (\d+) gametics in (\d+) realtics = [\d.]+ frames per second", log)
        if not (temp / "PASS.TXT").exists() or not match or int(match[1]) < 1000 or int(match[2]) < 1:
            raise RuntimeError(program + " did not finish the recorded game in DOS")
        return int(match[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulator", required=True, type=Path)
    parser.add_argument("--game", required=True, type=Path)
    args = parser.parse_args()
    counts = [run_demo(args.emulator.resolve(), args.game.resolve(), program, machine)
              for program, machine in TESTS]
    if len(set(counts)) != 1:
        raise SystemExit(f"Gameplay tic count differed by adapter: {counts}")
