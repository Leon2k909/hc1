""" A render-only view of the props stage with the other areas' staged materials under it.

The props stage only holds the materials the props area draws, so a Cycles render of it showed every paint another
area stages (the shed's rw_steel_soot, the backdrop's bd_*) in magenta. This links (hard links, falling back to copies)
into <props stage>/render_mix:

    models/, scenes/            from the props stage
    materials/                  the backdrop's, dressing's, structure's and materials' stages, then the props stage's
                                own on top (later wins)

so `render.py --stage <props stage>/render_mix` sees the whole map's current materials. render_mix is never integrated:
it's only a lens for renders.

    python Tools/railhead_props_mix.py [--stage <props stage>]
"""
import argparse
import os
import shutil
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
STAGES = ROOT / "output/railhead/stage"
ORDER = ( "backdrop", "dressing", "structure", "materials" )


def link( src, dst ):
    dst.parent.mkdir( parents=True, exist_ok=True )
    if dst.exists():
        try:
            if os.path.samefile( src, dst ):
                return
        except OSError:
            pass
        dst.unlink()
    try:
        os.link( src, dst )
    except OSError:
        shutil.copy2( src, dst )


def build( stage ):
    stage = Path( stage )
    mix = stage / "render_mix"
    wanted = {}
    for name in ORDER:
        base = STAGES / name / "materials"
        if base.is_dir():
            for f in base.rglob( "*" ):
                if f.is_file():
                    wanted[f.relative_to( STAGES / name )] = f
    for sub in ( "materials", "models", "scenes" ):
        base = stage / sub
        if base.is_dir():
            for f in base.rglob( "*" ):
                if f.is_file():
                    wanted[f.relative_to( stage )] = f
    for rel, src in wanted.items():
        link( src, mix / rel )
    # Drop what's no longer wanted (a renamed model or material).
    for f in list( mix.rglob( "*" ) ):
        if f.is_file() and f.relative_to( mix ) not in wanted:
            f.unlink()
    print( f"render_mix: {len( wanted )} files in {mix}" )
    return mix


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument( "--stage", default=str( STAGES / "props" ) )
    build( ap.parse_args().stage )
