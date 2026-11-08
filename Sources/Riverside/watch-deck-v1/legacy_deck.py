"""Regenerate the old watch deck exactly as the Pad holds it (read-only reference, writes one OBJ under output/).

The Pad was built by an older riverdale_parts.railing/stairs than the working tree's, so the current Tools draw a
different deck. Make a snapshot of the generator that built it and point this script at it:

    git archive 3bec244c Tools | tar -x -C <empty dir>
    python legacy_deck.py <that dir>/Tools

It draws `riverside_map.watch_deck(m, R.HIGH)` without the sandbag barricade (those bags are separate models), paints it
the way the map does, and writes output/riverside/watch-deck-v1/legacy_deck_3bec244c.obj: 812 triangles, 48 rs_concrete and
764 rs_wood, matching the Pad's own vertices exactly.
"""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
tools = Path(sys.argv[1]).absolute()
sys.path.insert(0, str(tools))
import map_kit as K          # noqa: E402
import riverside_parts as P  # noqa: E402
import riverside_map as R    # noqa: E402

assert Path(K.__file__).absolute().parent == tools, K.__file__
m = K.Model()
P.sandbag_wall = lambda *a, **k: None
R.watch_deck(m, R.HIGH)
R.configure(m)
out = ROOT / 'output/riverside/watch-deck-v1/legacy_deck_3bec244c.obj'
print(K.write_obj(out, m, 'legacy_deck_3bec244c'), 'triangles', out)
