"""Matched close-up of the single garden planter; restores the editor camera."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/olive-v2'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',required=True)
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    source=(ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt').read_text()
    source=source.replace('output/veridant/door-obstruction/capture-request.json','output/veridant/olive-v2/capture-request.json')
    target=ROOT/'Sources/Veridant/planter-shrub-v1/capture.cs.txt'
    if target.exists():assert target.read_text()==source
    else:target.write_text(source)
    position=K.to_world((-405,805,237));look=K.to_world((-470,740,188));delta=look-position
    angles=(-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0)
    scene=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
    config={'directory':'planter-shrub-'+args.phase,'name':'planter','width':1100,'height':1000,
            'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),
            'fov':64,'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
