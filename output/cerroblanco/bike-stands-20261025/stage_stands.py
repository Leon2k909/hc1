"""Swap Cerro Blanco's six bike hoops for the Sheffield stands (cerroblanco_fitout.bike_stand) in the installed
cerroblanco_fitout_fine.obj, without rebuilding the map.

Builds the old hoops (the ten six-sided rods each, as cerroblanco_fitout drew them until 2026-10-25) and the new stands
alone, configured and written the way cerroblanco_map.build() writes the fit-out (cerroblanco_map.configure, then
cerroblanco_fitout.point_quality, under the model's own name for its UV offset), finds every old face in the installed
OBJ (material, and each corner's position, UV and normal text), drops them and appends the new ones. Every other line
stays. The stands use cb_steel, which the model already has, and have no collision, so the .mtl and .vmdl stay.

    python stage_stands.py      stage into stage/ and write publish.json for Sources/Railhead/editor/import-staged.cs.txt
"""
import hashlib
import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert( 0, str( ROOT / "Tools" ) )
sys.path.insert( 0, str( ROOT / "output/railhead/cars-bench-20261025" ) )

import map_kit as K                     # noqa: E402
import cerroblanco_map as CBM           # noqa: E402
import cerroblanco_fitout as F          # noqa: E402
import cerroblanco_parts as P           # noqa: E402
import splice as SP                     # noqa: E402  (the Railhead splice's OBJ reading and face swapping)

NAME = "cerroblanco_fitout_fine"
REL = f"models/maps/cerroblanco/{NAME}.obj"


def old_hoops( m ):
    for k in range( 6 ):
        e, n = 880.0 + 32 * k, 1640.0
        pts = [ ( e, n, 0.0 ) ] + [ ( e, n + 9 - 9 * math.cos( math.pi * j / 8 ), 26 + 9 * math.sin( math.pi * j / 8 ) )
                                    for j in range( 9 ) ] + [ ( e, n + 18, 0.0 ) ]
        for a, b in zip( pts, pts[1:] ):
            P.rod( m, a, b, 1.0, P.STEEL, sides=6 )


def plated_stands( m ):
    """ The stands as first published on 2026-10-25, with a base plate and three bolts at each foot. """
    for k in range( 6 ):
        e, n = 1040.0 - F.STAND_PITCH * ( 5 - k ), 1649.0
        F.bike_stand( m, e, n )
        for foot in ( n - F.STAND_LENGTH / 2, n + F.STAND_LENGTH / 2 ):
            P.rod( m, ( e, foot, 0.0 ), ( e, foot, 0.3 ), 2.4, P.STEEL, sides=20, caps=True )
            for j in range( 3 ):
                a = math.pi / 2 + 2 * math.pi * j / 3
                bolt = ( e + 1.75 * math.cos( a ), foot + 1.75 * math.sin( a ) )
                P.rod( m, ( *bolt, 0.3 ), ( *bolt, 0.55 ), 0.3, P.STEEL, sides=6, caps=True )


def new_stands( m ):
    for k in range( 6 ):
        F.bike_stand( m, 1040.0 - F.STAND_PITCH * ( 5 - k ), 1649.0 )


def written_faces( draw ):
    m = K.Model()
    draw( m )
    CBM.configure( m )
    F.point_quality( m )
    with tempfile.TemporaryDirectory() as tmp:
        K.write_model( Path( tmp ), "models/maps/cerroblanco", NAME, m )
        return Counter( f for f, _ in SP.faces( Path( tmp ) / f"{NAME}.obj" )[1] )


def main():
    installed = ROOT / "Assets" / REL
    have = Counter( f for f, _ in SP.faces( installed )[1] )
    added = written_faces( new_stands )
    # Whichever earlier version is installed: the old hoops, or the plated stands.
    for draw in ( old_hoops, plated_stands ):
        removed = written_faces( draw )
        if not removed - have:
            print( f"installed: {draw.__name__}" )
            break
    else:
        raise SystemExit( "neither earlier version is in the installed OBJ" )
    text = SP._splice_obj( REL, installed, removed, added )
    out = HERE / "stage" / REL
    out.parent.mkdir( parents=True, exist_ok=True )
    out.write_text( text, encoding="utf-8", newline="" )
    sha = lambda p: hashlib.sha256( Path( p ).read_bytes() ).hexdigest()
    publish = { "files": { REL: { "source": out.relative_to( ROOT ).as_posix(), "before": sha( installed ), "after": sha( out ) } } }
    ( HERE / "publish.json" ).write_text( json.dumps( publish, indent=1 ), encoding="utf-8" )
    print( f"{REL}: {sum( removed.values() )} faces out, {sum( added.values() )} in; publish.json written" )


if __name__ == "__main__":
    main()
