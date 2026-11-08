"""Boxyard perimeter wall v1: installs the new wall (boxyard-model session, 2026-11-06).

    python install.py [--root DIR]

1. cut_old.py apply: boxyard_yard.obj without the old wall's drawn faces (and its mtl/vmdl as the generator writes them: the
   wall's four collision boxes stay in the vmdl). The originals are copied byte for byte into backup/ first.
2. scene_edit.py: the "Perimeter Wall" object (56 draw-only models) goes into boxyard.scene under the "Boxyard" root.
Then the editor needs a scene reload (close and reopen the Boxyard tab, or SceneEditorSession.Reload() on it; the swap.py in
output/model-trial-20261106/boxyard/ does install + reload and waits for the yard model to recompile). Safe to run again.
revert.py undoes both. --root points at another tree with the same Assets/ layout (the revert test uses a scratch copy).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import cut_old              # noqa: E402
import scene_edit           # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(scene_edit.ROOT))
    args = parser.parse_args()
    root = Path(args.root)
    cut_old.YARD_DIR = root / "Assets/models/maps/boxyard"
    cut_old.backup()
    kept = cut_old.apply()
    changed = scene_edit.add_group(root / scene_edit.SCENE)
    print(json.dumps({"yard paints kept": kept, "scene changed": changed}, indent=1))
