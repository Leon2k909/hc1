"""Capture the existing garden lounger with a matched, restored editor camera."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/lounger-v3'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=('garden','deck','roof'),default='garden')
    args=parser.parse_args()
    assert args.phase.replace('-','').isalnum()
    text=(ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt').read_text()
    text=text.replace('output/veridant/door-obstruction/capture-request.json','output/veridant/lounger-v3/capture-request.json')
    target=ROOT/'Sources/Veridant/lounger-v3/capture.cs.txt'
    if target.exists():assert target.read_text()==text
    else:target.write_text(text)
    views={'garden':((-506,287,182),(-439,340,142)),
           'deck':((-480,-212,184),(-559,-150,142)),
           'roof':((980,-160,248),(1060,-100,206))}
    eye,target_point=views[args.view]
    position=K.to_world(eye);look=K.to_world(target_point);delta=look-position
    angles=(-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0)
    scene=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
    config={'directory':'lounger-v3-'+args.phase,'name':args.view,'width':1200,'height':900,
            'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),
            'fov':53,'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
