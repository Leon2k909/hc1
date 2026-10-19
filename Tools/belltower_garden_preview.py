"""Studio renders of staged garden geometry, separate from native game QA.

Run after export-garden-studio.py with Blender --background --threads 2.
Only the three-dimensional model and its existing materials are rendered here.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Tools'))
import belltower_render as R
parser=argparse.ArgumentParser()
parser.add_argument('--views',nargs='+')
parser.add_argument('--revision',choices=('garden-v1','garden-v2','garden-v3'),default='garden-v3')
parser.add_argument('--directory',help='A staged studio folder directly under output/belltower/quality.')
parser.add_argument('--exposure',type=float,default=0.0,help='Studio camera exposure in stops; never changes game lighting.')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
quality=(ROOT/'output/belltower/quality').resolve()
FOLDER=(quality/(args.directory or f'{args.revision}-studio')).resolve()
if FOLDER.parent != quality:
    raise ValueError('The studio directory must be directly under the quality output folder')

def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def original_rgba_alpha(material,spec):
    """Opt-in preview of a custom shader that reads its original RGBA alpha."""
    nodes,links=material.node_tree.nodes,material.node_tree.links
    output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
    previous=output.inputs['Surface'].links[0].from_socket
    texture=nodes.new('ShaderNodeTexImage')
    texture.image=bpy.data.images.load(spec['source'],check_existing=True)
    threshold=nodes.new('ShaderNodeMath')
    threshold.operation='GREATER_THAN'
    threshold.inputs[1].default_value=spec['threshold']
    links.new(texture.outputs['Alpha'],threshold.inputs[0])
    transparent=nodes.new('ShaderNodeBsdfTransparent')
    mix=nodes.new('ShaderNodeMixShader')
    links.new(threshold.outputs[0],mix.inputs[0])
    links.new(transparent.outputs[0],mix.inputs[1])
    links.new(previous,mix.inputs[2])
    links.new(mix.outputs[0],output.inputs['Surface'])
    for node in nodes:
        if node.type=='BSDF_PRINCIPLED' and 'roughness' in spec:
            node.inputs['Roughness'].default_value=spec['roughness']

for record in json.loads((FOLDER/'models.json').read_text()):
    name=record['name']
    if args.views and name not in args.views:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    R.MATERIALS.clear()
    R.IMAGES.clear()
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.cycles.max_bounces=6
    scene.cycles.diffuse_bounces=3
    scene.cycles.glossy_bounces=2
    scene.render.threads_mode='FIXED'
    scene.render.threads=2
    scene.render.use_simplify=True
    scene.cycles.texture_limit_render='2048'
    scene.render.resolution_x=1200
    scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    scene.view_settings.exposure=args.exposure
    bpy.ops.wm.obj_import(filepath=str(FOLDER/(name+'.obj')),forward_axis='Y',up_axis='Z')
    props=[o for o in scene.objects if o.type=='MESH']
    alpha_patched=set()
    for obj in props:
        obj.matrix_world=Matrix.Scale(.0254,4)@R.OBJ_TO_MODEL
        for slot in obj.material_slots:
            paint=slot.material.name.rsplit('.',1)[0] if slot.material.name[-4:-3]=='.' else slot.material.name
            slot.material=R.material(record['materials'][paint])
            if paint in record.get('alpha_color_materials',{}) and paint not in alpha_patched:
                original_rgba_alpha(slot.material,record['alpha_color_materials'][paint])
                alpha_patched.add(paint)
    bpy.context.view_layer.update()
    bounds=[obj.matrix_world@Vector(p) for obj in props for p in obj.bound_box]
    lo=Vector(tuple(min(v[k] for v in bounds) for k in range(3)))
    hi=Vector(tuple(max(v[k] for v in bounds) for k in range(3)))
    if 'review_bounds' in record:
        lo,hi=(Vector(v)*.0254 for v in record['review_bounds'])
    centre=(lo+hi)/2
    extent=max(hi-lo)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(centre.x,centre.y,lo.z-.005))
    ground=bpy.data.materials.new('Neutral studio floor')
    ground.diffuse_color=(.15,.15,.135,1)
    bpy.context.object.data.materials.append(ground)
    world=bpy.data.worlds.new('Studio')
    world.use_nodes=True
    scene.world=world
    world.node_tree.nodes.get('Background').inputs[0].default_value=(.60,.67,.78,1)
    world.node_tree.nodes.get('Background').inputs[1].default_value=.35
    bpy.ops.object.light_add(type='AREA',location=centre+Vector((1.0,-1.1,1.6))*extent)
    key=bpy.context.object
    key.data.energy=450*extent*extent
    key.data.shape='DISK'
    key.data.size=extent*.85
    key.data.color=(1,.90,.77)
    aim(key,centre)
    bpy.ops.object.light_add(type='AREA',location=centre+Vector((-1,1,1))*extent)
    fill=bpy.context.object
    fill.data.energy=120*extent*extent
    fill.data.size=extent
    fill.data.color=(.76,.85,1)
    aim(fill,centre)
    offset=Vector((1.1,-1.3,.70)) if name=='shed-door' else Vector((1.1,1.3,.70))
    if name.startswith('firewood'): offset=Vector((1.25,.75,.7))
    if 'camera_offset' in record: offset=Vector(record['camera_offset'])
    bpy.ops.object.camera_add(location=centre+offset*extent)
    camera=bpy.context.object
    camera.data.lens=46
    aim(camera,centre)
    scene.camera=camera
    scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(FOLDER/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    (FOLDER/(name+'-render.json')).write_text(json.dumps({
        'kind':'offline Blender construction render; not a native game capture',
        'blender':bpy.app.version_string,'engine':'Cycles','device':'CPU','threads':2,
        'samples':scene.cycles.samples,'size':[scene.render.resolution_x,scene.render.resolution_y],
        'view_transform':scene.view_settings.view_transform,'exposure':scene.view_settings.exposure,
        'camera_position':list(camera.location),'camera_rotation':list(camera.rotation_euler),'lens':camera.data.lens,
        'review_bounds':[list(lo),list(hi)],
        'preview_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_sha256':hashlib.sha256((FOLDER/(name+'.obj')).read_bytes()).hexdigest(),
        'image_sha256':hashlib.sha256((FOLDER/(name+'.png')).read_bytes()).hexdigest()
    },indent=2)+'\n',encoding='utf-8')
    print('GARDEN_REVIEW '+name,flush=True)
