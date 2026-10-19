"""Stage distant forest silhouettes using the landscape's existing growth rules.

The original ImageGen RGBA is sampled directly. Trees are visual-only cards
facing the town, batched by terrain sector; scale follows the vista's perspective.
This command writes staging files only. The native editor imports and saves them.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

# Python 3.13's WMI platform query can hang independently of this build. Opt in
# to its normal Win32 fallback for this process when that service is unresponsive.
if os.name == "nt" and os.environ.get("BELLTOWER_SKIP_WMI") == "1":
    import platform
    platform._wmi = None

import numba
import numpy as np
from scipy.spatial import cKDTree

import belltower_map as B
import belltower_vista as V
import belltower_vista_paint as P
import belltower_vista_props as Props
import belltower_quality_foliage as F
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "output/belltower/quality"
RESOURCE = "models/maps/belltower/forest"
MATERIAL = "materials/belltower/forest/forest_trees.vmat"
GRID = 85.0
MIN_REACH, MAX_REACH = 3500.0, 54000.0
SECTOR = 12000.0
# UV windows of the unmodified generated atlas, with V upward for OBJ.
# The generated columns are unequal; these follow the actual silhouettes.
RECTS = ((.006, .004, .553, .532), (.557, .004, .998, .532),
         (.006, .546, .553, .987), (.557, .546, .998, .987))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@numba.njit(parallel=True, cache=True)
def candidates():
    count = int(math.ceil((MAX_REACH + 2500) / GRID))
    width = count * 2
    out = np.full((width * width, P.CROWN_FIELDS), np.nan)
    for row in numba.prange(width):
        j = row - count
        for col in range(width):
            i = col - count
            h = P._h(i, j, 34017)
            e = (i + .12 + .76 * P._u(h, 1)) * GRID
            n = (j + .12 + .76 * P._u(h, 2)) * GRID
            d = V._town_offset(e, n)[0]
            if d < MIN_REACH or d > MAX_REACH:
                continue
            s, z, use = P._decide(e, n, V._GRADIENTS)
            kind, density = int(use[5]), use[6]
            # Only natural woodland, never olive/poplar planting rows or crops.
            if kind not in (P.OAK, P.HOLM, P.BEECH, P.WILLOW) or density <= 0:
                continue
            canopy = 1 - math.exp(-density * math.pi * P.TREES[kind, 0] ** 2)
            # Respect soft woodland margins; fade the outermost band into paint.
            keep = canopy * (1 - V._smooth(42000., MAX_REACH, d))
            if P._u(h, 3) > keep:
                continue
            size = .8 + .4 * P._u(h, 4)
            tall = .85 + .3 * P._u(h, 5)
            q = out[row * width + col]
            q[0], q[1], q[2] = e, n, z
            q[3] = P.TREES[kind, 0] * size / s
            q[4] = P.TREES[kind, 1] * tall / s
            q[5] = P.TREES[kind, 2] * tall / s
            q[6] = kind
            q[7:10] = P.TREE_COLOURS[kind]
            q[10], q[11] = P.TREES[kind, 3], P._u(h, 9) * 1000.
    return out


def write_sector(out, name, crowns):
    """Write compact batched cards without recomputing planar UVs per vertex.

    Each card faces the town centre. From the playable town its turn angle is
    small; a second crossing card otherwise exposes a bright seam on every tree.
    The OBJ uses shared atlas UVs and one upward canopy normal.
    """
    folder=out / "Assets" / RESOURCE
    folder.mkdir(parents=True,exist_ok=True)
    lines=["# Tools/belltower_quality_forest.py",f"mtllib {name}.mtl",f"o {name}","vn 0 1 0"]
    for u0,top,u1,bottom in RECTS:
        for flip in (False,True):
            coords=[(u0,1-bottom),(u1,1-bottom),(u1,1-top),(u0,1-top)]
            if flip:
                coords=[(u0+u1-u,v) for u,v in coords]
            lines.extend(f"vt {u:.5f} {v:.5f}" for u,v in coords)
    lines.append("usemtl forest")
    faces=[]
    for i,c in enumerate(crowns):
        e,n,z,radius,mid,half,kind=c[:7]
        seed=c[11]
        variant=1 if kind==P.BEECH else (0 if seed%3<1 else 3)
        flip=seed%2<1
        height=mid+half
        z-=height*.025
        heading=math.atan2(n-V.CENTRE[1],e-V.CENTRE[0])+math.pi/2
        de,dn=math.cos(heading)*radius,math.sin(heading)*radius
        points=((e-de,n-dn,z),(e+de,n+dn,z),(e+de,n+dn,z+height),(e-de,n-dn,z+height))
        # map_kit's plan -> world -> OBJ transform, exactly (-east, z, north).
        lines.extend(f"v {-pe:.3f} {pz:.3f} {pn:.3f}" for pe,pn,pz in points)
        vi=i*4+1
        ti=(variant*2+int(flip))*4+1
        faces.append(f"f {vi}/{ti}/1 {vi+1}/{ti+1}/1 {vi+2}/{ti+2}/1")
        faces.append(f"f {vi}/{ti}/1 {vi+2}/{ti+2}/1 {vi+3}/{ti+3}/1")
    K.write_text(folder/f"{name}.obj","\n".join(lines+faces)+"\n")
    K.write_text(folder/f"{name}.mtl","newmtl forest\nKd 1 1 1\nd 1\n")
    metadata=K.Model()
    metadata.polygons["forest"]=[]  # Material declaration only; OBJ is already written.
    metadata.material_overrides["forest"]=MATERIAL
    K.write_vmdl(folder/f"{name}.vmdl",RESOURCE,name,metadata)
    return len(faces)


def main():
    global RESOURCE, MATERIAL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=QUALITY / "forest-v1-staging")
    parser.add_argument("--budget", type=int, default=320000)
    parser.add_argument("--reuse-crowns", action="store_true", help="Rebuild only geometry from this staging directory's saved placement")
    parser.add_argument("--near-trees", type=Path, default=ROOT / "Sources/Belltower/landscape/trees.json",
                        help="Validated companion near-tree staging group (defaults to current accepted group)")
    parser.add_argument("--resource", default=RESOURCE,
                        help="Model resource prefix; use a separate parcel trial folder for unreleased models")
    parser.add_argument("--material", default=MATERIAL,
                        help="Material resource path for each new sector model")
    args = parser.parse_args()
    RESOURCE = args.resource
    MATERIAL = args.material
    out = args.out.resolve()
    if not out.is_relative_to(QUALITY):
        raise ValueError("Use a staging directory inside output/belltower/quality")
    if not RESOURCE.startswith("models/maps/belltower/forest/") and RESOURCE != "models/maps/belltower/forest":
        raise ValueError("Forest resource must be inside the Belltower forest asset folder")
    if not MATERIAL.startswith("materials/belltower/") or not MATERIAL.endswith(".vmat"):
        raise ValueError("Invalid Belltower forest material path")
    near_path = args.near_trees.resolve()
    if not near_path.is_relative_to(ROOT):
        raise ValueError("Near-tree source must be inside the project")
    out.mkdir(parents=True, exist_ok=True)
    numba.set_num_threads(min(4, numba.get_num_threads()))
    if args.reuse_crowns:
        crowns = np.load(out / "crowns.npy")
    else:
        crowns = candidates()
        crowns = crowns[np.isfinite(crowns[:,0])]
        print(f"Woodland candidates: {len(crowns)}", flush=True)
        world = Props.build()
        crowns = F.clear_props(crowns, world)
        near = json.loads(near_path.read_text())
        positions = []
        for obj in near["Children"]:
            x,y,z = map(float, obj["Position"].split(","))
            positions.append((-y,x))
        distances, _ = cKDTree(positions).query(crowns[:,:2])
        crowns = crowns[distances > crowns[:,3] * 1.25 + 35]
        if len(crowns) > args.budget:
            # A deterministic, spatially even budget; no clustered truncation.
            order = np.argsort(crowns[:,11])[:args.budget]
            crowns = crowns[order]
        crowns[:,2] = world.ground(crowns[:,0], crowns[:,1])
    assert np.isfinite(crowns).all()
    np.save(out / "crowns.npy", crowns)
    groups = {}
    for crown in crowns:
        key = tuple(np.floor(crown[:2] / SECTOR).astype(int))
        groups.setdefault(key, []).append(crown)
    objects, triangles = [], 0
    for (x,y), group in sorted(groups.items()):
        name = f"belltower_forest_{x+8:02}_{y+8:02}"
        triangles += write_sector(out,name,group)
        key = f"landscape/forest/{x}/{y}"
        renderer = K.component(B.ids,"Sandbox.ModelRenderer",key+"/renderer",
            Model=f"{RESOURCE}/{name}.vmdl",RenderType="Off",Tint="1,1,1,1",CreateAttachments=False)
        objects.append(K.game_object(B.ids,f"Woodland {x}, {y}",key,components=[renderer]))
        print(f"Staged {name}: {len(group)} trees",flush=True)
    group = K.game_object(B.ids,"Distant woodland","landscape/forest",children=objects)
    (out / "forest.json").write_text(json.dumps(group,indent=2)+"\n")
    if RESOURCE == "models/maps/belltower/forest":
        # Legacy accepted forest build includes its established material/shader.
        material_dir = out / "Assets/materials/belltower/forest"
        material_dir.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT / "Sources/Belltower/generated/forest-trees-v1.png",material_dir / "forest-trees-v1.png")
        (material_dir / "forest_trees.vmat").write_text('''"Layer0"
{
    shader "shaders/belltower_forest.shader"
    TexturePlants "materials/belltower/forest/forest-trees-v1.png"
    F_ALPHA_TEST "1"
    g_flAlphaTestReference "0.35"
    g_flAntiAliasedEdgeStrength "1"
    g_flCanopyBrightness "1.0"
    CanopyColorB "materials/belltower/vista/vista_b_color.jpg"
    CanopyNormalB "materials/belltower/vista/vista_b_normal.jpg"
    CanopyColorC "materials/belltower/vista/vista_c_color.jpg"
    CanopyNormalC "materials/belltower/vista/vista_c_normal.jpg"
    CanopyColorD "materials/belltower/vista/vista_d_color.jpg"
    CanopyNormalD "materials/belltower/vista/vista_d_normal.jpg"
}
''')
        shader_dir = out / "Assets/shaders"
        shader_dir.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT / "Sources/Belltower/shaders/belltower_forest.shader",shader_dir / "belltower_forest.shader")
    imports = []
    for path in sorted((out / "Assets").rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(out / "Assets").as_posix()
        destination = ROOT / "Assets" / relative
        imports.append(dict(path=relative,source=path.relative_to(ROOT).as_posix(),sha256=sha(path),
                            expected_sha256=sha(destination) if destination.is_file() else None))
    (out / "import.json").write_text(json.dumps(imports,indent=2)+"\n")
    manifest = dict(generator="Tools/belltower_quality_forest.py",generator_sha256=sha(Path(__file__)),
        shader_sha256=sha(ROOT / "Assets/shaders/belltower_forest.shader"),
        atlas_sha256=sha(ROOT / "Sources/Belltower/generated/forest-trees-v1.png"),trees=len(crowns),triangles=triangles,
        sectors=len(objects),colliders=0,shadow_casting=False,minimum_distance=MIN_REACH,
        maximum_distance=MAX_REACH,source_group_sha256=sha(out / "forest.json"),
        near_tree_group=near_path.relative_to(ROOT).as_posix(),near_tree_sha256=sha(near_path),
        resource=RESOURCE,material=MATERIAL)
    (out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2),flush=True)


if __name__ == "__main__":
    main()
