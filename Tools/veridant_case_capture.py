"""Matched views of the olive case stack in the operations hall."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/cases-v3'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',required=True)
    parser.add_argument('--tone',choices=('olive','black'),default='olive')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    text=(ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt').read_text()
    text=text.replace('output/veridant/door-obstruction/capture-request.json','output/veridant/cases-v3/capture-request.json')
    script=ROOT/'Sources/Veridant/cases-v3/capture.cs.txt'
    if script.exists():assert script.read_text()==text
    else:script.write_text(text)
    rows=json.loads((OUT/'placements.json').read_text())
    case=next(r for r in rows if r['seed']==(95 if args.tone=='olive' else 96) and r['z0']==0.)
    centre=np.array((*case['centre'],0.));f=np.array((*case['along'],0.));s=np.cross((0,0,1),f)
    eye=centre+f*32-s*95+np.array((0,0,57));target=centre-s*3+np.array((0,0,23))
    eye=K.to_world(eye);target=K.to_world(target);delta=target-eye
    angles=(-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0.)
    config={'directory':'cases-v3-'+args.phase,'name':args.tone+'-stack','width':1100,'height':1000,
            'position':','.join(map(str,eye)),'angles':','.join(map(str,angles)),
            'fov':48,'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n');print(json.dumps(config))


if __name__=='__main__':main()
