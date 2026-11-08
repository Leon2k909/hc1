from pathlib import Path
import math
R=Path(__file__).resolve().parents[1];D=R/'Assets/models/maps/veridant/fountain-rim-v2';D.mkdir(parents=True,exist_ok=True)
profile=[(83.8,14),(83.8,20.6),(84.6,22),(90.6,22),(92,20.6),(92,18.8),(90,18.8),(90,20),(83.8,14)]
out=['mtllib coping.mtl','usemtl limestone'];idx=1;distance=0
for (r,z),(r2,z2) in zip(profile,profile[1:]):
    length=math.hypot(r2-r,z2-z)
    for i in range(256):
        a=i*math.tau/256;b=(i+1)*math.tau/256
        for rr,zz,t,dd in [(r,z,a,distance),(r,z,b,distance),(r2,z2,b,distance+length),(r2,z2,a,distance+length)]:
            x=150+rr*math.sin(t);y=-1600-rr*math.cos(t)
            nx=-(z2-z)*math.sin(t)/length;ny=(z2-z)*math.cos(t)/length;nz=(r2-r)/length
            out.extend([f'v {y} {zz} {x}',f'vt {t*88/36} {dd/36}',f'vn {ny} {nz} {nx}'])
        out.append('f '+' '.join(f'{j}/{j}/{j}' for j in [idx+3,idx+2,idx+1,idx]));idx+=4
    distance+=length
(D/'coping.obj').write_text('\n'.join(out));(D/'coping.mtl').write_text('newmtl limestone\n')
t=(R/'Assets/models/props/shared/veridant_fountain_reference_top/crown.vmdl').read_text()
t=t.replace('models/props/shared/veridant_fountain_reference_top/crown.obj','models/maps/veridant/fountain-rim-v2/coping.obj').replace('reference_bronze.vmat','limestone.vmat').replace('materials/veridant/fountain_limestone.vmat','materials/veridant/fountain_reference_limestone.vmat')
(D/'coping.vmdl').write_text(t)
