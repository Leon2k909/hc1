"""Offline textured layout review; approximate light, not an engine screenshot."""
from pathlib import Path
import argparse, json, math, re
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import map_kit as K
import collider_map as C

ROOT=Path(__file__).resolve().parents[1]

def material(paint):
    path=(C.STAGE/"materials/collider" if paint.startswith("co_") else ROOT/"Assets/materials/ares")/(paint+".vmat")
    text=path.read_text()
    def get(key,default=""):
        match=re.search(r'\b'+key+r'\s+"([^\"]+)"',text)
        return match.group(1) if match else default
    tint=np.array([float(v) for v in get("g_vColorTint","[1 1 1 1]").strip("[]").split()][:3])
    color=get("TextureColor")
    if color.startswith("["):
        texture=np.array([float(v) for v in color.strip("[]").split()][:3])[None,None,:]
    elif color=="materials/default/default_color.tga": texture=np.ones((1,1,3))
    else:
        p=(C.STAGE if paint.startswith("co_") else ROOT/"Assets")/color
        im=Image.open(p).convert("RGB")
        if paint!="co_signs": im.thumbnail((1024,1024))
        texture=np.array(im,float)/255
    emission=float(get("g_flSelfIllumBrightness","0")) if get("F_SELF_ILLUM")=="1" else 0
    levels=[np.power(texture*tint,2.2).astype(np.float32)]
    # The engine filters textures. Mips keep this geometry preview from falsely
    # showing distant grating, monitor plots and concrete as bright speckled noise.
    while min(levels[-1].shape[:2])>1:
        last=levels[-1]; h,w=last.shape[:2]
        reduced=last[:h//2*2,:w//2*2].reshape(h//2,2,w//2,2,3).mean(axis=(1,3))
        levels.append(reduced)
    return levels,emission

def clipped(vertices,near=2):
    out=[]
    for a,b in zip(vertices,np.roll(vertices,-1,axis=0)):
        if a[2]>=near: out.append(a)
        if (a[2]>=near)!=(b[2]>=near): out.append(a+(b-a)*(near-a[2])/(b[2]-a[2]))
    return [np.array((out[0],out[k],out[k+1])) for k in range(1,len(out)-1)]

def render(models,view,width=1440,height=810,exposure=1.65):
    eye=np.array(view["eye"],float); forward=K.normalise(np.array(view["target"])-eye)
    right=K.normalise(np.cross(forward,(0,0,1))); up=np.cross(right,forward)
    focal=width*.5/math.tan(math.radians(view["fov"])*.5)
    depth=np.zeros((height,width),np.float32)
    color=np.zeros((height,width,3),np.float32)
    normal=np.zeros_like(color); position=np.zeros_like(color); emissive=np.zeros((height,width),np.float32)
    materials={}
    for model_name,model in models.items():
        offset=K.uv_offset(model_name)
        for paint,polys in model.polygons.items():
            if "glass" in paint: continue
            if paint not in materials: materials[paint]=material(paint)
            levels,glow=materials[paint]; th,tw=levels[0].shape[:2]
            for index,(pts,norm) in enumerate(polys):
                points=np.asarray(pts)
                if np.dot(norm,eye-points[0])<=0: continue
                camera=np.stack(((points-eye)@right,(points-eye)@up,(points-eye)@forward),axis=1)
                if camera[:,2].max()<2: continue
                uv=model.polygon_uvs.get((paint,index))
                if uv is None:
                    uv=[K.face_uv(K.to_world(p),K.to_world(norm),paint,offset,model.tile_overrides.get(paint)) for p in points]
                vertices=np.column_stack((camera,points,uv))
                for k in range(1,len(points)-1):
                    tri=vertices[[0,k,k+1]]
                    for part in clipped(tri):
                        z=1/part[:,2]
                        screen=np.column_stack((width*.5+focal*part[:,0]*z,height*.5-focal*part[:,1]*z))
                        lo=np.maximum(np.floor(screen.min(axis=0)).astype(int),0)
                        hi=np.minimum(np.ceil(screen.max(axis=0)).astype(int),(width-1,height-1))
                        x0,y0=lo;x1,y1=hi
                        if x1<x0 or y1<y0: continue
                        (ax,ay),(bx,by),(cx,cy)=screen
                        area=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
                        if abs(area)<1e-8: continue
                        du=part[1,6:8]-part[0,6:8];dv=part[2,6:8]-part[0,6:8]
                        uv_dx=(du*(cy-ay)-dv*(by-ay))/area*np.array((tw,th))
                        uv_dy=(dv*(bx-ax)-du*(cx-ax))/area*np.array((tw,th))
                        footprint=max(np.linalg.norm(uv_dx),np.linalg.norm(uv_dy),1)
                        level=min(len(levels)-1,int(math.log2(footprint)))
                        texture=levels[level]; mh,mw=texture.shape[:2]
                        xs=np.arange(x0,x1+1)+.5;ys=(np.arange(y0,y1+1)+.5)[:,None]
                        a=((bx-xs)*(cy-ys)-(by-ys)*(cx-xs))/area
                        b=((cx-xs)*(ay-ys)-(cy-ys)*(ax-xs))/area;c=1-a-b
                        iz=a*z[0]+b*z[1]+c*z[2]
                        d=depth[y0:y1+1,x0:x1+1]
                        visible=(a>=0)&(b>=0)&(c>=0)&(iz>d)
                        if not visible.any(): continue
                        weights=np.stack((a[visible]*z[0],b[visible]*z[1],c[visible]*z[2]),axis=1)/iz[visible,None]
                        attrs=weights@part[:,3:]
                        u=(attrs[:,3]%1)*mw-.5;v=((1-attrs[:,4])%1)*mh-.5
                        ui=np.floor(u).astype(int);vi=np.floor(v).astype(int)
                        fu=(u-ui)[:,None];fv=(v-vi)[:,None]
                        sample=((texture[vi%mh,ui%mw]*(1-fu)+texture[vi%mh,(ui+1)%mw]*fu)*(1-fv)
                              +(texture[(vi+1)%mh,ui%mw]*(1-fu)+texture[(vi+1)%mh,(ui+1)%mw]*fu)*fv)
                        d[visible]=iz[visible]
                        color[y0:y1+1,x0:x1+1][visible]=sample
                        normal[y0:y1+1,x0:x1+1][visible]=norm
                        position[y0:y1+1,x0:x1+1][visible]=attrs[:,:3]
                        emissive[y0:y1+1,x0:x1+1][visible]=glow
        print("rasterized",model_name,flush=True)
    present=depth>0
    p=position[present];n=normal[present];base=color[present];emission=emissive[present,None]
    lighting=np.broadcast_to(np.array((.17,.20,.25)),base.shape).copy()
    spec=np.zeros_like(base)
    viewdir=eye-p;viewdir/=np.linalg.norm(viewdir,axis=1)[:,None]
    for _,at,rgb,radius,shadow in C.LIGHTS:
        delta=np.array(at)-p;dist=np.linalg.norm(delta,axis=1)
        inside=dist<radius
        if not inside.any(): continue
        l=delta[inside]/np.maximum(dist[inside,None],1)
        attenuation=np.clip(1-(dist[inside]/radius)**2,0,1)**2
        diffuse=np.maximum((n[inside]*l).sum(axis=1),0)
        light=np.array([float(v) for v in rgb.split(",")[:3]])
        lighting[inside]+=light[None,:]*(diffuse*attenuation*.65)[:,None]
        h=l+viewdir[inside];h/=np.maximum(np.linalg.norm(h,axis=1)[:,None],.001)
        shine=np.maximum((n[inside]*h).sum(axis=1),0)**65
        spec[inside]+=light[None,:]*(shine*attenuation*.15)[:,None]
    hdr=np.zeros_like(color)
    hdr[present]=base*(lighting+emission)+spec
    glow=gaussian_filter(np.maximum(hdr-1,0),sigma=(4,4,0))*.18
    hdr=(hdr+glow)*exposure
    rgb=np.clip((hdr*(2.51*hdr+.03))/(hdr*(2.43*hdr+.59)+.14),0,1)**(1/2.2)
    return Image.fromarray((rgb*255).astype(np.uint8))

def main():
    config=json.loads((ROOT/"Sources/Collider/editor/capture-config.json").read_text())
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view",default="art",choices=[view["name"] for view in config["views"]])
    parser.add_argument("--exposure",type=float,default=1.65,help="Approximate software-render exposure, unrelated to engine settings")
    parser.add_argument("--out",type=Path,default=ROOT/"output/collider/offline-preview")
    args=parser.parse_args()
    models=C.build();out=args.out
    out.mkdir(parents=True,exist_ok=True)
    view=next(view for view in config["views"] if view["name"]==args.view)
    render(models,view,exposure=args.exposure).save(out/(view["name"]+".png"))
    report=out/("provenance.json" if args.view=="art" else args.view+"-provenance.json")
    report.write_text(json.dumps({"kind":"offline software preview","native_engine_capture":False,
        "limitations":["Approximate lighting, no shadow tracing or reflections","Glass omitted"],"view":view,
        "software_exposure":args.exposure},indent=2))
    print("wrote",out/(view["name"]+".png"),flush=True)

if __name__=="__main__": main()
