"""Swap only the "Pipe Solids" collider group of a staged Riverdale scene into the saved scene.

    python Tools/riverdale_merge_pipe_solids.py --stage output/riverdale/aaa/round2/stage [--write]

The saved scene carries editor-made state the generator doesn't reproduce byte for byte (baked lighting, merged
collider groups, the forest sectors), so a moved pipe's box colliders are carried over on their own. Everything else in
the saved scene is kept verbatim; the result is checked to differ only inside that group. Without --write it reports.
"""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / "Assets/scenes/maps/Riverdale/riverdale.scene"
GROUP = "Pipe Solids"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    staged = json.loads((Path(args.stage) / "scenes/maps/Riverdale/riverdale.scene").read_text(encoding="utf-8"))
    raw = SAVED.read_bytes()
    crlf = b"\r\n" in raw
    saved = json.loads(raw.decode("utf-8"))
    assert json.dumps(saved, indent=2) == raw.decode("utf-8").replace("\r\n", "\n").rstrip("\n"), "saved scene doesn't round-trip"
    new = next(g for g in staged["GameObjects"] if g.get("Name") == GROUP)
    index = next(i for i, g in enumerate(saved["GameObjects"]) if g.get("Name") == GROUP)
    old = saved["GameObjects"][index]
    print(f"{GROUP}: {len(old['Children'])} colliders saved, {len(new['Children'])} staged")
    before = {json.dumps(c["Components"], sort_keys=True) + c.get("Position", "") for c in old["Children"]}
    after = {json.dumps(c["Components"], sort_keys=True) + c.get("Position", "") for c in new["Children"]}
    print(f"  {len(before - after)} removed or moved, {len(after - before)} added or moved")
    saved["GameObjects"][index] = new
    others = [json.dumps(g, sort_keys=True) for i, g in enumerate(saved["GameObjects"]) if i != index]
    kept = [json.dumps(g, sort_keys=True) for i, g in enumerate(json.loads(raw.decode("utf-8"))["GameObjects"]) if i != index]
    assert others == kept, "something besides the pipe solids would change"
    text = json.dumps(saved, indent=2)
    if crlf:
        text = text.replace("\n", "\r\n")
    if args.write:
        tmp = SAVED.with_name(SAVED.name + ".writing")
        tmp.write_bytes(text.encode("utf-8"))
        os.replace(tmp, SAVED)
        print("written", SAVED.relative_to(ROOT))


if __name__ == "__main__":
    main()
