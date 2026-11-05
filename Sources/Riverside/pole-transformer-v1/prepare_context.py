from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/riverside/pole-transformer-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import layout
spec=layout.placements()[1];c=spec['centre'];f=spec['facing'];r=np.cross(f,(0,0,1))
def v(a):return 'new Vector3('+','.join(f'{x:.5f}f' for x in a)+')'
views=[('pole',c-r*100-f*120+np.array((0,0,35)),c+np.array((0,0,20)),62),('tank',c+r*44-f*74+np.array((0,0,20)),c+np.array((0,0,6)),64)]
s=(ROOT/'Sources/Spillway/editor/capture.cs.txt').read_text()
s=s.replace('output/spillway/captures','output/riverside/pole-transformer-v1/context').replace('Assets/scenes/maps/Spillway/spillway.scene','Assets/scenes/maps/riverside/riverside.scene')
s=s.replace('"Sun", "Sky", "Sky Fill", "Fog", "Look", "Spillway", "Lights", "Reflection Probes", "Volumetric Fog"','"Moon", "Sky", "Sky Fill", "Fog", "Look", "Riverside", "Lights", "Reflection Probes", "Volumetric Fog"')
start=s.index('    var views = new[] {');end=s.index('    var wanted =',start)
s=s[:start]+'    var views = new[] {\n'+''.join(f'        (Name: "{name}", Eye: {v(eye)}, Target: {v(target)}, Fov: {fov}f),\n' for name,eye,target,fov in views)+'    };\n'+s[end:]
s=s.replace('view.Name + ".png"','view.Name + "-" + configuration["phase"].GetValue<string>() + ".png"')
s=s.replace('g.Parent.Name == "Spillway"','g.Parent.Name == "Riverside"')
(HERE/'context.cs.txt').write_text(s)
p=OUT/'context';p.mkdir(exist_ok=True)
(p/'config.json').write_text(json.dumps(dict(phase='before',width=1440,height=1000,settle_frames=35,stream_frames=35),indent=2))
