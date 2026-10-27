"""Full saved Forest Base geometry inspection, without opening S&box.

Uses the saved scene's actual models/transforms and practical-light locations.
Blender lighting energies and shader approximations are independent of the
engine; fog, native exposure, water animation and spray are not validated.
"""
import argparse
import ast
import bpy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from mathutils import Matrix,Quaternion,Vector

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'Assets';OUT=ROOT/'output/forestbase'
sys.path.insert(0,str(ROOT/'Tools'))
parser=argparse.ArgumentParser()
parser.add_argument('--scene',default=str(ASSETS/'scenes/maps/ForestBase/forestbase.scene'))
parser.add_argument('--name',default='overview-current')
parser.add_argument('--asset-overlay',type=Path)
parser.add_argument('--samples',type=int,default=24)
parser.add_argument('--view',choices=('compound','yard','workshop','east-rim'),default='compound')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

# Reuse only the existing authoring utility's asset-loading definitions. AST
# selection excludes its argument parser, scene construction and render calls.
base=ROOT/'Tools/forestbase_forest_preview.py'
functions=[n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('material','mesh')]
ns=dict(ROOT=ROOT,ASSETS=ASSETS,OUT=OUT,STAGE=OUT/'unused-current-assets',
        args=SimpleNamespace(lod='lod1'),bpy=bpy,math=math,re=re,hashlib=hashlib,
        CACHE={},loaded=[],source_hashes={})
ns['asset']=lambda path:args.asset_overlay/path if args.asset_overlay and (args.asset_overlay/path).exists() else ASSETS/path
exec(compile(ast.Module(body=functions,type_ignores=[]),str(base),'exec'),ns)
base_material=ns['material']


def scalar(text,key,default):
    m=re.search(r'\b'+key+r'\s+"([-\d.]+)"',text)
    return float(m[1]) if m else default


def vector(text,key):
    m=re.search(r'\b'+key+r'\s+"\[([^]]+)\]"',text)
    return tuple(map(float,m[1].split())) if m else None


def material(name,path):
    mat=base_material(name,path)
    if mat.get('full_overview_processed'):return mat
    mat['full_overview_processed']=True
    text=path.read_text() if path and path.exists() else ''
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bsdf=next(n for n in nodes if n.bl_idname=='ShaderNodeBsdfPrincipled')
    def constant_texture(key,socket):
        v=vector(text,'Texture'+key)
        if v and not bsdf.inputs[socket].is_linked:bsdf.inputs[socket].default_value=v[0]
    constant_texture('Roughness','Roughness');constant_texture('Metalness','Metallic')
    bsdf.inputs['Metallic'].default_value=scalar(text,'g_flCoatingMetalness',bsdf.inputs['Metallic'].default_value)
    source=bsdf.inputs['Base Color'].links[0].from_socket if bsdf.inputs['Base Color'].is_linked else None
    if source:
        desat=scalar(text,'CoatingDesaturation',0)
        if desat:
            gray=nodes.new('ShaderNodeRGBToBW');links.new(source,gray.inputs[0])
            mix=nodes.new('ShaderNodeMixRGB');mix.inputs[0].default_value=desat
            links.new(source,mix.inputs[1]);links.new(gray.outputs[0],mix.inputs[2]);source=mix.outputs[0]
        for key in ('g_flTintColor','CoatingTint'):
            tint=vector(text,key)
            if tint:
                mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
                mix.inputs[2].default_value=(*tint[:3],1);links.new(source,mix.inputs[1]);source=mix.outputs[0]
        links.new(source,bsdf.inputs['Base Color'])
    if 'forestbase_lamp.shader' in text:
        bsdf.inputs['Base Color'].default_value=(.85,.65,.38,1)
        bsdf.inputs['Emission Color'].default_value=(1,.61,.32,1)
        bsdf.inputs['Emission Strength'].default_value=3
    elif 'F_SELF_ILLUM "1"' in text and source:
        links.new(source,bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value=min(3,scalar(text,'g_flSelfIllumBrightness',1))
    if name.startswith(('waterfall_spray','waterfall_impact','waterfall_plunge')):
        bsdf.inputs['Alpha'].default_value=0
    elif name.startswith('waterfall_'):
        import forestbase_waterfall_preview
        forestbase_waterfall_preview.apply(mat,text,ASSETS)
    elif name in ('plunge_basin','river','water'):
        if bsdf.inputs['Base Color'].is_linked:links.remove(bsdf.inputs['Base Color'].links[0])
        bsdf.inputs['Base Color'].default_value=(.02,.055,.06,1)
        bsdf.inputs['Roughness'].default_value=.12;bsdf.inputs['Alpha'].default_value=.8
    return mat


ns['material']=material
mesh=ns['mesh'];records=[];lights=[]
scene_bytes=Path(args.scene).read_bytes();document=json.loads(scene_bytes)


def visit(nodes):
    for node in nodes:
        position=Vector(tuple(map(float,node.get('Position','0,0,0').split(','))))
        qx,qy,qz,qw=map(float,node.get('Rotation','0,0,0,1').split(','));q=Quaternion((qw,qx,qy,qz))
        for renderer in node.get('Components',[]):
            kind=renderer.get('__type','')
            if kind=='Sandbox.ModelRenderer':
                model=renderer['Model'];data,basis=mesh(model)
                obj=bpy.data.objects.new(node.get('Name','unnamed'),data);bpy.context.collection.objects.link(obj)
                scale=tuple(float(v)*.0254 for v in node.get('Scale','1,1,1').split(','))
                obj.matrix_world=Matrix.Translation(position*.0254)@q.to_matrix().to_4x4()@Matrix.Diagonal((*scale,1))@basis
                obj.color=tuple(map(float,renderer.get('Tint','1,1,1,1').split(',')))
                if '/floor/grass_' in model or model.endswith('shore_grass.vmdl'):obj.visible_shadow=False
                records.append(dict(name=obj.name,model=model))
            elif kind in ('Sandbox.SpotLight','Sandbox.PointLight','Sandbox.DirectionalLight'):
                color=tuple(map(float,renderer['LightColor'].split(',')))[:3];peak=max(color)
                type_='SUN' if kind.endswith('DirectionalLight') else 'SPOT' if kind.endswith('SpotLight') else 'POINT'
                data=bpy.data.lights.new(node.get('Name',kind),type_);data.color=tuple(c/peak for c in color)
                # Energy conversion is independent of native engine units.
                data.energy=peak*(3 if type_=='SUN' else 65)
                if type_=='SUN':data.angle=math.radians(5)
                else:
                    data.shadow_soft_size=.06;data.use_custom_distance=True
                    data.cutoff_distance=renderer.get('Radius',800)*.0254
                if type_=='SPOT':
                    outer=renderer.get('ConeOuter',70);inner=renderer.get('ConeInner',40)
                    data.spot_size=math.radians(min(170,outer*2));data.spot_blend=max(.05,1-inner/max(outer,1))
                obj=bpy.data.objects.new(data.name,data);bpy.context.collection.objects.link(obj)
                obj.location=position*.0254;direction=q@Vector((1,0,0))
                obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
                lights.append(dict(name=node.get('Name'),kind=kind,nativeColor=color,blenderEnergy=data.energy))
        visit(node.get('Children',[]))
visit(document['GameObjects'])

world=bpy.context.scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.065,.085,.12,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=2
def plan(e,n,z):return Vector((n,-e,z))*.0254
views={'compound':((-3300,-4000,2800),(0,300,150),42),
       'east-rim':((1400,-600,64),(5000,1100,450),32),
       'yard':((-1420,-1280,64),(-700,650,155),25),
       'workshop':((550,-800,90),(1120,520,110),30)}
eye,target,lens=views[args.view]
data=bpy.data.cameras.new('Independent whole-map inspection');camera=bpy.data.objects.new(data.name,data)
bpy.context.collection.objects.link(camera);bpy.context.scene.camera=camera
camera.location=plan(*eye);camera.rotation_euler=(plan(*target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=lens
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=max(1,args.samples);scene.cycles.use_denoising=False;scene.cycles.transparent_max_bounces=32
scene.render.use_simplify=True;scene.cycles.texture_limit_render='1024'
scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
file=f'{args.name}-{args.view}.png';scene.render.filepath=str(OUT/file)
bpy.ops.render.render(write_still=True)
(OUT/f'{args.name}-{args.view}.json').write_text(json.dumps(dict(
    scope='Saved explicit model-renderer nodes and practical-light placements, forced LOD1, independent Blender energy/shading/tone approximations. No prefab expansion, live characters, native fog/exposure/animation/performance validation.',
    renderer='Blender Cycles CPU',samples=scene.cycles.samples,view=file,
    scenePath=str(Path(args.scene).relative_to(ROOT)),sceneSha256=hashlib.sha256(scene_bytes).hexdigest(),
    camera=dict(planEye=eye,planTarget=target,lens=lens),practicalLightEnergyScale=65,worldStrength=2,instances=records,lights=lights,
    sourceHashes=ns['source_hashes']),indent=2)+'\n')
