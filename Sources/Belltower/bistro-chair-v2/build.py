"""Review a curved timber/steel cafe chair at one existing placement."""
from pathlib import Path
from collections import Counter
import json,math,re,sys,tempfile
import numpy as np
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_detail as D
import belltower_furniture as F
from belltower_move_square_lamps import geometry,sha
OUT=Path(tempfile.gettempdir())/'belltower-bistro-chair-v2'
STAGE=OUT/'stage'
RES='models/maps/belltower/bistro-chair-v2'
MODEL=STAGE/'Assets'/RES
GREEN='iron_green';BLACK='iron_black';CUT='endgrain'
CENTRE=(-602.5669562118178,-193.86232880099112)
YAW=445.6194869566527
X=np.array((1.,0,0));Y=np.array((0,1.,0));Z=np.array((0,0,1.))

def tube(m,points,radius,paint=GREEN,sides=12,closed=False):
    p=np.array(points,float)
    tangents=np.empty_like(p)
    tangents[1:-1]=p[2:]-p[:-2]
    tangents[0]=(p[1]-p[-2]) if closed else p[1]-p[0]
    tangents[-1]=tangents[0] if closed else p[-1]-p[-2]
    tangents/=np.linalg.norm(tangents,axis=1,keepdims=True)
    rings=[];normals=[];previous_u=None
    for c,t in zip(p,tangents):
        up=Y if abs(t[2])>.85 else Z
        projected=previous_u-t*np.dot(previous_u,t) if previous_u is not None else np.cross(t,up)
        u=K.normalise(projected if np.linalg.norm(projected)>1e-6 else np.cross(t,up));v=np.cross(t,u)
        previous_u=u
        ns=[u*math.cos(a)+v*math.sin(a) for a in np.arange(sides)*math.tau/sides]
        rings.append([c+radius*n for n in ns]);normals.append(ns)
    for i in range(len(p)-1):
        for k in range(sides):
            kk=(k+1)%sides;ids=((i,k),(i,kk),(i+1,kk),(i+1,k))
            D.outward(m,paint,[rings[a][b] for a,b in ids],sum(normals[a][b] for a,b in ids),normals=[normals[a][b] for a,b in ids])
    if not closed:
        D.outward(m,paint,rings[0],-tangents[0]);D.outward(m,paint,rings[-1],tangents[-1])

def curve(points,count):
    p=np.array(points,float);t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    return PchipInterpolator(t,p)(np.linspace(0,t[-1],count))

def screw(m,point,normal,lod):
    u=Y if abs(np.dot(normal,Z))>.8 else Z
    F.turned(m,np.array(point),np.array(normal),u,[(.15,0),(.18,.025),(.15,.06)],BLACK,segments=10 if lod==0 else 6)

def back_slat(m,z,lod):
    count=(12,7,3)[lod];height=3.5;depth=.78;b=.13
    profile=[(-depth/2+b,-height/2),(depth/2-b,-height/2),(depth/2,-height/2+b),(depth/2,height/2-b),
             (depth/2-b,height/2),(-depth/2+b,height/2),(-depth/2,height/2-b),(-depth/2,-height/2+b)]
    vertices=[];axes=[];arc=[0.]
    for y in np.linspace(-7.0,7.0,count+1):
        x=-7.5-2.4*((z-17)/16)-.4+1.2*(1-(y/7.0)**2)
        centre=np.array((x,y,z))
        tangent=K.normalise(np.array((-2.4*y/49,1.,0)))
        n=K.normalise(np.cross(tangent,(-.15,0,1.)));up=K.normalise(np.cross(n,tangent))
        axes.append((centre,n,up,tangent))
        vertices.append([centre+n*d+up*h for d,h in profile])
        if len(axes)>1:arc.append(arc[-1]+np.linalg.norm(axes[-1][0]-axes[-2][0]))
    u0,u1=F.STRIPS[2 if z<27 else 4]
    for i in range(count):
        for k in range(len(profile)):
            kk=(k+1)%len(profile);dd=profile[kk][0]-profile[k][0];dh=profile[kk][1]-profile[k][1]
            nn=K.normalise(np.array((dh,-dd)))
            n0=axes[i][1]*nn[0]+axes[i][2]*nn[1];n1=axes[i+1][1]*nn[0]+axes[i+1][2]*nn[1]
            pts=[vertices[i][k],vertices[i][kk],vertices[i+1][kk],vertices[i+1][k]]
            uv=[(u0+(h/height+.5)*(u1-u0),arc[j]/F.TILE+.17) for j,h in ((i,profile[k][1]),(i,profile[kk][1]),(i+1,profile[kk][1]),(i+1,profile[k][1]))]
            D.outward(m,F.WOOD,pts,n0+n1,uv=uv,normals=[n0,n0,n1,n1])
    for i,sign in ((0,-1),(-1,1)):
        uv=[((d/depth+.5)*.12,(h/height+.5)*.4) for d,h in profile]
        D.outward(m,CUT if lod<2 else F.WOOD,vertices[i],axes[i][3]*sign,uv=uv)
    if lod<2:
        for y in (-6.8,6.8):
            idx=0 if y<0 else -1;c,n,up,t=axes[idx]
            screw(m,c+n*(depth/2+.005),n,lod)
            screw(m,c-n*(depth/2+.005),-n,lod)

def build(lod):
    m=K.Model();sides=(12,8,6)[lod]
    for s in (-1,1):
        controls=[(-8.7,s*8.7,.45),(-7.58,s*7.58,16.3),(-7.55,s*7.5,17.4),(-8.25,s*7.25,24.2),(-9.9,s*6.9,33.)]
        tube(m,curve(controls,(20,12,5)[lod]),.45,sides=sides)
        front=[(8.7,s*8.7,.45),(7.65,s*7.65,15.5),(7.5,s*7.5,17.)]
        tube(m,curve(front,(8,5,2)[lod]),.45,sides=sides)
    # A continuous rounded carrier under the seat instead of square-section rails.
    carrier=[]
    for cx,cy,start in ((6.5,6.5,0),(-6.5,6.5,90),(-6.5,-6.5,180),(6.5,-6.5,270)):
        for a in np.linspace(start,start+90,(5,3,2)[lod],endpoint=False):
            carrier.append((cx+.9*math.cos(math.radians(a)),cy+.9*math.sin(math.radians(a)),17.0))
    carrier.append(carrier[0]);tube(m,carrier,.43,sides=sides,closed=True)
    for p,q in [((-8.25,-8.25,6),(-8.25,8.25,6)),((8.25,-8.25,6),(8.25,8.25,6)),((-8.25,-8.25,6),(8.25,-8.25,6)),((-8.25,8.25,6),(8.25,8.25,6))]:
        tube(m,[p,q],.23,sides=sides)
    for sx in (-1,1):
        for sy in (-1,1):
            F.turned(m,(sx*8.7,sy*8.7,0),Z,X,[(.57,0),(.59,.10),(.53,.62),(.46,.74)],BLACK,segments=sides)
            if lod<2:F.turned(m,(sx*7.5,sy*7.5,16.9),Z,X,[(.47,-.15),(.53,-.07),(.53,.07),(.47,.15)],GREEN,segments=sides)
    # Five eased slats, continuous scan strips, real end grain and low-domed fasteners.
    for k,y in enumerate(np.linspace(-6.,6.,5)):
        if lod<2:F.bevel_box(m,(-.05,y,17.77),(X,Y,Z),(15.6,2.58,.86),F.WOOD,bevel=.19,seed=10+k)
        else:m.oriented_box((-.05,y,17.77),(X,Y,Z),(15.6,2.58,.86),F.WOOD)
        if lod<2:
            for x,sign in ((-7.852,-1),(7.752,1)):
                pts=[(x,y-1.09,17.54),(x,y+1.09,17.54),(x,y+1.09,18.0),(x,y-1.09,18.0)]
                D.outward(m,CUT,pts,X*sign,uv=[(0,0),(.18,0),(.18,.04),(0,.04)])
            for x in (-5.8,5.8):screw(m,(x,y,18.205),Z,lod)
    back_slat(m,24.,lod);back_slat(m,30.,lod)
    D.configure(m)
    m.material_overrides.update({F.WOOD:'materials/belltower/furniture_wood.vmat',GREEN:'materials/buildings/iron_green.vmat',BLACK:'materials/buildings/iron_black.vmat',CUT:'materials/gunsmith_range/bench_oak_endgrain.vmat'})
    m.tile_overrides[CUT]=12.
    return m

def modeldoc():
    maps={F.WOOD:'materials/belltower/furniture_wood.vmat',GREEN:'materials/buildings/iron_green.vmat',BLACK:'materials/buildings/iron_black.vmat',CUT:'materials/gunsmith_range/bench_oak_endgrain.vmat'}
    remaps=', '.join('{ from = "'+p+'.vmat" to = "'+v+'" }' for p,v in maps.items())
    meshes=', '.join('{ _class = "RenderMeshFile" name = "lod'+str(i)+'" filename = "'+RES+'/chair_lod'+str(i)+'.obj" import_scale = 1.0 import_translation = [0,0,0] import_rotation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = {exclude_by_default = false exception_list = []} }' for i in range(3))
    return ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
      '{ rootNode = { _class = "RootNode" children = [ { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = ['+remaps+'] use_global_default = false global_default_material = "" } ] },'
      '{ _class = "RenderMeshList" children = ['+meshes+'] }, { _class = "LODGroupList" children = [ { _class = "LODGroup" switch_threshold = 0.0 meshes = ["lod0"] }, { _class = "LODGroup" switch_threshold = 15.0 meshes = ["lod1"] }, { _class = "LODGroup" switch_threshold = 45.0 meshes = ["lod2"] } ] } ] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" base_model_name = "" } }\n')

def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'chair_lod{i}.obj',build(i),f'chair_lod{i}') for i in range(3)]
    (MODEL/'bistro_chair.vmdl').write_text(modeldoc())
    print(json.dumps({'lods':lods,'accepted_resource_staged':True,'review_wrappers_recreated':False}))

if __name__=='__main__':main()
