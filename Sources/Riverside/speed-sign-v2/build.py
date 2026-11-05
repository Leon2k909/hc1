"""A formed, bolted speed sign on a perforated U-channel post. Review only."""
from pathlib import Path
import json, math, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT=Path(sys.argv[1]).resolve()
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
K.obj_vector=lambda p:f'{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}'
MODEL='models/props/riverside/speed_sign_v2'
MAT='materials/riverside/speed_sign_v2'
OUT=ROOT/'Assets'/MODEL
TEX=ROOT/'Assets'/MAT
REPORT=ROOT/'output/asset-improvement-20261030/riverside-speed-sign'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
S=1024
def field(shape,sigma,seed):
    a=ndi.gaussian_filter(np.random.default_rng(seed).normal(size=shape),sigma,mode='wrap')
    return a/(3*a.std()+1e-8)
def paint():
    y,x=np.mgrid[:S,:S]
    cloud=field((S,S),10,17)
    grain=field((S,S),.65,18)
    colour=np.ones((S,S,3))*.46
    rough=np.ones((S,S))*.59
    metal=np.ones((S,S))*.75
    height=grain*.0008
    original=np.asarray(Image.open(ROOT/'Assets/materials/riverside/rs_signs_color.png').convert('RGB').crop((0,0,512,640)),float)/255
    # Retain the existing artwork and its wear; add dirt only at the real fixings and lower edge.
    colour[:640,:512]=original
    rough[:640,:512]=.58+.07*cloud[:640,:512]
    metal[:640,:512]=.05
    for z in (80.2,106.2):
        py=(108-z)/30*640
        stain=np.exp(-((x-256)/8)**2)*np.exp(-np.maximum(y-py,0)/50)*(y>=py)*(y<640)*(x<512)*.38
        colour=colour*(1-stain[:,:,None])+np.array((.28,.15,.07))*stain[:,:,None]
        rough+=stain*.2
    # Zinc spangle on the rear and post; never a normal-map displacement of the sign lettering.
    zinc=field((640,512),1.8,24)+.45*field((640,512),7,25)
    colour[:640,512:]=np.array((.40,.43,.44))*(1+.10*zinc[:,:,None])
    rough[:640,512:]=np.clip(.55+.09*zinc,.35,.8)
    colour[672:]=np.array((.34,.37,.37))*(1+.10*cloud[672:,:,None]+.04*grain[672:,:,None])
    rough[672:]=.57+.08*cloud[672:]
    # Post base corrosion occupies the first two feet, according to physical height mapping.
    dirt=np.clip((y[672:]-912)/100,0,1)*np.clip(.5+cloud[672:],0,1)*.6
    colour[672:]=colour[672:]*(1-dirt[:,:,None])+np.array((.19,.13,.075))*dirt[:,:,None]
    metal[672:] *= 1-dirt
    dy,dx=np.gradient(height)
    normal=np.stack((-dx*28,dy*28,np.ones_like(height)),-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    for name,a in (('color',colour),('normal',normal*.5+.5),('rough',rough),('metal',metal)):
        Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(TEX/f'sign_{name}.png')
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def make(lod):
    m=K.Model()
    def box(c,size):
        if lod==2:m.oriented_box(plan(c),(X,Y,Z),size,'post')
        else:G.bevel_box(m,plan(c),(X,Y,Z),size,'post',bevel=min(.035,min(size)*.25))
    def cylinder(c,axis,length,radius,sides=None):
        G.lathe_axis(m,plan(c),plan(axis),[(0,0),(radius,0),(radius,length),(0,length)],'post',sides=sides or (12,8,6)[lod])
    def poly(points,paint):
        # Fan triangulation with per-triangle normals avoids warped rounded-corner shading.
        for j in range(1,len(points)-1):m.polygon(paint,[plan(points[k]) for k in (0,j,j+1)])
    # Real perforations in the web, open U-channel facing the rear.
    if lod==0:
        corner=math.atan2(1,1.1)
        angles=(0,corner,math.pi/2,math.pi-corner,math.pi,math.pi+corner,3*math.pi/2,2*math.pi-corner)
        sides=len(angles)
        # Each plate cell is a rectangular rim around a circular hole, extruded .12 inch.
        for z in np.arange(2.2,109,2):
            outer=[];inner=[]
            for a in angles:
                cy,sz=math.cos(a),math.sin(a)
                scale=1/max(abs(cy)/1.1,abs(sz)/1)
                outer.append((cy*scale,z+sz*scale));inner.append((cy*.23,z+sz*.23))
            for k in range(sides):
                j=(k+1)%sides
                for px,reverse in ((.06,False),(-.06,True)):
                    q=[(px,*v) for v in (outer[k],outer[j],inner[j],inner[k])]
                    poly(q[::-1] if reverse else q,'post')
                poly([(.06,*inner[k]),(.06,*inner[j]),(-.06,*inner[j]),(-.06,*inner[k])],'post')
        box((0,-1.175,55),(.12,.15,110));box((0,1.175,55),(.12,.15,110))
    else:box((0,0,55),(.12,2.5,110))
    for y in (-1.25,1.25):
        box((-.36,y,55),(.84,.16,110))
        box((-.79,y*1.08,55),(.15,.42,110))
    # Rounded sheet, shallow formed rim, a small bend near the top corner.
    outline=[]
    r=1.25
    for cy,cz,start in ((10.75,106.75,0),(-10.75,106.75,90),(-10.75,79.25,180),(10.75,79.25,270)):
        for a in np.linspace(start,start+90,(5,4,3)[lod],endpoint=False):
            t=math.radians(a);outline.append((cy+r*math.cos(t),cz+r*math.sin(t)))
    def depth(y,z):return 1.62+.14*(y/12)**2+.20*max(0,(z-99)/9)**2*max(0,y/12)
    front=[(depth(y,z)+.08,y,z) for y,z in outline]
    back=[(depth(y,z)-.08,y,z) for y,z in outline]
    # centre fan makes bending local and guarantees convex triangulation.
    for k in range(len(outline)):
        j=(k+1)%len(outline)
        poly([(1.70,0,93),front[k],front[j]],'front')
        poly([(1.54,0,93),back[j],back[k]],'back')
        poly([front[k],back[k],back[j],front[j]],'edge')
    # Two through bolts, front washers and rear nut plates/stand-offs.
    for z in (80.2,106.2):
        box((.55,0,z),(.30,5,1.2))
        cylinder((.7,0,z),(1,0,0),1.20,.17)
        cylinder((1.76,0,z),(1,0,0),.07,.48)
        cylinder((1.83,0,z),(1,0,0),.20,.30,sides=6)
        cylinder((.26,0,z),(-1,0,0),.24,.29,sides=6)
        if lod==0:
            for y in (-1.6,1.6):cylinder((.75,y,z),(1,0,0),.06,.16)
    for paint,polygons in m.polygons.items():
        m.material_overrides[paint]=MAT+'/speed_sign.vmat'
        m.tile_overrides[paint]=16
        for i,(points,n) in enumerate(polygons):
            ep=[K.to_world(p) for p in points];en=K.to_world(n)
            if paint in ('front','back'):
                coords=[((p[1]+12)/24*512 + (512 if paint=='back' else 0),(108-p[2])/30*640) for p in ep]
            else:
                axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
                coords=[(512+p[a]*20,(1008 if b==2 else 840)-p[b]*2.8) for p in ep]
            m.polygon_uvs[(paint,i)]=[(u/S,1-v/S) for u,v in coords]
    return m
def modeldoc():
    remaps=','.join('{ from = "%s.vmat" to = "%s/speed_sign.vmat" }'%(p,MAT) for p in ('front','back','edge','post'))
    mesh=','.join('{ _class = "RenderMeshFile" name = "lod%d" filename = "%s/sign_lod%d.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = { exclude_by_default = false exception_list = [] } }'%(k,MODEL,k) for k in range(3))
    (OUT/'speed_sign.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
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
    for k in range(3):counts.append(K.write_obj(OUT/f'sign_lod{k}.obj',make(k),'speed_sign'))
    modeldoc()
    (TEX/'speed_sign.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 TextureColor "%MAT%/sign_color.png"
 TextureNormal "%MAT%/sign_normal.png"
 TextureRoughness "%MAT%/sign_rough.png"
 TextureMetalness "%MAT%/sign_metal.png"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[S,S],installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
