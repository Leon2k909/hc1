"""Export the preserved full Rotunde as a standalone model, centred at its base.

    python Tools/railhead_rotunda_export.py <output root>      (a folder laid out as Assets, e.g. a stage)
Then run Blender with --python Tools/railhead_rotunda_bake.py -- --stage <output root> to refresh the distant bake
(Tools/railhead_rotunda_rebake.py does both, queued for the GPU). The full model is intentionally not instantiated in
Railhead.
"""
import sys
from pathlib import Path

import numpy as np
import railhead_backdrop as B
import railhead_map as R
from map_kit import Model


def export( root ):
    model = Model()
    B.rotunda_geometry( model )
    offset = np.array( ( B.ROTUNDA[0], B.ROTUNDA[1], B.ROTUNDA_BASE ) )
    for paint, faces in model.polygons.items():
        model.polygons[paint] = [ ( [ p - offset for p in points ], normal ) for points, normal in faces ]
    B.configure( model )
    R.K.write_model( Path( root ) / R.RESOURCE_DIR, R.RESOURCE_DIR, "railhead_rotunda_full", model )
    print( f"Preserved standalone Rotunde: {model.triangle_count()} triangles" )


if __name__ == "__main__":
    if len( sys.argv ) < 2:
        print( __doc__ )
        sys.exit( 1 )
    export( sys.argv[1] )
