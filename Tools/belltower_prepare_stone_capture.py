"""Matched native views for the stone-edge audit; restore the user's viewport."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/edge-realism-v1'
VIEWS = {
    'street-trough': ((45,1510,72),(-73,1455,20),58),
    'spawn-trough': ((465,2150,75),(380,2275,20),60),
    'fountain-rim': ((30,-190,82),(130,-88,27),62),
    'fountain-overview': ((-220,-370,186),(130,0,110),58),
    'market-steps': ((1060,-190,90),(1275,0,25),64),
    'market-steps-clear': ((1130,-150,90),(1275,0,25),70),
    'market-steps-street': ((1260,-220,100),(1275,0,22),68),
    'church-tomb': ((-805,485,65),(-700,560,20),60),
    'gate-corner': ((-380,2150,340),(-150,2345,300),65),
    'east-trough': ((45,-1510,72),(-73,-1455,20),58),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True)
    parser.add_argument('--view', choices=VIEWS, required=True)
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    source = (ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt').read_text()
    source = source.replace('output/belltower/fountain-ornaments-v2/capture-request.json',
                            'output/belltower/edge-realism-v1/capture-request.json')
    source = source.replace('Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt',
                            'Sources/Belltower/editor/capture-stone-wear-v1.cs.txt')
    helper = ROOT/'Sources/Belltower/editor/capture-stone-wear-v1.cs.txt'
    if helper.exists(): assert helper.read_text() == source
    else: helper.write_text(source)
    position,target,fov = VIEWS[args.view]
    delta = [b-a for a,b in zip(position,target)]
    angles = (-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),
              math.degrees(math.atan2(delta[1],delta[0])),0)
    scene = ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
    config = {'directory':'edge-realism-v1-'+args.phase,'name':args.view,'width':1600,'height':1100,
              'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),
              'fov':fov,'exposure':1.0,'settle_ms':3500,
              'expected_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__ == '__main__': main()
