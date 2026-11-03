"""The new pallets beside the old slabs, in s&box: python compare.py [folder] [shot names]. Nothing is saved or changed.

map_kit's plan (e, n, z) is engine (n, -e, z), and a plan heading along e is an engine yaw of 90. The old slabs lie at e -285..-111,
n -712..-663 against container 02. For this look only, the new ones stand just south of them: two singles and a stack of two.
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-cargo")
HEIGHT = 4.75


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


def shot(name, eye, target, fov=60):
    return f'("{name}", {P(*eye)}, {P(*target)}, {fov}f)'


PALLETS = [((-255, -745, 0), 92.0), ((-197, -748, 0), 269.0), ((-196, -747, HEIGHT), 94.5), ((-138, -742, 0), 276.0)]
SHOTS = {
    "pair": shot("pair", (-110, -930, 66), (-200, -712, 4), 52),
    "pair_wide": shot("pair_wide", (60, -1060, 120), (-190, -705, 10), 50),
    "new_close": shot("new_close", (-205, -835, 42), (-197, -745, 4), 50),
    "new_corner": shot("new_corner", (-100, -805, 22), (-140, -742, 3), 55),
    "new_top": shot("new_top", (-215, -800, 78), (-205, -742, 2), 52),
    "old_close": shot("old_close", (-205, -790, 40), (-198, -688, 4), 50),
    "far_12m": shot("far_12m", (-200, -1210, 70), (-200, -720, 10), 40),
}

args = sys.argv[1:]
folder = args.pop(0) if args and args[0] not in SHOTS else "pass1"
names = args or list(SHOTS)
out = f"output/asset-improvement-20261030/spillway-cargo/{folder}"
template = open(os.path.join(HERE, "compare.cs.txt"), encoding="utf-8").read()
code = template.replace("%OUT%", out).replace("%SHOTS%", ", ".join(SHOTS[n] for n in names))
code = code.replace("%PALLETS%", ", ".join(f"({P(*at)}, {yaw}f)" for at, yaw in PALLETS))
path = os.path.join(SCRATCH, "compare_run.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
started = time.time()
print(call("run_csharp", {"path": path}, 175)[:900].strip(), f"{time.time() - started:.0f}s", flush=True)
