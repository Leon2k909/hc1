#!/usr/bin/env python3
"""Convert the extracted MP5 attachment SMD meshes to static OBJ assets."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "Assets"
ATTACHMENT_ROOT = ASSET_ROOT / "attachments" / "mpapa5"
CLASSIC_STOCK_RECEIVER_JUNCTION_X = -4.5
MESH_REFERENCE = re.compile(r'(filename\s*=\s*")([^"]+\.(?:smd|obj))(")', re.IGNORECASE)
SMD_REFERENCE = re.compile(r'filename\s*=\s*"[^"]+\.smd"', re.IGNORECASE)
REMAPS = re.compile(r"(remaps\s*=\s*\[)(.*?)(\])", re.IGNORECASE | re.DOTALL)
EMPTY_MESH_CHOICE = re.compile(r'(meshes\s*=\s*)\[\s*""\s*\]', re.IGNORECASE)
MATERIAL_REMAP = re.compile(r'from\s*=\s*"([^"]+)"\s*to\s*=\s*"([^"]+)"', re.IGNORECASE)


def parse_triangles(path: Path) -> list[tuple[str, tuple[tuple[float, ...], ...]]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    try:
        index = next(i for i, line in enumerate(lines) if line.strip().lower() == "triangles") + 1
    except StopIteration as exc:
        raise ValueError(f"{path}: missing triangles section") from exc

    triangles: list[tuple[str, tuple[tuple[float, ...], ...]]] = []
    while index < len(lines):
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or lines[index].strip().lower() == "end":
            break

        material = lines[index].strip()
        index += 1
        vertices: list[tuple[float, ...]] = []
        for _ in range(3):
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index >= len(lines):
                raise ValueError(f"{path}: incomplete triangle for {material}")
            fields = lines[index].split()
            index += 1
            if len(fields) < 9:
                raise ValueError(f"{path}: malformed vertex row: {' '.join(fields)}")
            try:
                # SMD rows start with the parent bone, followed by position, normal, and UV.
                vertex = tuple(float(value) for value in fields[1:9])
            except ValueError as exc:
                raise ValueError(f"{path}: malformed vertex row: {' '.join(fields)}") from exc
            vertices.append(vertex)
        triangles.append((material, tuple(vertices)))

    if not triangles:
        raise ValueError(f"{path}: no triangles found")
    return triangles


def write_obj_mesh(
    obj_path: Path, triangles: list[tuple[str, tuple[tuple[float, ...], ...]]]
) -> set[str]:
    positions: list[str] = []
    uvs: list[str] = []
    normals: list[str] = []
    faces: list[str] = []
    materials: set[str] = set()
    last_material: str | None = None
    vertex_index = 1

    for material, vertices in triangles:
        materials.add(material)
        if material != last_material:
            faces.append(f"usemtl {material}")
            last_material = material
        face_indices: list[str] = []
        for vertex in vertices:
            x, y, z, nx, ny, nz, u, v = vertex
            # S&box maps OBJ (X,Y,Z) to model (Z,X,Y). Pre-rotate the
            # Source SMD coordinates so the compiled model keeps its bind pose.
            positions.append(f"v {y:.9g} {z:.9g} {x:.9g}")
            uvs.append(f"vt {u:.9g} {v:.9g}")
            normals.append(f"vn {ny:.9g} {nz:.9g} {nx:.9g}")
            face_indices.append(f"{vertex_index}/{vertex_index}/{vertex_index}")
            vertex_index += 1
        faces.append("f " + " ".join(face_indices))

    obj_path.parent.mkdir(parents=True, exist_ok=True)
    mtl_path = obj_path.with_suffix(".mtl")
    content = [f"mtllib {mtl_path.name}", f"o {obj_path.stem}"]
    content.extend(positions)
    content.extend(uvs)
    content.extend(normals)
    content.extend(faces)
    obj_path.write_text("\n".join(content) + "\n", encoding="utf-8", newline="\n")

    mtl = []
    for material in sorted(materials):
        mtl.extend((f"newmtl {material}", "Ka 1 1 1", "Kd 1 1 1", "Ks 0 0 0", "d 1", "illum 2", ""))
    mtl_path.write_text("\n".join(mtl), encoding="utf-8", newline="\n")
    return materials


def write_obj(source: Path) -> set[str]:
    return write_obj_mesh(source.with_suffix(".obj"), parse_triangles(source))


def clip_to_rear_stock(
    triangles: list[tuple[str, tuple[tuple[float, ...], ...]]], x_limit: float
) -> list[tuple[str, tuple[tuple[float, ...], ...]]]:
    """Keep only the buttstock behind the existing MP5 receiver junction."""
    clipped: list[tuple[str, tuple[tuple[float, ...], ...]]] = []
    for material, triangle in triangles:
        polygon = list(triangle)
        output: list[tuple[float, ...]] = []
        for previous, current in zip(polygon[-1:] + polygon[:-1], polygon):
            previous_inside = previous[0] <= x_limit
            current_inside = current[0] <= x_limit
            if previous_inside != current_inside:
                amount = (x_limit - previous[0]) / (current[0] - previous[0])
                output.append(tuple(a + (b - a) * amount for a, b in zip(previous, current)))
            if current_inside:
                output.append(current)
        for index in range(1, len(output) - 1):
            clipped.append((material, (output[0], output[index], output[index + 1])))
    return clipped


def referenced_smd_to_obj(match: re.Match[str]) -> str:
    reference = match.group(2).replace("\\", "/")
    if reference.lower().endswith(".obj"):
        return match.group(0)
    prefix = "attachments/mpapa5/"
    if not reference.lower().startswith(prefix):
        raise ValueError(f"Unexpected mesh path in ModelDoc: {reference}")
    source = ASSET_ROOT.joinpath(*reference.split("/"))
    if not source.is_file():
        raise FileNotFoundError(source)
    return match.group(1) + reference[:-4] + ".obj" + match.group(3)


def read_obj_materials(path: Path) -> set[str]:
    return {
        line.split(maxsplit=1)[1].strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.startswith("usemtl ")
    }


def update_modeldoc(path: Path) -> tuple[int, set[str]]:
    original = path.read_text(encoding="utf-8-sig")
    references = list(MESH_REFERENCE.finditer(original))
    if not references:
        return 0, set()

    materials: set[str] = set()
    for reference in references:
        mesh_reference = reference.group(2).replace("\\", "/")
        source = ASSET_ROOT.joinpath(*mesh_reference.split("/"))
        if mesh_reference.lower().endswith(".smd"):
            materials.update(material for material, _ in parse_triangles(source))
        else:
            materials.update(read_obj_materials(source))

    updated = MESH_REFERENCE.sub(referenced_smd_to_obj, original)
    updated = EMPTY_MESH_CHOICE.sub(r"\1[]", updated)
    remap_match = REMAPS.search(updated)
    if not remap_match:
        raise ValueError(f"{path}: no MaterialGroup remaps array found")
    remaps_body = remap_match.group(2)
    already_mapped = set(re.findall(r'from\s*=\s*"([^"]+)"', remaps_body, re.IGNORECASE))
    additions = []
    for material in sorted(materials):
        source_material = f"{material}.vmat"
        target_material = f"attachments/mpapa5/materials/{material}.vmat"
        if not (ASSET_ROOT / Path(*target_material.split("/"))).is_file():
            raise FileNotFoundError(ASSET_ROOT / Path(*target_material.split("/")))
        if source_material not in already_mapped:
            additions.append(f'{{ from = "{source_material}" to = "{target_material}" }}')
    if additions:
        separator = ", " if remaps_body.strip() else " "
        updated = updated[: remap_match.end(2)] + separator + ", ".join(additions) + updated[remap_match.end(2) :]

    path.write_text(updated, encoding="utf-8", newline="\n")
    return len(references), materials


def main() -> None:
    smd_files = sorted(ATTACHMENT_ROOT.rglob("*.smd"))
    converted_materials: set[str] = set()
    triangle_count = 0
    for source in smd_files:
        triangles = parse_triangles(source)
        triangle_count += len(triangles)
        converted_materials.update(write_obj(source))

        if source.stem == "stock_classic_full":
            fitted = clip_to_rear_stock(triangles, CLASSIC_STOCK_RECEIVER_JUNCTION_X)
            write_obj_mesh(source.with_name("stock_classic_full_fitted.obj"), fitted)

    modeldocs = sorted(ATTACHMENT_ROOT.rglob("*.vmdl"))
    reference_count = 0
    for modeldoc in modeldocs:
        references, _ = update_modeldoc(modeldoc)
        reference_count += references

    issues: list[str] = []
    for modeldoc in modeldocs:
        contents = modeldoc.read_text(encoding="utf-8-sig")
        if SMD_REFERENCE.search(contents):
            issues.append(f"{modeldoc}: still references an SMD")
        remaps = dict(MATERIAL_REMAP.findall(contents))
        for reference in MESH_REFERENCE.finditer(contents):
            mesh_reference = reference.group(2).replace("\\", "/")
            mesh_path = ASSET_ROOT.joinpath(*mesh_reference.split("/"))
            if not mesh_path.is_file():
                issues.append(f"{modeldoc}: missing mesh {mesh_reference}")
                continue
            for material in read_obj_materials(mesh_path):
                source_material = f"{material}.vmat"
                target_material = remaps.get(source_material)
                if not target_material:
                    issues.append(f"{modeldoc}: no remap for {source_material}")
                elif not ASSET_ROOT.joinpath(*target_material.split("/")).is_file():
                    issues.append(f"{modeldoc}: missing material {target_material}")
    if issues:
        raise RuntimeError("ModelDoc validation failed:\n" + "\n".join(issues))

    print(
        f"Converted {len(smd_files)} SMD meshes ({triangle_count:,} triangles) to OBJ/MTL; "
        f"updated {len(modeldocs)} ModelDocs and {reference_count} mesh references; "
        f"validated {len(converted_materials)} materials and their ModelDoc remaps."
    )


if __name__ == "__main__":
    main()
