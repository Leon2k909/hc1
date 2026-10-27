"""Capture the promenade bench at matched, restored native camera poses."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import veridant_parts as P

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/bench-v2'
SOURCE=ROOT/'Sources/Veridant/bench-v2'
POSES={
    'overview':('-514,1545,69','40.173,58.284,0',65,1400,950),
    'detail':('-525,1580,32','28.9,41.4,0',52,1300,900),
    'eye':('-528,1535,64','33.8,53.55,0',65,1400,950),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=POSES,default='overview')
    parser.add_argument('--snapshot',action='store_true')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    OUT.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
    if args.snapshot:
        target=SOURCE/'previous-bench.py'
        assert not target.exists()
        target.write_text('import numpy as np\nfrom riverdale_parts import unit, v, obox, UP, STONE\n\n'+inspect.getsource(P.bench))
    helper=ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt'
    script=helper.read_text().replace('output/veridant/door-obstruction/capture-request.json',
                                    'output/veridant/bench-v2/capture-request.json')
    target=SOURCE/'capture.cs.txt'
    if target.exists():assert target.read_text()==script
    else:target.write_text(script)
    pos,angles,fov,width,height=POSES[args.view]
    request={'directory':'bench-v2-'+args.phase,'name':args.view,'width':width,'height':height,
             'position':pos,'angles':angles,'fov':fov,'exposure':2.2,'settle_ms':2500,
             'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(request,indent=2)+'\n')
    print(json.dumps(request))


if __name__=='__main__':main()
