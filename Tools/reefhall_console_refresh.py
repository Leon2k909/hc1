"""Stage the control-room model without rewriting the scene or any other room.

Run before/after a console edit with --out pointing outside Assets. Import the
staged files through the running editor, then compile reefhall_control.vmdl.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import reefhall_map as R


def stage(out):
    index, (_, builder, flips) = next((i, row) for i, row in enumerate(R.ROOMS) if row[0] == "control")
    model, inside, lights = R.build_mirrored(builder, np.random.default_rng(1000 + index), flips)
    R.configure(model)
    triangles = R.K.write_model(out, R.RESOURCE_DIR, "reefhall_control", model)
    material_dir = out / "materials"
    material_dir.mkdir(parents=True, exist_ok=True)
    for name, source in R.RC.materials().items():
        (material_dir / f"{name}.vmat").write_text(source, encoding="utf-8", newline="\n")
    R.RC.MONITORS.write_textures(material_dir)
    boxes = [[np.asarray(c).tolist(), np.asarray(a).tolist(), np.asarray(s).tolist(), p] for c, a, s, p in model.boxes]
    hulls = [[np.asarray(points).tolist(), surface] for points, surface in model.hulls]
    collision = json.dumps([boxes, hulls], sort_keys=True).encode()
    report = {"triangles": triangles, "boxes": len(boxes), "hulls": len(hulls),
              "collision_sha256": hashlib.sha256(collision).hexdigest(), "lights": len(lights),
              "files": sorted(p.name for p in out.iterdir() if p.suffix in (".vmdl", ".obj", ".mtl"))}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    stage(parser.parse_args().out)
