"""Individual folded ivy leaves and branching hanging shoots for Veridant.

The generated RGBA texture is retained unchanged. Its alpha is read only to
trace actual leaf geometry, avoiding the old whole-vine billboard silhouette.
"""
from pathlib import Path
from functools import lru_cache
import json
import math
import numpy as np
from PIL import Image
from scipy import ndimage
import riverdale_parts as P

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='materials/veridant/ivy-v2'
MATERIALS={f'vr_ivy_{name}':f'{RESOURCE}/{name}.vmat' for name in ('leaf','fresh','back','stem')}
UP=np.array((0.,0.,1.))


def cross(a,b):return float(a[0]*b[1]-a[1]*b[0])


def simplify(points,tolerance=4.):
    a,b=points[0],points[-1];delta=b-a;length=np.linalg.norm(delta)
    distances=np.linalg.norm(points-a,axis=1) if length<1e-8 else np.abs(np.cross(delta,points-a))/length
    i=int(np.argmax(distances))
    if distances[i]<=tolerance:return np.array([a,b])
    return np.concatenate((simplify(points[:i+1],tolerance)[:-1],simplify(points[i:],tolerance)))


def contains(p,a,b,c,epsilon=1e-9):
    return min(cross(b-a,p-a),cross(c-b,p-b),cross(a-c,p-c))>=-epsilon


@lru_cache(maxsize=1)
def leaf_template():
    source=ROOT/'Sources/Veridant/ivy-v2/leaf-source.png'
    im=Image.open(source);alpha=np.asarray(im.getchannel('A'))
    # Contour analysis only: no raster output or generated pixels are altered.
    mask=alpha[::2,::2]>190
    labels,count=ndimage.label(mask)
    sizes=np.bincount(labels.ravel());sizes[0]=0
    mask=ndimage.binary_fill_holes(labels==int(np.argmax(sizes)))
    h,w=mask.shape;edges={}
    ys,xs=np.nonzero(mask)
    for y,x in zip(ys,xs):
        if y==0 or not mask[y-1,x]:edges[(x,y)]=(x+1,y)
        if x==w-1 or not mask[y,x+1]:edges[(x+1,y)]=(x+1,y+1)
        if y==h-1 or not mask[y+1,x]:edges[(x+1,y+1)]=(x,y+1)
        if x==0 or not mask[y,x-1]:edges[(x,y+1)]=(x,y)
    loops=[]
    while edges:
        start=next(iter(edges));p=start;loop=[]
        while p in edges:
            loop.append(p);p=edges.pop(p)
            if p==start:break
        if len(loop)>8:loops.append(np.array(loop,float))
    area=lambda p:abs(sum(cross(a,b) for a,b in zip(p,np.roll(p,-1,axis=0))))
    loop=max(loops,key=area);mid=len(loop)//2
    outline=np.concatenate((simplify(loop[:mid+1])[:-1],simplify(np.vstack((loop[mid:],loop[0])) )[:-1]))
    # Simplifying the two contour halves can leave a nearly collinear vertex at
    # their join. Remove those before triangulation; otherwise the OBJ's inch
    # precision can turn a long sliver over after a leaf is rotated in the map.
    while len(outline)>16:
        distances=[]
        for a,b,c in zip(np.roll(outline,1,axis=0),outline,np.roll(outline,-1,axis=0)):
            distances.append(abs(cross(b-a,c-a))/max(np.linalg.norm(c-a),1e-9))
        index=int(np.argmin(distances))
        if distances[index]>=2.:break
        outline=np.delete(outline,index,axis=0)
    uv=np.column_stack((outline[:,0]/w,1-outline[:,1]/h))
    if sum(cross(a,b) for a,b in zip(uv,np.roll(uv,-1,axis=0)))<0:uv=uv[::-1]
    points=list(uv);remaining=list(range(len(points)));triangles=[]
    while len(remaining)>3:
        candidates=[]
        for j,index in enumerate(remaining):
            ia,ib,ic=remaining[j-1],index,remaining[(j+1)%len(remaining)]
            a,b,c=points[ia],points[ib],points[ic]
            if cross(b-a,c-b)<=1e-10:continue
            if any(contains(points[k],a,b,c) for k in remaining if k not in (ia,ib,ic)):continue
            quality=cross(b-a,c-a)/(np.linalg.norm(b-a)**2+np.linalg.norm(c-b)**2+np.linalg.norm(a-c)**2)
            candidates.append((quality,j,(ia,ib,ic)))
        if not candidates:raise RuntimeError('Cannot triangulate the retained leaf silhouette')
        _,j,face=max(candidates);triangles.append(face);remaining.pop(j)
    triangles.append(tuple(remaining))
    # Interior midrib points make the leaf crown three-dimensional. Insert only
    # strictly inside a triangle, so no edge or boundary cracks are introduced.
    for i,t in enumerate((.34,.46,.58,.70,.83)):
        p=np.array((.5017+i*.0003,t))
        for j,(ia,ib,ic) in enumerate(triangles):
            a,b,c=points[ia],points[ib],points[ic]
            if min(cross(b-a,p-a),cross(c-b,p-b),cross(a-c,p-c))>.0004:
                k=len(points);points.append(p)
                triangles[j:j+1]=[(ia,ib,k),(ib,ic,k),(ic,ia,k)];break
    uv=np.array(points)
    assert len(triangles)<100 and len(triangles)>15
    assert all(cross(uv[b]-uv[a],uv[c]-uv[a])>1e-10 for a,b,c in triangles)
    return uv,triangles


def blade(model,base,direction,normal,length,phase,paint):
    uv,faces=leaf_template();base=np.asarray(base,float)
    n=P.unit(normal);direction=P.unit(np.asarray(direction)-n*np.dot(direction,n));across=np.cross(direction,n)
    def shape(t):
        x=(t[0]-.5)*1.16;y=(t[1]-.25)/.75
        ridge=.065*math.sin(math.pi*min(1,max(0,y)))*(1-min(1,abs(x)*1.8))
        return np.array((x,y,ridge+.055*y*y-.10*x*x+.018*math.sin(phase+y*5)*x))
    def pos(t):
        q=shape(t);return base+length*(across*q[0]+direction*q[1]+n*q[2])
    points=np.array([pos(t) for t in uv]);normals=[]
    for t in uv:
        eps=.0001
        du=pos(t+(eps,0))-pos(t-(eps,0));dv=pos(t+(0,eps))-pos(t-(0,eps))
        normals.append(P.unit(np.cross(du,dv)))
    packed=texture_coordinates()
    for ids in faces:
        model.polygon(paint,[points[i] for i in ids],normals=[normals[i] for i in ids],uv=[packed[i] for i in ids])
        reverse=ids[::-1]
        model.polygon('vr_ivy_back',[points[i] for i in reverse],normals=[-normals[i] for i in reverse],uv=[packed[i] for i in reverse])


@lru_cache(maxsize=1)
def texture_coordinates():
    data=json.loads((ROOT/'Sources/Veridant/ivy-v2/texture-packing.json').read_text())
    assert data['DecodedTexelsPreserved'] and not data['Resampled']
    uv,_=leaf_template()
    return np.column_stack(((uv[:,0]*data['SourceWidth']+data['OffsetX'])/data['Width'],
        (uv[:,1]*data['SourceHeight']+data['OffsetY'])/data['Height']))


def build_into(model,at,right,w,h,seed=0,off=1.2):
    rng=np.random.default_rng(abs(int(seed)));right=P.unit(right);out=P.unit(np.cross(right,UP));top=np.asarray(at,float)
    hero=w>=100
    model.material_overrides.update(MATERIALS)
    for paint in MATERIALS:model.tile_overrides[paint]=12.
    stats=getattr(model,'ivy_stats',{'assemblies':0,'shoots':0,'leaves':0,'branches':0});model.ivy_stats=stats
    stats['assemblies']+=1
    def stem(path,radius):
        if radius<=.045:
            # Tiny leaf petioles need a closed silhouette, not subpixel elbow
            # subdivisions. Keep the heavier shoots smoothly curved.
            P.rod(model,path[0],path[-1],radius,'vr_ivy_stem',sides=5,caps=True)
        else:
            P.tube(model,path,radius,'vr_ivy_stem',sides=6,bend_radius=radius*1.5)
        stats['branches']+=1
    def leaf(anchor,side,phase,small=False):
        normal=P.unit(out*rng.uniform(.50,1)+right*rng.uniform(-.8,.8)+UP*rng.uniform(-.35,.5))
        direction=right*side*rng.uniform(.55,1)-UP*rng.uniform(.15,.95)+out*rng.uniform(-.15,.3)
        length=float(rng.uniform(4.0,5.8) if hero else rng.uniform(2.7,4.5))*(.76 if small else 1)
        end=anchor+right*side*rng.uniform(.7,1.7)+out*rng.uniform(.3,1.2)-UP*rng.uniform(.1,.6)
        stem([anchor,(anchor+end)/2+out*.12,end],.033 if small else .045)
        blade(model,end,direction,normal,length,phase,'vr_ivy_fresh' if rng.random()<.22 else 'vr_ivy_leaf')
        stats['leaves']+=1
    count=max(2,round(w/(24 if hero else 33)))
    for i in range(count):
        fraction=(i+.5)/count-.5
        origin=top+right*(fraction*w+rng.uniform(-w/count*.20,w/count*.20))+out*(off+.55)
        drop=h*float(rng.uniform(.48,.98));phase=float(rng.uniform(0,math.tau))
        def point(t):
            return origin+right*(math.sin(t*4.5+phase)-math.sin(phase))*min(7.,w*.10)*t+out*(1.15*math.sin(t*4+phase)*t)-UP*(drop*t)
        path=[point(t) for t in np.linspace(0,1,max(6,round(drop/15)))]
        stem(path,.105);stats['shoots']+=1
        nodes=max(5,round(drop/6.5))
        for j,t in enumerate(np.linspace(.035,.97,nodes)):
            side=-1 if j%2 else 1;p=P._along(path,float(t))[0]
            leaf(p,side,phase+j*.8,small=t>.82)
            if j%5==2 and t<.80:
                length=float(rng.uniform(7,13))
                tip=p+right*side*length-UP*length*.45+out*rng.uniform(.3,1.2)
                twig=[p,(p+tip)/2+UP*.6,tip]
                stem(twig,.06)
                for k,f in enumerate((.4,.75,1.)):
                    leaf(P._along(twig,f)[0],side if k%2 else -side,phase+j+k*.9,small=True)
    return model


def write_materials(folder):
    import shutil
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'Sources/Veridant/ivy-v2/leaf-source.png',folder/'leaf.png')
    shutil.copyfile(ROOT/'Sources/Veridant/ivy-v2/leaf-packed.png',folder/'leaf-pot.png')
    for name,tint in [('leaf',(1.,1.,1.)),('fresh',(1.06,1.08,.98)),('back',(.78,.88,.74))]:
        color=' '.join(f'{x:.4f}' for x in tint)
        text=('// Tools/veridant_ivy.py\n"Layer0"\n{\n'
            '    shader "shaders/foliage.shader"\n    F_ALPHA_TEST "0"\n    F_RENDER_BACKFACES "0"\n'
            '    F_FOLIAGE_ANIMATION "0"\n    F_TRANSMISSIVE "1"\n'
            f'    TextureColor "{RESOURCE}/leaf-pot.png"\n'
            '    TextureNormal "materials/default/default_normal.tga"\n'
            '    TextureRoughness "[0.73 0.73 0.73 0]"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            '    TextureTransmissiveColor "[0.20 0.30 0.08 0]"\n'
            '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n'
            f'    g_vColorTint "[{color} 1]"\n    g_flModelTintAmount "1"\n}}\n')
        (folder/f'{name}.vmat').write_text(text,encoding='utf-8')
    (folder/'stem.vmat').write_text('// Tools/veridant_ivy.py\n"Layer0"\n{\n'
        '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
        '    TextureColor "[0.15 0.19 0.075 1]"\n'
        '    TextureNormal "materials/default/default_normal.tga"\n'
        '    TextureRoughness "[0.86 0.86 0.86 0]"\n'
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
        '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n}\n',encoding='utf-8')
