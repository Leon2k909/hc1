"""Blender side of zombie_male_02.py (run by it: blender -b --python this -- <stage> <work dir> ...).

Stage "lods": the Meshy scan (1.9M triangles) is decimated to each LOD's triangle count. Its UV atlas has more seams
than even LOD0 has edges, so decimating it puts triangles across islands (shards of the wrong texture at the neck,
collar and cheek): each LOD is unwrapped afresh and its own colour, roughness and normal maps are baked from the scan.
The scan's custom normals are dropped first (see `decimated`). Each LOD is saved as lod<i>.npz (positions in metres, Blender's axes: the
zombie faces -Y, its left is +X, feet on z = 0) with lod<i>_color/_rough/_normal.png. The scan's metallic map is
black (0.5% of a percent on average), so the material has none.

Stage "citizen": the citizen's reference body (citizen_human_male_REF.fbx in s&box's citizen addon) is saved as
citizen.npz: its body meshes' positions, triangles and bone weights, and its bones' rest heads.
"""

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import bpy
import numpy as np

SCAN = "Meshy_AI_Zombie_20260901_texture"


@dataclass(frozen=True)
class Lod:
    triangles: int
    size: int         # baked maps, pixels square
    extrusion: float  # metres: bake rays start this far outside the LOD and reach `reach` in. LOD0 is within a few
    reach: float      # millimetres of the scan; the shirt's flaps are thin, and rays starting further out hit their far side
    angle: float      # smart UV project's angle limit: wider makes fewer islands, each more stretched


# Smart UV project cuts a decimated body into 800-2,700 islands (the cloth's folds), so the gaps between them are kept
# to ISLAND_GAP pixels and the LODs seen far off get bigger maps and wider islands than their distance alone needs.
# zombie_male_02.py fills every pixel outside the islands from the nearest one, so lower mips don't bleed black.
# The lower LODs' surfaces stray further from the scan, so their rays reach further. (Their unbaked pixels, 0.2% of
# LOD1's islands and 1.8% of LOD3's, are triangles smaller than a pixel in UV, not misses: reach didn't change them.
# zombie_male_02.py fills those from their neighbours.)
LODS = [Lod(30000, 2048, 0.01, 0.025, 80), Lod(15000, 1024, 0.012, 0.05, 80), Lod(7000, 1024, 0.02, 0.08, 89),
        Lod(3000, 512, 0.03, 0.12, 89)]
ISLAND_GAP = 2


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
    uv = np.empty(len(m.loops) * 2, np.float32)
    m.uv_layers.active.data.foreach_get("uv", uv)
    nrm = np.empty(len(m.loops) * 3, np.float32)
    m.corner_normals.foreach_get("vector", nrm)
    nrm = nrm.reshape(-1, 3) @ np.linalg.inv(M[:3, :3])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return co, tris.reshape(-1, 3), uv.reshape(-1, 2)[loops].reshape(-1, 3, 2), nrm[loops].reshape(-1, 3, 3)


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
    # The scan's custom normals don't survive decimation (the bake then made up for them triangle by triangle, which
    # the engine's own tangents wouldn't match): plain smooth normals.
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def scan_material(src: Path):
    """The scan's own maps, to bake from."""
    mat = bpy.data.materials.new("scan")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = 0.0

    def image(suffix, noncolor):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(src / f"{SCAN}{suffix}.png"))
        if noncolor:
            node.image.colorspace_settings.name = "Non-Color"
        return node

    links.new(image("", False).outputs[0], bsdf.inputs["Base Color"])
    links.new(image("_roughness", True).outputs[0], bsdf.inputs["Roughness"])
    normal = nodes.new("ShaderNodeNormalMap")
    links.new(image("_normal", True).outputs[0], normal.inputs["Color"])
    links.new(normal.outputs[0], bsdf.inputs["Normal"])
    return mat


def unwrap(ob, lod: Lod):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(lod.angle), island_margin=ISLAND_GAP / lod.size, area_weight=0.0)
    # Repacked: half again as much of the map as smart project's own packing (its "FRACTION" margins and concave
    # shapes left the low LODs' islands as points).
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method="SCALED", margin=ISLAND_GAP / lod.size)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake_maps(high, low, lod: Lod, prefix: Path):
    """lod's colour, roughness and normal maps, baked from the scan into its own UVs."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    bake = scene.render.bake
    bake.use_selected_to_active = True
    bake.cage_extrusion = lod.extrusion
    bake.max_ray_distance = lod.reach
    bake.margin = max(4, lod.size // 128)
    bake.margin_type = "EXTEND"
    bake.normal_space = "TANGENT"
    bake.use_pass_direct = False
    bake.use_pass_indirect = False
    bake.use_pass_color = True
    target = bpy.data.materials.new(f"{low.name}_bake")
    target.use_nodes = True
    node = target.node_tree.nodes.new("ShaderNodeTexImage")
    target.node_tree.nodes.active = node
    low.data.materials.clear()
    low.data.materials.append(target)
    for kind, bake_type, colour in [("color", "DIFFUSE", "sRGB"), ("rough", "ROUGHNESS", "Non-Color"),
                                    ("normal", "NORMAL", "Non-Color")]:
        image = bpy.data.images.new(f"{low.name}_{kind}", lod.size, lod.size)
        image.colorspace_settings.name = colour
        node.image = image
        bpy.ops.object.select_all(action="DESELECT")
        high.select_set(True)
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.bake(type=bake_type)
        image.filepath_raw = f"{prefix}_{kind}.png"
        image.file_format = "PNG"
        image.save()


def lods(work: Path, src: Path):
    reset()
    bpy.ops.import_scene.fbx(filepath=str(src / f"{SCAN}.fbx"))
    high = next(o for o in bpy.data.objects if o.type == "MESH")
    bpy.context.view_layer.objects.active = high
    high.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = np.empty(len(high.data.vertices) * 3, np.float32)
    high.data.vertices.foreach_get("co", co)
    high.location.z = -float(co[2::3].min())  # feet on the floor
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    high.data.materials.clear()
    high.data.materials.append(scan_material(src))
    previous = high
    for i, lod in enumerate(LODS):
        # Each LOD is made from the one before, which is faster and keeps their silhouettes alike.
        ob = decimated(previous, lod.triangles, f"lod{i}")
        previous = ob
        unwrap(ob, lod)
        bake_maps(high, ob, lod, work / f"lod{i}")
        co, tris, uv, nrm = mesh_arrays(ob)
        np.savez(work / f"lod{i}.npz", positions=co, triangles=tris, uvs=uv, normals=nrm)
        print(f"lod{i}: {len(tris)} triangles, {len(co)} vertices, {lod.size}px maps")
    bpy.ops.wm.save_as_mainfile(filepath=str(work / "lods.blend"))


def citizen(work: Path, fbx: Path):
    """fbx: citizen_human_male_REF.fbx."""
    reset()
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    bones = [b.name for b in arm.data.bones]
    heads = np.array([list(arm.matrix_world @ b.head_local) for b in arm.data.bones])
    parts = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not any(k in ob.name for k in ("chest", "hands", "legs", "feet", "head")):
            continue
        co, tris, _, _ = mesh_arrays(ob)
        w = np.zeros((len(co), len(bones)), np.float32)
        names = {g.index: g.name for g in ob.vertex_groups}
        for v in ob.data.vertices:
            for g in v.groups:
                if names[g.group] in bones:
                    w[v.index, bones.index(names[g.group])] = g.weight
        parts[ob.name] = (co, tris, w)
    offsets = np.cumsum([0] + [len(p[0]) for p in parts.values()])
    np.savez(work / "citizen.npz", bones=np.array(bones), heads=heads,
             positions=np.concatenate([p[0] for p in parts.values()]),
             triangles=np.concatenate([p[1] + o for p, o in zip(parts.values(), offsets)]),
             weights=np.concatenate([p[2] for p in parts.values()]),
             part=np.concatenate([np.full(len(p[0]), i) for i, p in enumerate(parts.values())]),
             part_names=np.array(list(parts)))


def preview(work: Path):
    """Renders zombie_male_02.py's work/preview.npz: each panel's meshes from the front and the side."""
    reset()
    data = np.load(work / "preview.npz")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("world")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.type = "ORTHO"
    scene.collection.objects.link(camera)
    scene.camera = camera
    materials = {}

    def material(name):
        if name in materials:
            return materials[name]
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes["Principled BSDF"]
        if name == "wire":
            bsdf.inputs["Base Color"].default_value = (0.9, 0.05, 0.05, 1)
            bsdf.inputs["Emission Color"].default_value = (0.9, 0.05, 0.05, 1)
            bsdf.inputs["Emission Strength"].default_value = 1.0
        else:
            for kind, socket, noncolor in [("color", "Base Color", False), ("rough", "Roughness", True)]:
                node = nodes.new("ShaderNodeTexImage")
                node.image = bpy.data.images.load(str(work / f"{name}_{kind}.png"))
                if noncolor:
                    node.image.colorspace_settings.name = "Non-Color"
                links.new(node.outputs[0], bsdf.inputs[socket])
            node = nodes.new("ShaderNodeTexImage")
            node.image = bpy.data.images.load(str(work / f"{name}_normal.png"))
            node.image.colorspace_settings.name = "Non-Color"
            normal = nodes.new("ShaderNodeNormalMap")
            links.new(node.outputs[0], normal.inputs["Color"])
            links.new(normal.outputs[0], bsdf.inputs["Normal"])
        materials[name] = mat
        return mat

    for panel in data["panels"]:
        objects = []
        k = 0
        while f"{panel}_{k}_pos" in data:
            pos, tris = data[f"{panel}_{k}_pos"], data[f"{panel}_{k}_tri"]
            mesh = bpy.data.meshes.new(f"{panel}_{k}")
            mesh.from_pydata(pos.tolist(), [], tris.tolist())
            if f"{panel}_{k}_uv" in data:
                uv = mesh.uv_layers.new()
                uv.data.foreach_set("uv", data[f"{panel}_{k}_uv"].reshape(-1).astype(np.float32))
            for p in mesh.polygons:
                p.use_smooth = True
            ob = bpy.data.objects.new(mesh.name, mesh)
            scene.collection.objects.link(ob)
            kind = str(data[f"{panel}_{k}_mat"])
            ob.data.materials.append(material(kind))
            if kind == "wire":
                wire = ob.modifiers.new("wire", "WIREFRAME")
                wire.thickness = 0.002
            objects.append(ob)
            k += 1
        co = np.concatenate([data[f"{panel}_{i}_pos"] for i in range(k)])
        lo, hi = co.min(0), co.max(0)
        centre = (lo + hi) / 2
        width = max(hi[0] - lo[0], hi[1] - lo[1])
        scene.render.resolution_y = 1000
        scene.render.resolution_x = int(1000 * max(0.6, (width + 0.2) / (hi[2] - lo[2] + 0.1)))
        camera.data.ortho_scale = max(hi[2] - lo[2] + 0.1, width + 0.2)
        for view, location, rotation in [("front", (centre[0], -5, centre[2]), (math.pi / 2, 0, 0)),
                                         ("side", (5, centre[1], centre[2]), (math.pi / 2, 0, math.pi / 2))]:
            camera.location = location
            camera.rotation_euler = rotation
            scene.render.filepath = str(work / f"preview_{panel}_{view}.png")
            bpy.ops.render.render(write_still=True)
        for ob in objects:
            bpy.data.objects.remove(ob)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    stage, work = args[0], Path(args[1])
    if stage == "preview":
        preview(work)
    else:
        {"lods": lods, "citizen": citizen}[stage](work, Path(args[2]))
