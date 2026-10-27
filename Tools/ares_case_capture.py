"""Prepare matched, native captures of the installed Ares transport cases."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/crate-v2'
VIEWS={
    'hall-stack':((-452.,-190.,76.),(-560.,-300.,30.),50.),
    'player':((-452.,-190.,64.),(-560.,-300.,30.),80.),
    'hardware':((-492.,-240.,76.),(-560.,-300.,46.),40.),
    'cargo':((-1320.,380.,104.),(-1460.,260.,44.),45.),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True);parser.add_argument('--view',choices=VIEWS,default='hall-stack')
    parser.add_argument('--lod',type=int,choices=(0,1,2))
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    eye,target,fov=VIEWS[args.view];eye=K.to_world(eye);delta=K.to_world(target)-eye
    pitch=math.degrees(math.atan2(-delta[2],np.linalg.norm(delta[:2])));yaw=math.degrees(math.atan2(delta[1],delta[0]))
    if args.view=='hall-stack':pitch,yaw=16.62,135.53
    data={'directory':args.phase,'name':args.view+('' if args.lod is None else '-lod'+str(args.lod)),
          'width':1200,'height':950,'position':K.vec(eye),'angles':K.vec((pitch,yaw,0.)),
          'fov':fov,'exposure':2.6,'settle_ms':3000,
          'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_bytes()).hexdigest()}
    if args.lod is not None:data['case_lod']=args.lod
    (OUT/'capture-request.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data))


if __name__=='__main__':main()
