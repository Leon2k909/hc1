"""Stage Belltower's visible model refresh for import through the open editor.

Scene objects, terrain, foliage placement, and gameplay configuration are kept
in the editor. Collision checks run before the staged files may be imported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import belltower_map as B

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/quality/models"


def collision_signature(path):
    # QHull can triangulate a coplanar quad across either diagonal. Compare each
    # connected convex element's vertices rather than its triangle order.
    vertices,faces = [],[]
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            vertices.append(tuple(map(float,line.split()[1:])))
        elif line.startswith("f "):
            faces.append([int(v.split("/")[0])-1 for v in line.split()[1:]])
    parent = list(range(len(vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for face in faces:
        for i in face[1:]:
            parent[find(i)] = find(face[0])
    groups = {}
    for i,v in enumerate(vertices):
        groups.setdefault(find(i),[]).append(v)
    return sorted(tuple(sorted(v)) for v in groups.values())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT,help='Separate staging folder inside output/belltower/quality/models')
    parser.add_argument('--parts',nargs='+',choices=('centre','west','east'),default=('centre','west','east'))
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(OUT.resolve()):
        raise ValueError('Model staging must remain inside output/belltower/quality/models')
    out.mkdir(parents=True, exist_ok=True)
    # An interrupted build must not leave an older import list pointing at
    # partially replaced staging files.
    import_path = OUT.parent/'model-import.json' if out==OUT.resolve() else out/'model-import.json'
    import_path.write_text(json.dumps({"status":"building","invalid_spots":-1,"unreachable_spots":-1,"files":[]})+"\n")
    centre = B.build_centre([])
    west = B.build_west([], np.random.default_rng(2024))
    east = west.mirrored(B.EAST_PAINTS)
    B.CafeSpacing.apply_east(east, B.EAST_PAINTS)
    models = [("centre",centre),("west",west),("east",east)]
    for name,model in models:
        B.Detail.configure(model)
    aabbs = B.collision_aabbs([x[1] for x in models])
    spots = B.all_spots()
    problems = B.check_spots(aabbs,spots)
    cut_off = B.check_reach([x[1] for x in models],spots,None)
    if problems or cut_off:
        raise RuntimeError(f"Refusing import: {problems} invalid spots, {cut_off} unreachable")
    manifest = {"spots":len(spots),"invalid_spots":problems,"unreachable_spots":cut_off,"models":[],"files":[]}
    for name,model in models:
        if name not in args.parts:
            continue
        full_name = "belltower_"+name
        triangles = B.K.write_model(out,B.RESOURCE_DIR,full_name,model)
        record = {"name":full_name,"triangles":triangles,"boxes":len(model.boxes),"hulls":len(model.hulls)}
        manifest["models"].append(record)
        print(record,flush=True)
        for path in sorted(out.glob(full_name+"*")):
            if path.suffix not in (".obj",".mtl",".vmdl"):
                continue
            relative = f"{B.RESOURCE_DIR}/{path.name}"
            previous = ROOT/"Assets"/relative
            unchanged = previous.exists() and hashlib.md5(previous.read_bytes()).digest() == hashlib.md5(path.read_bytes()).digest()
            if "_hulls_" in path.name:
                if not previous.exists() or collision_signature(previous) != collision_signature(path):
                    raise RuntimeError(f"Unexpected collision change: {path.name}")
                continue
            if path.suffix == ".vmdl":
                physics = lambda p: p.read_text().partition('_class = "PhysicsShapeList"')[2].partition('\n\t\t]\n')[0]
                if physics(path) != physics(previous):
                    raise RuntimeError(f"Unexpected physics definition change: {path.name}")
            if not unchanged:
                manifest["files"].append({"source":path.relative_to(ROOT).as_posix(),"path":relative})
    import_path.write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Staged {len(manifest['files'])} changed files; {len(spots)} spots and all collision hulls passed.",flush=True)


if __name__ == "__main__":
    main()
