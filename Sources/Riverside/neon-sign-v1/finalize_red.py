from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/neon-sign-v1';MAT=REVIEW/'Assets/materials/riverside/neon-sign-v1'
q=np.abs(np.linspace(-1,1,256));hot=np.clip((q-.25)/.75,0,1)**2;rgb=np.stack([np.full(256,255),30+hot*200,10+hot*165],axis=1)
Image.fromarray(np.repeat(rgb[None,:,:],64,axis=0).astype('uint8')).save(MAT/'neon_red_color.png')
p=MAT/'neon_red.vmat';s=(MAT/'tube_glow.vmat').read_text(encoding='utf-8').replace('tube_color.png','neon_red_color.png').replace('g_flSelfIllumBrightness "18.0"','g_flSelfIllumBrightness "8.0"');p.write_text(s,encoding='utf-8')
p=REVIEW/'Assets/models/maps/riverside/neon-sign-v1/neon_sign.vmdl';p.write_text(p.read_text(encoding='utf-8').replace('/tube_glow.vmat','/neon_red.vmat'),encoding='utf-8')
p=HERE/'build.py';s=p.read_text(encoding='utf-8').replace('(q-.62)/.38','(q-.25)/.75').replace('tube_color.png','neon_red_color.png').replace("mat('tube_glow'","mat('neon_red'").replace('g_flSelfIllumBrightness "18.0"','g_flSelfIllumBrightness "8.0"').replace("MAT+'/tube_glow.vmat'","MAT+'/neon_red.vmat'");p.write_text(s,encoding='utf-8')
p=HERE/'check-materials.cs.txt';p.write_text(p.read_text(encoding='utf-8').replace('/tube_glow.vmat','/neon_red.vmat'),encoding='utf-8')
p=OUT/'manifest.json';m=json.loads(p.read_text());m['files']={f.relative_to(REVIEW).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for folder in (REVIEW/'Assets/models/maps/riverside/neon-sign-v1',MAT) for f in folder.iterdir() if f.is_file()};p.write_text(json.dumps(m,indent=2),encoding='utf-8')
