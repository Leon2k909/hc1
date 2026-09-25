"""SMD reading/writing and Source rotation helpers for the Kastov port.

Source SMD rotations are XYZ Euler angles in radians, composed as Rz * Ry * Rx.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def euler_to_mat(rx: float, ry: float, rz: float) -> np.ndarray:
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    rot_x = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    rot_y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rot_z = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rot_z @ rot_y @ rot_x


def mat_to_euler(rot: np.ndarray) -> tuple[float, float, float]:
    sin_y = float(np.clip(-rot[2, 0], -1.0, 1.0))
    ry = float(np.arcsin(sin_y))
    if abs(sin_y) < 0.999999:
        rx = float(np.arctan2(rot[2, 1], rot[2, 2]))
        rz = float(np.arctan2(rot[1, 0], rot[0, 0]))
    else:
        rx = float(np.arctan2(-rot[1, 2], rot[1, 1]))
        rz = 0.0
    return rx, ry, rz


def matrix(pos, rot3) -> np.ndarray:
    out = np.eye(4)
    out[:3, :3] = rot3
    out[:3, 3] = pos
    return out


def orthonormalize(rot: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(rot)
    fixed = u @ vt
    if np.linalg.det(fixed) < 0:
        u[:, -1] *= -1
        fixed = u @ vt
    return fixed


class Smd:
    """A parsed SMD: nodes, skeleton frames (sparse per frame) and triangles."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.nodes: list[tuple[str, int]] = []
        self.frames: list[dict[int, tuple[np.ndarray, np.ndarray]]] = []
        self.triangles: list[tuple[str, list]] = []
        self._parse(self.path.read_text(encoding="utf-8-sig", errors="replace").splitlines())
        self._lower = {name.lower(): index for index, (name, _) in enumerate(self.nodes)}

    def _parse(self, lines: list[str]) -> None:
        index = 0
        count = len(lines)
        while index < count:
            line = lines[index].strip()
            index += 1
            if line == "nodes":
                while lines[index].strip() != "end":
                    text = lines[index].strip()
                    index += 1
                    if not text:
                        continue
                    start = text.index('"')
                    end = text.index('"', start + 1)
                    node = int(text[:start])
                    while len(self.nodes) <= node:
                        self.nodes.append(("", -1))
                    self.nodes[node] = (text[start + 1:end], int(text[end + 1:]))
                index += 1
            elif line == "skeleton":
                current = None
                while lines[index].strip() != "end":
                    fields = lines[index].split()
                    index += 1
                    if not fields:
                        continue
                    if fields[0] == "time":
                        current = {}
                        self.frames.append(current)
                        continue
                    values = [float(value) for value in fields[1:7]]
                    current[int(fields[0])] = (np.array(values[:3]), np.array(values[3:6]))
                index += 1
            elif line == "triangles":
                while index < count and lines[index].strip() != "end":
                    material = lines[index].strip()
                    index += 1
                    if not material:
                        continue
                    vertices = []
                    for _ in range(3):
                        fields = lines[index].split()
                        index += 1
                        bone = int(fields[0])
                        position = np.array([float(v) for v in fields[1:4]])
                        normal = np.array([float(v) for v in fields[4:7]])
                        uv = (float(fields[7]), float(fields[8]))
                        links = []
                        if len(fields) > 9:
                            for link in range(int(fields[9])):
                                links.append((int(fields[10 + 2 * link]), float(fields[11 + 2 * link])))
                        if not links:
                            links = [(bone, 1.0)]
                        vertices.append((position, normal, uv, links))
                    self.triangles.append((material, vertices))
                index += 1

    def index(self, name: str) -> int:
        return self._lower.get(name.lower(), -1)

    def name(self, bone: int) -> str:
        return self.nodes[bone][0]

    def dense_frames(self) -> list[dict[int, tuple[np.ndarray, np.ndarray]]]:
        """SMD animation frames only list changed bones; carry previous values forward."""
        result = []
        previous: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for frame in self.frames:
            current = dict(previous)
            current.update(frame)
            result.append(current)
            previous = current
        return result

    def world(self, frame: dict[int, tuple[np.ndarray, np.ndarray]]) -> list[np.ndarray]:
        """Model-space 4x4 transform of every bone for one (dense) frame."""
        result: list[np.ndarray | None] = [None] * len(self.nodes)

        def solve(bone: int) -> np.ndarray:
            cached = result[bone]
            if cached is not None:
                return cached
            position, rotation = frame.get(bone, (np.zeros(3), np.zeros(3)))
            local = matrix(position, euler_to_mat(*rotation))
            parent = self.nodes[bone][1]
            value = local if parent < 0 else solve(parent) @ local
            result[bone] = value
            return value

        for bone in range(len(self.nodes)):
            solve(bone)
        return result  # type: ignore[return-value]


def write_smd(path: Path, nodes: list[tuple[str, int]], frames: list[list[np.ndarray]],
              triangles: list[tuple[str, list]] | None = None) -> None:
    """Write an SMD. frames holds, per frame, the local 4x4 transform of every node."""
    out = ["version 1", "nodes"]
    for index, (name, parent) in enumerate(nodes):
        out.append(f'{index} "{name}" {parent}')
    out.append("end")
    out.append("skeleton")
    for time, locals_ in enumerate(frames):
        out.append(f"time {time}")
        for index, local in enumerate(locals_):
            rx, ry, rz = mat_to_euler(local[:3, :3])
            px, py, pz = local[:3, 3]
            out.append(f"{index} {px:.6f} {py:.6f} {pz:.6f} {rx:.6f} {ry:.6f} {rz:.6f}")
    out.append("end")
    if triangles is not None:
        out.append("triangles")
        for material, vertices in triangles:
            out.append(material)
            for position, normal, uv, links in vertices:
                link_text = " ".join(f"{bone} {weight:.6f}" for bone, weight in links)
                out.append(
                    f"{links[0][0]} {position[0]:.6f} {position[1]:.6f} {position[2]:.6f} "
                    f"{normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f} {uv[0]:.6f} {uv[1]:.6f} "
                    f"{len(links)} {link_text}")
        out.append("end")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
