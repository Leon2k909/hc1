"""Offline material review; CPU shading, not an engine screenshot or performance test.

Samples the unchanged generated scan on a perspective floor plane with a CPU
equivalent of the staged board layout. Both candidates use matched GGX lighting,
8-tap anisotropic/trilinear sampling and the same cameras. No albedo is edited.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import lowtide_warehouse_floor as F

ROOT, OUT = F.ROOT, F.OUT
VIEWS = {
    'close': dict(eye=(.6,-1.8,1.45),target=(0,1.,0),fov=66),
    'wide': dict(eye=(.4,-5.1,4.3),target=(0,1.6,0),fov=68),
    'grazing': dict(eye=(-.6,-3.0,.48),target=(0,1.7,0),fov=63),
}


def unit(value):
    return value/np.maximum(np.linalg.norm(value,axis=-1,keepdims=True),1e-12)


def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1)
    return t*t*(3-2*t)


def floor_hash(row,block,salt):
    # uint32 wrap matches the shader; use uint64 intermediates without overflow warnings.
    row=np.asarray(row,dtype=np.int64).astype(np.uint64)&0xffffffff
    block=np.asarray(block,dtype=np.int64).astype(np.uint64)&0xffffffff
    h=((row*0x9e3779b9)^(block*0x85ebca6b)^np.uint64(salt))&0xffffffff
    h^=h>>16
    h=(h*0x7feb352d)&0xffffffff
    h^=h>>15
    h=(h*0x846ca68b)&0xffffffff
    return h^(h>>16)


def layout(plane,rects):
    across=(plane[...,1]-260)/10
    row=np.floor(across).astype(np.int64)
    phase=(floor_hash(row,0,107)%3).astype(float)
    q=(plane[...,0]-440)/110+phase
    block=np.floor(q/3).astype(np.int64)
    at=q-block*3
    split=1+(floor_hash(row,block,701)&1).astype(float)
    second=at>=split
    spans=np.where(second,3-split,split)
    along=(at-np.where(second,split,0))/spans
    variation=floor_hash(row,block*2+second.astype(int),419)
    choice=(variation&3).astype(int)
    scan=np.where(spans<1.5,np.asarray(F.SHORT)[choice],np.asarray(F.LONG)[choice])
    direction=np.stack((np.where(variation&16,-1,1),np.where(variation&32,-1,1)),-1)
    local=np.stack((along,across-row),-1)
    rect=np.asarray(rects)[scan]
    uv=rect[...,:2]+(.5+(local-.5)*direction)*rect[...,2:]
    scale=rect[...,2:]*direction/np.stack((110*spans,np.full_like(spans,10)),-1)
    tone=.97+((variation>>8)&255).astype(float)/255*.05
    # Board starts in plan north inches, for structural-support validation.
    start=440+(block*3+np.where(second,split,0)-phase)*110
    return dict(uv=uv,scale=scale,local=local,scan=scan,direction=direction,
                spans=spans,start=start,row=row,tone=tone,q=q)


def mips(path,srgb=False):
    value=np.asarray(Image.open(path),dtype=np.float32)/255
    if value.ndim==2: value=value[...,None]
    value=value[...,:3]
    if srgb: value=np.where(value<=.04045,value/12.92,((value+.055)/1.055)**2.4)
    result=[value]
    while min(value.shape[:2])>1:
        h,w=value.shape[:2]
        value=np.pad(value,((0,h%2),(0,w%2),(0,0)),mode='edge')
        value=(value[::2,::2]+value[1::2,::2]+value[::2,1::2]+value[1::2,1::2])*.25
        result.append(value)
    return result


def bilinear(image,uv,wrap):
    h,w=image.shape[:2]
    xy=uv*np.array((w,h))-.5
    at=np.floor(xy).astype(int)
    weight=xy-at
    x,y=at[:,0],at[:,1]
    if wrap: x0,x1,y0,y1=x%w,(x+1)%w,y%h,(y+1)%h
    else: x0,x1,y0,y1=np.clip(x,0,w-1),np.clip(x+1,0,w-1),np.clip(y,0,h-1),np.clip(y+1,0,h-1)
    a=image[y0,x0]*(1-weight[:,0,None])+image[y0,x1]*weight[:,0,None]
    b=image[y1,x0]*(1-weight[:,0,None])+image[y1,x1]*weight[:,0,None]
    return a*(1-weight[:,1,None])+b*weight[:,1,None]


def sample(chain,uv,dx,dy,wrap=False):
    shape=np.array((chain[0].shape[1],chain[0].shape[0]))
    sx,sy=dx*shape,dy*shape
    a=np.sum(sx*sx,axis=-1); b=np.sum(sy*sy,axis=-1); c=np.sum(sx*sy,axis=-1)
    disc=np.sqrt(np.maximum((a-b)**2+4*c*c,0))
    major=np.sqrt(np.maximum((a+b+disc)*.5,1e-10))
    minor=np.sqrt(np.maximum((a+b-disc)*.5,1e-10))
    lod=np.clip(np.log2(np.maximum(np.maximum(minor,major/8),1)),0,len(chain)-1)
    level=np.floor(lod).astype(int); fraction=lod-level
    # Principal footprint axis in texture space, including grazing camera skew.
    ax=np.sum(np.stack((sx[:,0],sy[:,0]),-1)**2,axis=-1)
    ay=np.sum(np.stack((sx[:,1],sy[:,1]),-1)**2,axis=-1)
    cross=sx[:,0]*sx[:,1]+sy[:,0]*sy[:,1]
    angle=.5*np.arctan2(2*cross,ax-ay)
    axis=np.stack((np.cos(angle),np.sin(angle)),-1)*major[:,None]/shape
    axis*=smooth(1.1,2.,major/np.maximum(minor,1e-5))[:,None]
    output=np.zeros((len(uv),chain[0].shape[-1]),np.float32)
    for k in range(8):
        at=uv+axis*((k+.5)/8-.5)
        color=np.zeros_like(output)
        for lev in np.unique(level):
            mask=level==lev
            lo=bilinear(chain[lev],at[mask],wrap)
            hi=bilinear(chain[min(lev+1,len(chain)-1)],at[mask],wrap)
            color[mask]=lo*(1-fraction[mask,None])+hi*fraction[mask,None]
        output+=color/8
    return output


def material(plane,px,py,side,maps,rects,candidate):
    if not candidate:
        # Lowtide top faces: OBJ U=e/128+offsetU, V=n/128+offsetV.
        # Import flips OBJ V, so the scan's horizontal grain currently runs east/west.
        import zlib
        crc=zlib.crc32(b'lowtide_east')
        offset=np.array(((crc&0xffff)/65535*7,((crc>>16)&0xffff)/65535*7))
        uv=np.stack((plane[:,1]/128+offset[0],1-plane[:,0]/128-offset[1]),-1)
        dx=np.stack((px[:,1],-px[:,0]),-1)/128
        dy=np.stack((py[:,1],-py[:,0]),-1)/128
        color=sample(maps['color'],uv,dx,dy,True)
        raw=unit(sample(maps['normal'],uv,dx,dy,True)*2-1)
        normal=unit(np.stack((raw[:,1],raw[:,0]*side,raw[:,2]),-1))
        rough=sample(maps['rough'],uv,dx,dy,True)[:,0]
        return color,normal,rough,np.ones(len(uv))
    tile=layout(plane,rects)
    uv,scale=tile['uv'],tile['scale']
    dx,dy=px*scale,py*scale
    color=sample(maps['color'],uv,dx,dy)
    raw=unit(sample(maps['normal'],uv,dx,dy)*2-1)
    rough=sample(maps['rough'],uv,dx,dy)[:,0]
    local,spans=tile['local'],tile['spans']
    footprint=(np.abs(px)+np.abs(py))*.0254
    distance=np.minimum(local,1-local)*np.stack((2.794*spans,np.full_like(spans,.254)),-1)
    aa=np.maximum(footprint*.5,.0001)
    coverage=1-smooth(.00125-aa,.00125+aa,distance)
    average=.0025/np.stack((2.794*spans,np.full_like(spans,.254)),-1)
    resolved=1-smooth(.032,.127,footprint)
    gaps=average+(coverage-average)*resolved
    gap=1-(1-gaps[:,0])*(1-gaps[:,1])
    direction=tile['direction']
    normal=np.stack((raw[:,0]*direction[:,0],-raw[:,1]*direction[:,1]*side,raw[:,2]),-1)
    t=np.clip((distance-.00125)/.00175,0,1)
    slope=.0005*6*t*(1-t)/.00175*np.clip(.00175/np.maximum(footprint,.0001),0,1)
    slope*=np.stack((np.where(local[:,0]<.5,1,-1),np.where(local[:,1]<.5,1,-1)*side),-1)
    normal[:,:2]-=slope
    near=np.abs(np.mod((plane[:,0]-440)/110+.5,1)-.5)*2.794
    nail_d=np.maximum(np.abs(near-.018),np.minimum(np.abs(local[:,1]*.254-.045),np.abs(local[:,1]*.254-.209)))
    nail_aa=np.maximum(footprint.max(axis=-1)*.5,.0001)
    nail=(1-smooth(.0018-nail_aa,.0018+nail_aa,nail_d))*(1-smooth(.003,.012,footprint.max(axis=-1)))
    color*=np.asarray(F.TINT)*tile['tone'][:,None]*(1-.73*gap[:,None])*(1-.70*nail[:,None])
    normal=unit(normal*(1-.65*nail[:,None])+np.array((0,0,1))*.65*nail[:,None])
    rough=(rough*(1-gap)+.96*gap)*(1-nail)+.60*nail
    return color,normal,rough,1-.14*gap


def ray_floor(spec,width,height):
    eye,target=np.array(spec['eye']),np.array(spec['target'])
    forward=unit(target-eye)
    right=unit(np.cross(forward,(0,0,1)))
    up=np.cross(right,forward)
    yy,xx=np.mgrid[0:height,0:width]
    sy=(1-2*(yy+.5)/height)*math.tan(math.radians(spec['fov'])/2)
    sx=(2*(xx+.5)/width-1)*math.tan(math.radians(spec['fov'])/2)*width/height
    ray=forward+sx[...,None]*right+sy[...,None]*up
    distance=-eye[2]/np.minimum(ray[...,2],-.0001)
    positions=eye+ray*distance[...,None]
    mask=(ray[...,2]<-.015)&(np.abs(positions[...,0])<9)&(np.abs(positions[...,1])<9)
    return positions,mask,eye


def shade(color,normal,rough,ao,view):
    # Two broad approximating sources; this does not reproduce warehouse DDGI.
    result=color*ao[:,None]*.30
    nview=np.maximum(np.sum(normal*view,axis=-1),.03)
    for direction,radiance in (((-.25,-.5,1),np.array((2.2,2.10,1.91))),((.6,.2,.8),np.array((.31,.37,.46)))):
        light=unit(np.array(direction,dtype=float))
        half=unit(view+light)
        nl=np.maximum(normal@light,0)
        nh=np.maximum(np.sum(normal*half,axis=-1),0)
        vh=np.maximum(np.sum(view*half,axis=-1),0)
        alpha=rough**2; a2=alpha**2
        distribution=a2/(math.pi*(nh*nh*(a2-1)+1)**2+1e-8)
        k=(rough+1)**2/8
        geometry=nl/(nl*(1-k)+k)*nview/(nview*(1-k)+k)
        fresnel=.04+.96*(1-vh)**5
        spec=distribution*geometry*fresnel/(4*nl*nview+1e-6)
        result+=(color/math.pi+spec[:,None])*radiance*nl[:,None]
    hdr=result*1.45
    rgb=np.clip((hdr*(2.51*hdr+.03))/(hdr*(2.43*hdr+.59)+.14),0,1)
    return np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)


def render(spec,maps,rects,candidate):
    width,height=1200,820
    pos,mask,eye=ray_floor(spec,width,height)
    # Actual east mezzanine world origin. Preview floor is translated down to z=0.
    plane=np.stack((pos[...,0]/.0254+700,-pos[...,1]/.0254+620),-1)
    py,px=np.gradient(plane,axis=(0,1))
    result=np.full((height,width,3),.16,np.float32)
    for y in range(0,height,64):
        active=mask[y:y+64]
        p=plane[y:y+64][active]
        color,normal,rough,ao=material(p,px[y:y+64][active],py[y:y+64][active],-1,maps,rects,candidate)
        view=unit(eye-pos[y:y+64][active])
        result[y:y+64][active]=shade(color,normal,rough,ao,view)
    image=Image.fromarray(np.rint(np.clip(result,0,1)*255).astype(np.uint8))
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,height-28,width,height),fill=(24,25,26))
    text='OFFLINE MATERIAL PREVIEW | '+('STAGED WAREHOUSE PINE' if candidate else 'CURRENT FLOORBOARDS')+' | matched CPU lighting; not an engine capture'
    draw.text((12,height-20),text,fill=(218,218,216))
    return image


def verify(manifest):
    assert manifest['source_color_sha256']==manifest['staged_color_sha256']
    assert all(F.sha(ROOT/p)==digest for p,digest in manifest['sources'].items())
    assert all(F.sha(ROOT/p)==digest for p,digest in manifest['protected'].items())
    assert all(F.sha(OUT/'stage'/p)==digest for p,digest in manifest['staged_files'].items())
    rng=np.random.default_rng(571)
    plane=rng.uniform((380,260),(1130,980),(100000,2))
    rects=manifest['board_rectangles']
    tile=layout(plane,rects)
    assert np.allclose(np.mod(tile['start']-440,110),0)
    assert np.allclose(np.mod(tile['start']+tile['spans']*110-440,110),0)
    assert set(np.unique(tile['spans']))=={1.,2.}
    assert set(np.unique(tile['scan']))==set(range(8))
    rect=np.asarray(rects)[tile['scan']]
    assert np.all(tile['uv']>=rect[:,:2]) and np.all(tile['uv']<=rect[:,:2]+rect[:,2:])
    assert np.all(tile['local']>=0) and np.all(tile['local']<1)
    # Independently difference atlas UVs to verify SampleGrad scaling and both flips.
    stable=(tile['local'].min(axis=-1)>.02)&(tile['local'].max(axis=-1)<.98)
    point=plane[stable][:2048]
    at=layout(point,rects)
    for axis in range(2):
        offset=np.zeros_like(point); offset[:,axis]=.0001
        finite=(layout(point+offset,rects)['uv']-layout(point-offset,rects)['uv'])/.0002
        expected=np.zeros_like(point); expected[:,axis]=at['scale'][:,axis]
        assert np.allclose(finite,expected,atol=1e-9)
    # Mirrored warehouse positions keep colour/roughness and flip only world-normal Y.
    maps={key:mips(OUT/'stage'/F.RESOURCE/f'warehouse_{suffix}.png',key=='color')
          for key,suffix in (('color','color'),('normal','normal'),('rough','rough'))}
    dx=np.tile((.02,0),(len(point),1)); dy=np.tile((0,.02),(len(point),1))
    east=material(point,dx,dy,-1,maps,rects,True)
    west=material(point,dx,dy,1,maps,rects,True)
    assert np.allclose(east[0],west[0]) and np.allclose(east[2],west[2])
    assert np.allclose(east[1]*np.array((1,-1,1)),west[1])
    assert all(np.isfinite(channel).all() for channel in east+west)
    # The no-geometry material remap must remain exactly one existing slot per half.
    for path,detail in manifest['models'].items():
        old=(ROOT/'Assets'/path).read_bytes()
        new=(OUT/'stage'/path).read_bytes()
        assert F.sha(ROOT/'Assets'/path)==detail['before']
        assert new.replace(F.MATERIAL.encode(),b'materials/buildings/floorboards.vmat')==old
    # Analytic edge normals point away from the raised face, on both mirror sides.
    boundary_cases=[]
    for side in (-1,1):
        for axis in (0,1):
            for end in (0,1):
                sign=(1 if end==0 else -1)*(side if axis==1 else 1)
                slope=.0005*1.5/.00175
                normal=np.zeros(3); normal[2]=1; normal[axis]=-sign*slope
                assert normal[axis]*sign<0
                boundary_cases.append(dict(side=side,axis=axis,end=end,normal=unit(normal).tolist()))
    return dict(status='offline_data_and_layout_checks_passed',manifest_sha256=F.sha(OUT/'manifest.json'),
        reviewer_sha256=F.sha(Path(__file__)),source_color_preserved=True,protected_live_files=len(manifest['protected']),
        sampled_points=len(plane),all_board_ends_on_existing_joist_grid=True,atlas_rows_used=list(map(int,np.unique(tile['scan']))),
        finite_difference_uv_samples=len(point)*2,mirrored_surface_samples=len(point),
        mirrored_edge_normal_cases=boundary_cases,exact_material_remaps=2,geometry_collision_scene_unchanged=True,
        native_shader_compilation='Not run; offline work requested',
        limitation='CPU equations and source inspection are not an HLSL compiler or native rendering test')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((OUT/'manifest.json').read_text())
    report=verify(manifest)
    if not args.verify_only:
        preview=OUT/'preview'; preview.mkdir(exist_ok=True)
        for label,base,prefix in (('before',ROOT/'Assets/materials/buildings','floorboards'),
                                  ('candidate',OUT/'stage'/F.RESOURCE,'warehouse')):
            maps={key:mips(base/f'{prefix}_{suffix}.png',key=='color') for key,suffix in (('color','color'),('normal','normal'),('rough','rough'))}
            for name,spec in VIEWS.items():
                render(spec,maps,manifest['board_rectangles'],label=='candidate').save(preview/f'{name}-{label}.png')
                print(f'Rendered {label} {name}',flush=True)
        F.write(preview/'provenance.json',json.dumps(dict(kind='CPU perspective PBR material comparison',native_engine_capture=False,
            manifest_sha256=F.sha(OUT/'manifest.json'),renderer_sha256=F.sha(Path(__file__)),views=VIEWS,
            source_texture_pixels_preserved=True,filtering='Approximate 8-tap anisotropic/trilinear texture sampling',
            limitations=['No engine shader compilation','No native DDGI, exposure, texture compression or temporal sampling',
                         'Isolated floor-plane review; not a recreation of the warehouse screenshot','No performance result'],
            previews={p.name:F.sha(p) for p in sorted(preview.glob('*.png'))}),indent=2)+'\n')
    F.write(OUT/'offline-verification.json',json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='mirrored_edge_normal_cases'},indent=2))


if __name__=='__main__':
    main()
