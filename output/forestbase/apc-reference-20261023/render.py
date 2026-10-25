"""Offline Blender preview of the actual OBJ/materials, without starting s&box."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
root=Path('C:/Users/mimi-/Documents/S&box Projects/hc1')
out=root/'output/forestbase/apc-reference-20261023';tex=out/'materials'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def point(p):return (-p[0]*.0254,p[2]*.0254,p[1]*.0254)
vertices=[];uvs=[];normals=[];faces=[];faceuv=[];facenorm=[];paints=[];group=None
for line in (out/'apc.obj').open():
    s=line.split()
    if not s:continue
    if s[0]=='v':vertices.append(point(tuple(map(float,s[1:]))))
    elif s[0]=='vt':uvs.append(tuple(map(float,s[1:3])))
    elif s[0]=='vn':normals.append(tuple(Vector(point(tuple(map(float,s[1:])))).normalized()))
    elif s[0]=='usemtl':group=s[1]
    elif s[0]=='f':
        refs=[tuple(map(int,v.split('/'))) for v in s[1:]]
        faces.append(tuple(v[0]-1 for v in refs));faceuv.extend(uvs[v[1]-1] for v in refs);facenorm.extend(normals[v[2]-1] for v in refs);paints.append(group)
mesh=bpy.data.meshes.new('Actual HC1 truck mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
obj=bpy.data.objects.new('FB041 reference APC',mesh);bpy.context.collection.objects.link(obj)
layer=mesh.uv_layers.new(name='UVMap')
for loop,uv in zip(layer.data,faceuv):loop.uv=uv
mesh.normals_split_custom_set(facenorm)
for poly in mesh.polygons:poly.use_smooth=True
spec={'armor':(.71,.05),'metal':(.62,.68),'rubber':(.85,0),'amber':(.48,.05),'red':(.5,.03),'vehicle_glass':(.12,0),'vehicle_canvas':(.86,0),'timber':(.78,0)}
materials={}
for paint in sorted(set(paints)):
    name=paint.removeprefix('apc_');m=bpy.data.materials.new(paint);m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links;p=nodes.get('Principled BSDF')
    if name in spec or name=='stencil':
        image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(tex/(name+'_color.png')));links.new(image.outputs['Color'],p.inputs['Base Color'])
        if name=='armor':
            tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(.60,.66,.53,1);links.new(image.outputs['Color'],tint.inputs[1]);links.new(tint.outputs[0],p.inputs['Base Color'])
        if name in spec:
            p.inputs['Roughness'].default_value=spec[name][0];p.inputs['Metallic'].default_value=spec[name][1]
            normal=nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(tex/(name+'_normal.png')));normal.image.colorspace_settings.name='Non-Color'
            converter=nodes.new('ShaderNodeNormalMap');converter.inputs['Strength'].default_value=.75;links.new(normal.outputs['Color'],converter.inputs['Color']);links.new(converter.outputs['Normal'],p.inputs['Normal'])
            rough=nodes.new('ShaderNodeTexImage');rough.image=bpy.data.images.load(str(tex/(name+'_rough.png')));rough.image.colorspace_settings.name='Non-Color';links.new(rough.outputs['Color'],p.inputs['Roughness'])
            if name=='vehicle_glass':p.inputs['Coat Weight'].default_value=.4;p.inputs['Coat Roughness'].default_value=.15
        else:
            alpha=nodes.new('ShaderNodeTexImage');alpha.image=bpy.data.images.load(str(tex/'stencil_alpha.png'));alpha.image.colorspace_settings.name='Non-Color';links.new(alpha.outputs['Color'],p.inputs['Alpha']);p.inputs['Roughness'].default_value=.8
    else:
        c={'amber':(1,.28,.025,1),'red':(.28,.008,.003,1),'lamp':(.9,.94,1,1)}[name]
        p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.6
        if name!='red':p.inputs['Emission Color'].default_value=c;p.inputs['Emission Strength'].default_value=.5 if name=='amber' else 1.2
    materials[paint]=len(obj.data.materials);obj.data.materials.append(m)
for poly,paint in zip(mesh.polygons,paints):poly.material_index=materials[paint]
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object
m=bpy.data.materials.new('Neutral preview floor');m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.10,.105,.09,1);p.inputs['Roughness'].default_value=.91
noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=16;noise.inputs['Detail'].default_value=3
bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.012;m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal']);floor.data.materials.append(m)
world=bpy.context.scene.world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.45,.51,.57,1);world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.45
def area(name,loc,energy,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1.8))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Large soft daylight',(3,5,9),2100,7);area('Front fill',(8,2,4),1100,5);area('Roof rim',(-4,-4,7),1800,5)
bpy.ops.object.camera_add(location=(-2.5,-15,5.7));cam=bpy.context.object;cam.rotation_euler=(Vector((-.1,0,1.75))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=62
s=bpy.context.scene;s.camera=cam;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=4
s.render.resolution_x=1800;s.render.resolution_y=1050;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';s.view_settings.exposure=-.35
s.render.image_settings.file_format='PNG';s.render.filepath=str(out/'apc-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'apc-preview.blend'));bpy.ops.render.render(write_still=True)
print('OFFLINE PREVIEW COMPLETE')
