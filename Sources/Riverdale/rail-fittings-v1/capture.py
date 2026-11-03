"""Shoot the fuel pool's rail in s&box from a small hidden scene: python capture.py <folder name> [compile] [spillway]. Nothing is saved.

The hall's own models, the map's lights and look, and no backdrop, so a running match is disturbed as little as can be.
Plan (e, n, z) is engine (n, -e, z). The pool's rail is a 48-sided ring of radius 530 at z 3, 42 tall, with a post at each corner and half way along each side.
"""
import json
import math
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "Tools"))
folder = sys.argv[1]
OUT = f"output/asset-improvement-20261030/rail-fittings/{folder}"
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "rail-fittings")
MODELS = ["Reactor Hall", "Reactor Hall Dressing", "Reactor Hall Detail", "Reactor Hall Fine", "Fuel Pool", "Pool Water", "Glass"]
POOL = None
for line in open(os.path.join(ROOT, "Tools", "riverdale_hall.py"), encoding="utf-8"):
    if line.startswith("POOL ="):
        POOL = eval(line.split("=", 1)[1].split("#")[0].strip())
        break


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


def world(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


def on_ring(angle, radius, z):
    a = math.radians(angle)
    return (POOL[0] + math.cos(a) * radius, POOL[1] + math.sin(a) * radius, z)


# Each corner of the ring is at a multiple of 7.5 degrees. The post's top rail is 45 up.
HEIGHT = 45.0
ANGLE = 247.5
post = on_ring(ANGLE, 530, HEIGHT)
SHOTS = [
    ("close", on_ring(ANGLE - 1.2, 545, HEIGHT + 8), post, 40),
    ("closer", on_ring(ANGLE - 0.5, 538, HEIGHT + 3), post, 40),
    ("from_inside", on_ring(ANGLE + 1.3, 512, HEIGHT + 8), post, 40),
    ("run", on_ring(ANGLE - 8, 560, HEIGHT + 26), on_ring(ANGLE + 3, 530, HEIGHT - 8), 55),
    ("low", on_ring(ANGLE - 1.0, 540, HEIGHT - 12), post, 45),
    # A right-angled corner, where the bent rail misses the post: a cap and no collar. On the upper landing, at z 288.
    ("corner", (-540, 556, 288 + 54), (-560, 580, 288 + 40), 45),
]

if "compile" in sys.argv:
    for rel in sys.argv[sys.argv.index("compile") + 1 :]:
        started = time.time()
        out = call("asset_compile", {"path": rel}, 175)
        print(("ok " if '"Success": true' in out else "NO ") + f"{time.time() - started:5.1f}s {rel}", out[:160].replace("\n", " ") if '"Success": true' not in out else "", flush=True)

template = open(os.path.join(HERE, "capture_engine.cs.txt"), encoding="utf-8").read()
code = template.replace("%OUT%", OUT).replace("%MODELS%", ", ".join(f'"{m}"' for m in MODELS))
code = code.replace("%SHOTS%", ", ".join(f'("{n}", {world(*a)}, {world(*b)}, {f}f)' for n, a, b, f in SHOTS))
path = os.path.join(SCRATCH, "capture_run.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
started = time.time()
print(call("run_csharp", {"path": path}, 175)[:600].strip(), f"{time.time() - started:.0f}s", flush=True)
