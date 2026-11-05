"""Compact caged bulkhead fixture; review resources only, existing lights retained."""
from pathlib import Path
import json,math,sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT=Path(sys.argv[1]).resolve()
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
K.obj_vector=lambda p:f'{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}'
MODEL='models/props/riverside/porch_light_v2';MAT='materials/riverside/porch_light_v2'
OUT=ROOT/'Assets'/MODEL;TEX=ROOT/'Assets'/MAT
REPORT=ROOT/'output/asset-improvement-20261030/riverside-porch-light'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
def field(sigma,seed):
    a=ndi.gaussian_filter(np.random.default_rng(seed).normal(size=(1024,1024)),sigma,mode='wrap')
    return a/(3*a.std()+1e-8)
def paint():
    y,x=np.mgrid[:1024,:1024].astype(float)
    cloud=field(13,33);speck=field(.6,34)
    c=np.ones((1024,1024,3))*.19
    c*=1+.06*cloud[:,:,None]+.018*speck[:,:,None]
    r=np.clip(.65+.06*cloud,.4,.9);metal=np.ones_like(r)*.35;glow=np.zeros_like(r)
    # Dusty warm frosted prismatic lens, mapped upright at physical size.
    u=(x[:512,:512]-256)/240;v=(y[:512,:512]-256)/240
    edge=np.clip((u*u+v*v-.35)/.65,0,1)
    c[:512,:512]=np.array((.74,.67,.49))*(1-.25*edge[:,:,None])*(1+.025*cloud[:512,:512,None])
    r[:512,:512]=.34+.06*edge;metal[:512,:512]=0
    glow[:512,:512]=.38*(1-.50*edge)
    # Fine flutes and frost relief; no opaque painted cage lines on the glass.
    h=.0005*speck
    h[:512,:512]+=.0035*np.sin(2*math.pi*x[:512,:512]/21)
    # Aged zinc on the screws, black rubber gasket in a separate lower-left patch.
    c[560:1024,:512]=np.array((.035,.038,.033))*(1+.07*cloud[560:,:512,None])
    r[560:,:512]=.88;metal[560:,:512]=0
    # Restrained green film and worn specks on the cast metal surfaces.
    moss=np.clip(cloud-.35,0,.45)*.25
    c[:,512:]=c[:,512:]*(1-moss[:,512:,None])+np.array((.16,.20,.12))*moss[:,512:,None]
    chip=np.clip((speck-.50)*2,0,1)*np.clip(cloud+.2,0,1)*.3
    c[:,512:]=c[:,512:]*(1-chip[:,512:,None])+np.array((.38,.34,.26))*chip[:,512:,None]
    dy,dx=np.gradient(h)
    n=np.stack((-dx*96,dy*96,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    for name,a in (('color',c),('normal',n*.5+.5),('rough',r),('metal',metal),('glow',glow)):
        Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(TEX/f'lamp_{name}.png')
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def make(lod):
    m=K.Model();sides=(32,16,8)[lod]
    def oval(profile,paint):
        part=K.Model();G.lathe_axis(part,(0,0,0),X,profile,paint,sides=sides)
        for _,polys in part.polygons.items():
            for i,(points,normal) in enumerate(polys):
                ep=[K.to_world(p)*np.array((1,2.25,2.8)) for p in points]
                smooth=part.polygon_normals.get((paint,i))
                ns=[]
                for j,p in enumerate(ep):
                    if paint=='glass' and p[0]>=-.20001:
                        n=np.array(((p[0]+.2)/1.75**2,p[1]/(2.25*.84)**2,p[2]/(2.8*.84)**2))
                    else:n=K.to_world(smooth[j] if smooth else normal)/np.array((1,2.25,2.8))
                    ns.append(plan(n))
                m.polygon(paint,[plan(p) for p in ep],normal=plan(K.to_world(normal)/np.array((1,2.25,2.8))),normals=ns)
    oval([(0,-2),(.84,-2),(.96,-1.85),(1,-1.6),(.98,-1.1),(.88,-.8),(0,-.8)],'metal')
    oval([(1,-1.1),(1.02,-.85),(1,-.55),(.92,-.4),(.84,-.45),(.84,-.65),(.9,-.85),(1,-1.1)],'metal')
    oval([(.86,-.54),(.88,-.40),(.86,-.28),(.82,-.30),(.82,-.45),(.86,-.54)],'rubber')
    angles=np.linspace(0,math.pi/2,(10,6,4)[lod])
    oval([(0,-.4),(.84,-.4)]+[(.84*math.cos(a),-.2+1.75*math.sin(a)) for a in angles],'glass')
    def box(c,size,paint='metal'):
        if lod==2:m.oriented_box(plan(c),(X,Y,Z),size,paint)
        else:G.bevel_box(m,plan(c),(X,Y,Z),size,paint,bevel=min(.08,min(size)*.2))
    def screw(c):
        G.lathe_axis(m,plan(c),X,[(0,0),(.22,0),(.22,.08),(.17,.14),(0,.14)],'metal',sides=(16,10,6)[lod])
        if lod==0:box((c[0]+.141,c[1],c[2]),(.012,.24,.035),'rubber')
    for y in (-2.15,2.15):
        box((-.9,y,0),(.7,.65,.82));screw((-.54,y,0))
    # Guard's rim and three arched rods follow the glass, with clearance at the crown.
    seg=(32,16,8)[lod]
    G.tube(m,[plan((.40,2.25*.91*math.cos(a),2.8*.91*math.sin(a))) for a in np.linspace(0,2*math.pi,seg,endpoint=False)],.095,'metal',sides=(8,6,4)[lod],closed=True)
    def lens_x(y,z):return max(.4,-.2+1.75*math.sqrt(max(0,1-(y/(2.25*.84))**2-(z/(2.8*.84))**2))+.18)
    for z in (-.72,.72):
        extent=2.25*.91*math.sqrt(1-(z/(2.8*.91))**2)
        pts=[plan((lens_x(y,z),y,z)) for y in np.linspace(-extent,extent,(13,7,4)[lod])]
        G.tube(m,pts,.075,'metal',sides=(8,6,4)[lod])
    pts=[plan((lens_x(0,z),0,z)) for z in np.linspace(-2.8*.91,2.8*.91,(15,9,5)[lod])]
    G.tube(m,pts,.075,'metal',sides=(8,6,4)[lod])
    for paint,polys in m.polygons.items():
        m.material_overrides[paint]=MAT+'/porch_light.vmat';m.tile_overrides[paint]=16
        for i,(pts,n) in enumerate(polys):
            ep=[K.to_world(p) for p in pts];en=K.to_world(n)
            if paint=='glass':
                if abs(en[0])<1e-7:
                    b=2 if abs(en[1])>=abs(en[2]) else 1
                    coords=[(256+p[0]*65,256-p[b]*65) for p in ep]
                else:coords=[(16+(p[1]/4.2+.5)*480,16+(.5-p[2]/5.3)*480) for p in ep]
            else:
                axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
                ox,oy=(768,256) if paint=='metal' else (256,768)
                coords=[(ox+p[a]*65,oy-p[b]*65) for p in ep]
            m.polygon_uvs[(paint,i)]=[(u/1024,1-v/1024) for u,v in coords]
    return m
def modeldoc():
    remaps=','.join('{ from = "%s.vmat" to = "%s/porch_light.vmat" }'%(p,MAT) for p in ('metal','glass','rubber'))
    mesh=','.join('{ _class = "RenderMeshFile" name = "lod%d" filename = "%s/lamp_lod%d.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = { exclude_by_default = false exception_list = [] } }'%(k,MODEL,k) for k in range(3))
    (OUT/'porch_light.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [%REMAPS%] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [%MESH%] },
{ _class = "LODGroupList" children = [
{ _class = "LODGroup" switch_threshold = 0 meshes = ["lod0"] },
{ _class = "LODGroup" switch_threshold = 18 meshes = ["lod1"] },
{ _class = "LODGroup" switch_threshold = 50 meshes = ["lod2"] }
] } ] } }
'''.replace('%REMAPS%',remaps).replace('%MESH%',mesh))
if __name__=='__main__':
    paint();counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'lamp_lod{k}.obj',make(k),'porch_light'))
    modeldoc()
    (TEX/'porch_light.vmat').write_text('''Layer0
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
 g_flSelfIllumBrightness "1.2"
 g_flSelfIllumAlbedoFactor "1"
 g_vSelfIllumTint "[1 0.84 0.60 0]"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[1024,1024],installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
