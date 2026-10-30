"""Bounded Collider guardrail replacement and true floor recess migration."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import hashlib
import json
import re
import types
import numpy as np
import map_kit as K
import collider_map as M
import collider_detail_geometry as D
import collider_craft as C

ROOT=Path(__file__).resolve().parents[1]
PRIVATE='output/collider-detail-v3-20261027'
NAMES=('collider_structure','collider_machine')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def triangles(model):
    for paint,polys in model.polygons.items():
        for points,normal in polys:
            for i in range(1,len(points)-1):
                yield paint,[points[0],points[i],points[i+1]]


def key(paint,points):return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))


def collect():
    original=types.ModuleType('original_collider_detail')
    exec(compile((ROOT/'Sources/Collider/craft-v1/original-detail.py.txt').read_text(),'<retained-original>','exec'),original.__dict__)
    cache=ROOT/PRIVATE/'rail-calls.json'
    call_sources=['Tools/collider_map.py','Tools/collider_detail_geometry.py','Tools/collider_machinery.py','Tools/collider_services.py']
    hashes={p:sha(ROOT/p) for p in call_sources}
    stored=json.loads(cache.read_text()) if cache.exists() else None
    calls=defaultdict(list);old_rail,old_slope=D.rail,D.slope_rail;old_floor=C.refine_floor
    def record(m,*args,**kw):calls[id(m)].append(('rail',args,kw))
    def slope(m,*args,**kw):calls[id(m)].append(('slope_rail',args,kw))
    if stored and stored['sources']==hashes:specs=stored['models']
    else:
        try:
            D.rail=record;D.slope_rail=slope;C.refine_floor=lambda m:None
            models=M.build()
        finally:D.rail=old_rail;D.slope_rail=old_slope;C.refine_floor=old_floor
        specs={name:calls[id(models[name])] for name in NAMES}
        cache.write_text(json.dumps({'sources':hashes,'models':specs},default=lambda v:v.tolist(),indent=2)+'\n')
    output={}
    for name in NAMES:
        old,new=K.Model(),K.Model()
        for method,args,kw in specs[name]:
            getattr(original,method)(old,*args,**kw)
            getattr(C,method)(new,*args,**kw)
        # Source collision authoring must agree independently of published bytes.
        assert len(old.boxes)==len(new.boxes) and len(old.hulls)==len(new.hulls)
        for left,right in zip(old.boxes,new.boxes):
            for a,b in zip(left[:3],right[:3]):assert np.allclose(a,b,atol=1e-9)
            assert left[3]==right[3]
        output[name]=(old,new,len(specs[name]))
    return output


def migrate(source,target,old,new,floors=False):
    lines=source.read_text(encoding='utf-8').splitlines(keepends=True)
    assert not any('Collider craft-v1' in s for s in lines)
    expected=Counter(key(p,pnts) for p,pnts in triangles(old));remaining=expected.copy()
    vertices=[];normals=[];uvs=[];paint=None;output=[];removed=0;cut=0
    for line in lines:
        if line.startswith('v '):
            a,b,c=map(float,line.split()[1:]);vertices.append(np.array((-a,c,b)))
        elif line.startswith('vn '):
            a,b,c=map(float,line.split()[1:]);normals.append(np.array((-a,c,b)))
        elif line.startswith('vt '):uvs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            indices=[list(map(int,p.split('/'))) for p in line.split()[1:]]
            assert len(indices)==3
            points=[vertices[i[0]-1] for i in indices];normal=normals[indices[0][2]-1]
            signature=key(paint,points)
            if remaining[signature]:remaining[signature]-=1;removed+=1;continue
            if floors and paint=='cf_floor' and normal[2]>.99:
                coords=[uvs[i[1]-1] for i in indices]
                assert np.allclose(coords,[C.floor_uv(p) for p in points],atol=1.2e-5),'Unexpected existing floor UV origin'
                pieces,changed=C.cut_floor(points,coords)
                if changed:
                    cut+=1
                    for polygon in pieces:
                        new.polygon(paint,[v[:3] for v in polygon],C.UP,uv=[v[3:] for v in polygon])
                    continue
        output.append(line)
    assert not +remaining,(source.name,'Missing original rail triangles',sum((+remaining).values()))
    if floors:
        assert cut>0
        C.floor_details(new)
    assert not new.hulls or len(new.hulls)==len(old.hulls)
    generated=target.parents[4]/'generated';generated.mkdir(parents=True,exist_ok=True)
    temp=generated/(source.stem+'.obj');K.write_obj(temp,C.configure(new),source.stem)
    extra=['\n# Collider craft-v1: fabricated guardrails and cut floor details\n','o collider_craft_v1\n']
    offsets=(len(vertices),len(uvs),len(normals));added=0;bad=0;minimum=1e9
    for paint,points in triangles(new):
        area=np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))*.5
        minimum=min(minimum,area)
        assert area>1e-8,(paint,points,area)
    for line in temp.read_text().splitlines(keepends=True):
        if line.startswith(('mtllib ','# ','o ')):continue
        if line.startswith('f '):
            parts=['/'.join(str(int(v)+offsets[k]) for k,v in enumerate(word.split('/'))) for word in line.split()[1:]]
            line='f '+' '.join(parts)+'\n';added+=1
        extra.append(line)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(''.join(output+extra),encoding='utf-8',newline='')
    return {'before_triangles':sum(s.startswith('f ') for s in lines),'removed_rail_triangles':removed,
        'split_floor_triangles':cut,'added_triangles':added,'final_triangles':sum(s.startswith('f ') for s in output+extra),
        'original_attribute_tables_preserved':True,'minimum_added_area':minimum,
        'materials':sorted(new.polygons)}


def build(stage,baseline=None,previous=None):
    assert not stage.exists(),stage
    stage.mkdir(parents=True)
    groups=collect();report={};files=[]
    if previous:
        previous_files={v['relative']:v['after'] for v in json.loads((previous/'manifest.json').read_text())['files']}
    for name in NAMES:
        rel=Path('models/maps/collider')/(name+'.obj')
        for suffix in ('.obj','.mtl','.vmdl'):
            p=rel.with_suffix(suffix);dest=stage/'before'/p;dest.parent.mkdir(parents=True,exist_ok=True)
            if previous:assert sha(ROOT/'Assets'/p)==previous_files[p.as_posix()],p
            dest.write_bytes((ROOT/'Assets'/p).read_bytes())
        source=(baseline/'before' if baseline else stage/'before')/rel
        old,new,calls=groups[name]
        stats=migrate(source,stage/'assets'/rel,old,new,floors=name=='collider_structure')
        stats['authored_runs']=calls;report[name]=stats
        srcroot=baseline/'before' if baseline else stage/'before'
        (stage/'assets'/rel.with_suffix('.mtl')).write_bytes((srcroot/rel.with_suffix('.mtl')).read_bytes()+
            ''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in C.PAINTS).encode())
        doc=(srcroot/rel.with_suffix('.vmdl')).read_text()
        pattern=r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
        additions=',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{C.MATERIAL_DIR}/{p}.vmat" }}' for p in C.PAINTS)
        result,count=re.subn(pattern,lambda m:m[1]+m[2].rstrip().rstrip(',')+',\n'+additions+m[3],doc,count=1)
        assert count==1
        marker='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
        if marker in doc:assert doc[doc.index(marker):]==result[result.index(marker):]
        (stage/'assets'/rel.with_suffix('.vmdl')).write_text(result,encoding='utf-8',newline='')
    C.materials(stage/'assets'/C.MATERIAL_DIR)
    for p in sorted((stage/'assets').rglob('*')):
        if p.is_file():
            relative=p.relative_to(stage/'assets').as_posix()
            files.append(dict(relative=relative,before=sha(ROOT/'Assets'/relative),after=sha(p)))
    protected=['scenes/maps/Collider/collider.scene','ui/Minimaps/minimap_collider.png',
        'models/maps/collider/collider_structure_hulls_metal.obj','models/maps/collider/collider_detail.obj',
        'models/maps/collider/collider_detail.vmdl','models/maps/collider/collider_glass.obj','models/maps/collider/collider_glass.vmdl']
    protected += [p.relative_to(ROOT/'Assets').as_posix() for p in (ROOT/'Assets/models/maps/collider').rglob('*') if p.is_file() and 'automatic' in p.as_posix() and not p.name.endswith('_c') and '.meta' not in p.name]
    protected += [p.relative_to(ROOT/'Assets').as_posix() for p in (ROOT/'Assets/materials/collider/finish-v1').rglob('*') if p.is_file() and not p.name.endswith('_c') and '.meta' not in p.name]
    sources=['Tools/collider_craft.py','Tools/collider_stage_craft.py','Tools/collider_detail_geometry.py','Tools/collider_map.py','Tools/collider_materials.py']
    manifest=dict(revision='collider-craft-v1',stage=stage.relative_to(ROOT).as_posix(),files=files,
        protected={p:sha(ROOT/'Assets'/p) for p in protected},sources={p:sha(ROOT/p) for p in sources},
        geometry=report,floor_features=list(C.FEATURES),scene_changes=False,light_changes=False)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'stage':manifest['stage'],'files':len(files),'geometry':report},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/PRIVATE/'stage-v1')
    ap.add_argument('--baseline',type=Path);ap.add_argument('--previous-stage',type=Path)
    a=ap.parse_args()
    # Keep the canonical logical path: output may be an offloaded junction.
    absolute=lambda p:ROOT/p if p is not None and not p.is_absolute() else p
    build(absolute(a.out),absolute(a.baseline),absolute(a.previous_stage))
