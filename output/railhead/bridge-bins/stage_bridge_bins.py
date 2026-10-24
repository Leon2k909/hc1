"""
Moves the footbridge's six bins (three each side, railhead_map.footbridge_kit) in the installed dressing models only.

Published, the two centre-stair bins (e +-8) stood inside each other mid-bridge and 4 into both stair openings, the
outer stairs' bins 4 into theirs, and every bin's lid went 0.35 into the bridge's handrail. footbridge_kit now puts each
clear of the stair's parapet (the centre stairs' beyond their platform plate) and 1.15 in front of the handrail.

The installed OBJs aren't rebuilt: other sessions have generator edits of their own under way that land in these files
(output/railhead/wing-poster/stage_wing_poster.py's pattern). This builds the old bins and the new ones with the
generator's own code, as railhead_map.build() writes them, finds every triangle of the old bins in the installed OBJs
(material, and each corner's position, UV and normal text), drops those faces and appends the new bins' vertices and
faces. The old bins are looked for twice, with HEAD's railhead_buffer.bevel_box corners and with the current ones, since
another session's splice replaces the bevel boxes' corner triangles. Since the extinguisher-v2 import the vmdls render
extinguisher-v2/<side>-base.obj, and railhead_dress_<side>.obj is that base plus the extinguishers: both get the bins.
Each bin's collision box is moved in the vmdl. Every other line stays as it was (the OBJs' v, vt and vn lines are
gathered ahead of the faces, which keeps every index).

    python output/railhead/bridge-bins/stage_bridge_bins.py            stage into output/railhead/bridge-bins/stage
    python output/railhead/bridge-bins/stage_bridge_bins.py --apply    copy the staged files into Assets, refusing any
                                                                       file that changed since it was staged
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import map_kit as K                     # noqa: E402
import railhead_buffer as B             # noqa: E402
import railhead_map as RMAP             # noqa: E402
import railhead_station as S            # noqa: E402

HERE = Path( __file__ ).resolve().parent
STAGE = HERE / "stage"
MANIFEST = HERE / "manifest.json"
INSTALLED = ROOT / "Assets/models/maps/railhead"
NAMES = ( "railhead_dress_east", "railhead_dress_west" )


def head_bevel_box():
    """ railhead_buffer.bevel_box as committed (its corner triangles before the 2026-10-25 fix). """
    source = subprocess.run( [ "git", "show", "HEAD:Tools/railhead_buffer.py" ], cwd=ROOT, capture_output=True,
                             check=True ).stdout
    with tempfile.TemporaryDirectory() as tmp:
        path = Path( tmp ) / "railhead_buffer_head.py"
        path.write_bytes( source )
        spec = importlib.util.spec_from_file_location( "railhead_buffer_head", path )
        module = importlib.util.module_from_spec( spec )
        spec.loader.exec_module( module )
    return module.bevel_box


def old_bins( m, s ):
    """ footbridge_kit's bins before 2026-10-25: on the opening's other side, 16 off it, 12 off the panel. """
    n0, n1 = S.BRIDGE_N0, S.BRIDGE_N1
    faces = { n1: ( n1 - 4.0, "-n", -1.0 ), n0: ( n0 + 4.0, "+n", 1.0 ) }
    for e0, e1, down in S.BRIDGE_STAIRS:
        face, facing, inward = faces[n1 if down > 0 else n0]
        e_bin = ( e0 - 16.0 ) if e0 < 100 else ( e1 + 16.0 )
        RMAP.put( "bin", m, s * e_bin, face + inward * 12.0, facing, S.DECK_Z )


def new_bins( m, s ):
    """ The bins footbridge_kit draws now: its put( "bin", ... ) calls, replayed into m. """
    calls = []
    put = RMAP.put

    def record( kind, model, *args, **kw ):
        if kind == "bin":
            calls.append( ( args, kw ) )
        return put( kind, K.Model(), *args, **kw )
    RMAP.put = record
    try:
        RMAP.footbridge_kit( K.Model(), s )
    finally:
        RMAP.put = put
    assert len( calls ) == len( S.BRIDGE_STAIRS ), calls
    for args, kw in calls:
        put( "bin", m, *args, **kw )


def pieces( kit ):
    """ { model name: Model } for kit on both sides, as build() would write them. """
    sides = {}
    for s, name in ( ( 1, "railhead_dress_east" ), ( -1, "railhead_dress_west" ) ):
        m = K.Model()
        kit( m, s )
        assert not RMAP.split_paints( m, RMAP.GLASS_PAINTS ).polygons, "a bin has no glass"
        RMAP.configure( m )
        sides[name] = m
    return sides


class Obj:
    """ An OBJ in map_kit's layout: header, v, vt and vn groups (a splice may add more before the faces), then usemtl
    blocks of faces. """

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
        # Other splices append v, vt and vn groups after faces too. Each kind's indices count only its own lines, in
        # order, so gathering them all ahead of the faces (data()) keeps every face's corners.
        assert layout[0] == "head" and layout[-1] == "f" and set( layout[1:] ) <= { "v", "vt", "vn", "f" }, \
            f"not map_kit's layout: {layout[:12]}"

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


def written( model, name ):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path( tmp ) / f"{name}.obj"
        K.write_obj( path, model, name )
        return Obj( path.read_bytes() )


def found_in( installed, want ):
    """ How many of want's triangles the installed OBJ has. """
    have = Counter()
    for material, faces in installed.blocks:
        for line in faces:
            key = installed.key( material, line )
            if key in want and have[key] < want[key]:
                have[key] += 1
    return sum( have.values() )


def splice( installed, old, new, name ):
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
    assert not ( want - found ), f"{name}: old bins' triangles missing"
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
    return sum( want.values() ), added


def box_text( box ):
    """ A collision box's origin, angles and dimensions lines, as map_kit.write_vmdl writes them. """
    centre, axes, size, surface = box
    world_axes = [ K.to_world( a ) for a in axes ]
    return ( f'\t\t\t\t\t\tsurface_prop = "{surface}"\n'
             '\t\t\t\t\t\tcollision_tags = "solid"\n'
             f"\t\t\t\t\t\torigin = {K.vec3( K.to_world( centre ) )}\n"
             f"\t\t\t\t\t\tangles = {K.vec3( K.angles_of( world_axes ) )}\n"
             f"\t\t\t\t\t\tdimensions = {K.vec3( size )}\n" )


def sha( path ):
    return hashlib.sha256( Path( path ).read_bytes() ).hexdigest()


def stage():
    assert RMAP.D is not None, "railhead_dress_detail didn't import"
    current = B.bevel_box
    B.bevel_box = head_bevel_box()
    try:
        olds_head = pieces( old_bins )
    finally:
        B.bevel_box = current
    olds_now, news = pieces( old_bins ), pieces( new_bins )
    STAGE.mkdir( parents=True, exist_ok=True )
    record = { "files": {} }
    for name in NAMES:
        new = written( news[name], name )
        # The old bins with whichever corners the installed files have.
        candidates = [ ( label, written( olds[name], name ) ) for label, olds in ( ( "HEAD corners", olds_head ),
                                                                                   ( "fixed corners", olds_now ) ) ]
        # Since the extinguisher-v2 import the vmdl renders extinguisher-v2/<side>-base.obj (the dressing without its
        # extinguishers); <name>.obj is that base plus the extinguishers. Both get the bins.
        side = name.rsplit( "_", 1 )[1]
        for rel in ( f"{name}.obj", f"extinguisher-v2/{side}-base.obj" ):
            path = INSTALLED / rel
            before = sha( path )
            installed = Obj( path.read_bytes() )
            materials = set( ( path.parent / f"{name}.mtl" ).read_text( encoding="utf-8" ).split() )
            for material, _ in new.blocks:
                assert material in materials, f"{rel}: {material} isn't in its .mtl"
            label, old = max( candidates,
                              key=lambda c: found_in( installed, c[1].keys() ) / sum( c[1].keys().values() ) )
            need = sum( old.keys().values() )
            have = found_in( installed, old.keys() )
            if have != need:
                raise SystemExit( f"{rel}: only {have} of the old bins' {need} triangles are installed (best match: "
                                  f"{label}); not staged" )
            removed, added = splice( installed, old, new, rel )
            out = STAGE / rel
            out.parent.mkdir( parents=True, exist_ok=True )
            out.write_bytes( installed.data() )
            record["files"][rel] = { "installed_sha256": before, "staged_sha256": sha( out ),
                                     "old_bins": label, "removed_triangles": removed, "added_triangles": added }
            print( f"{rel}: {removed} triangles removed ({label}), {added} added" )

        vmdl_path = INSTALLED / f"{name}.vmdl"
        vmdl_before = sha( vmdl_path )
        vmdl = vmdl_path.read_text( encoding="utf-8" )
        old_boxes, new_boxes = olds_now[name].boxes, news[name].boxes
        assert len( old_boxes ) == len( new_boxes ) == len( S.BRIDGE_STAIRS )
        for a, b in zip( old_boxes, new_boxes ):
            ta, tb = box_text( a ), box_text( b )
            if vmdl.count( ta ) != 1:
                raise SystemExit( f"{name}.vmdl: an old bin's collision box is there {vmdl.count( ta )} times; not staged" )
            vmdl = vmdl.replace( ta, tb )
        vout = STAGE / f"{name}.vmdl"
        vout.write_bytes( vmdl.encode( "utf-8" ) )
        record["files"][f"{name}.vmdl"] = { "installed_sha256": vmdl_before, "staged_sha256": sha( vout ),
                                            "moved_boxes": len( old_boxes ) }
        print( f"{name}.vmdl: {len( old_boxes )} collision boxes moved" )
    MANIFEST.write_text( json.dumps( record, indent=2 ) + "\n", encoding="utf-8" )
    print( f"wrote {MANIFEST.relative_to( ROOT )}" )


def apply():
    record = json.loads( MANIFEST.read_text( encoding="utf-8" ) )
    changed = [ name for name, f in record["files"].items() if sha( INSTALLED / name ) != f["installed_sha256"] ]
    if changed:
        raise SystemExit( f"changed since staging, stage again: {', '.join( changed )}" )
    for name, f in record["files"].items():
        staged = STAGE / name
        assert sha( staged ) == f["staged_sha256"], f"{staged} isn't what was staged"
    backup = HERE / "before"
    for name in record["files"]:
        ( backup / name ).parent.mkdir( parents=True, exist_ok=True )
        ( backup / name ).write_bytes( ( INSTALLED / name ).read_bytes() )
    # The OBJs first: the vmdl's write makes the editor recompile the model from them.
    for name in sorted( record["files"], key=lambda n: n.endswith( ".vmdl" ) ):
        K.write_text( INSTALLED / name, ( STAGE / name ).read_bytes().decode( "utf-8" ), newline="" )
        print( f"wrote {name}" )


if __name__ == "__main__":
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--apply", action="store_true" )
    apply() if parser.parse_args().apply else stage()
