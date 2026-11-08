"""Build the reception's paired glazed door leaves, staged for native import."""
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_parts as P

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = 'models/props/veridant/reception_doors_v1'
STAIR_GARDEN_RESOURCE = 'models/props/veridant/stair_garden_doors'


def build_stair_garden_leaf():
    model = K.Model()
    axes = np.eye(3)

    def box(center, size, material, bevel=.12):
        P.bevel_box(model, center, axes, size, material, bevel=bevel)

    width = 39.15
    for e in (1.25, width - 1.25):
        box((e, 0, 50), (2.5, 2.4, 98.8), 'bronze')
    for z in (1.85, 34, 98.15):
        box((width / 2, 0, z), (width - 5, 2.4, 2.5), 'bronze')
    box((width / 2, 0, 17.9), (width - 5, 1.9, 29.6), 'steel')
    box((width / 2, 0, 66.1), (width - 5, .4, 61.65), 'glass', .04)
    for e in np.linspace(5.5, width - 5.5, 9):
        box((e, 0, 66.1), (.48, .94, 61.65), 'bronze')
    for side in (-1, 1):
        box((width - 7, 1.65 * side, 49), (4.1, 1.9, .9), 'bronze')
        box((width - 5.2, 1.14 * side, 49), (1.1, 1.3, 4.3), 'bronze')
    model.material_overrides.update({
        'bronze': 'materials/veridant/vr_brass.vmat',
        'steel': 'materials/veridant/vr_steel.vmat',
        'glass': 'materials/veridant/vr_glass_clear.vmat',
    })
    return K.write_model(ROOT / 'Assets' / STAIR_GARDEN_RESOURCE, STAIR_GARDEN_RESOURCE, 'leaf', model)


def stair_garden_scene_objects(ids):
    objects = []
    for side, y, yaw in [('left', -520.65, 0), ('right', -599.35, 180)]:
        key = 'ops-stair-garden-door/' + side
        objects.append(K.game_object(ids, 'Operations stair garden door ' + side, key,
            (-692, y, 0), rotation=K.yaw_rotation(yaw), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=STAIR_GARDEN_RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-19.575,50', Scale='2.4,39.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def scene_objects(ids):
    objects = []
    for side, y, yaw in [('left', -140.65, 0), ('right', -199.35, 180)]:
        key = 'reception-door/' + side
        objects.append(K.game_object(ids, 'Reception glazed door ' + side, key,
            (208, y, 0), rotation=K.yaw_rotation(yaw), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def build():
    m = K.Model()
    axes = np.eye(3)
    def box(c, size, material, bevel=.12):
        P.bevel_box(m, c, axes, size, material, bevel=bevel)
    # Origin is the hinge at floor level. Plan east maps to model -Y.
    w, bottom, top = 29.15, .6, 99.4
    for e in (1.0, w-1.0):
        box((e,0,50), (2,2,98.8), 'frame')
    for z, h in ((1.85,2.5),(98.15,2.5),(14,1.2)):
        box((w/2,0,z), (w-4,2,h), 'frame')
    box((w/2,0,55.8),(w-4,.38,82.3),'glass',.04)
    box((w/2,0,7.7),(w-4,.65,8.8),'brass')
    for side in (-1,1):
        for z in (43,59):
            box((w-4,side*1.7,z),(.7,1.6,.7),'brass',.15)
        box((w-4,side*2.45,51),(.85,.85,18),'brass',.3)
    for z in (10,50,90):
        box((.5,0,z),(1.1,2.8,3.5),'brass',.22)
    m.material_overrides.update({
        'frame':'materials/veridant/vr_steel.vmat',
        'brass':'materials/veridant/vr_brass.vmat',
        'glass':'materials/veridant/vr_glass_clear.vmat'})
    m.tile_overrides.update({key:48 for key in m.polygons})
    stage = ROOT/'output/veridant/reception-doors-v1/stage'/RESOURCE
    print({'triangles':K.write_model(stage,RESOURCE,'leaf',m),'stage':str(stage)})

def cafe_scene_objects(ids, north=False):
    """The shopfront's 64 x 96 openings; retain the approved leaf asset."""
    objects = []
    entrance = 'north' if north else 'south'
    for side, x, yaw in [('left', -131.35, 90), ('right', -68.65, -90)]:
        key = 'cafe-' + entrance + '-door/' + side
        objects.append(K.game_object(ids, 'Cafe ' + entrance + ' glazed door ' + side, key,
            (x + (180 if north else 0), 268, 0), rotation=K.yaw_rotation(yaw),
            scale=K.vec((1, 31.15/29.15, .96)), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def ops_lobby_scene_objects(ids):
    """The upper operations balcony's 100 x 100 entrance."""
    objects = []
    for side, y, yaw in [('left', -460.65, 0), ('right', -559.35, 180)]:
        key = 'ops-lobby-door/' + side
        objects.append(K.game_object(ids, 'Operations lobby glazed door ' + side, key,
            (-428, y, 128), rotation=K.yaw_rotation(yaw),
            scale=K.vec((1, 49.15/29.15, 1)), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def lounge_courtyard_scene_objects(ids):
    """The lounge courtyard's 100 x 96 entrance."""
    objects = []
    for side, x, yaw in [('left', -299.35, 90), ('right', -200.65, -90)]:
        key = 'lounge-courtyard-door/' + side
        objects.append(K.game_object(ids, 'Lounge courtyard glazed door ' + side, key,
            (x, 208, 0), rotation=K.yaw_rotation(yaw),
            scale=K.vec((1, 49.15/29.15, .96)), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def gallery_balcony_scene_objects(ids, side_entrance=False):
    """The upper balcony and ground-floor lounge side 60 x 96 entrances."""
    objects = []
    prefix = 'lounge-side-door' if side_entrance else 'gallery-balcony-door'
    title = 'Lounge side' if side_entrance else 'Gallery balcony'
    for side, x, yaw in [('left', -399.35, 90), ('right', -340.65, -90)]:
        key = prefix + '/' + side
        objects.append(K.game_object(ids, title + ' glazed door ' + side, key,
            (x - (120 if side_entrance else 0), 208, 0 if side_entrance else 128), rotation=K.yaw_rotation(yaw),
            scale='1,1,0.96', components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def ops_courtyard_scene_objects(ids, garden=False):
    """The operations ground-floor courtyard/garden 80 x 100 entrances."""
    objects = []
    entrance = 'garden' if garden else 'courtyard'
    for side, y, yaw in [('left', -280.65, 0), ('right', -359.35, 180)]:
        key = 'ops-' + entrance + '-door/' + side
        objects.append(K.game_object(ids, 'Operations ' + entrance + ' glazed door ' + side, key,
            (-692 if garden else -328, y + (220 if garden else 0), 0), rotation=K.yaw_rotation(yaw),
            scale=K.vec((1, 39.15/29.15, 1)), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def ops_east_scene_objects(ids):
    """The operations east forecourt's 80 x 100 entrance."""
    objects = []
    for side, x, yaw in [('left', -639.35, 90), ('right', -560.65, -90)]:
        key = 'ops-east-door/' + side
        objects.append(K.game_object(ids, 'Operations east glazed door ' + side, key,
            (x, -752, 0), rotation=K.yaw_rotation(yaw),
            scale=K.vec((1, 39.15/29.15, 1)), components=[
                K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
                    Model=RESOURCE+'/leaf.vmdl', RenderType='On', Tint='1,1,1,1'),
                K.component(ids, 'Sandbox.BoxCollider', key+'/collider',
                    Center='0,-14.575,50', Scale='2,29.15,98.8', Static=False, IsTrigger=False),
                K.component(ids, 'Facepunch.Door', key+'/door',
                    TargetAngle=90, OpenTime=.55, OpenAwayFromPlayer=True),
            ]))
    return objects

def lounge_garden_scene_objects(ids, terrace=False, cafe_link=False):
    """The lounge garden, café link and upper terrace 60 x 96 entrances."""
    objects = []
    prefix = 'lounge-cafe-door' if cafe_link else 'gallery-terrace-door' if terrace else 'lounge-garden-door'
    title = 'Lounge cafe' if cafe_link else 'Gallery terrace' if terrace else 'Lounge garden'
    for side, y, yaw in [(