"""Low mushroom roof vent with open screened neck and roof-matched flashing."""
from pathlib import Path
import json,math,sys
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
K.obj_vector=lambda p:f'{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}'
MODEL='models/props/riverside/roof_vent_v1';MAT='materials/riverside/roof_vent_v1'
OUT=ROOT/'Assets'/MODEL;TEX=ROOT/'Assets'/MAT;REPORT=ROOT/'output/riverside/roof-vent-v1'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
info=json.loads((REPORT/'review.json').read_text())
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def roof(x):return info['roof_intercept']+info['roof_slope']*x
def paint():
    rng=np.random.default_rng(1439);a=rng.normal(size=(1024,1024));yy,xx=np.mgrid[:1024,:1024]
    def field(sig):
        n=ndi.gaussian_filter(a,sig,mode='wrap');return n/(3*n.std())
    cloud=field(16);spangle=field(3);grain=field(.6)
    film=np.clip(.12+.14*cloud,0,.35)
    c=np.array((.43,.46,.45))*(1+.065*spangle[:,:,None]+.018*grain[:,:,None])
    c=c*(1-film[:,:,None])+np.array((.20,.22,.16))*film[:,:,None]
    rough=np.clip(.42+.10*cloud+.04*spangle,.26,.70);metal=np.ones_like(a)*.82
    c[:,700:870]=np.array((.10,.105,.09))*(1+.12*cloud[:,700:870,None]);rough[:,700:870]=.78;metal[:,700:870]=0
    c[:,870:]=np.array((.08,.085,.08))*(1+.1*cloud[:,870:,None]);rough[:,870:]=.68;metal[:,870:]=.5
    dy,dx=np.gradient(grain*.00008+spangle*.0002);n=np.stack((-dx*90,dy*90,np.ones_like(a)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    for name,data in (('color',c),('normal',n*.5+.5),('rough',rough),('metal',metal)):
        Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(TEX/f'vent_{name}.png')
    yy,xx=np.mgrid[:512,:512];du=np.minimum(xx%32,32-xx%32);dv=np.minimum(yy%32,32-yy%32)
    mask=np.clip(2.3-np.minimum(du,dv),0,1)
    Image.fromarray(np.uint8(mask*255)).save(TEX/'screen_mask.png')
    Image.new('RGB',(8,8),(72,77,73)).save(TEX/'screen_color.png')
def make(lod):
    m=K.Model();sides=(48,28,16)[lod]
    def rod(a,b,r,mat='metal',n=None):G.rod(m,plan(a),plan(b),r,mat,sides=n or (12,8,6)[lod],caps=True)
    # A pitched sheet-metal flashing follows the actual existing roof under this vent.
    corners=[(-8,-8),(-8,8),(8,8),(8,-8)]
    for zoff,normal in ((.10,Z),(.01,-Z)):
        G.card(m,'metal',[plan((x,y,roof(x)+zoff)) for x,y in corners],normal)
    for (x,y),(xx,yy) in zip(corners,corners[1:]+corners[:1]):
        G.card(m,'metal',[plan((x,y,roof(x)+.01)),plan((xx,yy,roof(xx)+.01)),plan((xx,yy,roof(xx)+.10)),plan((x,y,roof(x)+.10))],plan((x+xx,y+yy,0)))
    # Sealant bead and raised curb, with its bottom continuously meeting the pitch.
    for k in range(sides):
        a,b=2*math.pi*k/sides,2*math.pi*(k+1)/sides
        p=np.array((4.35*math.cos(a),4.35*math.sin(a),0));q=np.array((4.35*math.cos(b),4.35*math.sin(b),0))
        G.card(m,'seal',[plan((p[0],p[1],roof(p[0])+.11)),plan((q[0],q[1],roof(q[0])+.11)),plan((q[0]*.90,q[1]*.90,roof(q[0]*.9)+.30)),plan((p[0]*.90,p[1]*.90,roof(p[0]*.9)+.30))],Z)
        G.card(m,'metal',[plan((p[0]*.9,p[1]*.9,roof(p[0]*.9)+.30)),plan((q[0]*.9,q[1]*.9,roof(q[0]*.9)+.30)),plan((q[0]*.9,q[1]*.9,.90)),plan((p[0]*.9,p[1]*.9,.90))],plan((p[0]+q[0],p[1]+q[1],0)))
    # Screened intake band is genuinely open, with no solid wall hidden behind it.
    r=3.88
    for k in range(sides):
        a,b=2*math.pi*k/sides,2*math.pi*(k+1)/sides
        pts=[(r*math.cos(a),r*math.sin(a),.88),(r*math.cos(b),r*math.sin(b),.88),(r*math.cos(b),r*math.sin(b),2.65),(r*math.cos(a),r*math.sin(a),2.65)]
        uv=[(r*a/2,.44),(r*b/2,.44),(r*b/2,1.325),(r*a/2,1.325)]
        G.card(m,'screen',[plan(p) for p in pts],plan((math.cos((a+b)/2),math.sin((a+b)/2),0)),uv=uv,both=True)
    # Lower rolled ring, inner dark throat, and the overhanging rain hood with a hemmed edge.
    G.lathe_axis(m,(0,0,0),Z,[(3.65,.75),(4.0,.75),(4.08,.86),(4.0,1.0),(3.7,1.0)],'metal',sides=sides)
    G.lathe_axis(m,(0,0,0),Z,[(3.5,.4),(3.5,.9),(3.44,.9),(3.44,.4)],'dark',sides=sides)
    profile=[(6.7,2.70),(6.94,2.75),(7.0,2.88),(6.97,3.02),(6.82,3.13),(6.35,3.30),(5.5,3.66),(4.4,4.00),(2.7,4.25),(0,4.34)]
    if lod==1:profile=[profile[i] for i in (0,2,4,6,7,8,9)]
    elif lod==2:profile=[profile[i] for i in (0,2,4,7,9)]
    G.lathe_axis(m,(0,0,0),Z,profile,'hood',sides=sides)
    G.lathe_axis(m,(0,0,0),Z,[(0,4.25),(2.7,4.16),(4.4,3.91),(5.5,3.57),(6.8,3.05),(6.7,2.70)],'metal',sides=sides)
    # Three support straps connect curb and hood; washer/hex screws retain the cap.
    for angle in (0,120,240):
        a=math.radians(angle);d=np.array((math.cos(a),math.sin(a),0));t=np.array((-d[1],d[0],0))
        G.extrude(m,plan(tuple(d*3.8+np.array((0,0,.7)))),plan(tuple(d*5.2+np.array((0,0,3.35)))),[(-.26,-.07),(.26,-.07),(.26,.07),(-.26,.07)],'metal',up=plan(t),caps=True)
        if lod<2:rod(tuple(d*5.4+np.array((0,0,3.61))),tuple(d*5.4+np.array((0,0,3.78))),.22,n=6)
    for x,y in ((-7,-7),(-7,7),(7,-7),(7,7),(0,-7),(0,7),(-7,0),(7,0)):
        z=roof(x)+.10
        rod((x,y,z),(x,y,z+.055),.27,n=(16,10,6)[lod]);rod((x,y,z+.055),(x,y,z+.20),.18,n=6)
        if lod==0:
            G.tube(m,[plan((x-.09,y,z+.205)),plan((x+.09,y,z+.205))],.025,'dark',sides=4)
    # Smooth only the pressed hood across profile transitions, retaining crisp fasteners.
    sums={}
    for i,(pts,n) in enumerate(m.polygons['hood']):
        ns=m.polygon_normals.get(('hood',i))
        for j,p in enumerate(pts):
            key=tuple(np.round(p,6));sums[key]=sums.get(key,np.zeros(3))+(ns[j] if ns else n)
    for i,(pts,n) in enumerate(m.polygons['hood']):m.polygon_normals[('hood',i)]=[K.normalise(sums[tuple(np.round(p,6))]) for p in pts]
    for mat,polys in m.polygons.items():
        m.material_overrides[mat]=MAT+('/screen.vmat' if mat=='screen' else '/vent.vmat');m.tile_overrides[mat]=16
        if mat=='screen':continue
        lo,hi=(20,675) if mat in ('metal','hood') else ((720,850) if mat=='seal' else (890,1000))
        for i,(pts,n) in enumerate(polys):
            ep=np.array([K.to_world(p) for p in pts]);en=K.to_world(n);axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
            if mat=='hood':
                # One continuous top projection: no per-face swatches across the pressed canopy.
                m.polygon_uvs[(mat,i)]=[((350+p[0]*42)/1024,1-(512+p[1]*42)/1024) for p in ep]
                continue
            if mat=='metal':
                m.polygon_uvs[(mat,i)]=[((350+p[a]*35)/1024,1-(512+p[b]*35)/1024) for p in ep]
                continue
            low=ep.min(0);span=max(float(np.ptp(ep[:,a])),float(np.ptp(ep[:,b])),1);scale=min(35,(hi-lo-8)/span)
            m.polygon_uvs[(mat,i)]=[((lo+4+(p[a]-low[a])*scale)/1024,1-(120+(i*31)%160+(p[b]-low[b])*scale)/1024) for p in ep]
    return m
if __name__=='__main__':
    paint();counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'vent_lod{k}.obj',make(k),'roof_vent'))
    remaps=','.join('{from="%s.vmat" to="%s/%s.vmat"}'%(p,MAT,'screen' if p=='screen' else 'vent') for p in ('metal','hood','seal','dark','screen'))
    meshes=','.join('{_class="RenderMeshFile" name="lod%d" filename="%s/vent_lod%d.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}'%(i,MODEL,i) for i in range(3))
    (OUT/'vent.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},{_class="RenderMeshList" children=[%M%]},{_class="LODGroupList" children=[{_class="LODGroup" switch_threshold=0 meshes=["lod0"]},{_class="LODGroup" switch_threshold=18 meshes=["lod1"]},{_class="LODGroup" switch_threshold=45 meshes=["lod2"]}]}]}}
'''.replace('%R%',remaps).replace('%M%',meshes))
    (TEX/'vent.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 TextureColor "%MAT%/vent_color.png"
 TextureNormal "%MAT%/vent_normal.png"
 TextureRoughness "%MAT%/vent_rough.png"
 TextureMetalness "%MAT%/vent_metal.png"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    (TEX/'screen.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_ALPHA_TEST 1
 F_SPECULAR 1
 TextureColor "%MAT%/screen_color.png"
 TextureTranslucency "%MAT%/screen_mask.png"
 TextureNormal "materials/default/default_normal.tga"
 g_flAlphaTestReference ".35"
 g_flAntiAliasedEdgeStrength "1"
 g_flMetalness ".6"
 g_flRoughnessScaleFactor ".7"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[1024,1024],screen_mask=[512,512],materials=2,roof_intercept=info['roof_intercept'],roof_slope=info['roof_slope'],installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
