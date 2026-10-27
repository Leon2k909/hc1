"""Reproducible spa-window views using the existing restored native camera helper."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/spa-windows-v2'
VIEWS={
    'front':{'position':'440,-380,305','angles':'0,0,0','fov':80,'width':1440,'height':850},
    'angle':{'position':'594,-115,303','angles':'0,-42,0','fov':72,'width':1280,'height':900},
    'west':{'position':'840,376,264','angles':'0,-90,0','fov':70,'width':1100,'height':1000},
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True);parser.add_argument('--view',choices=VIEWS,default='front')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    OUT.mkdir(parents=True,exist_ok=True)
    text=(ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt').read_text()
    text=text.replace('output/veridant/door-obstruction/capture-request.json',
                      'output/veridant/spa-windows-v2/capture-request.json')
    script=ROOT/'Sources/Veridant/spa-windows-v2/capture.cs.txt';script.parent.mkdir(parents=True,exist_ok=True)
    if script.exists():assert script.read_text()==text
    else:script.write_text(text)
    config={'directory':'spa-windows-v2-'+args.phase,'name':args.view,**VIEWS[args.view],
            'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
