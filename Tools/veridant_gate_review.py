"""Prepare scoped native gate import and state-restoring review captures."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/boundary-wall-v1'
SOURCE=ROOT/'Sources/Veridant/gates-v1'
VIEWS={
    'front':('-300,-1640,104','5,-90,0',65),
    'angle':('-460,-1660,100','5,-57,0',66),
    'detail':('-340,-1790,78','4,-90,0',50),
    'north':('500,-1640,104','5,-90,0',65),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True)
    parser.add_argument('--view',choices=VIEWS,default='front')
    args=parser.parse_args();assert args.phase.replace('-','').isalnum()
    SOURCE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    template=(ROOT/'Sources/Veridant/backbar-v1/import.cs.txt').read_text()
    text=template.replace('output/veridant/backbar-v1','output/veridant/boundary-wall-v1')
    for old,new in (
        ('veridant-backbar-v1','veridant-boundary-wall-v1'),
        ('Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj',
         'Assets/models/maps/veridant/chair-v2/dress-base.obj'),
        ('Assets/models/maps/veridant/veridant_buildings.vmdl','Assets/models/maps/veridant/veridant_dress.vmdl'),
        ('Assets/materials/veridant/backbar-v1/','Assets/materials/veridant/gates-v1/'),
        ('Assets/models/maps/veridant/backbar-v1/','Assets/models/maps/veridant/gates-v1/'),
        ('SectionsUpdated=3,Bottles=manifest["bottles"].GetValue<int>()','GatesUpdated=2'),
        ('.backbar-incoming','.gates-incoming'),
        ('// Publish the shelf-only extraction and three independent back-bar imports.',
         '// Publish only the two closed forecourt gate assemblies.')):
        assert old in text,old
        text=text.replace(old,new)
    target=SOURCE/'import.cs.txt'
    if target.exists():assert target.read_text()==text
    else:target.write_text(text)
    text=(ROOT/'Sources/Veridant/backbar-v1/capture.cs.txt').read_text().replace(
        'output/veridant/backbar-v1/capture-request.json','output/veridant/boundary-wall-v1/capture-request.json')
    target=SOURCE/'capture.cs.txt'
    if target.exists():assert target.read_text()==text
    else:target.write_text(text)
    position,angles,fov=VIEWS[args.view]
    config={'directory':'gates-v1-'+args.phase,'name':args.view,'width':1600,'height':1100,
        'position':position,'angles':angles,'fov':fov,'exposure':2.2,'settle_ms':3000,
        'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config))


if __name__=='__main__':main()
