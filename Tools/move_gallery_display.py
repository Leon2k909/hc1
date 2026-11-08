from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
src=root/'Assets/models/maps/cerroblanco'
dst=root/'output/cerroblanco/display-clearance-v1/stage'
dst.mkdir(parents=True,exist_ok=True)
for p in src.glob('cerroblanco_fitout*'):
    if p.suffix not in ('.obj','.mtl','.vmdl'): continue
    if 'fine' in p.name: continue
    text=p.read_text()
    if p.suffix=='.obj':
        lines=[]; count=0
        for line in text.splitlines():
            if line.startswith('v '):
                e,z,n=map(float,line.split()[1:])
                if -1296.1<=e<=-1251.9 and 179.9<=z<=234.1 and 20.9<=n<=47.1:
                    line=f'v {e-170:.3f} {z:.3f} {n:.3f}'; count+=1
            lines.append(line)
        text='\n'.join(lines)+'\n'
        print(p.name,count)
    if p.suffix=='.vmdl':
        text=text.replace('models/maps/cerroblanco/cerroblanco_fitout','models/maps/cerroblanco/display-clearance-v1/cerroblanco_fitout')
        text=text.replace('34.0000, -1274.0000, 197.0000','34.0000, -1444.0000, 197.0000')
    (dst/p.name).write_text(text)
