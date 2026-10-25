"""
Moves the head building wings' City-Light poster and extinguisher from the outer wall onto the inner one, in the
installed dressing models only. On the outer wall (e +-1159.5) the poster hung in the cab road door at n 1480 and the
extinguisher's sign in front of the window at 1380; railhead_map.wing_wall_kit now puts them on the hall's side wall
(e +-640.5).

The installed OBJs aren't rebuilt: other sessions have generator edits of their own under way that also land in these
files. Instead this builds the pieces with the generator's own code, as railhead_map.build() writes them (configured,
the glass split off, each model's own UV offset), finds every triangle of the old pieces in the installed OBJs (its
material, and each corner's position, UV and normal text), drops those faces and appends the new pieces' vertices and
faces. Every other line stays as it was; the old pieces' vertices stay in the files, unused. No collision changes
(neither piece has any), so the vmdls are left alone.

    python output/railhead/wing-poster/stage_wing_poster.py            stage into output/railhead/wing-poster/stage
    python output/railhead/wing-poster/stage_wing_poster.py --apply    copy the staged OBJs into Assets, refusing any
                                                                       file that changed since it was staged
"""
import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import map_kit as K                     # noqa: E402
import railhead_map as RMAP             # noqa: E402
import railhead_station as S            # noqa: E402

HERE = Path( __file__ ).resolve().parent
STAGE = HERE / "stage"
MANIFEST = HERE / "manifest.json"
INSTALLED = ROOT / "Assets/models/maps/railhead"
NAMES = ( "railhead_dress_east", "railhead_dress_west", "railhead_dress_glass" )


def old_wall_kit( m, s ):
    """ head_building's last lines before 2026-10-25. """
    wall_e = s * ( S.WALL_IN - 0.5 )
    inward = "-e" if s > 0 else "+e"
    RMAP.detail( "city_light", m, wall_e, 1480.0, inward, "poster_alps" if s > 0 else "poster_bike", bottom=36.0 )
    RMAP.detail( "extinguisher", m, wall_e, 1390.0, inward )


def pieces( kit ):
    """ { model name: Model } for kit on both sides, as build() would write them. """
    sides = {}
    glass = K.Model()
    for s, name in ( ( 1, "railhead_dress_east" ), ( -1, "railhead_dress_west" ) ):
        m = K.Model()
        kit( m, s )
        glass.extend( RMAP.split_paints( m, RMAP.GLASS_PAINTS ) )
        sides[name] = m
    sides["railhead_dress_glass"] = glass
    for m in sides.values():
        RMAP.configure( m )
    return sides


class Obj:
    """ An OBJ in map_kit's layout: header, every v, every vt, every vn, then usemtl blocks of faces. """

    def __init__( self, data ):
        assert b"\r" not in data, "map_kit writes LF only"
        lines = data.decode( "utf-8" ).split( "\n" )
        if lines and lines[-1] == "":
            lines.pop()
        self.head, self.v, self.vt, self.vn, self.blocks = [], [], [], [], []
        layout = []
        for line in lines:
            kind = line.split( " ", 1 )[0]
            if kind == "v":
                self.v.append( line )
            elif kind == "vt":
                self.vt.append( line )
            elif kind == "vn":
                self.vn.append( line )
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
        # map_kit writes head, v, vt, vn, faces; a splice may have added more v, vt and vn groups before the faces (each
        # kind's indices only count its own lines, so data() can gather them).
        assert layout[0] == "head" and layout[-1] == "f" and set( layout[1:-1] ) <= { "v", "vt", "vn" }, \
            f"not map_kit's layout: {layout}"

    def key( self, material, line ):
        """ A face as its material and its corners' v, vt and vn text. """
        corners = []
        for corner in line.split()[1:]:
            a, b, c = ( int( x ) for x in corner.split( "/" ) )
            corners.append( ( self.v[a - 1], self.vt[b - 1], self.vn[c - 1] ) )
        return material, tuple( corners )

    def data( self ):
        out = self.head + self.v + self.vt + self.vn
        for material, faces in self.blocks:
            if faces:
                out.append( f"usemtl {material}" )
                out.extend( faces )
        return ( "\n".join( out ) + "\n" ).encode( "utf-8" )


def written( model, name ):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path( tmp ) / f"{name}.obj"
        K.write_obj( path, model, name )
        return Obj( path.read_bytes() )


def splice( installed, old, new, name ):
    want = Counter( old.key( material, line ) for material, faces in old.blocks for line in faces )
    total = sum( want.values() )
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
    missing = want - found
    if missing:
        raise SystemExit( f"{name}: {sum( missing.values() )} of the old pieces' {total} triangles aren't in the installed "
                          f"OBJ (e.g. {next( iter( missing ) )[0]}); not staged" )
    # Append the new pieces: their v, vt and vn after the installed ones, their faces at the end of their material's
    # block (a new block if the material had none).
    dv, dt, dn = len( installed.v ), len( installed.vt ), len( installed.vn )
    installed.v += new.v
    installed.vt += new.vt
    installed.vn += new.vn
    blocks = { material: faces for material, faces in installed.blocks }
    added = 0
    for material, faces in new.blocks:
        moved = []
        for line in faces:
            corners = []
            for corner in line.split()[1:]:
                a, b, c = ( int( x ) for x in corner.split( "/" ) )
                corners.append( f"{a + dv}/{b + dt}/{c + dn}" )
            moved.append( "f " + " ".join( corners ) )
        if material not in blocks:
            blocks[material] = []
            installed.blocks.append( [ material, blocks[material] ] )
        blocks[material].extend( moved )
        added += len( moved )
    return total, added


def sha( path ):
    return hashlib.sha256( Path( path ).read_bytes() ).hexdigest()


def stage():
    assert RMAP.D is not None, "railhead_dress_detail didn't import"
    olds, news = pieces( old_wall_kit ), pieces( RMAP.wing_wall_kit )
    STAGE.mkdir( parents=True, exist_ok=True )
    record = { "files": {} }
    for name in NAMES:
        path = INSTALLED / f"{name}.obj"
        before = sha( path )
        installed = Obj( path.read_bytes() )
        materials = set( ( INSTALLED / f"{name}.mtl" ).read_text( encoding="utf-8" ).split() )
        old, new = written( olds[name], name ), written( news[name], name )
        for material, _ in new.blocks:
            assert material in materials, f"{name}: {material} isn't in its .mtl"
        removed, added = splice( installed, old, new, name )
        out = STAGE / f"{name}.obj"
        out.write_bytes( installed.data() )
        record["files"][name] = { "installed_sha256": before, "staged_sha256": sha( out ),
                                  "removed_triangles": removed, "added_triangles": added }
        print( f"{name}: {removed} triangles removed, {added} added" )
    MANIFEST.write_text( json.dumps( record, indent=2 ) + "\n", encoding="utf-8" )
    print( f"wrote {MANIFEST.relative_to( ROOT )}" )


def apply():
    record = json.loads( MANIFEST.read_text( encoding="utf-8" ) )
    changed = [ name for name, f in record["files"].items() if sha( INSTALLED / f"{name}.obj" ) != f["installed_sha256"] ]
    if changed:
        raise SystemExit( f"changed since staging, stage again: {', '.join( changed )}" )
    for name, f in record["files"].items():
        staged = STAGE / f"{name}.obj"
        assert sha( staged ) == f["staged_sha256"], f"{staged} isn't what was staged"
        K.write_text( INSTALLED / f"{name}.obj", staged.read_bytes().decode( "utf-8" ), newline="" )
        print( f"wrote {name}.obj" )


if __name__ == "__main__":
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--apply", action="store_true" )
    apply() if parser.parse_args().apply else stage()
