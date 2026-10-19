import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tools'))
import numpy as np
from PIL import Image
from scipy import ndimage,signal
import terrain_textures as T
rgb=np.asarray(Image.open(ROOT/'Assets/materials/lowtide/lt_brick_v2_color.png'),np.float32)/255
clay=T.smoothstep(.1,.25,(rgb[...,0]-rgb[...,1])/np.maximum(rgb[...,0],.05))
mortar=1-clay
profile=ndimage.gaussian_filter1d(mortar.mean(axis=1),1.8,mode='wrap')
extended=np.tile(profile,3)
rows,props=signal.find_peaks(extended,distance=60,prominence=.12,width=(2,30))
rows=rows[(rows>=2048)&(rows<4096)]-2048
print('beds',rows.tolist(),flush=True)
for a,b in zip(rows,np.r_[rows[1:],rows[0]+2048]):
    indices=np.arange(round(a+(b-a)*.3),round(a+(b-a)*.7))%2048
    p=ndimage.gaussian_filter1d(mortar[indices].mean(axis=0),3,mode='wrap')
    peaks,properties=signal.find_peaks(np.tile(p,3),distance=180,prominence=.15,width=(2,45))
    peaks=peaks[(peaks>=2048)&(peaks<4096)]-2048
    print(int(a),peaks.tolist(),flush=True)
