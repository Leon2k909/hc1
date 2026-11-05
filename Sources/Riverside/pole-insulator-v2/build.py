"""Glazed pin insulator with rain sheds and wire tie. Private review only."""
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
MODEL='models/props/riverside/pole_insulator_v2';MAT='materials/riverside/pole_insulator_v2'
OUT=ROOT/'Assets'/MODEL;TEX=ROOT/'Assets'/MAT
REPORT=ROOT/'output/asset-improvement-20261030/riverside-pole-insulator'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
def field(sigma,seed):
    a=ndi.gaussian_filter(np.random.default_rng(seed).normal(size=(1024,1024)),sigma,mode='wrap')
    return a/(3*a.std()+1e-8)
def paint():
    yy,xx=np.mgrid[:1024,:1024].astype(float)
    cloud=field(14,37);grain=field(.6,38);streak=field((35,2),39)
    c=np.ones((1024,1024,3))*np.array((.19,.079,.033))
    c*=1+.12*cloud[:,:,None]+.015*grain[:,:,None]
    film=np.clip(.06+.05*cloud+.03*streak,0,.18)
    c=c*(1-film[:,:,None])+np.array((.22,.24,.16))*film[:,:,None]
    rough=np.clip(.20+.055*cloud+.15*film,.10,.42);metal=np.zeros_like(rough)
    c[:,600:]=np.array((.40,.43,.43))*(1+.08*cloud[:,600:,None]+.02*grain[:,600:,None])
    rough[:,600:]=np.clip(.43+.07*cloud[:,600:],.28,.7);metal[:,600:]=.88
    h=grain*.00008
    dy,dx=np.gradient(h);n=np.stack((-dx*100,dy*100,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    for name,a in (('color',c),('normal',n*.5+.5),('rough',rough),('metal',metal)):
        Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(TEX/f'insulator_{name}.png')
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def make(lod,wire_tie=True):
    m=K.Model();sides=(24,16,8)[lod]
    profile=[(0,.60),(.48,.60),(.58,.75),(.60,1.05),
             (1.40,1.05),(1.62,1.12),(1.66,1.23),(1.58,1.34),(.85,1.60),(.65,1.73),(.61,1.88),
             (1.36,2.05),(1.60,2.11),(1.64,2.22),(1.54,2.33),(.82,2.58),(.60,2.71),(.58,2.88),
             (1.25,3.05),(1.48,3.13),(1.53,3.24),(1.45,3.35),(.75,3.60),(.58,3.78),
             (.58,4.00),(.78,4.15),(.80,4.30),(.70,4.45),(.50,4.65),(0,4.65)]
    if lod==1:profile=[profile[k] for k in (0,1,3,4,6,7,9,10,11,13,14,16,17,18,20,21,23,24,26,28,29)]
    elif lod==2:profile=[profile[k] for k in (0,1,3,6,9,10,13,16,17,20,23,24,26,28,29)]
    G.lathe_axis(m,(0,0,0),Z,profile,'ceramic',sides=sides)
    # Zinc pin, seating washer and hexagonal fastening nut at the original crossarm surface.
    G.lathe_axis(m,(0,0,0),Z,[(0,0),(.27,0),(.27,.83),(0,.83)],'metal',sides=(16,10,6)[lod])
    G.lathe_axis(m,(0,0,0),Z,[(0,.03),(.55,.03),(.55,.12),(0,.12)],'metal',sides=(20,12,8)[lod])
    G.lathe_axis(m,(0,0,0),Z,[(0,.12),(.39,.12),(.39,.39),(0,.39)],'metal',sides=6)
    # Neck tie and its loop over the existing 0.35-inch-radius wire at Z=5.
    if wire_tie:
        count=(24,16,8)[lod]
        G.tube(m,[plan((.64*math.cos(a),.64*math.sin(a),3.95)) for a in np.linspace(0,2*math.pi,count,endpoint=False)],.055,'metal',sides=(8,6,4)[lod],closed=True)
        tie=[(0,-.64,3.95),(0,-.60,4.6),(0,-.45,5.15),(0,-.25,5.35),(0,0,5.405),(0,.25,5.35),(0,.45,5.15),(0,.60,4.6),(0,.64,3.95)]
        if lod==2:tie=tie[::2]
        G.tube(m,[plan(p) for p in tie],.055,'metal',sides=(8,6,4)[lod])
        if lod==0:
            G.tube(m,[plan(p) for p in ((-.25,-.64,3.95),(-.40,-.63,3.9),(-.53,-.66,3.97),(-.66,-.63,3.9))],.045,'metal',sides=6)
    # Blend the porcelain profile transitions as well as the circumference, keeping metal fittings crisp.
    sums={}
    def vertex_key(p):return tuple(round(float(v),6) for v in p)
    for i,(pts,n) in enumerate(m.polygons['ceramic']):
        ns=m.polygon_normals.get(('ceramic',i))
        for j,p in enumerate(pts):sums[vertex_key(p)]=sums.get(vertex_key(p),np.zeros(3))+(ns[j] if ns else n)
    for i,(pts,n) in enumerate(m.polygons['ceramic']):
        m.polygon_normals[('ceramic',i)]=[K.normalise(sums[vertex_key(p)]) for p in pts]
    for paint,polys in m.polygons.items():
        m.material_overrides[paint]=MAT+'/pole_insulator.vmat';m.tile_overrides[paint]=16
        for i,(pts,n) in enumerate(polys):
            ep=[K.to_world(p) for p in pts];en=K.to_world(n)
            if paint=='ceramic':
                if abs(en[2])>.90:coords=[(280+p[0]*55,500-p[1]*55) for p in ep]
                else:
                    us=[math.atan2(p[1],p[0])/(2*math.pi)+.5 for p in ep]
                    if max(us)-min(us)>.5:us=[u+1 if u<.5 else u for u in us]
                    coords=[(20+480*u,820-p[2]*140-np.linalg.norm(p[:2])*10) for u,p in zip(us,ep)]
            else:
                axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
                coords=[(780+p[a]*60,350-p[b]*50) for p in ep]
            m.polygon_uvs[(paint,i)]=[(u/1024,1-v/1024) for u,v in coords]
    return m
def modeldoc(name='pole_insulator',prefix='insulator'):
    remaps=','.join('{ from = "%s.vmat" to = "%s/pole_insulator.vmat" }'%(p,MAT) for p in ('ceramic','metal'))
    mesh=','.join('{ _class = "RenderMeshFile" name = "lod%d" filename = "%s/%s_lod%d.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = { exclude_by_default = false exception_list = [] } }'%(k,MODEL,prefix,k) for k in range(3))
    (OUT/(name+'.vmdl')).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [%REMAPS%] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [%MESH%] },
{ _class = "LODGroupList" children = [
{ _class = "LODGroup" switch_threshold = 0 meshes = ["lod0"] },
{ _class = "LODGroup" switch_threshold = 18 meshes = ["lod1"] },
{ _class = "LODGroup" switch_threshold = 45 meshes = ["lod2"] }
] } ] } }
'''.replace('%REMAPS%',remaps).replace('%MESH%',mesh))
if __name__=='__main__':
    paint();counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'insulator_lod{k}.obj',make(k),'pole_insulator'))
    modeldoc()
    (TEX/'pole_insulator.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 TextureColor "%MAT%/insulator_color.png"
 TextureNormal "%MAT%/insulator_normal.png"
 TextureRoughness "%MAT%/insulator_rough.png"
 TextureMetalness "%MAT%/insulator_metal.png"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[1024,1024],installed=False,wire_center_height=5.0,ceramic_crown_height=4.65)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
