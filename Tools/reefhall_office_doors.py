"""South office doors with a fixed transom, sized to the existing partition."""
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_parts as P

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/reefhall/office_doors_v1'
LEAF='models/props/veridant/reception_doors_v1/leaf.vmdl'

def build():
    m=K.Model()
    axes=np.eye(3)
    # Plan e maps to model -Y; the existing jambs occupy two inches per side.
    for centre,size in [((40,0,97.5),(76,2,4)),((40,0,170.5),(76,2,3))]:
        P.bevel_box(m,centre,axes,size,'frame',bevel=.12)
    P.bevel_box(m,(40,0,134),axes,(72,.38,70),'glass',bevel=.04)
    m.material_overrides.update({'frame':'materials/reefhall/rh_gunmetal.vmat',
                                 'glass':'materials/reefhall/rh_glass.vmat'})
    m.tile_overrides.update({p:48 for p in m.polygons})
    stage=ROOT/'output/reefhall/office-doors-v1/stage'/RESOURCE
    print({'triangles':K.write_model(stage,RESOURCE,'transom',m),'stage':str(stage)})

def scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-2002.65,0),('right',-2077.35,180)]:
        key='office-south-door/'+side
        objects.append(K.game_object(ids,'Office south glazed door '+side,key,(720,y,208),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,37.15/29.15,.96)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=LEAF,RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    key='office-south-door/transom'
    objects.append(K.game_object(ids,'Office south fixed glass transom',key,(720,-2000,208),components=[
        K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=RESOURCE+'/transom.vmdl',RenderType='On',Tint='1,1,1,1'),
        K.component(ids,'Sandbox.BoxCollider',key+'/collider',Center='0,-40,134',Scale='2,76,76',Static=True,IsTrigger=False)]))
    return objects

if __name__=='__main__':build()
