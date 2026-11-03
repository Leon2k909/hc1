"""Swap Riverdale's five eye washes for eyewash_v2 without regenerating the map: python -X utf8 install_eyewash.py <project root>

The hall's models aren't to be rebuilt whole (docs/notes on Riverdale), and other sessions change these same files. So this cuts only the old eye washes' faces from the live `riverdale_hall_detail.obj` and
`riverdale_hall_fine.obj`, leaves their signs, and adds the "Eye Washes" group to the live scene. Each file is read just before it's written and swapped in whole, and the work is done again if the file
changed meanwhile or the open editor holds it. It stops without writing that file if a spot doesn't have the faces it should. Safe to rerun.
"""
import json
import os
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import riverdale_eyewash as EYEWASHES  # noqa: E402

BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverdale")
SCENE = os.path.join(ROOT, "Assets", "scenes", "maps", "Riverdale", "riverdale.scene")
IDS = K.SceneIds("5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85")  # riverdale_map's own, so a later rebuild makes the same objects.
# Plan ( e, n ) on the wall's face, and the way the wall looks. riverdale_hall's side walls at n 560, north wall at e 962, south wall at e +-880.
WALLS = (((-1000.0, 560.0), (1.0, 0.0)), ((1000.0, 560.0), (-1.0, 0.0)), ((962.0, 2000.0), (0.0, -1.0)), ((-880.0, -200.0), (0.0, 1.0)), ((880.0, -200.0), (0.0, 1.0)))
EXPECTED = {"riverdale_hall_detail.obj": {"rv_hall_green": 56, "rv_stainless": 12}, "riverdale_hall_fine.obj": {"rv_hall_green": 122, "rv_hall_chrome": 44}}


def swap_in(path, data, stamp):
    """Writes beside the file and moves it over. False if someone else changed the file since it was read, or the editor kept hold of it."""
    incoming = path + ".eyewash-incoming"
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
    want = EXPECTED[name]
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
        counts = [{k: 0 for k in want} for _ in WALLS]
        for n, line in enumerate(lines):
            if line.startswith("usemtl"):
                current = line.split()[1]
                group = n
            elif line.startswith("f "):
                faces_in_group[group] = faces_in_group.get(group, 0) + 1
                if current not in want:
                    continue
                f = np.array([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
                if up[f].min() < 5.9 or up[f].max() > 38.8:
                    continue
                for k, ((e, spot_n), (oe, on)) in enumerate(WALLS):
                    out = (east[f] - e) * oe + (north[f] - spot_n) * on
                    along = (east[f] - e) * -on + (north[f] - spot_n) * oe
                    if np.abs(along).max() <= 8.6 and out.min() >= -0.01 and out.max() <= 12.6:
                        drop.add(n)
                        counts[k][current] += 1
                        cut_in_group[group] = cut_in_group.get(group, 0) + 1
                        break
        print(name, "faces by spot", counts, flush=True)
        if not drop:
            print(name, "has none left: already cut", flush=True)
            return
        if any(c != want for c in counts):
            raise SystemExit(f"{name}: each spot should have {want}, not {counts}. Nothing written to it.")
        drop |= {g for g, c in cut_in_group.items() if g is not None and c == faces_in_group[g]}
        data = "".join(line for n, line in enumerate(lines) if n not in drop).encode("utf-8")
        if swap_in(path, data, stamp):
            print(name, "cut", len(drop), "lines", flush=True)
            return
        print(name, "changed or was held: reading it again", flush=True)
    raise SystemExit(f"{name} kept changing: rerun this.")


def add_to_scene():
    placed = []
    for (e, n), (oe, on) in WALLS:
        placed.append(EYEWASHES.placement((e + oe * EYEWASHES.STAND_OFF, n + on * EYEWASHES.STAND_OFF, 0.0), (oe, on)))
    group = EYEWASHES.scene_group(IDS, placed)
    for attempt in range(12):
        stamp = os.stat(SCENE).st_mtime_ns
        with open(SCENE, "rb") as h:
            raw = h.read()
        text = raw.decode("utf-8")
        scene = json.loads(text)
        world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
        if any(c.get("Name") == "Eye Washes" for c in world["Children"]):
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
                escaped = c == "\\" and not escaped
                if c == '"' and not escaped:
                    in_string = False
                if c != "\\":
                    escaped = False
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
            raise SystemExit("Adding the group would change more than the eye washes. Nothing written to the scene.")
        data = new_text.encode("utf-8")
        if swap_in(SCENE, data, stamp):
            print("scene:", len(group["Children"]), "eye washes", [c["Position"] for c in group["Children"]], flush=True)
            return
        print("scene changed or was held: reading it again", flush=True)
    raise SystemExit("The scene kept changing: rerun this.")


for name in EXPECTED:
    cut(name)
add_to_scene()
