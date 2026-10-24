"""Stage Cerro Blanco's window-head fix (2026-10-25) for publishing through the editor.

Twelve ground-floor windows of the two-storey galleries (and the East Hall's, beside its mezzanine) ran from 20 to 190,
over the first floor's top (180), so a 10-inch strip of glass showed along the foot of the upper rooms' walls. The
fit-out took each strip for a door out of the upper room and hung an exit sign over it, and likewise a sign and a room
plate for every ground-floor door and window under an upper room. Now those windows end at cerroblanco_map.GROUND_HEAD
(150, under the slab) and a doorway must start at its room's floor (cerroblanco_fitout.door_fittings).

The map is built twice, as it was before the fix (GROUND_HEAD 190, the old door rule) and as it is now, with the
backdrop left out. Every file staged is checked against the installed one first:
- the buildings model, the three detail models (cerroblanco_quality_geometry.py) and the scene's Breakable Glass group
  must be exactly what the old build gives, so the new build's are staged whole;
- the fit-out's fine model has hand-published changes (the bike stands), so only its faces that the fix removes are
  taken out of the installed file, every other line byte for byte (belltower_stage_barrels_v3.rewrite);
- the scene is the installed one with only the glass group replaced, written as it is (indent 2, blank lines between).
Two new pane models go in; the two no longer used are left where they are. Nothing is written to Assets:
Sources/CerroBlanco/editor/import-window-heads.cs.txt publishes the stage.
"""
import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import sys

import map_kit as K

ROOT = Path( __file__ ).resolve().parent.parent
OUT = ROOT / "output/cerroblanco/window-heads"
MODELS = "models/maps/cerroblanco"
SCENE = "scenes/maps/CerroBlanco/cerroblanco.scene"


def sha( path ):
    return hashlib.sha256( Path( path ).read_bytes() ).hexdigest()


def build( out, mode ):
    """ Runs in a child process (the modules keep state): python <this> --build <out> before|after. """
    import cerroblanco_map as C
    import cerroblanco_fitout as F
    import cerroblanco_glass as G
    import cerroblanco_quality_geometry as Q
    if mode == "before":
        C.GROUND_HEAD = 190.0
        source = inspect.getsource( F.door_fittings )
        assert source.count( "abs( z0 - room.floor ) > 10" ) == 1
        exec( source.replace( "abs( z0 - room.floor ) > 10", "z0 > room.floor + 10" ), F.__dict__ )
    out.mkdir( parents=True, exist_ok=True )
    Q.STAGE, Q.HEDGE_STAGE, Q.ROOT = out / "quality", out / "hedge", out
    ( out / "output/cerroblanco" ).mkdir( parents=True, exist_ok=True )
    Q.main()
    C.backdrop = lambda: ( K.Model(), K.Model() )
    models = C.build()
    glass = models.pop( "cerroblanco_glass" )
    for name in ( "cerroblanco_buildings", "cerroblanco_fitout_fine" ):
        K.write_model( out / "base", MODELS, name, models[name] )
    G.OUT = out / "glass"
    glass.write_models()
    ( out / "glass_group.json" ).write_text( json.dumps( glass.scene_group( C.ids ) ) )


def faces( path ):
    """ ( line number, ( material, corners as written ) ) for every face line. """
    tables, out, material = { b"v": [], b"vt": [], b"vn": [] }, [], None
    for number, line in enumerate( Path( path ).open( "rb" ) ):
        key = line.split( b" ", 1 )[0]
        if key in tables:
            tables[key].append( line.split( b" ", 1 )[1].strip() )
        elif key == b"usemtl":
            material = line[7:].strip()
        elif key == b"f":
            corners = []
            for token in line.split()[1:]:
                parts = token.split( b"/" )
                corners.append( tuple( tables[k][int( p ) - 1] if p else b"" for k, p in zip( ( b"v", b"vt", b"vn" ), parts ) ) )
            out.append( ( number, ( material, tuple( corners ) ) ) )
    return out


def find_group( node ):
    if node.get( "Name" ) == "Breakable Glass":
        return node
    for child in node.get( "Children", [] ):
        found = find_group( child )
        if found:
            return found
    return None


def scene_text( scene ):
    """ The scene as the installed file is written: json.dumps( indent=2 ) with a blank line after every line. """
    return json.dumps( scene, indent=2 ).replace( "\n", "\n\n" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--build", nargs=2, metavar=( "DIR", "MODE" ), help=argparse.SUPPRESS )
    parser.add_argument( "--revision", default="r1" )
    args = parser.parse_args()
    if args.build:
        build( Path( args.build[0] ), args.build[1] )
        return
    import subprocess
    assert re.fullmatch( "[a-z0-9-]+", args.revision )
    base = OUT / args.revision
    stage = base / "stage"
    assert not stage.exists(), stage
    for mode in ( "before", "after" ):
        subprocess.run( [ sys.executable, __file__, "--build", str( base / mode ), mode ], check=True, cwd=Path( __file__ ).parent )
    before, after, assets = base / "before", base / "after", K.ASSETS
    staged = {}

    def stage_file( relative, source=None, data=None ):
        target = stage / relative
        target.parent.mkdir( parents=True, exist_ok=True )
        if source is not None:
            shutil.copyfile( source, target )
        else:
            target.write_bytes( data )
        staged[relative] = target

    # Whole files: the installed ones must be the old build's.
    whole = [ ( f"{MODELS}/cerroblanco_buildings.{x}", f"base/cerroblanco_buildings.{x}" ) for x in ( "obj", "vmdl", "mtl" ) ]
    whole.append( ( f"{MODELS}/cerroblanco_buildings_hulls_default.obj", "base/cerroblanco_buildings_hulls_default.obj" ) )
    for name in ( "north", "south", "interior" ):
        for x in ( "obj", "vmdl", "mtl" ):
            whole.append( ( f"{MODELS}/quality-v1/cerroblanco_detail_{name}.{x}",
                            f"quality/{MODELS}/quality-v1/cerroblanco_detail_{name}.{x}" ) )
    for relative, built in whole:
        assert sha( assets / relative ) == sha( before / built ), ( "installed differs from the old build", relative )
        if sha( after / built ) != sha( before / built ):
            stage_file( relative, after / built )

    # New pane models; every pane model the old build has must be installed as it is.
    for path in sorted( ( before / "glass" ).iterdir() ):
        assert sha( assets / MODELS / "glass" / path.name ) == sha( path ), path.name
    added_panes = []
    for path in sorted( ( after / "glass" ).iterdir() ):
        installed = assets / MODELS / "glass" / path.name
        if installed.exists():
            assert sha( installed ) == sha( path ), path.name
        else:
            stage_file( f"{MODELS}/glass/{path.name}", path )
            added_panes.append( path.name )

    # The fit-out's fine model: drop the faces the fix removes, from the installed file.
    fine = f"{MODELS}/cerroblanco_fitout_fine.obj"
    old, new = Counter( k for _, k in faces( before / "base/cerroblanco_fitout_fine.obj" ) ), \
               Counter( k for _, k in faces( after / "base/cerroblanco_fitout_fine.obj" ) )
    removed, added = old - new, new - old
    assert not added and removed
    wanted, drop = Counter( removed ), set()
    for number, key in faces( assets / fine ):
        if wanted[key] > 0:
            wanted[key] -= 1
            drop.add( number )
    assert not +wanted, "a removed face isn't in the installed file"
    import belltower_stage_barrels_v3 as S
    fine_row = S.rewrite( assets / fine, stage / fine, drop )
    staged[fine] = stage / fine
    assert Counter( k for _, k in faces( stage / fine ) ) == Counter( k for _, k in faces( assets / fine ) ) - removed

    # The scene: only the glass group replaced.
    text = ( assets / SCENE ).read_text( encoding="utf-8" )
    scene = json.loads( text )
    assert scene_text( scene ) == text, "the scene isn't written as expected"
    group = next( g for g in map( find_group, scene["GameObjects"] ) if g )
    assert json.dumps( group, sort_keys=True ) == json.dumps( json.loads( ( before / "glass_group.json" ).read_text() ), sort_keys=True )
    new_group = json.loads( ( after / "glass_group.json" ).read_text() )
    group.clear()
    group.update( new_group )
    stage_file( SCENE, data=scene_text( scene ).encode( "utf-8" ) )

    manifest = { "revision": "cerroblanco-window-heads-r1", "files": {}, "source_sha256": {},
                 "fitout_fine": { **fine_row, "removed": { k.decode(): v for k, v in Counter( k[0] for k in removed.elements() ).items() } },
                 "added_panes": added_panes, "glass_children": [ len( group["Children"] ) ] }
    for relative, path in sorted( staged.items() ):
        installed = assets / relative
        backup = base / "backup" / relative
        if installed.exists():
            backup.parent.mkdir( parents=True, exist_ok=True )
            shutil.copyfile( installed, backup )
        manifest["files"][relative] = { "source": path.relative_to( ROOT ).as_posix(), "after": sha( path ),
                                        "before": sha( installed ) if installed.exists() else None,
                                        "backup": backup.relative_to( ROOT ).as_posix() if installed.exists() else None }
    for tool in ( "cerroblanco_map.py", "cerroblanco_fitout.py", "cerroblanco_parts.py", "cerroblanco_quality_geometry.py",
                  "cerroblanco_glass.py", "map_kit.py", "cerroblanco_stage_window_heads.py" ):
        manifest["source_sha256"][f"Tools/{tool}"] = sha( ROOT / "Tools" / tool )
    ( base / "manifest.json" ).write_text( json.dumps( manifest, indent=2 ) + "\n" )
    print( json.dumps( { "files": sorted( manifest["files"] ), "fitout_fine": manifest["fitout_fine"], "added_panes": added_panes }, indent=1 ) )


if __name__ == "__main__":
    main()
