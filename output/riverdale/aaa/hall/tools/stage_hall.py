"""
Stages Riverdale's reactor hall for an offline render (render.py): riverdale_hall's models (its five and its two detail
models) and the map's scene into output/riverdale/aaa/hall/stage, laid out as Assets. Models it doesn't stage are read
from Assets by the renderer; the scene only names models that are staged or in Assets.

    python output/riverdale/aaa/hall/tools/stage_hall.py [--materials] [--all]

--materials also writes the hall's own materials (riverdale_hall.EXTRA_SURFACES), every flat paint, and the shared ones
the hall uses that Assets hasn't got yet, into the stage. --all stages every model, not only the hall's.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import map_kit as K  # noqa: E402
import riverdale_map as M  # noqa: E402
import riverdale_hall as H  # noqa: E402
import riverdale_parts as P  # noqa: E402
import riverdale_materials as RM  # noqa: E402

STAGE = ROOT / "output/riverdale/aaa/hall/stage"
HALL = ( "riverdale_hall", "riverdale_hall_dress", "riverdale_pool", "riverdale_water", "riverdale_glass", "riverdale_hall_detail",
         "riverdale_hall_fine" )
SHARED = ( "rv_wall_clean", "rv_galv", "rv_stainless", "rv_line_yellow", "rv_grime_foot", "rv_grime_top", "rv_frame", "rv_dark",
           "rv_door", "rv_window_dark", "rv_louvre" )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument( "--materials", action="store_true" )
    ap.add_argument( "--all", action="store_true" )
    args = ap.parse_args()
    mats = STAGE / "materials/riverdale"
    if args.materials:
        RM.load_extras()
        mats.mkdir( parents=True, exist_ok=True )
        for name in list( H.EXTRA_SURFACES ) + [ n for n in SHARED if n in RM.SURFACES ] + [ "painted" ]:
            RM.build( name, mats )
    models = M.build()
    out = STAGE / M.RESOURCE_DIR
    out.mkdir( parents=True, exist_ok=True )
    for name, model in models.items():
        if not ( args.all or name in HALL ) or K.is_empty( model ):
            continue
        count = K.write_model( out, M.RESOURCE_DIR, name, model )
        print( f"{name}: {count} triangles" )
    written = { name for name in models if ( out / f"{name}.vmdl" ).exists() or ( K.ASSETS / M.RESOURCE_DIR / f"{name}.vmdl" ).exists() }
    M.SCENE_FILE = STAGE / "scenes/maps/Riverdale/riverdale.scene"
    M.ROOF_CLIPS[:] = M.roof_clips()
    M.write_scene( written, H.lights() + list( P.LIGHTS ), M.probes() )
    # The same without the volumetric haze, which Cycles renders as noise at low samples.
    scene = json.loads( M.SCENE_FILE.read_text( encoding="utf-8" ) )
    scene["GameObjects"] = [ g for g in scene["GameObjects"] if g.get( "Name" ) != "Volumetric Fog" ]
    ( M.SCENE_FILE.parent / "riverdale_nohaze.scene" ).write_text( json.dumps( scene, indent=1 ), encoding="utf-8" )


if __name__ == "__main__":
    main()
