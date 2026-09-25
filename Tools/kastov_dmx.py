"""Write skinned meshes and bone animations as keyvalues2 DMX, which s&box's ModelDoc imports (it no longer reads SMD).

Layout follows Blender Source Tools' Source 2 export (model format 22): a DmeModel whose jointList starts with the
model itself, parent-relative DmeJoint transforms, one DmeVertexData with "$0" streams, and DmeChannelsClip
animations whose channels drive the skeleton's DmeTransforms.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

_NAMESPACE = uuid.UUID("0b7f3f52-6d2c-4c55-9f0e-3a9b1d5c7e21")
FORMAT_VERSION = 22


def rotation_to_quaternion(rotation: np.ndarray) -> tuple[float, float, float, float]:
    """3x3 rotation -> (x, y, z, w)."""
    m = rotation
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        w, x, y, z = 0.25 / s, (m[2, 1] - m[1, 2]) * s, (m[0, 2] - m[2, 0]) * s, (m[1, 0] - m[0, 1]) * s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = 2.0 * np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        w, x, y, z = (m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = 2.0 * np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        w, x, y, z = (m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s
    else:
        s = 2.0 * np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        w, x, y, z = (m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s
    q = np.array([x, y, z, w], float)
    q /= np.linalg.norm(q)
    return tuple(float(v) for v in q)


class Element:
    def __init__(self, kind: str, name: str, key: str):
        self.kind = kind
        self.name = name
        self.id = str(uuid.uuid5(_NAMESPACE, key))
        self.attributes: list[tuple[str, str, object]] = []

    def set(self, name: str, kind: str, value) -> "Element":
        self.attributes.append((name, kind, value))
        return self


def _scalar(kind: str, value) -> str:
    if kind == "bool":
        return "1" if value else "0"
    if kind == "int":
        return str(int(value))
    if kind in ("float", "time"):
        return f"{float(value):.6f}"
    if kind == "string":
        return str(value).replace('"', "'")
    if kind == "color":
        return " ".join(str(int(v)) for v in value)
    if kind in ("vector2", "vector3", "vector4", "quaternion"):
        return " ".join(f"{float(v):.6f}" for v in value)
    raise ValueError(kind)


class Document:
    def __init__(self, key: str):
        self.key = key
        self.elements: list[Element] = []

    def add(self, kind: str, name: str, key: str) -> Element:
        element = Element(kind, name, f"{self.key}/{key}")
        self.elements.append(element)
        return element

    def write(self, path: Path) -> None:
        out = [f"<!-- dmx encoding keyvalues2 1 format model {FORMAT_VERSION} -->"]
        for element in self.elements:
            out.append(f'"{element.kind}"')
            out.append("{")
            out.append(f'\t"id" "elementid" "{element.id}"')
            out.append(f'\t"name" "string" "{_scalar("string", element.name)}"')
            for name, kind, value in element.attributes:
                if kind.endswith("_array"):
                    base = kind[:-6]
                    out.append(f'\t"{name}" "{kind}"')
                    out.append("\t[")
                    items = list(value)
                    last = len(items) - 1
                    for index, item in enumerate(items):
                        comma = "," if index < last else ""
                        if base == "element":
                            out.append(f'\t\t"element" "{item.id}"{comma}')
                        else:
                            out.append(f'\t\t"{_scalar(base, item)}"{comma}')
                    out.append("\t]")
                elif kind == "element":
                    out.append(f'\t"{name}" "element" "{value.id if value is not None else ""}"')
                else:
                    out.append(f'\t"{name}" "{kind}" "{_scalar(kind, value)}"')
            out.append("}")
            out.append("")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(out), encoding="utf-8", newline="\n")


def _transform(doc: Document, name: str, local: np.ndarray, key: str) -> Element:
    element = doc.add("DmeTransform", name, key)
    element.set("position", "vector3", local[:3, 3])
    element.set("orientation", "quaternion", rotation_to_quaternion(local[:3, :3]))
    return element


class Skeleton:
    """DmeModel + DmeJoints. Joint i of nodes is jointList index i + 1 (index 0 is the model itself)."""

    def __init__(self, doc: Document, model_name: str, nodes: list[tuple[str, int]], bind_locals: list[np.ndarray]):
        self.model = doc.add("DmeModel", model_name, "model")
        identity = np.eye(4)
        self.model.set("transform", "element", _transform(doc, model_name, identity, "model/transform"))
        self.model.set("shape", "element", None)
        self.model.set("visible", "bool", True)
        self.transforms: list[Element] = []
        joints: list[Element] = []
        base_transforms = [_transform(doc, model_name, identity, "model/base")]
        for index, (name, _) in enumerate(nodes):
            joint = doc.add("DmeJoint", name, f"joint/{name}")
            transform = _transform(doc, name, bind_locals[index], f"transform/{name}")
            joint.set("transform", "element", transform)
            joint.set("shape", "element", None)
            joint.set("visible", "bool", True)
            joint.set("lockInfluenceWeights", "bool", False)
            joints.append(joint)
            self.transforms.append(transform)
            base_transforms.append(_transform(doc, name, bind_locals[index], f"base/{name}"))
        children: dict[int, list[Element]] = {}
        for index, (_, parent) in enumerate(nodes):
            children.setdefault(parent, []).append(joints[index])
        for index, joint in enumerate(joints):
            joint.set("children", "element_array", children.get(index, []))
        self.root_children = list(children.get(-1, []))
        self.model.set("children", "element_array", self.root_children)
        self.model.set("jointList", "element_array", [self.model] + joints)
        base = doc.add("DmeTransformList", "base", "model/basestates")
        base.set("transforms", "element_array", base_transforms)
        self.model.set("baseStates", "element_array", [base])
        axis = doc.add("DmeAxisSystem", "axisSystem", "model/axis")
        axis.set("upAxis", "int", 3)
        axis.set("forwardParity", "int", 1)
        axis.set("coordSys", "int", 0)
        self.model.set("axisSystem", "element", axis)


def write_model(path: Path, model_name: str, nodes: list[tuple[str, int]], bind_locals: list[np.ndarray],
                triangles: list[tuple[str, list]]) -> None:
    """triangles: (material, [(position, normal, uv, [(node_index, weight), ...]) x3]) in model space."""
    doc = Document(f"{model_name}/mesh")
    root = doc.add("DmElement", "root", "root")
    skeleton = Skeleton(doc, model_name, nodes, bind_locals)

    positions: list[tuple] = []
    position_lookup: dict[tuple, int] = {}
    normals: list[tuple] = []
    normal_lookup: dict[tuple, int] = {}
    uvs: list[tuple] = []
    uv_lookup: dict[tuple, int] = {}
    influences: list[list[tuple[int, float]]] = []
    position_indices: list[int] = []
    normal_indices: list[int] = []
    uv_indices: list[int] = []
    faces_by_material: dict[str, list[int]] = {}
    joint_count = 1

    for material, vertices in triangles:
        faces = faces_by_material.setdefault(material, [])
        for position, normal, uv, links in vertices:
            links = sorted(((int(b), float(w)) for b, w in links if w > 1e-6), key=lambda link: -link[1])
            total = sum(w for _, w in links) or 1.0
            links = [(b, w / total) for b, w in links]
            joint_count = max(joint_count, len(links))
            p = tuple(round(float(v), 5) for v in position)
            key = (p, tuple((b, round(w, 4)) for b, w in links))
            index = position_lookup.get(key)
            if index is None:
                index = position_lookup[key] = len(positions)
                positions.append(p)
                influences.append(links)
            n = tuple(round(float(v), 4) for v in normal)
            n_index = normal_lookup.setdefault(n, len(normal_lookup))
            if n_index == len(normals):
                normals.append(n)
            t = (round(float(uv[0]), 6), round(float(uv[1]), 6))
            t_index = uv_lookup.setdefault(t, len(uv_lookup))
            if t_index == len(uvs):
                uvs.append(t)
            faces.append(len(position_indices))
            position_indices.append(index)
            normal_indices.append(n_index)
            uv_indices.append(t_index)
        faces.append(-1)

    weights: list[float] = []
    indices: list[int] = []
    for links in influences:
        padded = links + [(links[0][0], 0.0)] * (joint_count - len(links))
        for bone, weight in padded:
            weights.append(weight)
            indices.append(bone + 1)

    vertex_data = doc.add("DmeVertexData", "bind", "vertexdata")
    vertex_data.set("vertexFormat", "string_array",
                    ["position$0", "normal$0", "texcoord$0", "blendweights$0", "blendindices$0"])
    vertex_data.set("flipVCoordinates", "bool", True)
    vertex_data.set("jointCount", "int", joint_count)
    vertex_data.set("position$0", "vector3_array", positions)
    vertex_data.set("position$0Indices", "int_array", position_indices)
    vertex_data.set("normal$0", "vector3_array", normals)
    vertex_data.set("normal$0Indices", "int_array", normal_indices)
    vertex_data.set("texcoord$0", "vector2_array", uvs)
    vertex_data.set("texcoord$0Indices", "int_array", uv_indices)
    vertex_data.set("blendweights$0", "float_array", weights)
    vertex_data.set("blendindices$0", "int_array", indices)

    face_sets = []
    for material, faces in faces_by_material.items():
        material_element = doc.add("DmeMaterial", material, f"material/{material}")
        material_element.set("mtlName", "string", material)
        face_set = doc.add("DmeFaceSet", material, f"faceset/{material}")
        face_set.set("material", "element", material_element)
        face_set.set("faces", "int_array", faces)
        face_sets.append(face_set)

    mesh = doc.add("DmeMesh", model_name, "mesh")
    mesh.set("visible", "bool", True)
    mesh.set("bindState", "element", vertex_data)
    mesh.set("currentState", "element", vertex_data)
    mesh.set("baseStates", "element_array", [vertex_data])
    mesh.set("deltaStates", "element_array", [])
    mesh.set("faceSets", "element_array", face_sets)

    dag = doc.add("DmeDag", model_name, "dag")
    dag.set("transform", "element", _transform(doc, model_name, np.eye(4), "dag/transform"))
    dag.set("shape", "element", mesh)
    dag.set("visible", "bool", True)
    dag.set("children", "element_array", [])
    skeleton.root_children.append(dag)

    root.set("skeleton", "element", skeleton.model)
    root.set("model", "element", skeleton.model)
    doc.write(path)


def write_animation(path: Path, clip_name: str, nodes: list[tuple[str, int]], frames: list[list[np.ndarray]],
                    fps: float) -> None:
    """frames: per frame, the parent-relative 4x4 transform of every node."""
    doc = Document(f"{clip_name}/anim")
    root = doc.add("DmElement", "root", "root")
    skeleton = Skeleton(doc, clip_name, nodes, frames[0])
    times = [index / fps for index in range(len(frames))]

    channels = []
    for index, (name, _) in enumerate(nodes):
        for suffix, attribute, log_kind, value_kind in (("p", "position", "Vector3", "vector3"),
                                                        ("o", "orientation", "Quaternion", "quaternion")):
            if attribute == "position":
                values = [frame[index][:3, 3] for frame in frames]
            else:
                values = []
                previous = None
                for frame in frames:
                    q = np.array(rotation_to_quaternion(frame[index][:3, :3]))
                    if previous is not None and np.dot(q, previous) < 0:
                        q = -q
                    values.append(q)
                    previous = q
            layer = doc.add(f"Dme{log_kind}LogLayer", f"{name}_{suffix}", f"layer/{name}/{suffix}")
            layer.set("times", "time_array", times)
            layer.set("curvetypes", "int_array", [])
            layer.set("values", f"{value_kind}_array", values)
            log = doc.add(f"Dme{log_kind}Log", f"{name}_{suffix}", f"log/{name}/{suffix}")
            log.set("layers", "element_array", [layer])
            log.set("curveinfo", "element", None)
            log.set("usedefaultvalue", "bool", False)
            log.set("defaultvalue", value_kind, (0, 0, 0) if value_kind == "vector3" else (0, 0, 0, 1))
            channel = doc.add("DmeChannel", f"{name}_{suffix}", f"channel/{name}/{suffix}")
            channel.set("fromElement", "element", None)
            channel.set("fromAttribute", "string", "")
            channel.set("fromIndex", "int", 0)
            channel.set("toElement", "element", skeleton.transforms[index])
            channel.set("toAttribute", "string", attribute)
            channel.set("toIndex", "int", 0)
            channel.set("mode", "int", 1)
            channel.set("log", "element", log)
            channels.append(channel)

    time_frame = doc.add("DmeTimeFrame", "timeframe", "timeframe")
    time_frame.set("start", "time", 0.0)
    time_frame.set("duration", "time", max(times[-1], 1.0 / fps))
    time_frame.set("offset", "time", 0.0)
    time_frame.set("scale", "float", 1.0)
    clip = doc.add("DmeChannelsClip", clip_name, "clip")
    clip.set("timeFrame", "element", time_frame)
    clip.set("color", "color", (0, 0, 0, 0))
    clip.set("text", "string", "")
    clip.set("mute", "bool", False)
    clip.set("trackGroups", "element_array", [])
    clip.set("displayScale", "float", 1.0)
    clip.set("channels", "element_array", channels)
    clip.set("frameRate", "int", int(round(fps)))
    animation_list = doc.add("DmeAnimationList", "animationList", "animationlist")
    animation_list.set("animations", "element_array", [clip])

    root.set("skeleton", "element", skeleton.model)
    root.set("animationList", "element", animation_list)
    doc.write(path)
