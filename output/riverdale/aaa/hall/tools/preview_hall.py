"""
Flat previews of Riverdale's reactor hall alone (Tools/riverdale_hall.py's models, the detail ones too) from views of
its own, with railhead_preview's z-buffer, for checking shapes quickly.

    python output/riverdale/aaa/hall/tools/preview_hall.py [--out DIR] [--views name ...] [--size 960x540]

Textured paints take their colour from the staged materials (output/riverdale/aaa/hall/stage/materials/riverdale) when
Assets has none yet.
"""
import argparse
import sys
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import riverdale_map as M  # noqa: E402
import riverdale_hall as H  # noqa: E402
import riverdale_parts as P  # noqa: E402
import railhead_preview as PV  # noqa: E402

STAGE = ROOT / "output/riverdale/aaa/hall/stage/materials/riverdale"

# ( name, eye, target, horizontal fov ), plan coordinates.
VIEWS = [
    ( "hall_reference", ( -260, -150, 180 ), ( -40, 1400, 470 ), 88 ),
    ( "control_in", ( -600, 690, 352 ), ( -930, 1010, 335 ), 82 ),
    ( "control_back", ( -640, 1150, 350 ), ( -1000, 780, 330 ), 80 ),
    ( "control_out", ( -150, 520, 160 ), ( -760, 930, 370 ), 70 ),
    ( "crane", ( 350, 420, 640 ), ( 0, 900, 870 ), 85 ),
    ( "roof", ( 0, 300, 520 ), ( 0, 1300, 980 ), 90 ),
    ( "upper", ( -930, 1500, 350 ), ( 600, 900, 250 ), 80 ),
    ( "tanks", ( 260, -120, 110 ), ( 640, 80, 160 ), 75 ),
    ( "north_wall", ( 0, 1180, 110 ), ( 0, 2000, 260 ), 88 ),
    ( "stair", ( -420, -60, 90 ), ( -780, 420, 160 ), 78 ),
    ( "deck_west", ( -150, 200, 70 ), ( -1000, 300, 90 ), 85 ),
    ( "pool_edge", ( -150, 250, 90 ), ( 100, 900, -100 ), 85 ),
    ( "mast", ( -250, 600, 300 ), ( 70, 900, 500 ), 80 ),
    ( "exterior_south", ( 600, -1100, 160 ), ( 0, -240, 500 ), 80 ),
]


def colours():
    M.preview_setup()
    for paint in H.EXTRA_SURFACES:
        path = STAGE / f"{paint}_color.jpg"
        if path.exists():
            small = Image.open( path ).convert( "RGB" ).resize( ( 64, 64 ) )
            PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
    for paint, ( rgb, _, _, glow ) in H.EXTRA_PAINTS.items():
        PV._colours[paint] = np.array( rgb ) / 255.0
        if glow:
            PV.GLOWING.add( paint )
    for paint in ( "rv_lamp_cool", "rv_lamp_warm", "rv_screens", "rv_beacon" ):
        PV.GLOWING.add( paint )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument( "--out", default=str( ROOT / "output/riverdale/aaa/hall/preview" ) )
    ap.add_argument( "--views", nargs="*" )
    ap.add_argument( "--size", default="960x540" )
    args = ap.parse_args()
    out = Path( args.out )
    out.mkdir( parents=True, exist_ok=True )
    P.reset()
    models = list( H.build() ) + [ m for _, _, _, _, m in H.extra_models() ]
    colours()
    opaque, glass = PV.triangles( models ), PV.triangles( models, glass=True )
    w, h = ( int( x ) for x in args.size.split( "x" ) )
    for name, eye, target, fov in VIEWS:
        if args.views and name not in args.views:
            continue
        PV.perspective( opaque, glass, eye, target, size=( w, h ), fov=fov ).convert( "RGB" ).save( out / f"{name}.png" )
        print( f"wrote {out / ( name + '.png' )}" )


if __name__ == "__main__":
    main()
