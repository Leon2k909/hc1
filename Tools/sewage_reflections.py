"""Convert six native camera captures into a linear-light reflection panorama.

The normal sky texture asset compiler performs the cubemap conversion. This
avoids runtime envmap_filtering_cs, which faults on the workstation's driver.
Run after Sources/Sewage/editor/capture-reflection-faces.cs.txt for all six faces.
"""
from pathlib import Path
import argparse, ast, json, struct, zlib
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def write_exr(path,rgb):
    # Reuse the project's verified standalone EXR writer without importing its
    # unrelated procedural sky generation and optional numba dependencies.
    source=ast.parse((ROOT/'Tools/belltower_sky.py').read_text(encoding='utf-8'))
    writer=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='write_exr')
    namespace={'np':np,'struct':struct,'zlib':zlib}
    exec(compile(ast.Module(body=[writer],type_ignores=[]),'belltower_exr_writer','exec'),namespace)
    namespace['write_exr'](path,rgb)


def panorama(index):
    capture=ROOT/'output/sewage/reflections'/str(index)
    h,w=512,1024
    lat=(.5-(np.arange(h,dtype=np.float32)+.5)/h)*np.pi
    lon=-(np.arange(w,dtype=np.float32)+.5)/w*2*np.pi
    directions=np.stack(np.broadcast_arrays(np.cos(lat[:,None])*np.cos(lon),np.cos(lat[:,None])*np.sin(lon),np.sin(lat[:,None])),axis=-1)
    best=np.full((h,w),-1,np.float32)
    result=np.zeros((h,w,3),np.float32)
    for face in range(6):
        meta=json.loads((capture/f'face-{face}.json').read_text())['Faces'][0]
        vector=lambda name:np.array([float(v.strip()) for v in meta[name].split(',')],np.float32)
        forward,right,up=map(vector,['Forward','Right','Up'])
        denominator=directions@forward
        selected=denominator>best
        safe=np.maximum(denominator,1e-5)
        image=np.asarray(Image.open(capture/meta['File']).convert('RGB'),np.float32)/255
        size=image.shape[0]
        u=np.clip(((directions@right)/safe+1)*size/2-.5,0,size-1)
        v=np.clip((1-(directions@up)/safe)*size/2-.5,0,size-1)
        x=u.astype(np.int32);y=v.astype(np.int32)
        x1=np.minimum(x+1,size-1);y1=np.minimum(y+1,size-1)
        a=(u-x)[...,None];b=(v-y)[...,None]
        color=(image[y,x]*(1-a)+image[y,x1]*a)*(1-b)+(image[y1,x]*(1-a)+image[y1,x1]*a)*b
        result[selected]=color[selected];best[selected]=denominator[selected]
    output=ROOT/'output/sewage/stage/materials/sewage/reflections'
    output.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.clip(result*255,0,255).astype(np.uint8)).save(capture/'panorama.png')
    linear=np.where(result<=.04045,result/12.92,((result+.055)/1.055)**2.4)
    write_exr(output/f'reflection_{index}.exr',linear*2)
    (output/f'reflection_{index}.vmat').write_text('"Layer0"\n{\n shader "shaders/sky.shader"\n F_TEXTURE_FORMAT2 "6"\n g_flBrightnessExposureBias "0"\n g_flRenderOnlyExposureBias "0"\n SkyTexture "materials/sewage/reflections/reflection_'+str(index)+'.exr"\n}\n')
    print(f'Probe {index}: six captured faces -> {w}x{h} linear EXR')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('index',type=int,choices=range(3))
    panorama(parser.parse_args().index)
