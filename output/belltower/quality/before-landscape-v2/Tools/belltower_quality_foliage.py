"""Stage dimensional trees from the vista painter's deterministic planting plan.

The existing field, road, yard and building layout decides where trees belong.
This produces scene data only; the editor owns the final scene write. Native
models supply automatic LODs, and distant trees use the landscape's baked shadows.
"""
import json
import math
from pathlib import Path

import numba
import numpy as np
from scipy.spatial import cKDTree

import belltower_map as B
import belltower_vista as V
import belltower_vista_paint as P
import belltower_vista_props as Props

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Sources/Belltower/landscape"
REACH = 14000.0
MODELS = ("tree_oak_medium_a", "tree_oak_small_a", "tree_oak_dry_medium_a")
BOUNDS = ((610.15, 703.73), (303.83, 391.94), (610.15, 703.73))


def candidates():
    # This is a coordinate grid for candidate bounds, never an image or texture.
    es, ns = P.zone_grid(REACH, 256)
    grid = np.zeros((len(ns), len(es)))
    ge, gn = np.meshgrid(es, ns)
    inside = V.town_distance(ge, gn) <= REACH
    pe, pn, _ = V.apparent(ge[inside], gn[inside])
    all_crowns = []
    for layer in (0, 1):
        g = float(P.LAYER_CELL[layer])
        i0, i1 = math.floor(pe.min()/g)-2, math.ceil(pe.max()/g)+2
        j0, j1 = math.floor(pn.min()/g)-2, math.ceil(pn.max()/g)+2
        for j in range(j0, j1, 128):
            block = np.empty((min(128, j1-j), i1-i0, P.CROWN_FIELDS))
            P._candidates(layer, g, i0, j, block, 150, REACH, grid,
                          es[0], ns[0], es[1]-es[0], ns[0]-ns[1], 8.0, V._GRADIENTS)
            all_crowns.append(block[np.isfinite(block[:, :, 0])])
    return np.concatenate(all_crowns)


def clear_props(crowns, world):
    boxes, existing, yards, roads = world.paint_data()
    quads = [b[:8].reshape(4, 2) for b in boxes]
    quads += [np.asarray(outline) for _, outline in yards]
    centers = np.array([q.mean(axis=0) for q in quads])
    reaches = np.array([np.linalg.norm(q-c, axis=1).max() for q, c in zip(quads, centers)])
    tree = cKDTree(centers)
    prop_tree = cKDTree(existing[:, :2])
    segments = []
    for width, line in roads:
        for a, b in zip(line[:-1], line[1:]):
            a, b = np.asarray(a), np.asarray(b)
            segments.append((a, b, width*world.k_at(*((a+b)/2))))
    roads_a = np.array([s[0] for s in segments])
    roads_ab = np.array([s[1]-s[0] for s in segments])
    roads_w = np.array([s[2] for s in segments])
    roads_len2 = np.sum(roads_ab**2, axis=1).clip(1e-6)
    kept = []
    for crown in crowns:
        point, radius = crown[:2], crown[3]
        if any(P._quad_distance(point, quads[i]) < radius*.55+15
               for i in tree.query_ball_point(point, reaches.max()+radius)):
            continue
        dist, i = prop_tree.query(point)
        if dist < .8*(radius+existing[i, 3]):
            continue
        t = (np.sum((point-roads_a)*roads_ab, axis=1)/roads_len2).clip(0, 1)
        if np.any(np.linalg.norm(point-roads_a-t[:, None]*roads_ab, axis=1) < roads_w+radius*.45+18):
            continue
        kept.append(crown)
    return np.array(kept)


def choose(crowns):
    d = V.town_distance(crowns[:, 0], crowns[:, 1])
    kept, spatial = [], {}
    # Preserve coherent near woods and a thinner layer of distant silhouettes.
    for lower, upper, budget in ((150, 3000, 400), (3000, 7000, 550), (7000, REACH, 650)):
        indices = np.flatnonzero((d >= lower) & (d < upper))
        importance = crowns[indices, 3]/(d[indices]+800)*(0.8+.4*np.mod(crowns[indices, 11], 1))
        accepted = 0
        for i in indices[np.argsort(-importance)]:
            c = crowns[i]
            x, y = (np.floor(c[:2]/250)).astype(int)
            neighbors = [q for dx in range(-3, 4) for dy in range(-3, 4)
                         for q in spatial.get((x+dx, y+dy), [])]
            if any(np.linalg.norm(c[:2]-q[:2]) < .63*(c[3]+q[3]) for q in neighbors):
                continue
            kept.append(c)
            spatial.setdefault((x, y), []).append(c)
            accepted += 1
            if accepted == budget:
                break
    return np.array(kept)


def main():
    numba.set_num_threads(min(4, numba.get_num_threads()))
    crowns = candidates()
    print(f"Planting plan: {len(crowns)} candidates", flush=True)
    world = Props.build()
    crowns = clear_props(crowns, world)
    print(f"After roads, yards and buildings: {len(crowns)}", flush=True)
    crowns = choose(crowns)
    ground = world.ground(crowns[:, 0], crowns[:, 1])
    objects = []
    for i, (c, z) in enumerate(zip(crowns, ground)):
        e, n, _, radius, mid, half, kind = c[:7]
        seed = c[11]
        variant = 1 if kind in (P.OLIVE, P.WILLOW) or seed % 3 < 1 else (2 if seed % 11 < 1 else 0)
        width, height = BOUNDS[variant]
        xy = 2*radius/width
        zs = (mid+half)/height
        # Slender poplar rows stay slender; olives retain broad, low crowns.
        if kind == P.POPLAR:
            xy *= .72
        key = f"landscape/tree/{round(e, 2)}/{round(n, 2)}"
        component = B.K.component(B.ids, "Sandbox.ModelRenderer", key+"/renderer",
            Model=f"models/sbox_props/trees/oak/{MODELS[variant]}.vmdl",
            RenderType="On" if V.town_distance(e, n) < 1800 else "Off",
            Tint="1,1,1,1", CreateAttachments=False)
        objects.append(B.K.game_object(B.ids, "Hillside oak", key,
            position=(n,-e,z-2), rotation=B.K.angles_rotation(0,seed*137.508),
            scale=B.K.vec((xy,xy,zs)), components=[component]))
    root = B.K.game_object(B.ids, "Landscape trees", "landscape/trees", children=objects)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"trees.json").write_text(json.dumps(root, indent=2)+"\n", encoding="utf-8")
    (OUT/"manifest.json").write_text(json.dumps({"count":len(objects), "reach":REACH,
        "physics":False, "source":"belltower_vista_paint deterministic crowns",
        "models":list(MODELS), "runtime_shadows_within":1800,
        "packages":["facepunch.tree_oak_medium_a#288916","facepunch.tree_oak_small_a#288917",
                    "facepunch.treeoakdrymediuma#289352"]}, indent=2)+"\n")
    print(f"Staged {len(objects)} landscape trees; no collision changes.")


if __name__ == "__main__":
    main()
