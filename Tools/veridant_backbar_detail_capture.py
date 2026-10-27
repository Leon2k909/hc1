"""Prepare a reproducible native capture without changing the saved map."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/backbar-v2'
VIEWS={
    'cafe':('18.4844,615.8751,68.8968','0.650632143,93.8596115,0',80,1600,1000),
    'niche':('10,647,52','0,90,0',56,1500,1100),
    'bottles':('-26,650,78','0,90,0',40,1500,1100),
    'angle':('90,602,65','8,132,0',70,1600,1100),
}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',required=True)
    ap.add_argument('--view',choices=VIEWS,default='cafe')
    ap.add_argument('--settle-ms',type=int,default=3000);args=ap.parse_args()
    assert 0<=args.settle_ms<=5000
    assert args.phase.replace('-','').isalnum()
    position,angles,fov,width,height=VIEWS[args.view]
    config={'directory':'backbar-v2-'+args.phase,'name':args.view,'width':width,'height':height,
            'position':position,'angles':angles,'fov':fov,'exposure':2.2,'settle_ms':args.settle_ms,
            'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
