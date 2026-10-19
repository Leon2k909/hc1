"""Offline landscape crown trial using the unmodified generated RGBA atlas.

Uses belltower_canopy_trial.py's staging-only CLI. Alpha is preserved and
filtered with premultiplied linear colour. Planted olive/cypress/poplar crowns
retain the accepted painter; only natural broadleaf species use the atlas.
"""
from pathlib import Path
import math
import platform
platform._wmi = None
import numba
import numpy as np
from PIL import Image
import belltower_canopy_trial as T

P, V = T.P, T.V
ATLAS = T.ROOT/'Sources/Belltower/generated/canopy-crowns-v2.png'
ACCEPTED_TOPS = P._tops


@numba.njit(cache=True, inline='always')
def sample(image, sprite, u, v):
    n=image.shape[1]
    x, y=min(max(u*(n-1),0),n-1), min(max(v*(n-1),0),n-1)
    x0, y0=int(x), int(y)
    x1, y1=min(x0+1,n-1), min(y0+1,n-1)
    fx, fy=x-x0, y-y0
    return (image[sprite,y0,x0]*(1-fx)+image[sprite,y0,x1]*fx)*(1-fy)+(image[sprite,y1,x0]*(1-fx)+image[sprite,y1,x1]*fx)*fy


@numba.njit(cache=True, fastmath=True)
def paint_atlas(crowns, e0, n0, we, wn, w, top, ccol, cov, cid, mips, extents, means):
    rows, cols=top.shape
    for k in range(len(crowns)):
        species=int(crowns[k,6])
        if crowns[k,7]<0 or species not in (P.OAK,P.HOLM,P.BEECH,P.WILLOW):
            continue
        sprite=0 if species==P.OAK else 1 if species==P.HOLM else 2 if species==P.BEECH else 3
        ce,cn,zg,a,hc,bb=crowns[k,:6]
        seed=np.int64(crowns[k,11])
        angle=seed*2.399963229728653
        ca,sa=math.cos(angle),math.sin(angle)
        aspect=math.sqrt(.75+.50*P._u(seed,913))
        extent=a*extents[sprite]
        bound=extent*max(aspect,1/aspect)*math.sqrt(2)
        c0,c1=max(int((ce-bound-e0)/we)-1,0),min(int((ce+bound-e0)/we)+1,cols-1)
        r0,r1=max(int((n0-cn-bound)/wn)-1,0),min(int((n0-cn+bound)/wn)+1,rows-1)
        lod=min(max(math.log2(mips[0].shape[1]*w/(2*extent)),0),len(mips)-1)
        level=int(lod)
        blend=lod-level
        for row in range(r0,r1+1):
            dy=n0-row*wn-cn
            for col in range(c0,c1+1):
                dx=e0+col*we-ce
                u=(ca*dx+sa*dy)*aspect/(2*extent)+.5
                v=(-sa*dx+ca*dy)/aspect/(2*extent)+.5
                if u<0 or u>1 or v<0 or v>1:
                    continue
                texel=sample(mips[level],sprite,u,v)*(1-blend)+sample(mips[min(level+1,len(mips)-1)],sprite,u,v)*blend
                alpha=texel[3]
                if alpha<=.001:
                    continue
                rho2=min((dx*dx+dy*dy)/(a*a),1)
                hz=hc+bb*math.sqrt(1-rho2)
                if cid[row,col]>=0 and zg+hz<=top[row,col]:
                    continue
                nx,ny,nz=dx/(a*a),dy/(a*a),(hz-hc)/(bb*bb)
                length=math.sqrt(nx*nx+ny*ny+nz*nz)
                lit=max((nx*V.SUN[0]+ny*V.SUN[1]+nz*V.SUN[2])/length,0)
                sky=.75+.25*nz/length
                for channel in range(3):
                    shade=min((P.AMBIENT[channel]*sky+P.SUN_RGB[channel]*P.LEAF_SUN*lit)/P.FLAT_LIT[channel],P.SHADE_MAX)
                    leaf=texel[channel]/means[sprite,channel]*crowns[k,7+channel]
                    ccol[row,col,channel]=ccol[row,col,channel]*(1-alpha)+leaf*shade
                cov[row,col]=1-(1-cov[row,col])*(1-alpha)
                if alpha>=.5:
                    top[row,col],cid[row,col]=zg+hz,k


def load_atlas():
    image=Image.open(ATLAS)
    assert image.mode=='RGBA' and image.width==image.height and image.width%2==0
    pixels=np.asarray(image)
    half=image.width//2
    # The generated gap has occasional alpha=1 pixels. Keep those original
    # values; visible foliage must remain clear of each quadrant's boundary.
    assert pixels[half-12:half+12,:,3].max()<=1 and pixels[:,half-12:half+12,3].max()<=1
    tiles=np.stack([pixels[y:y+half,x:x+half] for y,x in ((0,0),(0,half),(half,0),(half,half))])
    alpha=tiles[:,:,:,3:4].astype(np.float32)/255
    colour=P.linear(tiles[:,:,:,:3]).astype(np.float32)*alpha
    sums=alpha.sum(axis=(1,2,3))
    means=colour.sum(axis=(1,2))/sums[:,None]
    # Preserve each original crown's area despite transparent atlas margins.
    extents=half*.5*np.sqrt(math.pi/sums)
    levels=numba.typed.List()
    level=np.concatenate((colour,alpha),axis=3)
    levels.append(np.ascontiguousarray(level))
    while level.shape[1]>1:
        size=level.shape[1]
        if size%2:
            level=np.pad(level,((0,0),(0,1),(0,1),(0,0)))
            size+=1
        level=level.reshape(4,size//2,2,size//2,2,4).mean(axis=(2,4),dtype=np.float32)
        levels.append(np.ascontiguousarray(level))
    return levels,extents,means


MIPS,EXTENTS,MEANS=load_atlas()


def photographic_tops(crowns,e0,n0,we,wn,w,top,ccol,cov,cid,grads):
    background=crowns.copy()
    natural=np.isin(background[:,6],(P.OAK,P.HOLM,P.BEECH,P.WILLOW))
    background[natural,7]=-1
    ACCEPTED_TOPS(background,e0,n0,we,wn,w,top,ccol,cov,cid,grads)
    paint_atlas(crowns,e0,n0,we,wn,w,top,ccol,cov,cid,MIPS,EXTENTS,MEANS)


if __name__=='__main__':
    T.main(painter=photographic_tops,style='photographic',extra_sources=(Path(__file__),ATLAS))
