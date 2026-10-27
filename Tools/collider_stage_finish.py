"""Stage a bounded visual migration against the currently published Collider mesh."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import platform
import numpy as np
import map_kit as K
import ares_map as A
import collider_finish as F

ROOT=Path(__file__).resolve().parents[1]
REL=Path("models/maps/collider/collider_structure.obj")
STAGE=ROOT/"output/depot-finish-20261027/stage-v1"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def triangle_key(paint,points):
    return paint,tuple(sorted(tuple(round(float(x),4) for x in point) for point in points))


def old_portals():
    model=K.Model()
    for values in F.portals(): A.door_frame(model,*values)
    triangles=Counter()
    for paint,polys in model.polygons.items():
        for points,normal in polys:
            for i in range(1,len(points)-1):
                triangles[triangle_key(paint,[points[0],points[i],points[i+1]])]+=1
    return triangles


def migrate_obj(source,stage):
    raw=source.read_text(encoding="utf-8").splitlines(keepends=True)
    if any("Collider finish-v1" in line for line in raw):
        raise RuntimeError("This is a one-time migration; build from the retained baseline for revisions.")
    verts=[];normals=[];counts=Counter();remove=old_portals();remaining=remove.copy()
    base_context=K.Model()
    paint=None;published=None;output=[];removed=0;reclassified=Counter()
    for line in raw:
        if line.startswith('v '):
            q=np.array(list(map(float,line.split()[1:])));verts.append(np.array((-q[0],q[2],q[1])))
        elif line.startswith('vn '):
            q=np.array(list(map(float,line.split()[1:])));normals.append(np.array((-q[0],q[2],q[1])))
        elif line.startswith('vt '): counts['vt']+=1
        elif line.startswith('usemtl '):
            paint=line.split()[1];published=paint
        elif line.startswith('f '):
            items=[word.split('/') for word in line.split()[1:]]
            assert len(items)==3
            points=[verts[int(item[0])-1] for item in items]
            normal=normals[int(items[0][2])-1]
            if paint in ('co_floor','co_white','co_steel'):
                base_context.polygon(paint,points,normal)
            key=triangle_key(paint,points)
            if remaining[key]:
                remaining[key]-=1;removed+=1;continue
            selected=F.surface_paint(paint,normal)
            if selected!=paint: reclassified[selected]+=1
            if selected!=published:
                output.append(f'usemtl {selected}\n');published=selected
        output.append(line)
    assert not +remaining, f"Unmatched original portal triangles: {sum((+remaining).values())}"
    assert removed==sum(remove.values())==1440,(removed,sum(remove.values()))
    geometry=K.Model()
    for values in F.portals(): F.door_frame(geometry,*values)
    # Main-hall fixtures live in the detail/machine resources. Read their published
    # planes to support them, without changing either model's geometry or physics.
    contexts=[base_context]
    for name in ('collider_detail','collider_machine'):
        positions=[];ns=[];paint=None;context=K.Model()
        with (ROOT/f'Assets/models/maps/collider/{name}.obj').open() as stream:
            for line in stream:
                if line.startswith('v '):
                    q=list(map(float,line.split()[1:]));positions.append((-q[0],q[2],q[1]))
                elif line.startswith('vn '):
                    q=list(map(float,line.split()[1:]));ns.append((-q[0],q[2],q[1]))
                elif line.startswith('usemtl '):paint=line.split()[1]
                elif line.startswith('f ') and paint in ('co_floor','co_white','co_steel'):
                    ix=[part.split('/') for part in line.split()[1:]]
                    context.polygon(paint,[positions[int(i[0])-1] for i in ix],ns[int(ix[0][2])-1])
        contexts.append(context)
    F.add_finish(geometry,F.surface_context(contexts))
    assert not geometry.boxes and not geometry.hulls
    generated=stage/'generated';generated.mkdir()
    added=K.write_obj(generated/'architecture.obj',F.configure(geometry),'collider_structure')
    offsets=(len(verts),counts['vt'],len(normals))
    extra=['\n# Collider finish-v1: render-only architecture and located wear\n','o collider_finish_v1\n']
    for line in (generated/'architecture.obj').read_text().splitlines(keepends=True):
        if line.startswith(('mtllib ','# ','o ')): continue
        if line.startswith('f '):
            words=[]
            for word in line.split()[1:]:
                words.append('/'.join(str(int(value)+offsets[k]) for k,value in enumerate(word.split('/'))))
            line='f '+' '.join(words)+'\n'
        extra.append(line)
    target=stage/'assets'/REL;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(''.join(output+extra),encoding='utf-8',newline='')
    # Every original attribute and retained face line remains byte-for-byte.
    for prefix in ('v ','vt ','vn '):
        before=[line for line in raw if line.startswith(prefix)]
        after=[line for line in output if line.startswith(prefix)]
        assert before==after
    return dict(removed_flat_portal_triangles=removed,added_finish_triangles=added,
                reclassified_triangles=dict(reclassified),new_materials=list(F.PAINTS),
                base_triangle_count=sum(l.startswith('f ') for l in raw),
                final_triangle_count=sum(l.startswith('f ') for l in output+extra))


def build(stage,baseline=None,previous_stage=None):
    if stage.exists(): raise FileExistsError(f"Refusing to replace stage: {stage}")
    stage.mkdir(parents=True)
    inputs=[REL,REL.with_suffix('.mtl'),REL.with_suffix('.vmdl')]
    before={str(p).replace('\\','/'):sha(ROOT/'Assets'/p) for p in inputs}
    for path in inputs:
        destination=stage/'before'/path;destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes((ROOT/'Assets'/path).read_bytes())
    source_root=ROOT/'Assets'
    if baseline is not None:
        previous=json.loads(((previous_stage or baseline)/'manifest.json').read_text())
        own={entry['relative']:entry for entry in previous['files']}
        for path in inputs:
            entry=own[path.as_posix()]
            assert before[path.as_posix()] in (entry['before'],entry['after']),f'Concurrent change to {path}'
        source_root=baseline/'before'
    report=migrate_obj(source_root/REL,stage)
    F.materials(stage/'assets'/F.MATERIAL_DIR)
    target=stage/'assets'/REL.with_suffix('.mtl')
    target.write_bytes((source_root/REL.with_suffix('.mtl')).read_bytes()+
        ''.join(f'newmtl {name}\nKd 1 1 1\nd 1\n' for name in F.PAINTS).encode())
    source=source_root/REL.with_suffix('.vmdl');raw=source.read_text(encoding='utf-8')
    assert 'cf_floor.vmat' not in raw
    pattern=r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
    def remap(match):
        body=match[2].rstrip().rstrip(',')
        new=',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{F.MATERIAL_DIR}/{p}.vmat" }}' for p in F.PAINTS)
        return match[1]+body+',\n'+new+match[3]
    result,count=re.subn(pattern,remap,raw,count=1);assert count==1
    physics=raw[raw.index('\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'):]
    assert result.endswith(physics)
    (stage/'assets'/REL.with_suffix('.vmdl')).write_text(result,encoding='utf-8',newline='')
    protected=[
        'scenes/maps/Collider/collider.scene','ui/Minimaps/minimap_collider.png',
        'models/maps/collider/collider_structure_hulls_metal.obj',
        'models/maps/collider/collider_detail.obj','models/maps/collider/collider_detail.vmdl',
        'models/maps/collider/collider_machine.obj','models/maps/collider/collider_machine.vmdl',
        'models/maps/collider/collider_glass.obj','models/maps/collider/collider_glass.vmdl',
    ]
    for scan in ('concrete_layers_02','concrete_wall_009'):
        for suffix in ('diff_2k.jpg','nor_dx_2k.jpg','rough_2k.jpg'):
            protected.append(f'{F.SCAN}{scan}_{suffix}')
    files=[]
    for p in sorted((stage/'assets').rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(stage/'assets').as_posix()
        files.append({'relative':relative,'before':sha(ROOT/'Assets'/relative) if (ROOT/'Assets'/relative).exists() else None,'after':sha(p)})
    sources=['Tools/collider_finish.py','Tools/collider_stage_finish.py','Tools/collider_map.py','Tools/collider_materials.py']
    sources += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'Sources/Collider/finish-v1/scans').iterdir()) if p.is_file()]
    manifest={'revision':'collider-environment-finish-v1','stage':str(stage.relative_to(ROOT)).replace('\\','/'),
        'files':files,'protected':{p:sha(ROOT/'Assets'/p) for p in protected},
        'sources':{p:sha(ROOT/p) for p in sources},
        'geometry':report,'physics_suffix_sha256':hashlib.sha256(physics.encode()).hexdigest(),
        'source_before':before,'scene_changes':False,'light_changes':False}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    assert all(sha(ROOT/'Assets'/p)==value for p,value in before.items())
    print(json.dumps({'stage':str(stage),'files':len(files),**report},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=STAGE)
    parser.add_argument('--baseline',type=Path,help='Retained first stage, allowing bounded material/geometry refinement')
    parser.add_argument('--previous-stage',type=Path,help='Most recently published stage, for concurrent-change guards')
    args=parser.parse_args()
    # Avoid the optional Windows WMI platform query during SciPy import.
    if hasattr(platform,'_wmi_query'): platform._wmi_query=lambda *a,**k: (_ for _ in ()).throw(OSError('Skipped for offline staging'))
    build(args.out.resolve(),args.baseline.resolve() if args.baseline else None,
          args.previous_stage.resolve() if args.previous_stage else None)
