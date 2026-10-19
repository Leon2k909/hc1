"""Raise the MWII 1x optics that sit far below a real co-witness height onto taller mounts.

python Tools/optic_risers.py [--check]

An AR's iron sight line is 1.41 over its rail: that's the absolute co-witness height red dot mounts are made to (SIG's
ROMEO8T manual; Scalarworks' LEAP/01 and fixed front sight, 1.42). Lower 1/3 mounts put the optical axis 1.516
(Trijicon's AC32059 for the RMR), 1.535 (Aimpoint's 39 mm) or 1.57 (Scalarworks) over the rail, so the irons show in
the window's lower third. The M16A4 keeps its front sight post up under an optic, so its 1x optics must sit at those
heights for the post to co-witness with the dot (kastov_prefabs optic_sight_lines). These five sat 0.3-0.47 under them,
so on the M16 the eye had to leave their windows to bring the post to its mark:

  the three Mini Red Dots (window 1.08-1.10 over the rail on their riser), lower 1/3: 1.55
  the Tube Red Dot (1.25 on its riser), lower 1/3: 1.55
  the Tube Collimator (1.10 on its own mount), absolute: 1.41

Each mount grows at a cut through a plain, vertical part of it (RISERS: in the riser's block over the rail clamp, or the
tube's mount block): everything over the cut goes up, and the faces crossing it are split there, with a band between
the two halves that repeats the texture's row at the cut. So the riser reads as the same anodised block, taller, its
edges and highlights running on, with no stretched texture. The rail clamp stays where it was.

The windows go up by the same amount on every gun, so every part made from these models (the M4's MWII parts, which the
ported guns share, and the MP5's) lowers its OpticAimOffset z by it: the eye stays where it was in the window, and since
the reticles are collimated the dots stay where they were on the screen.

The ripped OBJs and the parts' original offsets are in Backups/optic_risers_rip/, which every run starts from, so a
rerun writes the same files. --check lists the files a run would change.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "Assets"
MODELS = ASSETS / "attachments/mw2022/models"
BACKUP = ROOT / "Backups/optic_risers_rip"

ABSOLUTE = 1.41  # the iron sight line over the rail
LOWER_THIRD = 1.55  # 0.14 over it: kastov_prefabs' and Hc1M16OpticQa's lower 1/3 drop at the post

# Model -> (cut height, the window centre's height over the rail it should have). Heights are in the model's own space,
# where the rail's top is z 0.
RISERS = {
    # riser03's block, between the bolt heads over the rail clamp and the red dot's plate (z 0.121-0.135 has no vertex).
    "att_vm_minireddot01_tall": (0.128, LOWER_THIRD),
    "att_vm_minireddot02_tall": (0.128, LOWER_THIRD),
    "att_vm_minireddot03_tall": (0.128, LOWER_THIRD),
    # riser02's column, under its window (all its faces at 0.17 are vertical).
    "att_vm_reflex_west02_tall": (0.17, LOWER_THIRD),
    # The mount block under the tube's ring (16 of the 54 faces at 0.385 lean, by at most 15 degrees, in a side slot).
    "att_vm_holo_east01": (0.385, ABSOLUTE),
}


def obj_path(model: str) -> Path:
    return MODELS / model / f"{model}.obj"


def read_obj(path: Path):
    """Lines, and the vertex data (OBJ x, y, z; u, v; normal) of an OBJ whose v, vt and vn lines interleave and whose
    faces are triangles of i/i/i corners (every MWII optic converter's output)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    positions, uvs, normals = [], [], []
    for line in lines:
        if line.startswith("v "):
            positions.append([float(v) for v in line.split()[1:4]])
        elif line.startswith("vt "):
            uvs.append([float(v) for v in line.split()[1:3]])
        elif line.startswith("vn "):
            normals.append([float(v) for v in line.split()[1:4]])
    assert len(positions) == len(uvs) == len(normals), path
    return lines, positions, uvs, normals


def window_centre(model: str, positions, lines) -> float:
    """The height of the reticle's glass centre (model z is the OBJ's y)."""
    vmdl = (MODELS / model / f"{model}.vmdl").read_text(encoding="utf-8")
    remap = dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"', vmdl))
    reticle = next(name for name, target in remap.items() if target.endswith("_reticle.vmat"))
    heights, material = [], None
    for line in lines:
        if line.startswith("usemtl"):
            material = line.split()[1]
        elif line.startswith("f ") and material == reticle:
            heights += [positions[int(corner.split("/")[0]) - 1][1] for corner in line.split()[1:]]
    return (min(heights) + max(heights)) / 2


def fmt(values) -> str:
    return " ".join(f"{v:.7f}" for v in values)


def raise_mount(lines, positions, uvs, normals, cut: float, lift: float) -> list[str]:
    """The OBJ with everything over the cut lifted, and the faces across it split, with a band between their halves."""
    assert all(abs(p[1] - cut) > 1e-4 for p in positions), "a vertex lies on the cut"
    above = [p[1] > cut for p in positions]
    extra = []  # new interleaved vertices: (position, uv, normal)

    def lifted(i):
        p = list(positions[i])
        if above[i]:
            p[1] += lift
        return p

    cache = {}

    def crossing(a, b):
        """The point where edge a-b crosses the cut: its index at the cut, and its index lifted. The faces either side
        of an edge share them."""
        a, b = min(a, b), max(a, b)
        if (a, b) in cache:
            return cache[a, b]
        t = (cut - positions[a][1]) / (positions[b][1] - positions[a][1])
        mix = lambda x, y: [u + (v - u) * t for u, v in zip(x, y)]
        position, uv, normal = mix(positions[a], positions[b]), mix(uvs[a], uvs[b]), mix(normals[a], normals[b])
        length = sum(n * n for n in normal) ** 0.5
        normal = [n / length for n in normal]
        position[1] = cut
        low = len(positions) + len(extra) + 1
        extra.append((position, uv, normal))
        high = len(positions) + len(extra) + 1
        extra.append(([position[0], cut + lift, position[2]], uv, normal))
        cache[a, b] = low, high
        return low, high

    first = next(i for i, line in enumerate(lines) if line.startswith("v "))
    faces = []
    for line in lines[first:]:
        if line.startswith(("v ", "vt ", "vn ")):
            continue
        if not line.startswith("f "):
            faces.append(line)
            continue
        corners = [int(c.split("/")[0]) - 1 for c in line.split()[1:]]
        sides = [above[c] for c in corners]
        if all(sides) or not any(sides):
            faces.append(line)
            continue
        # Walk the triangle's edges; where one crosses the cut, insert its point at the cut and the same point lifted,
        # in the order the edge goes. The polygon then splits into the half under the cut, the band, and the half over.
        below, band, over = [], [], []
        for k, a in enumerate(corners):
            b = corners[(k + 1) % 3]
            (over if above[a] else below).append(a + 1)
            if above[a] != above[b]:
                low, high = crossing(a, b)
                if above[a]:  # going down
                    over.append(high)
                    below.append(low)
                    band += [high, low]
                else:  # going up
                    below.append(low)
                    over.append(high)
                    band += [low, high]
        for polygon in (below, band, over):
            for k in range(1, len(polygon) - 1):
                tri = (polygon[0], polygon[k], polygon[k + 1])
                faces.append("f " + " ".join(f"{i}/{i}/{i}" for i in tri))
    body = []
    for i in range(len(positions)):
        body += [f"v {fmt(lifted(i))}", f"vt {fmt(uvs[i])}", f"vn {fmt(normals[i])}"]
    for position, uv, normal in extra:
        body += [f"v {fmt(position)}", f"vt {fmt(uv)}", f"vn {fmt(normal)}"]
    return lines[:first] + body + faces


def parts_using(model: str) -> list[Path]:
    """Every gunsmith part whose prefab draws the model."""
    found = []
    for path in sorted((ASSETS / "gunsmith").rglob("*.gnsmth")):
        part = json.loads(path.read_text(encoding="utf-8"))
        prefab = part.get("MainPrefab")
        # A few old parts have the bare path, which doesn't resolve in-game (CLAUDE.md: Gunsmith).
        prefab = prefab.get("prefab") if isinstance(prefab, dict) else prefab
        if prefab and (ASSETS / prefab).is_file() and f"/{model}/{model}.vmdl" in (ASSETS / prefab).read_text(encoding="utf-8"):
            found.append(path)
    return found


def offset_text(original: str, lift: float) -> str:
    values = [float(v) for v in original.split(",")]
    values[2] -= lift
    if all(re.fullmatch(r"-?\d+\.\d{6}", v.strip()) for v in original.split(",")):
        return ",".join(f"{v:.6f}" for v in values)
    return ",".join(f"{round(v, 4):g}" for v in values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="list what a run would change, and change nothing")
    args = parser.parse_args()
    BACKUP.mkdir(parents=True, exist_ok=True)
    offsets_file = BACKUP / "aim_offsets.json"
    offsets = json.loads(offsets_file.read_text(encoding="utf-8")) if offsets_file.is_file() else {}
    stale = 0
    for model, (cut, target) in RISERS.items():
        rip = BACKUP / f"{model}.obj"
        if not rip.is_file():
            assert not args.check, f"{rip} missing: run without --check first"
            shutil.copyfile(obj_path(model), rip)
        lines, positions, uvs, normals = read_obj(rip)
        centre = window_centre(model, positions, lines)
        lift = round(target - centre, 4)
        out = "\r\n".join(raise_mount(lines, positions, uvs, normals, cut, lift)) + "\r\n"
        print(f"{model}: window {centre:.4f} -> {centre + lift:.4f} over the rail (+{lift:.4f}, cut at {cut})")
        if obj_path(model).read_bytes() != out.encode("utf-8"):
            stale += 1
            print(f"  {'stale' if args.check else 'wrote'} {obj_path(model).relative_to(ROOT)}")
            if not args.check:
                obj_path(model).write_bytes(out.encode("utf-8"))
        for part in parts_using(model):
            key = part.relative_to(ASSETS).as_posix()
            text = part.read_bytes().decode("utf-8")  # as it is, line endings and all
            current = re.search(r'"OpticAimOffset": "([^"]+)"', text).group(1)
            if key not in offsets:
                assert not args.check, f"{key}'s original offset isn't recorded: run without --check first"
                offsets[key] = current
            wanted = offset_text(offsets[key], lift)
            if current != wanted:
                stale += 1
                print(f"  {'stale' if args.check else 'wrote'} {key}: OpticAimOffset {current} -> {wanted}")
                if not args.check:
                    part.write_text(text.replace(f'"OpticAimOffset": "{current}"', f'"OpticAimOffset": "{wanted}"'),
                                    encoding="utf-8", newline="")
    if not args.check:
        offsets_file.write_text(json.dumps(offsets, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{stale} file(s) {'stale' if args.check else 'written'}")
    if args.check and stale:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
