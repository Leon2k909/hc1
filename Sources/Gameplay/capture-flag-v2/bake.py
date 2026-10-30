"""Bake the facts the paint stage works from: position, normal, finish and occlusion, on the two atlases and the flag.

blender -b --factory-startup -t 2 --python bake.py -- <work dir> [occlusion samples]
Writes work/bake_<atlas>_<fact>.npy, floats, row 0 at the bottom of the image as Blender stores it.
"""
import hashlib
import math
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK = argv[0]
AO_SAMPLES = int(argv[1]) if len(argv) > 1 else 48

bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "capture_flag_build.blend"))
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.cycles.use_denoising = False
scene.cycles.use_adaptive_sampling = False
scene.cycles.max_bounces = 2

for ob in scene.objects:
    keep = ob.name.endswith("_lod0")
    ob.hide_render = not keep
    ob.hide_set(not keep)
    ob.select_set(False)

# The ground darkens everything down at its contact, as it does in a map.
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.01))
ground = bpy.context.object
ground.name = "ground"

world = bpy.data.worlds.new("bake")
scene.world = world
world.light_settings.distance = 9.0


def uv_hash(ob):
    """Identifies the hardware's UV layout, which the bakes and so all the painted maps belong to."""
    data = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    return hashlib.sha1(data.tobytes()).hexdigest()


def emit_material(name, build):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(emit.outputs[0], out.inputs[0])
    build(nt, emit)
    return mat


def position(nt, emit):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mapped = nt.nodes.new("ShaderNodeVectorMath")
    mapped.operation = "MULTIPLY_ADD"
    mapped.inputs[1].default_value = (1 / 400.0, 1 / 400.0, 1 / 400.0)
    mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
    nt.links.new(geo.outputs["Position"], mapped.inputs[0])
    nt.links.new(mapped.outputs[0], emit.inputs[0])


def normal(nt, emit):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mapped = nt.nodes.new("ShaderNodeVectorMath")
    mapped.operation = "MULTIPLY_ADD"
    mapped.inputs[1].default_value = (0.5, 0.5, 0.5)
    mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
    nt.links.new(geo.outputs["Normal"], mapped.inputs[0])
    nt.links.new(mapped.outputs[0], emit.inputs[0])


def facts(nt, emit):
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "facts"
    nt.links.new(attr.outputs[0], emit.inputs[0])


def bake_one(ob, size, kind, build, samples, out_name):
    w, h = size
    img = bpy.data.images.new(out_name, w, h, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    mat = emit_material(out_name, build) if build else bpy.data.materials.new(out_name)
    mat.use_nodes = True
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    tex.select = True
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    scene.cycles.samples = samples
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    ob.select_set(False)
    data = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(data)
    np.save(os.path.join(WORK, out_name + ".npy"), data.reshape(h, w, 4))
    bpy.data.images.remove(img)
    print("baked", out_name, flush=True)


hw = bpy.data.objects["hw_lod0"]
with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
    h.write(uv_hash(hw))
soft = bpy.data.objects["soft_lod0"]
flag = bpy.data.objects["flag_lod0"]
rope = bpy.data.objects["rope_lod0"]
for ob in (hw, soft, flag, rope):
    ob.hide_set(False)

bake_one(hw, (2048, 2048), "EMIT", position, 1, "bake_hw_pos")
bake_one(hw, (2048, 2048), "EMIT", normal, 1, "bake_hw_nor")
bake_one(hw, (2048, 2048), "EMIT", facts, 1, "bake_hw_facts")
bake_one(soft, (2048, 2048), "EMIT", position, 1, "bake_soft_pos")
bake_one(soft, (2048, 2048), "EMIT", normal, 1, "bake_soft_nor")
bake_one(flag, (1024, 512), "EMIT", position, 1, "bake_flag_pos")
bake_one(hw, (1024, 1024), "AO", None, AO_SAMPLES, "bake_hw_ao")
bake_one(soft, (1024, 1024), "AO", None, AO_SAMPLES, "bake_soft_ao")
print("bake done", flush=True)
