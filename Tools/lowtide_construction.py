"""Native-reviewed construction details used by Lowtide's canonical writers.

Geometry stays in plan coordinates. These adapters change visible construction
only; panes, thresholds, physics, gameplay layout and the grate wells remain
owned by their existing writers.
"""
from functools import lru_cache

DETAIL_SILL_MAX = 320.0


def window_frame(model, module, wall, opening, style):
    from lowtide_window_construction import frame
    frame(model, module, wall, opening, style)


def is_shed_door(module, wall, opening):
    if abs(opening.z0) > .01:
        return False
    depth, _ = wall.outer()
    east, north, _ = wall.point((opening.r0 + opening.r1) * .5, depth, opening.z0)
    for e0, e1, n0, n1 in (module.YARD_SHED, module.QUAY_SHED):
        if e0-.01 <= east <= e1+.01 and n0-.01 <= north <= n1+.01:
            if min(abs(east-e0), abs(east-e1), abs(north-n0), abs(north-n1)) < .01:
                return True
    return False


@lru_cache(maxsize=1)
def door_mapping():
    from lowtide_door_construction import mapping
    return mapping()


def shed_door(model, module, wall, opening, style):
    from lowtide_door_construction import leaf_geometry
    leaf_geometry(model, module, wall, opening, style, door_mapping())


def drainpipe(model, module, e, n, top, out, bottom=3):
    from lowtide_drain_construction import drainpipe as pipe
    from lowtide_drain_junctions import warehouse
    record = dict(e=e, n=n, top=top, out=out, bottom=bottom)
    if top < 400:
        pipe(model, module, **dict(record, top=top-3.))
    else:
        warehouse(model, record)


def gutter(model, module, e0, e1, n, height):
    from lowtide_drain_junctions import gutter as connected_gutter
    side = -1 if e0 + e1 < 0 else 1
    pipes = [values for kind, values in module.FINISH.drainage_layout(module, side)
             if kind == 'pipe']
    outlets = [p for p in pipes if e0 < p[0] < e1 and
               abs(p[2]-(height+.5)) < .01 and abs(abs(p[1]-n)-2.8) < .01]
    if len(outlets) != 2:
        raise ValueError(f'Expected two shed gutter outlets at {e0, e1, n, height}')
    connected_gutter(model, dict(e0=e0, e1=e1, n=n, height=height,
                                outlets=sorted(p[0] for p in outlets),
                                direction=outlets[0][3][1]))


def metal_material(tint, metal, rough):
    from PIL import Image
    import map_kit as K
    with Image.open(K.ROOT/'Tools/lowtide_bridge_steel_source.png') as image:
        w, h = image.size
    with Image.open(K.ASSETS/'materials/lowtide/lt_bridge_steel_color.png') as image:
        pw, ph = image.size
    region = (.5/pw, .5/ph, (w-1)/pw, (h-1)/ph)
    return f'''// Offline candidate: repeat only the original steel scan region.
"Layer0"
{{
    shader "shaders/hc1_lowtide_finish_metal.shader"
    F_SPECULAR "1"
    TextureColor "materials/lowtide/lt_bridge_steel_color.png"
    TextureNormal "materials/lowtide/lt_bridge_steel_normal.png"
    g_flTintColor "[{tint}]"
    g_vFinishRegion "[{' '.join(f'{v:.12f}' for v in region)}]"
    g_flFinishScale "1.5"
    g_flFinishRoughness "{rough}"
    g_flFinishMetalness "{metal}"
}}
'''
