"""
Publishes Cerro Blanco's staged build into Assets: the map script's run with --stage (output/cerroblanco/stage-v2: the
fit-out, the landscape, the scene) and the quality pass's materials and shaders (output/cerroblanco/stage).

    python Tools/cerroblanco_publish.py [--scene] [--dry-run]

Only files that differ from Assets are copied, each through a temporary file renamed over the old one (the editor
compiles a changed file straight away), the old one first backed up to output/cerroblanco/before-v2/ (once). Left out:
- cb_glass.vmat: Assets has the accepted coated-glass candidate (cerroblanco_quality_glass.publish_accepted);
- the base dressing and glass models: the scene draws the quality pass's dressing_v2 and the breakable panes, and their
  collision (the vmdls and hull OBJs) is unchanged;
- the scene, unless --scene: copy it only while the editor doesn't have Cerro Blanco open with changes of its own.
Writes output/cerroblanco/publish-v2.json: what was copied, in the order the editor should compile it
(Sources/CerroBlanco/editor/compile-v2.cs.txt).
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"
STAGES = [ ROOT / "output/cerroblanco/stage-v2", ROOT / "output/cerroblanco/stage" ]
BACKUP = ROOT / "output/cerroblanco/before-v2"
SKIP = { "materials/cerroblanco/cb_glass.vmat", "models/maps/cerroblanco/cerroblanco_dressing.obj",
         "models/maps/cerroblanco/cerroblanco_glass.obj", "models/maps/cerroblanco/cerroblanco_glass.vmdl",
         "models/maps/cerroblanco/cerroblanco_glass.mtl", "models/maps/cerroblanco/cerroblanco_glass_hulls_glass.obj" }
ALLOWED = ( "materials/cerroblanco/", "models/maps/cerroblanco/", "shaders/cerroblanco_", "ui/Minimaps/minimap_cerroblanco",
            "scenes/maps/CerroBlanco/cerroblanco.scene" )
ORDER = ( ".shader", ".png", ".jpg", ".vmat", ".obj", ".mtl", ".vmdl", ".scene" )


def rank( path ):
    for k, suffix in enumerate( ORDER ):
        if path.endswith( suffix ):
            return k
    return len( ORDER )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--scene", action="store_true", help="also publish the scene" )
    parser.add_argument( "--dry-run", action="store_true" )
    args = parser.parse_args()
    chosen = {}
    for stage in STAGES:
        for source in stage.rglob( "*" ):
            if not source.is_file() or source.name.endswith( ( ".writing", ".meta" ) ):
                continue
            relative = source.relative_to( stage ).as_posix()
            if relative in chosen or relative in SKIP or not relative.startswith( ALLOWED ):
                continue
            if relative.endswith( ".scene" ) and not args.scene:
                continue
            chosen[relative] = source
    copied = []
    for relative in sorted( chosen, key=lambda p: ( rank( p ), p ) ):
        source, target = chosen[relative], ASSETS / relative
        data = source.read_bytes()
        if target.exists() and target.read_bytes() == data:
            continue
        copied.append( { "path": relative, "sha256": hashlib.sha256( data ).hexdigest(), "new": not target.exists() } )
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
        ( ROOT / "output/cerroblanco/publish-v2.json" ).write_text( json.dumps( report, indent=1 ) + "\n", encoding="utf-8" )
    for item in copied:
        print( ( "new     " if item["new"] else "changed " ) + item["path"] )
    print( f"{len( copied )} file(s){' (dry run)' if args.dry_run else ''}" )


if __name__ == "__main__":
    main()
