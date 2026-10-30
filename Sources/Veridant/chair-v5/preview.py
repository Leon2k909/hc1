"""Blender-only preview/export of the actual CC0 mesh; no game assets changed."""
import json
from pathlib import Path
import math
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[2]/'output/veridant/chair-v5'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'dining_chair_02_2k.gltf'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert meshes
points=[o.matrix_world@Vector(p) for o in meshes for p in o.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
centre=(lo+hi)*.5
for obj in meshes:
    obj.location-=Vector((centre.x,centre.y,lo.z))
    for material in obj.data.materials:
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:
                    old=Path(bpy.path.abspath(node.image.filepath))
                    candidate=ROOT/'textures'/(old.stem+'.png')
                    if candidate.exists():
                        previous_space=node.image.colorspace_settings.name
                        node.image=bpy.data.images.load(str(candidate),check_existing=True)
                        node.image.colorspace_settings.name=previous_space
    for face in obj.data.polygons: face.use_smooth=True
height=hi.z-lo.z
report={'bounds_metres':[list(lo),list(hi)],'height_metres':height,'objects':[]}
export=[]
for obj in meshes:
    mesh=obj.data;mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active
    vertices=[];normals=[];texcoords=[]
    normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
    for tri in mesh.loop_triangles:
        for loop in tri.loops:
            vertex=mesh.loops[loop].vertex_index
            vertices.append(list(obj.matrix_world@mesh.vertices[vertex].co))
            normals.append(list((normal_matrix@mesh.corner_normals[loop].vector).normalized()))
            texcoords.append(list(uv.data[loop].uv))
    report['objects'].append({'name':obj.name,'triangles':len(vertices)//3})
    export.append({'name':obj.name,'positions':vertices,'normals':normals,'uv':texcoords})
(OUT/'mesh.json').write_text(json.dumps(export,separators=(',',':')),encoding='utf-8')
(OUT/'source-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002))
floor=bpy.context.object
material=bpy.data.materials.new('Preview floor');material.diffuse_color=(.14,.15,.16,1)
material.use_nodes=True
material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.14,.15,.16,1)
material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.72
floor.data.materials.append(material)
world=bpy.context.scene.world or bpy.data.worlds.new('Studio')
bpy.context.scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.45,.50,.58,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
for name,location,power,size,colour in (
    ('Key',(-1.3,-1.3,2.4),220,1.8,(1,.88,.73)),
    ('Fill',(1.8,-.3,1.5),100,2.0,(.78,.86,1)),
    ('Rim',(.3,1.4,2),180,1.3,(1,.96,.88))):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=colour
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector((0,0,height*.45))-obj.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Preview camera');camera=bpy.data.objects.new('Preview camera',camera_data)
bpy.context.collection.objects.link(camera);bpy.context.scene.camera=camera;camera_data.lens=54
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
for name,position in (('view-a',(1.35,-1.75,1.15)),('view-b',(-1.35,1.75,1.15))):
    camera.location=position
    camera.rotation_euler=(Vector((0,0,height*.48))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print(json.dumps(report))
