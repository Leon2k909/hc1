"""
Railhead's cycle stands (railhead_dress_detail.cycle_stand), put into the installed dress models without rebuilding them.

The eight stands by the head building's corners (railhead_map.cab_road, four a side at n 1335) were 15 separate rods
each, with square-cut open ends, so every joint round the bow left a wedge you saw the paving through: bright bands
across a dark tube (the user's screenshot, 2026-10-25). cycle_stand now sweeps one mitred tube in brushed stainless.

A full railhead_map.py run would also publish whatever else has changed in the generators since the models were built
(other sessions' work in progress), so this only swaps the stands: it builds the old stands with the old code, finds
exactly those triangles in railhead_dress_east.obj and railhead_dress_west.obj by their written vertex positions and
material, drops them, and appends the new stands' vertices and triangles. Every other line of each file is kept, and it
refuses if the old stands aren't all there, once each. The models' vmdls and mtls already have rw_stainless.

    python Tools/railhead_stage_cycle_stands.py            stage into output/railhead/cycle-stands-v2/stage
    python Tools/railhead_stage_cycle_stands.py --install  stage, then copy over Assets if Assets is still as staged from
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import map_kit as K
from map_kit import Model
import railhead_dress_detail as D
import railhead_map as RMAP

ROOT = Path( __file__ ).resolve().parents[1]
MODELS = ROOT / "Assets/models/maps/railhead"
OUT = ROOT / "output/railhead/cycle-stands-v2"
SIDES = { "railhead_dress_east": 1.0, "railhead_dress_west": -1.0 }
STANDS_E = ( 1290.0, 1330.0, 1370.0, 1410.0 )   # railhead_map.cab_road
STANDS_N = 1335.0


def legacy_cycle_stand( model, e, n, facing, z0=0.0 ):
    """ railhead_dress_detail.cycle_stand before 2026-10-25, as the installed models were built with it. """
    F = D.Frame( e, n, z0, facing )
    r, hw, h, bend = 0.95, 15.75, 35.4, 6.0
    pts = [ F.p( -hw, 0.0, 0.0 ), F.p( -hw, 0.0, h - bend ) ]
    for k in range( 1, 7 ):
        t = math.pi / 2 * k / 6
        pts.append( F.p( -hw + bend * ( 1 - math.cos( t ) ), 0.0, h - bend + bend * math.sin( t ) ) )
    for k in range( 0, 7 ):
        t = math.pi / 2 * k / 6
        pts.append( F.p( hw - bend + bend * math.sin( t ), 0.0, h - bend * ( 1 - math.cos( t ) ) ) )
    pts.append( F.p( hw, 0.0, 0.0 ) )
    for a, b in zip( pts, pts[1:] ):
        if np.linalg.norm( b - a ) > 1e-6:
            D.rod( model, a, b, r, "rw_steel", 10 )
    D.rod( model, F.p( -hw, 0.0, 13.8 ), F.p( hw, 0.0, 13.8 ), 0.75, "rw_steel", 8 )
    for x in ( -hw, hw ):
        D.disc( model, "rw_steel_dark", F.p( x, 0.0, 0.05 ), ( 0, 0, 1 ), 2.2, 10 )


def stands( build, s ):
    model = Model()
    for e in STANDS_E:
        build( model, s * e, STANDS_N, "+e" )
    RMAP.configure( model )
    return model


def sha( path ):
    with Path( path ).open( "rb" ) as stream:
        return hashlib.file_digest( stream, "sha256" ).hexdigest()


def read_obj( path ):
    """ ( v, vt, vn ) lines as bytes, and each face as ( material, [ ( v, vt, vn ) index triples ] ), with its line. """
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
                corners = [ tuple( int( i ) for i in token.split( b"/" ) ) for token in line.split()[1:] ]
                faces.append( ( number, material, corners ) )
    return tables, faces


def signature( tables, material, corners ):
    return ( material, tuple( tables[b"v"][c[0] - 1] for c in corners ) )


def written( model, name ):
    with tempfile.TemporaryDirectory() as folder:
        path = Path( folder ) / f"{name}.obj"
        K.write_obj( path, model, name )
        return read_obj( path )


def patch( name, s, stage, before_dir ):
    source = MODELS / f"{name}.obj"
    before_hash = sha( source )
    old_tables, old_faces = written( stands( legacy_cycle_stand, s ), name )
    wanted = Counter( signature( old_tables, m, c ) for _, m, c in old_faces )
    tables, faces = read_obj( source )
    found = Counter()
    removed = set()
    for number, material, corners in faces:
        if material not in ( b"rw_steel", b"rw_steel_dark" ):
            continue
        key = signature( tables, material, corners )
        if key in wanted and found[key] < wanted[key]:
            found[key] += 1
            removed.add( number )
    if found != wanted:
        missing = sum( ( wanted - found ).values() )
        raise SystemExit( f"{name}: {missing} of the old stands' {sum( wanted.values() )} triangles aren't in it; "
                          "refusing (has it been rebuilt with the new stands already?)" )
    new_tables, new_faces = written( stands( D.cycle_stand, s ), name )
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
    target = stage / f"{name}.obj"
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
    mtl = ( MODELS / f"{name}.mtl" ).read_bytes()
    for material in groups:
        assert b"newmtl " + material + b"\n" in mtl, f"{name}.mtl has no {material.decode()}"
    return {
        "model": name, "source": source.relative_to( ROOT ).as_posix(), "before_sha256": before_hash,
        "staged": target.relative_to( ROOT ).as_posix(), "staged_sha256": sha( target ),
        "backup": ( before_dir / source.name ).relative_to( ROOT ).as_posix(),
        "triangles_before": len( faces ), "old_stand_triangles_removed": len( removed ),
        "new_stand_triangles": sum( len( rows ) for rows in groups.values() ),
        "triangles_after": len( faces ) - len( removed ) + sum( len( rows ) for rows in groups.values() ),
        "new_vertices": { kind.decode(): len( rows ) for kind, rows in append.items() },
        "new_materials": sorted( m.decode() for m in groups ),
        "kept_lines_sha256": kept.hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--install", action="store_true", help="copy the staged OBJs over Assets' afterwards" )
    args = parser.parse_args()
    stage = OUT / "stage/models/maps/railhead"
    if stage.exists():
        shutil.rmtree( stage )
    reports = [ patch( name, s, stage, OUT / "before" ) for name, s in SIDES.items() ]
    if args.install:
        for report in reports:
            source = ROOT / report["source"]
            if sha( source ) != report["before_sha256"]:
                raise SystemExit( f"{report['source']} changed while staging; nothing installed" )
        for report in reports:
            source = ROOT / report["source"]
            temporary = source.with_suffix( ".obj.tmp" )
            shutil.copyfile( ROOT / report["staged"], temporary )
            temporary.replace( source )
            report["installed_sha256"] = sha( source )
            assert report["installed_sha256"] == report["staged_sha256"]
    ( OUT / "report.json" ).write_text( json.dumps( reports, indent=2 ) + "\n" )
    for report in reports:
        print( f"{report['model']}: -{report['old_stand_triangles_removed']} +{report['new_stand_triangles']} triangles "
               f"({report['triangles_before']} -> {report['triangles_after']})"
               + ( ", installed" if args.install else ", staged" ) )


if __name__ == "__main__":
    main()
