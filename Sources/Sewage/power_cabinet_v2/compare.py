"""Render the before and after in s&box and compose them: python compare.py [view ...]

Writes output/asset-improvement-20261030/sewage-power-cabinet/engine/config.json, runs capture_engine.cs.txt through sbox-cli and
puts the pairs side by side in final/. Views are given in the map generator's plan coordinates (east, north, up).
"""
import json
import os
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030", "sewage-power-cabinet")
ENGINE = os.path.join(WORK, "engine")
FINAL = os.path.join(WORK, "final")


def world(e, n, z):
    return [n, -e, z]


CABINETS = [dict(at=world(-958, 470, 0), yaw=-90), dict(at=world(946, 600, 0), yaw=90), dict(at=world(-870, 830, 352), yaw=-90)]
VIEWS = {
    "a_wide": ((-740, 400, 64), (-958, 470, 58), 70),
    "a_door": ((-850, 450, 66), (-940, 462, 62), 75),
    "a_low": ((-860, 395, 56), (-950, 430, 40), 70),
    "a_top": ((-860, 495, 70), (-940, 455, 92), 70),
    "a_side": ((-760, 300, 64), (-958, 430, 62), 70),
    "a_south": ((-890, 330, 70), (-958, 432, 52), 70),
    "a_far": ((-400, 290, 64), (-958, 470, 58), 70),
    "a_far2": ((60, 120, 64), (-958, 470, 58), 70),
    "b_wide": ((745, 660, 64), (946, 600, 58), 70),
    "c_wide": ((-700, 760, 416), (-870, 830, 410), 75),
}
EXPOSURE = 2.0

picked = sys.argv[1:] or list(VIEWS)
os.makedirs(ENGINE, exist_ok=True)
os.makedirs(FINAL, exist_ok=True)
config = dict(
    model="models/maps/sewage/power_cabinet_v2/power_cabinet.vmdl",
    cabinets=CABINETS,
    # At the new status lamp, just below its glass.
    light_local=[24.0, -24.0, 104.5],
    exposure=EXPOSURE,
    stream_frames=70,
    settle_frames=14,
    width=1280,
    height=800,
    variants=["before", "after"],
    views=[dict(name=k, eye=world(*VIEWS[k][0]), target=world(*VIEWS[k][1]), fov=VIEWS[k][2]) for k in picked],
)
with open(os.path.join(ENGINE, "config.json"), "w") as h:
    json.dump(config, h, indent=1)
started = time.time()
run = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": os.path.join(HERE, "capture_engine.cs.txt")})], cwd=ROOT, capture_output=True, timeout=240)
print((run.stdout + run.stderr).decode("utf-8", "replace")[:1800], f"{time.time() - started:.0f}s", flush=True)

font = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 30)
for name in picked:
    pair = [Image.open(os.path.join(ENGINE, f"{name}-{v}.png")).convert("RGB") for v in ("before", "after")]
    w, h = pair[0].size
    # The far edge of a shot should match in both: if it doesn't, the exposure drifted and the comparison is unfair.
    edges = [sum(p.crop((0, h // 4, w // 12, h * 3 // 4)).convert("L").resize((1, 1)).getdata()) for p in pair]
    print(name, "left edge, before and after:", edges, flush=True)
    sheet = Image.new("RGB", (w * 2 + 12, h), (18, 18, 18))
    sheet.paste(pair[0], (0, 0))
    sheet.paste(pair[1], (w + 12, 0))
    d = ImageDraw.Draw(sheet)
    for x, label in ((18, "BEFORE"), (w + 30, "AFTER")):
        d.text((x + 2, 16), label, fill=(0, 0, 0), font=font)
        d.text((x, 14), label, fill=(240, 236, 220), font=font)
    sheet.save(os.path.join(FINAL, f"{name}.png"))
