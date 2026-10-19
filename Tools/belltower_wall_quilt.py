"""Build numerical UV selectors for periodic sampling of original PBR images.

The generated color and height pixels are never rewritten. Minimum-cost paths
select between offset samples; both maps always use the same selector.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'Sources/Belltower/generated'


def path(cost, low, high):
    """Top-to-bottom seam, with identical endpoint for a periodic other axis."""
    section=cost[:,low:high]
    rows,width=section.shape
    middle=width//2
    previous=np.full(width,np.inf)
    previous[middle]=section[0,middle]
    parents=np.zeros((rows,width),np.int16)
    for row in range(1,rows):
        options=[]
        for shift in range(-3,4):
            shifted=np.full(width,np.inf)
            if shift<0:
                shifted[:shift]=previous[-shift:]
            elif shift>0:
                shifted[shift:]=previous[:-shift]
            else:
                shifted=previous.copy()
            options.append(shifted+abs(shift)*.001)
        options=np.array(options)
        best=np.argmin(options,axis=0)
        parents[row]=np.arange(width)-(best-3)
        previous=np.min(options,axis=0)+section[row]
    seam=np.empty(rows,np.int32)
    seam[-1]=middle
    for row in range(rows-1,0,-1):
        seam[row-1]=parents[row,seam[row]]
    assert seam[0]==seam[-1]==middle
    return seam+low


def costs(a,b,ha,hb):
    # Albedo agreement and recessed-joint agreement both matter. Selecting the
    # color and height independently would give normals belonging to other stones.
    return (np.mean(np.abs(a-b),axis=2)*1.5 + np.abs(ha-hb)*3
            + np.minimum(ha,hb)*.035)


def main():
    color=np.array(Image.open(FOLDER/'wall-limestone-v3-color.png').convert('RGB'),dtype=np.float32)/255
    raw=np.array(Image.open(FOLDER/'wall-limestone-v3-height.png').convert('L'),dtype=np.float32)/255
    height=np.clip((raw-.16)/(.74-.16),0,1)
    height=height*height*(3-2*height)
    rows,cols=height.shape
    assert rows%2==cols%2==0
    shift_x,shift_y=round(cols*.37),round(rows*.43)
    shifted_color=np.roll(color,-shift_x,axis=1)
    shifted_height=np.roll(height,-shift_x,axis=1)
    cost=costs(color,shifted_color,height,shifted_height)
    left=path(cost,int(cols*.10),int(cols*.33))
    right=path(cost,int(cols*.69),int(cols*.92))
    x=np.arange(cols)[None,:]
    hmask=(x<left[:,None]) | (x>=right[:,None])
    horizontal_color=np.where(hmask[:,:,None],shifted_color,color)
    horizontal_height=np.where(hmask,shifted_height,height)
    shifted_color=np.roll(horizontal_color,-shift_y,axis=0)
    shifted_height=np.roll(horizontal_height,-shift_y,axis=0)
    cost=costs(horizontal_color,shifted_color,horizontal_height,shifted_height).T
    top=path(cost,int(rows*.10),int(rows*.33))
    bottom=path(cost,int(rows*.69),int(rows*.92))
    y=np.arange(rows)[:,None]
    vmask=(y<top[None,:]) | (y>=bottom[None,:])
    final_hmask=np.where(vmask,np.roll(hmask,-shift_y,axis=0),hmask)
    # Per-stone luminance is material data, not a repainted color texture. It
    # lets the shader restrain calcite pigmentation while retaining real grain.
    labels,count=ndimage.label(ndimage.binary_erosion(height>.72,iterations=1))
    sizes=np.bincount(labels.ravel())
    valid=(labels>0) & (sizes[labels]>=64)
    nearest=ndimage.distance_transform_edt(~valid,return_distances=False,return_indices=True)
    expanded=labels[tuple(nearest)]
    linear=np.where(color<=.04045,color/12.92,((color+.055)/1.055)**2.4)
    lum=linear@np.array([.2126,.7152,.0722])
    sums=np.bincount(labels.ravel(),weights=lum.ravel(),minlength=count+1)
    means=np.divide(sums,np.maximum(sizes,1))
    means=np.clip(.28+(means-.28)*.55,.18,.4)
    calm=means[expanded]
    calm=np.where(hmask,np.roll(calm,-shift_x,axis=1),calm)
    calm=np.where(vmask,np.roll(calm,-shift_y,axis=0),calm)
    data=np.zeros((rows,cols,3),np.uint8)
    data[:,:,0]=final_hmask*255
    data[:,:,1]=vmask*255
    data[:,:,2]=np.rint(calm*255).astype(np.uint8)
    Image.fromarray(data).save(FOLDER/'wall-limestone-v3-quilt.png')
    final_color=np.where(vmask[:,:,None],shifted_color,horizontal_color)
    final_height=np.where(vmask,shifted_height,horizontal_height)
    def borders(array):
        return {'horizontal':float(np.mean(np.abs(array[:,0]-array[:,-1]))),
                'vertical':float(np.mean(np.abs(array[0]-array[-1])))}
    result={'method':'two-axis minimum-cost periodic UV selector',
            'source_pixels_modified':False,'selector_size':[cols,rows],
            'stone_regions':int(np.count_nonzero(sizes[1:]>=64)),
            'uv_shift':[shift_x/cols,shift_y/rows],
            'color_borders_before':borders(color),'color_borders_after':borders(final_color),
            'height_borders_before':borders(height),'height_borders_after':borders(final_height)}
    target=ROOT/'output/belltower/quality/wall-v3/quilt-check.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
