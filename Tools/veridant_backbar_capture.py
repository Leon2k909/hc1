"""Match the user's current cafe bottle-display view, restoring editor state."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/backbar-v1'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',required=True)
    parser.add_argument('--detail',action='store_true')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    text=(ROOT/'Sources/Veridant/editor/capture-door-obstruction.cs.txt').read_text()
    text=text.replace('output/veridant/door-obstruction/capture-request.json','output/veridant/backbar-v1/capture-request.json')
    script=ROOT/'Sources/Veridant/backbar-v1/capture.cs.txt'
    if script.exists():assert script.read_text()==text
    else:script.write_text(text)
    raw=json.loads((OUT/'start-camera/get_editor_camera.json').read_text())
    camera=next(json.loads(c['text']) for c in raw['content'] if c['type']=='text')
    if args.detail:camera={'Position':'-39.2,673,44.5','Angles':'0,90,0','FieldOfView':50}
    config={'directory':'backbar-v1-'+args.phase,'name':'label-detail' if args.detail else 'cafe','width':1300,'height':800,
            'position':camera['Position'],'angles':camera['Angles'],'fov':camera['FieldOfView'],
            'exposure':2.2,'settle_ms':3000,
            'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n');print(json.dumps(config))


if __name__=='__main__':main()
