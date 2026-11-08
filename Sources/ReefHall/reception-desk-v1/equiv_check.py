"""Offline proof that the generator hook and the in-place cut of the lobby OBJ say the same thing.

Builds ONLY the lobby room with Tools/reefhall_map.py (nothing is written under Assets, no scene, no editor), once with
the reception-desk flag off and once on, writes both OBJs to a scratch folder, and compares face by face (material, the
three corners' positions, UVs and normals; order and index numbers ignored):

    flag off  ==  old/reefhall_lobby_original.obj        (the lobby model as it was before the trial)
    flag on   ==  stage/reefhall_lobby_without_desk.obj  (what install.py puts in Assets/models/maps/reefhall)
    off - on  ==  the 204 triangles of old/old_desk.obj

    python equiv_check.py [scratch-folder]
"""
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Tools"))

import numpy as np

import map_kit as K
import reefhall_map as R
import reefhall_reception_desk as RD


def lobby_obj(flag, folder):
    RD.ENABLED = flag
    k = [name for name, _, _ in R.ROOMS].index("lobby")
    model, inside, lights = R.build_mirrored(R.lobby, np.random.default_rng(1000 + k), [])
    for m in (model, inside):
        R.configure(m)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "reefhall_lobby.obj"
    K.write_obj(path, model, "reefhall_lobby")
    return path, model


def faces(path, full=True):
    """ A Counter of (material, ((v, vt, vn) x 3)) with positions to 3 decimals, UVs to 4, normals to 3. """
    v, vt, vn = [], [], []
    mat = None
    out = Counter()
    for line in open(path, encoding="utf-8"):
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            v.append(tuple(round(float(x), 3) + 0.0 for x in p[1:4]))
        elif p[0] == "vt":
            vt.append(tuple(round(float(x), 4) + 0.0 for x in p[1:3]))
        elif p[0] == "vn":
            vn.append(tuple(round(float(x), 3) + 0.0 for x in p[1:4]))
        elif p[0] == "usemtl":
            mat = p[1]
        elif p[0] == "f":
            corners = []
            for tok in p[1:]:
                a = tok.split("/")
                corners.append((v[int(a[0]) - 1], vt[int(a[1]) - 1], vn[int(a[2]) - 1]) if full else (v[int(a[0]) - 1],))
            # a triangle is the same triangle from any corner: start at the smallest, keep the winding
            i = corners.index(min(corners))
            out[(mat, tuple(corners[i:] + corners[:i]))] += 1
    return out


def report(label, a, b):
    only_a, only_b = a - b, b - a
    ok = not only_a and not only_b
    print(f"{'OK  ' if ok else 'DIFF'} {label}: {sum(a.values())} vs {sum(b.values())} faces; only left {sum(only_a.values())}, only right {sum(only_b.values())}")
    if not ok:
        for name, side in (("left", only_a), ("right", only_b)):
            for (mat, corners), n in list(side.items())[:3]:
                print(f"     only {name}: {mat} {[c[0] for c in corners]} x{n}")
    return ok


def main():
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="rd_equiv_"))
    off, model_off = lobby_obj(False, scratch / "off")
    on, model_on = lobby_obj(True, scratch / "on")
    RD.ENABLED = True
    print("scratch:", scratch)
    print("collision, flag off vs on: hulls", len(model_off.hulls), len(model_on.hulls), "| boxes", len(model_off.boxes), len(model_on.boxes))
    hulls_same = [(np.round(np.array(p), 6).tolist(), s) for p, s in model_off.hulls] == [(np.round(np.array(p), 6).tolist(), s) for p, s in model_on.hulls]
    print("collision hulls identical:", hulls_same)
    paints_off, paints_on = sorted(p for p, v in model_off.polygons.items() if v), sorted(p for p, v in model_on.polygons.items() if v)
    print("paints that lose all their faces in the lobby:", sorted(set(paints_off) - set(paints_on)))

    original = faces(HERE / "old" / "reefhall_lobby_original.obj")
    staged = faces(HERE / "stage" / "reefhall_lobby_without_desk.obj")
    f_off, f_on = faces(off), faces(on)
    ok = report("flag off  vs  original lobby OBJ", f_off, original)
    ok &= report("flag on   vs  staged cut        ", f_on, staged)
    removed = f_off - f_on
    old_desk = faces(HERE / "old" / "old_desk.obj", full=False)
    removed_pos = Counter({(m, tuple((c[0],) for c in corners)): n for (m, corners), n in removed.items()})
    ok &= report("(off - on) positions  vs  old_desk.obj", removed_pos, old_desk)
    print("ALL EQUIVALENT" if ok and hulls_same else "NOT EQUIVALENT")
    return 0 if ok and hulls_same else 1


if __name__ == "__main__":
    raise SystemExit(main())
