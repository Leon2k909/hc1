"""The Zombies workbench: the user's own Blender workbench, baked and exported for s&box.

The user modelled the bench in Blender (C:/Users/leon2/Documents/Workbench/Workbench.blend). Its game-ready copy,
GameReady/Workbench_GameReady.blend, has the modifiers applied, the mesh decimated and triangulated, and two UV
atlases packed: one for the bench's woodwork and fittings (the WB_Bench collection) and one for everything on it
(tools, the vise, the shelf's and floor's props). The materials are procedural Cycles node trees, so this script bakes
them into textures and writes:

  Assets/models/zombies/workbench/
    workbench.obj / .mtl     the mesh, in s&box inches, its back at x -20 and its middle at y 0, standing on z 0
    workbench.vmdl           the OBJ with its materials (no collision: the station's BoxCollider is it)
    workbench_<set>_{color,rough,metal,normal,ao}.png   for the bench, the props and the pegboard
    workbench_<set>.vmat     those, and the jars' glass and the shop light's lens (no textures)

Bakes (Cycles), a dozen objects at a time onto a joined copy of them, selected-to-active from the objects themselves
(see joined_copy and CHUNK), then each UV island grown 16 texels (grow_islands):
  colour, roughness and metalness: each Principled BSDF's input wired into an emission shader, baked as EMIT;
  normal: tangent space, with the materials' bump nodes (OpenGL, green up, as s&box reads it);
  AO: Cycles' AO pass, 0.3 m.
The pegboard's holes are its material's alpha: they're baked dark into its colour (what's behind a hole is shadow) and
kept opaque, since its back face shares its UVs.

In the .blend the bench runs along X (72 wide), its front is -Y and the vise is at -X, on the left of someone facing
it. The Zombies stations face +X (ZombiesRoundSystem.CreateStation), so the model is turned a quarter: model x is
Blender's -y and model y is Blender's x, which keeps the vise on the left. ModelDoc reads an OBJ as Y-up, so model
(X, Y, Z) is written as OBJ (Y, Z, X), as in Tools/ridgeback_buildings.py.

Run:
  blender -b --python Tools/zombies_workbench.py -- [--blend <GameReady .blend>] [--size 2048] [--samples 8]
"""

import argparse
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Assets" / "models" / "zombies" / "workbench"
RESOURCE = "models/zombies/workbench"
DEFAULT_BLEND = Path("C:/Users/leon2/Documents/Workbench/GameReady/Workbench_GameReady.blend")

INCHES = 39.37008
# The back of the top shelf (Blender y 18.5") goes to x -20, so the station's 40-deep BoxCollider, centred on the
# origin, runs from the back to the vise's handle (Blender y -21.2" -> 19.7). The wood shavings on the floor lie
# further out in front, with no collision.
BACK_X = -20.0

# Objects with materials of their own: the jars (glass, no texture) and the shop light's lens (lit, no texture).
GLASS = {"WB_Jar_0", "WB_Jar_1"}
LED = {"WB_ShopLight_Lens"}
PEGBOARD = {"WB_Pegboard", "WB_Pegboard_Back"}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", default=str(DEFAULT_BLEND))
    p.add_argument("--size", type=int, default=2048)
    p.add_argument("--samples", type=int, default=8)
    p.add_argument("--ao-samples", type=int, default=128)
    p.add_argument("--out", default=str(OUT))
    return p.parse_args(argv)


def groups():
    """Each exported object's material set: bench, pegboard, props, glass or led."""
    out = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or o.hide_render or not o.users_collection:
            continue
        cols = {c.name for c in o.users_collection}
        if not any(c.startswith("WB_") for c in cols):
            continue  # the template's default cube
        if o.name in GLASS:
            out[o.name] = "glass"
        elif o.name in LED:
            out[o.name] = "led"
        elif o.name in PEGBOARD:
            out[o.name] = "pegboard"
        elif "WB_Bench" in cols:
            out[o.name] = "bench"
        else:
            out[o.name] = "props"
    return out


def use_cycles(scene, samples):
    scene.render.engine = "CYCLES"
    # A headless Blender starts with no compute device set, so look for one: on the CPU the props' bake alone takes
    # several minutes a map.
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpu = False
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
        except Exception:
            continue
        devices = [d for d in prefs.devices if d.type == kind]
        if devices:
            for d in prefs.devices:
                d.use = d.type == kind
            gpu = True
            print(f"[workbench] baking on {kind}: {', '.join(d.name for d in devices)}", flush=True)
            break
    scene.cycles.device = "GPU" if gpu else "CPU"
    scene.cycles.samples = samples
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake_world")


def principled(mat):
    out = next((n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if out is None or not out.inputs["Surface"].is_linked:
        return None, None
    node = out.inputs["Surface"].links[0].from_node
    return (node if node.type == "BSDF_PRINCIPLED" else None), out


class Rewire:
    """Wires one Principled input into an emission shader on every material, for an EMIT bake, and puts it back."""

    def __init__(self, mats, socket):
        self.saved = []
        for mat in mats:
            bsdf, out = principled(mat)
            if bsdf is None:
                continue
            nt = mat.node_tree
            emit = nt.nodes.new("ShaderNodeEmission")
            emit.inputs["Strength"].default_value = 1.0
            src = bsdf.inputs[socket]
            if src.is_linked:
                nt.links.new(src.links[0].from_socket, emit.inputs["Color"])
            else:
                v = src.default_value
                emit.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1.0)
            nt.links.new(emit.outputs[0], out.inputs["Surface"])
            self.saved.append((nt, bsdf, out, emit))

    def restore(self):
        for nt, bsdf, out, emit in self.saved:
            nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
            nt.nodes.remove(emit)


# Selected-to-active: rays start this far outside the bake target's surface and look this far in for the user's own
# objects, whose surfaces it shares (metres, the .blend's units).
CAGE_EXTRUSION = 0.0005
MAX_RAY = 0.005


def joined_copy(objs, name):
    """The bake target: one mesh of the set's objects, modifiers applied, keeping each one's active UVs, normals and
    materials, hidden from the render.

    Blender bakes the objects of a bake call one at a time, setting the scene up again for each: on the GPU the
    bench's 55 objects took two minutes a map at 512, and the props' 255 would take most of an hour at full size. A
    joined copy bakes in one go. But it can't be baked from itself: the materials read each object's own colour,
    random value, attributes and object-space coordinates, which a joined mesh doesn't have (the painted vise and the
    toolbox came out bare). So it's baked selected-to-active from the user's objects, which shade as they are in the
    .blend, and the copy only carries the UVs.
    """
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    temps = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(depsgraph), preserve_all_data_layers=True,
                                             depsgraph=depsgraph)
        active = me.uv_layers.active.name if me.uv_layers.active else None
        for layer_name in [l.name for l in me.uv_layers if l.name != active]:
            me.uv_layers.remove(me.uv_layers[layer_name])
        if me.uv_layers:
            me.uv_layers[0].name = "bake"
        me.materials.clear()
        for slot in o.material_slots:
            me.materials.append(slot.material)
        t = bpy.data.objects.new(f"bake_{name}_{o.name}", me)
        t.matrix_world = o.matrix_world
        scene.collection.objects.link(t)
        temps.append(t)
    # Joined into an object at the origin, so the cage's extrusion is in metres.
    base = bpy.data.objects.new(f"bake_{name}", bpy.data.meshes.new(f"bake_{name}"))
    base.data.uv_layers.new(name="bake")
    # The base's own (empty) first slot would stay on the joined mesh, with no texture node to bake into.
    base.data.materials.append(temps[0].data.materials[0] if temps[0].data.materials else None)
    scene.collection.objects.link(base)
    joined = temps + [base]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in joined)
    bpy.context.view_layer.objects.active = base
    with bpy.context.temp_override(active_object=base, selected_objects=joined, selected_editable_objects=joined):
        bpy.ops.object.join()
    uv = base.data.uv_layers["bake"]
    base.data.uv_layers.active = uv
    uv.active_render = True
    base.hide_render = True
    # It lies on the objects' own surfaces: while it's renderable for its bake, the AO's and bounces' rays mustn't
    # meet it.
    for ray in ("diffuse", "glossy", "shadow", "transmission", "volume_scatter"):
        setattr(base, f"visible_{ray}", False)
    return base


# Objects per bake call. Selected-to-active tests each texel against every selected object, so one call for all the
# props' 255 took five minutes a map at 512, and a call per object pays Blender's setup 310 times a map.
CHUNK = 12
# How far each UV island is grown once every chunk is in. Blender's own margin can't be used: one chunk's would paint
# over the islands of the chunks baked before it.
MARGIN = 16


def bake_set(objs, name, width, height, args):
    """Bakes the set's objects, a chunk at a time onto joined copies, into images named workbench_<name>_<map>;
    returns {map: image}."""
    chunks = [objs[i:i + CHUNK] for i in range(0, len(objs), CHUNK)]
    copies = [joined_copy(chunk, f"{name}_{k}") for k, chunk in enumerate(chunks)]
    passes = [("color", "Base Color", True), ("rough", "Roughness", False), ("metal", "Metallic", False)]
    if name == "pegboard":
        passes.append(("alpha", "Alpha", False))
    passes += [("normal", None, False), ("ao", None, False)]
    images = {}
    for kind, socket, colour in passes:
        # Alpha 0 until baked: what stays 0 is outside every island, for grow_islands.
        img = bpy.data.images.new(f"workbench_{name}_{kind}", width, height, alpha=True)
        img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        img.pixels.foreach_set(np.zeros(width * height * 4, np.float32))
        for chunk, copy in zip(chunks, copies):
            bake_chunk(chunk, copy, img, kind, socket, args)
        covered = grow_islands(img)
        images[kind] = img
        print(f"[workbench] baked {name} {kind}: {covered:.0%} of the texels", flush=True)
    for copy in copies:
        bpy.data.objects.remove(copy)
    return images


def bake_chunk(objs, copy, img, kind, socket, args):
    """One bake call: the chunk's objects onto their joined copy, into img."""
    scene = bpy.context.scene
    mats = {s.material for s in copy.material_slots if s.material}
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objs or o == copy)
    bpy.context.view_layer.objects.active = copy
    copy.hide_render = False

    nodes = []
    for mat in mats:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        mat.node_tree.nodes.active = tex
        nodes.append((mat.node_tree, tex))
    wire = Rewire(mats, socket) if socket else None
    if kind == "ao":
        scene.world.light_settings.distance = 0.3
        scene.cycles.samples = args.ao_samples
    else:
        scene.cycles.samples = args.samples

    bake_type = {"normal": "NORMAL", "ao": "AO"}.get(kind, "EMIT")
    extra = {"normal_space": "TANGENT"} if bake_type == "NORMAL" else {}
    bpy.ops.object.bake(type=bake_type, use_selected_to_active=True, cage_extrusion=CAGE_EXTRUSION,
                        max_ray_distance=MAX_RAY, use_clear=False, margin=0, target="IMAGE_TEXTURES", **extra)

    if wire:
        wire.restore()
    for nt, tex in nodes:
        nt.nodes.remove(tex)
    copy.hide_render = True


def grow_islands(img, texels=MARGIN):
    """Grows the baked texels (alpha 1) out by texels, each new one the mean of its grown neighbours, so mip levels
    don't bleed the background into the islands' edges; fills the rest with the islands' mean and makes it all opaque.
    Returns the share of the texels that were baked."""
    a = pixels(img)
    covered = a[..., 3] > 0.5
    share = float(covered.mean())
    rgb = a[..., :3].copy()
    steps = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    for _ in range(texels):
        if covered.all():
            break
        total = np.zeros_like(rgb)
        count = np.zeros(covered.shape, np.float32)
        for dy, dx in steps:
            c = np.roll(covered, (dy, dx), axis=(0, 1))
            total += np.roll(rgb * covered[..., None], (dy, dx), axis=(0, 1))
            count += c
        new = ~covered & (count > 0)
        rgb[new] = total[new] / count[new][:, None]
        covered |= new
    if covered.any() and not covered.all():
        rgb[~covered] = rgb[covered].mean(axis=0)
    a[..., :3] = rgb
    a[..., 3] = 1.0
    set_pixels(img, a)
    return share


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def set_pixels(img, a):
    img.pixels.foreach_set(a.astype(np.float32).ravel())


def darken_holes(images):
    """The pegboard's holes (alpha 0) are shadow: dark, rough and occluded."""
    alpha = pixels(images.pop("alpha"))[..., :1]
    hole = 1.0 - np.clip(alpha, 0.0, 1.0)
    for kind, value in (("color", 0.035), ("rough", 1.0), ("ao", 0.15)):
        a = pixels(images[kind])
        a[..., :3] = a[..., :3] * (1.0 - hole) + value * hole
        set_pixels(images[kind], a)


def save(images, out_dir):
    for kind, img in images.items():
        img.filepath_raw = str(out_dir / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()


def world_coords(ob, depsgraph, me=None):
    """The object's evaluated vertices in world space, in inches."""
    ev = ob.evaluated_get(depsgraph)
    own = me is None
    if own:
        me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    if own:
        ev.to_mesh_clear()
    mw = np.array(ob.matrix_world)
    return (co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]) * INCHES


def export_obj(sets, out_dir):
    """Writes workbench.obj/.mtl: every object in world space, inches, in ModelDoc's axes."""
    lines_v, lines_vt, lines_vn, faces = [], [], [], {}
    nv = nt = nn = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    tris = 0
    # Blender (x, y, z) -> model (-y, x, z): a quarter turn, so the bench's front (Blender -y) faces model +x.
    turn = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    back = min(float(np.min(world_coords(bpy.data.objects[name], depsgraph) @ turn.T, axis=0)[0]) for name in sets)
    for name, group in sorted(sets.items()):
        ob = bpy.data.objects[name]
        ev = ob.evaluated_get(depsgraph)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        mw = np.array(ob.matrix_world)
        nm = turn @ np.array(ob.matrix_world.to_3x3().inverted_safe().transposed())
        co = world_coords(ob, depsgraph, me) @ turn.T
        co[:, 0] += BACK_X - back
        lo = np.minimum(lo, co.min(0))
        hi = np.maximum(hi, co.max(0))

        nloops = len(me.loops)
        ln = np.empty(nloops * 3, np.float32)
        me.corner_normals.foreach_get("vector", ln)
        ln = ln.reshape(-1, 3) @ nm.T
        ln /= np.maximum(np.linalg.norm(ln, axis=1, keepdims=True), 1e-8)
        uv = np.zeros((nloops, 2), np.float32)
        if me.uv_layers.active is not None:
            a = np.empty(nloops * 2, np.float32)
            me.uv_layers.active.data.foreach_get("uv", a)
            uv = a.reshape(-1, 2)

        tri_loops = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("loops", tri_loops)
        tri_loops = tri_loops.reshape(-1, 3)
        loop_vert = np.empty(nloops, np.int32)
        me.loops.foreach_get("vertex_index", loop_vert)
        if np.linalg.det(mw[:3, :3]) < 0:
            tri_loops = tri_loops[:, ::-1]

        uq_uv, uv_idx = np.unique(np.round(uv, 5), axis=0, return_inverse=True)
        uq_n, n_idx = np.unique(np.round(ln, 4), axis=0, return_inverse=True)
        uv_idx = uv_idx.ravel()
        n_idx = n_idx.ravel()
        lines_v += [f"v {p[1]:.4f} {p[2]:.4f} {p[0]:.4f}" for p in co]
        lines_vt += [f"vt {u:.5f} {v:.5f}" for u, v in uq_uv]
        lines_vn += [f"vn {n[1]:.4f} {n[2]:.4f} {n[0]:.4f}" for n in uq_n]
        out = faces.setdefault(f"workbench_{group}", [])
        for t in tri_loops:
            out.append("f " + " ".join(f"{nv + loop_vert[l] + 1}/{nt + uv_idx[l] + 1}/{nn + n_idx[l] + 1}" for l in t))
        tris += len(tri_loops)
        nv += len(co)
        nt += len(uq_uv)
        nn += len(uq_n)
        ev.to_mesh_clear()

    body = ["# Tools/zombies_workbench.py: the user's Blender workbench", "mtllib workbench.mtl", "o workbench"]
    body += lines_v + lines_vt + lines_vn
    for mat in sorted(faces):
        body.append(f"usemtl {mat}")
        body += faces[mat]
    (out_dir / "workbench.obj").write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")
    (out_dir / "workbench.mtl").write_text("".join(f"newmtl {m}\nKd 1 1 1\nd 1\n" for m in sorted(faces)),
                                           encoding="utf-8", newline="\n")
    print(f"[workbench] obj: {tris} triangles, {nv} vertices, bounds {np.round(lo, 2)} .. {np.round(hi, 2)}")
    return sorted(faces)


def write_vmats(out_dir):
    def textured(name, metal_tex=True):
        p = f"{RESOURCE}/workbench_{name}"
        metal = f'\tF_METALNESS_TEXTURE 1\n\tTextureMetalness "{p}_metal.png"\n' if metal_tex else '\tg_flMetalness "0.000"\n'
        return (
            "// Tools/zombies_workbench.py\n\nLayer0\n{\n"
            '\tshader "shaders/complex.shader"\n'
            "\tF_SPECULAR 1\n"
            f"{metal}"
            f'\tTextureColor "{p}_color.png"\n'
            f'\tTextureNormal "{p}_normal.png"\n'
            f'\tTextureRoughness "{p}_rough.png"\n'
            '\tg_flRoughnessScaleFactor "1.000"\n'
            f'\tTextureAmbientOcclusion "{p}_ao.png"\n'
            '\tg_flAmbientOcclusionDirectDiffuse "0.600"\n'
            '\tg_flAmbientOcclusionDirectSpecular "0.700"\n'
            '\tg_vColorTint "[1.000000 1.000000 1.000000 0.000000]"\n'
            '\tg_flModelTintAmount "1.000"\n'
            '\tg_bFogEnabled "1"\n'
            "}\n"
        )

    vmats = {
        "workbench_bench": textured("bench"),
        "workbench_props": textured("props"),
        "workbench_pegboard": textured("pegboard", metal_tex=False),
        # The jars' glass: its Blender colour, see-through. The screws inside are props.
        "workbench_glass": (
            "// Tools/zombies_workbench.py: the jars' glass\n\nLayer0\n{\n"
            '\tshader "shaders/complex.shader"\n'
            "\tF_SPECULAR 1\n"
            "\tF_TRANSLUCENT 1\n"
            '\tTextureColor "[0.716 0.694 0.604 1.0]"\n'
            '\tTextureTranslucency "[0.30 0.30 0.30 1.0]"\n'
            '\tTextureRoughness "[0.08 0.08 0.08 1.0]"\n'
            '\tg_flMetalness "0.000"\n'
            '\tg_bFogEnabled "1"\n'
            "}\n"
        ),
        # The shop light's lens: lit, warm white.
        "workbench_led": (
            "// Tools/zombies_workbench.py: the shop light's lens, self-lit\n\nLayer0\n{\n"
            '\tshader "shaders/complex.shader"\n'
            "\tF_SELF_ILLUM 1\n"
            '\tTextureColor "[1.0 0.96 0.88 1.0]"\n'
            '\tTextureSelfIllumMask "[1.0 1.0 1.0 1.0]"\n'
            '\tg_flSelfIllumBrightness "4.0"\n'
            '\tg_flSelfIllumAlbedoFactor "1.0"\n'
            '\tg_flMetalness "0.000"\n'
            '\tg_bFogEnabled "1"\n'
            "}\n"
        ),
    }
    for name, text in vmats.items():
        (out_dir / f"{name}.vmat").write_text(text, encoding="utf-8", newline="\n")


def write_vmdl(out_dir, materials):
    remaps = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{m}.vmat" to = "{RESOURCE}/{m}.vmat" }}' for m in materials)
    text = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
{{
\trootNode =
\t{{
\t\t_class = "RootNode"
\t\tchildren =
\t\t[
\t\t\t{{
\t\t\t\t_class = "MaterialGroupList"
\t\t\t\tchildren =
\t\t\t\t[
\t\t\t\t\t{{
\t\t\t\t\t\t_class = "DefaultMaterialGroup"
\t\t\t\t\t\tremaps =
\t\t\t\t\t\t[
{remaps}
\t\t\t\t\t\t]
\t\t\t\t\t\tuse_global_default = false
\t\t\t\t\t\tglobal_default_material = ""
\t\t\t\t\t}},
\t\t\t\t]
\t\t\t}},
\t\t\t{{
\t\t\t\t_class = "RenderMeshList"
\t\t\t\tchildren =
\t\t\t\t[
\t\t\t\t\t{{
\t\t\t\t\t\t_class = "RenderMeshFile"
\t\t\t\t\t\tname = "workbench"
\t\t\t\t\t\tfilename = "{RESOURCE}/workbench.obj"
\t\t\t\t\t\timport_translation = [ 0.0, 0.0, 0.0 ]
\t\t\t\t\t\timport_rotation = [ 0.0, 0.0, 0.0 ]
\t\t\t\t\t\timport_scale = 1.0
\t\t\t\t\t\talign_origin_x_type = "None"
\t\t\t\t\t\talign_origin_y_type = "None"
\t\t\t\t\t\talign_origin_z_type = "None"
\t\t\t\t\t\tparent_bone = ""
\t\t\t\t\t\timport_filter = {{ exclude_by_default = false exception_list = [ ] }}
\t\t\t\t\t}},
\t\t\t\t]
\t\t\t}},
\t\t]
\t\tmodel_archetype = ""
\t\tprimary_associated_entity = ""
\t\tanim_graph_name = ""
\t\tbase_model_name = ""
\t}}
}}
"""
    (out_dir / "workbench.vmdl").write_text(text, encoding="utf-8", newline="\n")


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=args.blend)
    scene = bpy.context.scene
    use_cycles(scene, args.samples)
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    sets = groups()
    counts = {g: sum(1 for v in sets.values() if v == g) for g in set(sets.values())}
    print(f"[workbench] sets {counts}", flush=True)

    size = args.size
    layout = (("bench", size, size), ("props", size, size), ("pegboard", size, size // 2))
    originals = {}
    for name, _, _ in layout:
        objs = [bpy.data.objects[o] for o, g in sets.items() if g == name]
        if name == "pegboard":
            # The back face shares the front's UVs: bake the front, and both use it.
            objs = [o for o in objs if o.name == "WB_Pegboard"]
        originals[name] = objs
    for name, w, h in layout:
        images = bake_set(originals[name], name, w, h, args)
        if name == "pegboard":
            darken_holes(images)
        save(images, out_dir)

    materials = export_obj(sets, out_dir)
    write_vmats(out_dir)
    write_vmdl(out_dir, materials)
    print("[workbench] done", flush=True)


if __name__ == "__main__":
    main()
