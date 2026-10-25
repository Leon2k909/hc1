"""
Flat-shaded views of Railhead's footbridge (railhead_preview's z-buffer) with the dressing read from OBJs, to compare
the installed dressing with the staged splice. The structure comes from the generator (railhead_station).

    python output/railhead/bridge-bins/render_bridge.py <out dir> <dress dir> [<dress dir> ...]

Each dress dir holds railhead_dress_east.obj / railhead_dress_west.obj (missing ones are read from Assets); the
pictures are <out dir>/<dir's name>_<view>.png.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import map_kit as K                     # noqa: E402
import railhead_preview as PV           # noqa: E402
import railhead_station as S            # noqa: E402

INSTALLED = ROOT / "Assets/models/maps/railhead"
LO, HI = np.array( ( -1200.0, -430.0, 150.0 ) ), np.array( ( 1200.0, -130.0, 320.0 ) )
VIEWS = { "along": ( ( 0.0, -280.0, 278.0 ), ( 600.0, -280.0, 260.0 ), 70.0 ),
          "centre": ( ( 300.0, -270.0, 272.0 ), ( -60.0, -240.0, 236.0 ), 70.0 ),
          "south": ( ( 480.0, -250.0, 272.0 ), ( 700.0, -320.0, 236.0 ), 70.0 ),
          "north_end": ( ( 880.0, -300.0, 272.0 ), ( 1100.0, -240.0, 236.0 ), 70.0 ) }


def clip( model ):
    out = K.Model()
    for paint, items in model.polygons.items():
        for points, normal in items:
            p = np.asarray( points, float )
            if ( p.max( 0 ) >= LO ).all() and ( p.min( 0 ) <= HI ).all():
                out.polygons[paint].append( ( p, normal ) )
    return out


def obj_model( path ):
    """ An OBJ's faces near the bridge as a Model in plan ( e, n, z ): OBJ ( a, b, c ) is world ( c, a, b ), world
    ( x, y, z ) is plan ( -y, x, z ). """
    v, out, paint = [], K.Model(), None
    with open( path, encoding="utf-8" ) as f:
        for line in f:
            if line.startswith( "v " ):
                a, b, c = ( float( x ) for x in line.split()[1:4] )
                v.append( ( -a, c, b ) )
            elif line.startswith( "usemtl " ):
                paint = line[7:].strip()
            elif line.startswith( "f " ):
                p = np.array( [ v[int( corner.split( "/" )[0] ) - 1] for corner in line.split()[1:] ] )
                if ( p.max( 0 ) >= LO ).all() and ( p.min( 0 ) <= HI ).all():
                    n = np.cross( p[1] - p[0], p[2] - p[0] )
                    length = np.linalg.norm( n )
                    if length > 1e-12:
                        out.polygons[paint].append( ( p, n / length ) )
    return out


def main():
    out = Path( sys.argv[1] )
    out.mkdir( parents=True, exist_ok=True )
    east, east_glass = S.east_half()
    mid, mid_glass = S.centre()
    struct = [ clip( east ), clip( east.mirrored() ), clip( mid ) ]
    glass = [ clip( east_glass ), clip( east_glass.mirrored() ), clip( mid_glass ) ]
    centre = obj_model( INSTALLED / "railhead_dress_centre.obj" )
    for folder in sys.argv[2:]:
        folder = Path( folder )
        dress = [ obj_model( folder / f"{n}.obj" if ( folder / f"{n}.obj" ).is_file() else INSTALLED / f"{n}.obj" )
                  for n in ( "railhead_dress_east", "railhead_dress_west" ) ] + [ centre ]
        opaque = PV.triangles( struct + dress )
        clear = PV.triangles( glass + dress, glass=True )
        for name, ( eye, target, fov ) in VIEWS.items():
            image = PV.perspective( opaque, clear, eye, target, size=( 1280, 720 ), fov=fov )
            path = out / f"{folder.name}_{name}.png"
            image.save( path )
            print( path )


if __name__ == "__main__":
    main()
