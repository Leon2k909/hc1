"""Boxyard perimeter wall v1: puts the old wall back (boxyard-model session, 2026-11-06).

    python revert.py [--root DIR]

1. boxyard_yard.obj / .vmdl / .mtl are copied back from backup/ byte for byte (the old wall's faces return to the yard model).
2. The "Perimeter Wall" object is taken out of boxyard.scene (every other byte of the file stays as it was).
The new models and materials stay on disk, unused (Assets/models/props/boxyard/perimeter_wall_v1/ and
Assets/materials/boxyard/perimeter_wall_v1/); nothing is deleted. Also set OLD_WALL_IN_YARD = True in Tools/boxyard_map.py so a
later run of the generator keeps the old wall. Then reload the scene in the editor (reopen the Boxyard tab, or SceneEditorSession.Reload()
on it; output/model-trial-20261106/boxyard/swap.py revert does revert + reload and waits for the yard model to recompile).
Safe to run again. --root points at another tree with the same Assets/ layout (the test of this script uses a scratch copy).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import scene_edit           # noqa: E402

BACKUP = HERE / "backup"
FILES = ("boxyard_yard.obj", "boxyard_yard.vmdl", "boxyard_yard.mtl")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def revert(root):
    yard = Path(root) / "Assets/models/maps/boxyard"
    manifest = json.loads((BACKUP / "manifest.json").read_text())
    out = {}
    # the OBJ first, the vmdl last (the editor compiles a file as it lands)
    for name in FILES:
        data = (BACKUP / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == manifest[name]["sha256"], f"backup/{name} is not the saved original"
        target = yard / name
        if not target.exists() or target.read_bytes() != data:
            temp = target.with_name(target.name + ".writing")
            temp.write_bytes(data)
            temp.replace(target)
            out[name] = "restored"
        else:
            out[name] = "already the original"
    removed, changed = scene_edit.remove_group(Path(root) / scene_edit.SCENE)
    out["scene: Perimeter Wall objects removed"] = removed
    out["yard files equal the saved originals"] = all(sha(yard / n) == manifest[n]["sha256"] for n in FILES)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(scene_edit.ROOT))
    print(json.dumps(revert(parser.parse_args().root), indent=1))
