"""Blender construction preview of the staged well; not a native game capture."""
import math
import os
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/well-v1/preview'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE = ROOT/'output/belltower/well-v1/preview-assets/Assets/models/maps/belltower/well-v1/garden_well.obj'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Soft daylight')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.63,.71,.80,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.50


def image_node(nodes,path,noncolor=False):
    node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(ROOT/'Assets'/path),check_existing=True)
    if noncolor:node.image.colorspace_settings.name='Non-Color'
    return node


def stone(name,tint,normal,roughness):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    photo=image_node(nodes,'materials/belltower/scans/medieval_blocks_03_diffuse_4k.png')
    multiply=nodes.new('ShaderNodeVectorMath');multiply.operation='MULTIPLY';multiply.inputs[1].default_value=tint
    links.new(photo.outputs['Color'],multiply.inputs[0]);links.new(multiply.outputs[0],bsdf.inputs['Base Color'])
    normals=image_node(nodes,'materials/belltower/scans/medieval_blocks_03_nor_gl_4k.png',True)
    decode=nodes.new('ShaderNodeNormalMap');decode.inputs['Strength'].default_value=normal
    links.new(normals.outputs['Color'],decode.inputs['Color']);links.new(decode.outputs['Normal'],bsdf.inputs['Normal'])
    rough=image_node(nodes,'materials/belltower/scans/medieval_blocks_03_rough_4k.png',True)
    limit=nodes.new('ShaderNodeMath');limit.operation='MAXIMUM';limit.inputs[1].default_value=roughness
    links.new(rough.outputs['Color'],limit.inputs[0]);links.new(limit.outputs[0],bsdf.inputs['Roughness'])
    return mat


materials={
    'well_cut_stone':stone('Cut limestone',(1.04,1.01,.93),.42,.72),
    'well_damp_stone':stone('Damp inner stone',(.40,.46,.39),.42,.50),
    'well_mortar':stone('Recessed mortar',(.30,.29,.25),.20,.96),
    'well_depth':stone('Dark shaft bed',(.035,.05,.04),0,.98)}
mat=bpy.data.materials.new('Quiet well water');mat.use_nodes=True
nodes,links=mat.node_tree.nodes,mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(.016,.041,.038,1)
bsdf.inputs['Roughness'].default_value=.12;bsdf.inputs['Metallic'].default_value=.02
bsdf.inputs['IOR'].default_value=1.333;bsdf.inputs['Transmission Weight'].default_value=.10
normal=image_node(nodes,'materials/belltower/fountain_water_normal.png',True)
decode=nodes.new('ShaderNodeNormalMap');decode.inputs['Strength'].default_value=.24
links.new(normal.outputs['Color'],decode.inputs['Color']);links.new(decode.outputs['Normal'],bsdf.inputs['Normal'])
materials['well_water']=mat

positions=[None];uvs=[None];normals=[None];faces=[];paints=[];loop_uvs=[];loop_normals=[];paint=None
for line in SOURCE.read_text().splitlines():
    values=line.split()
    if not values:continue
    if values[0]=='v':
        x,y,z=map(float,values[1:]);positions.append((-x,z,y))
    elif values[0]=='vt':uvs.append(tuple(map(float,values[1:3])))
    elif values[0]=='vn':
        x,y,z=map(float,values[1:]);normals.append((-x,z,y))
    elif values[0]=='usemtl':paint=values[1]
    elif values[0]=='f':
        indices=[list(map(int,v.split('/'))) for v in values[1:]]
        faces.append([i[0]-1 for i in indices]);paints.append(paint)
        loop_uvs.extend(uvs[i[1]] for i in indices);loop_normals.extend(normals[i[2]] for i in indices)
mesh=bpy.data.meshes.new('Constructed well');mesh.from_pydata(positions[1:],[],faces);mesh.update()
obj=bpy.data.objects.new('Garden well replacement',mesh);scene.collection.objects.link(obj)
slots=list(materials)
for p in slots:mesh.materials.append(materials[p])
for poly,paint in zip(mesh.polygons,paints):poly.material_index=slots.index(paint);poly.use_smooth=True
layer=mesh.uv_layers.new(name='Photographed stone UVs')
for loop,uv in zip(layer.data,loop_uvs):loop.uv=uv
mesh.normals_split_custom_set(loop_normals)

# A neutral grass base is only a studio backdrop, outside the production model.
bpy.ops.mesh.primitive_plane_add(size=1200,location=(0,0,-.05))
ground=bpy.context.object;ground.name='Studio ground'
mat=bpy.data.materials.new('Studio grass');mat.use_nodes=True
nodes,links=mat.node_tree.nodes,mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=.16;tex.inputs['Detail'].default_value=3.5
coord=nodes.new('ShaderNodeTexCoord');links.new(coord.outputs['Object'],tex.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.075,.093,.035,1)
ramp.color_ramp.elements[1].color=(.24,.27,.11,1);links.new(tex.outputs['Fac'],ramp.inputs[0])
links.new(ramp.outputs[0],bsdf.inputs['Base Color']);bsdf.inputs['Roughness'].default_value=.94
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.32;bump.inputs['Distance'].default_value=.3
links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],bsdf.inputs['Normal'])
ground.data.materials.append(mat)

sun=bpy.data.lights.new('Late morning sun','SUN');sun.energy=2.3;sun.angle=math.radians(5)
lamp=bpy.data.objects.new('Late morning sun',sun);scene.collection.objects.link(lamp)
lamp.rotation_euler=(math.radians(28),math.radians(-25),math.radians(-35))
camera=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camera)
scene.collection.objects.link(cam);scene.camera=cam;camera.clip_end=2500
for name,position,target,lens in (
    ('above',(108,-137,153),(0,0,12),52),
    ('low',(116,-146,72),(0,0,14),56)):
    cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camera.lens=lens;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    print('WELL_REVIEW '+name,flush=True)
