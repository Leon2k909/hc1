"""Convert six native camera captures into a linear-light reflection panorama.

The normal sky texture asset compiler performs the cubemap conversion. This
avoids runtime envmap_filtering_cs, which faults on the workstation's driver.
Run after Sources/Orion/editor/capture-reflections.cs.txt for all six faces.
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


def decode_aces(rgb,exposure=1.0):
    """Undo the native ACES display encoding for a linear-light texture source."""
    tree=ast.parse((ROOT/'Tools/belltower_sky.py').read_text(encoding='utf-8'))
    wanted={'DESIGN_EXPOSURE','ACES_IN','ACES_OUT'}
    selected=[n for n in tree.body if
              (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in wanted for t in n.targets)) or
              (isinstance(n,ast.FunctionDef) and n.name in {'srgb_linear','undisplay'})]
    namespace={'np':np}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'sky_encoding','exec'),namespace)
    return namespace['undisplay'](rgb,exposure=exposure)


def calibration():
    """Calibrate bitmap radiance against clear zenith sky in the outdoor probe."""
    source=ast.parse((ROOT/'Tools/belltower_sky.py').read_text(encoding='utf-8'))
    reader=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='read_exr')
    namespace={'np':np,'struct':struct,'zlib':zlib,'Path':Path}
    exec(compile(ast.Module(body=[reader],type_ignores=[]),'sky_exr_reader','exec'),namespace)
    sky=namespace['read_exr'](ROOT/'output/orion/stage/materials/orion/sky/orion_sky_v2.exr')
    folder=ROOT/'output/orion/reflections/Yard'
    meta=json.loads((folder/'face-4.json').read_text())['Faces'][0]
    vector=lambda name:np.array([float(v.strip()) for v in meta[name].split(',')])
    forward,right,up=map(vector,['Forward','Right','Up'])
    captured=np.asarray(Image.open(folder/meta['File']).convert('RGB'),float)
    size=captured.shape[0]
    pixels=np.arange(size//2-28,size//2+29,7)
    x,y=np.meshgrid(pixels,pixels)
    direction=forward+right*(2*(x+.5)/size-1)[...,None]+up*(1-2*(y+.5)/size)[...,None]
    direction/=np.linalg.norm(direction,axis=-1,keepdims=True)
    u=(-np.arctan2(direction[...,1],direction[...,0])/(2*np.pi))%1
    v=.5-np.arcsin(np.clip(direction[...,2],-1,1))/np.pi
    sx=np.minimum((u*sky.shape[1]).astype(int),sky.shape[1]-1)
    sy=np.minimum((v*sky.shape[0]).astype(int),sky.shape[0]-1)
    expected=sky[sy,sx]
    observed=decode_aces(captured[y,x],exposure=1.0)
    ratios=expected/np.maximum(observed,1e-5)
    channels=np.median(ratios,axis=(0,1))
    gain=float(np.median(channels))
    spread=float(np.max(np.abs(channels/gain-1)))
    if not .1<gain<10 or spread>.15:
        raise ValueError(f'Unexpected sky radiance calibration: RGB {channels}, gain {gain}')
    report={'Method':'Known zenith sky EXR versus native outdoor probe bitmap',
            'Gain':gain,'RgbGains':channels.tolist(),'ChannelDisagreement':spread,'Samples':int(x.size)}
    (ROOT/'output/orion/reflections/calibration.json').write_text(json.dumps(report,indent=2))
    return gain


def panorama(index):
    capture=ROOT/'output/orion/reflections'/str(index)
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
    output=ROOT/'output/orion/stage/materials/orion/reflections'
    output.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.clip(result*255,0,255).astype(np.uint8)).save(capture/'panorama.png')
    gain=calibration()
    linear=decode_aces(result*255,exposure=1.0)*gain
    write_exr(output/f'reflection_{index}.exr',linear)
    (output/f'reflection_{index}.vmat').write_text('"Layer0"\n{\n shader "shaders/sky.shader"\n F_TEXTURE_FORMAT2 "6"\n g_flBrightnessExposureBias "0"\n g_flRenderOnlyExposureBias "0"\n SkyTexture "materials/orion/reflections/reflection_'+str(index)+'.exr"\n}\n')
    print(f'Probe {index}: six captured faces -> {w}x{h} linear EXR, calibrated gain {gain:.4f}')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('index',choices=('Yard','Control','Service'))
    panorama(parser.parse_args().index)
