from geometry import *
RES='models/maps/belltower/well-frame-v2';OUT=Path(tempfile.gettempdir())/'belltower-well-frame-v2';STAGE=OUT/'stage';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
lods=[]
for i in range(3):lods.append(K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}'))
L.RES=RES;L.MAPS=MAPS;(MODEL/'well_frame.vmdl').write_text(L.modeldoc())
old=K.Model();e,n=B.GARDEN_WELL;z=B.GARDEN_Z
for se in (-1,1):old.box((e+se*38-4,n-4,z+34),(e+se*38+4,n+4,z+116),'planks_dark')
old.beam((e-44,n,z+106),(e+44,n,z+106),(6,6),'planks_dark')
B.axle(old,(e,n,z+96),(1,0,0),6,50,{'side':'planks','end':'planks_dark'})
remaining=Counter(geometry(old));removed=0
public=ROOT/'Assets/models/maps/belltower/belltower_centre.vmdl';text=public.read_text();guards=[public]
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text):
    if not re.search(r'_(planks|planks_dark)\.obj$',ref):continue
    source=ROOT/'Assets'/ref;guards.append(source);lines=source.read_bytes().splitlines(keepends=True);vs={};nv=0;paint=None;matches=set()
    for i,line in enumerate(lines):
        if line.startswith(b'v '):nv+=1;vs[nv]=line[2:].strip()
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f '):
            key=(paint,frozenset(vs[int(t.split(b'/')[0])] for t in line.split()[1:]))
            if remaining[key]>0:remaining[key]-=1;matches.add(i)
    if not matches:continue
    name='base_'+source.name
    (MODEL/name).write_bytes(b''.join(line for i,line in enumerate(lines) if i not in matches));text=text.replace(ref,RES+'/'+name);removed+=len(matches)
assert not +remaining,sum((+remaining).values())
(MODEL/'materials.mtl').write_bytes((ROOT/'Assets/models/maps/belltower/compiler-safe/west/materials.mtl').read_bytes())
(MODEL/'west_without_lantern.vmdl').write_text(text);(MODEL/'west_baseline.vmdl').write_bytes(public.read_bytes())
guards += [ROOT/'Assets/scenes/maps/Belltower/belltower.scene',*[ROOT/'Assets'/v for v in MAPS.values()]]
report={'revision':'belltower-well-frame-v2','review_only':True,'files':{p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},'guards':{p.relative_to(ROOT).as_posix():sha(p) for p in guards},'source_sha256':sha(Path(__file__)),'lod_triangles':lods,'old_triangles':removed}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2))
(HERE/'import.cs.txt').write_text((ROOT/'Sources/Belltower/terracotta-pot-v2/import.cs.txt').read_text().replace('terracotta-pot-v2','well-frame-v2'))
s=(ROOT/'Sources/Belltower/wall-lantern-v2/review.py').read_text().replace('wall-lantern-v2','well-frame-v2').replace('wall_lantern','well_frame')
s=s.replace('new Vector3(475,1850,126)','new Vector3(-1225,0,-48)').replace('0,180,0','0,0,0').replace('new Vector3(445,1910,140)','new Vector3(-1130,-90,100)')
s=s.replace('position=(443,1915,127),target=(475,1858,116),fov=38','position=(-1100,-130,70),target=(-1225,0,30),fov=48')
s=s.replace("path=HERE/'capture.cs.txt';path.write_text(text);return path","text=text.replace('belltower_west.vmdl','belltower_centre.vmdl')\n    path=HERE/'capture.cs.txt';path.write_text(text);return path")
(HERE/'review.py').write_text(s)
print({'lods':lods,'old_triangles':removed})
