"""Belltower: does removing the lorries change any authored gameplay check? Removing collision only opens space, so
the spot room/floor and reach checks can only fail if a spot stands on a lorry. A Retakes sightline (red to blue, eyes
at 64 or 46) can only open if it passes through one of the lorries' collision boxes: tested exactly (slab method)."""
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import belltower_map as BM

boxes = []
for east in (False, True):
    m = K.Model(); BM.lorry(m, (-900, 1290), 8)
    if east: m = m.mirrored(BM.EAST_PAINTS)
    boxes += [(np.asarray(c, float), [K.normalise(a) for a in axes], np.asarray(s, float) / 2) for c, axes, s, _ in m.boxes]

def hits(p0, p1, box, pad=0.0):
    c, axes, h = box
    d = np.asarray(p1, float) - p0; o = np.asarray(p0, float) - c
    t0, t1 = 0.0, 1.0
    for a, half in zip(axes, h + pad):
        od, dd = np.dot(o, a), np.dot(d, a)
        if abs(dd) < 1e-9:
            if abs(od) > half: return False
            continue
        ta, tb = sorted(((-half - od) / dd, (half - od) / dd))
        t0, t1 = max(t0, ta), min(t1, tb)
        if t0 > t1: return False
    return True

crossing = 0
for site, roles in BM.RETAKES.items():
    for r in roles["planter"] + roles["defender"]:
        for b in roles["attacker"]:
            for hr in (64, 46):
                for hb in (64, 46):
                    if any(hits((r[0], r[1], r[2] + hr), (b[0], b[1], b[2] + hb), box) for box in boxes):
                        crossing += 1; print("lorry blocks", site, r, b, hr, hb)
on = [name for name, p in BM.all_spots()
      if any(hits((p[0], p[1], p[2] + 1), (p[0], p[1], p[2] + 72), box, pad=16.0) for box in boxes)]
print({"RetakesSightlinesThroughLorries": crossing, "SpotsOnOrBesideLorries": on})
