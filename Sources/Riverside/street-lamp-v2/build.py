"""Formed cobra-head streetlight at the original arm attachment. Private review only."""
from pathlib import Path
import json,math,sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
K.obj_vector=lambda p:f'{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}'
MODEL='models/props/riverside/street_lamp_v2';MAT='materials/riverside/street_lamp_v2'
OUT=ROOT/'Assets'/MODEL;TEX=ROOT/'Assets'/MAT
REPORT=ROOT/'output/asset-improvement-20261030/riverside-street-lamp'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
def field(sigma,seed):
    a=ndi.gaussian_filter(np.random.default_rng(seed).normal(size=(1024,1024)),sigma,mode='wrap')
    return a/(3*a.std()+1e-8)
def paint():
    yy,xx=np.mgrid[:1024,:1024].astype(float)
    cloud=field(11,17);grain=field(.55,18);streak=field((20,1.8),19)
    c=np.ones((1024,1024,3))*np.array((.36,.38,.37))
    c*=1+.06*cloud[:,:,None]+.012*grain[:,:,None]
    dirt=np.clip(.1+.12*cloud+.07*streak,0,.35)
    c=c*(1-dirt[:,:,None])+np.array((.18,.19,.14))*dirt[:,:,None]
    r=np.clip(.59+.10*cloud,.35,.9);metal=np.ones((1024,1024))*.55
    h=grain*.0004;glow=np.zeros((1024,1024))
    # Lens patch: warm ribbed refractor, emission limited to glass.
    x=(xx[:512,:512]-256)/240;y=(yy[:512,:512]-256)/240
    edge=np.clip((x*x+y*y-.3)/.7,0,1)
    c[:512,:512]=np.array((.68,.49,.23))*(1-.25*edge[:,:,None])*(1+.02*grain[:512,:512,None])
    r[:512,:512]=.27+.1*edge;metal[:512,:512]=0
    glow[:512,:512]=.65*(1-.4*edge)
    h[:512,:512]+=.002*(np.sin(2*math.pi*xx[:512,:512]/15)+np.sin(2*math.pi*yy[:512,:512]/19))
    c[560:,:512]=np.array((.035,.037,.031))*(1+.07*cloud[560:,:512,None]);r[560:,:512]=.86;metal[560:,:512]=0
    dy,dx=np.gradient(h);n=np.stack((-dx*50,dy*50,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    for name,a in (('color',c),('normal',n*.5+.5),('rough',r),('metal',metal),('glow',glow)):
        Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(TEX/f'lamp_{name}.png')
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def make(lod):
    m=K.Model();segments=(32,20,12)[lod]
    section=[(-11,.55,.65,-.2),(-8,1.3,1.6,-.6),(-5,3.5,2.7,-1.4),(-1,4.8,3.5,-1.4),(4,5,3.2,-1.4),(8.5,3.9,2.6,-1.4),(10.8,1.6,1.6,-.9),(11,.15,.8,-.3)]
    if lod==2:section=[section[k] for k in (0,1,2,4,5,7)]
    rings=[]
    for x,w,top,bottom in section:
        mid=(top+bottom)/2;radius=(top-bottom)/2
        rings.append([np.array((x,w*math.sin(a),mid+radius*math.cos(a))) for a in np.linspace(0,2*math.pi,segments,endpoint=False)])
    # Smooth only the main casting; attachment and door edges retain crisp normals.
    quads=[];normal_sum={}
    def key(p):return tuple(round(float(v),6) for v in p)
    for j in range(len(rings)-1):
        for k in range(segments):
            q=[rings[j][k],rings[j+1][k],rings[j+1][(k+1)%segments],rings[j][(k+1)%segments]]
            n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n)
            quads.append((q,n))
            for p in q:normal_sum[key(p)]=normal_sum.get(key(p),np.zeros(3))+n
    for q,n in quads:
        for j in (1,2):
            ids=(0,j,j+1);m.polygon('metal',[plan(q[k]) for k in ids],normal=plan(n),normals=[plan(normal_sum[key(q[k])]) for k in ids])
    m.polygon('metal',[plan(p) for p in rings[0]],normal=-X)
    m.polygon('metal',[plan(p) for p in rings[-1][::-1]],normal=X)
    def ellipse(profile,paint,sx,sy,cx=1.3):
        part=K.Model();G.lathe_axis(part,(0,0,0),Z,profile,paint,sides=segments)
        for _,polys in part.polygons.items():
            for i,(pts,n) in enumerate(polys):
                ep=[K.to_world(p)*np.array((sx,sy,1))+np.array((cx,0,0)) for p in pts]
                smooth=part.polygon_normals.get((paint,i));ns=[];en=K.to_world(n)
                for j,p in enumerate(ep):
                    if paint=='glass' and en[2]<.5:
                        vn=np.array(((p[0]-cx)/sx**2,p[1]/sy**2,(p[2]+1.6)/1.4**2))
                    else:vn=K.to_world(smooth[j] if smooth else n)/np.array((sx,sy,1))
                    ns.append(plan(vn))
                m.polygon(paint,[plan(p) for p in ep],normal=plan(en/np.array((sx,sy,1))),normals=ns)
    ellipse([(.92,-1.75),(1,-1.65),(1,-1.38),(.96,-1.22),(.90,-1.35),(.90,-1.6),(.92,-1.75)],'metal',8.5,4.0)
    ellipse([(.98,-1.76),(1,-1.70),(1,-1.58),(.98,-1.55),(.96,-1.62),(.98,-1.76)],'rubber',8.0,3.6)
    ellipse([(0,-3.0),(.2,-3.0),(.6,-2.75),(.87,-2.35),(.98,-1.9),(1,-1.62),(0,-1.62)],'glass',7.8,3.5)
    # Hollow slip fitter surrounds the existing 1.2-inch radius arm, without moving it.
    G.lathe_axis(m,(0,0,0),X,[(1.48,-11.5),(1.48,-6.4),(1.26,-6.4),(1.26,-11.5),(1.48,-11.5)],'metal',sides=(24,16,8)[lod])
    def box(c,size,paint='metal'):
        if lod==2:m.oriented_box(plan(c),(X,Y,Z),size,paint)
        else:G.bevel_box(m,plan(c),(X,Y,Z),size,paint,bevel=min(.07,min(size)*.2))
    def bolt(c):G.lathe_axis(m,plan(c),Z,[(0,0),(.24,0),(.24,.17),(0,.17)],'metal',sides=6)
    for x in (-10,-7.6):bolt((x,0,1.48))
    # Rear hinge leaves, nose latch and seal line make the service door readable.
    for y in (-2.6,2.6):
        box((-4.8,y,-1.4),(2,.45,.35))
        G.lathe_axis(m,plan((-5.65,y,-1.5)),X,[(0,0),(.18,0),(.18,1.7),(0,1.7)],'metal',sides=(12,8,6)[lod])
    for y in (-2.25,2.25):box((7.8,y,-1.55),(.65,.45,.55))
    if lod<2:
        G.lathe_axis(m,plan((.5,0,3.46)),Z,[(0,0),(.52,0),(.52,.12),(.38,.18),(.38,.58),(0,.58)],'rubber',sides=(16,10)[lod])
        for x,y,z in ((-4.5,-2.6,-1.18),(-4.5,2.6,-1.18),(7.8,-2.25,-1.2),(7.8,2.25,-1.2)):bolt((x,y,z))
    for paint,polys in m.polygons.items():
        m.material_overrides[paint]=MAT+'/street_lamp.vmat';m.tile_overrides[paint]=16
        for i,(pts,n) in enumerate(polys):
            ep=[K.to_world(p) for p in pts];en=K.to_world(n)
            if paint=='glass':
                if abs(en[2])<1e-7:
                    a=0 if abs(en[1])>abs(en[0]) else 1;coords=[(256+p[a]*20,256-p[2]*35) for p in ep]
                else:coords=[(256+(p[0]-1.3)*28,256-p[1]*62) for p in ep]
            else:
                axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
                ox,oy=(768,256) if paint=='metal' else (256,768)
                coords=[(ox+p[a]*18,oy-p[b]*30) for p in ep]
            m.polygon_uvs[(paint,i)]=[(u/1024,1-v/1024) for u,v in coords]
    return m
def modeldoc():
    remaps=','.join('{ from = "%s.vmat" to = "%s/street_lamp.vmat" }'%(p,MAT) for p in ('metal','glass','rubber'))
    mesh=','.join('{ _class = "RenderMeshFile" name = "lod%d" filename = "%s/lamp_lod%d.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = { exclude_by_default = false exception_list = [] } }'%(k,MODEL,k) for k in range(3))
    (OUT/'street_lamp.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [%REMAPS%] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [%MESH%] },
{ _class = "LODGroupList" children = [
{ _class = "LODGroup" switch_threshold = 0 meshes = ["lod0"] },
{ _class = "LODGroup" switch_threshold = 22 meshes = ["lod1"] },
{ _class = "LODGroup" switch_threshold = 55 meshes = ["lod2"] }
] } ] } }
'''.replace('%REMAPS%',remaps).replace('%MESH%',mesh))
if __name__=='__main__':
    paint();counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'lamp_lod{k}.obj',make(k),'street_lamp'))
    modeldoc()
    (TEX/'street_lamp.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 F_SELF_ILLUM 1
 TextureColor "%MAT%/lamp_color.png"
 TextureNormal "%MAT%/lamp_normal.png"
 TextureRoughness "%MAT%/lamp_rough.png"
 TextureMetalness "%MAT%/lamp_metal.png"
 TextureSelfIllumMask "%MAT%/lamp_glow.png"
 g_flSelfIllumBrightness "3.0"
 g_flSelfIllumAlbedoFactor "1"
 g_vSelfIllumTint "[1 0.85 0.60 0]"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[1024,1024],installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
