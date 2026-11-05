"""Close-range display pedestal review; public Reef Hall assets remain unchanged."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,re
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import reefhall_map as R
OUT=ROOT/'output/reefhall/display-pedestal-v1';STAGE=OUT/'stage/Assets';RES='models/props/reefhall/display_pedestal_v1';MODEL=STAGE/RES;MODEL.mkdir(parents=True,exist_ok=True)
MAT='materials/reefhall/display_pedestal_v1';MATS=STAGE/MAT;MATS.mkdir(parents=True,exist_ok=True)
for name,color,rough,metal in [('coat',(.23,.31,.35),.6,.05),('alloy',(.55,.6,.61),.4,.25)]:
    (MATS/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "[{' '.join(map(str,color))} 1]"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[{rough} {rough} {rough} 0]"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flMetalness "{metal}"
 g_flModelTintAmount "1"
 g_flRoughnessScaleFactor "1"
}}
''')
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.))
def model(lod):
    m=K.Model()
    def box(c,size,paint='rh_gunmetal',b=.15,axes=(X,Y,Z)):
        if lod<2 and b:G.bevel_box(m,np.array(c,float),axes,size,paint,bevel=b)
        else:m.oriented_box(np.array(c,float),axes,size,paint)
    def tube(a,b,r,paint='rh_steel'):
        G.tube(m,[np.array(a,float),np.array(b,float)],r,paint,sides=(10,7,5)[lod])
    # Recessed toe plinth and rounded precast body, within the original 44-inch square.
    box((0,0,1.6),(40,40,3.2),'rh_black',.45)
    box((0,.6,16),(43.7,42.5,25.6),'rh_smooth',1.25)
    for x in (-19.,19.):box((x,-21.25,16),(5.7,1.2,25.6),'rh_smooth',.25)
    box((0,-21.25,4.45),(32.3,1.2,2.5),'rh_smooth',.2)
    box((0,-21.25,26.75),(32.3,1.2,4.1),'rh_smooth',.2)
    box((0,0,28.85),(44,44,1.7),'rh_steel',.3)
    box((0,0,29.8),(42.4,42.4,.4),'rh_black',.1)
    # Front maintenance aperture assembled from a recessed pan and fitted access door.
    box((0,-20.84,15.2),(32,.16,19),'rh_black',.05)
    box((0,-21.1,15.2),(30.8,.12,17.8),'rh_gunmetal',.04)
    for x in (-16,16):box((x,-22.02,15.2),(.55,.18,19.5),'rh_steel',.06)
    for z in (5.6,24.8):box((0,-22.02,z),(32.5,.18,.55),'rh_steel',.06)
    # Discrete fasteners, a quarter-turn latch and a recessed pull.
    for x in (-14,14):
        for z in (7.8,22.6):
            G.lathe_axis(m,(x,-21.18,z),-Y,np.array([(0,0),(.31,0),(.31,.1),(0,.1)]),'rh_steel',sides=8 if lod==0 else 6)
            if lod==0:box((x,-21.3,z),(.34,.035,.055),'rh_black',0)
    box((9,-21.22,15),(2.3,.1,4.6),'rh_black',.05)
    tube((8.5,-21.45,13.9),(8.5,-21.45,16.1),.14)
    for z in (10.,20.):box((-14.7,-21.27,z),(1.2,.2,2),'rh_steel',.08)
    # Side ventilation has real dark openings and projecting blades, not painted lines.
    for side in (-1,1):
        box((side*21.91,0,14),(.14,24,11),'rh_black',.04)
        for z in np.linspace(9.5,18.5,10 if lod<2 else 5):box((side*22.02,0,float(z)),(.25,23,.4),'rh_gunmetal',.06)
        for n in (-13,13):box((side*22.02,n,14),(.25,.6,12),'rh_steel',.08)
    # Continuous lower seal, slim corner extrusions and a formed removable cover.
    for y in (-20.3,20.3):box((0,y,30.25),(41.2,.7,.5),'rh_black',.1)
    for x in (-20.3,20.3):box((x,0,30.25),(.7,41.2,.5),'rh_black',.1)
    for x in (-20.7,20.7):
        for y in (-20.7,20.7):
            box((x,y,47.1),(1.05,1.05,33.8),'rh_steel',.2)
            box((x,y,31.1),(1.6,1.6,1.2),'rh_gunmetal',.15)
    # Top stays at the old 65.2-inch cover height. A thin lip wraps the unchanged glass.
    box((0,0,64.4),(42.3,42.3,1.6),'rh_gunmetal',.5)
    for y in (-20.8,20.8):box((0,y,63.9),(42.1,.65,.8),'rh_steel',.15)
    for x in (-20.8,20.8):box((x,0,63.9),(.65,42.1,.8),'rh_steel',.15)
    if lod<2:
        for y in np.linspace(14,17,5):box((0,float(y),65.16),(22,.23,.045),'rh_black',.01)
        for x in (-17,17):
            tube((x,-8,65.05),(x,-2,65.05),.17,'rh_black')
    # Painted access hardware and satin low-metalness trim remain readable in the aquarium's blue light.
    for original,paint in [('rh_gunmetal','dp_coat'),('rh_steel','dp_alloy')]:
        for points,normal in list(m.polygons.get(original,[])):
            m.polygon(paint,points,normal)
        m.polygons.pop(original,None)
    R.configure(m)
    for paint,name in [('dp_coat','coat'),('dp_alloy','alloy')]:m.material_overrides[paint]=f'{MAT}/{name}.vmat';m.tile_overrides[paint]=64
    return m
counts=[];models=[]
for lod in range(3):
    m=model(lod);models.append(m);counts.append(K.write_obj(MODEL/f'pedestal_lod{lod}.obj',m,f'pedestal_lod{lod}'))
K.write_vmdl(MODEL/'pedestal.vmdl',RES,'pedestal_lod0',models[0]);doc=(MODEL/'pedestal.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/pedestal_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,40,100)))
(MODEL/'pedestal.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {meshes} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
manifest=dict(installed=True,triangles=counts,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'build-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'triangles':counts,'installed':True}))
