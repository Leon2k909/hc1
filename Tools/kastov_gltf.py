"""Read Source2Viewer (VRF) glTF exports back into Source model space (inches, Z-up).

Used to read the HC1 first-person arms skeleton and the M4 viewmodel's idle pose, which
the Kastov port retargets onto.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

INCH = 0.0254
# VRF writes Source (x, y, z) as glTF (y, z, x).
CONV = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
_COMPONENTS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def quat_to_mat(quat) -> np.ndarray:
    x, y, z, w = quat
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _slerp(first, second, amount):
    first = np.asarray(first, float)
    second = np.asarray(second, float)
    dot = float(np.dot(first, second))
    if dot < 0:
        second, dot = -second, -dot
    if dot > 0.9995:
        value = first + amount * (second - first)
        return value / np.linalg.norm(value)
    theta = np.arccos(dot)
    return (np.sin((1 - amount) * theta) * first + np.sin(amount * theta) * second) / np.sin(theta)


class GltfModel:
    def __init__(self, path: Path | str):
        data = Path(path).read_bytes()
        _, _, length = struct.unpack_from("<III", data, 0)
        offset = 12
        self.json = None
        self.binary = b""
        while offset < length:
            chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
            offset += 8
            chunk = data[offset:offset + chunk_length]
            offset += chunk_length
            if chunk_type == 0x4E4F534A:
                self.json = json.loads(chunk)
            elif chunk_type == 0x004E4942:
                self.binary = chunk
        self.nodes = self.json["nodes"]
        self.parent: dict[int, int] = {}
        for index, node in enumerate(self.nodes):
            for child in node.get("children", []):
                self.parent[child] = index
        self.animations = {anim.get("name"): anim for anim in self.json.get("animations", [])}

    def _accessor(self, index: int) -> np.ndarray:
        accessor = self.json["accessors"][index]
        view = self.json["bufferViews"][accessor["bufferView"]]
        dtype = _COMPONENTS[accessor["componentType"]]
        width = _WIDTH[accessor["type"]]
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", 0)
        size = np.dtype(dtype).itemsize * width
        if stride and stride != size:
            raw = np.frombuffer(self.binary, np.uint8, stride * accessor["count"], start)
            raw = raw.reshape(accessor["count"], stride)[:, :size]
            return np.frombuffer(raw.tobytes(), dtype).reshape(accessor["count"], width)
        return np.frombuffer(self.binary, dtype, accessor["count"] * width, start).reshape(accessor["count"], width)

    def _locals(self, animation: str | None, time: float):
        values = {}
        for index, node in enumerate(self.nodes):
            values[index] = [np.array(node.get("translation", [0, 0, 0]), float),
                             np.array(node.get("rotation", [0, 0, 0, 1]), float)]
        if animation is None:
            return values
        anim = self.animations[animation]
        for channel in anim["channels"]:
            node = channel["target"].get("node")
            path = channel["target"]["path"]
            if node is None or path not in ("translation", "rotation"):
                continue
            sampler = anim["samplers"][channel["sampler"]]
            times = self._accessor(sampler["input"])[:, 0]
            outputs = self._accessor(sampler["output"]).astype(float)
            if time <= times[0]:
                value = outputs[0]
            elif time >= times[-1]:
                value = outputs[-1]
            else:
                key = int(np.searchsorted(times, time)) - 1
                amount = (time - times[key]) / (times[key + 1] - times[key])
                value = (_slerp(outputs[key], outputs[key + 1], amount) if path == "rotation"
                         else outputs[key] * (1 - amount) + outputs[key + 1] * amount)
            values[node][0 if path == "translation" else 1] = np.array(value, float)
        return values

    def pose(self, animation: str | None = None, time: float = 0.0) -> dict[str, np.ndarray]:
        """Bone name -> 4x4 model-space transform in Source units (inches, Z-up)."""
        locals_ = self._locals(animation, time)
        world: dict[int, np.ndarray] = {}

        def solve(index: int) -> np.ndarray:
            if index in world:
                return world[index]
            translation, rotation = locals_[index]
            local = np.eye(4)
            local[:3, :3] = quat_to_mat(rotation)
            local[:3, 3] = translation
            parent = self.parent.get(index)
            world[index] = local if parent is None else solve(parent) @ local
            return world[index]

        result = {}
        for index, node in enumerate(self.nodes):
            if "mesh" in node:
                continue
            gltf = solve(index)
            source = np.eye(4)
            source[:3, :3] = CONV.T @ gltf[:3, :3]
            source[:3, 3] = CONV.T @ gltf[:3, 3] / INCH
            result[node.get("name")] = source
        return result

    def length(self, animation: str) -> float:
        """Duration of an animation in seconds."""
        return max(float(self._accessor(sampler["input"]).max())
                   for sampler in self.animations[animation]["samplers"])

    def hierarchy(self) -> dict[str, str | None]:
        """Bone name -> parent bone name (None for bones under the model root node)."""
        result = {}
        for index, node in enumerate(self.nodes):
            if "mesh" in node or index not in self.parent:
                continue
            parent = self.parent[index]
            result[node.get("name")] = None if parent not in self.parent else self.nodes[parent].get("name")
        return result
