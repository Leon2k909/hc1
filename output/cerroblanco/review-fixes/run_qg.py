""" Runs cerroblanco_quality_geometry.main() into this folder (not the shared stage) and keeps the recorded walls and
slabs for checking. """
import sys, pickle, time
from pathlib import Path
HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import cerroblanco_quality_geometry as QG
STASH = {}
original = QG.recorder
def rec( module, name, records ):
    STASH[name] = records
    return original( module, name, records )
QG.recorder = rec
QG.STAGE = HERE / "stage"
QG.ROOT = HERE / "root"
( QG.ROOT / "output/cerroblanco" ).mkdir( parents=True, exist_ok=True )
t = time.time()
QG.main()
print( "seconds", time.time() - t )
def plain( v ):
    if isinstance( v, dict ): return { k: plain( x ) for k, x in v.items() }
    if isinstance( v, ( list, tuple ) ): return [ plain( x ) for x in v ]
    if hasattr( v, "tolist" ): return v.tolist()
    if isinstance( v, ( int, float, str, bool ) ) or v is None: return v
    return repr( v )
pickle.dump( { k: plain( v ) for k, v in STASH.items() }, open( HERE / "records.pkl", "wb" ) )
