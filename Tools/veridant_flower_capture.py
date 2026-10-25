"""Matched views of the pergola planting, restoring the existing editor view."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/pergola-flowers-v2'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=('front','angle'),default='front')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    folder=ROOT/'Sources/Veridant/pergola-flowers-v2';folder.mkdir(parents=True,exist_ok=True)
    text=(ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt').read_text()
    text=text.replace('output/veridant/door-obstruction/capture-request.json','output/veridant/pergola-flowers-v2/capture-request.json')
    script=folder/'capture.cs.txt'
    if script.exists():assert script.read_text()==text
    else:script.write_text(text)
    eye,target=((-460,-1000,104),(-460,-1180,92)) if args.view=='front' else ((-625,-1018,108),(-460,-1180,92))
    p=K.to_world(eye);d=K.to_world(target)-p
    angles=(-math.degrees(math.atan2(d[2],math.hypot(*d[:2]))),math.degrees(math.atan2(d[1],d[0])),0)
    scene=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
    config={'directory':'pergola-flowers-v2-'+args.phase,'name':args.view,'width':1440,'height':960,
            'position':','.join(map(str,p)),'angles':','.join(map(str,angles)),
            'fov':68,'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
