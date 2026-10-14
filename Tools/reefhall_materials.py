"""
Reef Hall's materials (Tools/reefhall_map.py), drawn from scratch with numpy and PIL like Belltower's: polished concrete
floor slabs, form-panelled wall concrete, dark painted steel, gunmetal frames, brushed brass trim, navy quilted vinyl
(the crates' pads), trench drain grating, hazard and yellow floor lines, painted pipes, tank sand, reef rock, coral,
kelp, the floor emblem, the banners, LED strips, the control room's screens and whale bone, and the lobby's entrance
doors: their wall's cladding, anodised and stainless metal, the frosted film on their glass and the planters' plants.

    python Tools/reefhall_materials.py [name ...] [--out <dir>] [--sheet <png>]

- Writes Assets/materials/reefhall/<name>_color.png, _normal.png, _rough.png (and _trans.png for kelp and the film,
  _illum.png for the lit ones) and <name>.vmat. Most are on shaders/complex.shader. The tank glass is on shaders/hc1_tank_glass.shader
  and the offices' and display cases' glass on shaders/glass.shader.
- Every picture tiles, except the decals (DECALS: the emblem, the banners and the screens), which reefhall_map.py maps
  once across their polygon. TILE_UNITS is how many inches a tile covers, which map_kit's world-scale UVs read through
  the model's tile_overrides.
- Normals are OpenGL style (green up the picture), as s&box's model shader reads them.
- The references are wet-looking polished concrete under warm downlights and blue tank light, so the floor's roughness
  runs low (0.14-0.42) with satin patches, and the walls' stays high.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import terrain_textures as T
import building_textures as BT

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/reefhall"
RESOURCE_DIR = "materials/reefhall"
DEFAULT_AO = "materials/default/default_ao.tga"
# Authored ImageGen screens live beside the procedural maps and survive rebuilds.
AUTHORED_COLOR = { "rh_screen_data": "rh_screen_telemetry_color.png" }

spectral, smoothstep, paint, gl_normals = T.spectral, T.smoothstep, BT.paint, BT.gl_normals


def unit( a ):
    return ( a - a.mean() ) / ( a.std() + 1e-9 )


def noise( rng, n, beta, fmin, fmax=None ):
    return unit( spectral( rng, n, beta, fmin, fmax ) )


def grid_distance( n, cells_x, cells_y=None, offset=( 0.0, 0.0 ) ):
    """ Distance in pixels to the nearest line of a cells_x x cells_y grid over the tile. """
    cells_y = cells_y or cells_x
    y, x = np.mgrid[0:n, 0:n].astype( float )
    sx, sy = n / cells_x, n / cells_y
    dx = np.abs( ( ( x + offset[0] ) % sx ) - sx / 2 )
    dy = np.abs( ( ( y + offset[1] ) % sy ) - sy / 2 )
    return np.minimum( sx / 2 - dx, sy / 2 - dy ), x, y


# ---------------------------------------------------------------------------------------------------------------------
# Tiling textures. Each returns ( { paint: colour }, roughness, height, normal strength[, extra maps] ).

def floor( rng, n ):
    """ Polished concrete slabs, 96 in square (two across the tile): fine grey with a cool cast, aggregate specks ground
    flat, faint trowel swirls and mottling, sawn joints between the slabs with a hairline of grime, and satin patches
    where it's been walked on, set into a gloss that reads as wet under the lights. """
    seam, x, y = grid_distance( n, 2 )
    mottle = noise( rng, n, 3.0, 1, 10 )
    swirl = noise( rng, n, 2.2, 6, 40 )
    fine = noise( rng, n, 1.0, n / 8 )
    speck = noise( rng, n, 0.4, n / 6 )
    agg_light = smoothstep( 2.2, 3.0, speck )
    agg_dark = smoothstep( 2.4, 3.2, -speck )
    joint = 1.0 - smoothstep( 1.0, 2.6, seam )
    grime = 1.0 - smoothstep( 2.0, 9.0, seam )
    scuff = smoothstep( 0.6, 1.8, noise( rng, n, 2.6, 3, 30 ) )
    crack = BT.cracks( rng, n, 2, ( 60, 200 ), 0.8 )

    height = 0.5 + 0.015 * swirl + 0.004 * fine - 0.45 * joint - 0.2 * crack
    lum = ( 1.0 + 0.08 * mottle + 0.03 * swirl + 0.025 * fine + 0.10 * agg_light - 0.12 * agg_dark
            - 0.55 * joint - 0.12 * grime - 0.25 * crack )
    colours = { "rh_floor": paint( ( 118, 124, 132 ), lum ) }
    rough = np.clip( 0.11 + 0.04 * mottle + 0.03 * fine + 0.18 * scuff + 0.35 * joint + 0.1 * grime, 0.06, 0.9 )
    return colours, rough, height, 2.0


def wall( rng, n ):
    """ Cast-in-place concrete: form panels 48 x 96 in (two by one across the tile, half-offset rows), their joints
    showing as fine ridges, tie holes in rows, the plywood's grain printed faintly, bug holes, and a little water
    staining under the joints. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    pw, ph = n / 4, n / 2                       # a 48 x 96 panel is a quarter of the tile across, half up (192 tile)
    row = np.floor( y / ph )
    xo = ( x + ( row % 2 ) * pw / 2 ) % pw
    yo = y % ph
    seam = np.minimum( np.minimum( xo, pw - xo ), np.minimum( yo, ph - yo ) )
    ridge = 1.0 - smoothstep( 0.6, 1.8, seam )
    # Tie holes: 2 x 3 per panel, 8 in from the edges.
    tx = np.minimum( np.abs( xo - pw * 0.17 ), np.abs( xo - pw * 0.83 ) )
    ty = np.min( [ np.abs( yo - ph * f ) for f in ( 0.12, 0.5, 0.88 ) ], axis=0 )
    tie = 1.0 - smoothstep( 3.0, 5.0, np.hypot( tx, ty ) )
    tie_ring = np.exp( -( ( np.hypot( tx, ty ) - 6.5 ) / 1.6 ) ** 2 )
    grain = BT.stretched( rng, n, 1.6, 8, n / 4, ( 0.5, 6.0 ) )
    blotch = noise( rng, n, 3.0, 1, 12 )
    fine = noise( rng, n, 1.0, n / 6 )
    pores = smoothstep( 2.7, 3.3, -noise( rng, n, 0.5, n / 8 ) )
    stain = np.clip( BT.stretched( rng, n, 2.0, 4, 60, ( 18.0, 1.0 ) ), 0, None ) * ( yo / ph ) * 0.6
    tone = ( row + np.floor( ( x + ( row % 2 ) * pw / 2 ) / pw ) ) % 3

    height = 0.5 + 0.02 * grain + 0.02 * fine + 0.25 * ridge - 0.5 * tie - 0.3 * pores
    lum = ( 1.0 + 0.06 * blotch + 0.02 * grain + 0.025 * fine + 0.03 * ( tone - 1 ) - 0.45 * tie + 0.04 * tie_ring
            - 0.25 * pores - 0.08 * stain + 0.04 * ridge )
    colours = { "rh_wall": paint( ( 150, 152, 152 ), lum ), "rh_wall_dark": paint( ( 104, 108, 112 ), lum ) }
    rough = np.clip( 0.72 + 0.05 * fine - 0.06 * stain + 0.1 * pores, 0, 1 )
    return colours, rough, height, 2.2


def smooth( rng, n ):
    """ Smooth precast concrete for columns, soffits, beams and the crates' blocks: even, faintly mottled, with pin
    holes and soft chipped edges' dust. """
    blotch = noise( rng, n, 3.0, 1, 8 )
    fine = noise( rng, n, 1.0, n / 6 )
    pores = smoothstep( 2.8, 3.4, -noise( rng, n, 0.5, n / 6 ) )
    streak = BT.stretched( rng, n, 2.0, 4, 40, ( 14.0, 1.2 ) )
    height = 0.5 + 0.02 * fine - 0.3 * pores
    lum = 1.0 + 0.06 * blotch + 0.02 * fine - 0.25 * pores - 0.03 * np.clip( streak, 0, None )
    colours = { "rh_smooth": paint( ( 156, 158, 160 ), lum ), "rh_block": paint( ( 168, 166, 160 ), lum ) }
    rough = np.clip( 0.58 + 0.06 * fine + 0.04 * blotch, 0, 1 )
    return colours, rough, height, 1.6


def steel( rng, n ):
    """ Dark painted steel (railings, beams, door frames, the crates' frames): a satin navy-grey coat, faintly orange
    peeled, rubbed lighter where hands and boots wear it, with fine scratches. """
    peel = noise( rng, n, 1.2, n / 10 )
    blotch = noise( rng, n, 3.0, 1, 10 )
    wear = smoothstep( 1.4, 2.4, noise( rng, n, 2.4, 3, 40 ) )
    scratch = BT.cracks( rng, n, 30, ( 10, 60 ), 0.6, branch=0.0 )
    height = 0.5 + 0.01 * peel - 0.1 * scratch
    lum = 1.0 + 0.04 * blotch + 0.015 * peel + 0.18 * wear + 0.35 * scratch
    colours = { "rh_steel": paint( ( 48, 56, 68 ), lum ), "rh_steel_blue": paint( ( 38, 58, 92 ), lum ) }
    rough = np.clip( 0.38 + 0.04 * peel - 0.1 * wear - 0.12 * scratch, 0, 1 )
    return colours, rough, height, 1.0


def gunmetal( rng, n ):
    """ Bare gunmetal (the tank windows' heavy frames, the tunnel's ribs, the rotunda's column): blued steel, finely
    brushed along, with the odd darker water stain. """
    brush = BT.stretched( rng, n, 1.0, 8, n / 2, ( 0.4, 12.0 ) )
    blotch = noise( rng, n, 3.0, 1, 8 )
    height = 0.5 + 0.004 * brush
    lum = 1.0 + 0.04 * brush + 0.06 * blotch
    colours = { "rh_gunmetal": paint( ( 70, 78, 88 ), lum ) }
    rough = np.clip( 0.32 + 0.05 * brush + 0.05 * blotch, 0, 1 )
    return colours, rough, height, 0.6


def brass( rng, n ):
    """ Brushed brass trim (the crates' corner guards and bands, the reception desk's edge): warm, brushed one way,
    darker in the grain, polished where it's handled. """
    brush = BT.stretched( rng, n, 1.0, 8, n / 2, ( 0.4, 14.0 ) )
    tarnish = smoothstep( 0.5, 2.0, noise( rng, n, 2.6, 2, 24 ) )
    height = 0.5 + 0.004 * brush
    lum = 1.0 + 0.05 * brush - 0.18 * tarnish
    colours = { "rh_brass": paint( ( 168, 132, 78 ), lum ), "rh_bronze": paint( ( 150, 96, 58 ), lum ) }
    rough = np.clip( 0.30 + 0.06 * brush + 0.12 * tarnish, 0, 1 )
    return colours, rough, height, 0.6


def pad( rng, n ):
    """ Navy quilted vinyl (the padded fronts and lids of the exhibit crates): tufted panels 12 in across (four to the
    tile), stitched seams sunk between them, a soft sheen, scuffs. """
    seam, x, y = grid_distance( n, 4, 2 )
    stitch = ( 1.0 - smoothstep( 1.0, 3.0, seam ) )
    puff = smoothstep( 0.0, n / 10, seam )
    crease = noise( rng, n, 2.0, 4, 40 )
    fine = noise( rng, n, 0.8, n / 6 )
    height = 0.2 + 0.5 * puff + 0.02 * crease + 0.01 * fine
    lum = 1.0 + 0.06 * crease + 0.03 * fine - 0.35 * stitch
    colours = { "rh_pad": paint( ( 42, 60, 108 ), lum ), "rh_pad_dark": paint( ( 30, 40, 70 ), lum ) }
    rough = np.clip( 0.48 + 0.05 * fine + 0.1 * stitch, 0, 1 )
    return colours, rough, height, 3.0


def grate( rng, n ):
    """ A trench drain's grating, 16 in across the tile: cast bars across a dark slot, rims along both sides. The
    channel under it reads black. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    bars = 16
    period = n / bars
    bx = np.abs( ( x % period ) - period / 2 )
    bar = 1.0 - smoothstep( period * 0.22, period * 0.32, bx )
    rim = 1.0 - smoothstep( n * 0.07, n * 0.09, np.minimum( y, n - y ) )
    solid = np.maximum( bar, rim )
    fine = noise( rng, n, 1.0, n / 8 )
    height = 0.1 + 0.8 * solid + 0.02 * fine
    lum = ( 0.06 + 0.94 * solid ) * ( 1.0 + 0.08 * fine )
    colours = { "rh_grate": paint( ( 60, 64, 70 ), lum ) }
    rough = np.clip( 0.45 - 0.1 * solid + 0.05 * fine, 0, 1 )
    return colours, rough, height, 4.0


def lines( rng, n ):
    """ Floor paint over the polished concrete: yellow hazard chevrons (45 degree stripes) and a plain yellow line, the
    paint worn through in patches and glossy like the floor. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    stripe = ( ( ( x + y ) / ( n / 2 ) ) % 1.0 ) < 0.5
    worn = smoothstep( 1.0, 2.2, noise( rng, n, 2.0, 4, 60 ) )
    fine = noise( rng, n, 1.0, n / 8 )
    base_floor = paint( ( 118, 124, 132 ), 1.0 + 0.05 * fine )
    yellow = paint( ( 206, 168, 46 ), 1.0 + 0.05 * fine )
    black = paint( ( 30, 30, 32 ), 1.0 + 0.05 * fine )
    hz = np.where( stripe[..., None], yellow, black )
    hz = BT.mix( hz, base_floor, worn * 0.85 )
    ln = BT.mix( yellow, base_floor, worn * 0.85 )
    height = 0.5 + 0.02 * fine + 0.03 * ( 1 - worn )
    colours = { "rh_hazard": hz, "rh_line": ln }
    rough = np.clip( 0.22 + 0.06 * fine + 0.1 * worn, 0, 1 )
    return colours, rough, height, 1.0


def pipe( rng, n ):
    """ Painted pipework (the filter hall's mains): glossy blue enamel, a little wavy where it was rolled on, with
    darker water streaks running down. """
    roll = BT.stretched( rng, n, 1.5, 4, n / 4, ( 1.0, 8.0 ) )
    blotch = noise( rng, n, 3.0, 1, 8 )
    streak = np.clip( BT.stretched( rng, n, 2.0, 4, 60, ( 20.0, 1.0 ) ), 0, None )
    height = 0.5 + 0.01 * roll
    lum = 1.0 + 0.03 * roll + 0.05 * blotch - 0.1 * streak
    colours = { "rh_pipe": paint( ( 36, 54, 88 ), lum ), "rh_pipe_dark": paint( ( 26, 36, 58 ), lum ) }
    rough = np.clip( 0.24 + 0.04 * roll + 0.06 * streak, 0, 1 )
    return colours, rough, height, 0.8


def sand( rng, n ):
    """ Tank sand: fine pale grains in ripples, crushed shell, a few pebbles, darker in the troughs. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    warp = noise( rng, n, 3.0, 1, 6 )
    ripple = np.sin( ( y / n * 10 + 0.8 * warp ) * 2 * math.pi )
    grain = noise( rng, n, 0.3, n / 4 )
    shell = smoothstep( 2.6, 3.2, noise( rng, n, 0.6, n / 12 ) )
    pebble = smoothstep( 2.8, 3.3, noise( rng, n, 1.2, n / 30, n / 10 ) )
    height = 0.5 + 0.08 * ripple + 0.02 * grain + 0.2 * pebble
    lum = 1.0 + 0.08 * ripple + 0.1 * grain + 0.25 * shell - 0.3 * pebble
    colours = { "rh_sand": paint( ( 182, 176, 156 ), lum ) }
    rough = np.clip( 0.9 + 0.04 * grain, 0, 1 )
    return colours, rough, height, 3.0


def rock( rng, n ):
    """ Reef rock (the arches, pinnacles and the rotunda's core): porous limestone in warm greys, pitted with holes,
    with crusts of coralline algae (pink-purple) and green film on the tops. """
    big = noise( rng, n, 2.6, 2, 20 )
    mid = noise( rng, n, 1.6, 8, 60 )
    fine = noise( rng, n, 0.8, n / 8 )
    holes = smoothstep( 1.4, 2.4, -noise( rng, n, 1.2, 16, 90 ) )
    crust = smoothstep( 0.6, 1.6, noise( rng, n, 2.0, 4, 40 ) )
    film = smoothstep( 0.8, 1.8, big )
    height = 0.5 + 0.18 * big + 0.1 * mid + 0.04 * fine - 0.4 * holes
    lum = 1.0 + 0.12 * big + 0.08 * mid + 0.06 * fine - 0.55 * holes
    base = paint( ( 126, 120, 110 ), lum )
    base = BT.mix( base, paint( ( 152, 98, 126 ), lum ), crust * 0.45 )
    base = BT.mix( base, paint( ( 96, 122, 88 ), lum ), film * 0.35 )
    colours = { "rh_rock": base }
    rough = np.clip( 0.86 + 0.05 * fine, 0, 1 )
    return colours, rough, height, 5.0


def coral( rng, n ):
    """ Living coral's skin: polyps packed in a cellular pattern, each a raised ring with a dark mouth, tinted per
    colony: pink, orange, yellow, purple, green and a pale bleached white. """
    pts = rng.uniform( 0, n, ( 900, 2 ) )
    pts = np.concatenate( [ pts + ( dx, dy ) for dx in ( -n, 0, n ) for dy in ( -n, 0, n ) ] )
    from scipy.spatial import cKDTree
    y, x = np.mgrid[0:n, 0:n].astype( float )
    d, _ = cKDTree( pts ).query( np.stack( [ x.ravel(), y.ravel() ], -1 ), k=2 )
    d0 = d[:, 0].reshape( n, n )
    edge = ( d[:, 1] - d[:, 0] ).reshape( n, n )
    cell = n / 30.0
    mouth = 1.0 - smoothstep( cell * 0.12, cell * 0.22, d0 )
    rim = np.exp( -( ( d0 - cell * 0.3 ) / ( cell * 0.12 ) ) ** 2 )
    valley = 1.0 - smoothstep( 0.0, cell * 0.25, edge )
    fine = noise( rng, n, 1.0, n / 8 )
    height = 0.5 + 0.3 * rim - 0.4 * mouth - 0.3 * valley + 0.03 * fine
    lum = 1.0 + 0.2 * rim - 0.6 * mouth - 0.25 * valley + 0.05 * fine
    tints = { "rh_coral_pink": ( 214, 104, 138 ), "rh_coral_orange": ( 222, 120, 62 ), "rh_coral_yellow": ( 216, 188, 70 ),
              "rh_coral_purple": ( 128, 82, 168 ), "rh_coral_green": ( 92, 160, 108 ), "rh_coral_white": ( 214, 208, 196 ) }
    colours = { name: paint( rgb, lum ) for name, rgb in tints.items() }
    rough = np.clip( 0.62 + 0.05 * fine - 0.15 * mouth, 0, 1 )
    return colours, rough, height, 4.0


def kelp( rng, n ):
    """ A kelp blade's texture across a frond strip: a gold-green leaf with a darker midrib, ruffled edges cut out by
    the alpha (the trans map), veins and translucent spots. u runs across the strip, v along it. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    u = x / n - 0.5
    v = y / n
    ruffle = 0.06 * np.sin( v * 2 * math.pi * 6 + 1.3 ) + 0.03 * np.sin( v * 2 * math.pi * 17 )
    halfwidth = 0.42 + ruffle
    alpha = 1.0 - smoothstep( halfwidth - 0.015, halfwidth + 0.005, np.abs( u ) )
    midrib = np.exp( -( u / 0.03 ) ** 2 )
    veins = np.clip( np.sin( ( v * 40 + np.abs( u ) * 6 ) * 2 * math.pi ), 0, 1 ) ** 6 * ( np.abs( u ) / 0.42 )
    blot = noise( rng, n, 2.4, 2, 30 )
    fine = noise( rng, n, 1.0, n / 8 )
    lum = 1.0 + 0.1 * blot + 0.04 * fine - 0.2 * midrib + 0.08 * veins - 0.25 * ( np.abs( u ) / 0.42 ) ** 3
    colour = BT.mix( paint( ( 120, 140, 52 ), lum ), paint( ( 176, 164, 66 ), lum ), smoothstep( -0.5, 1.5, blot ) )
    height = 0.5 + 0.1 * midrib + 0.05 * veins + 0.02 * fine
    rough = np.clip( 0.5 + 0.05 * fine, 0, 1 )
    return { "rh_kelp": colour }, rough, height, 1.5, { "trans": alpha }


def bone( rng, n ):
    """ The whale skeleton's bone: ivory, porous at the ends, smoother along the shafts, aged yellow in the hollows. """
    grain = BT.stretched( rng, n, 1.5, 4, n / 4, ( 1.0, 10.0 ) )
    blotch = noise( rng, n, 3.0, 1, 10 )
    pores = smoothstep( 2.4, 3.2, -noise( rng, n, 0.6, n / 10 ) )
    height = 0.5 + 0.03 * grain - 0.3 * pores
    lum = 1.0 + 0.05 * grain + 0.06 * blotch - 0.3 * pores
    colour = BT.mix( paint( ( 214, 206, 186 ), lum ), paint( ( 186, 168, 128 ), lum ), smoothstep( 0.5, 2.0, -blotch ) )
    rough = np.clip( 0.55 + 0.05 * grain + 0.1 * pores, 0, 1 )
    return { "rh_bone": colour }, rough, height, 2.0


def tankback( rng, n ):
    """ The far walls and floor edges inside a tank, painted as the dark rockwork real aquariums use to hide their back
    walls. The tank glass's water absorption fades them to the water's own blue. """
    big = noise( rng, n, 2.8, 2, 16 )
    mid = noise( rng, n, 1.8, 8, 60 )
    holes = smoothstep( 1.6, 2.6, -noise( rng, n, 1.2, 16, 90 ) )
    height = 0.5 + 0.2 * big + 0.1 * mid - 0.3 * holes
    lum = 1.0 + 0.15 * big + 0.08 * mid - 0.5 * holes
    return { "rh_tankback": paint( ( 62, 92, 108 ), lum ) }, np.full( ( n, n ), 0.9 ), height, 5.0


def plain( rng, n ):
    """ Plain finishes: the desk's dark laminate, rubber (chairs, cable trays), a light panel ceiling, and the LED
    strips' and sconces' diffusers, whose colour is their light (they're self-lit, ILLUM). """
    fine = noise( rng, n, 1.0, n / 8 )
    blotch = noise( rng, n, 3.0, 1, 8 )
    lum = 1.0 + 0.03 * fine + 0.04 * blotch
    colours = { "rh_laminate": paint( ( 44, 48, 56 ), lum ), "rh_rubber": paint( ( 22, 24, 26 ), lum ),
                "rh_ceiling": paint( ( 120, 126, 132 ), lum ), "rh_led_warm": paint( ( 255, 214, 160 ), 1.0 + 0.01 * fine ),
                "rh_led_cool": paint( ( 186, 222, 255 ), 1.0 + 0.01 * fine ), "rh_black": paint( ( 12, 13, 15 ), lum ),
                "rh_frosted_lit": paint( ( 168, 158, 140 ), 1.0 + 0.02 * blotch ),
                "rh_soil": paint( ( 44, 34, 27 ), 1.0 + 0.12 * fine + 0.08 * blotch ) }
    rough = np.clip( 0.5 + 0.05 * fine, 0, 1 )
    return colours, rough, 0.5 + 0.01 * fine, 0.4


def panel( rng, n ):
    """ The lobby's entrance wall cladding (the user's door reference): large satin panels in a dark blue-grey, faintly
    mottled with a fine orange peel, hung with real shadow gaps (reefhall_map's clad_wall draws each panel), so the
    picture has no joints. rh_panel_b is a slightly darker panel to set among them, rh_portal the near-black anthracite
    of the doors' surrounds and reveals, which also shows in the gaps. """
    blotch = noise( rng, n, 3.0, 1, 8 )
    peel = noise( rng, n, 1.1, n / 12 )
    fine = noise( rng, n, 1.0, n / 4 )
    smear = BT.stretched( rng, n, 2.0, 2, 30, ( 1.0, 16.0 ) )
    lum = 1.0 + 0.035 * blotch + 0.012 * peel + 0.01 * fine + 0.02 * smear
    colours = { "rh_panel": paint( ( 82, 87, 94 ), lum ), "rh_panel_b": paint( ( 74, 79, 86 ), lum ),
                "rh_portal": paint( ( 32, 34, 38 ), lum ) }
    rough = np.clip( 0.46 + 0.04 * peel + 0.03 * blotch - 0.03 * smear, 0, 1 )
    return colours, rough, 0.5 + 0.006 * peel + 0.002 * fine, 0.5


def doorframe( rng, n ):
    """ The entrance doors' metal: dark grey anodised aluminium (the frames, 'rh_anodised'), finely brushed with a satin
    sheen (its dyed oxide reads more like a satin paint than bare metal), and brushed stainless steel (the pull bars,
    the closer's cover, the threshold: 'rh_stainless'). """
    brush = BT.stretched( rng, n, 1.0, 8, n / 2, ( 0.4, 14.0 ) )
    blotch = noise( rng, n, 3.0, 1, 8 )
    scratch = BT.cracks( rng, n, 18, ( 8, 40 ), 0.5, branch=0.0 )
    height = 0.5 + 0.002 * brush - 0.02 * scratch
    lum = 1.0 + 0.015 * brush + 0.02 * blotch
    colours = { "rh_anodised": paint( ( 74, 77, 82 ), lum + 0.05 * scratch ),
                "rh_stainless": paint( ( 204, 206, 208 ), lum - 0.03 * scratch ) }
    rough = np.clip( 0.36 + 0.03 * brush + 0.02 * blotch - 0.04 * scratch, 0, 1 )
    return colours, rough, height, 0.5


# The entrance doors' frosted film covers both leaves' glass of a pair as one picture, so its waves run on from one leaf
# into the other. FILM_W x FILM_H inches: from the left leaf's glass's outer edge to the right one's, and from the
# glass's foot to its head. reefhall_map's door_pair lays each leaf's glass on its own part of the picture.
FILM_W, FILM_H = 87.0, 83.0
FILM_GAP = 4.625                # the glass's inner edge, either side of the pair's middle
FILM_WAVES = ( 23.5, 30.0 )     # the two lines' middles, up from the glass's foot
FILM_JELLY = ( 76.1, 55.0, 63.5 )   # the jellyfish's middle across, its bell's rim and top, up from the glass's foot


def film( rng, n ):
    """ The entrance doors' frosted vinyl (the user's reference): two wavy lines across both leaves, and a jellyfish
    on the right leaf, a plain bell with five wavy tentacles under it. Alpha tested (the trans map is
    the cut), frosted white with a fine sandblasted grain. The picture is FILM_W x FILM_H inches over the square. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    sx, sy = FILM_W / n, FILM_H / n
    ux = ( x + 0.5 ) * sx                       # inches across the pair's glass
    uy = FILM_H - ( y + 0.5 ) * sy              # inches up from the glass's foot (the picture's top is up)
    px = min( sx, sy )

    def edge( d ):                              # a signed distance (inches, inside < 0) to coverage
        return np.clip( 0.5 - d / px, 0.0, 1.0 )

    cover = np.zeros( ( n, n ) )
    # The waves: one sine across the whole pair, the two lines in step, 1.3 in wide.
    lam, amp = 46.0, 1.7
    phase = 2 * math.pi * ux / lam + 0.9
    slope = amp * 2 * math.pi / lam * np.cos( phase )
    for y0 in FILM_WAVES:
        d = np.abs( uy - ( y0 + amp * np.sin( phase ) ) ) / np.sqrt( 1 + slope ** 2 ) - 0.65
        cover = np.maximum( cover, edge( d ) )
    # The jellyfish's bell: a squared-off dome over a rim with four soft scallops.
    jx, rim, top = FILM_JELLY
    rx, ry = 6.3, top - rim
    dx = ux - jx
    t = np.clip( ( uy - rim ) / ry, 0, None )
    p = 2.4
    dome = ( np.abs( dx ) / rx ) ** p + t ** p
    bell_out = ( dome ** ( 1 / p ) - 1.0 ) * min( rx, ry )
    scallop = 0.55 * np.abs( np.sin( np.clip( dx / rx, -1, 1 ) * math.pi * 2.0 ) ) + 0.15
    below = ( rim - scallop ) - uy                       # under the rim: outside by this much
    bell = np.maximum( bell_out, below )
    cover = np.maximum( cover, edge( bell ) )
    # Five tentacles, each a wavy line hanging from the rim, the middle ones longest, thinning to a rounded tip.
    for k, ( x0, length, ph ) in enumerate( ( ( -4.5, 10.5, 0.3 ), ( -2.25, 12.5, 2.4 ), ( 0.0, 14.0, 4.4 ),
                                              ( 2.25, 12.0, 1.2 ), ( 4.5, 10.0, 3.4 ) ) ):
        s = np.clip( ( rim - 0.2 ) - uy, 0, None )                    # inches down the tentacle
        wob = 0.42 + 0.22 * s / length
        cx = jx + x0 + wob * np.sin( 2 * math.pi * s / 4.2 + ph ) * np.clip( s / 2.0, 0, 1 )
        dcx = wob * 2 * math.pi / 4.2 * np.cos( 2 * math.pi * s / 4.2 + ph )
        half = 0.42 - 0.12 * np.clip( s / length, 0, 1 )
        d = np.abs( ux - cx ) / np.sqrt( 1 + dcx ** 2 ) - half
        d = np.where( s > length, np.hypot( ux - cx, uy - ( rim - 0.2 - length ) ) - half, d )
        d = np.where( uy > rim + 0.5, 9.0, d )
        cover = np.maximum( cover, edge( d ) )
    grain = noise( rng, n, 0.6, n / 4 )
    blotch = noise( rng, n, 3.0, 1, 6 )
    lum = 1.0 + 0.025 * grain + 0.02 * blotch
    colour = paint( ( 214, 220, 224 ), lum )
    rough = np.clip( 0.62 + 0.05 * grain, 0, 1 )
    return { "rh_film": colour }, rough, 0.5 + 0.01 * grain, 0.4, { "trans": cover }


def plantleaf( rng, n ):
    """ A dracaena's strap leaf, the lobby planters' plants: u across the leaf (its edges at 0 and 1), v from its base to
    its tip. Deep green at the edges, a paler yellow-green band down the middle and a narrow pale midrib, with fine
    parallel veins along it. The leaves' outlines are their own geometry, so no cut. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    u = ( x + 0.5 ) / n - 0.5
    v = 1.0 - ( y + 0.5 ) / n
    band = np.exp( -( u / 0.2 ) ** 4 )
    midrib = np.exp( -( u / 0.025 ) ** 2 )
    veins = np.cos( u * 2 * math.pi * 26 ) ** 8 * 0.5
    blot = noise( rng, n, 2.6, 2, 20 )
    streak = BT.stretched( rng, n, 1.6, 4, n / 4, ( 18.0, 0.6 ) )
    lum = 1.0 + 0.06 * blot + 0.04 * streak - 0.06 * veins - 0.18 * ( np.abs( u ) / 0.5 ) ** 3 + 0.08 * v
    green = paint( ( 46, 104, 44 ), lum )
    light = paint( ( 128, 160, 62 ), lum )
    colour = BT.mix( green, light, np.clip( 0.75 * band + 0.6 * midrib, 0, 1 ) )
    height = 0.5 + 0.08 * midrib - 0.03 * veins + 0.01 * streak
    rough = np.clip( 0.42 + 0.04 * streak, 0, 1 )
    return { "rh_leaf": colour }, rough, height, 1.0


# ---------------------------------------------------------------------------------------------------------------------
# Decals, drawn once across their polygon

def emblem( rng, n ):
    """ The rotunda's floor emblem (ref5): a navy disc inlaid in the polished concrete, ringed in brushed brass, with
    three white waves across it. The square's corners are the floor itself, so the square replaces a floor slab. """
    floor_c, floor_r, floor_h, _ = floor( np.random.default_rng( 7 ), n )
    base = floor_c["rh_floor"].astype( float )
    y, x = np.mgrid[0:n, 0:n].astype( float )
    r = np.hypot( x - n / 2, y - n / 2 ) / ( n / 2 )
    disc = 1.0 - smoothstep( 0.855, 0.865, r )
    ring = np.clip( smoothstep( 0.865, 0.875, r ) - smoothstep( 0.92, 0.93, r ), 0, 1 )
    fine = noise( rng, n, 1.0, n / 8 )
    navy = paint( ( 30, 52, 96 ), 1.0 + 0.05 * fine )
    wave = np.zeros( ( n, n ) )
    u, v = ( x - n / 2 ) / ( n / 2 ), ( y - n / 2 ) / ( n / 2 )
    for k, off in enumerate( ( -0.28, 0.0, 0.28 ) ):
        crest = off + 0.09 * np.sin( u * 2 * math.pi * 1.2 + k * 0.9 ) + 0.04 * np.sin( u * 2 * math.pi * 2.6 )
        wave = np.maximum( wave, 1.0 - smoothstep( 0.028, 0.04, np.abs( v - crest ) ) )
    wave *= 1.0 - smoothstep( 0.62, 0.66, r )
    white = paint( ( 210, 220, 230 ), 1.0 + 0.03 * fine )
    gold = paint( ( 176, 142, 82 ), 1.0 + 0.05 * fine )
    colour = BT.mix( base, navy, disc )
    colour = BT.mix( colour, white, wave * disc )
    colour = BT.mix( colour, gold, ring )
    rough = np.where( disc > 0.5, 0.14 + 0.02 * fine, floor_r )
    rough = np.where( ring > 0.5, 0.28, rough )
    height = floor_h + 0.05 * ring
    return { "rh_emblem": colour }, rough, height, 1.5


def emblem_ray( rng, n ):
    """ The tunnel's floor emblem (ref1): the same navy disc and brass ring with a pale manta ray seen from above. """
    floor_c, floor_r, floor_h, _ = floor( np.random.default_rng( 11 ), n )
    base = floor_c["rh_floor"].astype( float )
    y, x = np.mgrid[0:n, 0:n].astype( float )
    r = np.hypot( x - n / 2, y - n / 2 ) / ( n / 2 )
    disc = 1.0 - smoothstep( 0.855, 0.865, r )
    ring = np.clip( smoothstep( 0.865, 0.875, r ) - smoothstep( 0.92, 0.93, r ), 0, 1 )
    fine = noise( rng, n, 1.0, n / 8 )
    ray = Image.new( "L", ( n, n ), 0 )
    d = ImageDraw.Draw( ray )
    c = n / 2
    s = n / 2 * 0.62
    wing = [ ( c, c - 0.35 * s ), ( c + 0.4 * s, c - 0.25 * s ), ( c + 1.0 * s, c + 0.05 * s ), ( c + 0.45 * s, c + 0.18 * s ),
             ( c + 0.12 * s, c + 0.45 * s ), ( c, c + 0.5 * s ), ( c - 0.12 * s, c + 0.45 * s ), ( c - 0.45 * s, c + 0.18 * s ),
             ( c - 1.0 * s, c + 0.05 * s ), ( c - 0.4 * s, c - 0.25 * s ) ]
    d.polygon( wing, fill=255 )
    d.line( [ ( c, c + 0.45 * s ), ( c + 0.05 * s, c + 1.05 * s ) ], fill=255, width=max( 2, n // 220 ) )
    for side in ( -1, 1 ):
        d.polygon( [ ( c + side * 0.08 * s, c - 0.3 * s ), ( c + side * 0.16 * s, c - 0.48 * s ), ( c + side * 0.2 * s, c - 0.28 * s ) ], fill=255 )
    mask = np.asarray( ray.filter( ImageFilter.GaussianBlur( 1.2 ) ), float ) / 255.0
    navy = paint( ( 30, 52, 96 ), 1.0 + 0.05 * fine )
    pale = paint( ( 196, 210, 224 ), 1.0 + 0.03 * fine )
    gold = paint( ( 176, 142, 82 ), 1.0 + 0.05 * fine )
    colour = BT.mix( base, navy, disc )
    colour = BT.mix( colour, pale, mask * disc )
    colour = BT.mix( colour, gold, ring )
    rough = np.where( disc > 0.5, 0.14 + 0.02 * fine, floor_r )
    rough = np.where( ring > 0.5, 0.28, rough )
    return { "rh_emblem_ray": colour }, rough, floor_h + 0.05 * ring, 1.5


def banner( rng, n ):
    """ The lobby's banners (ref4): heavy navy cloth, a woven texture, a thin pale border, and a white print: a manta
    ray seen from below, and a jellyfish trailing its arms. No writing. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    weave = 0.5 * ( np.sin( x * math.pi / 2 ) * np.sin( y * math.pi / 2 ) )
    fine = noise( rng, n, 1.0, n / 8 )
    fold = noise( rng, n, 3.0, 1, 4 )
    lum = 1.0 + 0.04 * weave + 0.04 * fine + 0.06 * fold
    navy = paint( ( 28, 48, 92 ), lum )
    white = paint( ( 214, 222, 232 ), lum )
    border = ( np.minimum( np.minimum( x, n - x ), np.minimum( y, n - y ) ) )
    edge = np.clip( smoothstep( n * 0.03, n * 0.034, border ) - smoothstep( n * 0.04, n * 0.044, border ), 0, 1 )
    out = {}
    for name in ( "manta", "jelly" ):
        img = Image.new( "L", ( n, n ), 0 )
        d = ImageDraw.Draw( img )
        c = n / 2
        if name == "manta":
            s = n * 0.36
            cy = n * 0.38
            d.polygon( [ ( c, cy - 0.3 * s ), ( c + 0.35 * s, cy - 0.2 * s ), ( c + 1.0 * s, cy + 0.15 * s ), ( c + 0.4 * s, cy + 0.25 * s ),
                         ( c + 0.12 * s, cy + 0.55 * s ), ( c, cy + 0.6 * s ), ( c - 0.12 * s, cy + 0.55 * s ), ( c - 0.4 * s, cy + 0.25 * s ),
                         ( c - 1.0 * s, cy + 0.15 * s ), ( c - 0.35 * s, cy - 0.2 * s ) ], fill=255 )
            d.line( [ ( c, cy + 0.55 * s ), ( c + 0.04 * s, cy + 1.4 * s ) ], fill=255, width=max( 3, n // 160 ) )
            for side in ( -1, 1 ):
                d.polygon( [ ( c + side * 0.07 * s, cy - 0.26 * s ), ( c + side * 0.14 * s, cy - 0.44 * s ),
                             ( c + side * 0.19 * s, cy - 0.24 * s ) ], fill=255 )
        else:
            s = n * 0.2
            cy = n * 0.3
            d.chord( ( c - s, cy - s * 0.8, c + s, cy + s * 0.8 ), 180, 360, fill=255 )
            d.rectangle( ( c - s, cy - 2, c + s, cy + s * 0.08 ), fill=255 )
            for k in range( 7 ):
                x0 = c - s * 0.8 + k * s * 1.6 / 6
                pts = [ ( x0 + 8 * math.sin( t * 0.35 + k ), cy + s * 0.08 + t * n * 0.012 ) for t in range( 34 ) ]
                d.line( pts, fill=255, width=max( 2, n // 300 ) )
            for k in range( 3 ):
                x0 = c - s * 0.3 + k * s * 0.3
                pts = [ ( x0 + 14 * math.sin( t * 0.22 + k * 2 ), cy + s * 0.1 + t * n * 0.008 ) for t in range( 45 ) ]
                d.line( pts, fill=255, width=max( 5, n // 110 ) )
        mask = np.asarray( img.filter( ImageFilter.GaussianBlur( 1.0 ) ), float ) / 255.0
        colour = BT.mix( navy, white, np.maximum( mask, edge ) )
        out[f"rh_banner_{name}"] = colour
    rough = np.clip( 0.85 + 0.03 * fine, 0, 1 )
    return out, rough, 0.5 + 0.02 * weave + 0.01 * fine, 1.0


def screens( rng, n ):
    """ The control room's monitors (ref2): a dark blue UI with no writing. A sea-floor relief map, a sonar scope, and
    a panel of gauges and trend lines. Self-lit (ILLUM), with the bezel's glass reflecting over them. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    u, v = x / n, y / n
    bg = np.stack( [ np.full( ( n, n ), 6.0 ), np.full( ( n, n ), 22.0 ), np.full( ( n, n ), 46.0 ) ], -1 )
    grid = ( ( np.abs( ( u * 24 ) % 1 - 0.5 ) > 0.47 ) | ( np.abs( ( v * 14 ) % 1 - 0.5 ) > 0.46 ) ) * 0.25
    frame = ( ( u < 0.02 ) | ( u > 0.98 ) | ( v < 0.03 ) | ( v > 0.97 ) ) * 0.8
    cyan = np.array( ( 80, 200, 255 ), float )
    out = {}
    # Relief map: contour lines of a noise field, filled shallow-to-deep.
    field = smoothstep( -2, 2, noise( np.random.default_rng( 5 ), n, 3.2, 1, 12 ) )
    contour = np.abs( ( field * 12 ) % 1 - 0.5 ) > 0.45
    inset = ( u > 0.08 ) & ( u < 0.92 ) & ( v > 0.12 ) & ( v < 0.9 )
    img = bg + grid[..., None] * cyan * 0.4 + frame[..., None] * cyan * 0.6
    img = np.where( inset[..., None], np.stack( [ 20 + 40 * field, 70 + 110 * field, 120 + 100 * field ], -1 ), img )
    img = np.where( ( inset & contour )[..., None], cyan * 1.1, img )
    out["rh_screen_map"] = img
    # Sonar scope: rings, a sweep and a few contacts.
    r = np.hypot( u - 0.5, ( v - 0.5 ) * 0.6 / 0.6 )
    ang = np.arctan2( v - 0.5, u - 0.5 )
    rings = ( np.abs( ( r * 10 ) % 1 - 0.5 ) > 0.46 ) & ( r < 0.42 )
    cross = ( ( np.abs( u - 0.5 ) < 0.003 ) | ( np.abs( v - 0.5 ) < 0.003 ) ) & ( r < 0.42 )
    sweep = np.clip( 1 - ( ( ang - 0.6 ) % ( 2 * math.pi ) ) / 1.2, 0, 1 ) * ( r < 0.42 )
    img = bg + frame[..., None] * cyan * 0.6
    img = img + ( rings | cross )[..., None] * cyan * 0.8 + sweep[..., None] * np.array( ( 30, 120, 160 ) )
    for cx, cy in ( ( 0.62, 0.38 ), ( 0.35, 0.6 ), ( 0.55, 0.7 ) ):
        img = img + ( np.hypot( u - cx, v - cy ) < 0.012 )[..., None] * np.array( ( 255, 220, 120 ) )
    out["rh_screen_sonar"] = img
    # Gauges and trends.
    img = bg + grid[..., None] * cyan * 0.3 + frame[..., None] * cyan * 0.6
    for k in range( 4 ):
        base = 0.2 + 0.18 * k
        t = np.sin( u * 18 + k ) * 0.03 + np.sin( u * 47 + 2 * k ) * 0.012
        img = img + ( ( np.abs( v - base - t ) < 0.004 ) & ( u > 0.06 ) & ( u < 0.6 ) )[..., None] * cyan
    for k in range( 3 ):
        cx, cy = 0.78, 0.22 + 0.28 * k
        rr = np.hypot( u - cx, ( v - cy ) * 1.6 )
        arc_ = ( np.abs( rr - 0.08 ) < 0.006 ) & ( np.arctan2( v - cy, u - cx ) < 0.2 )
        img = img + arc_[..., None] * np.array( ( 120, 230, 200 ) )
    out["rh_screen_data"] = img
    out = { k: np.clip( vv, 0, 255 ) for k, vv in out.items() }
    return out, np.full( ( n, n ), 0.15 ), np.full( ( n, n ), 0.5 ), 0.0


# name: ( draw, size, seed, metalness, tile units )
TEXTURES = {
    "floor": ( floor, 2048, 1, 0.0, 192.0 ),
    "wall": ( wall, 2048, 2, 0.0, 192.0 ),
    "smooth": ( smooth, 1024, 3, 0.0, 128.0 ),
    "steel": ( steel, 1024, 4, 0.15, 64.0 ),
    "gunmetal": ( gunmetal, 1024, 5, 0.85, 64.0 ),
    "brass": ( brass, 512, 6, 1.0, 32.0 ),
    "pad": ( pad, 1024, 7, 0.0, 48.0 ),
    "grate": ( grate, 512, 8, 0.7, 16.0 ),
    "lines": ( lines, 512, 9, 0.0, 32.0 ),
    "pipe": ( pipe, 1024, 10, 0.1, 96.0 ),
    "sand": ( sand, 1024, 11, 0.0, 128.0 ),
    "rock": ( rock, 2048, 12, 0.0, 160.0 ),
    "coral": ( coral, 1024, 13, 0.0, 48.0 ),
    "kelp": ( kelp, 512, 14, 0.0, 24.0 ),
    "bone": ( bone, 1024, 15, 0.0, 48.0 ),
    "tankback": ( tankback, 1024, 16, 0.0, 256.0 ),
    "plain": ( plain, 512, 17, 0.0, 64.0 ),
    "emblem": ( emblem, 2048, 18, 0.0, 192.0 ),
    "emblem_ray": ( emblem_ray, 2048, 19, 0.0, 192.0 ),
    "banner": ( banner, 1024, 20, 0.0, 96.0 ),
    "screens": ( screens, 1024, 21, 0.0, 48.0 ),
    "panel": ( panel, 1024, 22, 0.0, 128.0 ),
    "doorframe": ( doorframe, 512, 23, 0.8, 32.0 ),
    "film": ( film, 2048, 24, 0.0, FILM_W ),
    "plantleaf": ( plantleaf, 512, 25, 0.0, 24.0 ),
}

DECALS = { "rh_emblem", "rh_emblem_ray", "rh_banner_manta", "rh_banner_jelly", "rh_screen_map", "rh_screen_sonar",
           "rh_screen_data" }
# Self-lit paints: ( brightness ). Their colour is the light they give.
ILLUM = { "rh_film": 0.12, "rh_frosted_lit": 0.4, "rh_led_warm": 6.0, "rh_led_cool": 5.0, "rh_screen_map": 2.2, "rh_screen_sonar": 2.2, "rh_screen_data": 0.85 }
# Metalness per paint where it differs from its texture's.
METALNESS = { "rh_laminate": 0.0, "rh_rubber": 0.0, "rh_black": 0.0, "rh_soil": 0.0, "rh_steel_blue": 0.15,
              "rh_stainless": 0.85, "rh_anodised": 0.3 }
ALPHA_TESTED = { "rh_kelp", "rh_film" }
# Glass on shaders/glass.shader: ( tint, absorption ). The tank glass is its own shader (write_tank_glass).
GLASS = { "rh_glass": ( ( 0.92, 0.96, 0.98 ), 0.15 ), "rh_glass_office": ( ( 0.85, 0.92, 0.96 ), 0.35 ) }


def paints():
    """ paint -> ( texture, tile units ) for every paint the textures draw (without running them). """
    known = {
        "floor": [ "rh_floor" ], "wall": [ "rh_wall", "rh_wall_dark" ], "smooth": [ "rh_smooth", "rh_block" ],
        "steel": [ "rh_steel", "rh_steel_blue" ], "gunmetal": [ "rh_gunmetal" ], "brass": [ "rh_brass", "rh_bronze" ],
        "pad": [ "rh_pad", "rh_pad_dark" ], "grate": [ "rh_grate" ], "lines": [ "rh_hazard", "rh_line" ],
        "pipe": [ "rh_pipe", "rh_pipe_dark" ], "sand": [ "rh_sand" ], "rock": [ "rh_rock" ],
        "coral": [ "rh_coral_pink", "rh_coral_orange", "rh_coral_yellow", "rh_coral_purple", "rh_coral_green", "rh_coral_white" ],
        "kelp": [ "rh_kelp" ], "bone": [ "rh_bone" ], "tankback": [ "rh_tankback" ],
        "plain": [ "rh_laminate", "rh_rubber", "rh_ceiling", "rh_led_warm", "rh_led_cool", "rh_black", "rh_frosted_lit",
                   "rh_soil" ],
        "emblem": [ "rh_emblem" ], "emblem_ray": [ "rh_emblem_ray" ], "banner": [ "rh_banner_manta", "rh_banner_jelly" ],
        "screens": [ "rh_screen_map", "rh_screen_sonar", "rh_screen_data" ],
        "panel": [ "rh_panel", "rh_panel_b", "rh_portal" ], "doorframe": [ "rh_anodised", "rh_stainless" ],
        "film": [ "rh_film" ], "plantleaf": [ "rh_leaf" ],
    }
    out = { p: ( tex, TEXTURES[tex][4] ) for tex, ps in known.items() for p in ps }
    for g in GLASS:
        out[g] = ( "glass", 64.0 )
    out["rh_tank_glass"] = ( "glass", 64.0 )
    return out


def material_path( paint_name ):
    return f"{RESOURCE_DIR}/{paint_name}.vmat"


def save_grey( path, a ):
    Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save( path, optimize=True )


def save_rgb( path, a ):
    Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( path, optimize=True )


def vmat( paint_name, texture, metalness, extra ):
    colour_file = AUTHORED_COLOR.get( paint_name, f"{paint_name}_color.png" )
    lines_ = [ "// Tools/reefhall_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if paint_name in ALPHA_TESTED:
        lines_ += [ '    F_ALPHA_TEST "1"', '    F_RENDER_BACKFACES "1"', f'    TextureTranslucency "{RESOURCE_DIR}/{texture}_trans.png"',
                    '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"' ]
    if paint_name in ILLUM:
        lines_ += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"',
                    f'    g_flSelfIllumBrightness "{ILLUM[paint_name]:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                    '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines_ += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{METALNESS.get( paint_name, metalness ):.2f}"',
                f'    TextureColor "{RESOURCE_DIR}/{colour_file}"',
                f'    TextureNormal "{RESOURCE_DIR}/{texture}_normal.png"',
                f'    TextureRoughness "{RESOURCE_DIR}/{texture}_rough.png"',
                f'    TextureAmbientOcclusion "{DEFAULT_AO}"', '    g_vColorTint "[1.0 1.0 1.0 1.0]"',
                '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines_ ) + "\n"


def glass_vmat( paint_name, tint, absorption ):
    r, g, b = tint
    return ( '// Tools/reefhall_materials.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/glass.shader"\n'
             '    F_GLASS_QUALITY "2"\n'
             '    g_bFogEnabled "1"\n'
             '    g_flBlurAmount "0.02"\n'
             '    g_flRefractionStrength "1.006"\n'
             f'    AlbedoAbsorption "{absorption:.2f}"\n'
             '    g_flTintColor "[1.000000 1.000000 1.000000 0.000000]"\n'
             f'    TextureColor "[{r:.6f} {g:.6f} {b:.6f} 0.000000]"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             '    TextureRoughness "[0.040000 0.040000 0.040000 0.000000]"\n'
             '    TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"\n'
             '    TextureAmbientOcclusion "[1.000000 1.000000 1.000000 0.000000]"\n'
             '    TextureBlendMask "materials/default/default_blend.tga"\n'
             '    TextureTintMask "materials/default/default.tga"\n'
             '    TextureTranslucency "materials/default/default_trans.tga"\n'
             "}\n" )


def tank_glass_vmat( surface_z=400.0, deep_range=320.0, caustics=1.2, shafts=0.6, scatter=( 0.06, 0.38, 0.56 ),
                     deep=( 0.008, 0.07, 0.15 ), max_water=2000.0 ):
    """ The tank glass: shaders/hc1_tank_glass.shader, whose parameters are the water's (see the shader). Each tank has
    its own copy (reefhall_map.py writes rh_tank_glass_<tank>.vmat), since the light falls off from its own surface
    (surface_z, a world height). """
    def v3( c ):
        return f"[{c[0]:.6f} {c[1]:.6f} {c[2]:.6f} 0.000000]"
    lines_ = [ "// Tools/reefhall_materials.py", '"Layer0"', "{", '    shader "shaders/hc1_tank_glass.shader"',
               '    g_vWaterAbsorb "[0.006000 0.001200 0.000600 0.000000]"', '    g_flTurbidity "0.0006"',
               f'    g_vWaterScatter "{v3( scatter )}"', f'    g_vWaterDeep "{v3( deep )}"',
               f'    g_flSurfaceZ "{surface_z:.1f}"', f'    g_flDeepRange "{deep_range:.1f}"',
               f'    g_flMaxWater "{max_water:.1f}"',
               f'    g_flCaustics "{caustics:.2f}"', '    g_flCausticScale "48.0"', f'    g_flShafts "{shafts:.2f}"',
               '    g_flRefraction "0.0025"', '    g_flGlassRoughness "0.04"',
               '    g_vGlassEdge "[0.700000 0.860000 0.820000 0.000000]"', "}" ]
    return "\n".join( lines_ ) + "\n"


def write_texture( name, out_dir ):
    draw, size, seed, metalness, units = TEXTURES[name]
    rng = np.random.default_rng( seed )
    result = draw( rng, size )
    colours, rough, height, strength = result[:4]
    extra = result[4] if len( result ) > 4 else {}
    height = np.asarray( height, float ) * np.ones( ( size, size ) )
    normal = gl_normals( height, strength * size / 1024.0 )
    out_dir.mkdir( parents=True, exist_ok=True )
    save_rgb( out_dir / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( out_dir / f"{name}_rough.png", rough )
    if "trans" in extra:
        save_grey( out_dir / f"{name}_trans.png", extra["trans"] )
    for paint_name, colour in colours.items():
        save_rgb( out_dir / f"{paint_name}_color.png", colour )
        ( out_dir / f"{paint_name}.vmat" ).write_text( vmat( paint_name, name, metalness, extra ), encoding="utf-8", newline="\n" )
    print( f"wrote {name}: {', '.join( colours )} ({units:g} units a tile, {size / units:.1f} px an inch)" )
    return colours, normal


def write_glass( out_dir ):
    out_dir.mkdir( parents=True, exist_ok=True )
    for paint_name, ( tint, absorption ) in GLASS.items():
        ( out_dir / f"{paint_name}.vmat" ).write_text( glass_vmat( paint_name, tint, absorption ), encoding="utf-8", newline="\n" )
    ( out_dir / "rh_tank_glass.vmat" ).write_text( tank_glass_vmat(), encoding="utf-8", newline="\n" )
    print( f"wrote glass: {', '.join( list( GLASS ) + [ 'rh_tank_glass' ] )}" )


def lit( colour, normal ):
    light = np.array( ( -0.45, 0.55, 0.7 ) )
    light /= np.linalg.norm( light )
    ndl = np.clip( np.sum( normal * light, -1 ), 0.0, 1.0 )
    return np.clip( colour * ( 0.35 + 0.9 * ndl )[..., None], 0, 255 )


def write_sheet( results, path ):
    tiles = []
    for name, ( colours, normal ) in results.items():
        for paint_name, colour in colours.items():
            img = Image.fromarray( lit( colour, normal ).astype( np.uint8 ) ).resize( ( 384, 384 ), Image.LANCZOS )
            ImageDraw.Draw( img ).text( ( 6, 6 ), paint_name, fill=( 255, 255, 255 ) )
            tiles.append( img )
    cols = 6
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( 384 * cols, 384 * rows ), ( 16, 16, 16 ) )
    for k, t in enumerate( tiles ):
        sheet.paste( t, ( 384 * ( k % cols ), 384 * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"textures to draw (default all: {', '.join( TEXTURES )})" )
    parser.add_argument( "--out", help="write somewhere else (for trying things out)" )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    args = parser.parse_args()
    out_dir = Path( args.out ) if args.out else OUT_DIR
    names = args.names or list( TEXTURES )
    results = { name: write_texture( name, out_dir ) for name in names }
    write_glass( out_dir )
    if args.sheet:
        write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
