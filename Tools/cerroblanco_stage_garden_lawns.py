"""
Cerro Blanco's garden circle lawns (cerroblanco_map.lawn_quarter), put into the installed grounds model without
rebuilding it.

The four lawns round the bronze sphere (bomb site B) were annulus sectors with radial sides, so between each lawn and
the straight cross path beside it lay a wedge of gravel, widening outwards, with no kerb along it: the grass seemed to
stop short of the path (the user's screenshot, 2026-10-24). lawn_quarter runs the grass up to both paths in a honed
kerb on all four sides.

The museum's quality pass and other sessions edit the installed models in place, so a cerroblanco_map.py rebuild would
publish more than this. This only swaps the lawns: it builds the old quarters with the old code, finds exactly those
triangles in cerroblanco_grounds.obj by their written vertex positions and material, drops them and appends the new
quarters' vertices and triangles. Every other line is kept, and it refuses unless the old lawns are all there, once
each. The model already has the lawn and cb_honed materials, so its slots (and the scene's indexed overrides) stay.

    python Tools/cerroblanco_stage_garden_lawns.py            stage into output/cerroblanco/garden-lawns/stage
    python Tools/cerroblanco_stage_garden_lawns.py --install  stage, then copy over Assets if Assets is still as staged from
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import map_kit as K
from map_kit import Model
import cerroblanco_map as CB
import cerroblanco_parts as P

ROOT = Path( __file__ ).resolve().parents[1]
MODELS = ROOT / "Assets/models/maps/cerroblanco"
OUT = ROOT / "output/cerroblanco/garden-lawns"
NAME = "cerroblanco_grounds"


def legacy_lawns( m ):
    """ garden_circle's lawn quarters before 2026-10-24, as the installed model was built with them. """
    c = CB.GARDEN
    for k in range( 4 ):
        a0 = 90 * k + 12.0
        CB.annulus( m, c, 196, 466, 1.0, CB.LAWN, a0, a0 + 66.0, step=6.0 )
        P.ring( m, c, 466, 474, 0, 3, outer=CB.HONED, inner=CB.HONED, top=CB.HONED, a0=a0, a1=a0 + 66.0, step=6.0, surface=None )
        P.ring( m, c, 188, 196, 0, 3, outer=CB.HONED, inner=CB.HONED, top=CB.HONED, a0=a0, a1=a0 + 66.0, step=6.0, surface=None )


def new_lawns( m ):
    for k in range( 4 ):
        CB.lawn_quarter( m, CB.GARDEN, 90.0 * k )


def lawns( build ):
    model = Model()
    build( model )
    return CB.configure( model )


def sha( path ):
    with Path( path ).open( "rb" ) as stream:
        return hashlib.file_digest( stream, "sha256" ).hexdigest()


def read_obj( path ):
    """ ( v, vt, vn ) lines as bytes, and each face as ( line number, material, [ ( v, vt, vn ) index triples ] ). """
    tables = { b"v": [], b"vt": [], b"vn": [] }
    faces = []
    material = None
    with Path( path ).open( "rb" ) as stream:
        for number, line in enumerate( stream ):
            head = line.split( b" ", 1 )[0]
            if head in tables:
                tables[head].append( line.rstrip( b"\r\n" ) )
            elif head == b"usemtl":
                material = line.split()[1]
            elif head == b"f":
                faces.append( ( number, material, [ tuple( int( i ) for i in token.split( b"/" ) ) for token in line.split()[1:] ] ) )
    return tables, faces


def signature( tables, material, corners ):
    return ( material, tuple( tables[b"v"][c[0] - 1] for c in corners ) )


def written( model ):
    with tempfile.TemporaryDirectory() as folder:
        path = Path( folder ) / f"{NAME}.obj"
        K.write_obj( path, model, NAME )
        return read_obj( path )


def patch( stage, before_dir ):
    source = MODELS / f"{NAME}.obj"
    before_hash = sha( source )
    old_tables, old_faces = written( lawns( legacy_lawns ) )
    wanted = Counter( signature( old_tables, m, c ) for _, m, c in old_faces )
    materials = { m for m, _ in wanted }
    tables, faces = read_obj( source )
    found, removed = Counter(), set()
    for number, material, corners in faces:
        if material not in materials:
            continue
        key = signature( tables, material, corners )
        if found[key] < wanted[key]:
            found[key] += 1
            removed.add( number )
    if found != wanted:
        missing = sum( ( wanted - found ).values() )
        raise SystemExit( f"{NAME}: {missing} of the old lawns' {sum( wanted.values() )} triangles aren't in it; refusing "
                          "(has it been rebuilt with the new lawns already?)" )
    new_tables, new_faces = written( lawns( new_lawns ) )
    counts = { kind: len( rows ) for kind, rows in tables.items() }
    append = { kind: [] for kind in tables }
    index = { kind: {} for kind in tables }
    groups = {}
    for _, material, corners in new_faces:
        tokens = []
        for corner in corners:
            parts = []
            for kind, i in zip( ( b"v", b"vt", b"vn" ), corner ):
                value = new_tables[kind][i - 1]
                if value not in index[kind]:
                    append[kind].append( value )
                    index[kind][value] = counts[kind] + len( append[kind] )
                parts.append( str( index[kind][value] ).encode() )
            tokens.append( b"/".join( parts ) )
        groups.setdefault( material, [] ).append( b"f " + b" ".join( tokens ) )
    mtl = ( MODELS / f"{NAME}.mtl" ).read_bytes()
    for material in groups:
        assert b"newmtl " + material + b"\n" in mtl, f"{NAME}.mtl has no {material.decode()}"
    target = stage / f"{NAME}.obj"
    target.parent.mkdir( parents=True, exist_ok=True )
    before_dir.mkdir( parents=True, exist_ok=True )
    shutil.copyfile( source, before_dir / source.name )
    kept = hashlib.sha256()
    inserted = False
    with target.open( "wb" ) as output, source.open( "rb" ) as stream:
        for number, line in enumerate( stream ):
            if not inserted and line.startswith( b"usemtl " ):
                for kind in ( b"v", b"vt", b"vn" ):
                    output.writelines( row + b"\n" for row in append[kind] )
                inserted = True
            if number in removed:
                continue
            output.write( line )
            kept.update( line )
        for material in sorted( groups ):
            output.write( b"usemtl " + material + b"\n" )
            output.writelines( row + b"\n" for row in groups[material] )
    assert inserted and sha( source ) == before_hash
    added = sum( len( rows ) for rows in groups.values() )
    return {
        "model": NAME, "source": source.relative_to( ROOT ).as_posix(), "before_sha256": before_hash,
        "staged": target.relative_to( ROOT ).as_posix(), "staged_sha256": sha( target ),
        "backup": ( before_dir / source.name ).relative_to( ROOT ).as_posix(),
        "triangles_before": len( faces ), "old_lawn_triangles_removed": len( removed ), "new_lawn_triangles": added,
        "triangles_after": len( faces ) - len( removed ) + added,
        "new_vertices": { kind.decode(): len( rows ) for kind, rows in append.items() },
        "materials": sorted( m.decode() for m in groups ), "kept_lines_sha256": kept.hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--install", action="store_true", help="copy the staged OBJ over Assets' afterwards" )
    args = parser.parse_args()
    stage = OUT / "stage/models/maps/cerroblanco"
    if stage.exists():
        shutil.rmtree( stage )
    report = patch( stage, OUT / "backup" )
    if args.install:
        source = ROOT / report["source"]
        if sha( source ) != report["before_sha256"]:
            raise SystemExit( f"{report['source']} changed while staging; nothing installed" )
        temporary = source.with_suffix( ".obj.tmp" )
        shutil.copyfile( ROOT / report["staged"], temporary )
        temporary.replace( source )
        report["installed_sha256"] = sha( source )
        assert report["installed_sha256"] == report["staged_sha256"]
    ( OUT / "report.json" ).write_text( json.dumps( report, indent=2 ) + "\n" )
    print( f"{NAME}: -{report['old_lawn_triangles_removed']} +{report['new_lawn_triangles']} triangles "
           f"({report['triangles_before']} -> {report['triangles_after']})" + ( ", installed" if args.install else ", staged" ) )


if __name__ == "__main__":
    main()
