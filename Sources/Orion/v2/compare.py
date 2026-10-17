"""
Orion against its reference picture: renders the reference view of a scene (the installed one, or a staged one or a
variant) through the editor and prints matched patches of the picture and the capture.

    python Sources/Orion/v2/compare.py [name] [--scene <project-relative .scene>] [--disable <ComponentType> ...]
                                       [--exposure <fixed>] [--settle <frames>]

The view is the picture's: a level camera at the overlook (Tools/orion_map.py REF_EYE, 0,-560,400) looking due north,
75 degrees across, rendered 1536 x 1356 and cropped to the picture's 1536 x 1024 with its horizon 346 down. The
picture has a shifted lens (its verticals are parallel), which a level render cropped low reproduces; a pitched camera
doesn't. Writes output/orion/v2/captures/<name>.png (the crop) and prints each patch's mean colour and median.

The scene's exposure is automatic and adapts over real time, so a capture taken after a few frames is darker than a
match, where it has settled. 160 frames (several seconds) is enough for it to settle, as it does in play. Before
2026-10-17 captures took 40 frames and stopped part-way (near 1.2, with the maximum then 1.6).
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path( __file__ ).resolve().parents[3]
CAPTURES = ROOT / "output/orion/v2/captures"
CLI = Path( r"D:/SteamLibrary/steamapps/common/sbox/bin/managed/sbox-cli.exe" )
REFERENCE = Path( __file__ ).resolve().parent / "reference.png"

# ( x0, y0, x1, y1 ) in the picture: shaded faces, the wet yard, the sky by the sun and overhead, the hills.
PATCHES = { "lc_face": ( 180, 400, 290, 480 ), "orion_face": ( 720, 600, 880, 660 ), "b3_face": ( 1170, 560, 1330, 650 ),
            "yard_far": ( 560, 700, 1000, 760 ), "yard_near": ( 600, 860, 1000, 1000 ), "sky_sun": ( 300, 160, 360, 240 ),
            "sky_blue": ( 1100, 20, 1350, 60 ), "hills": ( 560, 280, 840, 330 ), "deck_front": ( 440, 470, 700, 530 ) }


def stats( a ):
    out = {}
    for k, ( x0, y0, x1, y1 ) in PATCHES.items():
        r = a[y0:y1, x0:x1].reshape( -1, 3 )
        out[k] = ( r.mean( 0 ).round( 0 ).astype( int ).tolist(), int( np.median( r.mean( 1 ) ) ) )
    return out


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "name", nargs="?", default="reference" )
    parser.add_argument( "--scene", default="Assets/scenes/maps/Orion/orion.scene" )
    parser.add_argument( "--disable", nargs="*", default=[] )
    parser.add_argument( "--exposure", type=float, help="a fixed exposure instead of the scene's automatic one" )
    parser.add_argument( "--settle", type=int, default=160, help="frames rendered before the capture (default 160)" )
    args = parser.parse_args()
    view = { "name": args.name, "eye": [ 0, -560, 400 ], "target": [ 0, 440, 400 ], "fov": 75.0, "width": 1536, "height": 1356 }
    if args.disable:
        view["disable"] = args.disable
    if args.exposure:
        view["exposure"] = args.exposure
    CAPTURES.mkdir( parents=True, exist_ok=True )
    ( CAPTURES / "config.json" ).write_text( json.dumps( { "scene": args.scene, "views": [ view ], "settle_frames": args.settle,
                                                           "stream_frames": 100 }, indent=1 ) )
    script = ( ROOT / "Sources/Orion/v2/editor/capture.cs.txt" ).as_posix()
    result = subprocess.run( [ str( CLI ), "--request-timeout", "590", "--call", "run_csharp", json.dumps( { "path": script } ) ],
                             cwd=str( CLI.parent ), capture_output=True, text=True, timeout=620 )
    if '"Written"' not in result.stdout + result.stderr:
        raise SystemExit( ( result.stdout + result.stderr )[-1500:] )
    crop = Image.open( CAPTURES / f"{args.name}.png" ).convert( "RGB" ).crop( ( 0, 332, 1536, 1356 ) )
    crop.save( CAPTURES / f"{args.name}.png" )
    ref = stats( np.asarray( Image.open( REFERENCE ).convert( "RGB" ) ).astype( float ) )
    cap = stats( np.asarray( crop ).astype( float ) )
    for k in PATCHES:
        print( f"{k:11s} picture {ref[k][0]} median {ref[k][1]:3d} | capture {cap[k][0]} median {cap[k][1]:3d}" )


if __name__ == "__main__":
    main()
