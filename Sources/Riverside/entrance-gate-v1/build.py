"""Private review: a locked pair of galvanized chain-link entrance gate leaves."""
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
MODEL='models/props/riverside/entrance_gate_v1';MAT='materials/riverside/entrance_gate_v1'
OUT=ROOT/'Assets'/MODEL;TEX=ROOT/'Assets'/MAT;REPORT=ROOT/'output/riverside/entrance-gate-v1'
for p in (OUT,TEX,REPORT):p.mkdir(parents=True,exist_ok=True)
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def paint():
    rng=np.random.default_rng(819);a=rng.normal(size=(1024,1024))
    def field(sig):
        n=ndi.gaussian_filter(a,sig,mode='wrap');return n/(3*n.std())
    broad=field(18);fine=field(.7);spangle=field(3)
    c=np.zeros((1024,1024,3));rough=np.ones((1024,1024))*.55;metal=np.ones_like(rough)*.82
    for sl,base in ((slice(0,512),(.38,.42,.43)),(slice(512,768),(.21,.16,.115)),(slice(768,928),(.40,.28,.10)),(slice(928,1024),(.055,.06,.059))):
        c[:,sl]=np.array(base)*(1+.18*broad[:,sl,None]+.07*spangle[:,sl,None]+.018*fine[:,sl,None])
    stain=np.clip((broad-.15)*.4,0,.3)
    c[:,:512]=c[:,:512]*(1-stain[:,:512,None])+np.array((.17,.10,.045))*stain[:,:512,None]
    rough=np.clip(rough+.12*broad+.055*spangle,.28,.84);rough[:,768:928]=np.clip(.37+.12*broad[:,768:928],.22,.65)
    metal[:,512:768]=.55;metal[:,768:928]=.78;metal[:,928:]=.25
    dy,dx=np.gradient(fine*.00012+spangle*.00025)
    n=np.stack((-dx*90,dy*90,np.ones_like(a)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    for name,data in (('color',c),('rough',rough),('metal',metal),('normal',n*.5+.5)):
        Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(TEX/f'gate_{name}.png')
def make(lod):
    m=K.Model();sides=(16,10,6)[lod]
    def rod(a,b,r,mat='galv',n=None):G.rod(m,plan(a),plan(b),r,mat,sides=n or sides,caps=True)
    def tube(pts,r,mat='galv',closed=False):G.tube(m,[plan(p) for p in pts],r,mat,sides=(8,6,4)[lod],closed=closed,bend_radius=0)
    def box(c,size,mat='galv'):
        m.oriented_box(plan(c),(X,Y,Z),size,mat)
    def bolt(x,y,z):
        rod((x-.15,y,z),(x+.15,y,z),.28,'galv',6)
        if lod==0:rod((x-.23,y,z),(x-.17,y,z),.39,'galv',12)
    # Original opening width/height and barbed-wire envelope are retained.
    for y in (-220,220):
        G.lathe_axis(m,plan((0,y,0)),Z,[(0,0),(1.6,0),(1.6,80.5),(1.8,80.5),(1.8,81),(1.6,82),(0,82.5)],'galv',sides=sides)
        for z in (18,66):
            rod((0,y,z-2),(0,y,z+2),2,'galv')
            rod((1.9,y,z),(2.2,y,z),.7,'worn',6)
            yy=y-math.copysign(3,y)
            rod((1.8,y,z),(1.8,yy,z),.65)
            rod((1.8,yy,z-2.8),(1.8,yy,z+2.8),.7,'worn')
            bolt(2.55,y,z)
    # Two rounded pipe frames with bracing and actual mesh tension bars.
    for lo,hi in ((-216,-2),(2,216)):
        corners=[(0,lo+3,4),(0,hi-3,4),(0,hi,7),(0,hi,76),(0,hi-3,79),(0,lo+3,79),(0,lo,76),(0,lo,7)]
        G.tube(m,[plan(p) for p in corners],.9,'galv',sides=sides,closed=True,bend_radius=2.5)
        start=np.array((-.6,lo+1,78 if hi<0 else 5));end=np.array((-.6,hi-1,5 if hi<0 else 78))
        rod(start,end,.32)
        mid=(start+end)/2;direction=(end-start)/np.linalg.norm(end-start)
        rod(mid-direction*3,mid+direction*3,.6,'worn')
        for y in (lo+2.2,hi-2.2):
            box((-.15,y,41.5),(.22,.65,70),'worn')
            for z in (12,34,56,72):
                box((.15,y, z),(.25,3.1,.55))
                if lod<2:bolt(.42,y,z)
        pts=[(-.5,lo+2,6),(-.5,hi-2,6),(-.5,hi-2,77),(-.5,lo+2,77)]
        uv=[(p[1]/24,p[2]/24) for p in pts]
        G.card(m,'mesh',[plan(p) for p in pts],X,uv=uv,both=True)
        if lod<2:
            for y in np.arange(lo+12,hi-6,24):
                for z in (4,79):
                    tube([(1.02*math.cos(a),y+.12*math.sin(a),z+1.02*math.sin(a)) for a in np.linspace(0,2*math.pi,9,endpoint=False)],.07,closed=True)
        # Centre meeting rail and drop bolt, held with two guide sleeves.
    box((1.05,2,35),(.4,1.5,10),'worn')
    for z in (12,29):rod((1.55,2,z-1.2),(1.55,2,z+1.2),.55)
    tube([(1.55,2,.2),(1.55,2,35),(1.55,6.5,35)],.32,'worn')
    box((.5,0,42),(.5,11,2),'worn');bolt(.95,-4,42);bolt(.95,4,42)
    # A closed chain wraps behind and in front of BOTH rails, with no loose floating ends.
    angles=np.linspace(0,2*math.pi,601)
    path=np.array([(2.1*math.cos(a),4.0*math.sin(a),33-3*max(math.cos(a),0)) for a in angles])
    distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    count=int(math.ceil(distances[-1]/1.0));count+=count%2
    centers=np.array([[np.interp(s,distances,path[:,j]) for j in range(3)] for s in np.arange(count)*distances[-1]/count])
    for k,c in enumerate(centers):
        tangent=centers[(k+1)%count]-centers[(k-1)%count];tangent/=np.linalg.norm(tangent)
        side=np.cross(tangent,np.array((0,0,1)));side/=np.linalg.norm(side)
        across=side if k%2 else np.cross(side,tangent)
        pts=[c+tangent*(.79*math.cos(a))+across*(.48*math.sin(a)) for a in np.linspace(0,2*math.pi,(16,12,8)[lod],endpoint=False)]
        tube(pts,.115,'worn',closed=True)
    # Brass padlock with a rounded shackle, inset keyway, seam and rivets.
    G.tube(m,[plan(p) for p in ((2.3,-.62,29.1),(2.3,-.62,30.9),(2.3,-.45,31.4),(2.3,.45,31.4),(2.3,.62,30.9),(2.3,.62,29.1))],.15,'galv',sides=(10,8,6)[lod],bend_radius=.35)
    box((2.3,0,28.45),(1.05,2.0,1.7),'brass')
    box((2.83,0,28.45),(.03,1.6,1.28),'brass')
    rod((2.85,0,28.2),(2.88,0,28.2),.20,'dark',12)
    box((2.90,0,28.02),(.03,.13,.31),'dark')
    if lod<2:
        for y in (-.70,.70):rod((2.86,y,28.82),(2.90,y,28.82),.07,'galv',8)
    # Three existing top-wire runs, with occasional twisted barb knots.
    for h in (4,8,12):
        rod((-h*.5,-220,80+h),(-h*.5,220,80+h),.15,'worn',n=(6,4,3)[lod])
        if lod<2:
            for y in np.arange(-208,219,18):
                tube([(-h*.5-.3,y-.6,80+h-.4),(-h*.5+.3,y,80+h+.4),(-h*.5-.3,y+.6,80+h-.4)],.085,'worn')
                rod((-h*.5-.9,y-.8,80+h-1.2),(-h*.5+.9,y+.8,80+h+1.2),.085,'worn',n=4)
    regions={'galv':(20,485),'worn':(535,745),'brass':(790,905),'dark':(946,1006)}
    for mat,polys in m.polygons.items():
        m.material_overrides[mat]='materials/riverside/rs_chainlink.vmat' if mat=='mesh' else MAT+'/gate.vmat'
        m.tile_overrides[mat]=24
        if mat=='mesh':continue
        lo,hi=regions[mat]
        for i,(pts,n) in enumerate(polys):
            ep=np.array([K.to_world(p) for p in pts]);en=K.to_world(n)
            axis=int(np.argmax(abs(en)));a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
            # Repeated small metal samples with an affine map on every face, no UV collapse.
            low=ep.min(0);span=max(float(np.ptp(ep[:,a])),float(np.ptp(ep[:,b])),1)
            scale=min(25,(hi-lo-8)/span)
            seed=(i*67)%130
            coords=[((lo+4+(p[a]-low[a])*scale)/1024,1-(40+seed+(p[b]-low[b])*scale)/1024) for p in ep]
            m.polygon_uvs[(mat,i)]=coords
    return m
def modeldoc():
    remaps=','.join('{ from = "%s.vmat" to = "%s" }'%(p,'materials/riverside/rs_chainlink.vmat' if p=='mesh' else MAT+'/gate.vmat') for p in ('galv','worn','brass','dark','mesh'))
    meshes=','.join('{ _class="RenderMeshFile" name="lod%d" filename="%s/gate_lod%d.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]} }'%(i,MODEL,i) for i in range(3))
    (OUT/'gate.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode={ _class="RootNode" children=[
{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},
{_class="RenderMeshList" children=[%M%]},
{_class="LODGroupList" children=[{_class="LODGroup" switch_threshold=0 meshes=["lod0"]},{_class="LODGroup" switch_threshold=30 meshes=["lod1"]},{_class="LODGroup" switch_threshold=70 meshes=["lod2"]}]}
]}}
'''.replace('%R%',remaps).replace('%M%',meshes))
if __name__=='__main__':
    paint();counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'gate_lod{k}.obj',make(k),'entrance_gate'))
    modeldoc()
    (TEX/'gate.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 TextureColor "%MAT%/gate_color.png"
 TextureNormal "%MAT%/gate_normal.png"
 TextureRoughness "%MAT%/gate_rough.png"
 TextureMetalness "%MAT%/gate_metal.png"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    report=dict(triangles=counts,atlas=[1024,1024],new_materials=1,shared_mesh_material='rs_chainlink',installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
