"""Apply one change to Riverdale's published models without rebuilding the rest of them.

    python Tools/riverdale_splice.py --baseline DIR --current DIR --out DIR model [model ...]

Riverdale's generator shares Railhead's prop and container code, which other work changes. A fresh build therefore
differs from the published models in places this change never touched. So the change is taken as the difference
between two builds made the same way, one without it (baseline) and one with it (current): the faces only the
baseline has are taken out of the published OBJ, the ones only the current build has are added. Every face taken
out must be found in the published model, or nothing is written. A face is its material and its corners'
positions, UVs and normals as written, kept as the polygon it was. The .mtl and the .vmdl get the materials the change brings (each added
material's line copied from the current build); a vmdl whose physics or other lines differ is refused.

Writes <out>/models/maps/riverdale/<model>.{obj,mtl,vmdl} for riverdale_publish.py --stage <out>.
"""
import argparse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = "models/maps/riverdale"


def read_obj(path):
    """ The header lines (before the first v), and the faces as ( material, corners ) with corners as text, kept as
    the polygons they were written as. """
    v, vt, vn, tris, header = [], [], [], [], []
    mat = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            tag = line[:3]
            if tag == "v  " or line.startswith("v "):
                v.append(line[2:].strip())
            elif line.startswith("vt "):
                vt.append(line[3:].strip())
            elif line.startswith("vn "):
                vn.append(line[3:].strip())
            elif line.startswith("usemtl "):
                mat = line.split(None, 1)[1].strip()
            elif line.startswith("f "):
                corners = []
                for c in line.split()[1:]:
                    a = c.split("/")
                    corners.append((v[int(a[0]) - 1], vt[int(a[1]) - 1] if len(a) > 1 and a[1] else "",
                                    vn[int(a[2]) - 1] if len(a) > 2 and a[2] else ""))
                tris.append((mat, tuple(corners)))
            elif not v:
                header.append(line)
    return header, tris


def write_obj(path, header, tris):
    index = {"v": {}, "vt": {}, "vn": {}}
    lines = {"v": [], "vt": [], "vn": []}

    def ref(kind, value):
        table = index[kind]
        if value not in table:
            table[value] = len(table) + 1
            lines[kind].append(f"{kind} {value}\n")
        return table[value]

    faces = []
    for mat, corners in tris:
        refs = []
        for p, uv, n in corners:
            a = str(ref("v", p))
            b = str(ref("vt", uv)) if uv else ""
            c = str(ref("vn", n)) if n else ""
            refs.append(f"{a}/{b}/{c}" if c else (f"{a}/{b}" if b else a))
        faces.append((mat, "f " + " ".join(refs) + "\n"))
    out = list(header) + lines["v"] + lines["vt"] + lines["vn"]
    current = None
    for mat, face in sorted(faces, key=lambda x: x[0] or ""):
        if mat != current:
            out.append(f"usemtl {mat}\n")
            current = mat
        out.append(face)
    tmp = path.with_name(path.name + ".writing")
    tmp.write_text("".join(out), encoding="utf-8", newline="\n")
    tmp.replace(path)


def mtl_blocks(path):
    blocks, name = {}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("newmtl "):
            name = line.split(None, 1)[1].strip()
            blocks[name] = [line]
        elif name:
            blocks[name].append(line)
    return blocks


def splice(model, baseline, current, out):
    pub = ROOT / "Assets" / FOLDER / f"{model}.obj"
    base = Path(baseline) / FOLDER / f"{model}.obj"
    cur = Path(current) / FOLDER / f"{model}.obj"
    header, published = read_obj(pub)
    _, b = read_obj(base)
    _, c = read_obj(cur)
    bc, cc = Counter(b), Counter(c)
    removed, added = bc - cc, cc - bc
    have = Counter(published)
    missing = removed - have
    assert not missing, f"{model}: {sum(missing.values())} of the change's {sum(removed.values())} removed faces aren't published"
    result = list((have - removed).elements()) + list(added.elements())
    target = Path(out) / FOLDER
    target.mkdir(parents=True, exist_ok=True)
    write_obj(target / f"{model}.obj", header, result)
    mats = {m for m, _ in result}
    old_mats = {m for m, _ in published}
    new_mats = sorted(mats - old_mats)
    # The material library: the published one, plus the new materials' blocks from the current build.
    blocks = mtl_blocks(pub.with_suffix(".mtl"))
    cur_blocks = mtl_blocks(cur.with_suffix(".mtl"))
    for m in new_mats:
        blocks[m] = cur_blocks[m]
    (target / f"{model}.mtl").write_text("".join(line for name in sorted(blocks) for line in blocks[name]), encoding="utf-8", newline="\n")
    # The vmdl: the published one with the new materials' remap lines from the current build.
    vpub = pub.with_suffix(".vmdl").read_text(encoding="utf-8").splitlines(keepends=True)
    vcur = cur.with_suffix(".vmdl").read_text(encoding="utf-8").splitlines(keepends=True)
    remap = lambda lines: {l for l in lines if "from = \"" in l and ".vmat\"" in l}
    others_pub = [l for l in vpub if l not in remap(vpub)]
    others_cur = [l for l in vcur if l not in remap(vcur)]
    assert [l.strip() for l in others_pub] == [l.strip() for l in others_cur], f"{model}: vmdl differs beyond its materials"
    adds = [l for l in vcur if l in remap(vcur) and any(f"\"{m}.vmat\"" in l for m in new_mats)]
    lines = list(vpub)
    if adds:
        last = max(i for i, l in enumerate(lines) if l in remap(vpub))
        if not lines[last].rstrip().endswith(","):
            lines[last] = lines[last].rstrip("\r\n").rstrip() + ",\n"
        adds = [a if a.rstrip().endswith(",") else a.rstrip("\r\n") + ",\n" for a in adds]
        adds[-1] = adds[-1].rstrip("\r\n").rstrip().rstrip(",") + "\n"
        lines[last + 1:last + 1] = adds
    (target / f"{model}.vmdl").write_text("".join(lines), encoding="utf-8", newline="")
    print(f"{model}: published {len(published)} faces, -{sum(removed.values())} +{sum(added.values())} -> "
          f"{len(result)}; new materials {new_mats}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("models", nargs="+")
    args = parser.parse_args()
    for model in args.models:
        splice(model, args.baseline, args.current, args.out)


if __name__ == "__main__":
    main()
