"""Stage the finished hall kiosks into existing station models, retaining collision.

Only the legacy booth faces are removed. Existing vertex/UV/normal records and
all physics blocks remain byte-identical; the finished booth mesh is appended.
"""
from pathlib import Path
import argparse
import json
import re
import railhead_map as R
import railhead_station as S

ROOT = Path(__file__).resolve().parents[1]
REMAP = re.compile(r'\{ from = "([^"]+)" to = "([^"]+)" \}')


def patch_obj(source, addition, side):
    original = source.splitlines(keepends=True)
    vertices = [tuple(map(float, line.split()[1:4])) for line in original if line.startswith('v ')]
    offsets = [sum(line.startswith(prefix) for line in original) for prefix in ('v ', 'vt ', 'vn ')]
    kept, removed, paint = [], [], None
    for line in original:
        if line.startswith('usemtl '):
            paint = line.split()[1]
        if line.startswith('f ') and paint in {'planks', 'planks_dark', 'copper', 'rw_window_dark'}:
            face = [vertices[int(value.split('/')[0])-1] for value in line.split()[1:]]
            # map_kit's OBJ axes are (-east, up, north).
            if all(1470-1e-4 <= z <= 1570+1e-4 and 250-1e-4 <= -x*side <= 350+1e-4 and -1e-4 <= y <= 114+1e-4 for x,y,z in face):
                removed.append(line)
                continue
        kept.append(line)
    if len(removed) != 44:
        raise RuntimeError(f'Expected 44 legacy booth triangles, found {len(removed)}')
    appended = []
    for line in addition.splitlines(keepends=True):
        if line.startswith(('mtllib ', '#')):
            continue
        if line.startswith('f '):
            values = []
            for value in line.split()[1:]:
                values.append('/'.join(str(int(index)+offsets[i]) if index else '' for i,index in enumerate(value.split('/'))))
            line = 'f ' + ' '.join(values) + '\n'
        appended.append(line)
    return ''.join(kept) + '\no hall_kiosk_finish\n' + ''.join(appended), len(removed)


def stage(destination):
    resource = 'models/maps/railhead'
    output = destination / resource
    output.mkdir(parents=True, exist_ok=True)
    scratch = destination.parent / 'hall-meshes'
    scratch.mkdir(parents=True, exist_ok=True)
    results = []
    for side, suffix in ((1,'east'),(-1,'west')):
        name = f'railhead_{suffix}'
        new = R.configure(S.hall_kiosk(side))
        R.K.write_model(scratch, resource, name, new)
        original_obj = (ROOT/'Assets'/resource/(name+'.obj')).read_text(encoding='utf-8')
        candidate, removed = patch_obj(original_obj, (scratch/(name+'.obj')).read_text(encoding='utf-8'), side)
        (output/(name+'.obj')).write_text(candidate, encoding='utf-8', newline='\n')
        original_mtl = (ROOT/'Assets'/resource/(name+'.mtl')).read_text(encoding='utf-8')
        blocks = (scratch/(name+'.mtl')).read_text(encoding='utf-8').split('newmtl ')[1:]
        known = set(re.findall(r'^newmtl (\S+)', original_mtl, re.M))
        additions = ''.join('\nnewmtl '+block for block in blocks if block.splitlines()[0].strip() not in known)
        (output/(name+'.mtl')).write_text(original_mtl+additions, encoding='utf-8', newline='\n')
        model_text = (ROOT/'Assets'/resource/(name+'.vmdl')).read_text(encoding='utf-8')
        remaps = list(REMAP.finditer(model_text))
        original_names = {m.group(1) for m in remaps}
        added = [m.group() for m in REMAP.finditer((scratch/(name+'.vmdl')).read_text(encoding='utf-8')) if m.group(1) not in original_names]
        insert = remaps[-1].end()
        model_text = model_text[:insert] + ''.join(',\n\t\t\t\t\t\t\t'+entry for entry in added) + model_text[insert:]
        model_text = model_text.replace('materials/buildings/render_cream.vmat', 'materials/railhead/finish/rw_lime.vmat')
        (output/(name+'.vmdl')).write_text(model_text, encoding='utf-8', newline='\n')
        results.append({'model':name,'removed_triangles':removed,'added_triangles':new.triangle_count(),'collision_preserved':True,'material_remaps_added':len(added)})
    # Apply the Railhead-specific plaster remap wherever the original cream
    # plaster was already used. Geometry and shared materials are untouched.
    for original in (ROOT/'Assets'/resource).glob('*.vmdl'):
        if original.stem in {'railhead_east','railhead_west'}:
            continue
        content = original.read_text(encoding='utf-8')
        replacement = content.replace('materials/buildings/render_cream.vmat', 'materials/railhead/finish/rw_lime.vmat')
        if replacement != content:
            (output/original.name).write_text(replacement, encoding='utf-8', newline='\n')
    (destination.parent/'hall-migration.json').write_text(json.dumps(results,indent=2), encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,default=ROOT/'output/railhead/quality/hall-stage')
    stage(parser.parse_args().stage)
