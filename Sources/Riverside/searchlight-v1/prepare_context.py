from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/riverside/searchlight-v1'
sys.path.insert(0,str(ROOT/'Tools'));import layout
sl,c,a=layout.placement();f=np.array((a[0],a[1],0));f/=np.linalg.norm(f);s=np.cross((0,0,1),f)
def v(a):return 'new Vector3('+','.join(f'{x:.5f}f' for x in a)+')'
views=[('lamp',c+f*70-s*65+np.array((0,0,30)),c+np.array((0,0,-2)),42),
       ('tower',c+f*190-s*180+np.array((0,0,30)),c+np.array((0,0,-28)),55)]
script=(ROOT/'Sources/Riverside/pole-transformer-v1/context.cs.txt').read_text().replace('pole-transformer-v1','searchlight-v1')
start=script.index('    var views = new[] {');end=script.index('    var wanted =',start)
script=script[:start]+'    var views = new[] {\n'+''.join(f'        (Name: "{name}", Eye: {v(eye)}, Target: {v(target)}, Fov: {fov}f),\n' for name,eye,target,fov in views)+'    };\n'+script[end:]
(HERE/'context.cs.txt').write_text(script)
p=OUT/'context';p.mkdir(exist_ok=True)
if not (p/'config.json').exists():(p/'config.json').write_text(json.dumps(dict(phase='before',width=1440,height=1000,settle_frames=35,stream_frames=35),indent=2))
