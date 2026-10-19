"""Verify that saving a new lighting bake changes only its three texture paths."""
from pathlib import Path
import argparse
import json

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('revision')
args=parser.parse_args()
quality=Path('output/belltower/quality')
before=json.loads((quality/args.revision/'visual-scene.json').read_text())
after=json.loads(Path('Assets/scenes/maps/Belltower/belltower.scene').read_text())

def normalize(value):
    if isinstance(value,dict):
        if set(value)=={'Id','Path'}: return value['Path']
        return {key:normalize(item) for key,item in value.items()}
    if isinstance(value,list): return [normalize(item) for item in value]
    return value

differences=[]
def compare(a,b,path=''):
    if a==b: return
    if isinstance(a,dict) and isinstance(b,dict):
        for key in sorted(a.keys()|b.keys()): compare(a.get(key),b.get(key),path+'/'+key)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for index,(x,y) in enumerate(zip(a,b)): compare(x,y,path+'/'+str(index))
    else: differences.append({'path':path,'before':a,'after':b})

compare(normalize(before),normalize(after))
output=quality/(args.revision+'-save')
output.mkdir(exist_ok=True)
(output/'scene-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
expected={key:f'lighting/belltower/{args.revision}/{stem}.vtex' for key,stem in
          [('IrradianceTexture','irradiance'),('DistanceTexture','distance'),('RelocationTexture','relocation')]}
assert len(differences)==3,differences
assert {item['path'].split('/')[-1] for item in differences}==set(expected),differences
assert all(item['after']==expected[item['path'].split('/')[-1]] for item in differences),differences
print('Saved scene differs only in the three accepted indirect-light texture paths.')
