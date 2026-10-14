"""Render the staged furniture in Blender for geometry/UV review, not game QA.

The small OBJ files are exported separately into output/belltower/quality/props-v1-studio.
Run with Blender --background --threads 4 --python Tools/belltower_furniture_preview.py.
"""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/"output/belltower/quality/props-v1-studio"
ASSETS=ROOT/"Assets"


def image_node(nodes,path,colour=False):
    node=nodes.new("ShaderNodeTexImage")
    node.image=bpy.data.images.load(str(path),check_existing=True)
    if not colour: node.image.colorspace_settings.name="Non-Color"
    return node


def material(name):
    m=bpy.data.materials.new(name+"-review")
    m.use_nodes=True
    nodes,links=m.node_tree.nodes,m.node_tree.links
    shader=nodes.get("Principled BSDF")
    if name in ("furniture_wood","furniture_wood_dark"):
        prefix=ASSETS/"materials/belltower/scans/brown_planks_03"
        colour=image_node(nodes,str(prefix)+"_diffuse_4k.png",True)
        tint=nodes.new("ShaderNodeMixRGB"); tint.blend_type="MULTIPLY"; tint.inputs[0].default_value=1
        tint.inputs[2].default_value=(1.08,.97,.82,1) if name=="furniture_wood" else (.83,.73,.60,1)
        links.new(colour.outputs["Color"],tint.inputs[1]); links.new(tint.outputs[0],shader.inputs["Base Color"])
        normal=image_node(nodes,str(prefix)+"_nor_gl_4k.png")
        normal_map=nodes.new("ShaderNodeNormalMap")
        links.new(normal.outputs["Color"],normal_map.inputs["Color"]); links.new(normal_map.outputs[0],shader.inputs["Normal"])
        rough=image_node(nodes,str(prefix)+"_rough_4k.png")
        links.new(rough.outputs["Color"],shader.inputs["Roughness"])
    elif name=="lantern_glass":
        shader.inputs["Base Color"].default_value=(.96,.92,.82,1)
        shader.inputs["Transmission Weight"].default_value=1
        shader.inputs["Roughness"].default_value=.10
        shader.inputs["IOR"].default_value=1.45
    elif name=="lamp_bulb":
        shader.inputs["Base Color"].default_value=(1,.84,.58,1)
        shader.inputs["Emission Color"].default_value=(1,.7,.35,1)
        shader.inputs["Emission Strength"].default_value=1.4
        shader.inputs["Roughness"].default_value=.35
    elif name=="lamp_reflector":
        shader.inputs["Base Color"].default_value=(.8,.77,.68,1)
        shader.inputs["Roughness"].default_value=.5
    elif name=="canvas_plain":
        path=ASSETS/"materials/buildings/canvas_plain_color.png"
        if path.exists(): links.new(image_node(nodes,path,True).outputs["Color"],shader.inputs["Base Color"])
        else: shader.inputs["Base Color"].default_value=(.52,.43,.29,1)
        shader.inputs["Roughness"].default_value=.95
    else:
        shader.inputs["Base Color"].default_value=(.025,.029,.027,1)
        shader.inputs["Metallic"].default_value=.65
        shader.inputs["Roughness"].default_value=.48
    return m


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


for name in ("cart","bench","lantern","sack"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=48
    scene.cycles.use_denoising=True
    scene.render.threads_mode="FIXED"; scene.render.threads=4
    scene.render.resolution_x=1600; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
    scene.view_settings.view_transform="AgX"
    bpy.ops.wm.obj_import(filepath=str(FOLDER/(name+".obj")),forward_axis="NEGATIVE_Z",up_axis="Y")
    props=[o for o in scene.objects if o.type=="MESH"]
    for obj in props:
        obj.scale=(.0254,)*3
        for slot in obj.material_slots: slot.material=material(slot.material.name)
    bpy.context.view_layer.update()
    bounds=[o.matrix_world@Vector(p) for o in props for p in o.bound_box]
    lo=Vector(tuple(min(v[k] for v in bounds) for k in range(3)))
    hi=Vector(tuple(max(v[k] for v in bounds) for k in range(3)))
    centre=(lo+hi)/2; extent=max(hi-lo)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,lo.z-.01))
    ground=bpy.data.materials.new("Warm grey studio floor"); ground.diffuse_color=(.15,.145,.125,1)
    bpy.context.object.data.materials.append(ground)
    world=bpy.data.worlds.new("Studio"); world.use_nodes=True; scene.world=world
    world.node_tree.nodes.get("Background").inputs[0].default_value=(.55,.63,.78,1)
    world.node_tree.nodes.get("Background").inputs[1].default_value=.45
    bpy.ops.object.light_add(type="AREA",location=centre+Vector((-1.1,-1.2,1.6))*extent)
    key=bpy.context.object; key.data.energy=500*extent*extent; key.data.shape="DISK"; key.data.size=extent*.8
    key.data.color=(1,.88,.69); aim(key,centre)
    bpy.ops.object.light_add(type="AREA",location=centre+Vector((1,1,1))*extent)
    fill=bpy.context.object; fill.data.energy=200*extent*extent; fill.data.size=extent
    fill.data.color=(.75,.84,1); aim(fill,centre)
    bpy.ops.object.camera_add(location=centre+Vector((-.8,-1.25,.7))*extent)
    camera=bpy.context.object; camera.data.lens=43; aim(camera,centre)
    scene.camera=camera
    scene.render.filepath=str(FOLDER/(name+".png"))
    bpy.ops.render.render(write_still=True)
    print("REVIEW "+name,flush=True)
