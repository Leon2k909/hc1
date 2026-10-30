"""Score visible-check.cs.txt's renders inside the teammate's own silhouette (the shadow and horizon left out).

python score-visible.py <folder> <trial[,trial...]> [case,...]: the changed pixels on the visible character, the share
of the hidden one that glows, and the partly covered one's glow inside and outside its covered part.
Writes scores.json to the folder."""
import sys, json
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image
folder = Path(sys.argv[1]); trials = sys.argv[2].split(",")
cases = sys.argv[3].split(",") if len(sys.argv) > 3 else ["front200", "side350", "run550", "back850", "crouch240"]
load = lambda n: np.asarray(Image.open(folder / n).convert("RGB")).astype(int)
diff = lambda a, b: np.abs(a - b).max(axis=2) > 3

DIST = {"front200": 200, "side350": 350, "run550": 550, "back850": 850, "crouch240": 240}
def body(case):
    """The actor's pixels: its difference from the empty frame inside a box round where it stands, its shadow left out."""
    vis, empty = load(f"{case}-visible-off.png"), load(f"{case}-empty.png")
    d = diff(vis, empty)
    ratio = (vis + 1) / (empty + 1)
    shadow = (ratio.max(axis=2) - ratio.min(axis=2) < 0.08) & (ratio.mean(axis=2) < 0.98)
    d &= ~shadow
    h = 44900 / DIST[case]
    box = np.zeros_like(d)
    box[int(360 - 0.8 * h):int(360 + 0.6 * h), int(640 - 0.5 * h):int(640 + 0.5 * h)] = True
    seen = d & box
    g = seen.copy()
    for _ in range(2):
        g = g | np.roll(g, 1, 0) | np.roll(g, -1, 0) | np.roll(g, 1, 1) | np.roll(g, -1, 1)
    return seen, g

rows = []
for case in cases:
    mask, grown = body(case)
    covered = mask & diff(load(f"{case}-partial-off.png"), load(f"{case}-visible-off.png"))
    for t in trials:
        vis = diff(load(f"{case}-visible-{t}.png"), load(f"{case}-visible-off.png")) & grown
        hid = diff(load(f"{case}-hidden-{t}.png"), load(f"{case}-hidden-off.png")) & mask
        par = diff(load(f"{case}-partial-{t}.png"), load(f"{case}-partial-off.png")) & grown
        rows.append(dict(case=case, trial=t, body=int(mask.sum()), visible_leak=int(vis.sum()),
                         hidden_cover=round(float(hid.sum()) / max(mask.sum(), 1), 3),
                         partial_in=round(float((par & covered).sum()) / max(covered.sum(), 1), 3),
                         partial_leak=int((par & ~covered).sum())))
for r in rows: print(r)
json.dump(rows, open(folder / "scores.json", "w"), indent=1)
