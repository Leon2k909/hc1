"""
The footbridge's dressing as installed (or staged): every connected piece of railhead_dress_east/west.obj on the bridge
that cuts into the bridge's structure (railhead_station, built by the generator) or into another dressing piece.

    python output/railhead/bridge-bins/check_installed.py [dress dir]      (default: Assets/models/maps/railhead)

Pieces are faces sharing a vertex (by the OBJ's own v lines); each piece's box, shrunk by TOL, is tested face by face
(separating axes). A piece inside the structure's box but clear of its faces isn't reported.
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import railhead_station as S            # noqa: E402

INSTALLED = ROOT / "Assets/models/maps/railhead"
LO = np.array( ( -S.WALL_IN - 5.0, S.BRIDGE_N0 - 12.0, S.DECK_Z - 1.0 ) )
HI = np.array( ( S.WALL_IN + 5.0, S.BRIDGE_N1 + 12.0, S.BRIDGE_ROOF + 1.0 ) )
TOL = 0.05


def poly_hits_box( pts, lo, hi ):
    c, h = ( lo + hi ) / 2, ( hi - lo ) / 2
    p = pts - c
    axes = [ np.eye( 3 )[k] for k in range( 3 ) ]
    n = np.cross( pts[1] - pts[0], pts[2] - pts[0] )
    if np.linalg.norm( n ) > 1e-9:
        axes.append( n / np.linalg.norm( n ) )
    for k in range( len( pts ) ):
        e = pts[( k + 1 ) % len( pts )] - pts[k]
        for b in axes[:3]:
            x = np.cross( e, b )
            if np.linalg.norm( x ) > 1e-9:
                axes.append( x / np.linalg.norm( x ) )
    for a in axes:
        r = np.abs( a ) @ h
        d = p @ a
        if d.min() >= r - 1e-6 or d.max() <= -r + 1e-6:
            return False
    return True


def obj_pieces( path ):
    """ [ ( materials, faces ) ] of the OBJ's connected pieces on the bridge, in plan ( e, n, z ). """
    v, faces, paint = [], [], None
    with open( path, encoding="utf-8" ) as f:
        for line in f:
            if line.startswith( "v " ):
                a, b, c = ( float( x ) for x in line.split()[1:4] )
                v.append( ( -a, c, b ) )
            elif line.startswith( "usemtl " ):
                paint = line[7:].strip()
            elif line.startswith( "f " ):
                idx = [ int( corner.split( "/" )[0] ) - 1 for corner in line.split()[1:] ]
                p = np.array( [ v[i] for i in idx ] )
                if ( p.min( 0 ) >= LO ).all() and ( p.max( 0 ) <= HI ).all():
                    faces.append( ( paint, idx, p ) )
    parent = list( range( len( faces ) ) )

    def find( i ):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    by_vertex = {}
    for i, ( _, idx, p ) in enumerate( faces ):
        for q in p:
            j = by_vertex.setdefault( tuple( np.round( q, 2 ) ), i )
            a, b = find( i ), find( j )
            if a != b:
                parent[a] = b
    groups = defaultdict( list )
    for i in range( len( faces ) ):
        groups[find( i )].append( i )
    return [ ( sorted( { faces[i][0] for i in g } ), [ ( faces[i][0], faces[i][2] ) for i in g ] ) for g in groups.values() ]


def main():
    folder = Path( sys.argv[1] ) if len( sys.argv ) > 1 else INSTALLED
    east, _ = S.east_half()
    struct = []
    for model in ( east, east.mirrored() ):
        for paint, items in model.polygons.items():
            for points, _ in items:
                p = np.asarray( points, float )
                if ( p.max( 0 ) >= LO ).all() and ( p.min( 0 ) <= HI ).all():
                    struct.append( ( "S:" + paint, p ) )
    pieces = []
    for name in ( "railhead_dress_east", "railhead_dress_west" ):
        path = folder / f"{name}.obj" if ( folder / f"{name}.obj" ).is_file() else INSTALLED / f"{name}.obj"
        pieces += obj_pieces( path )
    faces = struct + [ ( "D:" + paint, p ) for k, ( _, fs ) in enumerate( pieces ) for paint, p in fs ]
    owner = [ -1 ] * len( struct ) + [ k for k, ( _, fs ) in enumerate( pieces ) for _ in fs ]
    lo = np.array( [ p.min( 0 ) for _, p in faces ] )
    hi = np.array( [ p.max( 0 ) for _, p in faces ] )
    problems = 0
    for k, ( paints, fs ) in enumerate( pieces ):
        pts = np.concatenate( [ p for _, p in fs ] )
        a, b = pts.min( 0 ) + TOL, pts.max( 0 ) - TOL
        if ( b <= a ).any() or paints == [ "dress_gum" ]:
            continue
        hits = defaultdict( int )
        for i in np.where( ~( ( hi < a ).any( 1 ) | ( lo > b ).any( 1 ) ) )[0]:
            if owner[i] != k and poly_hits_box( faces[i][1], a, b ):
                hits[faces[i][0]] += 1
        if hits:
            problems += 1
            m = pts.min( 0 ); x = pts.max( 0 )
            print( f"{'/'.join( paints )[:44]:44s} e {m[0]:7.1f}..{x[0]:7.1f} n {m[1]:7.1f}..{x[1]:7.1f} z {m[2]:6.1f}..{x[2]:6.1f}"
                   f"  cut by {dict( hits )}" )
    print( f"{len( pieces )} dressing pieces on the bridge, {problems} cut into" )


if __name__ == "__main__":
    main()
