"""Additional collision for the new supports; every existing shape is retained."""
from pathlib import Path
import math,hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'Tools'))
import numpy as np
import map_kit as K
import geometry as G
def supports():
    m=K.Model()
    for e in (-900,-500,500,900):
        for n in (-691,734):m.box((e-30,n-35,208),(e+30,n+35,238),None,'metal')
        m.box((e-24,-719,238),(e+24,-663,476),None,'metal')
        m.beam((e,734,208),(e,815,548),(56,48),None,'metal',up=G.X)
    for side in (-1,1):
        for n in (-600,-150,300):
            m.oriented_box((side*1065,n,226),(G.X,G.Y,G.Z),(70,65,36),None,'metal')
            m.oriented_box((side*1070,n,363.5),(G.X,G.Y,G.Z),(56,48,251),None,'metal')
    assert len(m.boxes)==28
    return m
def skirt():
    pts=[(198*math.cos(a),198*math.sin(a),z) for z in (16,70) for a in np.linspace(0,2*math.pi,32,endpoint=False)]
    return [(pts,'metal')]
def augment(doc,model,stage):
    if 'ares_v3_support_' in doc or 'ares_v3_reactor_skirt' in doc:return doc
    marker='_class = "PhysicsShapeList"';start=doc.index(marker)
    original=doc[start:];nodes=[]
    if model=='hall':
        for i,(c,ax,size,surf) in enumerate(supports().boxes):
            nodes.append('''{
 _class = "PhysicsShapeBox"
 name = "ares_v3_support_%d"
 parent_bone = ""
 surface_prop = "metal"
 collision_tags = "solid"
 origin = %s
 angles = %s
 dimensions = %s
},'''%(i,K.vec3(K.to_world(c)),K.vec3(K.angles_of([K.to_world(a) for a in ax])),K.vec3(size)))
    else:
        path=stage/'Assets/models/maps/ares/constructed-v3/reactor_skirt_hulls.obj'
        K.write_hulls_obj(path,[points for points,surface in skirt()])
        nodes.append('''{
 _class = "PhysicsHullFile"
 name = "ares_v3_reactor_skirt"
 parent_bone = ""
 surface_prop = "metal"
 collision_tags = "solid"
 recenter_on_parent_bone = false
 offset_origin = [0,0,0]
 offset_angles = [0,0,0]
 align_origin_x_type = "None"
 align_origin_y_type = "None"
 align_origin_z_type = "None"
 filename = "models/maps/ares/constructed-v3/reactor_skirt_hulls.obj"
 import_scale = 1.0
 faceMergeAngle = 10.0
 maxHullVertices = 0
 import_mode = "HullPerElement"
 optimization_algorithm = "QEM"
 import_filter = { exclude_by_default = false exception_list = [] }
},''')
    index=doc.index('[',doc.index('children =',start))+1
    insertion='\n'+'\n'.join(nodes)+'\n';result=doc[:index]+insertion+doc[index:]
    assert result.replace(insertion,'',1)[start:]==original
    return result
if __name__=='__main__':
    import json
    ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/constructed-interior-v3';STAGE=OUT/'stage'
    for model in ('hall','reactor'):
        p=STAGE/f'Assets/models/maps/ares/constructed-v3/ares_{model}_trial.vmdl'
        p.write_text(augment(p.read_text(),model,STAGE),encoding='utf-8',newline='')
    manifest=json.loads((OUT/'manifest.json').read_text());manifest['files']={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()}
    manifest['collision_unchanged']=False;manifest['all_existing_collision_retained']=True
    manifest['additional_collision']={'hall_support_boxes':28,'reactor_skirt_hulls':1}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(manifest['additional_collision'])
