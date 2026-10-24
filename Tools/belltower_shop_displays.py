"""Shallow three-dimensional shop displays behind Belltower's existing glazing."""
import math
import zlib
import numpy as np
import belltower_furniture as F
from map_kit import Model

RESOURCE = 'materials/belltower/shop-display-v1'
COLOURS = {
    'shop_bottle_green': ((.055, .12, .038, 1), .19, .05),
    'shop_bottle_amber': ((.20, .085, .022, 1), .21, .03),
    'shop_stoneware': ((.64, .57, .43, 1), .38, 0),
    'shop_paper': ((.68, .60, .43, 1), .92, 0),
    'shop_tin': ((.22, .24, .23, 1), .36, .75),
    'shop_cork': ((.25, .16, .085, 1), .95, 0),
    'shop_wood': ((.38, .27, .17, 1), .83, 0),
}


def glass_properties():
    return {'shader': 'shaders/glass.shader', 'F_GLASS_QUALITY': 2,
            'F_RENDER_BACKFACES': 1,
            'TextureColor': 'materials/buildings/glass_clear_color.png',
            'TextureNormal': 'materials/belltower/lantern_glass_normal.png',
            'TextureRoughness': 'materials/buildings/glass_clear_rough.png',
            'g_flTintColor': '[.98 .99 1]', 'g_flBlurAmount': .015,
            'g_flRefractionStrength': 1.001, 'AlbedoAbsorption': .03}


def glass_material_text():
    values=glass_properties()
    return '\n'.join(['// Tools/belltower_quality_materials.py; sources: Sources/Belltower/scans/manifest.json',
                      '"Layer0"','{']+[f'    {k} "{v}"' for k,v in values.items()]+['}',''])


def material_text(name):
    colour, roughness, metalness = COLOURS[name]
    values = {'shader': 'shaders/complex.shader', 'F_SPECULAR': 1,
              'TextureColor': 'materials/default/default_color.tga',
              'TextureNormal': 'materials/default/default_normal.tga',
              'TextureRoughness': 'materials/default/default_rough.tga',
              'TextureAmbientOcclusion': 'materials/default/default_ao.tga',
              'g_vColorTint': '['+' '.join(map(str, colour))+']',
              'g_flRoughnessScaleFactor': roughness, 'g_flMetalness': metalness,
              'g_flModelTintAmount': 1}
    if name == 'shop_wood':
        scan='materials/belltower/scans/brown_planks_03'
        values.update(TextureColor=scan+'_diffuse_4k.png',TextureNormal=scan+'_nor_gl_4k.png',
                      TextureRoughness=scan+'_rough_4k.png',TextureAmbientOcclusion=scan+'_ao_4k.png')
    return '\n'.join(['// Tools/belltower_shop_displays.py', '"Layer0"', '{']+
                     [f'    {k} "{v}"' for k, v in values.items()]+['}', ''])


def build(model, origin, outward, width, height):
    """origin is the lower centre of the existing glass plane, in plan inches."""
    origin, outward = np.asarray(origin, float), np.asarray(outward, float)
    up = np.array((0., 0., 1.))
    right = np.cross(outward, up)
    depth_axis = -outward
    axes = np.array((right, depth_axis, up))
    seed = zlib.crc32(','.join(f'{v:.3f}' for v in (*origin, *outward, width, height)).encode())
    rng = np.random.default_rng(seed)
    half = width/2 - 4.4
    depth = 36.

    def at(x, y, z):
        return origin + right*x + depth_axis*y + up*z

    def box(x, y, z, w, d, h, paint=F.DARK, bevel=.12):
        # Retain the established board-strip UVs without changing the shared
        # furniture materials when this builder runs inside a complete town.
        target=Model() if paint in (F.WOOD,F.DARK) else model
        F.bevel_box(target, at(x, y, z), axes, (w, d, h), paint, bevel, seed+round(x*17+y*11+z*3))
        if target is not model:
            for i,(points,normal) in enumerate(target.polygons[paint]):
                model.polygon('shop_wood',points,normal,uv=target.polygon_uvs.get((paint,i)),
                              normals=target.polygon_normals.get((paint,i)))

    def label(x,y,z,radius,height):
        for a,b in zip(np.linspace(math.pi*1.14,math.pi*1.86,7)[:-1],
                       np.linspace(math.pi*1.14,math.pi*1.86,7)[1:]):
            def p(angle,h):return at(x+math.cos(angle)*radius,y+math.sin(angle)*radius,z+h)
            normal=right*math.cos((a+b)/2)+depth_axis*math.sin((a+b)/2)
            F.face(model,'shop_paper',[p(a,0),p(b,0),p(b,height),p(a,height)],normal)

    # An actual shallow room encloses the display, with no outside face or
    # collider. The old shop image is replaced by clear glass in its own plane.
    box(0, depth, height/2, width-1, 1.2, height, F.DARK)
    boards=max(1,round((width-3)/8))
    span=(width-3)/boards
    for i in range(boards):
        box(-(width-3)/2+(i+.5)*span,depth-.95,height/2,
            span-.10,.7,height-.4,F.DARK,.045)
    for x in (-half-2.1, half+2.1):
        box(x, depth/2+1, height/2, 1.2, depth, height, F.DARK)
    box(0, depth/2+1, height-.7, width-2, depth, 1.2, F.DARK)
    box(0, depth/2+1, 24.7, width-2, depth, 1.2, F.WOOD)
    for x in (-half+1.4, half-1.4):
        box(x, 28.5, (height+25)/2, 2.0, 3.4, height-27, F.WOOD)

    for row, shelf in enumerate((27., 51.5, 76.)):
        box(0, 23., shelf-.65, half*2, 24., 1.3, F.WOOD, .14)
        box(0, 11.1, shelf-1.3, half*2, .85, 2., F.DARK, .09)
        # Loose asymmetrical groups leave gaps and reveal the rear shelf edge.
        count = max(5, round(width/15))
        positions = np.linspace(-half+6.5, half-6.5, count)
        for index, x in enumerate(positions):
            if (index+row) % 7 == 6:
                continue
            x += rng.uniform(-2.5, 2.5)
            y = rng.uniform(17.5, 27.0)
            kind = rng.choice(5,p=(.28,.23,.20,.16,.13))
            radius = rng.uniform(2.1, 3.1)
            h = rng.uniform(9., 20.)
            if kind in (0, 1):
                paint = 'shop_bottle_green' if kind == 0 else 'shop_bottle_amber'
                profile = [(radius*.72, 0), (radius, .6), (radius, h*.63),
                           (radius*.85, h*.73), (radius*.34, h*.83),
                           (radius*.34, h-.65), (radius*.43, h-.5), (radius*.43, h)]
                F.turned(model, at(x,y,shelf), up, right, profile, paint, 12)
                F.turned(model, at(x,y,shelf+h), up, right,
                         [(radius*.30, 0), (radius*.32, .65)], 'shop_cork', 10)
                if rng.random()<.68:label(x,y,shelf+h*.20,radius+.035,h*.25)
            elif kind == 2:
                profile = [(radius*.85, 0), (radius, .5), (radius*1.04, h*.64),
                           (radius*.84, h*.76), (radius*.84, h*.84),
                           (radius*1.02, h*.87), (radius*.96, h*.94)]
                F.turned(model, at(x,y,shelf), up, right, profile, 'shop_stoneware', 14)
                F.turned(model, at(x,y,shelf+h*.94), up, right,
                         [(radius*.91, 0), (radius*.94, .6)], 'shop_cork', 12)
                if rng.random()<.5:label(x,y,shelf+h*.20,radius*1.04+.035,h*.23)
            elif kind == 3:
                box(x,y,shelf+h*.37, radius*2, radius*2.1, h*.74, 'shop_paper', .24)
                # Folded top and a cord give the parcel a readable silhouette.
                box(x,y,shelf+h*.78, radius*2-.4, radius*1.7, 1.0, 'shop_paper', .12)
                box(x,y-radius*1.07-.06,shelf+h*.4,.22,.18,h*.70,'shop_cork',.03)
            else:
                h *= .65
                F.turned(model,at(x,y,shelf),up,right,
                    [(radius*.92,0),(radius,.3),(radius,h-.3),(radius*.92,h)],'shop_tin',14)
                for z in (.25,h-.4):
                    F.turned(model,at(x,y,shelf+z),up,right,
                        [(radius*1.035,0),(radius*1.035,.22)],'shop_tin',14)
    for paint in COLOURS:
        model.material_overrides[paint] = f'{RESOURCE}/{paint.removeprefix("shop_")}.vmat'
        model.tile_overrides[paint] = 16


def opening(model, wall, aperture):
    d, sign = wall.outer()
    outward = np.zeros(3)
    outward[1 if wall.axis == 'e' else 0] = sign
    origin = wall.point((aperture.r0+aperture.r1)/2, d-sign*6, aperture.z0)
    build(model, origin, outward, aperture.r1-aperture.r0, aperture.z1-aperture.z0)
