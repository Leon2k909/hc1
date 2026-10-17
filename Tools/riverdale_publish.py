"""
Publishes Riverdale's staged build into Assets: the materials (Tools/riverdale_materials.py --out
output/riverdale/aaa/stage/materials/riverdale), the sky (Tools/riverdale_sky.py into the same stage) and the map script's
models, radar picture and scene (Tools/riverdale_map.py --stage output/riverdale/aaa/stage).

    python Tools/riverdale_publish.py [--scene] [--dry-run] [--stage DIR]

Only files that differ from Assets are copied, each through a temporary file renamed over the old one (the editor
compiles a changed file straight away), the old one first backed up to output/riverdale/aaa/before/ (once). The scene is
left out unless --scene: copy it only while the editor doesn't have Riverdale open with changes of its own, and not while
a match is playing on it. Writes output/riverdale/aaa/publish.json: what was copied, in the order the editor should compile
it (Sources/Riverdale/editor/compile-stale.cs.txt compiles whatever is newer than its compiled file).
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"
STAGE = ROOT / "output/riverdale/aaa/stage"
BACKUP = ROOT / "output/riverdale/aaa/before"
ALLOWED = ( "materials/riverdale/", "models/maps/riverdale/", "models/maps/riverdale_sectors/",
            "ui/minimaps/minimap_riverdale", "scenes/maps/Riverdale/riverdale.scene" )
ORDER = ( ".png", ".jpg", ".tga", ".exr", ".vmat", ".obj", ".mtl", ".vmdl", ".scene" )


def rank( path ):
    for k, suffix in enumerate( ORDER ):
        if path.endswith( suffix ):
            return k
    return len( ORDER )


def asset_target( relative ):
    """ Assets' own spelling of a path (ui/Minimaps on disk). """
    target = ASSETS / relative
    if target.exists():
        return target
    parent = ASSETS
    for part in Path( relative ).parts[:-1]:
        match = next( ( p for p in parent.iterdir() if p.is_dir() and p.name.lower() == part.lower() ), None ) if parent.exists() else None
        parent = match if match is not None else parent / part
    return parent / Path( relative ).name


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--scene", action="store_true", help="also publish the scene" )
    parser.add_argument( "--spatial-only", action="store_true", help="publish only verified tree sectors and, with --scene, the scene" )
    parser.add_argument( "--dry-run", action="store_true" )
    parser.add_argument( "--stage", default=str( STAGE ) )
    args = parser.parse_args()
    stage = Path( args.stage ).resolve()
    chosen = {}
    for source in stage.rglob( "*" ):
        if not source.is_file() or source.name.endswith( ( ".writing", ".meta", ".tmp", ".publishing" ) ):
            continue
        relative = source.relative_to( stage ).as_posix()
        if not relative.lower().startswith( tuple( a.lower() for a in ALLOWED ) ):
            continue
        if relative.endswith( ".scene" ) and not args.scene:
            continue
        if args.spatial_only and not ( relative.startswith( "models/maps/riverdale_sectors/" ) or
                                        relative == "scenes/maps/Riverdale/riverdale.scene" ):
            continue
        chosen[relative] = source
    copied = []
    for relative in sorted( chosen, key=lambda p: ( rank( p ), p ) ):
        source, target = chosen[relative], asset_target( relative )
        data = source.read_bytes()
        if target.exists() and target.read_bytes() == data:
            continue
        copied.append( { "path": target.relative_to( ASSETS ).as_posix(), "sha256": hashlib.sha256( data ).hexdigest(),
                         "new": not target.exists() } )
        if args.dry_run:
            continue
        if target.exists():
            backup = BACKUP / relative
            if not backup.exists():
                backup.parent.mkdir( parents=True, exist_ok=True )
                shutil.copy2( target, backup )
        target.parent.mkdir( parents=True, exist_ok=True )
        temp = target.with_name( target.name + ".publishing" )
        temp.write_bytes( data )
        temp.replace( target )
    report = { "copied": copied, "dry_run": args.dry_run }
    if not args.dry_run:
        out = ROOT / "output/riverdale/aaa/publish.json"
        out.parent.mkdir( parents=True, exist_ok=True )
        out.write_text( json.dumps( report, indent=1 ) + "\n", encoding="utf-8" )
    for item in copied:
        print( ( "new     " if item["new"] else "changed " ) + item["path"] )
    print( f"{len( copied )} file(s){' (dry run)' if args.dry_run else ''}" )


if __name__ == "__main__":
    main()
