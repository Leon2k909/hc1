"""Offline inspection of actual exported assets; not an S&box render or performance test."""
import bpy, re, math, json, sys, bmesh
from pathlib import Path
from mathutils import Vector,Quaternion

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/forestbase'
cliff_mode='--cliffs' in sys.argv
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def material(name,path):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    text=path.read_text()
    def scalar(key,default):
        match=re.search(r'\b'+key+r'\s+"([\d.]+)"',text)
        return float(match[1]) if match else default
    bsdf.inputs['Metallic'].default_value=scalar('g_flCoatingMetalness',scalar('g_flMetalness',0))
    bsdf.inputs['Roughness'].default_value=.65
    def image(channel):
        match=re.search(r'\bTexture'+channel+r'\s+"([^"\[ ]+)"',text)
        if not match:return None
        file=ROOT/'Assets'/match[1]
        if not file.exists():return None
        node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(file),check_existing=True)
        if channel!='Color':node.image.colorspace_settings.name='Non-Color'
        return node
    color=image('Color')
    if color:
        socket=color.outputs['Color'];desat=scalar('CoatingDesaturation',0)
        if desat:
            gray=nodes.new('ShaderNodeRGBToBW');links.new(socket,gray.inputs[0])
            mix=nodes.new('ShaderNodeMixRGB');mix.inputs[0].default_value=desat
            links.new(socket,mix.inputs[1]);links.new(gray.outputs[0],mix.inputs[2]);socket=mix.outputs[0]
        tint=re.search(r'\bCoatingTint\s+"\[([^]]+)\]"',text)
        if tint:
            multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
            multiply.inputs[2].default_value=(*map(float,tint[1].split()),1)
            links.new(socket,multiply.inputs[1]);socket=multiply.outputs[0]
        links.new(socket,bsdf.inputs['Base Color'])
    normal=image('Normal')
    if normal:
        bump=nodes.new('ShaderNodeNormalMap');links.new(normal.outputs['Color'],bump.inputs['Color'])
        links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    rough=image('Roughness')
    if rough:links.new(rough.outputs['Color'],bsdf.inputs['Roughness'])
    alpha=image('Translucency')
    if alpha:
        clip=nodes.new('ShaderNodeMath');clip.operation='GREATER_THAN';clip.inputs[1].default_value=.35
        links.new(alpha.outputs['Color'],clip.inputs[0]);links.new(clip.outputs[0],bsdf.inputs['Alpha'])
    return mat

folder=ROOT/'Assets/models/maps/forestbase'
bpy.ops.wm.obj_import(filepath=str(folder/('vista.obj' if cliff_mode else 'logistics.obj')),forward_axis='Z',up_axis='Y')
obj=bpy.context.selected_objects[0];obj.scale=(.0254,)*3;obj.rotation_euler.z=math.pi/2
remaps=dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"',(folder/('vista.vmdl' if cliff_mode else 'logistics.vmdl')).read_text()))
if cliff_mode:
    keep={i for i,slot in enumerate(obj.material_slots) if slot.material and slot.material.name=='cascade_rock'}
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    bmesh.ops.delete(mesh,geom=[face for face in mesh.faces if face.material_index not in keep],context='FACES')
    mesh.to_mesh(obj.data);mesh.free()
for slot in obj.material_slots:
    if slot.material:
        name=slot.material.name
        if name in remaps:slot.material=material(name,ROOT/'Assets'/remaps[name])
if cliff_mode:
    data=json.loads((ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    source=None
    for root in data['GameObjects']:
        if root.get('Name')!='Forest Backdrop':continue
        for item in root['Children']:
            if not item['Name'].startswith(('Cascade cliff','Distant mountain')):continue
            if source is None:
                bpy.ops.wm.obj_import(filepath=str(folder/'mountainside/cliff_lod0.obj'),forward_axis='Z',up_axis='Y')
                source=bpy.context.selected_objects[0]
                scan_basis=Quaternion((0,0,1),math.pi/2)@source.rotation_euler.to_quaternion()
                scan_mat=material('Mountainside scan',folder/'mountainside/cliff.vmat')
                source.data.materials.clear();source.data.materials.append(scan_mat)
                source.hide_render=True
            scan=source.copy();scan.hide_render=False;bpy.context.collection.objects.link(scan)
            scan.location=Vector(tuple(map(float,item['Position'].split(','))))*.0254
            scan.scale=Vector(tuple(map(float,item['Scale'].split(','))))*.0254
            q=tuple(map(float,item['Rotation'].split(',')))
            scan.rotation_mode='QUATERNION';scan.rotation_quaternion=Quaternion((q[3],q[0],q[1],q[2]))@scan_basis
bpy.ops.mesh.primitive_plane_add(size=150,location=(0,0,-.03))
floor=bpy.context.object;floor.data.materials.append(material('Preview ground',ROOT/'Assets/materials/forestbase/scans/asphalt_02.vmat'))
world=bpy.context.scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.20,.26,.36,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
def plan(e,n,z):return Vector((n,-e,z))*.0254
def area(name,e,n,z,energy,color,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.color=color;data.shape='DISK';data.size=size
    light=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(light);light.location=plan(e,n,z)
    light.rotation_euler=(plan(0,160,60)-light.location).to_track_quat('-Z','Y').to_euler()
area('Offline cool daylight',-800,-400,900,4200,(.72,.82,1),12)
if not cliff_mode:area('Offline warm shelter light',-30,100,115,150,(1,.67,.38),1.8)
else:
    sun_data=bpy.data.lights.new('Offline escarpment sunlight','SUN');sun_data.energy=2
    sun=bpy.data.objects.new('Offline escarpment sunlight',sun_data);bpy.context.collection.objects.link(sun)
    sun.rotation_euler=(math.radians(26),math.radians(-30),math.radians(-20))
camera_data=bpy.data.cameras.new('Asset camera');camera=bpy.data.objects.new('Asset camera',camera_data)
bpy.context.collection.objects.link(camera);bpy.context.scene.camera=camera;camera_data.lens=30
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
views=[('cliff-debug-all',(-2600,-2900,2000),(0,200,90)),('cliff-debug-scans',(-2600,-2900,2000),(0,200,90)),('cliff-debug-infill',(-2600,-2900,2000),(0,200,90))] if cliff_mode else [('net-asset-preview',(-700,-480,285),(-25,160,90)),('net-detail-preview',(420,-190,105),(-55,190,120))]
for name,eye,target in views:
    if cliff_mode:
        obj.hide_render=name=='cliff-debug-scans'
        for scan_obj in bpy.context.scene.objects:
            if scan_obj.type=='MESH' and scan_obj.data.name==source.data.name and scan_obj!=source:scan_obj.hide_render=name=='cliff-debug-infill'
    camera.location=plan(*eye);camera.rotation_euler=(plan(*target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
(OUT/('cliff-debug.json' if cliff_mode else 'asset-preview.json')).write_text(json.dumps({'renderer':'Blender Cycles CPU','scope':'Actual exported OBJ, material textures and coating parameters; approximate independent lighting. Does not verify S&box appearance.','views':[name+'.png' for name,eye,target in views]},indent=2)+'\n')
