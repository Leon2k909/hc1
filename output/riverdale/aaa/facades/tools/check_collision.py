""" Compares the collision (boxes and hulls) and the clips and lights of the facades area's functions in
Tools/riverdale_map.py against git HEAD's version, run with the same modules. Prints the triangle counts too. """
import sys
from pathlib import Path
import numpy as np
HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert( 0, str( ROOT / "Tools" ) )
sys.path.insert( 0, str( HERE ) )
import map_kit as K
import riverdale_parts as P
import riverdale_map as NEW
import rmap_old as OLD


def collision( m ):
    out = []
    for c, axes, size, surface in m.boxes:
        out.append( ( "box", tuple( np.round( np.asarray( c, float ), 3 ) ), tuple( np.round( np.asarray( axes, float ).ravel(), 4 ) ),
                      tuple( np.round( np.asarray( size, float ), 3 ) ), surface ) )
    for pts, surface in m.hulls:
        out.append( ( "hull", tuple( sorted( tuple( np.round( np.asarray( p, float ), 3 ) ) for p in pts ) ), surface ) )
    return sorted( out, key=repr )


def run( mod, fn, *args ):
    P.reset()
    m = K.Model()
    getattr( mod, fn )( m, *args )
    return m, list( P.CLIPS ), list( P.LIGHTS )


calls = [ ( "annex", ( -1, ) ), ( "annex", ( 1, ) ), ( "court", ( -1, ) ), ( "court", ( 1, ) ), ( "yard_side", ( -1, ) ),
          ( "yard_side", ( 1, ) ), ( "spawn_side", ( -1, ) ), ( "spawn_side", ( 1, ) ), ( "turbine_annex", () ),
          ( "middle_yard", () ), ( "north_lane", () ), ( "turbine_hall", () ) ]
total_old = total_new = 0
bad = 0
for fn, args in calls:
    mo, co, lo = run( OLD, fn, *args )
    mn, cn, ln = run( NEW, fn, *args )
    same = collision( mo ) == collision( mn )
    clips = sorted( map( repr, co ) ) == sorted( map( repr, cn ) )
    lights_old = { l[0]: l for l in lo }
    lights_new = { l[0]: l for l in ln }
    total_old += mo.triangle_count()
    total_new += mn.triangle_count()
    flag = "" if same and clips else "   <-- COLLISION/CLIPS DIFFER"
    bad += 0 if same and clips else 1
    print( f"{fn}{args}: tris {mo.triangle_count()} -> {mn.triangle_count()}, boxes {len( mo.boxes )}/{len( mn.boxes )}, "
           f"hulls {len( mo.hulls )}/{len( mn.hulls )}, clips {len( co )}/{len( cn )}, lights {len( lo )}/{len( ln )}{flag}" )
    gone = sorted( set( lights_old ) - set( lights_new ) )
    added = sorted( set( lights_new ) - set( lights_old ) )
    if gone or added:
        print( f"    lights gone {gone} added {added}" )
# b1 takes a glass model too.
P.reset(); mo = K.Model(); OLD.b1( mo, K.Model() ); co = list( P.CLIPS )
P.reset(); mn = K.Model(); NEW.b1( mn, K.Model() ); cn = list( P.CLIPS )
same = collision( mo ) == collision( mn ) and sorted( map( repr, co ) ) == sorted( map( repr, cn ) )
bad += 0 if same else 1
total_old += mo.triangle_count(); total_new += mn.triangle_count()
print( f"b1: tris {mo.triangle_count()} -> {mn.triangle_count()}, boxes {len( mo.boxes )}/{len( mn.boxes )}"
       f"{'' if same else '   <-- COLLISION/CLIPS DIFFER'}" )
for e0, e1, n0, n1 in ( ( 130, 320, -1165, -1065 ), ( -140, 140, 2220, 2290 ) ):
    mo, mn = K.Model(), K.Model()
    OLD.generator( mo, e0, e1, n0, n1 ); NEW.generator( mn, e0, e1, n0, n1 )
    same = collision( mo ) == collision( mn )
    bad += 0 if same else 1
    print( f"generator: tris {mo.triangle_count()} -> {mn.triangle_count()}{'' if same else '   <-- COLLISION DIFFERS'}" )
print( f"total (these functions): {total_old} -> {total_new} triangles (+{total_new - total_old})" )
print( f"{bad} function(s) with changed collision" )
