"""Bake model-specific PBR maps from the authored Blender parts and generated metal.

Run after build_parts.py. Bakes wear/cavity/roughness/normal detail into unique UVs;
the final models keep geometry-based highlights instead of flat colour swatches.
"""
import bpy, math, json, shutil, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Assets/attachments/m4a1'
SOURCE=ROOT/'Sources/M4A1'
SUPPRESSORS='--suppressors' in sys.argv
OPTICS='--optics' in sys.argv
input_blend=SOURCE/'m4a1_optics.blend' if OPTICS else ROOT/'Sources/Attachments/hc1_attachments.blend' if SUPPRESSORS else SOURCE/'m4a1_parts.blend'
bpy.ops.wm.open_mainfile(filepath=str(input_blend))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.cycles.use_denoising=False
scene.render.bake.margin=12
scene.render.bake.use_selected_to_active=False
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
grain=bpy.data.images.load(str(OUT/'textures/recon_anodized_color.png'),check_existing=True)

def node(tree,kind):return tree.nodes.new(kind)
def mathnode(tree,op,a,b=None):
    n=node(tree,'ShaderNodeMath');n.operation=op
    for i,value in enumerate([a,b]):
        if value is None:continue
        if isinstance(value,(int,float)):n.inputs[i].default_value=value
        else:tree.links.new(value,n.inputs[i])
    return n.outputs[0]

def finish_material(surface):
    mat=bpy.data.materials.new('bake_'+surface);mat.use_nodes=True
    t=mat.node_tree;t.nodes.clear()
    output=node(t,'ShaderNodeOutputMaterial');emission=node(t,'ShaderNodeEmission')
    t.links.new(emission.outputs[0],output.inputs['Surface'])
    geo=node(t,'ShaderNodeNewGeometry');coords=node(t,'ShaderNodeTexCoord')
    scale=node(t,'ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=1/6
    t.links.new(coords.outputs['Object'],scale.inputs[0])
    tex=node(t,'ShaderNodeTexImage');tex.image=grain;tex.projection='BOX';tex.projection_blend=.2
    t.links.new(scale.outputs[0],tex.inputs[0])
    noise=node(t,'ShaderNodeTexNoise');noise.inputs['Scale'].default_value=22;noise.inputs['Detail'].default_value=3
    t.links.new(coords.outputs['Object'],noise.inputs[0])
    wear=node(t,'ShaderNodeValToRGB');wear.color_ramp.elements[0].position=.505;wear.color_ramp.elements[1].position=.535
    t.links.new(geo.outputs['Pointiness'],wear.inputs[0])
    edge=mathnode(t,'MULTIPLY',wear.outputs[0],mathnode(t,'MULTIPLY',noise.outputs['Fac'],.8))
    mix=node(t,'ShaderNodeMixRGB');mix.blend_type='MIX'
    t.links.new(edge,mix.inputs[0]);t.links.new(tex.outputs['Color'],mix.inputs[1])
    polymer=surface in ('stock','polymer');rubber=surface in ('recess','rubber');metal=surface in ('guard','steel','anodized','ceramic')
    mix.inputs[2].default_value=(.14,.145,.15,1) if metal else (.065,.066,.069,1)
    if rubber:
        mix.inputs[0].default_value=0
        for link in list(mix.inputs[0].links):t.links.remove(link)
        for link in list(mix.inputs[1].links):t.links.remove(link)
        mix.inputs[1].default_value=(.005,.006,.007,1)
    rough=mathnode(t,'ADD',.37 if metal else (.84 if rubber else .54),mathnode(t,'MULTIPLY',noise.outputs['Fac'],.19))
    rough=mathnode(t,'SUBTRACT',rough,mathnode(t,'MULTIPLY',edge,.22))
    bump=node(t,'ShaderNodeBump');bump.inputs['Strength'].default_value=.12 if polymer else .045;bump.inputs['Distance'].default_value=.012
    fine=node(t,'ShaderNodeTexNoise');fine.inputs['Scale'].default_value=320
    t.links.new(coords.outputs['Object'],fine.inputs[0]);t.links.new(fine.outputs['Fac'],bump.inputs['Height'])
    bevel=node(t,'ShaderNodeBevel');bevel.inputs['Radius'].default_value=.014;bevel.samples=4
    t.links.new(bump.outputs['Normal'],bevel.inputs['Normal'])
    shader=node(t,'ShaderNodeBsdfPrincipled');t.links.new(mix.outputs[0],shader.inputs['Base Color']);t.links.new(rough,shader.inputs['Roughness'])
    shader.inputs['Metallic'].default_value=.8 if metal else 0
    t.links.new(bevel.outputs['Normal'],shader.inputs['Normal'])
    return mat,{'color':mix.outputs[0],'roughness':rough,'metalness':.8 if metal else 0},emission,output,shader

stats={}
for name in (['tube_red_dot'] if OPTICS else ['compact_suppressor','rifle_suppressor'] if SUPPRESSORS else ['precision_stock','heavy_barrel']):
    collection=bpy.data.collections[name]
    members=list(collection.objects)
    for member in members:
        for slot in member.material_slots:
            if slot.material is None:slot.material=bpy.data.materials['hc1_'+member.get('surface','guard')]
    # Exclude the other part from both AO and ray baking.
    for obj in scene.objects:obj.hide_render=obj not in members
    bpy.ops.object.select_all(action='DESELECT')
    for obj in members:obj.select_set(True)
    bpy.context.view_layer.objects.active=members[0]
    bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.25,island_margin=.008,area_weight=1,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    baked=[]
    for slot in obj.material_slots:
        surface=slot.material.name.removeprefix('hc1_').split('.')[0] if slot.material else 'guard'
        mat,channels,emission,output,shader=finish_material(surface)
        slot.material=mat;baked.append((mat,channels,emission,output,shader))
    folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
    for channel in ['color','roughness','metalness','normal','ao']:
        resolution=1024 if channel=='ao' else 2048
        scene.cycles.samples=8 if channel=='ao' else 16
        target=bpy.data.images.new(name+'_'+channel,width=resolution,height=resolution,alpha=False)
        target.colorspace_settings.name='sRGB' if channel=='color' else 'Non-Color'
        target.generated_color=(.5,.5,1,1) if channel=='normal' else (0,0,0,1)
        for mat,channels,emission,output,shader in baked:
            t=mat.node_tree
            for n in t.nodes:n.select=False
            image_node=node(t,'ShaderNodeTexImage');image_node.image=target;image_node.select=True;t.nodes.active=image_node
            for link in list(output.inputs['Surface'].links):t.links.remove(link)
            t.links.new(shader.outputs[0] if channel in ('normal','ao') else emission.outputs[0],output.inputs['Surface'])
            if channel in channels:
                for link in list(emission.inputs['Color'].links):t.links.remove(link)
                value=channels[channel]
                if isinstance(value,(int,float)):emission.inputs['Color'].default_value=(value,value,value,1)
                else:t.links.new(value,emission.inputs['Color'])
        if channel=='normal':
            scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_g='NEG_Y'
        bpy.ops.object.bake(type={'normal':'NORMAL','ao':'AO'}.get(channel,'EMIT'))
        target.filepath_raw=str(folder/f'{name}_{channel}.png');target.file_format='PNG';target.save()
        print('BAKED',name,channel,flush=True)
    mesh=obj.data;mesh.calc_loop_triangles();uvs=mesh.uv_layers.active.data;normals=mesh.corner_normals
    lines=[f'mtllib {name}.mtl',f'o {name}',f'usemtl {name}_pbr'];index=1
    for tri in mesh.loop_triangles:
        for li in tri.loops:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;n=normals[li].vector;uv=uvs[li].uv
            lines.extend([f'v {v.y:.7f} {v.z:.7f} {v.x:.7f}',f'vt {uv.x:.7f} {uv.y:.7f}',f'vn {n.y:.7f} {n.z:.7f} {n.x:.7f}'])
        lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(index,index+3)));index+=3
    (folder/f'{name}.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
    (folder/f'{name}.mtl').write_text(f'newmtl {name}_pbr\nKd 1 1 1\n',encoding='utf8')
    (folder/f'{name}.vmat').write_text('"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n F_METALNESS_TEXTURE "1"\n g_flRoughnessScaleFactor "1"\n g_vColorTint "[1 1 1 1]"\n'+''.join(f' Texture{key} "attachments/m4a1/{name}/{name}_{value}.png"\n' for key,value in [('Color','color'),('Normal','normal'),('Roughness','roughness'),('Metalness','metalness'),('AmbientOcclusion','ao')])+'}\n',encoding='utf8')
    vmdl=folder/f'{name}.vmdl'
    import re
    if OPTICS:
        data=(OUT/'heavy_barrel/heavy_barrel.vmdl').read_text(encoding='utf8').replace('heavy_barrel','tube_red_dot')
        vmdl.write_text(data,encoding='utf8')
    if SUPPRESSORS:
        data=(ROOT/f'Assets/attachments/hc1/{name}/{name}.vmdl').read_text(encoding='utf8')
        vmdl.write_text(data.replace(f'attachments/hc1/{name}/',f'attachments/m4a1/{name}/'),encoding='utf8')
    data=vmdl.read_text(encoding='utf8')
    data=re.sub(r'remaps = \[.*?\] use_global_default',f'remaps = [ {{ from = "{name}_pbr.vmat" to = "attachments/m4a1/{name}/{name}.vmat" }} ] use_global_default',data,flags=re.S)
    vmdl.write_text(data,encoding='utf8')
    if OPTICS:
        data=data.replace('use_global_default', '{ from = "optic_reticle.vmat" to = "attachments/m4a1/optics/tube_reticle.vmat" } ] use_global_default',1).replace('} ] { from','}, { from')
        # Append a second source mesh to the existing RenderMeshList.
        marker='{ _class = "RenderMeshList" children = ['
        data=data.replace(marker,marker+' { _class = "RenderMeshFile" filename = "attachments/m4a1/tube_red_dot/tube_lens.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" },')
        vmdl.write_text(data,encoding='utf8')
    stats[name]={'triangles':len(mesh.loop_triangles),'texture_resolution':{k:1024 if k=='ao' else 2048 for k in ['color','normal','roughness','metalness','ao']}}
    obj.select_set(False)
stem='m4a1_optics_pbr' if OPTICS else 'm4a1_suppressors_pbr' if SUPPRESSORS else 'm4a1_parts_pbr'
staging=SOURCE/f'{stem}_build.blend';bpy.ops.wm.save_as_mainfile(filepath=str(staging))
shutil.copyfile(staging,SOURCE/f'{stem}.blend');staging.unlink()
(SOURCE/('optic-pbr-report.json' if OPTICS else 'suppressor-pbr-report.json' if SUPPRESSORS else 'pbr-report.json')).write_text(json.dumps(stats,indent=2)+'\n',encoding='utf8')
