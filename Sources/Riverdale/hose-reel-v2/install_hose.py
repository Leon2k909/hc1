"""Swap Riverdale's five fire hose reel cabinets for hose_reel_v2 without regenerating the map: python -X utf8 install_hose.py <project root>

The hall's models aren't to be rebuilt whole, and other sessions change these same files. So this cuts only the old boards' faces from the live
`riverdale_hall_detail.obj` and `riverdale_hall_fine.obj`, and adds the "Hose Reels" group to the live scene. Each file is read just before it's written and swapped in
whole, and the write is abandoned if the file changed meanwhile or the open editor holds it. It stops without writing a file if a spot doesn't have the faces it should.
Safe to rerun. Same method as Sources/Riverdale/notice-board-v2/install_board.py.
"""
import json
import os
import shutil
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import riverdale_hose_reels as REELS  # noqa: E402

BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverdale")
SCENE = os.path.join(ROOT, "Assets", "scenes", "maps", "Riverdale", "riverdale.scene")
ROLLBACK = os.path.join(ROOT, "output", "asset-improvement-20261030", "hose-reel", "before-install")
IDS = K.SceneIds("5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85")  # riverdale_map's own, so a later rebuild makes the same objects.
W, H, DEEP = 33.0, 35.0, 2.4  # The old box and the handle on it.
# Plan ( e, n ) on the wall's face under the cabinet's middle, its bottom edge, and the way the wall looks. riverdale_hall's items: the deck's west and east walls at
# n 700, the north wall at e +-680 and the south wall at e 560.
WALLS = (((-1000.0, 700.0), 28.5, (1.0, 0.0)), ((1000.0, 700.0), 28.5, (-1.0, 0.0)), ((680.0, 2000.0), 28.5, (0.0, -1.0)), ((-680.0, 2000.0), 28.5, (0.0, -1.0)), ((560.0, -200.0), 28.5, (0.0, 1.0)))
# The box in the detail model; the window, the label and the handle in the fine one. Each spot has 10 triangles in the first and 2 + 2 + 10 in the second.
PAINT = {"riverdale_hall_detail.obj": ("rv_hall_red",), "riverdale_hall_fine.obj": ("rv_window_dark", "rv_hall_signs", "rv_hall_chrome")}
EXPECT = {"riverdale_hall_detail.obj": 10, "riverdale_hall_fine.obj": 14}


def swap_in(path, data, stamp):
    """Writes beside the file and moves it over. False if someone else changed the file since it was read, or the editor kept hold of it."""
    incoming = path + ".hose-incoming"
    with open(incoming, "wb") as h:
        h.write(data)
    for _ in range(45):
        if os.stat(path).st_mtime_ns != stamp:
            os.remove(incoming)
            return False
        try:
            os.replace(incoming, path)
            return True
        except PermissionError:
            time.sleep(2)
    os.remove(incoming)
    return False


def cut(name):
    path = os.path.join(BASE, name)
    paint = PAINT[name]
    for attempt in range(12):
        stamp = os.stat(path).st_mtime_ns
        with open(path, "rb") as h:
            raw = h.read()
        lines = raw.decode("utf-8").splitlines(keepends=True)
        verts = []
        for line in lines:
            if line.startswith("v "):
                a, b, c = line[2:].split()[:3]
                verts.append((float(a), float(b), float(c)))
        v = np.array(verts)
        # OBJ (a, b, c) is engine (c, a, b), and plan (e, n, z) is engine (n, -e, z).
        east, north, up = -v[:, 0], v[:, 2], v[:, 1]
        current = group = None
        faces_in_group, cut_in_group = {}, {}
        drop = set()
        counts = [0 for _ in WALLS]
        for n, line in enumerate(lines):
            if line.startswith("usemtl"):
                current = line.split()[1]
                group = n
            elif line.startswith("f "):
                faces_in_group[group] = faces_in_group.get(group, 0) + 1
                if current not in paint:
                    continue
                f = np.array([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
                for k, ((e, spot_n), z0, (oe, on)) in enumerate(WALLS):
                    out = (east[f] - e) * oe + (north[f] - spot_n) * on
                    along = (east[f] - e) * -on + (north[f] - spot_n) * oe
                    if np.abs(along).max() <= W / 2 + 0.02 and out.min() >= -0.02 and out.max() <= DEEP + 0.02 and up[f].min() >= z0 - 0.02 and up[f].max() <= z0 + H + 0.02:
                        drop.add(n)
                        counts[k] += 1
                        cut_in_group[group] = cut_in_group.get(group, 0) + 1
                        break
        print(name, paint, "faces by spot", counts, flush=True)
        if not drop:
            print(name, "has none left: already cut", flush=True)
            return
        if counts != [EXPECT[name]] * len(WALLS):
            raise SystemExit(f"{name}: every spot should have {EXPECT[name]} faces, not {counts}. Nothing written to it.")
        drop |= {g for g, c in cut_in_group.items() if g is not None and c == faces_in_group[g]}
        data = "".join(line for n, line in enumerate(lines) if n not in drop).encode("utf-8")
        os.makedirs(ROLLBACK, exist_ok=True)
        keep = os.path.join(ROLLBACK, name)
        if not os.path.exists(keep):
            shutil.copy2(path, keep)
        if swap_in(path, data, stamp):
            print(name, "cut", len(drop), "lines", flush=True)
            return
        print(name, "changed or was held: reading it again", flush=True)
    raise SystemExit(f"{name} kept changing: rerun this.")


def add_to_scene():
    placed = [REELS.placement((e, n, z0), out) for (e, n), z0, out in WALLS]
    group = REELS.scene_group(IDS, placed)
    for attempt in range(12):
        stamp = os.stat(SCENE).st_mtime_ns
        with open(SCENE, "rb") as h:
            raw = h.read()
        text = raw.decode("utf-8")
        scene = json.loads(text)
        world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
        if any(c.get("Name") == "Hose Reels" for c in world["Children"]):
            print("scene: already there", flush=True)
            return
        # An earlier tool left some of this file's line ends doubled, so writing it out whole would change far more than the group. The group goes into the text
        # as it stands, and only if the result reads as exactly the scene plus the group.
        at = text.index('"Children"', text.index('"Name": "Riverdale"'))
        at = text.index("[", at)
        depth, in_string, escaped, end = 0, False, False, None
        for k in range(at, len(text)):
            c = text[k]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
            elif c == '"':
                in_string = True
            elif c in "[{":
                depth += 1
            elif c in "]}":
                depth -= 1
                if depth == 0:
                    end = k
                    break
        before = text[:end].rstrip()
        block = "\n".join("      " + line for line in json.dumps(group, indent=2).split("\n"))
        new_text = before + ",\n" + block + "\n    " + text[end:]
        world["Children"].append(group)
        if json.loads(new_text) != scene:
            raise SystemExit("Adding the group would change more than the hose reels. Nothing written to the scene.")
        data = new_text.encode("utf-8")
        os.makedirs(ROLLBACK, exist_ok=True)
        keep = os.path.join(ROLLBACK, "riverdale.scene")
        if not os.path.exists(keep):
            shutil.copy2(SCENE, keep)
        if swap_in(SCENE, data, stamp):
            print("scene:", len(group["Children"]), "hose reels", [(c["Position"], c["Rotation"]) for c in group["Children"]], flush=True)
            return
        print("scene changed or was held: reading it again", flush=True)
    raise SystemExit("The scene kept changing: rerun this.")


cut("riverdale_hall_detail.obj")
cut("riverdale_hall_fine.obj")
add_to_scene()
