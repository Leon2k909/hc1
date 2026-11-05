"""Review a complete hanging wall lantern and wrought bracket at the original doorway."""
from pathlib import Path
from collections import Counter
import importlib.util,json,math,re,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_furniture as F
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('chair_geometry',ROOT/'Sources/Belltower/bistro-chair-v2/build.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
OUT=Path(tempfile.gettempdir())/'belltower-wall-lantern-v2';STAGE=OUT/'stage'
RES='models/maps/belltower/wall-lantern-v2';MODEL=STAGE/'Assets'/RES
BLACK='iron_black';GLASS='lantern_glass';BULB='lamp_bulb';CERAMIC='lamp_reflector';BRASS='door_brass'
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.))
MAPS={BLACK:'materials/buildings/iron_black.vmat',GLASS:'materials/belltower/lantern_glass.vmat',BULB:'materials/belltower/lamp_bulb.vmat',CERAMIC:'materials/belltower/lamp_reflector.vmat',BRASS:'materials/belltower/fountain_bronze.vmat'}
PLACEMENT=json.loads((HERE/'placement.json').read_text())

def append(m,part,offset=(0,0,0),scale=(1,1,1)):
    offset=np.asarray(offset,float);scale=np.asarray(scale,float)
    for paint,faces in part.polygons.items():
        for i,(points,normal) in enumerate(faces):
            smooth=part.polygon_normals.get((paint,i));uv=part.polygon_uvs.get((paint,i))
            m.polygon(paint,[p*scale+offset for p in points],normal=K.normalise(normal/scale),uv=uv,normals=[K.normalise(n/scale) for n in smooth] if smooth is not None else None)

def round_square(half,corner,count,z):
    pts=[]
    for cx,cy,start in ((half-corner,half-corner,0),(-half+corner,half-corner,90),(-half+corner,-half+corner,180),(half-corner,-half+corner,270)):
        for angle in np.linspace(start,start+90,count,endpoint=True):
            a=math.radians(angle);pts.append(np.array((cx+corner*math.cos(a),cy+corner*math.sin(a),z)))
    return pts

def square_profile(m,profile,lod,caps=True):
    rings=[round_square(r,min(.24,r*.18),(6,4,2)[lod],z) for r,z in profile]
    for i,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
        n=len(rings[i]);slope=K.normalise(np.array((z1-z0,-(r1-r0))))
        ns=[]
        for k in range(n):
            tangent=K.normalise(rings[i][(k+1)%n]-rings[i][(k-1)%n]);radial=K.normalise(np.cross(tangent,Z))
            ns.append(radial*slope[0]+Z*slope[1])
        for k in range(n):
            q=(k+1)%n
            D.outward(m,BLACK,[rings[i][k],rings[i][q],rings[i+1][q],rings[i+1][k]],ns[k]+ns[q],normals=[ns[k],ns[q],ns[q],ns[k]])
    if caps:
        D.outward(m,BLACK,rings[0],-Z);D.outward(m,BLACK,rings[-1],Z)

def body(lod):
    m=K.Model();sides=(24,16,10)[lod]
    square_profile(m,[(1.25,-1.3),(2.,-1.05),(3.8,-.15),(4.25,0),(4.5,.18),(4.5,.65),(4.25,.9),(3.65,1.1)],lod)
    # Continuous tapered glazing frame, with real inset pane edges.
    square_profile(m,[(3.6,.95),(3.65,1.2),(3.4,1.35)],lod)
    for k in range(4):
        a=k*math.pi/2;d=np.array((math.cos(a),math.sin(a),0));side=np.cross(Z,d)
        pts=[d*3.29-side*3.29+Z*1.25,d*3.29+side*3.29+Z*1.25,d*4.04+side*4.04+Z*10.85,d*4.04-side*4.04+Z*10.85]
        D.outward(m,GLASS,pts,d,uv=[(0,0),(1,0),(1,1),(0,1)])
        corner=np.array((math.cos(a+math.pi/4),math.sin(a+math.pi/4),0))*math.sqrt(2)
        F.beam(m,corner*3.5+Z*1.05,corner*4.25+Z*11.1,(.68,.68),BLACK,bevel=.10)
        # A shallow curved upper transom and a lower retaining bead.
        for z in (1.3,9.25):
            h=3.5+(4.25-3.5)*(z-1)/10
            C.tube(m,[d*h-side*h+Z*z,d*h+side*h+Z*z],.11,BLACK,sides=(8,6,4)[lod])
    square_profile(m,[(4.1,10.85),(4.5,11.05),(4.55,11.5),(4.4,11.75)],lod)
    # An ogee hipped roof, stepped cornice and open-sided vent cap.
    square_profile(m,[(5.,11.8),(5.35,12.05),(5.35,12.4),(5.1,12.6),(4.8,12.7),(4.55,13.1),(4.05,13.75),(3.4,14.4),(2.6,15.08),(1.65,15.6),(1.25,15.75)],lod)
    square_profile(m,[(1.3,15.65),(1.5,15.85),(1.5,16.05)],lod)
    for x in (-1.05,1.05):
        for y in (-1.05,1.05):C.tube(m,[(x,y,16.),(x,y,16.7)],.17,BLACK,sides=(8,6,4)[lod])
    square_profile(m,[(1.7,16.65),(1.75,16.85),(1.65,17.05),(1.1,17.15)],lod)
    F.turned(m,(0,0,17.1),Z,X,[(.5,0),(.5,.18),(.3,.35),(.3,1.05)],BLACK,segments=sides)
    angles=np.linspace(0,math.tau,(28,18,10)[lod]+1)
    C.tube(m,[(math.cos(a),0,19.1+math.sin(a)) for a in angles],.25,BLACK,sides=(10,8,6)[lod],closed=True)
    F.turned(m,(0,0,-2.8),Z,X,[(.24,0),(.55,.35),(.65,.7),(.5,1.),(.23,1.2)],BLACK,segments=sides)
    # Rounded ceramic lampholder and the original warm emissive globe material.
    D.lathe(m,(0,0),0,[(1.,1.1),(1.05,1.3),(.9,1.7),(.65,2.),(.65,2.7),(.8,2.85),(.8,3.15),(.65,3.3)],CERAMIC,sides=sides,caps=(True,True))
    D.lathe(m,(0,0),0,[(.62,3.15),(.68,3.3),(.68,3.8),(.55,4.)],BRASS,sides=sides,caps=(True,True))
    D.lathe(m,(0,0),0,[(.48,3.9),(.7,4.1),(1.05,4.5),(1.3,5.),(1.35,5.5),(1.2,6.),(.85,6.4),(.32,6.62)],BULB,sides=sides,caps=(True,True))
    if lod<2:
        # Glazed-door hinges follow the taper; latch sits on the front pane edge.
        for z in (3.1,7.8):
            h=3.5+.075*(z-1)
            F.turned(m,(h+.15,-h,z),Z,X,[(.20,-.35),(.24,-.25),(.24,.25),(.20,.35)],BLACK,segments=10)
        h=3.5+.075*4.5
        F.turned(m,(h+.13,2.6,5.5),X,Y,[(.32,0),(.32,.12),(.2,.18),(.2,.4)],BRASS,segments=12)
    return m

def build(lod):
    m=K.Model();sides=(24,16,10)[lod]
    plate=K.Model();F.turned(plate,(0,0,0),X,Y,[(.91,.03),(1.,.13),(1.,.43),(.96,.62),(.86,.77)],BLACK,segments=sides)
    append(m,plate,offset=(0,0,-3.5),scale=(1.,2.5,6.5))
    if lod<2:
        for z in (1.2,-8.2):F.turned(m,(.8,0,z),X,Y,[(.32,0),(.37,.05),(.3,.18),(.2,.24)],BLACK,segments=12)
    C.tube(m,[(.8,0,0),(13.8,0,0)],.48,BLACK,sides=(14,10,6)[lod])
    scroll=C.curve([(.8,0,-8.0),(2.6,0,-7.5),(5.7,0,-5.1),(8.7,0,-1.0),(9.6,0,-.5),(9.8,0,-2.0),(8.7,0,-3.1),(7.4,0,-2.5),(7.6,0,-1.5)],(36,22,10)[lod])
    C.tube(m,scroll,.28,BLACK,sides=(10,8,6)[lod])
    hook=C.curve([(12.,0,0),(13.15,0,-.2),(13.4,0,-.9),(13.15,0,-1.5),(12.8,0,-1.55)],(12,8,4)[lod])
    C.tube(m,hook,.22,BLACK,sides=(10,8,6)[lod])
    # Body's ring top meets the hook at the original height and reach.
    append(m,body(lod),offset=(13,0,-1.2-D.LANTERN_HANG*.8),scale=(.8,.8,.8))
    D.configure(m);m.material_overrides.update(MAPS)
    return m

def modeldoc():
    remaps=', '.join('{ from = "'+p+'.vmat" to = "'+v+'" }' for p,v in MAPS.items())
    meshes=', '.join('{ _class = "RenderMeshFile" name = "lod'+str(i)+'" filename = "'+RES+'/lantern_lod'+str(i)+'.obj" import_scale = 1.0 import_translation = [0,0,0] import_rotation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = {exclude_by_default = false exception_list = []} }' for i in range(3))
    return ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
      '{ rootNode = { _class = "RootNode" children = [ { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = ['+remaps+'] use_global_default = false global_default_material = "" } ] },'
      '{ _class = "RenderMeshList" children = ['+meshes+'] }, { _class = "LODGroupList" children = [ { _class = "LODGroup" switch_threshold = 0.0 meshes = ["lod0"] }, { _class = "LODGroup" switch_threshold = 15.0 meshes = ["lod1"] }, { _class = "LODGroup" switch_threshold = 45.0 meshes = ["lod2"] } ] } ] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" base_model_name = "" } }\n')

def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}') for i in range(3)]
    (MODEL/'wall_lantern.vmdl').write_text(modeldoc())
    print(json.dumps({'lods':lods,'accepted_resource_staged':True,'original_asset_preserved':True}))

if __name__=='__main__':main()
