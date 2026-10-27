"""Closed resort gates: folded steel leaves and coursed limestone lamp piers.

All geometry is visual. The forecourt retains its existing boundary and pier
collision boxes, lamp locations and light settings.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

import map_kit as K
import riverdale_parts as P
import veridant_materials as VM

PREFIX = 'materials/veridant/gates-v1'
NAMES = ('stone', 'stone_warm', 'stone_cool', 'mortar', 'paint', 'hardware', 'plaque')
MATERIALS = {f'vr_gate_{name}': f'{PREFIX}/{name}.vmat' for name in NAMES}
X, Y, Z = np.eye(3)


def old_into(model, east, north):
    """Exact original visible geometry, used only for sparse extraction."""
    P.box(model, east - 1, east, north - 90, north + 90, 0, 110, 'vr_steel')
    for side in (-1, 1):
        P.box(model, east - 14, east + 24, north + side * 100 - 14,
              north + side * 100 + 14, 0, 150, 'vr_stone_dark')


def build_into(model, east, north):
    local = K.Model()
    rng = np.random.default_rng(618 + int(north))

    def block(centre, size, paint, bevel=.12, stone=False):
        start = len(local.polygons[paint])
        P.bevel_box(local, centre, (X, Y, Z), size, paint, bevel=bevel)
        if stone:
            # One continuous, joint-free region per cut stone, with real joints
            # supplied by geometry. Never paint a second set of joints on it.
            offset = rng.uniform(.25, .75, 2)
            for i in range(start, len(local.polygons[paint])):
                points, normal = local.polygons[paint][i]
                across = X if abs(normal[0]) < .7 else Y
                up = Z if abs(normal[2]) < .7 else Y
                local.polygon_uvs[(paint, i)] = [
                    (float(offset[0] + np.dot(p-centre, across)/96),
                     float(offset[1] + np.dot(p-centre, up)/96)) for p in points]

    # Lamp piers retain their old 38 x 28 x 150 inch overall envelope.
    # Recessed mortar cores close all joints; nothing is an open black crack.
    for side in (-1, 1):
        c = side * 100
        block((5, c, 72), (36.8, 26.8, 144), 'vr_gate_mortar', .16)
        block((5, c, 5.5), (38, 28, 11), 'vr_gate_stone_cool', .42, True)
        for row in range(7):
            bottom = 11.18 + row * 18.7
            height = 18.48
            paint = ('vr_gate_stone', 'vr_gate_stone_warm', 'vr_gate_stone_cool')[(row + (side == 1)) % 3]
            # Very small cutting/setting variation; these are maintained resort
            # piers, not deliberately broken ruins.
            block((5 + rng.uniform(-.045, .045), c, bottom + height/2),
                  (37.88, 27.88, height), paint, rng.uniform(.20, .32), True)
        block((5, c, 143), (37.9, 27.9, 2.7), 'vr_gate_stone_cool', .28, True)
        block((5, c, 145.25), (35.5, 25.5, 1.8), 'vr_gate_mortar', .15)
        block((5, c, 148), (38, 28, 4), 'vr_gate_stone', .65, True)

    # Steel frames are in front of the retained solid boundary wall. Two leaves
    # meet on a narrow overlapping astragal rather than a featureless sheet.
    for side in (-1, 1):
        centre = side * 42.8
        block((-2.7, centre, 61), (3.0, 84.8, 116), 'vr_gate_paint', .18)
        for edge in (-1, 1):
            block((-4.65, centre + edge * 40.9, 61), (1.3, 2.3, 116), 'vr_gate_paint', .15)
        for z in (5, 117):
            block((-4.65, centre, z), (1.3, 82, 3.8), 'vr_gate_paint', .16)
        # Folded, tongue-and-groove vertical panels. Their lip and recess catch
        # grazing light; one does not need a heavy painted noise overlay.
        for index in range(6):
            u = centre - 33.5 + index * 13.4
            block((-4.48, u, 61), (.7, 13.24, 106.5), 'vr_gate_paint', .16)
        block((-5.2, centre, 15.5), (.75, 79.8, 1.4), 'vr_gate_paint', .11)
        # Visible hinge straps, three knuckles and retaining washers each side.
        hinge = side * 84.65
        for z in (23, 61, 101):
            block((-5.5, side * 80, z), (1.0, 10.4, 2.8), 'vr_gate_hardware', .22)
            for dz, height in ((-2.05, 1.8), (0, 2.05), (2.05, 1.8)):
                P.rod(local, (-6.6, hinge, z+dz-height/2), (-6.6, hinge, z+dz+height/2),
                      .82, 'vr_gate_hardware', 16, caps=True)
            P.rod(local, (-6.6, hinge, z-3.35), (-6.6, hinge, z+3.35), .31,
                  'vr_gate_hardware', 12, caps=True)
            for u in (side*77, side*82):
                P.rod(local, (-6.15, u, z), (-5.95, u, z), .34,
                      'vr_gate_hardware', 6, caps=True)

    block((-5.9, -.35, 61), (1.0, 1.0, 115), 'vr_gate_paint', .14)
    # Handle stand-offs, lever, keeper and a small key escutcheon.
    for u in (-6.3, 5.8):
        block((-5.55, u, 56), (.75, 2.3, 11), 'vr_gate_hardware', .28)
        for z in (52.1, 59.9):
            P.rod(local, (-6.0, u, z), (-6.17, u, z), .22, 'vr_gate_hardware', 8, caps=True)
    P.rod(local, (-6.1, -6.3, 57.5), (-8.0, -6.3, 57.5), .30, 'vr_gate_hardware', 12, caps=True)
    P.rod(local, (-8.0, -6.3, 57.5), (-8.0, -15.0, 57.5), .39, 'vr_gate_hardware', 16, caps=True)
    block((-6.1, -6.3, 53.5), (.18, .34, .75), 'vr_gate_mortar', .12)
    # Surface-mounted drop bolt secures the inactive leaf.
    block((-5.9, 5.8, 14), (1.2, 2.5, 18), 'vr_gate_hardware', .18)
    P.rod(local, (-7.0, 5.8, 1.3), (-7.0, 5.8, 21), .30, 'vr_gate_hardware', 12, caps=True)
    P.rod(local, (-7.0, 5.8, 19.7), (-7.0, 9.0, 19.7), .30, 'vr_gate_hardware', 12, caps=True)
    for z in (4, 14.7):
        block((-7.0, 5.8, z), (1.4, 2.7, 1.2), 'vr_gate_hardware', .15)

    # Small engraved resort identification, sized as hardware rather than a sign.
    block((-5.25, -42.8, 74), (.65, 15, 5.8), 'vr_gate_hardware', .28)
    P.card(local, 'vr_gate_plaque', [(-5.59, -49.9, 71.4), (-5.59, -35.7, 71.4),
           (-5.59, -35.7, 76.6), (-5.59, -49.9, 76.6)], -X,
           uv=[(1, 0), (0, 0), (0, 1), (1, 1)])
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({paint:48. for paint in MATERIALS})
    # Local x is plan east (depth); local y follows the boundary north.
    for paint, polygons in local.polygons.items():
        for i, (points, normal) in enumerate(polygons):
            model.polygon(paint, [p + (east, north, 0) for p in points],
                          uv=local.polygon_uvs.get((paint, i)),
                          normals=local.polygon_normals.get((paint, i)))
    assert not local.boxes and not local.hulls
    return {'east':east, 'north':north, 'triangles':local.triangle_count(),
            'leaves':2, 'piers':2, 'hinges':6}


def material(colour, normal, roughness, tint=(1,1,1), metal=0):
    return ('// Tools/veridant_boundary_wall.py\n"Layer0"\n{\n'
            '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
            f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
            f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n'
            f'    TextureRoughness "{roughness}"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n'
            '    g_flModelTintAmount "1.0"\n}\n')


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    c,r,h,ppi=VM.stone(seed=821,base=(163,160,149),n=1024,tile=96,
                     panel=(96,96),joint=.05,pits=.65,rough=.77)
    # Geometry owns the stone's joints; use only the interior texture range.
    VM.save_rgb(out/'stone_color.jpg',VM.T.linear_to_srgb(c))
    VM.save_rgb(out/'stone_normal.jpg',(VM.RM.normal_map(h*.55,ppi)*.5+.5)*255,quality=95)
    VM.save_grey(out/'stone_rough.png',r)
    rng=np.random.default_rng(961);n=1024
    def noise(sigma):
        a=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap')
        return a/max(a.std(),1e-9)
    broad=noise(35);fine=noise(.65)
    colour=np.array((68,78,72))[None,None,:]*(1+.008*broad+.004*fine)[...,None]
    Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(out/'paint_color.png')
    Image.fromarray(np.clip((.71+.008*broad+.006*fine)*255,0,255).astype('uint8')).save(out/'paint_rough.png')
    # Coating orange-peel is barely perceptible, with no random rust/grime layer.
    dx=(np.roll(fine,-1,1)-np.roll(fine,1,1))*.0016
    dy=(np.roll(fine,-1,0)-np.roll(fine,1,0))*.0016
    normals=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1)[...,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(out/'paint_normal.png')
    plaque=Image.new('RGB',(1024,384),(56,58,48));draw=ImageDraw.Draw(plaque)
    font=ImageFont.truetype(str(K.ASSETS/'fonts/Dinish-Regular.ttf'),104)
    small=ImageFont.truetype(str(K.ASSETS/'fonts/Dinish-Regular.ttf'),41)
    ink=(183,165,119)
    draw.rounded_rectangle((25,24,999,360),radius=20,outline=ink,width=4)
    draw.text((512,155),'VERIDANT',font=font,fill=ink,anchor='mm')
    draw.text((512,264),'P R I V A T E   R E S O R T',font=small,fill=ink,anchor='mm')
    plaque.save(out/'plaque_color.png')
    flat='materials/default/default_normal.tga'
    for name,tint in (('stone',(1,1,1)),('stone_warm',(1.025,.995,.955)),('stone_cool',(.94,.95,.94))):
        (out/f'{name}.vmat').write_text(material(f'{PREFIX}/stone_color.jpg',f'{PREFIX}/stone_normal.jpg',f'{PREFIX}/stone_rough.png',tint))
    (out/'paint.vmat').write_text(material(f'{PREFIX}/paint_color.png',f'{PREFIX}/paint_normal.png',f'{PREFIX}/paint_rough.png'))
    (out/'mortar.vmat').write_text(material('[0.27 0.27 0.24 0]',flat,'[0.91 0.91 0.91 0]'))
    (out/'hardware.vmat').write_text(material('[0.48 0.45 0.36 0]',flat,'[0.39 0.39 0.39 0]',metal=.65))
    (out/'plaque.vmat').write_text(material(f'{PREFIX}/plaque_color.png',flat,'[0.46 0.46 0.46 0]',metal=.65))
