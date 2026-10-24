"""Prepare water-only review views; use a private request and capture helper."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/fountain-water-v3'
HELPER=ROOT/'Sources/Belltower/editor/capture-fountain-water-v3.cs.txt'


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=['stream','impact','overview'],required=True)
    parser.add_argument('--settle-ms',type=int,default=3500,
                        help='Viewport settling; use 0 for a synchronous saved-scene render during play.')
    args=parser.parse_args()
    assert 0<=args.settle_ms<=5000
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    text=(ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt').read_text()
    text=text.replace('output/belltower/fountain-ornaments-v2/capture-request.json',
                      'output/belltower/fountain-water-v3/capture-request.json')
    text=text.replace('Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt',
                      'Sources/Belltower/editor/capture-fountain-water-v3.cs.txt')
    if HELPER.exists(): assert HELPER.read_text()==text
    else: HELPER.write_text(text)
    position,target,fov={'stream':((85,-120,76),(130,-52,34),48),
                         'impact':((113,-105,50),(130,-72,21.5),40),
                         'overview':((-220,-370,186),(130,0,110),58)}[args.view]
    d=[b-a for a,b in zip(position,target)]
    angles=(-math.degrees(math.atan2(d[2],math.hypot(*d[:2]))),math.degrees(math.atan2(d[1],d[0])),0)
    request={'directory':'fountain-water-v3-'+args.phase,'name':args.view,'width':1600,'height':1200,
             'fov':fov,'exposure':1.,'settle_ms':args.settle_ms,'position':','.join(map(str,position)),
             'angles':','.join(map(str,angles)),
             'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest()}
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'capture-request.json').write_text(json.dumps(request,indent=2)+'\n')
    print(json.dumps(request))


if __name__=='__main__': main()
