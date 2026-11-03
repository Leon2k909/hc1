"""Swap Riverside's six propane cylinders for propane_v2 without regenerating the map: python -X utf8 install_propane.py <project root>

The placements come from riverside_map's own code (its trailers and pad, run without writing anything), so the scene gets exactly what a later rebuild makes.
This cuts only the old cylinders' faces from the live `riverside_pad.obj` and `riverside_terrace.obj`, leaving the big ones' collision hulls, and adds the
"Propane Cylinders" group to the live scene after "Teddy". Each file is read just before it's written and swapped in whole, and the write is abandoned if the file
changed meanwhile or the open editor holds it. It stops without writing a file if a spot doesn't have the faces it should. Safe to rerun.
Same method as Sources/Riverdale/hose-reel-v2/install_hose.py.
"""
import json
import os
import shutil
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.argv = sys.argv[:1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import riverside_map as M  # noqa: E402
import riverside_parts as P  # noqa: E402

BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverside")
SCENE = os.path.join(ROOT, "Assets", "scenes", "maps", "Riverside", "riverside.scene")
ROLLBACK = os.path.join(ROOT, "output", "asset-improvement-20261030", "propane", "before-install")
PAINTS = ("rs_propane", "rs_steel")
REACH = {"100": (7.6, 50.05), "20": (6.15, 18.05)}  # The old cylinders' radius and height, a hair over.

P.reset()
zones = {"riverside_low.obj": K.Model(), "riverside_terrace.obj": K.Model(), "riverside_levee.obj": K.Model(), "riverside_pad.obj": K.Model()}
low, terrace, high, pad = zones.values()
M.trailers(low, terrace, high)
M.pad(pad)
file_of = {id(m): name for name, m in zones.items()}
SPOTS = [(file_of[id(owner)], np.array(K.to_world(position), float), size) for owner, position, yaw, size in P.PROPANE]
assert len(SPOTS) == 6, SPOTS


def swap_in(path, data, stamp):
    """Writes beside the file and moves it over. False if someone else changed the file since it was read, or the editor kept hold of it."""
    incoming = path + ".propane-incoming"
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


def keep(path):
    os.makedirs(ROLLBACK, exist_ok=True)
    target = os.path.join(ROLLBACK, os.path.basename(path))
    if not os.path.exists(target):
        shutil.copy2(path, target)


def cut(name):
    path = os.path.join(BASE, name)
    spots = [(at, size) for file, at, size in SPOTS if file == name]
    for attempt in range(12):
        stamp = os.stat(path).st_mtime_ns
        with open(path, "rb") as h:
            lines = h.read().decode("utf-8").splitlines(keepends=True)
        verts = []
        for line in lines:
            if line.startswith("v "):
                a, b, c = line[2:].split()[:3]
                verts.append((float(c), float(a), float(b)))  # OBJ (a, b, c) is engine (c, a, b).
        v = np.array(verts)
        current = group = None
        faces_in_group, cut_in_group = {}, {}
        drop, counts = set(), [0] * len(spots)
        for n, line in enumerate(lines):
            if line.startswith("usemtl"):
                current, group = line.split()[1], n
            elif line.startswith("f "):
                faces_in_group[group] = faces_in_group.get(group, 0) + 1
                if current not in PAINTS:
                    continue
                p = v[[int(t.split("/")[0]) - 1 for t in line.split()[1:]]]
                for k, (at, size) in enumerate(spots):
                    r, tall = REACH[size]
                    if np.hypot(p[:, 0] - at[0], p[:, 1] - at[1]).max() <= r and p[:, 2].min() >= at[2] - 0.05 and p[:, 2].max() <= at[2] + tall:
                        drop.add(n)
                        counts[k] += 1
                        cut_in_group[group] = cut_in_group.get(group, 0) + 1
                        break
        print(name, "faces by spot", list(zip([s for _, s in spots], counts)), flush=True)
        if not drop:
            print(name, "has none left: already cut", flush=True)
            return
        for size in set(s for _, s in spots):
            got = {c for (_, s), c in zip(spots, counts) if s == size}
            if len(got) != 1 or 0 in got:
                raise SystemExit(f"{name}: every {size} lb spot should have the same faces, not {counts}. Nothing written to it.")
        drop |= {g for g, c in cut_in_group.items() if g is not None and c == faces_in_group[g]}
        data = "".join(line for n, line in enumerate(lines) if n not in drop).encode("utf-8")
        keep(path)
        if swap_in(path, data, stamp):
            print(name, "cut", len(drop), "lines", flush=True)
            return
        print(name, "changed or was held: reading it again", flush=True)
    raise SystemExit(f"{name} kept changing: rerun this.")


def object_end(text, start):
    """The index of the closing brace of the JSON object that opens at text[start]."""
    depth, in_string, escaped = 0, False, False
    for k in range(start, len(text)):
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
                return k
    raise ValueError("unbalanced")


def add_to_scene():
    group = K.game_object(M.ids, "Propane Cylinders", "propane", children=M.propane_objects())
    for attempt in range(12):
        stamp = os.stat(SCENE).st_mtime_ns
        with open(SCENE, "rb") as h:
            text = h.read().decode("utf-8")
        scene = json.loads(text)
        names = [o.get("Name") for o in scene["GameObjects"]]
        if "Propane Cylinders" in names:
            print("scene: already there", flush=True)
            return
        after = names.index("Teddy")
        teddy = scene["GameObjects"][after]
        # Find the Teddy object in the text by its guid, then its own opening brace, and insert the group after its closing one.
        at = text.index(f'"{teddy["__guid"]}"')
        start = text.rindex("{", 0, at)
        end = object_end(text, start)
        newline = "\r\n" if "\r\n" in text else "\n"
        indent = text[text.rindex("\n", 0, start) + 1:start]
        block = newline.join(indent + line for line in json.dumps(group, indent=2).split("\n")).lstrip()
        new_text = text[:end + 1] + "," + newline + indent + block + text[end + 1:]
        scene["GameObjects"].insert(after + 1, group)
        if json.loads(new_text) != scene:
            raise SystemExit("Adding the group would change more than the cylinders. Nothing written to the scene.")
        keep(SCENE)
        if swap_in(SCENE, new_text.encode("utf-8"), stamp):
            print("scene:", len(group["Children"]), "cylinders", [(c["Position"], c["Components"][0]["Model"].split("/")[-1]) for c in group["Children"]], flush=True)
            return
        print("scene changed or was held: reading it again", flush=True)
    raise SystemExit("The scene kept changing: rerun this.")


cut("riverside_pad.obj")
cut("riverside_terrace.obj")
add_to_scene()
