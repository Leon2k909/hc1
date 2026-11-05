"""Weathered aluminum trailer entry door; the original map window remains in place."""
from pathlib import Path
import json,math,sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
K.obj_vector=lambda p:f'{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}'
MODEL='models/props/riverside/trailer_door_v1';MAT='materials/riverside/trailer_door_v1'
OUT=ROOT/'Assets'/MODEL;TEX=ROOT/'Assets'/MAT;REPORT=ROOT/'output/riverside/trailer-door-v1'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def paint():
    rng=np.random.default_rng(7201);a=rng.normal(size=(1024,1024));yy,xx=np.mgrid[:1024,:1024]
    def field(sig):
        n=ndi.gaussian_filter(a,sig,mode='wrap');return n/(3*n.std())
    cloud=field(16);grain=field(.7);streak=field((40,1.6))
    c=np.ones((1024,1024,3))*np.array((.64,.63,.57))
    hand=np.exp(-((xx-479)/28)**2-((yy-493)/47)**2)
    hinge_drips=sum(np.exp(-((xx-58)/10)**2)*np.exp(-np.maximum(yy-y,0)/95)*(yy>y) for y in (190,470,750))
    dirt=np.clip(.055+.05*cloud+.018*streak+.23*hand+.14*hinge_drips+np.clip((yy-690)/300,0,1)*.34,0,.48)
    c=c*(1-dirt[:,:,None])+np.array((.16,.14,.10))*dirt[:,:,None]
    edge=np.clip((abs(xx-300)-238)/28,0,1)*(field(2)>.1)
    chips=(field(.5)>.55)*edge
    c=c*(1-chips[:,:,None]*.55)+np.array((.25,.27,.25))*chips[:,:,None]*.55
    rough=np.clip(.59+.10*cloud+.10*dirt,.38,.85);metal=np.ones((1024,1024))*.05
    c[:,608:800]=np.array((.37,.40,.40))*(1+.12*cloud[:,608:800,None]+.02*grain[:,608:800,None])
    rough[:,608:800]=np.clip(.38+.12*cloud[:,608:800],.23,.65);metal[:,608:800]=.84
    c[:,800:928]=np.array((.035,.039,.037))*(1+.15*cloud[:,800:928,None]);rough[:,800:928]=.73;metal[:,800:928]=.05
    c[:,928:]=np.array((.24,.18,.12))*(1+.15*cloud[:,928:,None]);rough[:,928:]=.72;metal[:,928:]=.35
    dy,dx=np.gradient(grain*.0001+cloud*.0003);n=np.stack((-dx*75,dy*75,np.ones_like(a)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    for name,data in (('color',c),('normal',n*.5+.5),('rough',rough),('metal',metal)):
        Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(TEX/f'door_{name}.png')
def make(lod):
    m=K.Model();sides=(20,12,6)[lod]
    def box(c,s,mat='paint'):m.oriented_box(plan(c),(X,Y,Z),s,mat)
    def rod(a,b,r,mat='metal',n=None):G.rod(m,plan(a),plan(b),r,mat,sides=n or sides,caps=True)
    def screw(y,z,x=1.36):
        rod((x-.08,y,z),(x+.02,y,z),.12,n=(12,8,6)[lod])
        if lod==0:box((x+.025,y,z),(.012,.17,.028),'rubber')
    # Complete thickness on jambs/header/threshold, with a dark continuous weather seal.
    for y in (-16.7,16.7):box((.55,y,38),(1.1,1.6,78),'metal')
    box((.55,0,76.3),(1.1,32,1.4),'metal');box((.85,0,.3),(1.7,33,1),'metal')
    for y in (-15.8,15.8):box((.72,y,38),(.30,.24,75.4),'rubber')
    for z in (.7,75.3):box((.72,0,z),(.30,31.5,.24),'rubber')
    # Infill surrounds a real opening; the original lit/dark window is never covered.
    for y in (-11.8,11.8):box((.52,y,38),(.3,7.6,74.6))
    box((.52,0,23.48),(.3,16,45.76));box((.52,0,69.24),(.3,16,12.32))
    # Raised perimeter pressing and a recessed lower panel.
    for y in (-14.8,14.8):box((.79,y,38),(.18,.45,72.6))
    for z in (1.7,74.3):box((.79,0,z),(.18,29.6,.45))
    for y in (-12.7,12.7):box((.78,y,25),(.2,.35,33.5))
    for z in (8.25,41.75):box((.78,0,z),(.2,25.4,.35))
    # Black rubber window gasket and rounded metal bezel, matching the original pane.
    def rect_loop(x,half_w,bottom,top,r,mat):
        pts=[]
        for cy,cz,start in ((half_w-r,top-r,0),(-half_w+r,top-r,90),(-half_w+r,bottom+r,180),(half_w-r,bottom+r,270)):
            for angle in np.linspace(start,start+90,(7,5,3)[lod],endpoint=False):
                a=math.radians(angle);pts.append((x,cy+r*math.cos(a),cz+r*math.sin(a)))
        G.tube(m,[plan(p) for p in pts],.28 if mat=='metal' else .26,mat,sides=(8,6,4)[lod],closed=True,bend_radius=0)
    rect_loop(.76,8.25,46.1,63.34,.65,'rubber');rect_loop(.95,8.72,45.63,63.81,.9,'metal')
    if lod<2:
        for y in (-8.7,8.7):
            for z in (47,54.72,62.4):screw(y,z,1.19)
    # Three real hinge leaves/barrels, alternating knuckles and end caps.
    for z in (10,38,66):
        box((1.16,-15.95,z),(.18,2.7,4.3),'metal')
        for k in range(5):
            rod((1.46,-16.15,z-2+k*.8),(1.46,-16.15,z-1.26+k*.8),.34,'metal')
        rod((1.46,-16.15,z-2.25),(1.46,-16.15,z+2.25),.12)
        if lod<2:
            for zz in (z-1.35,z+1.35):screw(-15.10,zz,1.31)
    # Recessed paddle latch and separate deadbolt, at the original handle height.
    box((.90,11.15,35.72),(.26,3.7,5.1),'rubber')
    box((1.06,11.15,35.72),(.14,3.35,4.75),'metal')
    box((1.15,11.15,35.50),(.05,2.45,2.3),'rubber')
    box((1.36,11.15,36.12),(.36,2.45,.88),'metal')
    rod((1.18,11.15,37.20),(1.30,11.15,37.20),.42)
    box((1.315,11.15,37.20),(.02,.045,.27),'rubber')
    rod((.86,11.15,43),(1.04,11.15,43),.77)
    rod((1.04,11.15,43),(1.15,11.15,43),.53)
    box((1.17,11.15,43),(.025,.06,.36),'rubber')
    if lod<2:
        for y in (9.75,12.55):
            for z in (33.85,37.6):screw(y,z,1.18)
    # Worn kick plate, mounting screws and tread grooves at the sill.
    box((.77,0,5.1),(.18,28.8,6.5),'metal')
    if lod<2:
        for y in (-13.6,13.6):
            for z in (2.7,7.4):screw(y,z,.91)
        for x in (1.10,1.40):box((x,0,.82),(.06,30,.05),'rubber')
    # Small rain cap over the door; rolled front lip and screw heads.
    box((1.1,0,77.5),(2.2,35.4,.22),'metal');box((2.10,0,77.20),(.16,35.4,.7),'metal')
    if lod<2:
        for y in (-16.7,16.7):
            for z in (5,25,51,73):screw(y,z,1.13)
    regions={'metal':(630,778),'rubber':(816,912),'worn':(943,1007)}
    for mat,polys in m.polygons.items():
        m.material_overrides[mat]=MAT+'/door.vmat';m.tile_overrides[mat]=32
        for i,(pts,n) in enumerate(polys):
            ep=np.array([K.to_world(p) for p in pts]);en=K.to_world(n)
            if mat=='paint' and abs(en[0])>.9:
                coords=[((300+p[1]*16)/1024,1-(90+(76-p[2])*10)/1024) for p in ep]
            else:
                lo,hi=regions.get(mat,(30,575));axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
                low=ep.min(0);span=max(float(np.ptp(ep[:,a])),float(np.ptp(ep[:,b])),1);scale=min(35,(hi-lo-8)/span)
                coords=[((lo+4+(p[a]-low[a])*scale)/1024,1-(70+(i*29)%180+(p[b]-low[b])*scale)/1024) for p in ep]
            m.polygon_uvs[(mat,i)]=coords
    return m
if __name__=='__main__':
    paint();counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'door_lod{k}.obj',make(k),'trailer_door'))
    remaps=','.join('{from="%s.vmat" to="%s/door.vmat"}'%(p,MAT) for p in ('paint','metal','rubber','worn'))
    meshes=','.join('{_class="RenderMeshFile" name="lod%d" filename="%s/door_lod%d.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}'%(i,MODEL,i) for i in range(3))
    (OUT/'door.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},{_class="RenderMeshList" children=[%M%]},{_class="LODGroupList" children=[{_class="LODGroup" switch_threshold=0 meshes=["lod0"]},{_class="LODGroup" switch_threshold=20 meshes=["lod1"]},{_class="LODGroup" switch_threshold=50 meshes=["lod2"]}]}]}}
'''.replace('%R%',remaps).replace('%M%',meshes))
    (TEX/'door.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 TextureColor "%MAT%/door_color.png"
 TextureNormal "%MAT%/door_normal.png"
 TextureRoughness "%MAT%/door_rough.png"
 TextureMetalness "%MAT%/door_metal.png"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[1024,1024],materials=1,original_window_retained=True,installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
