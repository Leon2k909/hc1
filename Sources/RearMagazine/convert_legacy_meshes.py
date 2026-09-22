"""Preserve the SCAR's old static SMD attachments in the current ModelDoc OBJ format."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'Assets/attachments/rear_mag/legacy';out.mkdir(parents=True,exist_ok=True)
sources={'reflex':'attachments/swb/sight/reflex/w_reflex_sight.smd','silencer':'attachments/swb/muzzle/silencer_rifle/silencer_rifle.smd'}
for name,source in sources.items():
    lines=(ROOT/'Assets'/source).read_text().splitlines();i=lines.index('triangles')+1;obj=[f'mtllib {name}.mtl'];materials=set();index=1
    while lines[i].strip()!='end':
        mat=Path(lines[i].strip()).stem.lower();materials.add(mat);obj.append('usemtl '+mat);i+=1
        for _ in range(3):
            a=lines[i].split();i+=1;x,y,z,nx,ny,nz,u,v=map(float,a[1:9])
            # Source SMD's XY basis is rotated relative to ModelDoc's OBJ basis.
            x,y,nx,ny=-y,x,-ny,nx
            obj.extend([f'v {y} {z} {x}',f'vt {u} {v}',f'vn {ny} {nz} {nx}'])
        obj.append('f '+' '.join(f'{j}/{j}/{j}' for j in range(index,index+3)));index+=3
    (out/f'{name}.obj').write_text('\n'.join(obj)+'\n')
    (out/f'{name}.mtl').write_text('\n'.join(f'newmtl {m}\nKd 1 1 1\n' for m in sorted(materials)))
for variant in ['v_scarh','v_scarh_gunsmith','w_scarh']:
    path=ROOT/f'Assets/Weapons/swb/scarh/{variant}.vmdl';text=path.read_text()
    for name,source in sources.items():text=text.replace('"'+source+'"',f'"attachments/rear_mag/legacy/{name}.obj"')
    path.write_text(text,encoding='utf-8')
print('SCAR legacy attachment geometry converted to OBJ; source SMD files preserved')
