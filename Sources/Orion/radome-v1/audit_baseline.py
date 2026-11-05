"""Confirm the review baseline is the radome actually baked into Orion's current vista."""
from pathlib import Path
from collections import Counter
import sys,json
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import orion_parts as O
import orion_map as R
import orion_backdrop as B
OUT=ROOT/'output/orion/radome-v1'
e,n=B.RADOME;z=float(B.height(np.array([e]),np.array([n]))[0])
old=K.Model();O.radome(old,(e,n,z),340.,200.,16,40);R.configure(old)
scratch=OUT/'baseline-world.obj';K.write_obj(scratch,old,'baseline-world')
def records(path):
    vertices=[];paint='';result=Counter()
    with path.open() as file:
        for line in file:
            if line.startswith('v '):vertices.append(tuple(round(float(x),3) for x in line.split()[1:4]))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f '):
                face=tuple(sorted(vertices[int(t.split('/')[0])-1] for t in line.split()[1:]))
                result[(paint,face)]+=1
    return result
wanted=records(scratch);actual=records(ROOT/'Assets/models/maps/orion/orion_vista.obj')
assert sum(wanted.values())==1812 and not +(wanted-actual),'Generated baseline differs from current map'
audit=json.loads((OUT/'existing-model-audit.json').read_text());audit.update(current_baked_faces_matched=1812,current_position_plan=[e,n,z],baseline_matches_actual_map=True)
(OUT/'existing-model-audit.json').write_text(json.dumps(audit,indent=2))
scratch.unlink();scratch.with_suffix('.mtl').unlink();print(json.dumps(audit,indent=2))
