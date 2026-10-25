"""Stage only the clock-frontage barrel pairs and translate their existing hulls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np

import map_kit as K
import belltower_detail as D
import belltower_barrels_v2 as V
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/barrels-v2'
PAINTS={b'planks_dark',b'planks',b'iron_black'}


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def patch_mesh(source,target,centres,addition=None,expected=None):
    sparse={};counts={b'v':0,b'vt':0,b'vn':0};removed=set();found=Counter();paint=None;total=0
    for number,line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            counts[b'v']+=1
            p=np.asarray(list(map(float,line.split()[1:])))
            plan=np.array((-p[0],p[2]))
            if -.001 <= p[1] <= 36.001 and any(np.max(np.abs(plan-c))<13.12 for c in centres):
                sparse[counts[b'v']]=(p,line[2:].strip())
        elif line.startswith(b'vt '):counts[b'vt']+=1
        elif line.startswith(b'vn '):counts[b'vn']+=1
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f '):
            total+=1
            if paint not in PAINTS:continue
            ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
            if not all(i in sparse for i in ids):continue
            points=[sparse[i][0] for i in ids]
            if not any(all(np.max(np.abs(np.array((-p[0],p[2]))-c))<13.12 for p in points) for c in centres):continue
            signature=(paint,frozenset(sparse[i][1] for i in ids))
            if expected is not None and signature not in expected:continue
            removed.add(number);found[signature]+=1
    if not removed:return None,found
    extra_tables=[];extra_faces=[]
    if addition:
        for line in addition.open('rb'):
            if line.startswith((b'v ',b'vt ',b'vn ')):extra_tables.append(line)
            elif line.startswith(b'usemtl '):extra_faces.append(line)
            elif line.startswith(b'f '):
                tokens=[b'/'.join(str(int(v)+counts[k]).encode() for k,v in zip((b'v',b'vt',b'vn'),token.split(b'/')))
                        for token in line.split()[1:]]
                extra_faces.append(b'f '+b' '.join(tokens)+b'\n')
    target.parent.mkdir(parents=True,exist_ok=True)
    retained=hashlib.sha256();inserted=False
    with target.open('wb') as output:
        for number,line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '):output.writelines(extra_tables);inserted=True
            if number not in removed:output.write(line);retained.update(line)
        output.writelines(extra_faces)
    assert inserted
    return {'removed_triangles':len(removed),'added_triangles':sum(s.startswith(b'f ') for s in extra_faces),
            'triangles_before':total,'triangles_after':total-len(removed)+sum(s.startswith(b'f ') for s in extra_faces),
            'unrelated_source_bytes_exact':True,'retained_bytes_sha256':retained.hexdigest()},found


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='r1');args=parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+',args.revision)
    stage=OUT/args.revision/'stage';assert not stage.exists();stage.mkdir(parents=True)
    manifest={'revision':'clock-frontage-barrels-v2','files':{},'models':{},'source_sha256':{},
              'protected_sha256':{},'scene_unchanged':True,'only_clock_frontage_barrels_changed':True}
    records=V.placements();assert len(records)==2
    # Exact old triangle count, while position selection uses the installed hulls
    # to avoid guessing a random-number stream or rebuilding the entire map.
    original=K.Model();D.barrel(original,(0.,0.),0.,13.,36.)
    expected_count=original.triangle_count()*2
    for side in ('west','east'):
        sign=1 if side=='west' else -1
        centres=[np.asarray((row['old'][0]*sign,row['old'][1])) for row in records]
        canonical=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        vmdl=canonical.with_suffix('.vmdl')
        vmdl_raw=vmdl.read_bytes();vmdl_text=vmdl_raw.decode()
        new=K.Model()
        for row in records:
            V.build(new,row['new'],seed=row['seed'])
        if side=='east':new=new.mirrored()
        assert not new.boxes and not new.hulls and not new.props
        addition=stage/f'Assets/models/maps/belltower/barrels-v2/{side}.obj'
        addition.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(addition,new,f'belltower_{side}')
        row,wanted=patch_mesh(canonical,stage/canonical.relative_to(ROOT),centres,addition)
        assert sum(wanted.values())==expected_count,(side,sum(wanted.values()),expected_count)
        model_record={'canonical':row,'bounded':[],'moved_hulls':[]}
        found=Counter()
        resources=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl_text)
        for resource in resources:
            # These are the only original materials used by the old casks.
            if not any(resource.endswith('_'+paint.decode()+'.obj') for paint in PAINTS):continue
            source=ROOT/'Assets'/resource
            result,seen=patch_mesh(source,stage/source.relative_to(ROOT),centres,expected=wanted)
            if result:
                found.update(seen);model_record['bounded'].append({'path':source.relative_to(ROOT).as_posix(),**result})
        assert found==wanted,('Bounded/canonical barrel faces differ',side)

        hull_path=ROOT/f'Assets/models/maps/belltower/belltower_{side}_hulls_wood.obj'
        hull_lines=hull_path.read_bytes().splitlines(keepends=True);changed_lines=set()
        for item in V.read_hulls(hull_path):
            for source_row,old in zip(records,centres):
                if np.linalg.norm(np.asarray(item['centre'])-old)>.003 or abs(item['height']-36)>.001:continue
                new_centre=np.asarray((source_row['new'][0]*sign,source_row['new'][1]))
                delta=new_centre-old
                for number,point in zip(item['lines'],item['obj']):
                    moved=point+np.array((-delta[0],0,delta[1]))
                    ending=b'\r\n' if hull_lines[number].endswith(b'\r\n') else b'\n'
                    hull_lines[number]=('v '+' '.join(f'{v:.3f}' for v in moved)).encode()+ending
                    changed_lines.add(number)
                model_record['moved_hulls'].append({'old':old.tolist(),'new':new_centre.tolist(),'vertices':len(item['indices'])})
        assert len(model_record['moved_hulls'])==2 and len(changed_lines)==40
        target=stage/hull_path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b''.join(hull_lines))
        before_lines=hull_path.read_bytes().splitlines(keepends=True)
        assert all(a==b for i,(a,b) in enumerate(zip(before_lines,hull_lines)) if i not in changed_lines)
        model_record['all_other_hull_bytes_exact']=True

        # Append one small render import, preserving all current shared nodes.
        lo,hi=span(vmdl_text,'_class = "RenderMeshList"');render=vmdl_text[lo:hi]
        a,b=span(render,'_class = "RenderMeshFile"');node=render[a:b]
        node=re.sub(r'name = "[^"]+"',f'name = "clock_barrels_v2_{side}"',node,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "models/maps/belltower/barrels-v2/{side}.obj"',node,count=1)
        insertion=render.rfind(']')
        prefix=render[:insertion]
        end=len(prefix.rstrip())
        if prefix[:end].endswith('}'):prefix=prefix[:end]+','+prefix[end:]
        updated_render=prefix+node+',\n'+render[insertion:]
        updated=vmdl_text[:lo]+updated_render+vmdl_text[hi:]
        existing=set(re.findall(r'from = "([^"]+)"',updated))
        remaps=''.join(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{path}" }},\n'
                      for paint,path in V.MATERIALS.items() if paint+'.vmat' not in existing)
        anchor=re.search(r'(?m)^.*\{ from = "[^"]+" to = "[^"]+" \}.*$',updated).group(0)
        updated=updated.replace(anchor,remaps+anchor,1)
        assert updated.replace(remaps,'',1).replace(updated_render,render,1)==vmdl_text
        (stage/vmdl.relative_to(ROOT)).write_bytes(updated.encode())
        model_record['new_triangles']=new.triangle_count();assert new.triangle_count()<30000
        model_record['existing_render_and_physics_nodes_exact']=True
        manifest['models'][side]=model_record
    for p in (stage/'Assets').rglob('*'):
        if not p.is_file():continue
        relative=p.relative_to(stage).as_posix();installed=ROOT/relative
        before=sha(installed) if installed.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(installed,backup)
        manifest['files'][relative]={'source':p.relative_to(ROOT).as_posix(),'before':before,'after':sha(p),
                                    'backup':backup.relative_to(ROOT).as_posix() if before else None}
    for path in ['Tools/belltower_barrels_v2.py','Tools/belltower_stage_barrels_v2.py',
                 'Tools/belltower_map.py','Tools/belltower_detail.py',V.SOURCE.relative_to(ROOT).as_posix()]:
        manifest['source_sha256'][path]=sha(ROOT/path)
    path='Assets/scenes/maps/Belltower/belltower.scene';manifest['protected_sha256'][path]=sha(ROOT/path)
    for path in V.MATERIALS.values():manifest['protected_sha256']['Assets/'+path]=sha(ROOT/'Assets'/path)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(manifest['files']),'new_triangles_per_pair':new.triangle_count(),
                      'moved_barrels':4,'all_unrelated_obj_and_hull_bytes_preserved':True}))


if __name__=='__main__':main()
