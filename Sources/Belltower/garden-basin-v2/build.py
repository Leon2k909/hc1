from geometry import *
RES='models/maps/belltower/garden-basin-v2';OUT=Path(tempfile.gettempdir())/'belltower-garden-basin-v2';STAGE=OUT/'stage';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
lods=[]
for i in range(3):lods.append(K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}'))
L.RES=RES;L.MAPS=MAPS;(MODEL/'garden_basin.vmdl').write_text(L.modeldoc())
old=K.Model();B.ring(old,(-1100,-1365),22,32,-48,-16,10,{'outside':'rubble','inside':'rubble','top':'ashlar_grey'});old.cylinder((-1100,-1365),22,-42,-41,{'top':'water'},sides=10,turn=math.pi/10)
remaining=Counter(geometry(old));removed=0
public=ROOT/'Assets/models/maps/belltower/belltower_west.vmdl';text=public.read_text();guards=[public]
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text):
    if not re.search(r'_(rubble|ashlar_grey|water)\.obj$',ref):continue
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
report={'revision':'belltower-garden-basin-v2','review_only':True,'files':{p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},'guards':{p.relative_to(ROOT).as_posix():sha(p) for p in guards},'source_sha256':sha(Path(__file__)),'lod_triangles':lods,'old_triangles':removed}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2))
(HERE/'import.cs.txt').write_text((ROOT/'Sources/Belltower/terracotta-pot-v2/import.cs.txt').read_text().replace('terracotta-pot-v2','garden-basin-v2'))
s=(ROOT/'Sources/Belltower/wall-lantern-v2/review.py').read_text().replace('wall-lantern-v2','garden-basin-v2').replace('wall_lantern','garden_basin')
s=s.replace('new Vector3(475,1850,126)','new Vector3(-1365,1100,-48)').replace('0,180,0','0,0,0').replace('new Vector3(445,1910,140)','new Vector3(-1270,990,80)')
s=s.replace('position=(443,1915,127),target=(475,1858,116),fov=38','position=(-1275,1000,35),target=(-1365,1100,-28),fov=40')
s=s.replace("path=HERE/'capture.cs.txt';path.write_text(text);return path","text=text.replace('belltower_west.vmdl','belltower_west.vmdl')\n    path=HERE/'capture.cs.txt';path.write_text(text);return path")
(HERE/'review.py').write_text(s)
print({'lods':lods,'old_triangles':removed})
