"""Matched native views of the wall-pipe rebuild, preserving the editor camera."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VIEWS={
    'cargo-close':((-1175.,860.,255.),(-1360.,860.,252.),58),
    'cargo-angle':((-1130.,770.,262.),(-1360.,900.,252.),58),
    'wing-close':((-495.,1470.,322.),(-684.,1470.,320.),58),
    'wing-angle':((-470.,1390.,325.),(-684.,1510.,320.),62),
}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',required=True)
    ap.add_argument('--view',choices=VIEWS,default='cargo-close');ap.add_argument('--trial',action='store_true')
    ap.add_argument('--stage',default='stage-v3');args=ap.parse_args()
    assert args.phase.replace('-','').isalnum()
    eye,target,fov=VIEWS[args.view];d=[b-a for a,b in zip(eye,target)]
    config={'directory':'pipework-v1-'+args.phase,'name':args.view,'width':1600,'height':1000,
        'position':','.join(str(x) for x in eye),
        'angles':f'{-math.degrees(math.atan2(d[2],math.hypot(*d[:2]))):.6f},{math.degrees(math.atan2(d[1],d[0])):.6f},0',
        'fov':fov,'exposure':2.4,'settle_ms':0,'preserve_unsaved':True,'stage':args.stage,
        'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_bytes()).hexdigest()}
    # Keep the exact initial comparison projection.
    if args.view=='cargo-close':config['angles']='0.93,180,0'
    if args.trial:config['trial_model']='models/maps/ares/pipework-v1/trial_hall.vmdl'
    (ROOT/'output/ares/pipework-v1/capture-request.json').write_text(json.dumps(config))
    print(json.dumps({'phase':args.phase,'view':args.view,'trial':args.trial}))
if __name__=='__main__':main()
