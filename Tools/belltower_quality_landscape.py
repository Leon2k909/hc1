"""Stage a generated landscape texture bundle for guarded native import.

Generate with belltower_vista_paint.py --out first. This prepares only the
manifest and material source; import-landscape.cs.txt owns asset writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
import belltower_vista_paint as P

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/quality"

def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=OUT/"landscape-v2-staging")
    parser.add_argument("--target",default="materials/belltower/vista")
    args = parser.parse_args()
    source = args.source.resolve()
    target = (ROOT/"Assets"/args.target).resolve()
    if not source.is_relative_to(OUT) or not target.is_relative_to(ROOT/"Assets/materials/belltower/vista"):
        raise ValueError("Landscape staging paths must stay in their project directories")
    material = OUT / "landscape-material-staged.vmat"
    material.write_text(P.vmat_text(args.target),encoding="utf-8")
    files = []
    for zone, _ in P.ZONES:
        for suffix in ("color.jpg","kind.png","normal.jpg"):
            files.append(source/f"vista_{zone}_{suffix}")
    files += [source/f"detail_{name}.png" for name in ("grass","soil","stone")]
    payload = []
    dimensions = {}
    for path in files+[material]:
        name = "vista_land.vmat" if path == material else path.name
        if path != material:
            with Image.open(path) as image:
                dimensions[name] = list(image.size)
                if min(image.size) < 512:
                    raise ValueError("Landscape input is unexpectedly small: " + name)
        destination = target/name
        payload.append({"path":destination.relative_to(ROOT/"Assets").as_posix(),
            "source":path.relative_to(ROOT).as_posix(),"sha256":sha(path),
            "expected_sha256":sha(destination) if destination.exists() else None})
    (OUT/"landscape-import.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    (OUT/"landscape-textures-staged.json").write_text(json.dumps({
        "generator":"Tools/belltower_vista_paint.py","generator_sha256":sha(Path(P.__file__)),
        "target":args.target,"dimensions":dimensions,"assets":payload},indent=2)+"\n",encoding="utf-8")
    print(f"Validated and staged {len(payload)} landscape assets. Native import remains pending.")

if __name__ == "__main__":
    main()
