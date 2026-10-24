"""Compare the authored terrain and boulders independently of shifted OBJ vertex/material indices."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
PAINTS = (b"ar_terrain", b"ar_rock")


def signatures(path):
    ranges = {paint: [[10**10, 0] for _ in range(3)] for paint in PAINTS}
    offsets = {}
    faces = {paint: hashlib.sha256() for paint in PAINTS}
    counts = {paint: 0 for paint in PAINTS}
    paint = b""
    with path.open("rb") as stream:
        for line in stream:
            if line.startswith(b"usemtl "):
                paint = line.split()[1]
            elif paint in ranges and line.startswith(b"f "):
                indices = [tuple(map(int, point.split(b"/"))) for point in line.split()[1:]]
                offsets.setdefault(paint, indices[0])
                normalized = [tuple(value - offsets[paint][i] for i, value in enumerate(point)) for point in indices]
                faces[paint].update(repr(normalized).encode())
                counts[paint] += 1
                for point in indices:
                    for i, value in enumerate(point):
                        ranges[paint][i][0] = min(ranges[paint][i][0], value)
                        ranges[paint][i][1] = max(ranges[paint][i][1], value)
    attributes = {paint: [hashlib.sha256() for _ in range(3)] for paint in PAINTS}
    counts_attr = [0, 0, 0]
    prefixes = {b"v": 0, b"vt": 1, b"vn": 2}
    with path.open("rb") as stream:
        for line in stream:
            kind = prefixes.get(line.split(b" ", 1)[0])
            if kind is None:
                continue
            counts_attr[kind] += 1
            for paint in PAINTS:
                lo, hi = ranges[paint][kind]
                if lo <= counts_attr[kind] <= hi:
                    attributes[paint][kind].update(line)
    return {paint.decode(): {"triangles": counts[paint], "faces": faces[paint].hexdigest(),
            "attributes": [value.hexdigest() for value in attributes[paint]]} for paint in PAINTS}


directory = ROOT / "output/ares/outpost-20261019"
before = signatures(directory / "before/Assets/models/maps/ares/ares_backdrop.obj")
after = signatures(directory / "stage/models/maps/ares/ares_backdrop.obj")
report = {"terrain_and_boulders_identical": before == after, "before": before, "after": after}
(directory / "retained-geometry.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
if before != after:
    raise SystemExit("The retained terrain or boulder geometry changed")
