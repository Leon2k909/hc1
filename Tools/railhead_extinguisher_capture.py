"""Prepare matched native captures of Railhead's replacement extinguisher."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import map_kit as K
import railhead_dress_detail as D
import railhead_station as S

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/railhead/extinguisher-v2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=('front','oblique','east','east-close','bridge','bridge-close','hero'),required=True)
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    source = (ROOT/'Sources/Belltower/editor/capture-stone-wear-v1.cs.txt').read_text()
    source = source.replace('belltower','railhead').replace('Belltower','Railhead')
    source = source.replace('output/railhead/edge-realism-v1/capture-request.json','output/railhead/extinguisher-v2/capture-request.json')
    source = source.replace('capture-stone-wear-v1.cs.txt','capture-extinguisher-v2.cs.txt')
    helper = ROOT/'Sources/Railhead/editor/capture-extinguisher-v2.cs.txt'
    helper.parent.mkdir(parents=True,exist_ok=True)
    if helper.exists(): assert helper.read_text() == source
    else: helper.write_text(source)
    side = 1 if args.view.startswith('east') else -1
    n = -262 if args.view.startswith('bridge') else 228
    z = S.DECK_Z if args.view.startswith('bridge') else 0
    frame = D.Frame(side*(S.WALL_IN-.5),n,z,'-e' if side>0 else '+e')
    close = args.view in ('hero','bridge-close','east-close')
    position = K.to_world(frame.p(48 if args.view=='oblique' else 17,60 if close else 86,40 if close else 43))
    target = K.to_world(frame.p(0,3.9,40))
    delta = target-position
    angles = (-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0)
    scene = ROOT/'Assets/scenes/maps/Railhead/railhead.scene'
    config = {'directory':'extinguisher-v2-'+args.phase,'name':args.view,'width':1200,'height':1500,
              'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),
              'fov':42,'exposure':1.0,'settle_ms':3000,
              'expected_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__': main()
