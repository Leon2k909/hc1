"""Swap Cerro Blanco's eight cafe tables for cafe_table_v2 without regenerating the map: python -X utf8 install_tables.py <project root> [--write]

The scene draws quality-v1/cerroblanco_dressing_v2.obj, and other sessions change the map's files, so this cuts only the old tables' faces from that OBJ (the same ones as cut_compare.py) and adds
the "Cafe Tables" group under "Cerro Blanco" in the live scene: the whole table in the cafe, the top only under the courtyard's parasols. Their collision boxes stay in the dressing model. Each file is read just before it's written and swapped in whole, and the work is done again if the file changed meanwhile or the open
editor holds it. It stops without writing a file if a table doesn't have the faces it should. Without --write it only reports. Safe to rerun.
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
import cerroblanco_tables as TABLES  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut_compare  # noqa: E402
from cut_compare import COURTYARD, EXPECTED, INSIDE  # noqa: E402

OBJ = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "quality-v1", "cerroblanco_dressing_v2.obj")
SCENE = os.path.join(ROOT, "Assets", "scenes", "maps", "CerroBlanco", "cerroblanco.scene")
IDS = K.SceneIds("7d2e9b41-3c58-4a6f-b1e0-5f93c8a2d714")  # cerroblanco_map's own, so a later rebuild makes the same objects.



def swap_in(path, data, stamp):
    """Writes beside the file and moves it over. False if someone else changed the file since it was read, or the editor kept hold of it."""
    incoming = path + ".table-incoming"
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


def cut():
    for attempt in range(12):
        stamp = os.stat(OBJ).st_mtime_ns
        with open(OBJ, "rb") as h:
            raw = h.read()
        lines = raw.decode("utf-8").splitlines(keepends=True)
        v = np.array([line[2:].split()[:3] for line in lines if line.startswith("v ")], float)
        drop, counts = cut_compare.faces_to_cut(lines, v)
        print("faces by table", counts, flush=True)
        if not drop:
            print("none left: already cut", flush=True)
            return
        if any(c != EXPECTED[k] for k, c in enumerate(counts)):
            raise SystemExit(f"The tables should have {[EXPECTED[k] for k in range(len(counts))]}, not {counts}. Nothing written to the OBJ.")
        if not WRITE:
            return
        # A material whose every face went comes out with them: the loader refuses one left empty at the end of a file.
        group, faces_in_group, cut_in_group = None, {}, {}
        for n, line in enumerate(lines):
            if line.startswith("usemtl"):
                group = n
            elif line.startswith("f "):
                faces_in_group[group] = faces_in_group.get(group, 0) + 1
                if n in drop:
                    cut_in_group[group] = cut_in_group.get(group, 0) + 1
        drop |= {g for g, c in cut_in_group.items() if g is not None and c == faces_in_group[g]}
        data = "".join(line for n, line in enumerate(lines) if n not in drop).encode("utf-8")
        if swap_in(OBJ, data, stamp):
            print("OBJ cut", len(drop), "lines", flush=True)
            return
        print("OBJ changed or was held: reading it again", flush=True)
    raise SystemExit("The OBJ kept changing: rerun this.")


def add_to_scene():
    group = TABLES.scene_group(IDS, [(e, n, 0.0) for e, n in list(INSIDE) + list(COURTYARD)], parasols=[(e, n, 0.0) for e, n in COURTYARD])
    for attempt in range(12):
        stamp = os.stat(SCENE).st_mtime_ns
        with open(SCENE, "rb") as h:
            raw = h.read()
        text = raw.decode("utf-8")
        scene = json.loads(text)
        world = next(o for o in scene["GameObjects"] if o.get("Name") == "Cerro Blanco")
        if any(c.get("Name") == "Cafe Tables" for c in world["Children"]):
            print("scene: already there", flush=True)
            return
        # Other sessions' changes sit uncommitted in this file, so the group goes into the text as it stands, in its CRLF line ends, and only if the result reads as exactly the scene plus the group.
        at = text.index('"Children"', text.index('"Name": "Cerro Blanco"'))
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
        newline = "\r\n" if "\r\n" in text[:200] else "\n"
        before = text[:end].rstrip()
        block = newline.join("      " + line for line in json.dumps(group, indent=2).split("\n"))
        new_text = before + "," + newline + block + newline + "    " + text[end:]
        world["Children"].append(group)
        if json.loads(new_text) != scene:
            raise SystemExit("Adding the group would change more than the tables. Nothing written to the scene.")
        print("scene:", len(group["Children"]), "tables", [(c["Position"], c["Components"][0]["Model"].rsplit("/", 1)[-1]) for c in group["Children"]], flush=True)
        if not WRITE:
            print("dry run: nothing written", flush=True)
            return
        if swap_in(SCENE, new_text.encode("utf-8"), stamp):
            print("scene written", flush=True)
            return
        print("scene changed or was held: reading it again", flush=True)
    raise SystemExit("The scene kept changing: rerun this.")


# The scene goes first, so a stop on the OBJ leaves the old table drawn with the new one rather than nothing.
add_to_scene()
cut()
