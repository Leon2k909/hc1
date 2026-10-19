"""Localise the reviewed sack components without re-sculpting their geometry."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = ROOT/'output/lowtide/quality-pass/rebase-2026-10-18'
REVIEW = 'models/maps/lowtide/sack_review'
STACKS = 'models/maps/lowtide/sacks'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest = json.loads((BASE/'sacks/manifest.json').read_text())
lods = json.loads((BASE/'sack-lods/manifest.json').read_text())
report = dict(revision='localised-sewn-sack-stacks-v1', source_manifest=sha(BASE/'sacks/manifest.json'),
              production_changed=False, files={}, protected={}, bases=[], stacks=[], preserved_triangles=0,
              thresholds=[0, 10, 24], thresholds_native_reviewed=False)

def write(relative, data):
    path=OUT/'stage'/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data,str): data=data.encode()
    if path.exists(): assert path.read_bytes()==data, f'Changed stage {path}'
    else: path.write_bytes(data)
    report['files'][relative]=sha(path)

def connected(rows):
    remaining=set(range(len(rows)))
    groups=[]
    while remaining:
        pending=[min(remaining)]; remaining.remove(pending[0]); group=[]
        while pending:
            a=pending.pop(); group.append(a)
            lo=rows[a]['lo']; hi=[x+y for x,y in zip(lo,rows[a]['size'])]
            near=[b for b in remaining if all(max(lo[k]-rows[b]['lo'][k]-rows[b]['size'][k],rows[b]['lo'][k]-hi[k])<=2.01 for k in range(3))]
            remaining.difference_update(near); pending.extend(near)
        groups.append(sorted(group))
    return groups

HEADER='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
def modeldoc(name):
    meshes=',\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{STACKS}/{name}_lod{i}.obj" import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }}' for i in range(3))
    levels=',\n'.join(f'{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{i}" ] }}' for i,t in enumerate(report['thresholds']))
    return HEADER+'''{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ { from = "lt_jute.vmat" to = "materials/lowtide/lt_jute.vmat" } ] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = ['''+meshes+'''] },
{ _class = "LODGroupList" children = ['''+levels+'''] }
] model_archetype = "" primary_associated_entity = "" base_model_name = "" } }\n'''

for name,rows in manifest['layout'].items():
    original=ROOT/f'Assets/models/maps/lowtide/{name}.obj'
    assert sha(original)==manifest['changes'][f'models/maps/lowtide/{name}.obj']['before']
    for ext in ('obj','mtl','vmdl'):
        p=original.with_suffix('.'+ext)
        report['protected'][p.relative_to(ROOT).as_posix()]=sha(p)
    lines=original.read_text().splitlines(); paint=None; kept=[]; removed=0; other=0
    for line in lines:
        if line.startswith('usemtl '): paint=line[7:]
        if line.startswith('f ') and paint=='lt_jute': removed+=1
        else:
            kept.append(line)
            if line.startswith('f '): other+=1
    assert removed==len(rows)*120
    report['preserved_triangles']+=other
    write(f'{REVIEW}/{name}.obj','\n'.join(kept)+'\n')
    write(f'{REVIEW}/{name}.mtl',original.with_suffix('.mtl').read_bytes())
    vmdl=original.with_suffix('.vmdl').read_text()
    old=f'filename = "models/maps/lowtide/{name}.obj"'
    assert vmdl.count(old)==1
    write(f'{REVIEW}/{name}.vmdl',vmdl.replace(old,f'filename = "{REVIEW}/{name}.obj"'))
    report['bases'].append(dict(source=f'models/maps/lowtide/{name}.vmdl',review=f'{REVIEW}/{name}.vmdl',removed=removed,other_triangles=other))
    groups=connected(rows)
    records=[]
    for number,ids in enumerate(groups):
        lo=[min(rows[i]['lo'][k] for i in ids) for k in range(3)]
        hi=[max(rows[i]['lo'][k]+rows[i]['size'][k] for i in ids) for k in range(3)]
        origin=[round((a+b)*.5,4) for a,b in zip(lo,hi)]
        short=name.replace('lowtide_dress_','').replace('lowtide_','')
        stack=f'{short}_{number:02d}'
        record=dict(name=stack,source=name,indices=ids,sacks=len(ids),lo=lo,hi=hi,plan_origin=origin,
                    world_position=[origin[1],-origin[0],origin[2]],model=f'{STACKS}/{stack}.vmdl',triangles=[])
        records.append(record)
        write(record['model'],modeldoc(stack))
    for level,per_sack in enumerate((1570,818,288)):
        if level==0:
            component=BASE/f'sacks/{name}-sacks.obj'; expected=manifest['models'][name]['component_sha256']
        else:
            c=lods['levels'][str(level)][name]
            component=ROOT/c['component']; expected=c['component_sha256']
        assert sha(component)==expected
        attributes=[[],[],[]]; faces=[]
        for line in component.read_text().splitlines():
            if line.startswith('v '): attributes[0].append(line[2:])
            elif line.startswith('vt '): attributes[1].append(line[3:])
            elif line.startswith('vn '): attributes[2].append(line[3:])
            elif line.startswith('f '): faces.append(tuple(tuple(int(c)-1 for c in p.split('/')) for p in line[2:].split()))
        assert len(faces)==per_sack*len(rows)
        seen=set()
        for rec in records:
            stem=f"{rec['name']}_lod{level}"
            maps=[{}, {}, {}]; values=[[],[],[]]; output_faces=[]
            e,n,z=rec['plan_origin']; shift=(-e,z,n)
            for index in rec['indices']:
                assert index not in seen; seen.add(index)
                for face in faces[index*per_sack:(index+1)*per_sack]:
                    corners=[]
                    for corner in face:
                        result=[]
                        for k,old_index in enumerate(corner):
                            if old_index not in maps[k]:
                                value=attributes[k][old_index]
                                if k==0:
                                    original_position=list(map(float,value.split()))
                                    local_position=[round(v-d,4) for v,d in zip(original_position,shift)]
                                    assert all(abs(v-(l+d))<.000051 for v,l,d in zip(original_position,local_position,shift))
                                    value=' '.join(f'{v:.4f}' for v in local_position)
                                maps[k][old_index]=len(values[k])+1
                                values[k].append(value)
                            result.append(str(maps[k][old_index]))
                        corners.append('/'.join(result))
                    output_faces.append('f '+' '.join(corners))
            content=[f'# Reviewed sewn sacks; local stack {rec["name"]}',f'mtllib {stem}.mtl',f'o {stem}']
            for prefix,array in zip(('v','vt','vn'),values): content += [prefix+' '+v for v in array]
            content+=['usemtl lt_jute']+output_faces
            write(f'{STACKS}/{stem}.obj','\n'.join(content)+'\n')
            write(f'{STACKS}/{stem}.mtl','newmtl lt_jute\nKd 1 1 1\nd 1\n')
            rec['triangles'].append(len(output_faces))
        assert len(seen)==len(rows)
    report['stacks']+=records

assert report['preserved_triangles']==742742
assert sum(s['sacks'] for s in report['stacks'])==264
assert all(sha(ROOT/p)==h for p,h in report['protected'].items())
(OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stacks=len(report['stacks']),files=len(report['files']),sacks=264,unchanged_other_triangles=report['preserved_triangles'],triangles=[sum(s['triangles'][i] for s in report['stacks']) for i in range(3)],groups=[(s['name'],s['sacks'],s['world_position']) for s in report['stacks']]),indent=2))
