"""Build 16-bit real-mode executables with Open Watcom v2 on Windows or Linux."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

PORT = Path(__file__).resolve().parent
ENGINE = PORT / "engine"
MODES = {
    "tandy": ("DOOMTGA", "i_vcga", ["VIDEO_MODE_TANDY", "NR_OF_COLORS=16", "VIEWWINDOWWIDTH=30",
                                     "FLAT_NUKAGE1_COLOR=32", "FLAT_SKY_COLOR=7"]),
    "tandy-full": ("DOOMTGH", "i_vcga", ["VIDEO_MODE_TANDY", "NR_OF_COLORS=16",
                                          "FLAT_NUKAGE1_COLOR=32", "FLAT_SKY_COLOR=7"]),
    "cga": ("DOOMCGA", "i_vcga", ["VIDEO_MODE_CGA", "NR_OF_COLORS=4", "VIEWWINDOWWIDTH=30",
                                   "FLAT_NUKAGE1_COLOR=65", "FLAT_SKY_COLOR=3"]),
    "vga": ("DOOMVGA", "i_vvga13", []),
}


def build_launcher(watcom, output):
    """Create the one public DOS executable that selects the overlays."""
    env = os.environ.copy()
    env["WATCOM"] = str(watcom)
    host_dirs = [watcom / p for p in ("binnt64", "binnt")] if os.name == "nt" else [
        watcom / p for p in ("binl64", "binl")]
    env["PATH"] = os.pathsep.join([*(str(p) for p in host_dirs), env["PATH"]])
    env["INCLUDE"] = str(watcom / "h")
    cc = shutil.which("wcc", path=env["PATH"])
    linker = shutil.which("wlink", path=env["PATH"])
    if not cc or not linker:
        raise SystemExit("Open Watcom v2 missing")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="doomselect-") as scratch:
        subprocess.run([cc, "-bt=dos", "-0", "-ms", "-zp1", "-j", "-s", "-ox",
                        "-os", "-za99", "-zq", "-fo=selector.obj",
                        str(PORT / "selector.c")],
                       cwd=scratch, env=env, check=True)
        script = ["format dos", "option quiet", "option stack=2048",
                  "name DOOM.EXE",
                  "libpath '" + str(watcom / "lib286") + "'",
                  "libpath '" + str(watcom / "lib286" / "dos") + "'",
                  "library noemu87", "file selector.obj"]
        Path(scratch, "link.lnk").write_text("\n".join(script) + "\n",
                                              encoding="ascii")
        subprocess.run([linker, "@link.lnk"], cwd=scratch, env=env, check=True)
        shutil.copyfile(Path(scratch, "DOOM.EXE"), output / "DOOM.EXE")
    print("Built", output / "DOOM.EXE", flush=True)


def build(mode, watcom, output):
    name, driver, defines = MODES[mode]
    env = os.environ.copy()
    env["WATCOM"] = str(watcom)
    host_dirs = [watcom / p for p in ("binnt64", "binnt")] if os.name == "nt" else [
        watcom / p for p in ("binl64", "binl")]
    env["PATH"] = os.pathsep.join([*(str(p) for p in host_dirs), env["PATH"]])
    env["INCLUDE"] = str(watcom / "h")
    cc = shutil.which("wcc", path=env["PATH"])
    linker = shutil.which("wlink", path=env["PATH"])
    if not cc or not linker:
        raise SystemExit("Set WATCOM to the Open Watcom v2 installation directory.")

    # Keep display-specific objects apart. They have different colors and WADs.
    sources = sorted(p for p in ENGINE.glob("*.c") if not p.name.startswith("i_v"))
    sources += [ENGINE / (driver + ".c"), PORT.parent / "linuxdoom-1.10" / "m_argv.c",
                PORT.parent / "linuxdoom-1.10" / "m_random.c"]
    flags = ["-bt=dos", "-0", "-mm", "-zp1", "-j", "-s", "-ox", "-os", "-za99",
             "-zq", "-dC_ONLY", "-dFLAT_SPAN", "-dstrcasecmp=stricmp",
             *("-d" + value for value in defines)]
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="doomxt-") as scratch:
        for source in sources:
            subprocess.run([cc, *flags, "-fo=" + source.stem + ".obj", str(source)],
                           cwd=scratch, env=env, check=True)
        script = ["format dos", "option quiet", "option stack=4096", "name " + name + ".EXE",
                  "libpath '" + str(watcom / "lib286") + "'",
                  "libpath '" + str(watcom / "lib286" / "dos") + "'", "library noemu87"]
        script += ["file " + source.stem + ".obj" for source in sources]
        Path(scratch, "link.lnk").write_text("\n".join(script) + "\n", encoding="ascii")
        subprocess.run([linker, "@link.lnk"], cwd=scratch, env=env, check=True)
        shutil.copyfile(Path(scratch, name + ".EXE"), output / (name + ".EXE"))
    print("Built", output / (name + ".EXE"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modes", nargs="*", metavar="MODE", help=", ".join(MODES))
    parser.add_argument("--watcom", default=os.getenv("WATCOM"))
    parser.add_argument("--out", type=Path, default=PORT / "bin")
    args = parser.parse_args()
    if not args.watcom:
        parser.error("set WATCOM or use --watcom PATH")
    for selected in args.modes or MODES:
        if selected not in MODES:
            parser.error("unknown mode " + selected)
        build(selected, Path(args.watcom).resolve(), args.out.resolve())
    build_launcher(Path(args.watcom).resolve(), args.out.resolve())
