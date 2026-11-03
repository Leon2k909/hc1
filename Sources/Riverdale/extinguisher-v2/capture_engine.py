"""Matched before and after of Riverdale's extinguishers, drawn by s&box in an isolated scene: python capture_engine.py <project root> <scratch dir> <prepare|shoot>

prepare makes temporary copies of the hall's two models from the before-install OBJs, under Assets/models/compare_old/riverdale-extinguisher/, and compiles them.
shoot draws both and makes the sheet. Neither touches the map's files, open tabs or a running match.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT, SCRATCH, STAGE = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
A = os.path.join(ROOT, "Assets")
WORK_REL = "output/asset-improvement-20261030/riverdale-extinguisher"
WORK = os.path.join(ROOT, WORK_REL)
TEMP_REL = "models/compare_old/riverdale-extinguisher"
TEMP = os.path.join(A, TEMP_REL)
NAMES = ("riverdale_hall_detail", "riverdale_hall_fine")
places = json.load(open(os.path.join(WORK, "placements.json")))


def call(tool, **args):
    r = subprocess.run([CLI, "--call", tool, json.dumps(args)], capture_output=True, text=True, cwd=ROOT, timeout=175, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


if STAGE == "prepare":
    os.makedirs(TEMP, exist_ok=True)
    for name in NAMES:
        shutil.copyfile(os.path.join(WORK, "before-install", name + ".obj"), os.path.join(TEMP, name + ".obj"))
        shutil.copyfile(os.path.join(A, "models/maps/riverdale", name + ".mtl"), os.path.join(TEMP, name + ".mtl"))
        text = open(os.path.join(A, "models/maps/riverdale", name + ".vmdl"), encoding="utf-8").read()
        # Whatever OBJ the model names now: other installs repoint them.
        text, count = re.subn(r'filename = "[^"]+\.obj"', f'filename = "{TEMP_REL}/{name}.obj"', text)
        if count != 1:
            sys.exit(f"{name}.vmdl doesn't name its OBJ once.")
        open(os.path.join(TEMP, name + "_before.vmdl"), "w", encoding="utf-8", newline="\n").write(text)
        print(name, call("asset_compile", path=f"{TEMP_REL}/{name}_before.vmdl")[:2], os.path.getsize(os.path.join(TEMP, name + "_before.vmdl_c")), flush=True)
    sys.exit(0)


def find(x, y):
    return min(places, key=lambda p: (p["at"][0] - x) ** 2 + (p["at"][1] - y) ** 2)


def view(name, place, dist, side, height, aim, fov=55):
    x, y, z = place["at"]
    ox, oy = place["out"]
    rx, ry = oy, -ox
    return dict(name=name, eye=[x + ox * dist + rx * side, y + oy * dist + ry * side, z + height], target=[x, y, z + aim], fov=fov)


views = [view("upper", find(1300, -1000), 92, -18, 34, 21), view("deck", find(1621, -640), 84, 14, 30, 21), view("close", find(1090, -1000), 42, 8, 20, 12, 52)]
outside = ["Ground", "Fuel Pool", "Pool Water", "Glass", "Yard Middle", "West", "East", "North Lane", "Boundary", "Backdrop", "Backdrop Near", "Backdrop Land East", "Backdrop Land West",
           "Backdrop Trees", "Backdrop Trees Near", "Yard Ground Detail", "Yard Props"]
common = dict(scene="Assets/scenes/maps/Riverdale/riverdale.scene", roots=["Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes", "Indirect Light"], exposure=2.0)
jobs = [
    dict(common, name="before", drop_children=outside + ["Extinguishers"], swap={f"models/maps/riverdale/{n}.vmdl": f"{TEMP_REL}/{n}_before.vmdl" for n in NAMES}),
    dict(common, name="after", drop_children=outside),
]
out_rel = WORK_REL + "/engine"
os.makedirs(os.path.join(ROOT, out_rel), exist_ok=True)
config = os.path.join(SCRATCH, "capture_engine.json")
json.dump(dict(out=out_rel, width=1600, height=900, stream_frames=120, settle_frames=24, views=views, jobs=jobs), open(config, "w"), indent=1)
script = os.path.join(SCRATCH, "capture_engine_run.cs.txt")
open(script, "w", encoding="utf-8", newline="\n").write(open(os.path.join(HERE, "capture_engine.cs.txt"), encoding="utf-8").read().replace("__CONFIG__", config.replace("\\", "/")))
code, out, err = call("run_csharp", path=script.replace("\\", "/"))
print(code, re.sub(r"\s+", " ", out)[-1100:], err[-400:], flush=True)
if code != 0:
    sys.exit(1)

W, H, GAP, HEAD, FOOT = 1100, 619, 8, 44, 40
sheet = Image.new("RGB", (W * 2 + GAP, HEAD + len(views) * (H + GAP) - GAP + FOOT), (14, 15, 17))
d = ImageDraw.Draw(sheet)
font = r"C:\Windows\Fonts\bahnschrift.ttf"
d.text((16, 8), "BEFORE", (235, 235, 235), font=ImageFont.truetype(font, 26))
d.text((W + GAP + 16, 8), "AFTER: Railhead's extinguisher", (235, 235, 235), font=ImageFont.truetype(font, 26))
for row, v in enumerate(views):
    for col, mode in enumerate(("before", "after")):
        frame = Image.open(os.path.join(ROOT, out_rel, f"{v['name']}-{mode}.png")).convert("RGB").resize((W, H), Image.LANCZOS)
        sheet.paste(frame, (col * (W + GAP), HEAD + row * (H + GAP)))
d.text((16, sheet.height - FOOT + 9), "Drawn by s&box from the hall's own files, same camera in each row. Not match screenshots: no HUD or gun.", (190, 190, 190), font=ImageFont.truetype(font, 18))
path = os.path.join(WORK, "riverdale-extinguisher-before-after.png")
sheet.save(path)
print(path, sheet.size, flush=True)
