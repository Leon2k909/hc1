"""Install the pews in the map's files: python install_pews.py <project root> [--write]

Cuts the old pews' faces from the two OBJs belltower_centre.vmdl really builds from, and adds the "Church Pews" group to belltower.scene, renderers only, so the old
collision in the merged model stays. Every corner must be one of an old pew's, and each pew must lose exactly its old triangles, or nothing is written. Without --write
it only reports. Files are moved into place with os.replace, and the originals are kept in the work folder's before-install. No full map run.
"""
import json
import os
import re
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import belltower_pews as Pews  # noqa: E402

DIR = os.path.join(ROOT, "Assets/models/maps/belltower/fountain-ornaments-v2/centre")
SCENE = os.path.join(ROOT, "Assets/scenes/maps/Belltower/belltower.scene")
BACKUP = os.path.join(ROOT, "output/asset-improvement-20261030/pew/before-install")
EXPECTED = {"centre_013_planks.obj": 2, "centre_014_planks_dark.obj": 22}  # Triangles each pew loses from each file.


def key(p):
    return tuple(round(float(x), 2) for x in p)


# Each pew is two boxes in the map script: a seat block and a back slab. Plan ( e, n, z ) is engine ( n, -e, z ).
boxes = []
for n in Pews.ROWS:
    for e0, e1 in Pews.BLOCKS:
        for n0, n1, z0, z1 in ((n - 18.0, n, 0.0, 18.0), (n - 3.0, n, 18.0, 38.0)):
            boxes.append(((n, e0), {key((nn, -e, z)) for nn in (n0, n1) for e in (e0, e1) for z in (z0, z1)}))
corner_boxes = {}
for index, (_, corners) in enumerate(boxes):
    for c in corners:
        corner_boxes.setdefault(c, set()).add(index)

out = {}
counts = {}
for name, each in EXPECTED.items():
    path = os.path.join(DIR, name)
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    v = []
    for line in lines:
        if line.startswith("v "):
            a, b, c = line[2:].split()[:3]
            v.append((float(c), float(a), float(b)))  # OBJ (a, b, c) is engine (c, a, b).
    drop = set()
    per_pew = {}
    for n, line in enumerate(lines):
        if not line.startswith("f "):
            continue
        tokens = line.split()[1:]
        hits = None
        for t in tokens:
            found = corner_boxes.get(key(v[int(t.split("/")[0]) - 1]), set())
            hits = found if hits is None else hits & found
            if not hits:
                break
        if hits:
            drop.add(n)
            pew = boxes[next(iter(hits))][0]
            per_pew[pew] = per_pew.get(pew, 0) + len(tokens) - 2
    counts[name] = per_pew
    print(name, "faces to cut:", len(drop), "per pew:", sorted(set(per_pew.values())), "pews:", len(per_pew), "of", len(lines), "lines", flush=True)
    if len(per_pew) != 12 or set(per_pew.values()) != {each}:
        sys.exit(f"{name}: expected 12 pews losing {each} triangles each. Nothing written.")
    out[path] = "".join(line for n, line in enumerate(lines) if n not in drop)

text = open(SCENE, "rb").read().decode("utf-8")
newline = "\r\n" if "\r\n" in text else "\n"
scene = json.loads(text)
namespace = re.search(r'ids = K\.SceneIds\( "([^"]+)" \)', open(os.path.join(ROOT, "Tools/belltower_map.py"), encoding="utf-8").read()).group(1)
ids = K.SceneIds(namespace)
group = Pews.scene_group(ids)


def find(nodes, name):
    for node in nodes:
        if node.get("Name") == name:
            return node
        found = find(node.get("Children", []), name)
        if found:
            return found
    return None


town = find(scene["GameObjects"], "Town")
if town is None:
    sys.exit("No Town object in the scene.")
town["Children"] = [c for c in town["Children"] if c.get("Name") != "Church Pews"] + [group]
scene_text = json.dumps(scene, indent=2, ensure_ascii=False).replace("\n", newline) + (newline if text.endswith("\n") else "")
for child in group["Children"][:2]:
    print(child["Name"], child["Position"], child["Rotation"], child["Components"][0]["Model"])
print("group under Town:", len(group["Children"]), "pews; scene grows by", len(scene_text) - len(text), "bytes", flush=True)
if not WRITE:
    print("report only: pass --write to change the files")
    sys.exit(0)
os.makedirs(BACKUP, exist_ok=True)
for path, body in out.items():
    backup = os.path.join(BACKUP, os.path.basename(path))
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
    temporary = path + ".installing"
    with open(temporary, "w", encoding="utf-8", newline="") as h:
        h.write(body)
    os.replace(temporary, path)
backup = os.path.join(BACKUP, os.path.basename(SCENE))
if not os.path.exists(backup):
    shutil.copyfile(SCENE, backup)
temporary = SCENE + ".installing"
with open(temporary, "wb") as h:
    h.write(scene_text.encode("utf-8"))
os.replace(temporary, SCENE)
print("written", flush=True)
