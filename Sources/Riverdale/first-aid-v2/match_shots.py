"""In-game shots of the cabinet's scan-based finish and the kept code-painted one, from a short Riverdale match in the editor: python match_shots.py <project root> <out dir> <scratch dir>

Starts play if it isn't running, starts a deathmatch on Riverdale with dev_mode, takes each shot with the HUD and gun as the player sees it, and stops play again if it started it.
Nothing is saved: the code-painted finish and the comparison copy only exist in the running match. Files come out as <shot>.png.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
ROOT, OUT, SCRATCH = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
PAIR_GAP = 34.0
# name: feet x, y, the point looked at, mode. The east wall is at y 1000, its cabinet at x 985; +x is to your right as you face it. The gun fills the lower right, so the cabinets sit above centre.
SHOTS = [
    ("pair", (1002, 932), (1002, 1000, 50), "pair"),
    ("pair_angle", (1062, 925), (1000, 1000, 52), "pair"),
    ("close_scanned", (985, 958), (985, 1000, 54), "scanned"),
    ("close_painted", (985, 958), (985, 1000, 54), "painted"),
    ("walkup_scanned", (1060, 880), (985, 1000, 58), "scanned"),
    ("walkup_painted", (1060, 880), (985, 1000, 58), "painted"),
]
os.makedirs(OUT, exist_ok=True)


def call(tool, timeout=170, **args):
    r = subprocess.run([CLI, "--call", tool, json.dumps(args)], capture_output=True, text=True, cwd=ROOT, timeout=timeout, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def playing():
    code, out, _ = call("is_playing", timeout=60)
    return code == 0 and '"isPlaying": true' in out


def snippet(text):
    path = os.path.join(SCRATCH, "fa_match_run.cs.txt")
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    return call("run_csharp", path=path.replace("\\", "/"))


started_here = False
if not playing():
    print("start_play", call("start_play", timeout=600)[1][:200], flush=True)
    started_here = True
    for _ in range(120):
        if playing():
            break
        time.sleep(5)
    else:
        raise SystemExit("Play didn't start.")

state = 'return new { Scene = Game.ActiveScene?.Name, Pawn = Facepunch.Client.Local?.PlayerPawn.IsValid() ?? false };'
code, out, err = snippet(state)
print("state", out[:200], flush=True)
if '"Scene": "riverdale"' not in out:
    print("dev_mode", call("console_run", command="dev_mode deathmatch riverdale")[1][:160], flush=True)
for _ in range(90):
    time.sleep(4)
    code, out, err = snippet(state)
    if '"Scene": "riverdale"' in out and '"Pawn": true' in out:
        break
else:
    raise SystemExit(f"Riverdale's match didn't come up: {out} {err}")
print("in the match", out[:200], flush=True)
time.sleep(6)

template = open(os.path.join(HERE, "match_view.cs.txt"), encoding="utf-8").read()
try:
    for name, (ex, ey), (tx, ty, tz), mode in SHOTS:
        text = template.replace('"MODE"', f'"{mode}"').replace("PAIR_GAP", f"{PAIR_GAP}f")
        for key, value in (("EYE_X", ex), ("EYE_Y", ey), ("TARGET_X", tx), ("TARGET_Y", ty), ("TARGET_Z", tz)):
            text = text.replace(key, f"{float(value)}f")
        code, out, err = snippet(text)
        print(name, mode, code, re.sub(r"\s+", " ", out if code == 0 else err)[:300], flush=True)
        if code != 0 or "No player" in out:
            raise SystemExit(1)
        code, out, err = call("take_screenshot", width=1920, height=1080, renderUI=True)
        found = re.findall(r"[A-Za-z]:[\\/][^\s\"']+\.png", out + "\n" + err)
        if not found:
            raise SystemExit(f"No screenshot: {out[:200]} {err[:200]}")
        shutil.copyfile(found[-1], os.path.join(OUT, name + ".png"))
        print("  saved", name, flush=True)
finally:
    # The match's paint goes back as it was installed, and play stops if this started it.
    snippet(template.replace('"MODE"', '"scanned"').replace("PAIR_GAP", "0f").replace("EYE_X", "1002f").replace("EYE_Y", "932f").replace("TARGET_X", "1002f").replace("TARGET_Y", "1000f").replace("TARGET_Z", "50f").replace("await Task.Delay(6000, cancellationToken);", ""))
    if started_here:
        print("stop_play", call("stop_play", timeout=300)[1][:160], flush=True)
print("match shots done", flush=True)
