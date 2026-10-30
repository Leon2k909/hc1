"""Matched native views for the current case shell and hardware redesign."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/cases-v4'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True);parser.add_argument('--tone',choices=('olive','black'),default='olive')
    parser.add_argument('--view',choices=('stack','end','detail'),default='stack')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    rows=json.loads((ROOT/'output/veridant/cases-v3/placements.json').read_text())
    case=next(r for r in rows if r['seed']==(95 if args.tone=='olive' else 96) and r['z0']==0.)
    centre=np.array((*case['centre'],0.));f=np.array((*case['along'],0.));s=np.cross((0,0,1),f)
    if args.view=='stack':
        eye=centre+f*32-s*95+np.array((0,0,57));target=centre-s*3+np.array((0,0,23));fov=48
    elif args.view=='end':
        eye=centre+f*62-s*40+np.array((0,0,36));target=centre+f*15+np.array((0,0,12));fov=48
    else:
        eye=centre+f*11-s*38+np.array((0,0,21));target=centre+f*4-s*(case['size'][1]/2-.45)+np.array((0,0,14.5));fov=54
    eye=K.to_world(eye);target=K.to_world(target);delta=target-eye
    angles=(-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0.)
    config={'directory':'cases-v4-'+args.phase,'name':args.tone+'-'+args.view,'width':1200,'height':1100,
            'position':','.join(map(str,eye)),'angles':','.join(map(str,angles)),
            'fov':fov,'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n');print(json.dumps(config))


if __name__=='__main__':main()
