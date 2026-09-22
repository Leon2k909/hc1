"""Independent Blender fit check using the original HC1 receiver geometry."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;A=HERE.parents[1]/'Assets'
bpy.ops.wm.open_mainfile(filepath=str(HERE/'v_m4a1.2e216481e1b73b07.blend'))
for o in list(bpy.data.objects):
    if o.type!='MESH' or o.name not in ('m4a1_v_m4a1_a','m4a1_v_m4a1_b'):bpy.data.objects.remove(o,do_unlink=True)
for o in bpy.data.objects:
    o.parent=None
    o.modifiers.clear()
    if o.name=='m4a1_v_m4a1_b':
        import bmesh
        bm=bmesh.new();bm.from_mesh(o.data)
        kill=[]
        for f in bm.faces:
            c=f.calc_center_median()
            if c.x>3.5 or c.x<-4.03 or (c.x<-1.6 and c.z<5.65):kill.append(f)
        bmesh.ops.delete(bm,geom=kill,context='FACES');bm.to_mesh(o.data);bm.free()
    for material in o.data.materials:
        material.use_nodes=True
        node=material.node_tree.nodes.get('Principled BSDF')
        if node:node.inputs['Base Color'].default_value=(.07,.08,.085,1);node.inputs['Metallic'].default_value=.5;node.inputs['Roughness'].default_value=.35
keys=['att_vm_p01_ar_mike4_barhvy_v0','att_vm_p01_ar_mike4_stockl_v0','att_vm_p01_ar_mike4_grpskel_v0','att_vm_p01_ar_mike4_xmag_v0','att_vm_silencer02','att_vm_minireddot01_tall','att_vm_p01_ar_mike4_stubbygrip01','att_vm_p01_ar_mike4_laser01']
barrel=json.loads((A/'gunsmith/m4a1/mw2022'/f'{keys[0]}.prefab').read_text())['RootObject']['Components'][1]
for key in keys:
    meta=json.loads((HERE/'models'/f'{key}.json').read_text())
    prefab=json.loads((A/'gunsmith/m4a1/mw2022'/f'{key}.prefab').read_text())
    mount=prefab['RootObject']['Components'][1]
    choices={g['choices'][0]['mesh']for g in meta['bodygroups']if g['name']not in ('boolet','tag_tip','sight')}
    with bpy.data.libraries.load(str(HERE/'models'/f'{key}.blend'),link=False)as(src,dst):dst.objects=[n for n in src.objects if n in choices]
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj);obj.parent=None;obj.modifiers.clear();obj.hide_set(False);obj.hide_render=False
        pos=mount['BindPosition']
        if meta['category']=='Muzzle':pos=barrel['BarrelMuzzle']
        if meta['category']=='Underbarrel':pos=barrel['BarrelGrip']
        if meta['category']=='Laser':pos=barrel['BarrelLaser'];obj.rotation_euler.x=math.pi/2
        obj.location=Vector(tuple(map(float,pos.split(','))))
        obj.scale=tuple(map(float,mount['PartScale'].split(',')))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1600;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.world.color=(.14,.14,.14)
camera_data=bpy.data.cameras.new('Fit camera');camera=bpy.data.objects.new('Fit camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
center=Vector((5,0,5.7));camera.location=center+Vector((6,-72,14));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=39
for pos,power,size in [((1,-18,32),20000,25),((8,15,18),15000,20)]:
    data=bpy.data.lights.new('Studio','AREA');data.energy=power;data.shape='DISK';data.size=size;obj=bpy.data.objects.new('Studio',data);scene.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.view_transform='AgX'
(HERE/'qa').mkdir(exist_ok=True);scene.render.filepath=str(HERE/'qa/blender-fit.png');bpy.ops.render.render(write_still=True)
