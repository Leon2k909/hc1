"""Swap the OPS room's whiteboard for whiteboard_v2 without rerunning orion_map: python -X utf8 install_whiteboard.py <project root>

Orion's map script doesn't reproduce its live OBJs exactly (docs/notes/171), so this cuts only the old picture's two triangles from the live `orion_fuel.obj`, and adds the
board to the live scene's "Orion" object, built by orion_map's own `whiteboard_object` so a later rerun makes the same object. Each file is read just before it's written and
swapped in whole, and the write is abandoned if the file changed meanwhile. It stops without writing if it doesn't find exactly what it expects. Safe to rerun.
"""
import json
import os
import shutil
import sys
import time

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import orion_map as B  # noqa: E402

OBJ = os.path.join(ROOT, "Assets", "models", "maps", "orion", "orion_fuel.obj")
SCENE = os.path.join(ROOT, "Assets", "scenes", "maps", "Orion", "orion.scene")
ROLLBACK = os.path.join(ROOT, "output", "asset-improvement-20261030", "whiteboard", "before-install")


def swap_in(path, data, stamp):
    incoming = path + ".whiteboard-incoming"
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


def cut():
    for attempt in range(12):
        stamp = os.stat(OBJ).st_mtime_ns
        lines = open(OBJ, "rb").read().decode("utf-8").splitlines(keepends=True)
        verts = []
        for line in lines:
            if line.startswith("v "):
                a, b, c = map(float, line[2:].split()[:3])
                verts.append((c, a, b))  # OBJ (a, b, c) is engine (c, a, b).
        current, drop = None, []
        for n, line in enumerate(lines):
            if line.startswith("usemtl"):
                current = line.split()[1]
            elif line.startswith("f ") and current == "oa_plates":
                p = [verts[int(t.split("/")[0]) - 1] for t in line.split()[1:]]
                if all(abs(x - 822.5) < 0.05 and -952.6 < y < -847.4 and 339.9 < z < 400.1 for x, y, z in p):
                    drop.append(n)
        if not drop:
            print("orion_fuel.obj: the old picture is already gone", flush=True)
            return
        if len(drop) != 2:
            raise SystemExit(f"orion_fuel.obj: expected the old picture's 2 triangles, found {len(drop)}. Nothing written.")
        keep(OBJ)
        data = "".join(line for n, line in enumerate(lines) if n not in set(drop)).encode("utf-8")
        if swap_in(OBJ, data, stamp):
            print("orion_fuel.obj: cut the old picture's 2 triangles", flush=True)
            return
        print("orion_fuel.obj changed or was held: reading it again", flush=True)
    raise SystemExit("orion_fuel.obj kept changing: rerun this.")


def add_to_scene():
    objects = [B.whiteboard_object(*placed) for placed in B.WHITEBOARDS]
    for attempt in range(12):
        stamp = os.stat(SCENE).st_mtime_ns
        text = open(SCENE, "rb").read().decode("utf-8")
        scene = json.loads(text)
        world = next(o for o in scene["GameObjects"] if o.get("Name") == "Orion")
        if any(c.get("Name") == "Whiteboard" for c in world["Children"]):
            print("scene: already there", flush=True)
            return
        newline = "\r\n" if "\r\n" in text else "\n"
        # Insert into the text as it stands, after the world object's last child, and only if the result reads as exactly the scene plus the board.
        anchor = text.index(f'"{world["__guid"]}"')
        at = text.index("[", text.index('"Children"', anchor))
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
        block = newline.join("        " + line for line in json.dumps(objects[0], indent=2).split("\n"))
        new_text = before + "," + newline + block + newline + "      " + text[end:]
        world["Children"].extend(objects)
        if json.loads(new_text) != scene:
            raise SystemExit("Adding the board would change more than the board. Nothing written to the scene.")
        keep(SCENE)
        if swap_in(SCENE, new_text.encode("utf-8"), stamp):
            print("scene: added", objects[0]["Position"], objects[0]["Rotation"], flush=True)
            return
        print("scene changed or was held: reading it again", flush=True)
    raise SystemExit("The scene kept changing: rerun this.")


cut()
add_to_scene()
