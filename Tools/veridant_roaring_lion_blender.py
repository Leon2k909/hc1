"""Prepare the Burlingame roaring-lion scan for the Veridant fountain crown (run inside Blender).

blender -b --factory-startup --threads 4 --python Tools/veridant_roaring_lion_blender.py -- <stage> <scan.glb> <work dir>

Stages
  prep   Import the CC-BY scan, join its parts, turn it so the head faces +X (outward from the pier),
         cut away the scanned concrete slab, scale it to game units and centre the mouth on Y=0.
         Saves high.blend and prep.json (bounds, mouth opening).
  lods   Decimate the cut scan into three LODs, unwrap LOD0 and bake LOD0's tangent normal map,
         ambient occlusion and the verdigris bronze colour / roughness / metalness from the full scan.
         Saves lod<i>.npz (positions, triangles, per-corner UVs and normals) and the texture PNGs.

The scan: "Lion Statue" by beachmouse (Sketchfab 9abb1020ee34465cab478616ece693ac), CC BY 4.0.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index("--") + 1:]
STAGE, SCAN, WORK = ARGS[0], Path(ARGS[1]), Path(ARGS[2])
WORK.mkdir(parents=True, exist_ok=True)

# Game units (inches). The lion lies along +X with its rump against the pier.
LION_LENGTH = 31.5          # rump to the tips of the front paws
RUMP_X = 5.4                # where the rump starts, clear of the pier's narrow face
BASE_TOP = 49.6             # top of the bronze base the lion lies on
SINK = 0.35                 # the cut underside sits this far into the base
LODS = (52000, 14000, 3800)
BAKE = 4096


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def arrays(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def prep():
    reset()
    bpy.ops.import_scene.gltf(filepath=str(SCAN), merge_vertices=True)
    parts = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    lion = bpy.context.view_layer.objects.active
    lion.name = "scan"
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # The head faces -Y in the imported scan: turn it to +X.
    lion.data.transform(Matrix.Rotation(math.radians(90), 4, "Z"))
    bm = bmesh.new()
    bm.from_mesh(lion.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.faces.ensure_lookup_table()
    # The slab: large upward faces in the lowest part of the scan.
    zs = np.array([v.co.z for v in bm.verts])
    zmin, zmax = zs.min(), zs.max()
    up = [f for f in bm.faces if f.normal.z > 0.97 and f.calc_center_median().z < zmin + 0.12 * (zmax - zmin)]
    area = np.array([f.calc_area() for f in up])
    heights = np.array([f.calc_center_median().z for f in up])
    order = np.argsort(heights)
    cumulative = np.cumsum(area[order]) / area.sum()
    slab_top = float(heights[order][np.searchsorted(cumulative, 0.5)])
    cut = slab_top + 0.012 * (zmax - zmin)
    doomed = [v for v in bm.verts if v.co.z < cut]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    # Keep the lion; the slab's scattered remnants become separate islands once the slab is cut.
    bm.verts.ensure_lookup_table()
    islands = []
    seen = set()
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, island = [v], []
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            island.append(cur)
            for e in cur.link_edges:
                other = e.other_vert(cur)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
        islands.append(island)
    islands.sort(key=len, reverse=True)
    keep = set()
    report_islands = []
    for island in islands:
        zz = np.array([v.co.z for v in island])
        rise = zz.max() - cut
        report_islands.append((len(island), round(float(rise), 4)))
        if len(island) == len(islands[0]) or (len(island) > 300 and rise > 0.08 * (zmax - zmin)):
            keep.update(v.index for v in island)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(lion.data)
    bm.free()
    co = arrays(lion)
    lo, hi = co.min(0), co.max(0)
    scale = LION_LENGTH / (hi[0] - lo[0])
    # Scale, rump at RUMP_X, underside SINK below the base top.
    m = Matrix.Translation((RUMP_X, 0, BASE_TOP - SINK)) @ Matrix.Scale(scale, 4) @ Matrix.Translation((-lo[0], 0, -cut))
    lion.data.transform(m)
    co = arrays(lion)
    # Find the open mouth: cast rays from the front along -X and look for the cavity between the jaws.
    bvh = BVHTree.FromObject(lion, bpy.context.evaluated_depsgraph_get())
    hi = co.max(0)
    head = co[co[:, 0] > hi[0] - 0.12 * LION_LENGTH]
    rows = []
    for z in np.linspace(head[:, 2].min(), head[:, 2].max(), 120):
        for y in np.linspace(head[:, 1].min(), head[:, 1].max(), 41):
            hit = bvh.ray_cast(Vector((hi[0] + 5, y, z)), Vector((-1, 0, 0)), 30)
            if hit[0] is not None:
                rows.append((float(z), float(y), float(hit[0].x)))
    rows = np.array(rows)
    report = {
        "scale": scale, "slab_top_source": slab_top, "cut_source": cut,
        "islands": report_islands[:12], "faces": len(lion.data.polygons),
        "bounds": [co.min(0).tolist(), co.max(0).tolist()],
    }
    np.save(WORK / "front_rays.npy", rows)
    (WORK / "prep.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "high.blend"))
    print("PREP", json.dumps(report))


MOUTH_Y = -1.09             # measured from prep's front rays: the open mouth sits off the scan's axis
CAGE = 0.06
MAX_RAY = 0.3


def select_only(*objects, active=None):
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objects[0]


def decimated(source, triangles, name):
    ob = source.copy()
    ob.data = source.data.copy()
    ob.name = name
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.use_collapse_triangulate = True
    mod.ratio = min(1.0, triangles / sum(len(p.vertices) - 2 for p in source.data.polygons))
    select_only(ob)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def mesh_arrays(ob):
    """Positions (V, 3), triangles (T, 3), per-corner UVs (T, 3, 2) and normals (T, 3, 3)."""
    me = ob.data
    me.calc_loop_triangles()
    co = arrays(ob).astype(np.float32)
    tris = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tris)
    loops = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    nrm = np.empty(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", nrm)
    uv = uv.reshape(-1, 2)[loops].reshape(-1, 3, 2)
    nrm = nrm.reshape(-1, 3)[loops].reshape(-1, 3, 3)
    return co, tris.reshape(-1, 3), uv, nrm


def bake_target(low, name, size):
    image = bpy.data.images.new(name, size, size, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("target_" + name)
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    mat.node_tree.nodes.active = node
    low.data.materials.clear()
    low.data.materials.append(mat)
    return image


def emission_source(high, build):
    """Give the scan an emission shader whose colour is build(nodes, links) (a socket)."""
    mat = bpy.data.materials.new("source")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(build(nt.nodes, nt.links), emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    high.data.materials.clear()
    high.data.materials.append(mat)


def bake(high, low, kind, name, size, path, samples):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    image = bake_target(low, name, size)
    select_only(high, low, active=low)
    b = scene.render.bake
    b.use_selected_to_active = True
    b.cage_extrusion = CAGE
    b.max_ray_distance = MAX_RAY
    b.margin = 24
    b.margin_type = "EXTEND"
    b.normal_space = "TANGENT"
    bpy.ops.object.bake(type=kind)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    print("BAKED", path)


def ingredients_a(nodes, links):
    """R: tight cavity occlusion, G: broad occlusion, B: convexity (pointiness)."""
    small = nodes.new("ShaderNodeAmbientOcclusion"); small.samples = 24; small.only_local = True
    small.inputs["Distance"].default_value = 0.7
    large = nodes.new("ShaderNodeAmbientOcclusion"); large.samples = 24; large.only_local = True
    large.inputs["Distance"].default_value = 4.0
    geo = nodes.new("ShaderNodeNewGeometry")
    point = nodes.new("ShaderNodeMapRange")
    point.inputs["From Min"].default_value = 0.42
    point.inputs["From Max"].default_value = 0.58
    links.new(geo.outputs["Pointiness"], point.inputs["Value"])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(small.outputs["AO"], combine.inputs[0])
    links.new(large.outputs["AO"], combine.inputs[1])
    links.new(point.outputs["Result"], combine.inputs[2])
    return combine.outputs["Color"]


def ingredients_b(nodes, links):
    """R: broad verdigris mottling, G: fine speckle, B: run-off streaks (stretched vertically)."""
    coord = nodes.new("ShaderNodeTexCoord")
    def noise(scale, detail, roughness, stretch=(1, 1, 1)):
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = stretch
        links.new(coord.outputs["Object"], mapping.inputs["Vector"])
        n = nodes.new("ShaderNodeTexNoise")
        n.noise_dimensions = "3D"
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = roughness
        links.new(mapping.outputs["Vector"], n.inputs["Vector"])
        return n.outputs["Fac"]
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(noise(0.33, 7, 0.62), combine.inputs[0])
    links.new(noise(2.6, 9, 0.7), combine.inputs[1])
    links.new(noise(0.55, 6, 0.6, (1.0, 1.0, 0.18)), combine.inputs[2])
    return combine.outputs["Color"]


def lods():
    bpy.ops.wm.open_mainfile(filepath=str(WORK / "high.blend"))
    high = bpy.data.objects["scan"]
    high.data.transform(Matrix.Translation((0, -MOUTH_Y, 0)))
    for p in high.data.polygons:
        p.use_smooth = True
    co = arrays(high)
    # Footprint and rump profile for fitting the bronze base and the pier.
    np.save(WORK / "high_points.npy", co.astype(np.float32))
    lod0 = decimated(high, LODS[0], "lod0")
    # The scan's surface noise splits a direct unwrap into thousands of slivers. Unwrap a heavily
    # smoothed copy (same topology, so the same loops) into clean charts and copy its UVs back.
    calm = lod0.copy()
    calm.data = lod0.data.copy()
    calm.name = "unwrap"
    bpy.context.scene.collection.objects.link(calm)
    smooth = calm.modifiers.new("smooth", "SMOOTH")
    smooth.factor = 1.0
    smooth.iterations = 60
    select_only(calm)
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0025, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = np.empty(len(calm.data.loops) * 2, np.float32)
    calm.data.uv_layers.active.data.foreach_get("uv", uv)
    if not lod0.data.uv_layers:
        lod0.data.uv_layers.new(name="UVMap")
    lod0.data.uv_layers.active.data.foreach_set("uv", uv)
    islands = len(set(map(tuple, np.round(uv.reshape(-1, 2), 4).tolist())))
    print("UNWRAP", len(calm.data.polygons), "faces", islands, "distinct uv corners")
    bpy.data.objects.remove(calm)
    previous = lod0
    for i, triangles in enumerate(LODS):
        ob = lod0 if i == 0 else decimated(previous, triangles, f"lod{i}")
        c, t, uv, nrm = mesh_arrays(ob)
        np.savez(WORK / f"lod{i}.npz", positions=c, triangles=t, uvs=uv, normals=nrm)
        print(f"LOD{i}", len(t), "triangles", len(c), "vertices")
        previous = ob
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 12
    bake(high, lod0, "NORMAL", "normal", BAKE, WORK / "lion_normal.png", 4)
    emission_source(high, ingredients_a)
    bake(high, lod0, "EMIT", "occlusion", BAKE, WORK / "lion_ingredients_a.png", 24)
    emission_source(high, ingredients_b)
    bake(high, lod0, "EMIT", "noise", BAKE, WORK / "lion_ingredients_b.png", 1)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "lods.blend"))


if STAGE == "prep":
    prep()
elif STAGE == "lods":
    lods()
