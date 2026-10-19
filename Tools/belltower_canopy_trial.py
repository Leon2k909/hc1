"""Stage an irregular painted-canopy candidate without changing the accepted landscape.

The existing growth rules, crown positions, terrain and shadow placement are
reused. Only crown silhouette and leaf-cluster shading are replaced in memory.
Use --swatch for a small construction comparison, or --zones bc for zone maps.
All output is restricted to output/belltower/quality.
"""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

platform._wmi = None
import numba
import numpy as np
from PIL import Image
import belltower_vista as V
import belltower_vista_paint as P

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / 'output/belltower/quality'


@numba.njit(cache=True, fastmath=True)
def clustered_tops(crowns, e0, n0, we, wn, w, top, ccol, cov, cid, grads):
    """Paint bounded, asymmetric crowns with branch-sized foliage clusters."""
    rows, cols = top.shape
    for k in range(crowns.shape[0]):
        if crowns[k, 7] < 0:
            continue
        ce, cn, zg, a, hc, bb = crowns[k, :6]
        extent = a*1.3
        c0, c1 = max(int((ce-extent-e0)/we)-1, 0), min(int((ce+extent-e0)/we)+1, cols-1)
        r0, r1 = max(int((n0-cn-extent)/wn)-1, 0), min(int((n0-cn+extent)/wn)+1, rows-1)
        seed = np.int64(crowns[k, 11])
        angle = seed * 2.399963229728653
        ca, sa = math.cos(angle), math.sin(angle)
        aspect = math.sqrt(.75 + .50 * P._u(seed, 913))
        axis_u, axis_v = a/aspect, a*aspect
        detail = V._smooth(2.0, 7.0, a/w)
        for row in range(r0, r1+1):
            dy = n0-row*wn-cn
            for col in range(c0, c1+1):
                dx = e0+col*we-ce
                u, v = (ca*dx+sa*dy)/axis_u, (-sa*dx+ca*dy)/axis_v
                # The same coordinates and seed are used in every zone. A crown
                # cannot acquire a different outline at a texture-zone seam.
                branch = V._gradient_noise(u*2.8, v*2.8, seed+17, grads)
                branch2 = V._gradient_noise(u*5.6+7.1, v*5.6-3.9, seed+23, grads)
                radius = min(max(1.0 + .10*branch + .05*branch2, .88), 1.12)
                rr = math.sqrt(u*u+v*v)
                coverage = min(max((radius-rr)*a/w+.5, 0.0), 1.0)
                if coverage <= 0:
                    continue
                rho = min(rr/max(radius, .1), 1.0)
                dome = math.sqrt(max(1.0-rho*rho, 0.0))
                hz = hc+bb*dome
                if cid[row, col] >= 0 and zg+hz <= top[row, col]:
                    continue
                # Rotate the elliptical crown normal back into world east/north.
                nx = ca*u/axis_u-sa*v/axis_v
                ny = sa*u/axis_u+ca*v/axis_v
                nz = dome/bb
                length = math.sqrt(nx*nx+ny*ny+nz*nz)
                nx, ny, nz = nx/length, ny/length, nz/length
                cluster_x = V._gradient_noise(u*6.0, v*6.0, seed+31, grads)
                cluster_y = V._gradient_noise(u*6.0+19.2, v*6.0-8.6, seed+37, grads)
                nx += .65*detail*cluster_x
                ny += .65*detail*cluster_y
                length = math.sqrt(nx*nx+ny*ny+nz*nz)
                nx, ny, nz = nx/length, ny/length, nz/length
                lit = max(nx*V.SUN[0]+ny*V.SUN[1]+nz*V.SUN[2], 0.0)
                sky = .75+.25*nz
                fine = V._gradient_noise(u*13, v*13, seed+43, grads)
                grain = 1.0+detail*(.28*cluster_x+.12*cluster_y+.10*fine)
                for c in range(3):
                    shade = min((P.AMBIENT[c]*sky+P.SUN_RGB[c]*P.LEAF_SUN*lit)/P.FLAT_LIT[c], P.SHADE_MAX)*grain
                    ccol[row, col, c] = ccol[row, col, c]*(1-coverage)+crowns[k, 7+c]*shade*coverage
                cov[row, col] = 1-(1-cov[row, col])*(1-coverage)
                if coverage >= .5:
                    top[row, col], cid[row, col] = zg+hz, k


def swatch_crowns():
    """The same small, overlapping grove for construction and diagnostic views."""
    rng = np.random.default_rng(814)
    crowns = []
    for row in range(5):
        for col in range(5):
            e, n = (col+.6)*290+rng.uniform(-50, 50), (row+.6)*290+rng.uniform(-50, 50)
            radius = rng.uniform(140, 220)
            crowns.append([e, n, 0, radius, radius*1.5, radius*.8, P.OAK,
                           *(P.TREE_COLOURS[P.OAK]*rng.uniform(.85, 1.15)), .88, rng.integers(0, 1000)])
    return np.asarray(crowns, np.float64)


def swatch(out, painter=clustered_tops, style='clustered'):
    """Compare the exact old/new crown painters with identical tree inputs."""
    size, span = 768, 1600.0
    crowns = swatch_crowns()
    records = []
    for name, painter in [('accepted', P._tops), (style, painter)]:
        top, cov = np.zeros((size, size)), np.zeros((size, size))
        color = np.zeros((size, size, 3))
        cid = np.full((size, size), -1, np.int64)
        step = span/(size-1)
        painter(crowns, 0, span, step, step, step, top, color, cov, cid, V._GRADIENTS)
        shadow = np.zeros_like(top)
        P._shadows(crowns, 0, span, step, step, step, top, cid, shadow)
        ground = np.asarray(P.WOOD_FLOOR)
        result = (color+ground*(1-cov[..., None]))*(1-shadow[..., None]*(1-P.SHADOW_TINT))
        assert np.isfinite(result).all() and cov.min()>=0 and cov.max()<=1
        Image.fromarray(P.srgb8(result)).save(out/(name+'.png'))
        records.append({'name': name, 'coverage': float(cov.mean()), 'crown_inputs_sha256': hashlib.sha256(crowns.tobytes()).hexdigest()})
    assert abs(records[0]['coverage']-records[1]['coverage']) < .04, 'Crown style must preserve overall canopy cover'
    (out/'swatch.json').write_text(json.dumps({'kind':'offline albedo construction swatch; not an engine capture', 'variants':records}, indent=2)+'\n')


def main(painter=clustered_tops, style='clustered', extra_sources=()):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--size', default=1024, type=int, choices=(512, 1024, 2048, 4096))
    parser.add_argument('--zones', default='')
    parser.add_argument('--swatch', action='store_true')
    parser.add_argument('--baseline', action='store_true', help='Render the accepted crown style at the same resolution for comparison')
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(QUALITY.resolve()) or out==QUALITY.resolve():
        raise ValueError('Canopy trials must stay in a separate quality-output directory')
    if any(zone not in 'abcd' for zone in args.zones) or not (args.zones or args.swatch):
        raise ValueError('Select --swatch or valid --zones')
    out.mkdir(parents=True, exist_ok=True)
    numba.set_num_threads(min(2, numba.get_num_threads()))
    if args.swatch:
        swatch(out, painter, style)
    previous = P._tops
    try:
        P._tops = previous if args.baseline else painter
        inner = 0.0
        for zone, margin in P.ZONES:
            if zone in args.zones:
                colour, kind, normal = P.paint_zone(zone, margin, inner, args.size)
                P.write_zone(out, zone, colour, kind, normal)
            inner = margin*(1-P.ZONE_BLEND)
    finally:
        P._tops = previous
    sources = [Path(__file__), Path(P.__file__), Path(V.__file__), *extra_sources]
    (out/'trial.json').write_text(json.dumps({
        'state':'offline trial; native review pending', 'style':'accepted' if args.baseline else style, 'zones':args.zones, 'size':args.size,
        'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'scope':('Natural broadleaf crowns use the unchanged generated atlas and are layered by summit height; '
                 'planted-tree painting, placement, terrain and shadow algorithm reused.') if style=='photographic' and not args.baseline else
                'Crown silhouette and foliage-cluster shading only; placement, terrain and shadow algorithm reused.',
        'limitation':'Existing ellipsoid shadows are approximate for the revised irregular crown edges.',
    }, indent=2)+'\n')
    print('Canopy trial written to '+str(out), flush=True)


if __name__=='__main__':
    main()
