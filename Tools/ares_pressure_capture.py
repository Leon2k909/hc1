"""Native door inspection views, with only synchronous camera/exposure overrides."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import ares_map as A
from boxyard_map import Frame
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/airlock-door-v1'


def placements():
    return [dict(name='wing-west',centre=(-A.WING_E+.5,-60.,0.),facing=(1.,0.),width=180.,height=180.,border=16.),
            dict(name='wing-east',centre=(A.WING_E-.5,-60.,0.),facing=(-1.,0.),width=180.,height=180.,border=16.),
            dict(name='cargo',centre=(0.,A.CON_N0+.5,0.),facing=(0.,1.),width=320.,height=200.,border=20.)]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',required=True)
    ap.add_argument('--view',choices=('cargo','wing-west','wing-east','hardware','angle'),default='cargo');args=ap.parse_args()
    assert args.phase.replace('-','').isalnum()
    spec=next(p for p in placements() if p['name']==(args.view if args.view.startswith('wing') else 'cargo'))
    facing=spec['facing'];f=Frame(*spec['centre'][:2],math.degrees(math.atan2(facing[1],facing[0]))+90,spec['centre'][2])
    if args.view.startswith('wing'):eye=(22,-260,104);target=(0,-5,99);fov=65
    elif args.view=='hardware':eye=(26,-145,60);target=(26,-7,60);fov=61
    elif args.view=='angle':eye=(165,-420,146);target=(0,-5,110);fov=62
    else:eye=(30,-320,118);target=(0,-5,111);fov=62
    position=K.to_world(f.p(*eye));delta=K.to_world(f.p(*target))-position
    pitch=-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2])))
    yaw=math.degrees(math.atan2(delta[1],delta[0]))
    config={'directory':'pressure-door-v2-'+args.phase,'name':args.view,'width':1600,'height':1100,
            'position':','.join(f'{x:.6f}' for x in position),'angles':f'{pitch:.6f},{yaw:.6f},0',
            'fov':fov,'exposure':2.4,'settle_ms':0,
            'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_bytes()).hexdigest()}
    OUT.mkdir(exist_ok=True,parents=True);(OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
