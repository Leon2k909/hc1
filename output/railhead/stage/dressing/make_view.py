"""Builds output/railhead/stage/dressing/_view: a render-only stage made of hard links (no copies) to the dressing
stage's models, scene and dress materials, plus the materials agent's staged materials, so Cycles renders of the
dressing show the other agents' current materials instead of magenta. Nothing here is for integration."""
import os
import shutil
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
VIEW = HERE / "_view"
SOURCES = [ ( HERE.parent / "structure" / "materials", VIEW / "materials" ),
            ( HERE.parent / "backdrop" / "materials", VIEW / "materials" ),
            ( HERE.parent / "props" / "materials", VIEW / "materials" ),
            ( HERE.parent / "materials" / "materials", VIEW / "materials" ),
            ( HERE / "materials", VIEW / "materials" ),            # mine last: they win
            ( HERE / "models", VIEW / "models" ),
            ( HERE / "scenes", VIEW / "scenes" ) ]


def link_tree( src, dst ):
    for root, _, files in os.walk( src ):
        out = dst / Path( root ).relative_to( src )
        out.mkdir( parents=True, exist_ok=True )
        for f in files:
            target = out / f
            if target.exists():
                target.unlink()
            try:
                os.link( Path( root ) / f, target )
            except OSError:
                shutil.copy2( Path( root ) / f, target )


if __name__ == "__main__":
    if VIEW.exists():
        shutil.rmtree( VIEW )
    for src, dst in SOURCES:
        if src.exists():
            link_tree( src, dst )
    print( "view stage at", VIEW )
