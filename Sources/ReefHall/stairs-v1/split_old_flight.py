"""Writes old/lobby_old_flight_north.obj: one flight of the old lobby stairs (the one at n > 0), cut out of
old/lobby_old_stairs.obj (both flights), so BEFORE and AFTER can be counted per flight (the new model is one flight).
The OBJ is written Y-up ( x = -e, y = height, z = plan n ), so the north flight is the faces with z > 0.

    python split_old_flight.py
"""
from collections import defaultdict
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
src = HERE / "old/lobby_old_stairs.obj"
lines = src.read_text().split( "\n" )
v = [ l for l in lines if l.startswith( "v " ) ]
vt = [ l for l in lines if l.startswith( "vt " ) ]
vn = [ l for l in lines if l.startswith( "vn " ) ]
pos = [ tuple( float( x ) for x in l.split()[1:4] ) for l in v ]
keep, mat, body = defaultdict( dict ), None, []
used_v, used_vt, used_vn = {}, {}, {}


def take( table, i, src_list, out_list ):
    if i == 0:
        return 0
    if i not in table:
        out_list.append( src_list[i - 1] )
        table[i] = len( out_list )
    return table[i]


out_v, out_vt, out_vn = [], [], []
last = None
for l in lines:
    if l.startswith( "usemtl " ):
        mat = l
    elif l.startswith( "f " ):
        idx = [ tuple( int( x ) if x else 0 for x in tok.split( "/" ) ) for tok in l.split()[1:] ]
        cn = sum( pos[i[0] - 1][2] for i in idx ) / len( idx )
        if cn <= 0:
            continue
        if mat != last:
            body.append( mat )
            last = mat
        tri = [ ( take( used_v, a, v, out_v ), take( used_vt, b, vt, out_vt ), take( used_vn, c, vn, out_vn ) ) for a, b, c in idx ]
        body.append( "f " + " ".join( f"{a}/{b}/{c}" for a, b, c in tri ) )
head = [ "# One flight (n > 0) of the old lobby stairs, from lobby_old_stairs.obj.", "mtllib lobby_old_stairs.mtl", "o lobby_old_flight_north" ]
( HERE / "old/lobby_old_flight_north.obj" ).write_text( "\n".join( head + out_v + out_vt + out_vn + body ) + "\n", newline="\n" )
print( "faces:", sum( 1 for b in body if b.startswith( "f " ) ), "| v lines:", len( out_v ) )
