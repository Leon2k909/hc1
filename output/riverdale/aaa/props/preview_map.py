"""
riverdale_map.py's flat previews with colours for paints whose textures are staged but not yet in Assets (this area's
and the other areas' staged materials), so they don't come out magenta.

    python output/riverdale/aaa/props/preview_map.py --no-scene --no-models --preview <dir> --views <names>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path( __file__ ).resolve().parents[4]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import riverdale_map as M          # noqa: E402
import railhead_preview as PV      # noqa: E402
import riverdale_materials as RM   # noqa: E402

_setup = M.preview_setup


def preview_setup():
    _setup()
    staged = sorted( ( ROOT / "output/riverdale/aaa" ).glob( "**/*_color.*" ), key=lambda f: -f.stat().st_size )
    found = {}
    for f in staged:
        found.setdefault( f.name.rsplit( "_color", 1 )[0], f )
    for paint in RM.all_paints():
        if paint in PV._colours or paint in RM.PAINTED:
            continue
        if paint in found:
            small = Image.open( found[paint] ).convert( "RGB" ).resize( ( 64, 32 ) )
            PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0


M.preview_setup = preview_setup
sys.argv = [ "riverdale_map.py" ] + sys.argv[1:]
M.main()
