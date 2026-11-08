"""Pulls the lobby balcony's old glass railing (north run and its south mirror) out of
Assets/models/maps/reefhall/reefhall_lobby.obj, without touching Assets.

Tools/reefhall_map.py lobby_north() draws it with railing( model, ( v_e0, v_n1 + 2 ), ( v_e1, v_n1 + 2 ), L1 ) and
build_mirrored() adds the south copy, so there is no old asset to keep, only faces. Same method as the reception desk
(Sources/ReefHall/reception-desk-v1/extract_old.py): re-draw the old railing with the generator's own code, find those exact
triangles (same material, same three vertex positions, same order) in the live lobby OBJ, then write

  old/old_rail.obj (+ .mtl)         the railing's faces as the lobby holds them: the BEFORE geometry for the numbers
  stage/reefhall_lobby_without_rail.obj   the lobby OBJ with only those face lines dropped (every v / vt / vn record stays)
  old/removed.json                  line numbers and SHA-256 of the original and the cut

Run:  python extract_old.py [--write]     without --write it only counts and checks.
It never writes under Assets/.
"""
import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
import map_kit as K          # noqa: E402
import reefhall_map as R     # noqa: E402

HERE = Path( __file__ ).resolve().parent
LOBBY_OBJ = ROOT / "Assets/models/maps/reefhall/reefhall_lobby.obj"
OLD_DIR = HERE / "old"
STAGE_DIR = HERE / "stage"


def old_rail():
    """ Tools/reefhall_map.py lobby_north(), as it was before this trial: the railing's drawing, north run and south mirror. """
    v_e0, v_e1, v_n0, v_n1 = R.LOBBY_VOID
    north = K.Model()
    R.railing( north, ( v_e0, v_n1 + 2 ), ( v_e1, v_n1 + 2 ), R.L1, collide=False )
    both = K.Model()
    both.extend( north )
    both.extend( R.mirror_model( north, False, True ) )
    R.configure( both )
    return both


def parse_obj( text ):
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


def main( write ):
    raw = LOBBY_OBJ.read_bytes()
    assert b"\r\n" not in raw
    text = raw.decode( "utf-8" )
    lines, v, vt, vn, faces = parse_obj( text )
    print( "lobby OBJ:", len( v ), "v,", len( faces ), "f" )

    model = old_rail()
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path( tmp ) / "probe.obj"
        K.write_obj( probe, model, "probe" )
        p_lines, p_v, p_vt, p_vn, p_faces = parse_obj( probe.read_text() )
    want = Counter( key_of( p_v, m, idx ) for _, m, idx in p_faces )
    print( "old rail drawn again:", len( p_faces ), "triangles in", sorted( { m for _, m, _ in p_faces } ) )

    found = defaultdict( list )
    for n, m, idx in faces:
        k = key_of( v, m, idx )
        if k in want:
            found[k].append( ( n, m, idx ) )
    hits = [ f for k in want for f in found[k][: want[k]] ]
    extra = sum( max( 0, len( found[k] ) - want[k] ) for k in want )
    missing = sum( max( 0, want[k] - len( found[k] ) ) for k in want )
    print( "matched", len( hits ), "of", len( p_faces ), "| duplicates elsewhere:", extra, "| missing:", missing )
    by_mat = Counter( m for _, m, _ in hits )
    print( "by material:", dict( by_mat ) )
    if len( hits ) != len( p_faces ) or extra or missing:
        raise SystemExit( "the live lobby OBJ does not hold exactly the old railing's triangles: stop and look" )
    if not write:
        return

    OLD_DIR.mkdir( exist_ok=True )
    STAGE_DIR.mkdir( exist_ok=True )
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
    head = [ "# Old lobby balcony railing: the faces of reefhall_lobby.obj (Tools/reefhall_map.py, lobby_north()).",
             "mtllib old_rail.mtl", "o old_rail" ]
    ( OLD_DIR / "old_rail.obj" ).write_text( "\n".join( head + out_v + out_vt + out_vn + body ) + "\n", newline="\n" )
    ( OLD_DIR / "old_rail.mtl" ).write_text( "".join( f"newmtl {m}\nKd 1 1 1\nd 1\n" for m in mats ), newline="\n" )

    drop = { n for n, _, _ in hits }
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
    ( STAGE_DIR / "reefhall_lobby_without_rail.obj" ).write_bytes( cut_text.encode( "utf-8" ) )
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
    print( "old_rail.obj:", len( out_v ), "v lines,", sum( 1 for b in body if b.startswith( "f " ) ), "triangles" )


if __name__ == "__main__":
    main( "--write" in sys.argv )
