"""Add portable texture nodes and sensible bodygroup visibility to editable sources."""
import bpy,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;A=HERE.parents[1]/'Assets'
materials=json.loads((HERE/'materials.json').read_text())['materials']
bpy.context.preferences.filepaths.save_version=0
for path in sorted((HERE/'models').glob('*.blend')):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    for material in bpy.data.materials:
        key=material.get('full_path',material.name).lower().replace('\\','/')
        if key not in materials:continue
        data=materials[key];material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
        output=nodes.new('ShaderNodeOutputMaterial');output.location=(600,0)
        shader=nodes.new('ShaderNodeBsdfPrincipled');shader.location=(300,0)
        links.new(shader.outputs['BSDF'],output.inputs['Surface'])
        if data.get('hidden'):shader.inputs['Alpha'].default_value=0;continue
        if data.get('optic_glass'):
            shader.inputs['Base Color'].default_value=(.08,.13,.15,1)
            shader.inputs['Alpha'].default_value=.06
            shader.inputs['Roughness'].default_value=.05
            continue
        for index,role in enumerate(('color','normal','roughness','opacity')):
            if not data.get(role):continue
            node=nodes.new('ShaderNodeTexImage');node.location=(-500,-index*260)
            im=bpy.data.images.load(str(A/data[role]),check_existing=True)
            im.filepath='//'+os.path.relpath(A/data[role],path.parent).replace('\\','/')
            if role!='color':im.colorspace_settings.name='Non-Color'
            node.image=im
            if role=='normal':
                normal=nodes.new('ShaderNodeNormalMap');normal.location=(-100,-260);links.new(node.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
            else:links.new(node.outputs['Color'],shader.inputs[{'color':'Base Color','roughness':'Roughness','opacity':'Alpha'}[role]])
    meta=json.loads(path.with_suffix('.json').read_text())
    for group in meta['bodygroups']:
        for i,choice in enumerate(group['choices']):
            obj=bpy.data.objects.get(choice['mesh'])
            if obj:obj.hide_render=(i!=0 or group['name']=='boolet');obj.hide_set(obj.hide_render)
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    bpy.data.orphans_purge(do_recursive=True)
    print('LINKED',path.stem,flush=True)
