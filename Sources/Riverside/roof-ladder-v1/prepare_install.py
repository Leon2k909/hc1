from pathlib import Path
import json,hashlib,re
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/roof-ladder-v1';STAGE=OUT/'install-stage';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());assert json.loads((OUT/'verification.json').read_text())['actual_play_verified']
public=ROOT/m['source_vmdl'];assert sha(public)==m['source_vmdl_sha256'] and sha(ROOT/m['source_model'])==m['source_sha256']
original=public.read_text();assert 'roof_ladder_lod' not in original
def span(s,kind):
    a=s.rfind('{',0,s.index('_class = "'+kind+'"'));depth=0
    for b in range(a,len(s)):
        if s[b]=='{':depth+=1
        elif s[b]=='}':
            depth-=1
            if depth==0:return a,b+1
    raise ValueError(kind)
t=original.replace((Path(m['source_model']).relative_to('Assets')).as_posix(),'models/maps/riverside/roof-ladder-v1/levee_without_ladder.obj');nodes=[]
for i in range(3):
    src=REVIEW/f'Assets/models/maps/riverside/roof-ladder-v1/ladder_lod{i}.obj';dst=STAGE/f'Assets/models/maps/riverside/roof-ladder-v1/installed_lod{i}.obj';dst.parent.mkdir(parents=True,exist_ok=True);lines=[]
    for line in src.read_text().splitlines():
        if line.startswith('v '):
            x,y,z=map(float,line.split()[1:]);line=f'v {z-697:.3f} {y+96:.3f} {407-x:.3f}'
        elif line.startswith('vn '):
            x,y,z=map(float,line.split()[1:]);line=f'vn {z:.3f} {y:.3f} {-x:.3f}'
        elif line.startswith('mtllib '):line=f'mtllib installed_lod{i}.mtl'
        lines.append(line)
    dst.write_text('\n'.join(lines)+'\n');dst.with_suffix('.mtl').write_bytes(src.with_suffix('.mtl').read_bytes())
    nodes.append(f'{{_class="RenderMeshFile" name="roof_ladder_lod{i}" filename="models/maps/riverside/roof-ladder-v1/installed_lod{i}.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},')
a,b=span(t,'RenderMeshList');block=t[a:b];at=block.rfind(']');block=block[:at]+''.join(nodes)+block[at:];t=t[:a]+block+t[b:]
assert 'LODGroupList' not in t
groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["riverside_levee","roof_ladder_lod{i}"]}},' for i,d in enumerate((0,20,45)))
t=t[:a]+'{_class="LODGroupList" children=['+groups+']},'+t[a:]
candidate=(REVIEW/'Assets/models/maps/riverside/roof-ladder-v1/ladder.vmdl').read_text();remaps=re.findall(r'\{ from = "[^"]+" to = "[^"]+" \}',candidate)
at=t.index('{ from = ');t=t[:at]+''.join(r+',\n' for r in remaps)+t[at:]
marker='_class = "PhysicsShapeList"';assert t[t.index(marker):]==original[original.index(marker):]
dst=STAGE/public.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(t,encoding='utf-8')
(OUT/'install-before.vmdl').write_bytes(public.read_bytes());plan=dict(before={m['source_vmdl']:sha(public),m['source_model']:sha(ROOT/m['source_model'])},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print('Staged approved public ladder integration; physics unchanged.')
