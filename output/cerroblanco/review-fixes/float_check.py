""" Runs the quality pass again (into this folder) recording every strip it draws, then measures how far each one is
from the map's own drawn geometry: a strip with nothing within a fraction of an inch floats. """
import sys, pickle, time, json
from pathlib import Path
import numpy as np
HERE = Path( __file__ ).resolve().parent
sys.path.insert( 0, str( HERE.parents[2] / "Tools" ) )
import cerroblanco_map as C
import cerroblanco_quality_geometry as QG
import map_kit as K
# STUB: the backdrop (cerroblanco_landscape -> veridant/riverdale scripts another session is mid-edit on) isn't used here.
C.backdrop = lambda: ( K.Model(), K.Model() )
QG.STAGE = HERE / "stage"
QG.ROOT = HERE / "root"
strips, base = [], {}
original_box = QG.linear_box
def linear_box( m, axis, run, across, z0, z1, paint ):
    if run[1] - run[0] > .01:
        lo, hi = C.lohi( axis, run, across, z0, z1 )
        strips.append( ( np.array( lo, float ), np.array( hi, float ), paint, axis, tuple( run ), tuple( across ), z0, z1 ) )
    return original_box( m, axis, run, across, z0, z1, paint )
QG.linear_box = linear_box
original_build = C.build
def build():
    models = original_build()
    base.update( models )
    return models
C.build = build
detail = {}
import map_kit as K
original_write = K.write_model
def write_model( out, resource, name, model ):
    detail[name] = model
    return original_write( out, resource, name, model )
K.write_model = write_model
QG.main()
K.write_model = original_write
C.build = original_build
# Every drawn polygon of the map's own models (not the backdrop), as AABBs.
boxes = []
for name, model in base.items():
    if "backdrop" in name or name.endswith( "dressing" ) and False:
        continue
    polys = getattr( model, "polygons", {} )
    for paint, items in polys.items():
        for points, normal in items:
            p = np.array( points, float )
            boxes.append( ( p.min( 0 ), p.max( 0 ), name, paint ) )
lo_all = np.array( [ b[0] for b in boxes ] ); hi_all = np.array( [ b[1] for b in boxes ] )
print( len( boxes ), "base polygons" )
report = []
for lo, hi, paint, axis, run, across, z0, z1 in strips:
    gap = None
    for tol in ( .02, .12, .35, .6, 1.2, 2.5, 6 ):
        ok = np.all( lo_all <= hi + tol, axis=1 ) & np.all( hi_all >= lo - tol, axis=1 )
        if ok.any():
            gap = tol
            break
    report.append( ( gap if gap is not None else 99, paint, axis, run, across, z0, z1 ) )
extra = [ ( (e0-.4,n0-.4,z-.15), (e1+.4,n1+.4,z+1.25), "fixed coping" ) for e0,e1,n0,n1,z in [(-576,-570,-100,1050,326),(-588,-584,-100,1050,196),(-800,-716,-246,-240,326),(-760,180,-2440,-2436,420)] ]
for lo, hi, what in extra:
    lo, hi = np.array( lo ), np.array( hi )
    for tol in ( .02, .12, .35, .6, 1.2, 2.5, 6, 20 ):
        ok = np.all( lo_all <= hi + tol, axis=1 ) & np.all( hi_all >= lo - tol, axis=1 )
        if ok.any():
            print( what, lo, hi, "gap <=", tol, sorted( { ( boxes[i][2], boxes[i][3] ) for i in np.nonzero( ok )[0] } )[:6] )
            break
np.savez( HERE / "base_aabbs.npz", lo=lo_all, hi=hi_all, names=np.array( [ b[2] + "|" + b[3] for b in boxes ] ) )
report.sort( key=lambda r: -r[0] )
for r in report[:60]:
    print( r )
from collections import Counter
print( Counter( r[0] for r in report ) )
pickle.dump( report, open( HERE / "float_report.pkl", "wb" ) )

# Flat-shaded views of the details on the buildings, for looking at.
PV = C.PV
C.preview_colours()
models = [ m for n, m in base.items() if "backdrop" not in n ] + [ detail[n] for n in detail if n != "cerroblanco_dressing_v2" ]
opaque, glass_ = PV.triangles( models ), PV.triangles( models, glass=True )
for name, eye, target, fov in (
        ( "sill_courtyard", ( -560, 200, 60 ), ( -650, 330, 25 ), 40 ),
        ( "cafe_floor", ( 900, 600, 60 ), ( 700, 330, 5 ), 60 ),
        ( "facade_floor1", ( -350, 600, 120 ), ( -660, 450, 200 ), 50 ),
        ( "canopy_front", ( -150, -2700, 300 ), ( -150, -2440, 415 ), 55 ),
        ( "parapet_roof", ( -400, 1300, 470 ), ( -430, 1068, 392 ), 45 ) ):
    PV.perspective( opaque, glass_, eye, target, size=( 960, 540 ), fov=fov ).save( HERE / f"view_{name}.png" )
    print( "wrote", name )
