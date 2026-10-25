"""Matched native views of the three west bar doorways; restore the editor view."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/door-obstruction'
VIEWS={'cafe-south':-80.,'cafe-north':100.,'lounge':-390.}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=VIEWS,required=True)
    args=parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    text=(ROOT/'Sources/Railhead/editor/capture-extinguisher-v2.cs.txt').read_text()
    text=text.replace('railhead','veridant').replace('Railhead','Veridant')
    text=text.replace('output/veridant/extinguisher-v2/capture-request.json','output/veridant/door-obstruction/capture-request.json')
    text=text.replace('capture-extinguisher-v2.cs.txt','capture-door-obstruction.cs.txt')
    path=ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt'
    if path.exists():assert path.read_text()==text
    else:path.write_text(text)
    n=VIEWS[args.view]
    position=K.to_world((-810,n+8,60));target=K.to_world((-698,n,48))
    delta=target-position
    angles=(-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0)
    scene=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
    config={'directory':'door-obstruction-'+args.phase,'name':args.view,'width':1100,'height':1300,
            'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),
            'fov':60,'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
