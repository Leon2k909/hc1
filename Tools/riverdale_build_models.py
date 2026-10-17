"""Builds Riverdale's models (no scene, the far backdrop stubbed out) into a stage, from an optional source dir first:
the two builds Tools/riverdale_splice.py compares.

    python Tools/riverdale_build_models.py <stage> [<source dir ahead of Tools>]
"""
import os, runpy, sys
tools = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = ([os.path.abspath(sys.argv[2])] if len(sys.argv) > 2 else []) + [tools]
import importlib
if len(sys.argv) > 2:
    # Load the source dir's modules before anything else: riverdale_materials puts Tools back at the path's front.
    for name in sorted(f[:-3] for f in os.listdir(sys.argv[2]) if f.endswith(".py") and f != "riverdale_map.py"):
        print("from source dir:", importlib.import_module(name).__file__, flush=True)
import map_kit as K
import riverdale_backdrop as BD
BD.build = lambda: (K.Model(), K.Model())
BD.extra_models = lambda: []
script = os.path.join(sys.argv[2] if len(sys.argv) > 2 else tools, "riverdale_map.py")
print("map script:", script, flush=True)
sys.argv = [script, "--stage", sys.argv[1], "--no-scene"]
runpy.run_path(script, run_name="__main__")
