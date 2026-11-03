"""Matched in-game before and after shots in a Belltower match already running in the editor: python match_shots.py <project root> <out dir> <scratch dir> <before,after> [shot names]

Needs preview_model.py's model compiled. Files come out as <shot>-<mode>.png. The match is left showing the last mode shot.
"""
import json
import os
import re
import shutil
import subprocess
import sys

CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
ROOT, OUT, SCRATCH, MODES = sys.argv[1:5]
WANTED = sys.argv[5:]
HERE = os.path.dirname(os.path.abspath(__file__))
TOPS = {"low": 26.0, "shouldered": 29.0, "arched": 32.0}
# name: feet x, y, then the point looked at. The gun fills the lower right, so the stones are framed left of centre.
SHOTS = {
    "yard": (-430, 440, -530, 530, 16),
    "crosses": (-405, 575, -470, 612, 22),
    "arched": (-400, 540, -466, 558, 20),
    "shouldered": (-398, 338, -468, 354, 20),
    "row": (-498, 400, -555, 300, 15),
    "across": (-830, 300, -560, 235, 14),
}
os.makedirs(OUT, exist_ok=True)
template = open(os.path.join(HERE, "match_view.cs.txt"), encoding="utf-8").read()
stones = json.load(open(os.path.join(ROOT, "output/asset-improvement-20261030/headstone/old_stones.json")))
lines = []
for s in stones:
    kind = "cross" if s["kind"] == "cross" else min(TOPS, key=lambda k: abs(TOPS[k] - s["height"]))
    lines.append(f'    ("{kind}", new({s["x"]:.3f}f, {s["y"]:.3f}f, 0f), {s["yaw"]:.3f}f),')
template = template.replace("STONES", "\n".join(lines))


def call(tool, **args):
    r = subprocess.run([CLI, "--call", tool, json.dumps(args)], capture_output=True, text=True, cwd=ROOT, timeout=170, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def view(name, mode):
    ex, ey, tx, ty, tz = SHOTS[name]
    text = template.replace('"MODE"', f'"{mode}"')
    for key, value in (("EYE_X", ex), ("EYE_Y", ey), ("TARGET_X", tx), ("TARGET_Y", ty), ("TARGET_Z", tz)):
        text = text.replace(key, f"{float(value)}f")
    script = os.path.join(SCRATCH, "match_view_run.cs.txt")
    open(script, "w", encoding="utf-8", newline="\n").write(text)
    return call("run_csharp", path=script.replace("\\", "/"))


for name in SHOTS:
    if WANTED and name not in WANTED:
        continue
    for mode in MODES.split(","):
        code, out, err = view(name, mode)
        print(name, mode, code, re.sub(r"\s+", " ", out if code == 0 else err)[:330], flush=True)
        if code != 0:
            sys.exit(1)
        code, out, err = call("take_screenshot", width=1920, height=1080, renderUI=True)
        found = re.findall(r"[A-Za-z]:[\\/][^\s\"']+\.png", out + "\n" + err)
        if found:
            shutil.copyfile(found[-1], os.path.join(OUT, f"{name}-{mode}.png"))
        else:
            print(" no shot", out[:200], err[:200], flush=True)
print("done", flush=True)
