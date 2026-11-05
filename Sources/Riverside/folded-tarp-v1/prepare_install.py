from pathlib import Path
import re,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/folded-tarp-v1';stage=OUT/'install-stage';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());assert json.loads((OUT/'verification.json').read_text())['actual_play_verified'];public=ROOT/m['source_vmdl']
assert sha(public)==m['source_vmdl_sha256'] and sha(ROOT/m['source_model'])==m['source_sha256']
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
original=public.read_text();assert 'folded_tarp_lod' not in original
def span(s,kind):
    match=re.search(r'_class\s*=\s*"'+kind+'"',s);a=s.rfind('{',0,match.start());depth=0
    for b in range(a,len(s)):
        if s[b]=='{':depth+=1
        elif s[b]=='}':
            depth-=1
            if depth==0:return a,b+1
    raise ValueError(kind)
t=original.replace(Path(m['source_model']).relative_to('Assets').as_posix(),'models/maps/riverside/folded-tarp-v1/levee_without_tarp.obj');nodes=[]
for lod in range(3):
    src=REVIEW/f'Assets/models/maps/riverside/folded-tarp-v1/tarp_lod{lod}.obj';dst=stage/f'Assets/models/maps/riverside/folded-tarp-v1/installed_lod{lod}.obj';dst.parent.mkdir(parents=True,exist_ok=True);lines=[]
    for line in src.read_text().splitlines():
        if line.startswith('v '):
            x,y,z=map(float,line.split()[1:]);line=f'v {z-737:.3f} {y+314:.3f} {607-x:.3f}'
        elif line.startswith('vn '):
            x,y,z=map(float,line.split()[1:]);line=f'vn {z:.3f} {y:.3f} {-x:.3f}'
        elif line.startswith('mtllib '):line=f'mtllib installed_lod{lod}.mtl'
        elif line.startswith('usemtl '):line='usemtl rf_tarp_'+line.split()[1]
        lines.append(line)
    dst.write_text('\n'.join(lines)+'\n');dst.with_suffix('.mtl').write_text(re.sub(r'(?m)^newmtl (\S+)',r'newmtl rf_tarp_\1',src.with_suffix('.mtl').read_text()))
    nodes.append(f'{{_class="RenderMeshFile" name="folded_tarp_lod{lod}" filename="models/maps/riverside/folded-tarp-v1/installed_lod{lod}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},')
a,b=span(t,'RenderMeshList');block=t[a:b];at=block.rfind(']');block=block[:at]+''.join(nodes)+block[at:];t=t[:a]+block+t[b:]
a,b=span(t,'LODGroupList');old=[]
for d,names in re.findall(r'_class\s*=\s*"LODGroup"\s+switch_threshold\s*=\s*([\d.]+)\s+meshes\s*=\s*\[([^\]]+)\]',t[a:b]):old.append((float(d),re.findall(r'"([^"]+)"',names)))
assert len(old)==3
groups=[]
for d in sorted(set([v for v,_ in old]+[0,15,35])):
    names=max((g for g in old if g[0]<=d),key=lambda g:g[0])[1];lod=2 if d>=35 else 1 if d>=15 else 0
    groups.append('{_class="LODGroup" switch_threshold=%g meshes=[%s]},'%(d,','.join('"'+n+'"' for n in names+[f'folded_tarp_lod{lod}'])))
t=t[:a]+'{_class="LODGroupList" children=['+''.join(groups)+']}'+t[b:]
candidate=(REVIEW/'Assets/models/maps/riverside/folded-tarp-v1/tarp.vmdl').read_text();remaps=re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',candidate);at=t.index('{ from = ');t=t[:at]+''.join('{ from = "rf_tarp_%s" to = "%s" },\n'%(a,b) for a,b in remaps)+t[at:]
marker='_class = "PhysicsShapeList"';assert t[t.index(marker):]==original[original.index(marker):]
dst=stage/public.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(t);(OUT/'install-before.vmdl').write_bytes(public.read_bytes())
plan=dict(before={m['source_vmdl']:sha(public),m['source_model']:sha(ROOT/m['source_model'])},files={p.relative_to(stage).as_posix():sha(p) for p in stage.rglob('*') if p.is_file()});(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
s=(ROOT/'Sources/Riverside/roof-ladder-v1/install.cs.txt').read_text().replace('roof-ladder-review','folded-tarp-review').replace('roof-ladder-v1','folded-tarp-v1').replace('legacy_ladder.vmdl','legacy_tarp.vmdl');(HERE/'install.cs.txt').write_text(s)
print('Staged tarp replacement with five combined LOD groups; roof ladder and physics preserved.')
