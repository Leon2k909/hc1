"""Boxyard perimeter wall v1: take the old wall's faces out of the yard model (boxyard-model session, 2026-11-06).

The old wall was drawn inside Assets/models/maps/boxyard/boxyard_yard.obj as three paints that nothing else in that model
uses: bx_wall_panel (28 panels x 3 faces), bx_steel_dark (32 posts x 6 faces) and bx_galv (8 wire strands). The model's
collision (five boxes in boxyard_yard.vmdl) does not come from those faces and is not touched.

    python cut_old.py extract     writes backup/ (byte-exact copies, first run only) and old_wall.obj/.mtl (the BEFORE geometry)
    python cut_old.py apply       rewrites boxyard_yard.obj without the wall's faces, and the mtl and vmdl as the generator
                                  (Tools/boxyard_map.py, OLD_WALL_IN_YARD = False) writes them: without the wall paints' entries
    python cut_old.py check       compares the live yard model with the backup and the cut

revert.py puts the three backed-up files back byte for byte.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import objcut                                           # noqa: E402
from build import atomic_write                          # noqa: E402

ROOT = HERE.parents[2]
YARD_DIR = ROOT / "Assets/models/maps/boxyard"
FILES = ("boxyard_yard.obj", "boxyard_yard.vmdl", "boxyard_yard.mtl")
BACKUP = HERE / "backup"
WALL_PAINTS = {"bx_wall_panel", "bx_steel_dark", "bx_galv"}
EXPECT = {"bx_wall_panel": 168, "bx_steel_dark": 384, "bx_galv": 64}      # triangles in the original


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def backup():
    BACKUP.mkdir(exist_ok=True)
    manifest = BACKUP / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text())
    info = {}
    for name in FILES:
        data = (YARD_DIR / name).read_bytes()
        (BACKUP / name).write_bytes(data)
        info[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    manifest.write_text(json.dumps(info, indent=1) + "\n")
    return info


def parts():
    text = (BACKUP / "boxyard_yard.obj").read_text()           # always cut from the backup: re-running is idempotent
    return objcut.parse(text)


def extract():
    info = backup()
    head, v, vt, vn, blocks = parts()
    counts = {p: len(t) for p, t in blocks}
    for paint, want in EXPECT.items():
        assert counts.get(paint) == want, (paint, counts.get(paint), want)
    wall = objcut.build(head, v, vt, vn, blocks, WALL_PAINTS, mtl_name="old_wall.mtl",
                        comment="# The old perimeter wall, cut from boxyard_yard.obj (Sources/Boxyard/perimeter-wall-v1/cut_old.py)")
    (HERE / "old_wall.obj").write_text(wall, newline="\n")
    (HERE / "old_wall.mtl").write_text("".join(f"newmtl {p}\nKd 1 1 1\nd 1\n" for p in sorted(WALL_PAINTS)), newline="\n")
    rest = objcut.build(head, v, vt, vn, blocks, {p for p, _ in blocks} - WALL_PAINTS)
    return info, counts, objcut.triangle_count(blocks, WALL_PAINTS), len(rest)


def generator_files():
    """ The yard model's mtl and vmdl as Tools/boxyard_map.py writes them now that the wall is drawn by separate models: the
    two original files without the three wall paints' entries (verify_generator.py shows the OBJ it writes is the cut below). """
    import tempfile
    sys.path.insert(0, str(ROOT / "Tools"))
    sys.dont_write_bytecode = True
    import boxyard_map as B
    import map_kit as K
    assert B.OLD_WALL_IN_YARD is False
    model = B.yard()
    B.configure(model)
    with tempfile.TemporaryDirectory() as scratch:
        K.write_model(Path(scratch), B.RESOURCE_DIR, "boxyard_yard", model)
        return ((Path(scratch) / "boxyard_yard.mtl").read_text(), (Path(scratch) / "boxyard_yard.vmdl").read_text())


def apply():
    """ The OBJ first, then the mtl, the vmdl last (the editor compiles a file as it lands). """
    backup()
    head, v, vt, vn, blocks = parts()
    keep = {p for p, _ in blocks} - WALL_PAINTS
    mtl, vmdl = generator_files()
    atomic_write(YARD_DIR / "boxyard_yard.obj", objcut.build(head, v, vt, vn, blocks, keep))
    atomic_write(YARD_DIR / "boxyard_yard.mtl", mtl)
    atomic_write(YARD_DIR / "boxyard_yard.vmdl", vmdl)
    return {p: len(t) for p, t in blocks if p in keep}


def check():
    manifest = json.loads((BACKUP / "manifest.json").read_text())
    out = {}
    for name in FILES:
        live = sha(YARD_DIR / name)
        out[name] = "original" if live == manifest[name]["sha256"] else "changed"
    head, v, vt, vn, blocks = objcut.parse((YARD_DIR / "boxyard_yard.obj").read_text())
    out["live paints"] = {p: len(t) for p, t in blocks}
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    print(json.dumps({"extract": extract, "apply": apply, "check": check}[cmd](), indent=1, default=str))
