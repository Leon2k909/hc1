"""Boxyard perimeter wall v1: proves Tools/boxyard_map.py reproduces what was installed (boxyard-model session, 2026-11-06).

    python verify_generator.py

Runs nothing that writes into Assets/ or Tools/. It checks that
  1. wall_objects() holds the same 56 instances (names, models, positions, yaws) as build.py layout(), and
  2. the generator's yard model, built with OLD_WALL_IN_YARD = False into a scratch folder, is the same OBJ text as the yard
     model cut_old.py writes (and so the same triangles, uvs and normals as the original with the wall's faces taken out), and
     keeps the same vmdl (the four wall collision boxes and the floor's).
"""
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Tools"))

import build as PW          # noqa: E402
import objcut               # noqa: E402
import cut_old              # noqa: E402
import boxyard_map as B     # noqa: E402
import map_kit as K         # noqa: E402


def yaw_of(rotation):
    x, y, z, w = (float(t) for t in rotation.split(","))
    return math.degrees(2.0 * math.atan2(z, w))


def check_instances():
    assert B.OLD_WALL_IN_YARD is False
    parent = B.wall_objects()
    assert len(parent) == 1 and parent[0]["Name"] == "Perimeter Wall", parent
    kids = parent[0]["Children"]
    want = PW.layout()
    assert len(kids) == len(want) == 56, (len(kids), len(want))
    worst_pos = worst_yaw = 0.0
    for kid, (name, stem, pos, yaw) in zip(kids, want):
        assert kid["Name"] == name, (kid["Name"], name)
        model = kid["Components"][0]["Model"]
        assert model == f"{PW.MODEL_DIR}/{stem}.vmdl", (model, stem)
        got = [float(t) for t in kid["Position"].split(",")]
        worst_pos = max(worst_pos, max(abs(g - p) for g, p in zip(got, pos)))
        d = (yaw_of(kid["Rotation"]) - yaw + 180.0) % 360.0 - 180.0
        worst_yaw = max(worst_yaw, abs(d))
        assert kid["Components"][0]["__type"] == "Sandbox.ModelRenderer" and len(kid["Components"]) == 1
        assert kid["Children"] == []
    assert worst_pos < 0.01 and worst_yaw < 1e-4, (worst_pos, worst_yaw)
    keys = {k["__guid"] for k in kids}
    assert len(keys) == 56
    return {"instances": len(kids), "worst position error in": worst_pos, "worst yaw error deg": worst_yaw}


def check_yard():
    model = B.yard()
    B.configure(model)
    with tempfile.TemporaryDirectory() as scratch:
        K.write_model(Path(scratch), B.RESOURCE_DIR, "boxyard_yard", model)
        made = {n: (Path(scratch) / n).read_bytes() for n in ("boxyard_yard.obj", "boxyard_yard.vmdl", "boxyard_yard.mtl")
                if (Path(scratch) / n).exists()}
    head, v, vt, vn, blocks = cut_old.parts()
    keep = {p for p, _ in blocks} - cut_old.WALL_PAINTS
    cut_text = objcut.build(head, v, vt, vn, blocks, keep).encode()
    out = {"generator obj bytes": len(made["boxyard_yard.obj"]), "cut obj bytes": len(cut_text),
           "obj identical": made["boxyard_yard.obj"].replace(b"\r\n", b"\n") == cut_text}
    manifest = json.loads((cut_old.BACKUP / "manifest.json").read_text())
    for n in ("boxyard_yard.vmdl", "boxyard_yard.mtl"):
        if n in made:
            out[n + " identical to the original"] = hashlib.sha256(made[n].replace(b"\r\n", b"\n")).hexdigest() == manifest[n]["sha256"]
    return out


if __name__ == "__main__":
    print(json.dumps({"scene objects": check_instances(), "yard model": check_yard()}, indent=1))
