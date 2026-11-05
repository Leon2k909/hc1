from pathlib import Path
p=Path(__file__).parent/'prepare_install.py';s=p.read_text()
s=s.replace("dst=STAGE/src.relative_to(REVIEW)","dst=STAGE/f'Assets/models/maps/riverside/roof-ladder-v1/installed_lod{i}.obj'")
s=s.replace("dst.write_bytes(src.read_bytes())",'''lines=[]
    for line in src.read_text().splitlines():
        if line.startswith('v '):
            x,y,z=map(float,line.split()[1:]);line=f'v {z-697:.3f} {y+96:.3f} {407-x:.3f}'
        elif line.startswith('vn '):
            x,y,z=map(float,line.split()[1:]);line=f'vn {z:.3f} {y:.3f} {-x:.3f}'
        elif line.startswith('mtllib '):line=f'mtllib installed_lod{i}.mtl'
        lines.append(line)
    dst.write_text('\\n'.join(lines)+'\\n')''')
s=s.replace('filename="models/maps/riverside/roof-ladder-v1/ladder_lod{i}.obj"','filename="models/maps/riverside/roof-ladder-v1/installed_lod{i}.obj"').replace('import_translation=[407,-697,96] import_rotation=[0,90,0]','import_translation=[0,0,0] import_rotation=[0,0,0]')
p.write_text(s,encoding='utf-8')
