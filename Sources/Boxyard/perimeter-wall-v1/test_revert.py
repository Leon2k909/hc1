"""Boxyard perimeter wall v1: tests install.py and revert.py on a scratch copy of the four files they touch (boxyard-model
session, 2026-11-06). Nothing under Assets/ is written.

    python test_revert.py [--from-git]

Copies the scene and the three yard-model files into a scratch tree (the working copies, or with --from-git the committed
versions, which are the originals), installs, checks the changes, reverts, and checks that all four files are byte for byte the
copies again; reverting twice, and installing twice, change nothing more.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import scene_edit           # noqa: E402

ROOT = scene_edit.ROOT
FILES = [scene_edit.SCENE] + [f"Assets/models/maps/boxyard/boxyard_yard.{e}" for e in ("obj", "vmdl", "mtl")]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(script, root):
    r = subprocess.run([sys.executable, str(HERE / script), "--root", str(root)], capture_output=True, text=True,
                       encoding="utf-8", env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, (script, r.stdout, r.stderr)
    return json.loads(r.stdout)


def main(from_git=False):
    results = {}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        for rel in FILES:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            if from_git:
                data = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, check=True).stdout
                (root / rel).write_bytes(data)
            else:
                shutil.copyfile(ROOT / rel, root / rel)
        before = {rel: sha(root / rel) for rel in FILES}
        results["started from"] = "git HEAD" if from_git else "working copies"

        first = run("install.py", root)
        after_install = {rel: sha(root / rel) for rel in FILES}
        results["install changed the scene"] = after_install[FILES[0]] != before[FILES[0]]
        results["install changed the yard obj"] = after_install[FILES[1]] != before[FILES[1]]
        results["scene now holds the group"] = len(scene_edit.has_group(root / scene_edit.SCENE)) == 1
        results["install again changes nothing"] = (run("install.py", root) and
                                                    {rel: sha(root / rel) for rel in FILES} == after_install)

        reverted = run("revert.py", root)
        after_revert = {rel: sha(root / rel) for rel in FILES}
        results["revert restores all four files byte for byte"] = after_revert == before
        results["scene holds no group"] = len(scene_edit.has_group(root / scene_edit.SCENE)) == 0
        results["revert again changes nothing"] = (run("revert.py", root) and
                                                   {rel: sha(root / rel) for rel in FILES} == before)
        run("install.py", root)
        run("revert.py", root)
        results["install then revert once more"] = {rel: sha(root / rel) for rel in FILES} == before
        results["revert report"] = reverted
    results["ALL PASSED"] = all(v is True for k, v in results.items() if k not in ("started from", "revert report"))
    return results


if __name__ == "__main__":
    out = main("--from-git" in sys.argv)
    print(json.dumps(out, indent=1))
    raise SystemExit(0 if out["ALL PASSED"] else 1)
