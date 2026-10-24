"""Replace the flat black squares under Cerro Blanco's paved trees with tree pits, in its active dressing render OBJ.

cerroblanco_parts.tree drew each paved tree's "grate" as one flat black 60-inch square, smaller than the medium oaks'
trunk flare (79 across where it meets the paving), so the roots spilled over a black tile (the user, 2026-10-25). It
now draws a tree pit (cerroblanco_parts.tree_pit): soil inside a honed travertine kerb, sized to clear the flare.

The scene draws quality-v1/cerroblanco_dressing_v2.vmdl for visuals and keeps the original dressing vmdl for
collisions, so, as Tools/cerroblanco_bollards_upgrade.py does, this changes only that OBJ: it finds the trees from the
map generator (the cerroblanco_parts.tree calls with grate=True in cerroblanco_map.build()), removes exactly each one's
old black square (a cb_black face at z 0.4 inside its 60 square), and appends the pits from cerroblanco_parts.tree_pit.
Every other face, both colliders and the vmdl stay as they are (cb_honed and soil already have remaps).

    python Tools/cerroblanco_tree_pits.py             # dry run: report and stage
    python Tools/cerroblanco_tree_pits.py --apply     # publish the OBJ (refuses if it changed since the dry run)
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import cerroblanco_parts as P
import map_kit as K

ROOT = Path( __file__ ).resolve().parent.parent
OBJ = ROOT / "Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj"
MTL = OBJ.with_suffix( ".mtl" )
SCENE = ROOT / "Assets/scenes/maps/CerroBlanco/cerroblanco.scene"
WORK = ROOT / "output/cerroblanco/tree-pits"
STAGED = WORK / "stage" / OBJ.name
FRESH = WORK / "new_pits.obj"
REPORT = WORK / "report.json"
OLD_HALF = 30.0             # the old square's half width
OLD_Z = 0.4                 # and its top


def paved_trees():
    """ ( e, n, z, path, scale ) of every tree cerroblanco_map.build() stands in paving. """
    calls = []
    tree = P.tree

    def record( m, e, n, path=f"{P.OAK}/tree_oak_medium_a.vmdl", scale=1.0, z=0.0, grate=True, trunk=9.0 ):
        if grate:
            calls.append( ( float( e ), float( n ), float( z ), path, float( scale ) ) )
        return tree( m, e, n, path, scale, z, grate, trunk )
    P.tree = record
    try:
        import cerroblanco_map as C
        C.build()
    finally:
        P.tree = tree
    return calls, C


def obj_parts( text ):
    lines = text.split( "\n" )
    if lines and lines[-1] == "":
        lines.pop()
    v = [ tuple( map( float, line.split()[1:4] ) ) for line in lines if line.startswith( "v " ) ]
    vt = sum( 1 for line in lines if line.startswith( "vt " ) )
    vn = sum( 1 for line in lines if line.startswith( "vn " ) )
    return lines, v, vt, vn


def old_square( line, v, trees ):
    """ The index of the tree whose old black square this face is part of, or None. OBJ ( x, y, z ) is plan
    ( -e, z, n ). """
    points = [ v[int( token.split( "/" )[0] ) - 1] for token in line.split()[1:] ]
    if not all( abs( y - OLD_Z ) < 0.005 for _, y, _ in points ):
        return None
    for index, ( e, n, z, _, _ ) in enumerate( trees ):
        if all( abs( -x - e ) <= OLD_HALF + 0.01 and abs( north - n ) <= OLD_HALF + 0.01 for x, _, north in points ):
            return index
    return None


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--apply", action="store_true" )
    args = parser.parse_args()
    assert "models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.vmdl" in SCENE.read_text( encoding="utf-8" )
    trees, C = paved_trees()
    assert trees and all( z == 0.0 for _, _, z, _, _ in trees ), trees

    # How many faces each old square was, as the map writer wrote it.
    old = K.Model()
    old.box( ( -OLD_HALF, -OLD_HALF, -1 ), ( OLD_HALF, OLD_HALF, OLD_Z ), { "+z": P.BLACK, "default": None } )
    C.configure( old )
    WORK.mkdir( parents=True, exist_ok=True )
    per_tree = K.write_obj( WORK / "old_square.obj", old, "old_square" )
    per_tree_faces = sum( 1 for line in ( WORK / "old_square.obj" ).read_text( encoding="utf-8" ).split( "\n" )
                          if line.startswith( "f " ) )

    original = OBJ.read_bytes()
    lines, v, vt, vn = obj_parts( original.decode( "utf-8" ) )
    material = None
    removed = Counter()
    kept = []
    for line in lines:
        if line.startswith( "usemtl " ):
            material = line[7:]
        if line.startswith( "f " ) and material == P.BLACK:
            index = old_square( line, v, trees )
            if index is not None:
                removed[index] += 1
                continue
        kept.append( line )
    if dict( removed ) != { k: per_tree_faces for k in range( len( trees ) ) }:
        raise SystemExit( f"unexpected black squares (found {dict( removed )}, expected {per_tree_faces} for each of "
                          f"{len( trees )} trees); not staged" )

    pits = K.Model()
    sizes = []
    for e, n, z, path, scale in trees:
        flare = P.TRUNK_FLARE.get( path.rsplit( "/", 1 )[-1].removesuffix( ".vmdl" ), 40.0 ) * scale
        half = 6.0 * -( -( flare + 12.0 ) // 6.0 )
        P.tree_pit( pits, e, n, z, half )
        sizes.append( half )
    C.configure( pits )
    assert not pits.boxes and not pits.hulls
    fresh = K.write_obj( FRESH, pits, OBJ.stem )
    new_lines, new_v, new_vt, new_vn = obj_parts( FRESH.read_text( encoding="utf-8" ) )
    materials = set( MTL.read_text( encoding="utf-8" ).split() )
    used = { line[7:] for line in new_lines if line.startswith( "usemtl " ) }
    assert used <= materials, used - materials

    # New v, vt and vn after the existing ones of each kind (each kind's indices count only its own lines), the new
    # faces in their own usemtl blocks at the end. Every original line keeps its place.
    merged, done = [], set()
    for line in kept:
        kind = line.split( " ", 1 )[0]
        for before, group in ( ( "vt", "v" ), ( "vn", "vt" ), ( "usemtl", "vn" ) ):
            if kind == before and group not in done:
                merged.extend( l for l in new_lines if l.startswith( group + " " ) )
                done.add( group )
        merged.append( line )
    assert done == { "v", "vt", "vn" }, done
    for line in new_lines:
        if line.startswith( "usemtl " ):
            merged.append( line )
        elif line.startswith( "f " ):
            refs = []
            for token in line.split()[1:]:
                a, b, c = map( int, token.split( "/" ) )
                refs.append( f"{a + len( v )}/{b + vt}/{c + vn}" )
            merged.append( "f " + " ".join( refs ) )
    output = ( "\n".join( merged ) + "\n" ).encode( "utf-8" )
    faces_before = sum( 1 for line in lines if line.startswith( "f " ) )
    faces_after = sum( 1 for line in merged if line.startswith( "f " ) )
    new_faces = sum( 1 for line in new_lines if line.startswith( "f " ) )
    assert faces_after == faces_before - sum( removed.values() ) + new_faces

    STAGED.parent.mkdir( parents=True, exist_ok=True )
    STAGED.write_bytes( output )
    result = { "trees": [ { "e": e, "n": n, "model": path.rsplit( "/", 1 )[-1], "scale": s, "pit_half": h }
                          for ( e, n, _, path, s ), h in zip( trees, sizes ) ],
               "original_sha256": hashlib.sha256( original ).hexdigest(),
               "staged_sha256": hashlib.sha256( output ).hexdigest(),
               "old_faces_removed": sum( removed.values() ), "new_triangles": fresh, "new_faces": new_faces,
               "faces_before": faces_before, "faces_after": faces_after, "vmdl_or_collision_changed": False }
    if args.apply:
        record = json.loads( REPORT.read_text( encoding="utf-8" ) )
        if record["original_sha256"] != result["original_sha256"] or record["staged_sha256"] != result["staged_sha256"]:
            raise SystemExit( "the OBJ or the pits changed since the dry run; run it again first" )
        backup = WORK / "before" / OBJ.name
        backup.parent.mkdir( parents=True, exist_ok=True )
        if backup.exists() and backup.read_bytes() != original:
            raise SystemExit( f"{backup} holds another version; refusing to overwrite it" )
        backup.write_bytes( original )
        K.write_text( OBJ, output.decode( "utf-8" ) )
        result["applied"] = True
    else:
        REPORT.write_text( json.dumps( result, indent=2 ) + "\n", encoding="utf-8" )
    print( json.dumps( { k: v for k, v in result.items() if k != "trees" }, indent=2 ) )
    print( Counter( ( t["model"], t["scale"], t["pit_half"] ) for t in result["trees"] ) )


if __name__ == "__main__":
    main()
