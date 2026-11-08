from pathlib import Path
s=Path('output/veridant/gallery-frames-v1/prepare.py').read_text().replace('gallery-frames-v1','colonnade-tree-fit-v1').replace('gallery-wall-art-v1','colonnade-tree-fit-v1').replace('wall_art_placement_','tree_fit_').replace('gallery-wall-art','colonnade-tree-fit')
start=s.index('placements=');end=s.index('stage=OUT/',start)
s=s[:start]+'''targets={};counts=Counter()
for name,delta in [('tree',(-7,-7.5,-1.5)),('uplight',(-22,-21,0))]:
    m=K.Model()
    if name=='tree':P.olive(m,(-226,20,22),96,seed=7,spread=.8)
    else:P.uplight(m,'Original colonnade fixture',(-222,20,22.1),light=False)
    V.configure(m);path=OUT/(name+'-original.obj');K.write_obj(path,m,'veridant_buildings')
    for _,key,_ in faces(path.read_text().splitlines()):
        assert key not in targets;targets[key]=(name,tuple(K.to_world(delta)[[1,2,0]]));counts[name]+=1
'''+s[end:]
s=s.replace('sbox.2026.11.06.13.44.48.png','sbox.2026.11.06.17.15.22.png')
s+='''\nimport shutil
oldroot=ROOT/'output/veridant/colonnade-planter-reuse-v1/stage/models/props/shared/colonnade_planter_v1'
alt='models/props/shared/colonnade_bronze_alternative_v1';dest=stage/alt;dest.mkdir(parents=True,exist_ok=True)
for f in oldroot.iterdir():
    if not f.is_file():continue
    data=f.read_bytes()
    if f.suffix=='.vmdl':
        txt=data.decode();assert 'rhp_bronze' in txt;data=txt.replace('models/props/shared/colonnade_planter_v1',alt).encode()
    (dest/f.name).write_bytes(data)
'''
o=Path('output/veridant/colonnade-tree-fit-v1');o.mkdir(exist_ok=True);(o/'prepare.py').write_text(s)
