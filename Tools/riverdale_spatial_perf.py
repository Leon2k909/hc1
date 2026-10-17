"""Conservative frustum-culling estimate for Riverdale's staged forest sectors.

    python Tools/riverdale_spatial_perf.py --stage output/riverdale/aaa/spatial-stage

Uses each mesh's AABB rather than culling individual triangles, as a coarse engine mesh culler
would. Ignores wall occlusion, shadows, transparency and GPU work. This predicts the fraction
of forest triangles eligible for frustum rejection, not a measured frame-time improvement.
"""
import argparse
import itertools
import math
from pathlib import Path

import numpy as np

import riverdale_map as R


def bounds( obj ):
    lo = np.array( ( math.inf, math.inf, math.inf ) )
    hi = -lo.copy()
    triangles = 0
    with obj.open( encoding="utf-8" ) as stream:
        for line in stream:
            if line.startswith( "v " ):
                _, x, y, z = line.split()
                plan = np.array( ( -float( x ), float( z ), float( y ) ) )
                lo = np.minimum( lo, plan )
                hi = np.maximum( hi, plan )
            elif line.startswith( "f " ):
                triangles += 1
    if triangles <= 0 or not np.all( np.isfinite( lo ) ):
        raise ValueError( f"No valid triangles in {obj}" )
    return lo, hi, triangles


def in_view( b, eye, target, fov, aspect=16 / 9 ):
    lo, hi, _ = b
    points = np.array( list( itertools.product( *zip( lo, hi ) ) ) )
    forward = np.array( target, float ) - eye
    forward /= np.linalg.norm( forward )
    right = np.cross( forward, ( 0, 0, 1 ) )
    right /= np.linalg.norm( right )
    up = np.cross( right, forward )
    rays = points - eye
    depth = rays @ forward
    x = rays @ right
    y = rays @ up
    tanx = math.tan( math.radians( fov / 2 ) )
    tany = tanx / aspect
    # A volume entirely beyond any one frustum plane is invisible; this is conservative
    # for boxes crossing several planes, which can be reported visible despite being outside.
    return bool( np.max( depth ) > 0 and np.min( x - depth * tanx ) <= 0 and
                 np.max( x + depth * tanx ) >= 0 and np.min( y - depth * tany ) <= 0 and
                 np.max( y + depth * tany ) >= 0 )


def main():
    ap = argparse.ArgumentParser( description=__doc__ )
    ap.add_argument( "--stage", type=Path, required=True )
    args = ap.parse_args()
    base = args.stage.resolve() / "models/maps/riverdale"
    sectors = args.stage.resolve() / "models/maps/riverdale_sectors"
    originals = [ bounds( base / f"{name}.obj" ) for name in R.TREE_SOURCE_NAMES ]
    slices = [ bounds( p ) for p in sorted( sectors.glob( "riverdale_backdrop_trees*sector*.obj" ) ) ]
    assert len( slices ) == 16
    assert sum( v[2] for v in originals ) == sum( v[2] for v in slices )
    for name, eye, target, fov in R.VIEWS:
        eye = np.array( eye, float )
        n0 = sum( v[2] for v in originals if in_view( v, eye, target, fov ) )
        n1 = sum( v[2] for v in slices if in_view( v, eye, target, fov ) )
        print( f"{name:16} unsplit {n0:>7,d} tr  sectorised {n1:>7,d} tr  "
               f"{(100 * (n0-n1) / n0 if n0 else 0):5.1f}% rejected, "
               f"{sum(in_view(v,eye,target,fov) for v in slices)} of {len(slices)} sectors visible" )


if __name__ == "__main__":
    main()
