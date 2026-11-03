"""Blender side of zombie_female_01.py (run by it: blender -b --python this -- <stage> <work dir> <source>).

Stage "lods": the Meshy scan (1.88M triangles, one mesh, unrigged) is decimated to LODS triangles each, keeping its
UVs, so its own colour and roughness maps still fit; the detail the decimation loses (and the scan's own normal map) is
baked into LOD0's normal map. Each LOD is saved as lod<i>.npz in Blender's axes and the scan's units (she faces -Y, her
left is +X, about 1.9 units tall), with her feet on z = 0.

Stage "citizen": the citizen's reference body (citizen_human_male_REF.fbx in s&box's citizen addon) is saved as
citizen.npz: its body meshes' positions, triangles, normals and bone weights, and its bones' rest heads.
"""

import sys
from pathlib import Path

import bpy
import numpy as np

# Triangles. A fourth LOD at 3,500 (it stopped at 5,700) lost her legs and skirt: the hair's strands keep most of
# the vertices the decimation has, so the body collapses first.
LODS = [36000, 18000, 8000]
BAKE_SIZE = 2048
# Rays start this far outside LOD0 and reach this far in (scan units, about metres). LOD0 is within a few millimetres
# of the scan; the skirt's hem and the hair's strands are thin enough that rays starting further out land on their
# far side.
CAGE_EXTRUSION = 0.008
MAX_RAY = 0.02


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mesh_arrays(ob):
    """Positions (V, 3), triangles (T, 3), per-corner UVs (T, 3, 2) and normals (T, 3, 3), in world space."""
    m = ob.data
    m.calc_loop_triangles()
    co = np.empty(len(m.vertices) * 3, np.float32)
    m.vertices.foreach_get("co", co)
    M = np.array(ob.matrix_world)
    co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    tris = np.empty(len(m.loop_triangles) * 3, np.int32)
    m.loop_triangles.foreach_get("vertices", tris)
    loops = np.empty(len(m.loop_triangles) * 3, np.int32)
    m.loop_triangles.foreach_get("loops", loops)
    nrm = np.empty(len(m.loops) * 3, np.float32)
    m.corner_normals.foreach_get("vector", nrm)
    nrm = nrm.reshape(-1, 3) @ np.linalg.inv(M[:3, :3])
    lengths = np.linalg.norm(nrm, axis=1, keepdims=True)
    bad = lengths[:, 0] < 1e-12
    if bad.any():
        # A collapsed sliver can retain a zero custom normal. Use its geometric vertex normal.
        tri = tris.reshape(-1, 3)
        face = np.cross(co[tri[:, 1]]-co[tri[:, 0]], co[tri[:, 2]]-co[tri[:, 0]])
        vertex = np.zeros_like(co)
        np.add.at(vertex, tri.ravel(), np.repeat(face, 3, axis=0))
        loop_vertex = np.empty(len(m.loops), np.int32)
        m.loops.foreach_get('vertex_index', loop_vertex)
        nrm[bad] = vertex[loop_vertex[bad]]
        lengths = np.linalg.norm(nrm, axis=1, keepdims=True)
        nrm[lengths[:, 0] < 1e-12] = (0, 0, 1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    if m.uv_layers.active:
        uv = np.empty(len(m.loops) * 2, np.float32)
        m.uv_layers.active.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)[loops].reshape(-1, 3, 2)
    else:
        uv = np.zeros((len(loops) // 3, 3, 2), np.float32)
    return co, tris.reshape(-1, 3), uv, nrm[loops].reshape(-1, 3, 3)


def decimated(source, triangles, name):
    ob = source.copy()
    ob.data = source.data.copy()
    ob.name = ob.data.name = name
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = triangles / len(source.data.polygons)
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def bake_normal(high, low, path):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    image = bpy.data.images.new("normal_bake", BAKE_SIZE, BAKE_SIZE, float_buffer=True)
    image.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("bake_target")
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    mat.node_tree.nodes.active = node
    low.data.materials.clear()
    low.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bake = scene.render.bake
    bake.use_selected_to_active = True
    bake.cage_extrusion = CAGE_EXTRUSION
    bake.max_ray_distance = MAX_RAY
    bake.margin = 16
    bake.margin_type = "EXTEND"
    bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type="NORMAL")
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()


def lods(work: Path, glb: Path):
    reset()
    # The scan's UV seams split its vertices; merged, the decimation can't open cracks along them.
    bpy.ops.import_scene.gltf(filepath=str(glb), merge_vertices=True)
    high = next(o for o in bpy.data.objects if o.type == "MESH")
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = high
    high.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = np.empty(len(high.data.vertices) * 3, np.float32)
    high.data.vertices.foreach_get("co", co)
    high.location.z = -float(co[2::3].min())  # feet on the floor
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    print(f"scan: {len(high.data.polygons)} faces, {len(high.data.vertices)} vertices")
    previous = high
    for i, triangles in enumerate(LODS):
        # Each LOD is made from the one before, which is faster and keeps their silhouettes alike.
        ob = decimated(previous, triangles, f"lod{i}")
        co, tris, uv, nrm = mesh_arrays(ob)
        np.savez(work / f"lod{i}.npz", positions=co, triangles=tris, uvs=uv, normals=nrm)
        print(f"lod{i}: {len(tris)} triangles, {len(co)} vertices")
        previous = ob
    bake_normal(high, bpy.data.objects["lod0"], work / "normal_lod0.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(work / "lods.blend"))


def citizen(work: Path, fbx: Path):
    reset()
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    bones = [b.name for b in arm.data.bones]
    heads = np.array([list(arm.matrix_world @ b.head_local) for b in arm.data.bones])
    parts = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not any(k in ob.name for k in ("chest", "hands", "legs", "feet", "head")):
            continue
        co, tris, _, nrm = mesh_arrays(ob)
        w = np.zeros((len(co), len(bones)), np.float32)
        names = {g.index: g.name for g in ob.vertex_groups}
        for v in ob.data.vertices:
            for g in v.groups:
                if names[g.group] in bones:
                    w[v.index, bones.index(names[g.group])] = g.weight
        vn = np.zeros_like(co)
        np.add.at(vn, tris.ravel(), nrm.reshape(-1, 3))
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
        parts[ob.name] = (co, tris, w, vn)
    print("citizen parts:", {k: len(v[1]) for k, v in parts.items()})
    offsets = np.cumsum([0] + [len(p[0]) for p in parts.values()])
    np.savez(work / "citizen.npz", bones=np.array(bones), heads=heads,
             positions=np.concatenate([p[0] for p in parts.values()]),
             normals=np.concatenate([p[3] for p in parts.values()]),
             triangles=np.concatenate([p[1] + o for p, o in zip(parts.values(), offsets)]),
             weights=np.concatenate([p[2] for p in parts.values()]),
             part=np.concatenate([np.full(len(p[0]), i) for i, p in enumerate(parts.values())]),
             part_names=np.array(list(parts)))


def preview(work: Path, spec: Path):
    """Orthographic renders of meshes saved as npz (positions in Blender's axes, triangles, per-corner UVs), textured
    with the colour map. spec (JSON): {"meshes": [{"npz", "offset"}], "color", "views": [{"name", "center", "axis",
    "scale", "width", "height"}]}; axis is the side the camera looks from ("-y" is her front)."""
    import json
    reset()
    s = json.loads(spec.read_text())
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = s.get("color_type", "TEXTURE")
    scene.display.shading.single_color = (0.62, 0.62, 0.6)
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = False
    scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.55, 0.57, 0.6)
    mat = bpy.data.materials.new("m")
    mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(s["color"])
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    for i, m in enumerate(s["meshes"]):
        d = np.load(m["npz"])
        co = d["positions"] + np.array(m.get("offset", [0, 0, 0]))
        me = bpy.data.meshes.new(f"m{i}")
        me.from_pydata(co.tolist(), [], d["triangles"].tolist())
        uv = me.uv_layers.new()
        uv.data.foreach_set("uv", d["uvs"].reshape(-1).astype(np.float32))
        if "colors" in d.files:  # per vertex, for color_type "VERTEX"
            attr = me.color_attributes.new("c", "FLOAT_COLOR", "POINT")
            rgba = np.c_[d["colors"], np.ones(len(d["colors"]))].astype(np.float32)
            attr.data.foreach_set("color", rgba.reshape(-1))
            me.color_attributes.active_color = attr
        me.update()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"m{i}", me)
        scene.collection.objects.link(ob)
    rots = {"-y": (np.pi / 2, 0, 0), "+y": (np.pi / 2, 0, np.pi), "+x": (np.pi / 2, 0, np.pi / 2),
            "-x": (np.pi / 2, 0, -np.pi / 2), "+z": (0, 0, 0)}
    dirs = {"-y": (0, -1, 0), "+y": (0, 1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0), "+z": (0, 0, 1)}
    for v in s["views"]:
        cam_d = bpy.data.cameras.new("c")
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = v["scale"]
        cam_d.clip_end = 100
        cam = bpy.data.objects.new("c", cam_d)
        scene.collection.objects.link(cam)
        scene.camera = cam
        cam.location = np.array(v["center"]) + 10 * np.array(dirs[v["axis"]])
        cam.rotation_euler = rots[v["axis"]]
        scene.render.resolution_x = v["width"]
        scene.render.resolution_y = v["height"]
        scene.render.filepath = str(work / f"{v['name']}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    stage, work = args[0], Path(args[1])
    {"lods": lods, "citizen": citizen, "preview": preview}[stage](work, Path(args[2]))
