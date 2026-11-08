"""Extract the garden pavilion as a local-origin prop and remove it from dressing."""
from pathlib import Path
import re

assets = Path(__file__).resolve().parents[1] / 'Assets'
base = 'models/maps/veridant/'
clean = base + 'garden-without-pavilion'
archive = 'models/props/shared/veridant_garden_pavilion'
for folder in (clean, archive):
    (assets/folder).mkdir(parents=True, exist_ok=True)
original = (assets/base/'terrace-paved-garden/dressing.vmdl').read_text()

def inside(x, y, z):
    return -1190.1 <= x <= -929.9 and -330.1 <= y <= -109.9 and -.1 <= z <= 152.1

def read_obj(path):
    lines = (assets/path).read_text().splitlines()
    vertices = [tuple(map(float, line.split()[1:4])) for line in lines if line.startswith('v ')]
    return lines, vertices

def save_local(source, name, lines):
    """Copy only referenced attributes, with positions relative to the pavilion centre."""
    records = {key: [line.split()[1:] for line in lines if line.startswith(key+' ')]
               for key in ('v','vt','vn')}
    indices = {key: {} for key in records}
    output = ['o '+name]
    for line in lines:
        if line.startswith('usemtl '):
            output.append(line)
        if not line.startswith('f '):
            continue
        face = []
        for token in line.split()[1:]:
            remapped = []
            for key, field in zip(records, token.split('/')):
                if not field:
                    remapped.append('')
                    continue
                index = int(field)-1
                lookup = indices[key]
                if index not in lookup:
                    values = records[key][index].copy()
                    if key == 'v':
                        values[0] = str(float(values[0])+220)
                        values[2] = str(float(values[2])+1060)
                    lookup[index] = len(lookup)+1
                    output.append(key+' '+' '.join(values))
                remapped.append(str(lookup[index]))
            face.append('/'.join(remapped))
        output.append('f '+' '.join(face))
    if source_mtl := next((line.split(maxsplit=1)[1] for line in lines if line.startswith('mtllib ')), None):
        source_file = (assets/source).with_name(source_mtl)
        if source_file.exists():
            (assets/archive/(name+'.mtl')).write_bytes(source_file.read_bytes())
            output.insert(0,'mtllib '+name+'.mtl')
    path = f'{archive}/{name}.obj'
    attributes = ('v ', 'vt ', 'vn ')
    ordered = [line for line in output if line.startswith('mtllib ')]
    ordered += [line for prefix in attributes for line in output if line.startswith(prefix)]
    ordered += [line for line in output if not line.startswith((*attributes, 'mtllib '))]
    (assets/path).write_text('\n'.join(ordered)+'\n')
    return path

render_pattern = re.compile(r'(?m)^[ \t]*\{\n[ \t]*_class = "RenderMeshFile"[\s\S]*?^[ \t]*\},?\n')
physics_pattern = re.compile(r'(?m)^([ \t]*)\{\n[ \t]*_class = "PhysicsShape(?:Box|HullFile)"[\s\S]*?^\1\},?\n')
archived_render, archived_physics = [], []
counts = []

def split_render(match):
    block = match[0]
    path = re.search(r'filename = "([^"]+)"', block)[1]
    lines, vertices = read_obj(path)
    kept, selected = [], []
    count = 0
    for line in lines:
        if line.startswith('f ') and all(inside(x,y,z) for y,z,x in
                (vertices[int(token.split('/')[0])-1] for token in line.split()[1:])):
            selected.append(line)
            count += 1
            continue
        kept.append(line)
        if not line.startswith('f '):
            selected.append(line)
    if not count:
        return block
    counts.append(count)
    name = f'part_{len(counts)}'
    new_path = f'{clean}/{name}.obj'
    for i,line in enumerate(kept[:10]):
        if line.startswith('mtllib '):
            mtl = (assets/path).with_name(line.split(maxsplit=1)[1])
            if mtl.exists():
                (assets/clean/(name+'.mtl')).write_bytes(mtl.read_bytes())
                kept[i] = 'mtllib '+name+'.mtl'
    (assets/new_path).write_text('\n'.join(kept)+'\n')
    archived_render.append(block.replace(path, save_local(path,name,selected)).rstrip().rstrip(',')+',\n')
    return block.replace(path,new_path)

def split_physics(match):
    block = match[0]
    origin = re.search(r'origin = \[ ([^]]+)\]', block)
    if not origin:
        return block
    x,y,z = map(float,origin[1].split(','))
    if not inside(x,y,z):
        return block
    archived_physics.append(block.replace(origin[0],f'origin = [ {x+1060}, {y+220}, {z} ]').rstrip().rstrip(',')+',\n')
    return ''

cleaned = physics_pattern.sub(split_physics, render_pattern.sub(split_render, original))
if counts != [3176, 22013, 44026] or len(archived_physics) != 10:
    raise RuntimeError(f'Unexpected pavilion matches: {counts}, {len(archived_physics)} collision boxes')
(assets/clean/'dressing.vmdl').write_text(cleaned)

template = archived_render[0]
first_path = re.search(r'filename = "([^"]+)"', template)[1]
for source, name in [(base+'pavilion-junction/junction.obj','returns'),
                     (base+'garden-shelter/shelter_details.obj','roof')]:
    lines, _ = read_obj(source)
    archived_render.append(template.replace(first_path,save_local(source,name,lines)).replace('name = '+re.search(r'name = ("[^"]+")', template)[1],f'name = "{name}"'))

def insert_once(pattern, text, blocks):
    matches = iter((''.join(blocks),))
    return pattern.sub(lambda _: next(matches,''), text)

prop = insert_once(physics_pattern, insert_once(render_pattern,original,archived_render),archived_physics)
prop = re.sub(r'(?m)^[ \t]*\{\n[ \t]*_class = "PhysicsHullFile"[\s\S]*?^[ \t]*\},?\n', '', prop)
prop = re.sub(r'(remaps =\s*\[)', r'\1\n{ from = "vr_pavilion_tile.vmat" to = "materials/buildings/roof_tiles.vmat" },',prop,count=1)
(assets/archive/'pavilion.vmdl').write_text(prop)
(assets/archive/'pavilion_flat.vmdl').write_text(render_pattern.sub(
    lambda match: '' if f'{archive}/roof.obj' in match[0] else match[0], prop))
print(f'Archived {sum(counts):,} faces and {len(archived_physics)} collision boxes')
