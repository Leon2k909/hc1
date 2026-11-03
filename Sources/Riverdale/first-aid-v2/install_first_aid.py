"""Swap Riverdale's four first aid boxes for first_aid_v2 without regenerating the map: python -X utf8 install_first_aid.py <project root> [--write]

The hall's models aren't to be rebuilt whole (docs/notes on Riverdale), and other sessions change these same files. So this cuts only the old boxes' faces from the live `riverdale_hall_detail.obj`
and their pictures from `riverdale_hall_fine.obj`, and adds the "First Aid Cabinets" group to the live scene. Each file is read just before it's written and swapped in whole, and the work is done
again if the file changed meanwhile or the open editor holds it. It stops without writing a file if a spot doesn't have the faces it should. Without --write it only reports. Safe to rerun.
"""
import json
import os
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import riverdale_first_aid as FIRST_AID  # noqa: E402

BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverdale")
SCENE = os.path.join(ROOT, "Assets", "scenes", "maps", "Riverdale", "riverdale.scene")
IDS = K.SceneIds("5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85")  # riverdale_map's own, so a later rebuild makes the same objects.
Z_FOOT = 54.0
# Plan ( e, n ) on the wall's face, and the way the wall looks: the side walls at n 985, and the north wall at e -962 and -95.
WALLS = (((-1000.0, 985.0), (1.0, 0.0)), ((1000.0, 985.0), (-1.0, 0.0)), ((-962.0, 2000.0), (0.0, -1.0)), ((-95.0, 2000.0), (0.0, -1.0)))
# file: paint, faces at each spot, how far along the wall, how far out, nearest and farthest.
EXPECTED = {"riverdale_hall_detail.obj": ("rv_hall_green", 10, 7.02, -0.01, 5.02), "riverdale_hall_fine.obj": ("rv_hall_signs", 2, 6.42, 5.0, 5.1)}


def swap_in(path, data, stamp):
    """Writes beside the file and moves it over. False if someone else changed the file since it was read, or the editor kept hold of it."""
    incoming = path + ".first-aid-incoming"
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
    paint, want, along_limit, near, far = EXPECTED[name]
    for attempt in range(12):
        stamp = os.stat(path).st_mtime_ns
        with open(path, "rb") as h:
            raw = h.read()
        lines = raw.decode("utf-8").splitlines(keepends=True)
        v = np.array([line[2:].split()[:3] for line in lines if line.startswith("v ")], float)
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
                if current != paint:
                    continue
                f = np.array([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
                if up[f].min() < Z_FOOT - 0.1 or up[f].max() > Z_FOOT + 17.1:
                    continue
                for k, ((e, spot_n), (oe, on)) in enumerate(WALLS):
                    out = (east[f] - e) * oe + (north[f] - spot_n) * on
                    along = (east[f] - e) * -on + (north[f] - spot_n) * oe
                    if np.abs(along).max() <= along_limit and out.min() >= near and out.max() <= far:
                        drop.add(n)
                        counts[k] += 1
                        cut_in_group[group] = cut_in_group.get(group, 0) + 1
                        break
        print(name, paint, "faces by spot", counts, flush=True)
        if not drop:
            print(name, "has none left: already cut", flush=True)
            return
        if any(c != want for c in counts):
            raise SystemExit(f"{name}: each spot should have {want}, not {counts}. Nothing written to it.")
        if not WRITE:
            return
        # A material whose every face went comes out with them: the loader refuses one left empty at the end of a file.
        drop |= {g for g, c in cut_in_group.items() if g is not None and c == faces_in_group[g]}
        data = "".join(line for n, line in enumerate(lines) if n not in drop).encode("utf-8")
        if swap_in(path, data, stamp):
            print(name, "cut", len(drop), "lines", flush=True)
            return
        print(name, "changed or was held: reading it again", flush=True)
    raise SystemExit(f"{name} kept changing: rerun this.")


def add_to_scene():
    placed = [FIRST_AID.placement((e, n, Z_FOOT), (oe, on)) for (e, n), (oe, on) in WALLS]
    group = FIRST_AID.scene_group(IDS, placed)
    for attempt in range(12):
        stamp = os.stat(SCENE).st_mtime_ns
        with open(SCENE, "rb") as h:
            raw = h.read()
        text = raw.decode("utf-8")
        scene = json.loads(text)
        world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
        if any(c.get("Name") == "First Aid Cabinets" for c in world["Children"]):
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
            raise SystemExit("Adding the group would change more than the cabinets. Nothing written to the scene.")
        print("scene:", len(group["Children"]), "cabinets", [(c["Position"], c["Rotation"]) for c in group["Children"]], flush=True)
        if not WRITE:
            print("dry run: nothing written", flush=True)
            return
        if swap_in(SCENE, new_text.encode("utf-8"), stamp):
            print("scene written", flush=True)
            return
        print("scene changed or was held: reading it again", flush=True)
    raise SystemExit("The scene kept changing: rerun this.")


# The scene goes first, so a stop on an OBJ's faces leaves the old box drawn inside the new cabinet, which covers it, rather than a bare wall.
add_to_scene()
for name in EXPECTED:
    cut(name)
