"""
Cerro Blanco's two bronze spheres (the garden circle's, r 58, and the South Gallery's, r 40) in the installed render
model only: the 24 x 12 spheres' faces are found in quality-v1/cerroblanco_dressing_v2.obj and replaced by
cerroblanco_bronze.sphere's 64 x 32 ones with their UVs, and cb_bronze becomes cerroblanco_bronze's textured patina
(its vmat and four PNGs). The drums, the hulls (in the original dressing model, which the scene keeps for collision),
the busts and every other face stay as they are; the old spheres' vertices stay in the file, unused.

The OBJ isn't rebuilt: other sessions splice it too (the tree pits, the bollards). The old faces are drawn with the old
code (old_sphere) and the new with the generator's (cerroblanco_parts.bronze_sphere's call), both configured and
written as the quality pass writes the model (cerroblanco_map.configure, the model's own name for its UV offset), and
matched by material and each corner's v/vt/vn text; every old triangle must be there.

    python output/cerroblanco/bronze-sphere/stage_bronze_sphere.py            stage into output/cerroblanco/bronze-sphere/stage
    python output/cerroblanco/bronze-sphere/stage_bronze_sphere.py --apply    publish, refusing any file changed since staging
"""
import argparse
import hashlib
import json
import math
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import map_kit as K                     # noqa: E402
import cerroblanco_map as C             # noqa: E402
import cerroblanco_parts as P           # noqa: E402
import cerroblanco_bronze as B          # noqa: E402

HERE = Path( __file__ ).resolve().parent
STAGE = HERE / "stage"
MANIFEST = HERE / "manifest.json"
NAME = "cerroblanco_dressing_v2"
OBJ = ROOT / f"Assets/models/maps/cerroblanco/quality-v1/{NAME}.obj"
MATERIALS = ROOT / "Assets" / B.RESOURCE
# Where cerroblanco_map.build() puts its two spheres: ( e, n, r, plinth ).
SPHERES = ( ( *C.GARDEN, 58.0, 24.0 ), ( -200.0, -1230.0, 40.0, 30.0 ) )


def old_sphere( m, e, n, r, plinth ):
    """ bronze_sphere's sphere before 2026-10-24. """
    c = np.array( ( e, n, plinth + r * 0.95 ) )
    rings, sides = 12, 24
    for i in range( rings ):
        t0, t1 = math.pi * i / rings, math.pi * ( i + 1 ) / rings
        for k in range( sides ):
            p0, p1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
            d = [ np.array( ( math.sin( t ) * math.cos( p ), math.sin( t ) * math.sin( p ), math.cos( t ) ) )
                  for t, p in ( ( t0, p0 ), ( t1, p0 ), ( t1, p1 ), ( t0, p1 ) ) ]
            pts = [ c + v * r for v in d ]
            if i == 0:
                pts, d = [ pts[0], pts[1], pts[2] ], [ d[0], d[1], d[2] ]
            elif i == rings - 1:
                pts, d = [ pts[0], pts[1], pts[3] ], [ d[0], d[1], d[3] ]
            P.card( m, P.BRONZE, pts, sum( d ), normals=d )


def new_sphere( m, e, n, r, plinth ):
    B.sphere( m, np.array( ( e, n, plinth + r * 0.95 ) ), r, P.BRONZE )


class Obj:
    """ An OBJ as map_kit writes it (head, v, vt, vn, then usemtl blocks of faces), allowing more v/vt/vn groups that a
    splice appended before the faces: each kind's indices count only its own lines. """

    def __init__( self, data ):
        assert b"\r" not in data, "map_kit writes LF only"
        lines = data.decode( "utf-8" ).split( "\n" )
        if lines and lines[-1] == "":
            lines.pop()
        self.head, self.v, self.vt, self.vn, self.blocks = [], [], [], [], []
        layout = []
        for line in lines:
            kind = line.split( " ", 1 )[0]
            if kind in ( "v", "vt", "vn" ):
                getattr( self, kind ).append( line )
            elif kind == "usemtl":
                self.blocks.append( [ line[7:], [] ] )
                kind = "f"
            elif kind == "f":
                self.blocks[-1][1].append( line )
            else:
                self.head.append( line )
                kind = "head"
            if not layout or layout[-1] != kind:
                layout.append( kind )
        assert layout[0] == "head" and layout[-1] == "f" and set( layout[1:-1] ) <= { "v", "vt", "vn" }, layout

    def key( self, material, line ):
        corners = []
        for corner in line.split()[1:]:
            a, b, c = ( int( x ) for x in corner.split( "/" ) )
            corners.append( ( self.v[a - 1], self.vt[b - 1], self.vn[c - 1] ) )
        return material, tuple( corners )

    def keys( self ):
        return Counter( self.key( material, line ) for material, faces in self.blocks for line in faces )

    def data( self ):
        out = self.head + self.v + self.vt + self.vn
        for material, faces in self.blocks:
            if faces:
                out.append( f"usemtl {material}" )
                out.extend( faces )
        return ( "\n".join( out ) + "\n" ).encode( "utf-8" )


def written( draw ):
    m = K.Model()
    for sphere in SPHERES:
        draw( m, *sphere )
    C.configure( m )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path( tmp ) / f"{NAME}.obj"
        K.write_obj( path, m, NAME )
        return Obj( path.read_bytes() )


def splice( installed, old, new ):
    want = old.keys()
    found = Counter()
    for material, faces in installed.blocks:
        kept = []
        for line in faces:
            key = installed.key( material, line )
            if found[key] < want[key]:
                found[key] += 1
                continue
            kept.append( line )
        faces[:] = kept
    missing = sum( ( want - found ).values() )
    if missing:
        raise SystemExit( f"{missing} of the old spheres' {sum( want.values() )} triangles aren't in {OBJ.name}; not staged" )
    dv, dt, dn = len( installed.v ), len( installed.vt ), len( installed.vn )
    installed.v += new.v
    installed.vt += new.vt
    installed.vn += new.vn
    blocks = { material: faces for material, faces in installed.blocks }
    for material, faces in new.blocks:
        assert material in blocks, f"{material} has no block in {OBJ.name}"
        for line in faces:
            corners = [ tuple( int( x ) for x in c.split( "/" ) ) for c in line.split()[1:] ]
            blocks[material].append( "f " + " ".join( f"{a + dv}/{b + dt}/{c + dn}" for a, b, c in corners ) )
    return sum( want.values() ), sum( len( f ) for _, f in new.blocks )


def sha( path ):
    return hashlib.sha256( Path( path ).read_bytes() ).hexdigest()


def stage():
    before = sha( OBJ )
    installed = Obj( OBJ.read_bytes() )
    removed, added = splice( installed, written( old_sphere ), written( new_sphere ) )
    ( STAGE / "models" ).mkdir( parents=True, exist_ok=True )
    out = STAGE / "models" / OBJ.name
    out.write_bytes( installed.data() )
    # Re-read the staged OBJ: every new triangle present, none of the old ones.
    check = Obj( out.read_bytes() ).keys()
    assert not ( written( old_sphere ).keys() & check ) and not ( written( new_sphere ).keys() - check )
    B.write_materials( STAGE / "materials" )
    files = { OBJ.relative_to( ROOT ).as_posix(): ( out, before ) }
    for path in sorted( p for p in ( STAGE / "materials" ).iterdir() if p.is_file() ):
        target = MATERIALS / path.name
        files[target.relative_to( ROOT ).as_posix()] = ( path, sha( target ) if target.exists() else None )
    record = { "removed_triangles": removed, "added_triangles": added,
               "files": { k: { "staged": str( s.relative_to( ROOT ) ), "staged_sha256": sha( s ), "installed_sha256": i }
                          for k, ( s, i ) in files.items() } }
    MANIFEST.write_text( json.dumps( record, indent=2 ) + "\n", encoding="utf-8" )
    print( f"{OBJ.name}: {removed} triangles removed, {added} added; {len( files ) - 1} material files staged" )


def apply():
    record = json.loads( MANIFEST.read_text( encoding="utf-8" ) )
    changed = [ k for k, f in record["files"].items()
                if ( sha( ROOT / k ) if ( ROOT / k ).exists() else None ) != f["installed_sha256"] ]
    if changed:
        raise SystemExit( f"changed since staging, stage again: {', '.join( changed )}" )
    # The textures and material first, so the model compiles against them.
    for key in sorted( record["files"], key=lambda k: k.endswith( ".obj" ) ):
        f = record["files"][key]
        staged = ROOT / f["staged"]
        assert sha( staged ) == f["staged_sha256"], f"{staged} isn't what was staged"
        target = ROOT / key
        temp = target.with_name( target.name + ".writing" )
        temp.write_bytes( staged.read_bytes() )
        # The editor can hold a file it's compiling for a moment (map_kit.write_text waits the same way).
        for attempt in range( 20 ):
            try:
                temp.replace( target )
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep( 0.5 )
        print( f"wrote {key}" )


if __name__ == "__main__":
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--apply", action="store_true" )
    apply() if parser.parse_args().apply else stage()
