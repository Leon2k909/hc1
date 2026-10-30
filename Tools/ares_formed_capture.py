"""Configure and execute serial, fully restored Ares prop captures."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import numpy as np
from ares_pressure_capture import placements
from boxyard_map import Frame
import map_kit as K

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/ares/pressure-door-v3'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',required=True);ap.add_argument('--trial',action='store_true')
    ap.add_argument('--pid',type=int)
    ap.add_argument('views',nargs='+',choices=('cargo','wing-west','wing-east','hardware','clamp','pressing','angle'));args=ap.parse_args()
    assert args.phase.replace('-','').isalnum()
    for view in args.views:
        spec=next(p for p in placements() if p['name']==(view if view.startswith('wing') else 'cargo'))
        facing=spec['facing'];f=Frame(*spec['centre'][:2],math.degrees(math.atan2(facing[1],facing[0]))+90,spec['centre'][2])
        if view.startswith('wing'):eye=(22,-260,104);target=(0,-5,99);fov=65
        elif view=='hardware':eye=(26,-145,60);target=(26,-7,60);fov=61
        elif view=='clamp':eye=(116,-107,149);target=(150,-7,137);fov=53
        elif view=='pressing':eye=(-68,-145,150);target=(-78,-6,145);fov=53
        elif view=='angle':eye=(165,-420,146);target=(0,-5,110);fov=62
        else:eye=(30,-320,118);target=(0,-5,111);fov=62
        position=K.to_world(f.p(*eye));delta=K.to_world(f.p(*target))-position
        pitch=-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2])));yaw=math.degrees(math.atan2(delta[1],delta[0]))
        config=dict(directory='pressure-door-v3-'+args.phase,name=view,width=1600,height=1100,
            position=','.join(f'{x:.6f}' for x in position),angles=f'{pitch:.6f},{yaw:.6f},0',
            fov=fov,exposure=2.4,settle_ms=0,preserve_unsaved=True,
            expected_scene_sha256=hashlib.sha256((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_bytes()).hexdigest())
        if args.trial:config['trial_model']='models/maps/ares/pressure-doors-v3/trial_hall.vmdl'
        (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
        command=['rtk','proxy',sys.executable,'-X','utf8','output/knife-throw/editor_check.py',
            '--script','Sources/Ares/pressure-doors-v3/capture.cs.txt','--output-dir',
            f'output/ares/pressure-door-v3/capture-{args.phase}-{view}',
            '--timeout','45','--direct-call','--cleanup-exchange']
        if args.pid is not None:command+=['--pid',str(args.pid)]
        subprocess.run(command,cwd=ROOT,check=True)


if __name__=='__main__':main()
