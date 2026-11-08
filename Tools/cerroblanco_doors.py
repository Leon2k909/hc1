"""Approved glazed leaves fitted inside the existing café terrace frame."""
import map_kit as K

def scene_objects(ids, courtyard=False):
    objects=[]
    entrance='courtyard' if courtyard else 'terrace'
    placements=[('left',(248.15,-489,0),90),('right',(331.85,-489,0),-90)] if courtyard else [
        ('left',(331,-553.15,180),0),('right',(331,-646.85,180),180)]
    scale=(1,41.65/29.15,1.22) if courtyard else (1,46.65/29.15,1.18)
    for side,position,yaw in placements:
        key='cafe-'+entrance+'-door/'+side
        objects.append(K.game_object(ids,'Cafe '+entrance+' glazed door '+side,key,position,
            rotation=K.yaw_rotation(yaw),scale=K.vec(scale),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects

def north_gallery_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',453.15,90),('right',546.85,-90)]:
        key='north-gallery-terrace-door/'+side
        objects.append(K.game_object(ids,'North gallery terrace glazed door '+side,key,(x,-1009,180),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.18)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects

def north_gallery_ground_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',303.15,90),('right',396.85,-90)]:
        key='north-gallery-ground-door/'+side
        objects.append(K.game_object(ids,'North gallery ground glazed door '+side,key,(x,-1009,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects

def cafe_north_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-693.15,0),('right',-786.85,180)]:
        key='cafe-north-door/'+side
        objects.append(K.game_object(ids,'Cafe north glazed door '+side,key,(706,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects

def cafe_south_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-693.15,0),('right',-786.85,180)]:
        key='cafe-south-door/'+side
        objects.append(K.game_object(ids,'Cafe south glazed door '+side,key,(-9,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects

def north_gallery_main_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-1253.15,0),('right',-1346.85,180)]:
        key='north-gallery-main-door/'+side
        objects.append(K.game_object(ids,'North gallery main glazed door '+side,key,(706,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects


def north_gallery_east_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-1753.15,0),('right',-1846.85,180)]:
        key='north-gallery-east-door/'+side
        objects.append(K.game_object(ids,'North gallery east glazed door '+side,key,(706,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects


def north_gallery_south_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-1453.15,0),('right',-1546.85,180)]:
        key='north-gallery-south-door/'+side
        objects.append(K.game_object(ids,'North gallery south glazed door '+side,key,(-9,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects



def north_gallery_southeast_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-1853.15,0),('right',-1946.85,180)]:
        key='north-gallery-southeast-door/'+side
        objects.append(K.game_object(ids,'North gallery southeast glazed door '+side,key,(-9,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects



def north_gallery_end_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',153.15,90),('right',246.85,-90)]:
        key='north-gallery-end-door/'+side
        objects.append(K.game_object(ids,'North gallery end glazed door '+side,key,(x,-2051,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects


def west_gallery_garden_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',153.15,90),('right',246.85,-90)]:
        key='west-gallery-garden-door/'+side
        objects.append(K.game_object(ids,'West gallery garden glazed door '+side,key,(x,1117,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects


def west_gallery_far_garden_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',1253.15,90),('right',1346.85,-90)]:
        key='west-gallery-far-garden-door/'+side
        objects.append(K.game_object(ids,'West gallery far garden glazed door '+side,key,(x,1117,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects


def west_gallery_link_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',1253.15,90),('right',1346.85,-90)]:
        key='west-gallery-link-door/'+side
        objects.append(K.game_object(ids,'West gallery link glazed door '+side,key,(x,209,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,46.65/29.15,1.22)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/veridant/reception_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-14.575,50',Scale='2,29.15,98.8',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects


def walnut_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',53.15,90),('right',146.85,-90)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'West gallery champagne glazed door '+side,key,(x,659,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects



def east_champagne_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',603.15,90),('right',696.85,-90)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'West gallery east champagne door '+side,key,(x,659,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects



def courtyard_champagne_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',936.85,0),('right',843.15,180)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'West gallery courtyard champagne door '+side,key,(-151,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects



def end_champagne_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',696.85,0),('right',603.15,180)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'West gallery end champagne door '+side,key,(1501,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects



def east_gallery_garden_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-593.15,0),('right',-686.85,180)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'East gallery garden champagne door '+side,key,(-991,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def east_gallery_courtyard_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-546.85,90),('right',-453.15,-90)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'East gallery courtyard champagne door '+side,key,(x,-489,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def east_gallery_north_courtyard_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-246.85,90),('right',-153.15,-90)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'East gallery north courtyard champagne door '+side,key,(x,-489,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def east_gallery_outer_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-546.85,90),('right',-453.15,-90)]:
        key='walnut-door/'+side
        objects.append(K.game_object(ids,'East gallery outer champagne door '+side,key,(x,-1391,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def east_gallery_outer_south_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-846.85,90),('right',-753.15,-90)]:
        key='east-gallery-outer-south/'+side
        objects.append(K.game_object(ids,'East gallery outer south champagne door '+side,key,(x,-1391,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def south_gallery_courtyard_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-253.15,0),('right',-346.85,180)]:
        key='south-gallery-courtyard/'+side
        objects.append(K.game_object(ids,'South gallery courtyard champagne door '+side,key,(-1009,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def south_gallery_rear_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-203.15,0),('right',-296.85,180)]:
        key='south-gallery-rear/'+side
        objects.append(K.game_object(ids,'South gallery rear champagne door '+side,key,(-2141,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




def south_gallery_east_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-1546.85,90),('right',-1453.15,-90)]:
        key='south-gallery-east/'+side
        objects.append(K.game_object(ids,'South gallery east champagne door '+side,key,(x,-471,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects





def south_gallery_west_north_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-1346.85,90),('right',-1253.15,-90)]:
        key='south-gallery-west-north/'+side
        objects.append(K.game_object(ids,'South gallery west north champagne door '+side,key,(x,1021,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects





def south_gallery_west_south_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',-1746.85,90),('right',-1653.15,-90)]:
        key='south-gallery-west-south/'+side
        objects.append(K.game_object(ids,'South gallery west south champagne door '+side,key,(x,1021,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects





def south_gallery_rear_west_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',646.85,0),('right',553.15,180)]:
        key='south-gallery-rear-west/'+side
        objects.append(K.game_object(ids,'South gallery rear west champagne door '+side,key,(-2141,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects





def south_gallery_main_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',156.85,0),('right',43.15,180)]:
        key='south-gallery-main/'+side
        objects.append(K.game_object(ids,'South gallery main champagne door '+side,key,(-1009,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,56.65/46.65,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects





def south_gallery_rear_main_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',156.85,0),('right',43.15,180)]:
        key='south-gallery-rear-main/'+side
        objects.append(K.game_object(ids,'South gallery rear main champagne door '+side,key,(-2141,y,0),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,56.65/46.65,1)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects





def west_gallery_balcony_scene_objects(ids):
    objects=[]
    for side,x,yaw in [('left',333.15,90),('right',426.85,-90)]:
        key='west-gallery-balcony/'+side
        objects.append(K.game_object(ids,'West gallery balcony champagne door '+side,key,(x,659,180),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,108/122)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects






def north_gallery_upper_link_scene_objects(ids):
    objects=[]
    for side,y,yaw in [('left',-1253.15,0),('right',-1346.85,180)]:
        key='north-gallery-upper-link/'+side
        objects.append(K.game_object(ids,'North gallery upper link champagne door '+side,key,(-9,y,180),
            rotation=K.yaw_rotation(yaw),scale=K.vec((1,1,118/122)),components=[
                K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                    Model='models/props/cerroblanco/champagne_doors_v1/leaf.vmdl',RenderType='On',Tint='1,1,1,1'),
                K.component(ids,'Sandbox.BoxCollider',key+'/collider',
                    Center='0,-23.325,61.5',Scale='2.6,46.65,121',Static=False,IsTrigger=False),
                K.component(ids,'Facepunch.Door',key+'/door',TargetAngle=90,OpenTime=.55,OpenAwayFromPlayer=True)]))
    return objects




