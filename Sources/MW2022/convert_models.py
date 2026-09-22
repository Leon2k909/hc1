"""Batch-import the M4 attachment MDLs via SourceIO; run with Blender 5.1."""
import argparse
import hashlib
import json
import re
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--tools', type=Path, default=Path('D:/tmp/hc1-mw22-tools'))
parser.add_argument('--limit', type=int, default=0)
parser.add_argument('--only', default='')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
sys.path.insert(0, str(args.tools))
from SourceIO.blender_bindings.models import import_model
from SourceIO.blender_bindings.models.common import put_into_collections
from SourceIO.blender_bindings.operators.import_settings_base import ModelOptions
from SourceIO.library.models.mdl.v49.mdl_file import MdlV49
from SourceIO.library.shared.app_id import SteamAppId
from SourceIO.library.shared.content_manager import ContentManager
from SourceIO.library.shared.content_manager.providers.loose_files import LooseFilesContentProvider
from SourceIO.library.utils import FileBuffer
from SourceIO.library.utils.tiny_path import TinyPath

HEADER = '<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
inventory = json.loads((HERE/'inventory.json').read_text())
cm = ContentManager()
providers = [LooseFilesContentProvider(TinyPath(p['extracted']), SteamAppId(4000)) for p in inventory['packs']]
cm.children.update(providers)
cm.priority_list = providers
options = ModelOptions.default()
options.scale = 1.0
options.import_textures = False
options.import_animations = False
options.import_include_animations = False


def clean(value):
    return re.sub('[^a-z0-9_]', '_', value.lower()).strip('_')


def material_id(material):
    full = material.get('full_path', material.name).lower().replace('\\', '/')
    return 'm_' + hashlib.sha1(full.encode()).hexdigest()[:12], full


def export_obj(objects, path):
    lines = ['# Original Source units; Y,Z,X file axes counter ModelDoc OBJ conversion.', f'mtllib {path.stem}.mtl']
    unique, entries, faces, materials = {}, [], [], {}
    bounds = []
    degenerate = 0
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        uv_layer = mesh.uv_layers.active
        assert uv_layer is not None, f'Missing UVs: {obj.name}'
        matrix = obj.matrix_world
        normal_matrix = matrix.to_3x3().inverted().transposed()
        rows = []
        for tri in mesh.loop_triangles:
            mat, full = material_id(mesh.materials[tri.material_index])
            materials[mat] = full
            indices = []
            pts = []
            for loop_index in tri.loops:
                loop = mesh.loops[loop_index]
                p = matrix @ mesh.vertices[loop.vertex_index].co
                n = (normal_matrix @ mesh.corner_normals[loop_index].vector).normalized()
                uv = uv_layer.data[loop_index].uv
                key = tuple(round(x, 7) for x in (*p, *n, *uv))
                pts.append(p)
                if key not in unique:
                    unique[key] = len(entries)+1
                    entries.append((tuple(p), tuple(n), tuple(uv)))
                    bounds.append(p)
                indices.append(unique[key])
            if (pts[1]-pts[0]).cross(pts[2]-pts[0]).length < 1e-9:
                degenerate += 1
                continue
            rows.append((mat, indices))
        faces.append((obj.name, rows))
    for p,n,uv in entries:
        lines.append('v %.7f %.7f %.7f' % (p[1],p[2],p[0]))
        lines.append('vt %.7f %.7f' % uv)
        lines.append('vn %.7f %.7f %.7f' % (n[1],n[2],n[0]))
    for name, rows in faces:
        lines.append('o '+name)
        previous = None
        for mat, indices in rows:
            if mat != previous:
                lines.append('usemtl '+mat)
                previous = mat
            lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in indices))
    path.write_text('\n'.join(lines)+'\n')
    path.with_suffix('.mtl').write_text('\n'.join(f'newmtl {m}\nKd 1 1 1' for m in materials)+'\n')
    return dict(vertices=len(entries), triangles=sum(len(rows) for _,rows in faces),
                removed_degenerate=degenerate, materials=materials,
                bounds=[[min(v[i] for v in bounds) for i in range(3)], [max(v[i] for v in bounds) for i in range(3)]])


def convert(entry):
    key = entry['key']
    folder = ROOT/'Assets/attachments/mw2022/models'/key
    folder.mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    bpy.data.orphans_purge(do_recursive=True)
    path = TinyPath(entry['model_file'])
    with FileBuffer(path) as f:
        mdl = MdlV49.from_buffer(f)
    with FileBuffer(path) as f:
        container = import_model(path, f, cm, options)
    assert container and container.objects, f'No geometry in {path}'
    put_into_collections(container, key, bodygroup_grouping=True)
    group_info = []
    mesh_counter = 0
    for body in mdl.body_parts:
        objects = iter(container.bodygroups.get(body.name, []))
        choices = []
        for model in body.models:
            name = ''
            if model.vertex_count:
                obj = next(objects)
                name = f'mesh_{mesh_counter:02d}'
                obj['original_name'] = obj.name
                obj.name = name
                mesh_counter += 1
            choices.append(dict(source=model.name, mesh=name))
        group_info.append(dict(name=body.name, choices=choices))
    bpy.context.view_layer.update()
    report = export_obj(container.objects, folder/(key+'.obj'))
    rel = folder.relative_to(ROOT/'Assets').as_posix()
    meshes = ',\n'.join('{ _class = "RenderMeshFile" name = "'+o.name+'" filename = "'+rel+'/'+key+'.obj" '
        'import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" '
        'import_filter = { exclude_by_default = true exception_list = [ "'+o.name+'" ] } }' for o in container.objects)
    remaps = ', '.join('{ from = "'+mid+'.vmat" to = "attachments/mw2022/materials/'+full+'.vmat" }'
                       for mid, full in report['materials'].items())
    groups = ',\n'.join('{ _class = "BodyGroup" name = "'+clean(g['name'])+'" children = [ '+
        ', '.join('{ _class = "BodyGroupChoice" name = "'+(clean(c['source']) if c['mesh'] else '')+'" meshes = [ "'+c['mesh']+'" ] }'
                  for c in g['choices'])+' ] }' for g in group_info if len(g['choices']) > 1)
    vmdl = (HEADER+'{ rootNode = { _class = "RootNode" children = [\n'
        '{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ '+remaps+' ] use_global_default = false } ] },\n'
        '{ _class = "RenderMeshList" children = [ '+meshes+' ] },\n'
        + ('{ _class = "BodyGroupList" children = [ '+groups+' ] },\n' if groups else '') + '] } }\n')
    (folder/(key+'.vmdl')).write_text(vmdl)
    source_dir = HERE/'models'
    source_dir.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(source_dir/(key+'.blend')), compress=True)
    report.update(key=key, name=entry['name'], category=entry['category'], source=entry['model'],
                  vmdl=rel+'/'+key+'.vmdl', bodygroups=group_info,
                  bones=[dict(name=b.name, head=list(b.head_local), matrix=[list(row) for row in b.matrix_local])
                         for b in container.armature.data.bones] if container.armature else [])
    (source_dir/(key+'.json')).write_text(json.dumps(report, indent=2)+'\n')
    print(f'CONVERTED {key}: {report["triangles"]} triangles', flush=True)
    return report


seen, results, failures = set(), [], []
for entry in inventory['attachments']:
    if not entry['model_file'] or entry['model'] in seen:
        continue
    seen.add(entry['model'])
    if args.only and args.only not in entry['key']:
        continue
    try:
        results.append(convert(entry))
    except Exception as exc:
        traceback.print_exc()
        failures.append(dict(key=entry['key'], error=str(exc)))
    if args.limit and len(results)+len(failures) >= args.limit:
        break
(HERE/'conversion.json').write_text(json.dumps(dict(models=results, failures=failures), indent=2)+'\n')
print('CONVERSION_SUMMARY', len(results), 'models;', len(failures), 'failures', flush=True)
if failures:
    raise RuntimeError('Model conversion failures; see conversion.json')
