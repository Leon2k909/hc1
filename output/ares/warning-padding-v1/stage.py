"""Patch only the warning rectangle; keep every other atlas pixel intact."""
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import ares_materials as A

OUT=Path(__file__).resolve().parent
STAGE=OUT/'stage'
STAGE.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
material=ROOT/'Assets/materials/ares/ar_signs.vmat'
text=material.read_text()
assert 'TextureColor "materials/ares/ar_signs_color.jpg"' in text
base=ROOT/'Assets/materials/ares/ar_signs_color.jpg'
original=np.array(Image.open(base).convert('RGB'))
assert tuple(original.shape[:2])==(4096,4096)
x,y,w,h=A.SIGN['stripe_warning']
colour=A.T.linear_to_srgb(A.warning_stripe((h,w)))
tile=np.clip(np.rint(colour),0,255).astype(np.uint8)
patched=original.copy();patched[y:y+h,x:x+w]=tile
outside=np.ones(original.shape[:2],bool);outside[y:y+h,x:x+w]=False
assert np.array_equal(original[outside],patched[outside])
target=STAGE/'Assets/materials/ares/ar_signs_color.png'
target.parent.mkdir(parents=True)
Image.fromarray(patched).save(target,optimize=True)
assert np.array_equal(np.array(Image.open(target))[outside],original[outside])
Image.fromarray(original[y:y+h,x:x+w]).save(OUT/'before.png')
Image.fromarray(tile).save(OUT/'after.png')
updated=text.replace('TextureColor "materials/ares/ar_signs_color.jpg"','TextureColor "materials/ares/ar_signs_color.png"',1)
(STAGE/'Assets/materials/ares/ar_signs.vmat').write_text(updated)
files={}
for rel in ('Assets/materials/ares/ar_signs_color.png','Assets/materials/ares/ar_signs.vmat'):
    live=ROOT/rel;backup=OUT/'before'/rel
    if live.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,backup)
    files[rel]={'before':sha(live) if live.exists() else None,'after':sha(STAGE/rel)}
words=A.text_layer((h,w),[('CAUTION  HIGH ENERGY',A.FONT_BOLD,h*.3,w*.5,h*.35,'m',.06,w*.62)])
yy,xx=np.where(words>.1)
padding={'left':int(xx.min()-np.floor(w*.1)-1),'right':int(np.ceil(w*.9)-xx.max()-1),
         'top':int(yy.min()-np.floor(h*.1)-1),'bottom':int(np.ceil(h*.9)-yy.max()-1)}
assert min(padding.values())>=h*.20,padding
manifest={'files':files,'original_atlas_sha256':sha(base),'warning_rect':[x,y,w,h],
          'unchanged_pixels_outside_warning':int(outside.sum()),'text_padding_pixels':padding,
          'source_snippet':inspect.getsource(A.warning_stripe)}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:manifest[k] for k in ('warning_rect','unchanged_pixels_outside_warning','text_padding_pixels')}))
