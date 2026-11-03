"""Replace the railing kit's open sleeves with a closed T-fitting in the live map OBJs: python fix_fittings.py [--apply] <map/model> ...

The old fitting was a six-sided sleeve with no top under the rail. Back faces aren't drawn, so its open top read as a torn edge with
the room showing through it, under every rail. riverdale_parts._rail_fitting now draws a capped socket and a collar round the rail.
The map scripts aren't rerun, as they rewrite far more than this. Each post is found from its old sleeve in the live mesh, which gives
its position and height, and its rail's direction comes from the long sides of the rail's tube over it. Where the rail turns a corner
there's a cap and no collar. Everything else in the file is left alone. Originals go to output/.../rail-fittings/retired/.
"""
import itertools
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
sys.dont_write_bytecode = True
import map_kit as K  # noqa: E402
import riverdale_parts as P  # noqa: E402

WORK = ROOT / "output" / "asset-improvement-20261030" / "rail-fittings"
PAINTS = ("rv_yellow", "rv_steel", "oa_yellow", "oa_steel", "oa_dark")
SLEEVE_R = P.RAIL_POST + 0.32
SLEEVE_H, CONE_H = 2.2, 0.4


def read(path):
    text = open(path, encoding="utf-8", newline="").read()
    eol = "\r\n" if "\r\n" in text[:2000] else "\n"
    lines = text.split(eol)
    verts = []
    uvs = []
    faces = {}
    current = None
    for i, line in enumerate(lines):
        if line.startswith("v "):
            p = line.split()
            verts.append((-float(p[1]), float(p[3]), float(p[2])))  # OBJ (-e, z, n) to plan (e, n, z).
        elif line.startswith("vt "):
            uvs.append(line.split()[1:3])
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in PAINTS:
            t = line.split()[1:]
            if len(t) == 3:
                faces.setdefault(current, []).append((i, [int(x.split("/")[0]) - 1 for x in t]))
    return lines, eol, np.array(verts, float), np.array(uvs, float), faces


def measure_tile(lines, verts, uvs, removed):
    """Inches to one repeat of this paint's texture, from the old fitting's own edges, so the new one matches what's around it."""
    found = []
    for i in removed[:240]:
        tokens = [token.split("/") for token in lines[i].split()[1:]]
        for a, b in zip(tokens, tokens[1:] + tokens[:1]):
            inches = np.linalg.norm(verts[int(a[0]) - 1] - verts[int(b[0]) - 1])
            repeats = np.linalg.norm(uvs[int(a[1]) - 1] - uvs[int(b[1]) - 1])
            if inches > 0.5 and repeats > 1e-5:
                found.append(inches / repeats)
    return float(np.median(found))


def split_pair(points):
    """Two six-sided sleeves about two inches apart: each one's centre from its corners, or None. A corner of one can lie on the other's circle, so any circle through six or more counts, and two must cover all twelve."""
    corners = np.unique(points.round(3), axis=0)
    if len(corners) != 12:
        return None
    circles = []
    for a, b, c in itertools.combinations(range(12), 3):
        (ax, ay), (bx, by), (cx, cy) = corners[a], corners[b], corners[c]
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-6:
            continue
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
        centre = np.array((ux, uy))
        on = np.abs(np.linalg.norm(corners - centre, axis=1) - SLEEVE_R) < 0.03
        if on.sum() >= 6 and not any(np.linalg.norm(centre - other) < 0.05 for other, _ in circles):
            circles.append((centre, on))
    for (first, on_first), (second, on_second) in itertools.combinations(circles, 2):
        if (on_first | on_second).all():
            return first, second
    return None


def find_posts(verts, entries):
    """Each sleeve: twelve triangles 2.2 tall on a radius of 1.27, and the twelve of the cone below it. Where two rails end at one post
    there are two sleeves in one place, which become one fitting. Sleeves a few inches apart wait for a second pass, as they group wrongly until one has gone."""
    if not entries:
        return [], []
    index = np.array([f for _, f in entries])
    line_no = np.array([i for i, _ in entries])
    tris = verts[index]
    span = np.ptp(tris[:, :, 2], axis=1)
    high = tris[:, :, 2].max(1)
    centres = tris[:, :, :2].mean(1)
    sleeve = np.where(np.abs(span - SLEEVE_H) < 0.012)[0]
    cone = np.where(np.abs(span - CONE_H) < 0.012)[0]
    posts, remove = [], []
    if len(sleeve) == 0:
        return posts, remove
    tree = cKDTree(np.column_stack((centres[sleeve], high[sleeve] * 10)))
    seen = set()
    cone_tree = cKDTree(centres[cone]) if len(cone) else None
    for k in range(len(sleeve)):
        if k in seen:
            continue
        group = tree.query_ball_point(np.array((*centres[sleeve[k]], high[sleeve[k]] * 10)), 2.4)
        if len(group) % 12:
            # Part of a close pair can fall outside that reach. Look a little wider for all 24 of its sides.
            wider = tree.query_ball_point(np.array((*centres[sleeve[k]], high[sleeve[k]] * 10)), 4.6)
            if len(wider) != 24:
                seen.update(group)
                continue
            group = wider
        seen.update(group)
        pts = tris[sleeve[group]].reshape(-1, 3)
        centre = np.unique(pts[:, :2].round(3), axis=0).mean(0)
        if np.abs(np.linalg.norm(pts[:, :2] - centre, axis=1) - SLEEVE_R).max() > 0.03:
            pair = split_pair(pts[:, :2]) if len(group) == 24 else None
            if pair is None:
                continue
            top = float(pts[:, 2].max())
            base = [cone[j] for j in cone_tree.query_ball_point(centre, 3.6) if abs(high[cone[j]] - (top - SLEEVE_H)) < 0.012]
            if len(base) == 24:
                posts.extend((float(each[0]), float(each[1]), top + 0.8) for each in pair)
                remove.extend(line_no[sleeve[group]].tolist())
                remove.extend(line_no[base].tolist())
            continue
        top = float(pts[:, 2].max())
        below = []
        if cone_tree is not None:
            for j in cone_tree.query_ball_point(centre, 1.3):
                if abs(high[cone[j]] - (top - SLEEVE_H)) < 0.012:
                    below.append(cone[j])
        if len(below) != len(group):
            continue
        posts.append((float(centre[0]), float(centre[1]), top + 0.8))
        remove.extend(line_no[sleeve[group]].tolist())
        remove.extend(line_no[below].tolist())
    return posts, remove


def long_edges(verts, entries):
    """Every triangle edge over 1.5 in that isn't upright: a rail's long sides. Its bends are shorter than that, and posts stand upright."""
    index = np.array([f for _, f in entries])
    start = verts[index[:, [0, 1, 2]]].reshape(-1, 3)
    end = verts[index[:, [1, 2, 0]]].reshape(-1, 3)
    d = end - start
    length = np.linalg.norm(d, axis=1)
    keep = (length > 1.5) & (np.abs(d[:, 2]) < length * 0.9)
    return start[keep], d[keep], length[keep]


def rail_direction(edges, post):
    """The rail over this post, from the long sides of its tube, which pass one radius from the post's top. None where the rail bends away."""
    start, d, length = edges
    target = np.array(post)
    t = np.clip(((target - start) * d).sum(1) / (length * length), 0, 1)
    gap = np.linalg.norm(start + d * t[:, None] - target, axis=1)
    near = (gap > 0.7) & (gap < 1.25)
    if near.sum() < 4:
        return None
    dirs = d[near] / length[near][:, None]
    # All one way, whichever end each edge started from.
    dirs *= np.sign((dirs * dirs[0]).sum(1))[:, None]
    mean = dirs.mean(0)
    mean /= np.linalg.norm(mean)
    if (dirs * mean).sum(1).min() < math.cos(math.radians(25.0)):
        return None
    return mean


def patch(rel, apply):
    path = ROOT / "Assets" / "models" / "maps" / (rel + ".obj")
    lines, eol, verts, uvs, faces = read(path)
    counts = {tag: sum(1 for l in lines if l.startswith(tag + " ")) for tag in ("v", "vt", "vn")}
    model = K.Model()
    remove = set()
    report = {}
    for paint, entries in faces.items():
        edges = long_edges(verts, entries)
        posts, gone = find_posts(verts, entries)
        collars = 0
        tile = measure_tile(lines, verts, uvs, gone) if gone else None
        if tile:
            model.tile_overrides[paint] = tile
        for post in posts:
            direction = rail_direction(edges, post)
            collars += direction is not None
            P._rail_fitting(model, P.v(post[0], post[1], post[2] - 42.0), 42.0, paint, direction)
        remove.update(gone)
        if posts:
            report[paint] = dict(posts=len(posts), collars=int(collars), removed=len(gone), tile=round(tile, 2), sample=[[round(c, 1) for c in q] for q in posts[:: max(1, len(posts) // 6)]])
    if not remove:
        print(rel, "nothing to do", report, flush=True)
        return report
    temp = WORK / "new-fittings.obj"
    K.write_obj(temp, model, Path(rel).name)
    new = {"v": [], "vt": [], "vn": []}
    by_paint = {}
    current = None
    for line in open(temp, encoding="utf-8").read().split("\n"):
        tag = line.split(" ", 1)[0]
        if tag in new:
            new[tag].append(line)
        elif tag == "usemtl":
            current = line.split()[1]
        elif tag == "f":
            tokens = []
            for token in line.split()[1:]:
                a, b, c = (int(x) for x in token.split("/"))
                tokens.append(f"{a + counts['v']}/{b + counts['vt']}/{c + counts['vn']}")
            by_paint.setdefault(current, []).append("f " + " ".join(tokens))
    last = {tag: max(i for i, l in enumerate(lines) if l.startswith(tag + " ")) for tag in new}
    out = []
    for i, line in enumerate(lines):
        if i in remove:
            continue
        out.append(line)
        for tag in new:
            if i == last[tag]:
                out.extend(new[tag])
        if line.startswith("usemtl"):
            out.extend(by_paint.pop(line.split()[1], []))
    if by_paint:
        raise SystemExit(f"{rel}: no section for {list(by_paint)}")
    added = sum(1 for l in out if l.startswith("f ")) - sum(1 for l in lines if l.startswith("f "))
    print(rel, {k: {a: b for a, b in v.items() if a != "sample"} for k, v in report.items()}, "triangles", f"{added:+d}", flush=True)
    if apply:
        retired = WORK / "retired" / Path(rel).parent
        retired.mkdir(parents=True, exist_ok=True)
        if not (retired / path.name).exists():
            shutil.copy2(path, retired / path.name)
        incoming = str(path) + ".fitting-incoming"
        with open(incoming, "w", encoding="utf-8", newline="") as h:
            h.write(eol.join(out))
        # The editor can hold the file mapped for a moment while it compiles it.
        for attempt in range(60):
            try:
                os.replace(incoming, path)
                break
            except OSError:
                if attempt == 59:
                    raise
                time.sleep(2)
    return dict(report, added=added)


apply = "--apply" in sys.argv
names = [a for a in sys.argv[1:] if not a.startswith("--")]
WORK.mkdir(parents=True, exist_ok=True)
results = {name: patch(name, apply) for name in names}
print("APPLIED" if apply else "dry run, nothing written")
with open(WORK / ("applied.json" if apply else "dry-run.json"), "w") as h:
    json.dump(results, h, indent=1)
