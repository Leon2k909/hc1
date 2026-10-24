""" What stands round each of Cerro Blanco's grated trees: the ground's paint under it, and dressing pieces near. """
import sys
from pathlib import Path
import numpy as np
ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import cerroblanco_parts as P
calls = []
orig = P.tree
def record( m, e, n, path=f"{P.OAK}/tree_oak_medium_a.vmdl", scale=1.0, z=0.0, grate=True, trunk=9.0 ):
    if grate:
        calls.append( ( e, n, z, scale, path.rsplit( "/", 1 )[1] ) )
    return orig( m, e, n, path, scale, z, grate, trunk )
P.tree = record
import cerroblanco_map as C
models = C.build()
print( sorted( models ) )
for e, n, z, s, name in calls:
    under = []
    near = []
    for mname, model in models.items():
        for paint, items in model.polygons.items():
            for pts, normal in items:
                p = np.asarray( pts, float )
                lo, hi = p.min( 0 ), p.max( 0 )
                if normal[2] > 0.9 and lo[0] <= e <= hi[0] and lo[1] <= n <= hi[1] and abs( hi[2] - z ) < 8:
                    under.append( ( mname, paint, round( float( hi[2] ), 2 ) ) )
                elif paint != "cb_black" and hi[0] > e - 60 and lo[0] < e + 60 and hi[1] > n - 60 and lo[1] < n + 60 and lo[2] < z + 40 and hi[2] > z + 0.5:
                    near.append( ( mname, paint ) )
    print( f"tree {name} at ({e:.0f},{n:.0f},{z}) x{s}: under {sorted( set( under ) )}; within 60: {sorted( set( near ) )}" )
