"""Offline preview of the ported Kastov viewmodel with the HC1 arms skinned onto it (painter's algorithm, PIL)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kastov_gltf import CONV, INCH, GltfModel

ARMS_GLB = Path(r"D:\tmp\hc1-mw22-tools\kastov_work\arms.glb")
LIGHT = np.array([0.4, -0.3, 0.85]) / np.linalg.norm([0.4, -0.3, 0.85])


def _gltf_to_source(matrix_gltf: np.ndarray) -> np.ndarray:
    out = np.eye(4)
    out[:3, :3] = CONV.T @ matrix_gltf[:3, :3]
    out[:3, 3] = CONV.T @ matrix_gltf[:3, 3] / INCH
    return out


class Arms:
    """The HC1 first-person arms mesh, skinnable with Source-space bone transforms."""

    def __init__(self, path: Path = ARMS_GLB):
        model = GltfModel(path)
        node_index = next(i for i, node in enumerate(model.nodes) if node.get("name", "").endswith(".arms"))
        mesh = model.json["meshes"][model.nodes[node_index]["mesh"]]
        skin = model.json["skins"][model.nodes[node_index]["skin"]]
        primitive = mesh["primitives"][0]
        attributes = primitive["attributes"]
        self.positions = model._accessor(attributes["POSITION"]).astype(float) @ CONV / INCH
        self.joints = model._accessor(attributes["JOINTS_0"]).astype(int)
        self.weights = model._accessor(attributes["WEIGHTS_0"]).astype(float)
        self.indices = model._accessor(primitive["indices"]).reshape(-1, 3).astype(int)
        self.joint_names = [model.nodes[j].get("name") for j in skin["joints"]]
        inverse_binds = model._accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
        self.bind = [_gltf_to_source(np.linalg.inv(m)) for m in inverse_binds]
        self.parent = model.hierarchy()

    def skin(self, bone_world: dict[str, np.ndarray]) -> np.ndarray:
        palette = []
        resolved: dict[str, np.ndarray] = {}
        for index, name in enumerate(self.joint_names):
            if name in bone_world:
                resolved[name] = bone_world[name]
        for index, name in enumerate(self.joint_names):
            if name in resolved:
                palette.append(resolved[name] @ np.linalg.inv(self.bind[index]))
                continue
            # Follow the nearest ancestor that the viewmodel drives (bone-merge behaviour).
            ancestor = self.parent.get(name)
            while ancestor is not None and ancestor not in resolved:
                ancestor = self.parent.get(ancestor)
            if ancestor is None:
                palette.append(np.eye(4))
            else:
                a = self.joint_names.index(ancestor)
                palette.append(resolved[ancestor] @ np.linalg.inv(self.bind[a]))
        palette = np.array(palette)
        homogeneous = np.c_[self.positions, np.ones(len(self.positions))]
        out = np.zeros((len(self.positions), 3))
        for slot in range(4):
            matrices = palette[self.joints[:, slot]]
            moved = np.einsum("nij,nj->ni", matrices, homogeneous)[:, :3]
            out += moved * self.weights[:, slot:slot + 1]
        return out


def _shade(base: tuple[int, int, int], normal: np.ndarray) -> tuple[int, int, int]:
    light = 0.35 + 0.65 * max(0.0, float(np.dot(normal, LIGHT)))
    return tuple(int(min(255, c * light)) for c in base)


def _collect(gun_triangles, gun_world, bind, arms: Arms, bone_world_by_name):
    polys = []
    for material, vertices in gun_triangles:
        points = []
        for position, _, _, links in vertices:
            p = np.zeros(3)
            for bone, weight in links:
                skin = gun_world[bone] @ np.linalg.inv(bind[bone])
                p += weight * (skin[:3, :3] @ position + skin[:3, 3])
            points.append(p)
        color = (150, 110, 70) if "stock" in material or "guard" in material or "pgrip" in material else (95, 95, 100)
        if material.startswith("76239"):
            color = (200, 160, 60)
        polys.append((np.array(points), color))
    skinned = arms.skin(bone_world_by_name)
    for a, b, c in arms.indices:
        polys.append((skinned[[a, b, c]], (200, 160, 130)))
    return polys


def _draw(polys, project, size, depth_key) -> Image.Image:
    image = Image.new("RGB", size, (40, 44, 52))
    draw = ImageDraw.Draw(image)
    items = []
    for points, color in polys:
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        length = np.linalg.norm(normal)
        if length < 1e-9:
            continue
        screen = project(points)
        if screen is None:
            continue
        items.append((depth_key(points), screen, _shade(color, normal / length) if True else color, normal / length))
    items.sort(key=lambda item: -item[0])
    for _, screen, color, _ in items:
        draw.polygon([tuple(p) for p in screen], fill=color)
    return image


def render(kastov, triangles, world: list[np.ndarray], out_path: Path, fov: float = 85.0) -> None:
    arms = Arms()
    names = {name: world[i] for i, (name, _) in enumerate(kastov.nodes)}
    polys = _collect(triangles, world, kastov.bind, arms, names)
    width, height = 960, 540
    focal = (width / 2) / math.tan(math.radians(fov) / 2)

    # First-person view from the (animated) camera bone.
    camera_inv = np.linalg.inv(names["camera"])

    def project_fp(points):
        local = (camera_inv[:3, :3] @ points.T).T + camera_inv[:3, 3]
        if np.any(local[:, 0] < 0.5):
            return None
        u = width / 2 - focal * local[:, 1] / local[:, 0]
        v = height / 2 - focal * local[:, 2] / local[:, 0]
        return np.c_[u, v]

    first = _draw(polys, project_fp, (width, height), lambda p: float(np.mean(p[:, 0])))

    # Orthographic view from the right-hand side (looking along +Y).
    scale = 14.0

    def project_side(points):
        u = width / 2 + scale * (points[:, 0] - 10.0)
        v = height / 2 - scale * (points[:, 2] + 4.0)
        return np.c_[u, v]

    side = _draw(polys, project_side, (width, height), lambda p: -float(np.mean(p[:, 1])))

    # Top view (looking down).
    def project_top(points):
        u = width / 2 + scale * (points[:, 0] - 10.0)
        v = height / 2 + scale * (points[:, 1] + 4.0)
        return np.c_[u, v]

    top = _draw(polys, project_top, (width, height), lambda p: -float(np.mean(p[:, 2])))

    sheet = Image.new("RGB", (width, height * 3))
    sheet.paste(first, (0, 0))
    sheet.paste(side, (0, height))
    sheet.paste(top, (0, height * 2))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(f"preview -> {out_path}")
