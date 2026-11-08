"""Pulls the lobby's old reception desk out of Assets/models/maps/reefhall/reefhall_lobby.obj, without touching Assets.

The desk is baked into the lobby's merged render model (Tools/reefhall_map.py, lobby(): "The desk: a curved counter..."),
so there is no old asset to keep, only faces. This script:

  1. re-draws the old desk with the generator's own code, into a model of its own, and writes it with map_kit's writer;
  2. finds those exact triangles (same material, same three vertex positions, same order) in the live lobby OBJ;
  3. writes old/old_desk.obj (+ .mtl): the desk's faces as the lobby holds them, with their own UVs and normals. That is
     the BEFORE geometry for the numbers, and it is what revert.py puts back;
  4. writes stage/reefhall_lobby_without_desk.obj: the lobby OBJ with only those face lines dropped, line by line (every
     vertex, UV and normal record stays, so nothing else in the model can move), and old/removed.json: the line numbers
     and the SHA-256 of the original and the cut.

Run:  python extract_old.py        (plain python; it needs the project's Tools on sys.path, which it adds itself)
It never writes under Assets/. It is safe to run again; it refuses to continue if the live lobby OBJ no longer holds
exactly the 204 triangles it expects (that means somebody has changed the desk or the lobby since).
"""
import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
import map_kit as K          # noqa: E402
import reefhall_map as R     # noqa: E402

HERE = Path( __file__ ).resolve().parent
LOBBY_OBJ = ROOT / "Assets/models/maps/reefhall/reefhall_lobby.obj"
OLD_DIR = HERE / "old"
STAGE_DIR = HERE / "stage"
EXPECTED_TRIANGLES = 204


def old_desk( model ):
    """ Tools/reefhall_map.py lobby(), as it was before this trial: draws only (the collision hulls stay in the lobby model). """
    tc = np.array( R.LOBBY_TANK )
    d0, d1, da, db = 212.0, 250.0, -62.0, 62.0
    steps = 16
    for k in range( steps ):
        a, b = da + ( db - da ) * k / steps, da + ( db - da ) * ( k + 1 ) / steps
        pa0, pb0, pa1, pb1 = tc + R.polar( a, d0 ), tc + R.polar( b, d0 ), tc + R.polar( a, d1 ), tc + R.polar( b, d1 )
        R.facing( model, "rh_laminate", [ ( *pa0, 42 ), ( *pb0, 42 ), ( *pb1, 42 ), ( *pa1, 42 ) ], ( 0, 0, 1 ) )
        out = np.array( ( *R.polar( ( a + b ) / 2, 1 ), 0.0 ) )
        R.facing( model, "rh_smooth", [ ( *pa1, 0 ), ( *pb1, 0 ), ( *pb1, 42 ), ( *pa1, 42 ) ], out )
        R.facing( model, "rh_smooth", [ ( *pa0, 0 ), ( *pb0, 0 ), ( *pb0, 42 ), ( *pa0, 42 ) ], -out )
        qa, qb = tc + R.polar( a, d1 + 0.2 ), tc + R.polar( b, d1 + 0.2 )
        R.facing( model, "rh_led_warm", [ ( *qa, 5 ), ( *qb, 5 ), ( *qb, 8 ), ( *qa, 8 ) ], out )
    for a in ( da, db ):
        pa0, pa1 = tc + R.polar( a, d0 ), tc + R.polar( a, d1 )
        side = np.array( ( *R.polar( a + ( 90 if a > 0 else -90 ), 1 ), 0.0 ) )
        R.facing( model, "rh_smooth", [ ( *pa0, 0 ), ( *pa1, 0 ), ( *pa1, 42 ), ( *pa0, 42 ) ], side )
    for a in ( -32.0, 0.0, 32.0 ):
        p = tc + R.polar( a, 228 )
        fr_m = R.Frame( p, R.polar( a + 90, 1 ), -R.polar( a, 1 ) )
        R.fbox( model, fr_m, -11, 11, -1.5, 1.5, 47, 62, { "default": "rh_black", "front": "rh_screen_data" } )
        R.fbox( model, fr_m, -2, 2, -3, 0, 42, 48, "rh_gunmetal" )
    return model


def parse_obj( text ):
    """ Lines kept as they are; the vertex/uv/normal records by index (1-based, like the file); faces with their line. """
    lines = text.split( "\n" )
    v, vt, vn, faces = [], [], [], []
    mat = None
    for n, line in enumerate( lines ):
        if line.startswith( "v " ):
            v.append( line )
        elif line.startswith( "vt " ):
            vt.append( line )
        elif line.startswith( "vn " ):
            vn.append( line )
        elif line.startswith( "usemtl " ):
            mat = line.split( None, 1 )[1].strip()
        elif line.startswith( "f " ):
            idx = [ tuple( int( x ) if x else 0 for x in tok.split( "/" ) ) for tok in line.split()[1:] ]
            faces.append( ( n, mat, idx ) )
    return lines, v, vt, vn, faces


def key_of( v, mat, idx ):
    return ( mat, tuple( v[i[0] - 1][2:].strip() for i in idx ) )


def main():
    OLD_DIR.mkdir( exist_ok=True )
    STAGE_DIR.mkdir( exist_ok=True )
    raw = LOBBY_OBJ.read_bytes()
    assert b"\r\n" not in raw, "the lobby OBJ has CRLF line ends; this script assumes LF (map_kit writes LF)"
    text = raw.decode( "utf-8" )
    lines, v, vt, vn, faces = parse_obj( text )
    print( "lobby OBJ:", len( v ), "v,", len( faces ), "f" )

    # 1. the old desk, drawn again
    model = K.Model()
    old_desk( model )
    R.configure( model )        # Reef Hall's paints and tile sizes (the writer needs them; the positions don't depend on them)
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path( tmp ) / "reefhall_lobby.obj"
        K.write_obj( probe, model, "reefhall_lobby" )
        p_lines, p_v, p_vt, p_vn, p_faces = parse_obj( probe.read_text() )
    want = Counter( key_of( p_v, m, idx ) for _, m, idx in p_faces )
    print( "old desk drawn again:", len( p_faces ), "triangles in", sorted( { m for _, m, _ in p_faces } ) )
    assert len( p_faces ) == EXPECTED_TRIANGLES, len( p_faces )

    # 2. the same triangles in the live lobby OBJ
    found = defaultdict( list )
    for n, m, idx in faces:
        k = key_of( v, m, idx )
        if k in want:
            found[k].append( ( n, m, idx ) )
    hits = [ f for k in want for f in found[k][: want[k]] ]
    extra = sum( max( 0, len( found[k] ) - want[k] ) for k in want )
    missing = sum( max( 0, want[k] - len( found[k] ) ) for k in want )
    print( "matched", len( hits ), "of", len( p_faces ), "| duplicates elsewhere:", extra, "| missing:", missing )
    if len( hits ) != EXPECTED_TRIANGLES or extra or missing:
        raise SystemExit( "the live lobby OBJ does not hold exactly the old desk's triangles: stop and look" )

    # 3. old_desk.obj: those faces, with the UVs and normals the lobby gives them
    hits.sort()
    out_v, out_vt, out_vn, map_v, map_vt, map_vn = [], [], [], {}, {}, {}

    def take( table, src, out, i ):
        if i == 0:
            return 0
        if i not in table:
            out.append( src[i - 1] )
            table[i] = len( out )
        return table[i]

    body, last = [], None
    for n, m, idx in hits:
        if m != last:
            body.append( f"usemtl {m}" )
            last = m
        tri = [ ( take( map_v, v, out_v, a ), take( map_vt, vt, out_vt, b ), take( map_vn, vn, out_vn, c ) ) for a, b, c in idx ]
        body.append( "f " + " ".join( f"{a}/{b}/{c}" for a, b, c in tri ) )
    mats = sorted( { m for _, m, _ in hits } )
    head = [ "# Old reception desk: the faces of reefhall_lobby.obj (Tools/reefhall_map.py, lobby()), as the lobby draws them.",
             "mtllib old_desk.mtl", "o old_desk" ]
    ( OLD_DIR / "old_desk.obj" ).write_text( "\n".join( head + out_v + out_vt + out_vn + body ) + "\n", newline="\n" )
    ( OLD_DIR / "old_desk.mtl" ).write_text( "".join( f"newmtl {m}\nKd 1 1 1\nd 1\n" for m in mats ), newline="\n" )

    # 4. the lobby without those faces, and the way back
    drop = { n for n, _, _ in hits }
    # A material that loses all its faces loses its `usemtl` line too (the generator draws no group for a paint with no
    # faces), so the cut has no empty material group for the importer to trip on.
    groups, current = defaultdict( list ), None
    for n, line in enumerate( lines ):
        if line.startswith( "usemtl " ):
            current = n
            groups[current] = []
        elif line.startswith( "f " ) and current is not None:
            groups[current].append( n )
    emptied = sorted( g for g, face_lines in groups.items() if all( f in drop for f in face_lines ) )
    emptied_names = [ lines[g].split()[1] for g in emptied ]
    cut = [ line for n, line in enumerate( lines ) if n not in drop and n not in set( emptied ) ]
    cut_text = "\n".join( cut )
    ( STAGE_DIR / "reefhall_lobby_without_desk.obj" ).write_bytes( cut_text.encode( "utf-8" ) )
    shutil.copyfile( LOBBY_OBJ, OLD_DIR / "reefhall_lobby_original.obj" )
    info = {
        "lobby_obj": "Assets/models/maps/reefhall/reefhall_lobby.obj",
        "triangles_removed": len( hits ),
        "line_numbers_removed_0_based": sorted( drop | set( emptied ) ),
        "usemtl_lines_dropped_because_empty": emptied_names,
        "materials": mats,
        "sha256_original": hashlib.sha256( raw ).hexdigest(),
        "sha256_cut": hashlib.sha256( cut_text.encode( "utf-8" ) ).hexdigest(),
        "bytes_original": len( raw ),
        "bytes_cut": len( cut_text.encode( "utf-8" ) ),
    }
    ( OLD_DIR / "removed.json" ).write_text( json.dumps( info, indent=1 ) + "\n" )
    print( json.dumps( { k: v_ for k, v_ in info.items() if k != "line_numbers_removed_0_based" }, indent=1 ) )
    print( "old_desk.obj:", len( out_v ), "v lines,", sum( 1 for b in body if b.startswith( "f " ) ), "triangles" )


if __name__ == "__main__":
    main()
