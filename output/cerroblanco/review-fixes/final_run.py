""" The quality pass with every fix, into this folder, plus the fit-out models it built (for the flags' OBJ). """
import sys
from pathlib import Path
HERE = Path( __file__ ).resolve().parent
sys.path.insert( 0, str( HERE.parents[2] / "Tools" ) )
import map_kit as K
import cerroblanco_map as C
import cerroblanco_quality_geometry as QG
import map_kit as K
# STUB: the backdrop (cerroblanco_landscape -> veridant/riverdale scripts another session is mid-edit on) isn't used here.
C.backdrop = lambda: ( K.Model(), K.Model() )
QG.STAGE = HERE / "stage"
QG.ROOT = HERE / "root"
base = {}
original_build = C.build
def build():
    models = original_build()
    base.update( models )
    return models
C.build = build
QG.main()
C.build = original_build
for name in ( "cerroblanco_fitout", "cerroblanco_fitout_fine" ):
    print( name, K.write_model( HERE / "fitout", "x", name, base[name] ) )
