"""
The props area's prop sheet: every riverdale_parts primitive and helper laid out on a test wall and floor, written with
map_kit's own OBJ writer (the engine's UVs and normals) plus materials.json and cameras.json for render_sheet.py.

    python output/riverdale/aaa/props/build_sheet.py [--old]

--old builds the same sheet with the original riverdale_parts (a copy passed by RV_PARTS_ORIG) for a before/after.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path( __file__ ).resolve().parents[4]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import numpy as np                      # noqa: E402

import map_kit as K                     # noqa: E402
import riverdale_materials as RM        # noqa: E402

OLD = "--old" in sys.argv
if OLD:
    spec = importlib.util.spec_from_file_location( "riverdale_parts_orig", os.environ["RV_PARTS_ORIG"] )
    P = importlib.util.module_from_spec( spec )
    spec.loader.exec_module( P )
else:
    import riverdale_parts as P         # noqa: E402

OUT = Path( __file__ ).resolve().parent / ( "sheet_old" if OLD else "sheet" )
STAGED = Path( __file__ ).resolve().parent / "materials"
UP = np.array( ( 0.0, 0.0, 1.0 ) )
STONE, METAL = "default", "metal"


def v( *p ):
    return np.asarray( p, float )


def build():
    P.reset()
    m = K.Model()
    m.box( ( -250, -350, -4 ), ( 1450, 900, 0 ), { "default": None, "+z": "rv_yard" }, STONE )
    # The wall, its face at n 600 looking south, an opening for a recessed double door at e 300..370.
    for e0, e1 in ( ( -150, 300 ), ( 370, 1300 ) ):
        m.box( ( e0, 600, 0 ), ( e1, 630, 300 ), "rv_wall", STONE )
    m.box( ( 300, 600, 96 ), ( 370, 630, 300 ), "rv_wall", STONE )
    m.box( ( 300, 630, 0 ), ( 370, 760, 0.2 ), { "default": None, "+z": "rv_floor" } )
    right, out = v( 1, 0, 0 ), v( 0, -1, 0 )
    P.door( m, ( 0, 600, 0 ), right, 80, 96, double=False )
    P.louvre( m, ( 150, 600, 200 ), right, 120, 90 )
    P.door( m, ( 335, 600, 0 ), right, 66, 92 )
    P.wall_light( m, "lamp", ( 500, 600, 150 ), out, "warm", 300 )
    P.life_ring( m, ( 440, 600, 64 ), out )
    if not OLD:
        P.extinguisher( m, ( 600, 600, 0 ), out )
        P.electrical_box( m, ( 690, 600, 60 ), out )
        P.conduit( m, [ ( 690, 597, 82 ), ( 690, 597, 140 ), ( 760, 597, 160 ), ( 900, 597, 160 ) ], wall=( 0, 1, 0 ) )
        P.hose_reel( m, ( 790, 600, 50 ), out )
        P.cctv( m, ( 880, 600, 200 ), out )
        P.ladder( m, ( 1100, 593, 0 ), 300, out )
    P.plate( m, "danger", ( 950, 600, 120 ), right, 18 )
    P.beacon( m, "beacon", ( 1250, 615, 300 ) )
    # Floor props.
    P.jersey( m, ( 0, 420 ), ( 1, 0 ) )
    P.jersey( m, ( 170, 400 ), ( 0.2, 1 ) )
    P.case_stack( m, ( 300, 430 ), ( 1, 0.05 ), "olive", seed=3 )
    P.case_stack( m, ( 380, 470 ), ( 0.1, 1 ), "dark", seed=7 )
    if not OLD:
        P.case( m, ( 470, 430 ), ( 44, 28, 22 ), ( 1, 0 ), "rv_olive", 0.0, lid_open=True )
    P.bollard( m, 545, 430 )
    if not OLD:
        P.cone( m, ( 590, 420 ) )
        P.cone( m, ( 612, 450 ) )
        P.drum( m, ( 660, 430 ) )
        P.pallet( m, ( 760, 440 ), ( 1, 0 ) )
        P.drum( m, ( 748, 432 ), z0=5.7 )
        P.drum( m, ( 774, 452 ), z0=5.7, paint="rv_drum_red" )
        P.cable_reel( m, ( 880, 440 ), ( 0.3, 1 ) )
        P.manhole( m, ( 980, 420 ) )
        P.drain_grate( m, ( 1060, 420 ), ( 1, 0 ) )
        P.sign_post( m, ( 1150, 460 ), ( 0, -1 ), "caution" )
    # Tank, stairs and a platform.
    P.tank( m, ( 0, 0 ), 56, 280, facing=( 0, -1 ), letters_name="water_purification" )
    m.box( ( 210, 170, 176 ), ( 290, 260, 192 ), { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    P.stairs( m, ( 250, -100 ), ( 250, 170 ), 48, 0, 192, name="test stair" )
    P.railing( m, [ ( 210, 170 ), ( 210, 260 ), ( 290, 260 ), ( 290, 170 ) ], 192, clip_to=60 )
    m.box( ( 360, 120, 0 ), ( 440, 200, 128 ), { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    P.stairs( m, ( 400, -100 ), ( 400, 120 ), 60, 0, 128, tread="rv_plinth", side="rv_plinth", solid_under=True, surface=STONE, name="concrete" )
    P.railing( m, [ ( 500, -150 ), ( 700, -150 ), ( 700, 0 ), ( 500, 0 ) ], 0, closed=True, clip_to=40, height=40 )
    # A pipe rack: columns, I-beams, pipes on shoes with a valve and flanges, a truss, a cable tray.
    for e in ( 760, 1000, 1240 ):
        for n in ( -100, 0 ):
            m.box( ( e - 5, n - 5, 0 ), ( e + 5, n + 5, 150 ), "rv_steel", METAL )
    for n in ( -100, 0 ):
        P.i_beam( m, ( 750, n, 150 ), ( 1250, n, 150 ), 12, 8 )
    for e in ( 760, 1000, 1240 ):
        P.i_beam( m, ( e, -110, 150 ), ( e, 10, 150 ), 12, 8 )
    kw = {} if OLD else { "supports": 240.0 }
    P.pipe( m, [ ( 740, -80, 156 + 9 ), ( 1240, -80, 156 + 9 ), ( 1240, -80, 40 ) ], 9, "rv_pipe", 12, caps=True, **kw )
    kw = {} if OLD else { "supports": 240.0, "valves": ( 0.55, ) }
    P.pipe( m, [ ( 740, -40, 156 + 5 ), ( 1250, -40, 156 + 5 ) ], 5, "rv_steel", 12, flanges=( 0, -1 ), **kw )
    kw = {} if OLD else { "supports": 240.0 }
    P.pipe( m, [ ( 740, -10, 156 + 4 ), ( 1100, -10, 156 + 4 ), ( 1100, 60, 156 + 4 ), ( 1100, 60, 260 ) ], 4, "rv_pipe", 10, **kw )
    P.truss( m, ( 750, 150, 250 ), ( 1250, 150, 250 ), 40, panel=60 )
    P.cable_tray( m, ( 750, 100, 200 ), ( 1250, 100, 200 ) )
    m.box( ( 1300, -100, 200 ), ( 1420, 100, 212 ), "rv_wall", STONE )
    P.ceiling_light( m, "batten", ( 1360, 0, 170 ), ( 0, 1 ), "cool", 400 )
    return m


def materials( m ):
    """ Each paint's look for Blender: a texture set or a flat colour, metal, roughness, glow, alpha. """
    RM.load_extras()
    out = {}
    for paint in m.polygons:
        spec = { "color": None, "rough": 0.6, "metal": 0.0, "glow": 0.0 }
        others = sorted( ( ROOT / "output/riverdale/aaa/surfaces" ).glob( f"**/{paint}_color.*" ), key=lambda f: -f.stat().st_size )
        for base in [ STAGED, RM.OUT_DIR ] + [ f.parent for f in others ]:
            for ext in ( "jpg", "png" ):
                if ( base / f"{paint}_color.{ext}" ).exists():
                    spec["texture"] = str( base / f"{paint}_color.{ext}" )
                    for kind, key in ( ( "normal", "normal" ), ( "rough", "roughmap" ), ( "trans", "alpha" ), ( "illum", "illum" ) ):
                        for e2 in ( "jpg", "png" ):
                            if ( base / f"{paint}_{kind}.{e2}" ).exists():
                                spec[key] = str( base / f"{paint}_{kind}.{e2}" )
                    break
            if "texture" in spec:
                break
        spec["metal"] = RM.METALNESS.get( paint, 0.0 )
        if paint in RM.PAINTED:
            rgb, metal, rough, glow = RM.PAINTED[paint]
            spec.update( color=rgb, metal=metal, rough=rough, glow=glow )
        if paint.startswith( "rv_letters" ):
            spec.update( color=( 20, 20, 22 ) if paint.endswith( "dark" ) else ( 220, 222, 220 ), alpha=str( RM.OUT_DIR / "rv_letters_trans.png" ) )
        if paint == "rv_plates":
            spec["texture"] = str( RM.OUT_DIR / "rv_plates_color.png" )
        if paint == "rv_grating":
            spec["alpha"] = str( RM.OUT_DIR / "rv_grating_trans.png" )
            spec["metal"] = 0.5
        if not spec.get( "texture" ) and not spec.get( "color" ):
            spec["color"] = ( 96, 98, 100 )
        if paint == "rw_glass":
            spec.update( color=( 200, 220, 225 ), glass=True )
        out[paint] = spec
    return out


CAMERAS = [
    ( "overview", ( 600, -720, 360 ), ( 600, 300, 60 ), 70 ),
    ( "wall_left", ( 170, 330, 110 ), ( 170, 600, 110 ), 80 ),
    ( "wall_right", ( 740, 360, 100 ), ( 740, 600, 110 ), 70 ),
    ( "floor_left", ( 230, 260, 80 ), ( 300, 430, 15 ), 62 ),
    ( "floor_right", ( 820, 270, 75 ), ( 820, 435, 15 ), 66 ),
    ( "tank_stairs", ( 130, -470, 170 ), ( 200, 30, 130 ), 66 ),
    ( "pipe_rack", ( 1000, -360, 120 ), ( 1000, -20, 165 ), 62 ),
    ( "barrier_close", ( 40, 330, 42 ), ( 10, 420, 14 ), 50 ),
    ( "door_close", ( 335, 470, 62 ), ( 335, 600, 52 ), 52 ),
    ( "wall_close", ( 660, 470, 70 ), ( 660, 600, 75 ), 56 ),
    ( "stairs_close", ( 330, -170, 70 ), ( 250, -40, 50 ), 60 ),
]


def main():
    sys.path.insert( 0, str( ROOT / "Tools" ) )
    import riverdale_map as M
    m = build()
    M.configure( m )
    OUT.mkdir( parents=True, exist_ok=True )
    tris = K.write_obj( OUT / "props_sheet.obj", m, "props_sheet" )
    ( OUT / "materials.json" ).write_text( json.dumps( materials( m ), indent=1 ) )
    ( OUT / "cameras.json" ).write_text( json.dumps( [ { "name": n, "eye": e, "target": t, "fov": f } for n, e, t, f in CAMERAS ], indent=1 ) )
    print( f"wrote {OUT / 'props_sheet.obj'}: {tris} triangles, {len( m.polygons )} paints, {len( P.LIGHTS )} lights, {len( P.CLIPS )} clips" )
    ( OUT / "lights.json" ).write_text( json.dumps( [ { "name": l[0], "at": list( map( float, l[1] ) ), "colour": l[2], "radius": l[3] } for l in P.LIGHTS ] ) )


if __name__ == "__main__":
    main()
