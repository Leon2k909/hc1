"""
Veridant's materials: a Mediterranean cliffside resort at sunset after rain, drawn with numpy into
Assets/materials/veridant/ (the picture the map is built after, 2026-10-15).

    python Tools/veridant_materials.py [names ...] [--out <dir>] [--sheet <jpg>] [--scale 0.25]

Drawn at their real size with Tools/boxyard_materials.py's and Tools/riverdale_materials.py's helpers. Veridant
Resort, its three-wave mark and the banner's SECURE / EXPLORE / CONTROL are the picture's made-up names. Run this
before Tools/veridant_map.py. It writes:
    vr_stone        pitted grey travertine in 48 x 24 in panels, running bond, vein cut (the buildings, the pylon)
    vr_stone_dark   the same, darker and wetter: plinths, copings, the pool's kerb
    vr_stone_light  honed pale limestone: stair treads, sills, bench tops
    vr_concrete     fair-faced concrete: soffits, slabs, inside walls
    vr_paving       the courtyard's grey granite slabs after rain: 48 x 32 in, wet, standing puddles (384 in tile)
    vr_floor        polished limestone tiles inside
    vr_timber, vr_timber_dark   oiled teak boards and slats, and the pergola's dark stained beams
    vr_steel        black powder-coated steel: railings, frames, the pergola's steel
    vr_case_black, vr_case_olive   moulded military hard cases
    vr_tarp         a dark canvas tarp
    vr_bark, vr_palm_bark   an olive's fissured bark, a date palm's trunk
    vr_rock         a pale limestone boulder; vr_cliff the headland's cliffs (backdrop, 3072 in tile)
    vr_render       the village's and the hotel's warm stucco
    vr_grate        a linear drain's steel grate
    vr_hedge, vr_gravel, vr_lawn   the garden's box hedges, gravel paths and grass
    vr_foliage      leaves and fronds, alpha tested, from one atlas (FOLIAGE): olive, ivy, stone pine, palm, shrubs
    vr_print        printed things, from one atlas (PRINTS): the banner, the flag, the lounge's paintings, signs
    vr_letters_dark, vr_letters_light   cut lettering and the mark, alpha tested (LETTERS)
    vr_sea, vr_pool the sea and the reflecting pool on Lowtide's water shader
    vr_glass, vr_glass_clear   glazing and the glass balustrades
and flat paints (PAINTED), the LED strips and lamps among them self-lit.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import boxyard_materials as BM  # noqa: E402
import riverdale_materials as RM  # noqa: E402

T = BM.T
lin, mix, smoothstep = BM.lin, BM.mix, BM.smoothstep

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/veridant"
RESOURCE_DIR = "materials/veridant"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT = ROOT / "Assets/fonts/Dinish-Regular.ttf"
FONT_BOLD = ROOT / "Assets/fonts/Dinish-Bold.ttf"

SCALE = 1.0

# Tile sizes (inches) for the map's UVs.
TILES = { "vr_stone": 192.0, "vr_stone_dark": 192.0, "vr_stone_light": 96.0, "vr_concrete": 192.0, "vr_paving": 384.0,
          "vr_floor": 192.0, "vr_timber": 48.0, "vr_timber_dark": 48.0, "vr_steel": 48.0, "vr_case_black": 48.0,
          "vr_case_olive": 48.0, "vr_tarp": 64.0, "vr_bark": 48.0, "vr_palm_bark": 48.0, "vr_rock": 128.0,
          "vr_cliff": 3072.0, "vr_render": 192.0, "vr_grate": 24.0, "vr_hedge": 64.0, "vr_gravel": 96.0,
          "vr_lawn": 128.0, "vr_palm_mulch": 48.0 }


def px( n ):
    return max( 16, int( round( n * SCALE ) ) )


def field( rng, n, tile ):
    return RM.field( rng, n, tile )


def aniso( rng, n, ppi, stretch, beta, longest, shortest=None ):
    """ Noise whose features are stretch[0] times longer across (x) and stretch[1] times longer up (z) than its own
    scale: bedding, grain. (Telling the noise there are more pixels to the inch one way draws its features longer that
    way.) """
    return BM.noise( rng, ( n, n ), ( ppi * stretch[0], ppi * stretch[1] ), beta, longest, shortest )


# ---------------------------------------------------------------------------------------------------------------------
# Stone and concrete

def stone( seed=11, base=( 152, 149, 142 ), grime=0.0, n=None, tile=None, panel=( 48.0, 24.0 ), joint=0.14, pits=1.0,
           rough=0.74 ):
    """ Vein-cut travertine panels in a running bond: each panel its own shade, bedding bands running across, the
    stone's voids (dark, stretched along the beds), fine joints, and faint streaks run down from the voids. """
    n = n or px( 2048 )
    tile = tile or TILES["vr_stone"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    pw, ph = panel
    rows, cols = int( round( tile / ph ) ), int( round( tile / pw ) )
    row = np.floor( z / ph ).astype( int )
    shift = ( row % 2 ) * pw * 0.5
    xs = ( x + shift ) % tile
    col = np.floor( xs / pw ).astype( int )
    tone = rng.normal( 0, 0.05, ( rows, cols ) ).astype( np.float32 )
    warm = rng.normal( 0, 0.025, ( rows, cols ) ).astype( np.float32 )
    t, w = tone[row % rows, col % cols], warm[row % rows, col % cols]
    beds = aniso( rng, n, ppi, ( 7.0, 1.0 ), 2.2, 40, 0.6 )
    fine = aniso( rng, n, ppi, ( 3.0, 1.0 ), 1.2, 3, 0.1 )
    colour = lin( base )[None, None, :] * ( 1.0 + t + 0.045 * beds + 0.025 * fine + 0.02 * nz( 2.4, 60, 6 ) )[..., None]
    colour *= ( 1.0 + w[..., None] * np.array( [ 0.9, 0.25, -0.9 ], np.float32 ) )
    height = 0.02 * fine + 0.01 * beds
    r = np.full( ( n, n ), rough, np.float32 ) + 0.04 * fine
    # Subtle mineral deposition follows the vein-cut bedding; the palest calcite inclusions catch grazing light.
    # Reuse the same bedding fields so these details register in colour, micro-height and roughness.
    sediment = smoothstep( 0.45, 1.95, beds + 0.35 * fine )
    calcite = smoothstep( 1.5, 2.8, -fine + 0.2 * beds )
    colour *= ( 1.0 - sediment[..., None] * np.array( [ 0.024, 0.037, 0.052 ], np.float32 ) )
    colour *= ( 1.0 + 0.035 * calcite )[..., None]
    height += 0.008 * calcite - 0.006 * sediment
    r += 0.022 * sediment - 0.016 * calcite
    # Voids: small ones everywhere, stretched along the beds; a few larger pockets, more in some beds than others.
    small = aniso( rng, n, ppi, ( 2.6, 1.0 ), 0.9, 1.2, 0.08 )
    big = aniso( rng, n, ppi, ( 3.2, 1.0 ), 1.4, 6.0, 0.3 )
    porous = smoothstep( -0.6, 1.2, beds )
    voids = np.maximum( smoothstep( 2.55 - 0.35 * porous * pits, 2.95 - 0.35 * porous * pits, small ),
                        smoothstep( 2.9 - 0.2 * pits, 3.2 - 0.2 * pits, big ) ) * min( 1.0, pits )
    # A faint darker rim round open pores is characteristic of cut travertine, especially after rain.
    pore_rims = ndimage.gaussian_filter( voids, ( 1.5, 3.5 ), mode="wrap" )
    colour *= ( 1.0 - 0.075 * pore_rims )[..., None]
    colour = mix( colour, colour * 0.28, voids[..., None] * 0.92 )
    height -= 0.22 * voids
    r = mix( r, 0.95, voids )
    # Joints.
    dx = np.minimum( xs % pw, pw - xs % pw )
    dz = np.minimum( z % ph, ph - z % ph )
    j = smoothstep( joint, joint * 0.35, np.minimum( dx, dz ) )
    colour = mix( colour, colour * 0.45, j[..., None] * 0.85 )
    height -= 0.12 * j
    # Faint streaks run down from the voids and the joints' crossings.
    src = ndimage.gaussian_filter( voids * ( rng.random( voids.shape ) < 0.05 ), ( 0.6, 1.0 ), mode="wrap" ) * 6
    runs = np.clip( RM.runs_down( src.astype( np.float32 ), ppi, 18.0 ) * 3.0, 0, 1 )
    colour = mix( colour, colour * 0.8, runs[..., None] * 0.5 )
    if grime:
        dirt = smoothstep( 0.0, 2.2, nz( 2.4, 50, 4 ) ) * grime
        colour = mix( colour, colour * lin( ( 120, 112, 100 ) ) * 3.0, dirt[..., None] * 0.4 )
        colour *= 1.0 - 0.18 * grime
        r = np.clip( r - 0.12 * grime, 0.3, 1.0 )
    return colour, np.clip( r, 0.2, 1.0 ), height, ppi


def concrete( seed=14, base=( 166, 164, 158 ), n=None ):
    c, r, h, ppi = RM.concrete_wall( seed=seed, base=base, grime=0.0, n=n or px( 2048 ) )
    # Preserve the existing formwork seams, ties and bug holes, but give the poured face a restrained
    # fine aggregate / float texture rather than a uniformly smooth surface at close range.
    rng = np.random.default_rng( seed + 401 )
    finish = BM.noise( rng, h.shape, ( ppi, ppi ), 1.65, 16.0, 0.25 )
    exposed = smoothstep( 1.45, 2.75, finish )
    c *= ( 1.0 + 0.018 * finish )[..., None]
    c = mix( c, lin( ( 184, 181, 174 ) ), exposed[..., None] * 0.045 )
    h += 0.009 * finish
    r = np.clip( r + 0.018 * finish, 0.4, 1.0 )
    return c, r, h, ppi


def paving( seed=31, n=None, wet=1.0 ):
    """ Flamed grey granite slabs, 48 x 32 in in a running bond, after rain: every slab its own shade and a hair out of
    level, the stone's grain and dark mica, grouted joints, the whole darkened wet and glossy, with standing water
    where the slabs dip. """
    n = n or px( 4096 )
    tile = TILES["vr_paving"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    sw, sh = 48.0, 32.0
    rows, cols = int( tile / sh ), int( tile / sw )
    row = np.floor( z / sh ).astype( int )
    shift = ( row % 2 ) * sw * 0.5
    xs = ( x + shift ) % tile
    col = np.floor( xs / sw ).astype( int )
    tone = rng.normal( 0, 0.075, ( rows, cols ) ).astype( np.float32 )
    hue = rng.normal( 0, 0.02, ( rows, cols ) ).astype( np.float32 )
    tilt = rng.normal( 0, 0.008, ( rows, cols, 2 ) ).astype( np.float32 )
    rr, cc = row % rows, col % cols
    grain = nz( 0.4, 0.5, 0.05 )
    mica = smoothstep( 2.1, 2.7, nz( 0.2, 0.25, 0.04 ) )
    mineral = nz( 1.4, 1.8, 0.14 )
    feldspar = smoothstep( 1.45, 2.8, mineral )
    dark_grains = smoothstep( 1.5, 2.8, -mineral )
    colour = lin( ( 138, 138, 136 ) )[None, None, :] * ( 1.0 + tone[rr, cc] + 0.07 * grain + 0.03 * nz( 2.2, 30, 2 ) )[..., None]
    colour *= ( 1.0 + hue[rr, cc][..., None] * np.array( [ 0.8, 0.1, -0.8 ], np.float32 ) )
    colour = mix( colour, colour * 0.35, mica[..., None] * 0.8 )
    # Scattered pale feldspar and dark minerals break up broad uniform granite patches without visible tiling.
    colour = mix( colour, lin( ( 164, 158, 150 ) ), feldspar[..., None] * 0.13 )
    colour *= ( 1.0 - 0.045 * dark_grains )[..., None]
    lx, lz = xs % sw - sw / 2, z % sh - sh / 2
    height = 0.02 * grain + 0.009 * mineral + tilt[rr, cc, 0] * lx + tilt[rr, cc, 1] * lz
    dx, dz = np.minimum( xs % sw, sw - xs % sw ), np.minimum( z % sh, sh - z % sh )
    edge = np.minimum( dx, dz )
    j = smoothstep( 0.2, 0.08, edge )
    arris = smoothstep( 0.7, 0.2, edge ) * ( 1 - j )
    colour = mix( colour, lin( ( 34, 34, 34 ) ), j[..., None] * 0.9 )
    height -= 0.25 * j + 0.04 * arris
    r = 0.62 + 0.05 * grain + 0.015 * mineral
    # Wet: stone darkens and shines; a little drier on some slabs' crowns.
    damp = np.clip( wet * ( 0.75 + 0.25 * smoothstep( -1.0, 1.0, nz( 2.4, 120, 10 ) ) ), 0, 1 )
    colour = colour * ( 1.0 - 0.26 * damp )[..., None]
    r = mix( r, 0.24, damp )
    r = r + 0.05 * arris
    # Puddles where the slabs dip.
    if wet:
        # Smooth-edged pools in the slabs' dips: water over stone darkens it a little; what makes them read as puddles
        # is their mirror finish, not a dark stain.
        dip = nz( 2.4, 160, 14 ) + 0.18 * nz( 1.8, 30, 3 )
        # Water stays on slab faces: don't paint a reflective slick over the recessed, rough grout.
        puddle = smoothstep( 1.2, 1.45, dip ) * smoothstep( 0.35, 2.2, edge )
        colour = mix( colour, colour * 0.78 + lin( ( 4, 5, 6 ) ), puddle[..., None] * 0.9 )
        r = mix( r, 0.03, puddle )
        height = mix( height, float( np.mean( height ) ), puddle )
    return colour, np.clip( r, 0.02, 1.0 ), height, ppi


def floor_tiles( seed=33, n=None ):
    """ Polished limestone tiles, 24 in square: pale, honey veined, glossy, hairline joints. """
    n = n or px( 2048 )
    tile = TILES["vr_floor"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    s = 24.0
    k = int( tile / s )
    i, j_ = ( np.floor( x / s ).astype( int ) ) % k, ( np.floor( z / s ).astype( int ) ) % k
    tone = rng.normal( 0, 0.03, ( k, k ) ).astype( np.float32 )
    veins = aniso( rng, n, ppi, ( 2.0, 1.0 ), 1.8, 10, 0.2 )
    colour = lin( ( 206, 196, 178 ) )[None, None, :] * ( 1.0 + tone[j_, i] + 0.03 * veins + 0.02 * nz( 0.6, 0.6, 0.1 ) )[..., None]
    vein = smoothstep( 2.0, 2.6, np.abs( veins ) * 1.6 )
    colour = mix( colour, lin( ( 176, 156, 124 ) ), vein[..., None] * 0.5 )
    d = np.minimum( np.minimum( x % s, s - x % s ), np.minimum( z % s, s - z % s ) )
    jt = smoothstep( 0.08, 0.03, d )
    colour = mix( colour, lin( ( 150, 140, 124 ) ), jt[..., None] * 0.7 )
    r = 0.16 + 0.04 * nz( 2.0, 20, 2 )
    height = 0.004 * veins - 0.05 * jt
    return colour, np.clip( r, 0.05, 1 ), height, ppi


# ---------------------------------------------------------------------------------------------------------------------
# Timber, steel, cases, fabric

def timber( seed=41, colour=( 126, 80, 46 ), n=None, board=6.0, rough=0.48 ):
    """ Oiled hardwood boards with the grain up the picture (map_kit's grain paints map it along each board). """
    n = n or px( 1024 )
    tile = TILES["vr_timber"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    k = int( round( tile / board ) )
    b = ( np.floor( x / board ).astype( int ) ) % k
    tone = rng.normal( 0, 0.09, k ).astype( np.float32 )
    grain = aniso( rng, n, ppi, ( 1.0, 14.0 ), 1.6, 3, 0.05 )
    figure = aniso( rng, n, ppi, ( 1.0, 6.0 ), 2.4, 12, 0.5 )
    c = lin( colour )[None, None, :] * ( 1.0 + tone[b] + 0.08 * grain + 0.05 * figure )[..., None]
    dark = smoothstep( 1.4, 2.2, grain )
    c = mix( c, c * 0.6, dark[..., None] * 0.6 )
    gap = smoothstep( 0.12, 0.04, np.minimum( x % board, board - x % board ) )
    c = mix( c, lin( ( 20, 14, 10 ) ), gap[..., None] * 0.9 )
    r = rough + 0.06 * grain
    h = 0.03 * grain - 0.2 * gap
    return c, np.clip( r, 0.2, 1 ), h, ppi


def moulded( seed, colour, rough=0.55, chips=0.06 ):
    """ Moulded polypropylene: a fine pebble finish, scuffs and dust. """
    c, r, h, ppi = RM.painted( seed, colour, chips=chips, tile=48.0, rough=rough, grime=0.25, n=px( 1024 ), bare=tuple( int( v * 1.6 ) for v in colour ) )
    rng = np.random.default_rng( seed + 7 )
    n = c.shape[0]
    pebble = BM.noise( rng, ( n, n ), ( n / 48.0, n / 48.0 ), 0.6, 0.15, 0.03 )
    h = h + 0.012 * pebble
    r = np.clip( r + 0.04 * pebble, 0.2, 1.0 )
    return c, r, h, ppi


def tarp( seed=51, n=None ):
    n = n or px( 1024 )
    tile = TILES["vr_tarp"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    weave = np.sin( x * 2 * math.pi / 0.08 ) * np.sin( z * 2 * math.pi / 0.08 )
    folds = nz( 2.6, 30, 3 )
    c = lin( ( 92, 94, 87 ) )[None, None, :] * ( 1.0 + 0.04 * weave + 0.12 * folds + 0.03 * nz( 1.0, 2, 0.2 ) )[..., None]
    stain = smoothstep( 1.0, 2.4, nz( 2.2, 20, 2 ) )
    c = mix( c, c * 0.7, stain[..., None] * 0.6 )
    # Wet from the rain: glossy, more so where it's soaked, so its folds catch the sky as the picture's do.
    r = 0.34 + 0.06 * folds - 0.08 * stain
    h = 0.01 * weave + 0.25 * folds
    return c, np.clip( r, 0.4, 1 ), h, ppi


def bark( seed=61, n=None ):
    """ An old olive's bark: grey, in long twisting ridges with dark fissures between, a little lichen. """
    n = n or px( 1024 )
    tile = TILES["vr_bark"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    ridges = aniso( rng, n, ppi, ( 1.0, 5.0 ), 2.0, 6, 0.3 )
    fiss = smoothstep( -0.4, -1.4, ridges )
    c = lin( ( 104, 98, 88 ) )[None, None, :] * ( 1.0 + 0.1 * ridges + 0.05 * nz( 0.8, 0.8, 0.1 ) )[..., None]
    c = mix( c, lin( ( 38, 32, 28 ) ), fiss[..., None] * 0.85 )
    lichen = smoothstep( 1.6, 2.4, nz( 1.6, 4, 0.3 ) ) * ( 1 - fiss )
    c = mix( c, lin( ( 150, 156, 132 ) ), lichen[..., None] * 0.5 )
    r = 0.85 + 0.05 * ridges
    h = 0.4 * ridges - 0.3 * fiss
    return c, np.clip( r, 0.5, 1 ), h, ppi


def palm_bark( seed=63, n=None ):
    """ Weathered fibrous date-palm bark with broken leaf scars, rather than a drawn diamond grid. """
    n = n or px( 1024 )
    tile = TILES["vr_palm_bark"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    broad = nz( 1.8, 15, 1.0 )
    fibre = aniso( rng, n, ppi, ( .22, 4.5 ), 1.4, 3.0, .04 )
    fine = aniso( rng, n, ppi, ( .12, 2.8 ), 1.0, .7, .025 )
    warp = nz( 1.5, 6.0, .6 )
    rows = ( z + .50 * warp ) * 13 / tile
    rid = np.floor( rows )
    # Short staggered, curved scars, broken up by the fibrous surface.
    sx = np.mod( x + rid * ( 40 / 13 ) + .7 * warp, 8.0 ) / 8.0
    scar_line = .20 + .35 * np.abs( sx * 2 - 1 )
    scar = smoothstep( .09, .015, np.abs( np.mod( rows, 1 ) - scar_line ) )
    scar *= smoothstep( .05, .2, sx ) * smoothstep( .98, .80, sx ) * smoothstep( -1.2, .4, fibre )
    c = lin( ( 113, 96, 73 ) )[None, None, :] * ( 1 + .12 * broad + .12 * fibre + .055 * fine )[..., None]
    c = mix( c, lin( ( 65, 53, 39 ) ), scar[..., None] * .38 )
    r = .9 + .025 * fibre + .015 * fine
    h = .045 * fibre + .012 * fine + .025 * broad - .045 * scar
    return c, np.clip( r, 0.5, 1 ), h, ppi


def rock( seed=71, n=None ):
    n = n or px( 1024 )
    tile = TILES["vr_rock"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    big, mid, grit = nz( 2.6, 60, 4 ), nz( 2.0, 10, 1 ), nz( 0.7, 0.6, 0.08 )
    c = lin( ( 134, 128, 118 ) )[None, None, :] * ( 1.0 + 0.1 * big + 0.06 * mid + 0.04 * grit )[..., None]
    cracks = smoothstep( 0.12, 0.0, np.abs( aniso( rng, n, ppi, ( 1.0, 1.0 ), 2.0, 20, 1 ) ) * 0.3 )
    c = mix( c, c * 0.4, cracks[..., None] * 0.7 )
    lichen = smoothstep( 1.4, 2.2, nz( 1.8, 6, 0.4 ) )
    c = mix( c, lin( ( 162, 160, 140 ) ), lichen[..., None] * 0.35 )
    r = 0.72 + 0.06 * mid
    h = 0.6 * big + 0.15 * mid - 0.3 * cracks
    return c, np.clip( r, 0.3, 1 ), h, ppi


def cliff( seed=73, n=None ):
    """ The headland: pale limestone in thick beds, split by joints, scrub (garrigue) clinging in the ledges and
    gullies. Drawn coarse: it's seen from a kilometre off. """
    n = n or px( 2048 )
    tile = TILES["vr_cliff"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    beds = aniso( rng, n, ppi, ( 8.0, 1.0 ), 2.0, 600, 20 )
    joints = aniso( rng, n, ppi, ( 1.0, 6.0 ), 2.0, 400, 20 )
    # Several rock strata and erosion scales remain legible through sunset fog.
    strata = np.sin( z * ( 2 * math.pi / 155.0 ) + 1.6 * nz( 1.9, 170, 10 ) )
    fractures = smoothstep( 0.21, 0.035, np.abs( joints ) )
    scree = smoothstep( 1.05, 2.1, nz( 2.3, 95, 6 ) )
    c = lin( ( 169, 157, 139 ) )[None, None, :] * ( 1.0 + 0.16 * beds + 0.07 * strata + 0.09 * nz( 2.4, 300, 10 ) )[..., None]
    c = mix( c, c * 0.47, fractures[..., None] * 0.48 )
    c = mix( c, lin( ( 186, 172, 151 ) ), scree[..., None] * 0.15 )
    ledge = smoothstep( 1.0, 1.8, beds )
    gully = smoothstep( 1.2, 2.0, np.abs( joints ) )
    scrub = np.clip( ledge * 0.8 + gully * 0.6 + smoothstep( 1.4, 2.4, nz( 2.2, 200, 10 ) ), 0, 1 )
    c = mix( c, lin( ( 56, 64, 44 ) ) * ( 1.0 + 0.2 * nz( 1.0, 20, 2 ) )[..., None], scrub[..., None] * 0.85 )
    stain = smoothstep( 0.6, 2.2, nz( 2.4, 400, 30 ) )
    c = mix( c, c * lin( ( 170, 140, 110 ) ) * 2.5, stain[..., None] * 0.3 )
    r = 0.85 + 0.05 * beds
    h = 3.0 * beds + 1.0 * joints + 0.7 * strata - 1.2 * fractures
    return c, np.clip( r, 0.5, 1 ), h, ppi


def render( seed=81, colour=( 222, 206, 182 ), n=None ):
    n = n or px( 1024 )
    tile = TILES["vr_render"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    trowel = nz( 1.8, 6, 0.4 )
    c = lin( colour )[None, None, :] * ( 1.0 + 0.04 * trowel + 0.04 * nz( 2.6, 80, 6 ) )[..., None]
    src = ( rng.random( ( n, n ) ) < 0.0003 ).astype( np.float32 )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.5 ), mode="wrap" ) * 5
    runs = np.clip( RM.runs_down( src, ppi, 30.0 ) * 3.0, 0, 1 )
    c = mix( c, c * 0.8, runs[..., None] * 0.5 )
    r = 0.86 + 0.04 * trowel
    h = 0.05 * trowel
    return c, np.clip( r, 0.5, 1 ), h, ppi


def grate( seed=91, n=None ):
    """ A linear drain's grate seen from above: slots across it every 0.8 in, the bars steel. """
    n = n or px( 512 )
    tile = TILES["vr_grate"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    pitch = tile / 30.0
    bar = smoothstep( 0.22, 0.16, np.minimum( z % pitch, pitch - z % pitch ) )
    c = mix( lin( ( 8, 8, 8 ) )[None, None, :] * np.ones( ( n, n, 1 ), np.float32 ), lin( ( 70, 70, 72 ) ) * ( 1.0 + 0.1 * nz( 2.0, 6, 0.5 ) )[..., None], bar[..., None] )
    r = mix( np.full( ( n, n ), 0.9, np.float32 ), 0.35, bar )
    h = 0.3 * bar
    return c, r, h, ppi


def hedge( seed=93, n=None ):
    n = n or px( 1024 )
    tile = TILES["vr_hedge"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    leaf = nz( 0.9, 0.6, 0.08 )
    clump = nz( 2.2, 10, 1 )
    c = lin( ( 50, 70, 40 ) )[None, None, :] * ( 1.0 + 0.25 * leaf + 0.15 * clump )[..., None]
    shade = smoothstep( -0.5, -1.8, leaf + 0.5 * clump )
    c = mix( c, lin( ( 12, 18, 10 ) ), shade[..., None] * 0.8 )
    r = 0.7 + 0.1 * leaf
    h = 0.4 * leaf + 0.6 * clump
    return c, np.clip( r, 0.3, 1 ), h, ppi


def gravel( seed=95, n=None ):
    n = n or px( 1024 )
    tile = TILES["vr_gravel"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    stones = nz( 0.5, 0.5, 0.06 )
    c = lin( ( 178, 168, 148 ) )[None, None, :] * ( 1.0 + 0.12 * stones + 0.05 * nz( 2.0, 20, 2 ) )[..., None]
    gaps = smoothstep( -0.8, -1.6, stones )
    c = mix( c, c * 0.4, gaps[..., None] * 0.7 )
    damp = smoothstep( -0.5, 1.0, nz( 2.4, 40, 4 ) )
    c = c * ( 1.0 - 0.25 * damp )[..., None]
    r = 0.8 - 0.1 * damp
    h = 0.3 * stones
    return c, np.clip( r, 0.3, 1 ), h, ppi


def lawn( seed=97, n=None ):
    n = n or px( 1024 )
    tile = TILES["vr_lawn"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    blades = aniso( rng, n, ppi, ( 1.0, 3.0 ), 0.8, 0.5, 0.04 )
    c = lin( ( 74, 92, 52 ) )[None, None, :] * ( 1.0 + 0.2 * blades + 0.1 * nz( 2.2, 30, 2 ) )[..., None]
    dry = smoothstep( 1.0, 2.2, nz( 2.4, 60, 4 ) )
    c = mix( c, lin( ( 120, 116, 70 ) ), dry[..., None] * 0.3 )
    r = 0.8 + 0.05 * blades
    h = 0.2 * blades
    return c, np.clip( r, 0.4, 1 ), h, ppi


# ---------------------------------------------------------------------------------------------------------------------
# The wave mark and lettering

def wave_mark( draw, box, fill=255, lines=3, stroke=0.085 ):
    """ Veridant's mark: three wavy lines stacked, each a wave and a half, round ended. """
    x, y, w, h = box
    s = min( w, h )
    cx, cy = x + w / 2, y + h / 2
    width = s * 0.84
    amp = s * 0.07
    gap = s * 0.2
    sw = max( 2, int( s * stroke ) )
    for k in range( lines ):
        yy = cy + ( k - ( lines - 1 ) / 2 ) * gap
        pts = []
        for t in np.linspace( 0, 1, 80 ):
            px_ = cx - width / 2 + width * t
            pts.append( ( px_, yy - amp * math.sin( t * 3.0 * math.pi + 0.3 ) ) )
        draw.line( pts, fill=fill, width=sw, joint="curve" )
        for p in ( pts[0], pts[-1] ):
            draw.ellipse( ( p[0] - sw / 2, p[1] - sw / 2, p[0] + sw / 2, p[1] + sw / 2 ), fill=fill )


def tracked( draw, box, text, fill=255, track=0.4, light=True, height=0.7, align="center" ):
    """ One line of capitals, widely spaced, fitted in box ( x, y, w, h ) at height share of the box's height. """
    x, y, w, h = box
    size = h * height / 0.72
    for _ in range( 60 ):
        f = ImageFont.truetype( str( FONT if light else FONT_BOLD ), max( 6, int( size ) ) )
        widths = [ f.getlength( ch ) for ch in text ]
        total = sum( widths ) + track * size * ( len( text ) - 1 )
        if total <= w * 0.96:
            break
        size *= 0.96
    cx = x + ( w - total ) / 2 if align == "center" else x + w * 0.02
    cap = 0.72 * size
    cy = y + ( h - cap ) / 2 - 0.26 * size
    for ch, cw in zip( text, widths ):
        draw.text( ( cx, cy ), ch, font=f, fill=fill )
        cx += cw + track * size


LETTER_ATLAS = ( 4096, 2048 )
LETTERS = {
    "veridant": ( 0, 0, 4096, 512 ), "resort": ( 0, 512, 2048, 320 ), "logo": ( 2048, 512, 1024, 1024 ),
    "reception": ( 0, 832, 2048, 256 ), "beach_club": ( 0, 1088, 2048, 256 ), "spa": ( 3072, 512, 1024, 256 ),
    "terrace": ( 3072, 768, 1024, 256 ), "lounge": ( 3072, 1024, 1024, 256 ), "secure": ( 0, 1344, 2048, 224 ),
    "explore": ( 0, 1568, 2048, 224 ), "control": ( 0, 1792, 2048, 224 ), "no_entry": ( 3072, 1280, 1024, 256 ),
    "n1": ( 2048, 1536, 512, 512 ), "n2": ( 2560, 1536, 512, 512 ), "n3": ( 3072, 1536, 512, 512 ), "n4": ( 3584, 1536, 512, 512 ),
}


def letters_atlas():
    W, H = px( LETTER_ATLAS[0] ), px( LETTER_ATLAS[1] )
    k = W / LETTER_ATLAS[0]
    img = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( img )

    def box( name ):
        x, y, w, h = LETTERS[name]
        return ( x * k, y * k, w * k, h * k )

    tracked( d, box( "veridant" ), "VERIDANT", track=0.32, height=0.62 )
    tracked( d, box( "resort" ), "RESORT", track=0.55, height=0.55 )
    wave_mark( d, box( "logo" ) )
    tracked( d, box( "reception" ), "RECEPTION", track=0.4 )
    tracked( d, box( "beach_club" ), "BEACH CLUB", track=0.4 )
    tracked( d, box( "spa" ), "SPA", track=0.5 )
    tracked( d, box( "terrace" ), "TERRACE", track=0.4 )
    tracked( d, box( "lounge" ), "LOUNGE", track=0.4 )
    tracked( d, box( "secure" ), "SECURE", track=0.35 )
    tracked( d, box( "explore" ), "EXPLORE", track=0.35 )
    tracked( d, box( "control" ), "CONTROL", track=0.35 )
    tracked( d, box( "no_entry" ), "STAFF ONLY", track=0.3 )
    for name, text in ( ( "n1", "1" ), ( "n2", "2" ), ( "n3", "3" ), ( "n4", "4" ) ):
        tracked( d, box( name ), text, track=0.0, height=0.7, light=False )
    return np.asarray( img, np.float32 ) / 255.0


# ---------------------------------------------------------------------------------------------------------------------
# Prints: the banner, the flag, paintings, signs, a room's window

PRINT_ATLAS = ( 4096, 4096 )
PRINTS = {
    "banner": ( 0, 0, 1024, 2560 ), "flag": ( 1024, 0, 1536, 1024 ), "art_1": ( 1024, 1024, 768, 1024 ),
    "art_2": ( 1792, 1024, 768, 1024 ), "art_3": ( 2560, 0, 1536, 768 ), "art_4": ( 2560, 768, 768, 768 ),
    "art_5": ( 3328, 768, 768, 1024 ), "art_6": ( 2560, 1792, 1536, 768 ), "menu": ( 0, 2560, 768, 1024 ),
    "poster": ( 768, 2560, 768, 1152 ), "room": ( 1536, 2560, 1024, 768 ), "room_2": ( 2560, 2560, 1024, 768 ),
    "plaque_reception": ( 1024, 2048, 1536, 256 ), "plaque_spa": ( 1024, 2304, 768, 256 ),
    "plaque_beach": ( 1792, 2304, 768, 256 ), "board": ( 0, 3584, 1536, 512 ), "fabric": ( 1536, 3328, 1024, 768 ),
    "room_3": ( 2560, 3328, 1024, 768 ),
}


def fabric_weave( shape, rng, base, amount=0.06 ):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    weave = np.sin( xx * 2.4 ) * np.sin( yy * 2.4 )
    noise = ndimage.gaussian_filter( rng.standard_normal( ( h, w ) ).astype( np.float32 ), 2.0 )
    noise /= noise.std() + 1e-6
    return np.asarray( base, np.float32 )[None, None, :] * ( 1.0 + amount * weave + 0.03 * noise )[..., None]


def paint_strokes( arr, rng, palette, count, size, horizontal=False ):
    """ Broad painterly strokes onto an RGB float picture. """
    h, w = arr.shape[:2]
    img = Image.fromarray( np.clip( arr, 0, 255 ).astype( np.uint8 ) )
    layer = Image.new( "RGBA", img.size, ( 0, 0, 0, 0 ) )
    d = ImageDraw.Draw( layer )
    for _ in range( count ):
        col = palette[int( rng.integers( 0, len( palette ) ) )]
        x0, y0 = rng.uniform( 0, w ), rng.uniform( 0, h )
        ang = rng.normal( 0, 0.25 ) if horizontal else rng.uniform( 0, math.pi )
        L = rng.uniform( 0.3, 1.0 ) * size
        x1, y1 = x0 + math.cos( ang ) * L, y0 + math.sin( ang ) * L
        d.line( ( x0, y0, x1, y1 ), fill=( *col, int( rng.uniform( 90, 200 ) ) ), width=int( rng.uniform( 0.08, 0.25 ) * size ) )
    img = Image.alpha_composite( img.convert( "RGBA" ), layer.filter( ImageFilter.GaussianBlur( 1.5 ) ) )
    return np.asarray( img.convert( "RGB" ), np.float32 )


def prints_atlas():
    W, H = px( PRINT_ATLAS[0] ), px( PRINT_ATLAS[1] )
    k = W / PRINT_ATLAS[0]
    canvas = np.full( ( H, W, 3 ), 40.0, np.float32 )
    rng = np.random.default_rng( 17 )

    def region( name ):
        x, y, w, h = PRINTS[name]
        return int( x * k ), int( y * k ), max( 4, int( w * k ) ), max( 4, int( h * k ) )

    def put( name, arr ):
        x, y, w, h = region( name )
        canvas[y:y + h, x:x + w] = arr[:h, :w]

    def text_layer( w, h, draw_fn ):
        img = Image.new( "L", ( w, h ), 0 )
        draw_fn( ImageDraw.Draw( img ), w, h )
        return np.asarray( img, np.float32 ) / 255.0

    # The banner: charcoal fabric, the three words widely spaced, the mark under them.
    x, y, w, h = region( "banner" )
    arr = fabric_weave( ( h, w ), rng, ( 44, 46, 50 ) )
    sag = 1.0 - 0.12 * np.abs( np.linspace( -1, 1, w ) )[None, :] ** 2
    arr *= sag[..., None]

    def banner_text( d, w_, h_ ):
        for i, word in enumerate( ( "SECURE", "EXPLORE", "CONTROL" ) ):
            tracked( d, ( 0, h_ * ( 0.36 + i * 0.068 ), w_, h_ * 0.06 ), word, track=0.3, height=0.7 )
        wave_mark( d, ( w_ * 0.36, h_ * 0.6, w_ * 0.28, w_ * 0.28 ), stroke=0.07 )

    a = text_layer( w, h, banner_text )
    arr = mix( arr, np.array( ( 226, 226, 222 ), np.float32 ), a[..., None] * 0.92 )
    put( "banner", arr )
    # The flag: black, the mark in white.
    x, y, w, h = region( "flag" )
    arr = fabric_weave( ( h, w ), rng, ( 22, 22, 24 ), 0.08 )
    a = text_layer( w, h, lambda d, w_, h_: wave_mark( d, ( w_ * 0.3, h_ * 0.15, w_ * 0.4, h_ * 0.7 ), stroke=0.075 ) )
    put( "flag", mix( arr, np.array( ( 232, 232, 228 ), np.float32 ), a[..., None] * 0.95 ) )
    # Paintings: colour fields and broad strokes in the coast's colours.
    palettes = [
        [ ( 208, 150, 82 ), ( 186, 94, 52 ), ( 236, 214, 170 ), ( 64, 80, 104 ) ],
        [ ( 40, 70, 110 ), ( 90, 140, 170 ), ( 220, 210, 190 ), ( 180, 120, 70 ) ],
        [ ( 120, 40, 40 ), ( 210, 170, 120 ), ( 40, 40, 44 ), ( 240, 230, 210 ) ],
        [ ( 70, 90, 60 ), ( 160, 170, 120 ), ( 220, 200, 150 ), ( 60, 50, 40 ) ],
        [ ( 230, 200, 160 ), ( 200, 120, 90 ), ( 120, 140, 170 ), ( 250, 240, 225 ) ],
        [ ( 30, 50, 80 ), ( 240, 180, 90 ), ( 210, 90, 60 ), ( 20, 20, 24 ) ],
    ]
    for i, name in enumerate( ( "art_1", "art_2", "art_3", "art_4", "art_5", "art_6" ) ):
        x, y, w, h = region( name )
        pal = palettes[i]
        base = np.array( pal[2], np.float32 )
        yy = np.linspace( 0, 1, h )[:, None, None]
        arr = base[None, None, :] * ( 0.9 + 0.1 * yy ) * np.ones( ( h, w, 1 ), np.float32 )
        if name == "art_3":
            # A seascape: sky, a headland, the sea, a low sun.
            sky = np.array( pal[0], np.float32 ) * ( 1 - yy ) + np.array( pal[2], np.float32 ) * yy
            arr = sky * np.ones( ( h, w, 1 ), np.float32 )
            horizon = int( h * 0.6 )
            arr[horizon:] = np.array( pal[3], np.float32 ) * ( 0.8 + 0.3 * np.linspace( 0, 1, h - horizon )[:, None, None] )
            hill = ( h * ( 0.6 - 0.25 * np.exp( -( ( np.arange( w ) / w - 0.25 ) / 0.18 ) ** 2 ) ) ).astype( int )
            for c in range( w ):
                arr[hill[c]:horizon, c] = np.array( ( 60, 56, 60 ), np.float32 )
            yy_, xx_ = np.mgrid[0:h, 0:w]
            sun = np.exp( -( ( xx_ - w * 0.72 ) ** 2 + ( yy_ - h * 0.55 ) ** 2 ) / ( 2 * ( h * 0.05 ) ** 2 ) )
            arr = arr * ( 1 - sun[..., None] ) + np.array( ( 255, 220, 150 ), np.float32 ) * sun[..., None]
        arr = paint_strokes( arr, rng, pal, 60 if name != "art_3" else 30, min( w, h ) * 0.5, horizontal=name in ( "art_3", "art_6" ) )
        # A thin dark frame painted round it (the frame itself is geometry).
        arr[:max( 2, int( 6 * k ) )] *= 0.5
        arr[-max( 2, int( 6 * k ) ):] *= 0.5
        arr[:, :max( 2, int( 6 * k ) )] *= 0.5
        arr[:, -max( 2, int( 6 * k ) ):] *= 0.5
        put( name, arr )
    # A menu board: dark slate, lines of chalk text.
    x, y, w, h = region( "menu" )
    arr = np.full( ( h, w, 3 ), ( 34, 36, 36 ), np.float32 )

    def menu( d, w_, h_ ):
        tracked( d, ( 0, h_ * 0.04, w_, h_ * 0.08 ), "VERIDANT", track=0.3 )
        wave_mark( d, ( w_ * 0.42, h_ * 0.13, w_ * 0.16, w_ * 0.16 ), stroke=0.08 )
        for j in range( 12 ):
            yy_ = h_ * ( 0.3 + 0.055 * j )
            ww = w_ * ( 0.5 + 0.3 * ( ( j * 37 ) % 7 ) / 7 )
            d.rectangle( ( w_ * 0.1, yy_, w_ * 0.1 + ww, yy_ + h_ * 0.012 ), fill=200 )
            d.rectangle( ( w_ * 0.82, yy_, w_ * 0.9, yy_ + h_ * 0.012 ), fill=200 )

    a = text_layer( w, h, menu )
    put( "menu", mix( arr, np.array( ( 220, 214, 200 ), np.float32 ), a[..., None] * 0.85 ) )
    # A poster: the mark over a sunset.
    x, y, w, h = region( "poster" )
    yy = np.linspace( 0, 1, h )[:, None, None]
    arr = ( np.array( ( 236, 150, 90 ), np.float32 ) * ( 1 - yy ) + np.array( ( 40, 46, 70 ), np.float32 ) * yy ) * np.ones( ( h, w, 1 ), np.float32 )

    def poster( d, w_, h_ ):
        wave_mark( d, ( w_ * 0.3, h_ * 0.2, w_ * 0.4, w_ * 0.4 ), stroke=0.07 )
        tracked( d, ( 0, h_ * 0.62, w_, h_ * 0.08 ), "VERIDANT", track=0.3 )
        tracked( d, ( 0, h_ * 0.71, w_, h_ * 0.05 ), "RESORT", track=0.6 )

    a = text_layer( w, h, poster )
    put( "poster", mix( arr, np.array( ( 245, 240, 230 ), np.float32 ), a[..., None] * 0.95 ) )
    # A lit room seen through a window: warm walls, a lamp, a picture, curtains at the sides, a bed's end.
    for name, wall, curtain in ( ( "room", ( 214, 176, 132 ), ( 196, 186, 168 ) ), ( "room_2", ( 186, 150, 118 ), ( 120, 100, 86 ) ),
                                 ( "room_3", ( 224, 196, 160 ), ( 210, 204, 190 ) ) ):
        x, y, w, h = region( name )
        yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
        arr = np.array( wall, np.float32 )[None, None, :] * ( 0.55 + 0.6 * np.exp( -( ( xx - w * 0.62 ) ** 2 + ( yy - h * 0.38 ) ** 2 ) / ( 2 * ( w * 0.28 ) ** 2 ) ) )[..., None]
        arr[int( h * 0.72 ):] = np.array( ( 120, 92, 70 ), np.float32 ) * 0.8
        img = Image.fromarray( np.clip( arr, 0, 255 ).astype( np.uint8 ) )
        d = ImageDraw.Draw( img )
        d.rectangle( ( w * 0.36, h * 0.2, w * 0.52, h * 0.42 ), fill=( 70, 80, 96 ) )
        d.rectangle( ( w * 0.6, h * 0.5, w * 0.95, h * 0.85 ), fill=( 236, 232, 222 ) )
        d.rectangle( ( w * 0.7, h * 0.24, w * 0.76, h * 0.5 ), fill=( 60, 50, 40 ) )
        d.ellipse( ( w * 0.66, h * 0.16, w * 0.8, h * 0.3 ), fill=( 255, 236, 200 ) )
        d.rectangle( ( 0, 0, w * 0.14, h ), fill=curtain )
        d.rectangle( ( w * 0.86, 0, w, h ), fill=curtain )
        put( name, np.asarray( img, np.float32 ) )
    # Plaques: dark bronze with the words cut in.
    for name, word in ( ( "plaque_reception", "RECEPTION" ), ( "plaque_spa", "SPA" ), ( "plaque_beach", "BEACH CLUB" ) ):
        x, y, w, h = region( name )
        arr = np.full( ( h, w, 3 ), ( 52, 46, 40 ), np.float32 )
        a = text_layer( w, h, lambda d, w_, h_, word=word: tracked( d, ( 0, 0, w_, h_ ), word, track=0.35, height=0.5 ) )
        put( name, mix( arr, np.array( ( 210, 180, 120 ), np.float32 ), a[..., None] ) )
    # A notice board.
    x, y, w, h = region( "board" )
    arr = np.full( ( h, w, 3 ), ( 228, 226, 218 ), np.float32 )
    arr[:int( h * 0.2 )] = ( 34, 38, 44 )
    a = text_layer( w, h, lambda d, w_, h_: tracked( d, ( 0, 0, w_, h_ * 0.2 ), "VERIDANT  /  GUEST INFORMATION", track=0.15, height=0.5 ) )
    arr = mix( arr, np.array( ( 236, 236, 230 ), np.float32 ), a[..., None] )
    put( "board", arr )
    # Plain dark fabric (the banner's back, cushions).
    x, y, w, h = region( "fabric" )
    put( "fabric", fabric_weave( ( h, w ), rng, ( 50, 52, 56 ) ) )
    rough = 0.6 + 0.2 * ( canvas.mean( -1 ) < 60 )
    return canvas, rough.astype( np.float32 )


# ---------------------------------------------------------------------------------------------------------------------
# Foliage (alpha atlas): leaves drawn at twice the size and taken down

FOLIAGE_ATLAS = ( 4096, 4096 )
FOLIAGE = {
    "olive": ( 0, 0, 2048, 2048 ), "ivy": ( 2048, 0, 1024, 2048 ), "ivy_2": ( 3072, 0, 1024, 2048 ),
    "pine": ( 0, 2048, 2048, 1024 ), "palm": ( 2048, 2048, 2048, 1024 ), "shrub": ( 0, 3072, 1024, 1024 ),
    "flowers": ( 1024, 3072, 1024, 1024 ), "grass": ( 2048, 3072, 1024, 1024 ), "rosemary": ( 3072, 3072, 1024, 1024 ),
}


def leaf_poly( cx, cy, length, width, angle, tip=0.0 ):
    pts = []
    for t in np.linspace( 0, 1, 9 ):
        half = width * 0.5 * math.sin( math.pi * t ) ** 0.8
        pts.append( ( t * length, half ) )
    for t in np.linspace( 1, 0, 9 ):
        half = width * 0.5 * math.sin( math.pi * t ) ** 0.8
        pts.append( ( t * length, -half ) )
    ca, sa = math.cos( angle ), math.sin( angle )
    return [ ( cx + x * ca - y * sa, cy + x * sa + y * ca ) for x, y in pts ]


def foliage_atlas():
    W, H = px( FOLIAGE_ATLAS[0] ), px( FOLIAGE_ATLAS[1] )
    k = W / FOLIAGE_ATLAS[0]
    ss = 2
    big = Image.new( "RGBA", ( W * ss, H * ss ), ( 0, 0, 0, 0 ) )
    d = ImageDraw.Draw( big )
    rng = np.random.default_rng( 23 )

    def region( name ):
        x, y, w, h = FOLIAGE[name]
        return x * k * ss, y * k * ss, w * k * ss, h * k * ss

    def jitter( col, amt=18 ):
        return tuple( int( np.clip( c + rng.normal( 0, amt ), 0, 255 ) ) for c in col ) + ( 255, )

    # Olive: thin twigs fanning out, narrow silver-green leaves in pairs along them.
    x, y, w, h = region( "olive" )
    for _ in range( 46 ):
        sx, sy = x + w * rng.uniform( 0.3, 0.7 ), y + h * rng.uniform( 0.55, 0.95 )
        ang = rng.uniform( -math.pi * 0.95, -math.pi * 0.05 )
        L = rng.uniform( 0.25, 0.55 ) * w
        pts = [ ( sx, sy ) ]
        for t in range( 1, 12 ):
            ang += rng.normal( 0, 0.08 )
            pts.append( ( pts[-1][0] + math.cos( ang ) * L / 11, pts[-1][1] + math.sin( ang ) * L / 11 ) )
        d.line( pts, fill=( 70, 62, 52, 255 ), width=max( 1, int( 3 * k * ss ) ) )
        for i in range( 2, len( pts ) ):
            px_, py_ = pts[i]
            seg = math.atan2( pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0] )
            for side in ( -1, 1 ):
                la = seg + side * rng.uniform( 0.35, 0.8 )
                ll = rng.uniform( 0.05, 0.075 ) * w
                top = rng.random() < 0.55
                col = jitter( ( 112, 128, 92 ) if top else ( 150, 160, 136 ), 14 )
                d.polygon( leaf_poly( px_, py_, ll, ll * 0.16, la ), fill=col )
    # Ivy strands: a wandering vine down the strip, alternate heart-shaped lobed leaves.
    for name in ( "ivy", "ivy_2" ):
        x, y, w, h = region( name )
        for strand in range( 3 ):
            cx = x + w * ( 0.25 + 0.25 * strand ) + rng.normal( 0, w * 0.04 )
            cy = y
            pts = []
            while cy < y + h:
                pts.append( ( cx, cy ) )
                cy += h * 0.02
                cx += rng.normal( 0, w * 0.015 )
            d.line( pts, fill=( 60, 50, 36, 255 ), width=max( 1, int( 3 * k * ss ) ) )
            for i, ( px_, py_ ) in enumerate( pts[::2] ):
                side = 1 if i % 2 else -1
                s = rng.uniform( 0.09, 0.15 ) * w
                lx, ly = px_ + side * s * 0.6, py_ + s * 0.15
                col = jitter( ( 46, 72, 34 ), 12 )
                for lobe in range( 5 ):
                    a = -math.pi / 2 + ( lobe - 2 ) * 0.55
                    lr = s * ( 0.5 if lobe in ( 1, 2, 3 ) else 0.35 )
                    d.polygon( leaf_poly( lx, ly, lr, lr * 0.9, a + math.pi ), fill=col )
                d.line( ( px_, py_, lx, ly ), fill=( 70, 80, 40, 255 ), width=max( 1, int( 2 * k * ss ) ) )
    # Stone pine: dense tufts of long needles, dark green, seen from the side and below: a band of tufts.
    x, y, w, h = region( "pine" )
    for _ in range( 520 ):
        cx, cy = x + w * rng.uniform( 0.02, 0.98 ), y + h * rng.uniform( 0.12, 0.88 )
        base = rng.uniform( 0, 2 * math.pi )
        col = jitter( ( 40, 62, 40 ), 10 )
        for _n in range( 14 ):
            a = base + rng.normal( 0, 0.9 )
            L = rng.uniform( 0.025, 0.05 ) * w
            d.line( ( cx, cy, cx + math.cos( a ) * L, cy + math.sin( a ) * L * 0.6 ), fill=col, width=max( 1, int( 2.2 * k * ss ) ) )
    # A palm frond: an arching midrib with narrow leaflets angled forward.
    x, y, w, h = region( "palm" )
    rib = [ ( x + w * 0.02 + w * 0.96 * t, y + h * ( 0.5 - 0.25 * math.sin( math.pi * t * 0.9 ) + 0.2 * t * t ) ) for t in np.linspace( 0, 1, 40 ) ]
    d.line( rib, fill=( 110, 110, 60, 255 ), width=max( 2, int( 8 * k * ss ) ) )
    for i in range( 2, len( rib ) - 1 ):
        px_, py_ = rib[i]
        seg = math.atan2( rib[i + 1][1] - py_, rib[i + 1][0] - px_ )
        for side in ( -1, 1 ):
            a = seg + side * 1.0
            L = h * 0.42 * math.sin( math.pi * ( i / len( rib ) ) * 0.95 + 0.1 )
            col = jitter( ( 70, 96, 50 ), 12 )
            d.polygon( leaf_poly( px_, py_, L, L * 0.09, a ), fill=col )
    # Shrub: a dense mound of small round leaves.
    x, y, w, h = region( "shrub" )
    for _ in range( 1800 ):
        r_ = rng.random() ** 0.5 * 0.48
        a = rng.uniform( 0, 2 * math.pi )
        cx, cy = x + w * ( 0.5 + r_ * math.cos( a ) ), y + h * ( 0.55 + r_ * math.sin( a ) * 0.85 )
        s = rng.uniform( 0.02, 0.035 ) * w
        d.ellipse( ( cx - s, cy - s * 0.7, cx + s, cy + s * 0.7 ), fill=jitter( ( 58, 84, 46 ), 14 ) )
    # Bougainvillea: leaves and magenta bracts.
    x, y, w, h = region( "flowers" )
    for _ in range( 900 ):
        cx, cy = x + w * rng.uniform( 0.05, 0.95 ), y + h * rng.uniform( 0.05, 0.95 )
        s = rng.uniform( 0.02, 0.04 ) * w
        if rng.random() < 0.45:
            d.ellipse( ( cx - s, cy - s, cx + s, cy + s ), fill=jitter( ( 196, 40, 120 ), 20 ) )
        else:
            d.polygon( leaf_poly( cx, cy, s * 2.4, s * 1.2, rng.uniform( 0, 6.28 ) ), fill=jitter( ( 60, 86, 44 ), 12 ) )
    # Ornamental grass: blades from the foot.
    x, y, w, h = region( "grass" )
    for _ in range( 260 ):
        bx = x + w * rng.normal( 0.5, 0.12 )
        a = -math.pi / 2 + rng.normal( 0, 0.35 )
        L = rng.uniform( 0.5, 0.95 ) * h
        pts = [ ( bx, y + h ), ( bx + math.cos( a ) * L * 0.5, y + h + math.sin( a ) * L * 0.5 ),
                ( bx + math.cos( a ) * L + rng.normal( 0, 0.05 ) * w, y + h + math.sin( a ) * L + L * 0.15 ) ]
        d.line( pts, fill=jitter( ( 140, 136, 90 ), 18 ), width=max( 1, int( 4 * k * ss ) ) )
    # Rosemary / lavender: fine upright stems with grey-green needles and a few blue flowers.
    x, y, w, h = region( "rosemary" )
    for _ in range( 180 ):
        bx = x + w * rng.uniform( 0.1, 0.9 )
        top = y + h * rng.uniform( 0.05, 0.4 )
        d.line( ( bx, y + h, bx + rng.normal( 0, 0.03 ) * w, top ), fill=( 90, 100, 76, 255 ), width=max( 1, int( 2 * k * ss ) ) )
        for t in np.linspace( 0, 1, 10 ):
            py_ = y + h - ( y + h - top ) * t
            col = jitter( ( 96, 112, 90 ), 10 ) if rng.random() < 0.85 else jitter( ( 120, 110, 190 ), 20 )
            d.line( ( bx, py_, bx + rng.normal( 0, 0.03 ) * w, py_ - h * 0.03 ), fill=col, width=max( 1, int( 3 * k * ss ) ) )
    small = big.resize( ( W, H ), Image.LANCZOS )
    rgba = np.asarray( small, np.float32 )
    colour = rgba[..., :3]
    alpha = rgba[..., 3] / 255.0
    # Bleed the colour into the transparent texels round the leaves, so mips don't fringe dark.
    mask = alpha > 0.05
    if mask.any():
        idx = ndimage.distance_transform_edt( ~mask, return_distances=False, return_indices=True )
        colour = colour[idx[0], idx[1]]
    return colour, alpha


# ---------------------------------------------------------------------------------------------------------------------
# Writing

# Flat paints: colour (sRGB), metalness, roughness, self-illumination brightness (0 for none)
PAINTED = {
    "vr_black": ( ( 20, 20, 22 ), 0.0, 0.55, 0 ),
    "vr_dark": ( ( 38, 38, 40 ), 0.1, 0.5, 0 ),
    "vr_soffit": ( ( 54, 52, 50 ), 0.0, 0.8, 0 ),
    "vr_led": ( ( 255, 188, 116 ), 0.0, 0.3, 4.0 ),
    "vr_led_soft": ( ( 255, 196, 132 ), 0.0, 0.3, 1.5 ),
    "vr_lamp": ( ( 255, 212, 158 ), 0.0, 0.3, 3.2 ),
    "vr_bulb": ( ( 255, 222, 172 ), 0.0, 0.3, 3.0 ),
    "vr_window_lit": ( ( 255, 204, 148 ), 0.0, 0.25, 1.0 ),
    "vr_window_dark": ( ( 24, 28, 34 ), 0.5, 0.1, 0 ),
    "vr_interior": ( ( 204, 190, 170 ), 0.0, 0.75, 0 ),
    "vr_interior_dark": ( ( 112, 98, 86 ), 0.0, 0.8, 0 ),
    "vr_ceiling": ( ( 220, 214, 204 ), 0.0, 0.85, 0 ),
    "vr_sofa": ( ( 196, 188, 172 ), 0.0, 0.88, 0 ),
    "vr_cushion": ( ( 134, 112, 94 ), 0.0, 0.9, 0 ),
    "vr_rug": ( ( 84, 72, 62 ), 0.0, 0.95, 0 ),
    "vr_white": ( ( 228, 228, 224 ), 0.0, 0.45, 0 ),
    "vr_umbrella": ( ( 112, 26, 32 ), 0.0, 0.78, 0 ),
    "vr_chrome": ( ( 204, 204, 208 ), 1.0, 0.18, 0 ),
    "vr_brass": ( ( 178, 134, 72 ), 1.0, 0.3, 0 ),
    "vr_planter": ( ( 46, 48, 50 ), 0.0, 0.7, 0 ),
    "vr_leaf_far": ( ( 70, 86, 62 ), 0.0, 0.85, 0 ),
    "vr_olive_mass": ( ( 98, 112, 84 ), 0.0, 0.85, 0 ),
    "vr_pine_dark": ( ( 30, 44, 32 ), 0.0, 0.9, 0 ),
    "vr_yacht": ( ( 236, 238, 240 ), 0.0, 0.28, 0.35 ),
    "vr_yacht_glass": ( ( 18, 24, 32 ), 0.6, 0.06, 0 ),
    "vr_yacht_trim": ( ( 60, 64, 70 ), 0.6, 0.3, 0 ),
    "vr_yacht_lit": ( ( 255, 214, 160 ), 0.0, 0.3, 2.0 ),
    "vr_sail": ( ( 240, 236, 226 ), 0.0, 0.7, 0 ),
    "vr_hull_dark": ( ( 30, 36, 48 ), 0.3, 0.3, 0 ),
    "vr_village": ( ( 196, 178, 150 ), 0.0, 0.9, 0 ),
    "vr_village_roof": ( ( 152, 84, 60 ), 0.0, 0.8, 0 ),
    "vr_village_lit": ( ( 255, 196, 128 ), 0.0, 0.3, 2.2 ),
    "vr_scrub": ( ( 50, 58, 40 ), 0.0, 0.95, 0 ),
    "vr_scrub_dark": ( ( 34, 42, 30 ), 0.0, 0.95, 0 ),
    "vr_far_land": ( ( 92, 98, 112 ), 0.0, 0.95, 0 ),
    "vr_line_yellow": ( ( 196, 160, 40 ), 0.0, 0.6, 0 ),
    "vr_flowerpot": ( ( 166, 92, 62 ), 0.0, 0.8, 0 ),
    "vr_cloth_white": ( ( 236, 232, 222 ), 0.0, 0.9, 0 ),
    "vr_mattress": ( ( 210, 204, 190 ), 0.0, 0.9, 0 ),
    "vr_mast": ( ( 220, 220, 216 ), 0.4, 0.4, 0 ),
    "vr_beacon_red": ( ( 255, 50, 40 ), 0.0, 0.3, 3 ),
    "vr_screen": ( ( 40, 120, 160 ), 0.0, 0.2, 1.0 ),
    "vr_umbrella_tie": ( ( 66, 16, 20 ), 0.0, 0.7, 0 ),
    # The headland seen from a kilometre and more: limestone in three tones, the maquis (holm oak, lentisk, pine) and
    # the garrigue between, the olive groves inland, the village's and castle's pale stone.
    "vr_lime_pale": ( ( 156, 154, 150 ), 0.0, 0.92, 0 ),
    "vr_lime": ( ( 128, 126, 123 ), 0.0, 0.92, 0 ),
    "vr_lime_shade": ( ( 98, 97, 96 ), 0.0, 0.94, 0 ),
    "vr_garrigue": ( ( 84, 88, 68 ), 0.0, 0.95, 0 ),
    "vr_maquis": ( ( 44, 56, 40 ), 0.0, 0.92, 0 ),
    "vr_maquis_dark": ( ( 28, 38, 30 ), 0.0, 0.92, 0 ),
    "vr_olive_grove": ( ( 88, 100, 78 ), 0.0, 0.9, 0 ),
    "vr_cypress": ( ( 24, 34, 27 ), 0.0, 0.92, 0 ),
    "vr_castle": ( ( 184, 176, 160 ), 0.0, 0.9, 0 ),
}


def save_grey( path, a, size=None ):
    img = Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" )
    if size:
        img = img.resize( size, Image.LANCZOS )
    img.save( path, optimize=True )


def save_rgb( path, a, quality=92 ):
    img = Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" )
    if str( path ).endswith( ".jpg" ):
        img.save( path, quality=quality, subsampling=0 )
    else:
        img.save( path, optimize=True )


def vmat( colour, normal, rough, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0, illum_tint=( 1, 1, 1 ),
          tint=( 1.0, 1.0, 1.0 ), rough_exp=1.0 ):
    lines = [ "// Tools/veridant_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha:
        lines += [ '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{alpha}"', '    g_flAlphaTestReference "0.5"',
                   '    g_flAntiAliasedEdgeStrength "1"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{illum}"', f'    g_flSelfIllumBrightness "{illum_brightness:.2f}"',
                   '    g_flSelfIllumAlbedoFactor "1.0"',
                   f'    g_vSelfIllumTint "[{illum_tint[0]:.6f} {illum_tint[1]:.6f} {illum_tint[2]:.6f} 0.000000]"' ]
    lines += [ f'    g_flRoughnessScaleFactor "{rough_exp:g}"', f'    g_flMetalness "{metalness:.2f}"', f'    TextureColor "{colour}"',
               f'    TextureNormal "{normal}"', f'    TextureRoughness "{rough}"', f'    TextureAmbientOcclusion "{DEFAULT_AO}"',
               f'    g_vColorTint "[{tint[0]:.6f} {tint[1]:.6f} {tint[2]:.6f} 1.000000]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines ) + "\n"


def painted_vmat( colour, metalness, roughness, glow ):
    r, g, b = ( c / 255.0 for c in colour )
    illum = ""
    if glow:
        illum = ( '    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"\n'
                  f'    g_flSelfIllumBrightness "{glow:.2f}"\n    g_flSelfIllumAlbedoFactor "1.0"\n'
                  '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"\n' )
    return ( '// Tools/veridant_materials.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n' + illum +
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             '    TextureColor "materials/default/default_color.tga"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             '    g_flModelTintAmount "1.0"\n}\n' )


def water_vmat( colour, flow, tile, strength, roughness, absorption, bank, note ):
    return ( f'// Tools/veridant_materials.py: {note} (Lowtide\'s water shader: filtered waves, depth absorption)\n"Layer0"\n{{\n'
             '    shader "shaders/hc1_lowtide_water.shader"\n'
             f'    g_vWaterColor "[{colour[0]:.4f} {colour[1]:.4f} {colour[2]:.4f}]"\n'
             f'    g_vWaterFlow "[{flow[0]:.2f} {flow[1]:.2f}]"\n'
             f'    g_flRippleTile "{tile:.1f}"\n'
             f'    g_flRippleStrength "{strength:.2f}"\n'
             f'    g_flWaterRoughness "{roughness:.3f}"\n'
             f'    g_flAbsorptionDistance "{absorption:.1f}"\n'
             f'    g_flBankFade "{bank:.2f}"\n}}\n' )


def glass_vmat( colour, blur=0.02, absorption=0.15, rough=0.04 ):
    return ( '// Tools/veridant_materials.py (Railhead\'s glass)\n"Layer0"\n{\n'
             '    shader "shaders/glass.shader"\n    F_GLASS_QUALITY "2"\n    g_bFogEnabled "1"\n'
             f'    g_flBlurAmount "{blur:.3f}"\n    g_flRefractionStrength "1.006"\n    AlbedoAbsorption "{absorption:.2f}"\n'
             '    g_flTintColor "[1.000000 1.000000 1.000000 0.000000]"\n'
             f'    TextureColor "[{colour[0]:.6f} {colour[1]:.6f} {colour[2]:.6f} 0.000000]"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]"\n'
             '    TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"\n'
             '    TextureAmbientOcclusion "[1.000000 1.000000 1.000000 0.000000]"\n'
             '    TextureBlendMask "materials/default/default_blend.tga"\n'
             '    TextureTintMask "materials/default/default.tga"\n'
             '    TextureTranslucency "materials/default/default_trans.tga"\n}\n' )


def write_text( path, text ):
    RM.write_text( path, text )


def write_surface( out, name, colour, rough, height, ppi, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0,
                   illum_tint=( 1, 1, 1 ), normal_size=None ):
    srgb = T.linear_to_srgb( colour )
    save_rgb( out / f"{name}_color.jpg", srgb )
    normal = ( RM.normal_map( height, ppi ) * 0.5 + 0.5 ) * 255
    if normal_size:
        normal = np.asarray( Image.fromarray( np.clip( normal, 0, 255 ).astype( np.uint8 ) ).resize( ( normal_size, normal_size ), Image.LANCZOS ), np.float32 )
    save_rgb( out / f"{name}_normal.jpg", normal, quality=94 )
    save_grey( out / f"{name}_rough.png", rough )
    alpha_path = illum_path = None
    if alpha is not None:
        save_grey( out / f"{name}_trans.png", alpha )
        alpha_path = f"{RESOURCE_DIR}/{name}_trans.png"
    if illum is not None:
        save_grey( out / f"{name}_illum.png", illum )
        illum_path = f"{RESOURCE_DIR}/{name}_illum.png"
    write_surface_vmat( out, name, metalness, alpha_path, illum_path, illum_brightness, illum_tint )
    print( f"wrote {name}" )
    return srgb


def write_surface_vmat( out, name, metalness=0.0, alpha_path=None, illum_path=None, illum_brightness=0.0, illum_tint=( 1, 1, 1 ) ):
    write_text( out / f"{name}.vmat", vmat( f"{RESOURCE_DIR}/{name}_color.jpg", f"{RESOURCE_DIR}/{name}_normal.jpg",
                                            f"{RESOURCE_DIR}/{name}_rough.png", metalness, alpha_path, illum_path,
                                            illum_brightness, illum_tint, tint=SURFACE_TINT.get( name, ( 1.0, 1.0, 1.0 ) ),
                                            rough_exp=ROUGH_EXP.get( name, 1.0 ) ) )


SURFACES = {
    "vr_wicker": lambda: __import__("veridant_chair").wicker_surface(px(1024)),
    "vr_stone": lambda: stone( pits=1.9 ),
    "vr_stone_dark": lambda: stone( seed=12, base=( 118, 116, 110 ), grime=0.7, pits=1.6 ),
    "vr_stone_light": lambda: stone( seed=13, base=( 192, 188, 178 ), tile=TILES["vr_stone_light"], n=px( 1024 ), panel=( 48.0, 48.0 ),
                                     pits=0.35, rough=0.6 ),
    "vr_concrete": lambda: concrete(),
    "vr_paving": lambda: paving(),
    "vr_floor": lambda: floor_tiles(),
    "vr_timber": lambda: timber(),
    "vr_timber_dark": lambda: timber( seed=42, colour=( 64, 46, 34 ), rough=0.55 ),
    "vr_steel": lambda: RM.painted( 43, ( 26, 27, 28 ), chips=0.05, tile=48.0, rough=0.36, grime=0.15, n=px( 1024 ), bare=( 70, 70, 70 ) ),
    "vr_case_black": lambda: moulded( 44, ( 30, 31, 32 ) ),
    "vr_case_olive": lambda: moulded( 45, ( 62, 68, 48 ), rough=0.6 ),
    "vr_tarp": lambda: tarp(),
    "vr_bark": lambda: bark(),
    "vr_palm_bark": lambda: palm_bark(),
    "vr_rock": lambda: rock(),
    "vr_cliff": lambda: cliff(),
    "vr_render": lambda: render(),
    "vr_grate": lambda: grate(),
    "vr_hedge": lambda: hedge(),
    "vr_gravel": lambda: gravel(),
    "vr_lawn": lambda: lawn(),
}
METALNESS = { "vr_grate": 0.6 }
# Tints and roughness exponents written into a surface's vmat (so they change without redrawing its maps:
# `python Tools/veridant_materials.py tints`). g_flRoughnessScaleFactor is an exponent: over 1 is glossier.
SURFACE_TINT = { "vr_stone": ( 0.76, 0.76, 0.78 ), "vr_stone_light": ( 0.78, 0.78, 0.8 ), "vr_stone_dark": ( 0.88, 0.88, 0.9 ) }
ROUGH_EXP = { "vr_paving": 1.45 }
NORMAL_SIZE = { "vr_paving": 2048, "vr_cliff": 1024 }
# Text-only materials over another surface's maps, tinted: the backdrop's distant cliffs.
DERIVED = { "vr_soil": ( "vr_gravel", ( .60, .55, .48 ) ),
            "vr_palm_mulch": ( "palm-mulch-v1/soil-bark", ( 1.0, 1.0, 1.0 ) ),  # dedicated PNG material in build()
            "vr_cliff_far": ( "vr_cliff", ( 0.60, 0.62, 0.68 ) ), "vr_cliff_grey": ( "vr_cliff", ( 0.78, 0.83, 0.94 ) ),
            "vr_rock_dark": ( "vr_rock", ( 0.55, 0.54, 0.54 ) ) }
NAMES = list( SURFACES ) + [ "foliage", "prints", "letters", "water", "glass", "painted", "derived", "impostors" ]


def all_paints():
    return ( list( SURFACES ) + [ "vr_foliage", "vr_print", "vr_letters_dark", "vr_letters_light", "vr_sea", "vr_pool",
                                  "vr_glass", "vr_glass_clear", "vr_bay_headland", "vr_bay_boats", "vr_inland_vista",
                                  "vr_inland_vista_b", "vr_inland_vista_c", "vr_inland_scrub", "vr_inland_brush" ] + list( PAINTED ) + list( DERIVED ) )


def build( name, out ):
    done = {}
    if name == "impostors":
        from veridant_impostors import write_materials
        write_materials(out)
        from veridant_inland_vista import write_materials as write_inland_materials
        write_inland_materials(out)
    elif name in SURFACES:
        c, r, h, ppi = SURFACES[name]()
        done[name] = write_surface( out, name, c, r, h, ppi, METALNESS.get( name, 0.0 ), normal_size=NORMAL_SIZE.get( name ) )
    elif name == "foliage":
        colour, alpha = foliage_atlas()
        save_rgb( out / "vr_foliage_color.png", colour )
        save_grey( out / "vr_foliage_trans.png", alpha )
        write_text( out / "vr_foliage.vmat", vmat( f"{RESOURCE_DIR}/vr_foliage_color.png", "materials/default/default_normal.tga",
                                                    "[0.750000 0.750000 0.750000 0.000000]", 0.0, f"{RESOURCE_DIR}/vr_foliage_trans.png" ) )
        done["vr_foliage"] = colour * alpha[..., None] + 30 * ( 1 - alpha[..., None] )
        print( "wrote vr_foliage" )
    elif name == "prints":
        c, r = prints_atlas()
        save_rgb( out / "vr_print_color.png", c )
        save_grey( out / "vr_print_rough.png", r )
        write_text( out / "vr_print.vmat", vmat( f"{RESOURCE_DIR}/vr_print_color.png", "materials/default/default_normal.tga",
                                                  f"{RESOURCE_DIR}/vr_print_rough.png" ) )
        done["vr_print"] = c
        print( "wrote vr_print" )
    elif name == "letters":
        a = letters_atlas()
        save_grey( out / "vr_letters_trans.png", a )
        for tone, tint, rough in ( ( "dark", ( 0.045, 0.045, 0.048 ), 0.75 ), ( "light", ( 0.88, 0.88, 0.86 ), 0.5 ) ):
            text = vmat( "[1.000000 1.000000 1.000000 0.000000]", "materials/default/default_normal.tga",
                         f"[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]", 0.0, f"{RESOURCE_DIR}/vr_letters_trans.png", tint=tint )
            write_text( out / f"vr_letters_{tone}.vmat", text )
        done["vr_letters"] = np.repeat( a[..., None] * 255, 3, -1 )
        print( "wrote vr_letters" )
    elif name == "water":
        write_text( out / "vr_sea.vmat", water_vmat( ( 0.012, 0.030, 0.042 ), ( -5.0, 1.5 ), 420.0, 0.85, 0.07, 80.0, 6.0,
                                                     "the sea" ) )
        from veridant_pool_detail import water_material
        write_text( out / "vr_pool.vmat", water_material() )
        print( "wrote vr_sea, vr_pool" )
    elif name == "glass":
        write_text( out / "vr_glass.vmat", glass_vmat( ( 0.86, 0.88, 0.86 ) ) )
        write_text( out / "vr_glass_clear.vmat", glass_vmat( ( 0.90, 0.95, 0.93 ), blur=0.0, absorption=0.08, rough=0.03 ) )
        print( "wrote vr_glass, vr_glass_clear" )
    elif name == "tints":
        for p in sorted( set( SURFACE_TINT ) | set( ROUGH_EXP ) ):
            write_surface_vmat( out, p, METALNESS.get( p, 0.0 ) )
        print( f"rewrote {len( set( SURFACE_TINT ) | set( ROUGH_EXP ) )} surface vmats" )
    elif name == "derived":
        for p, ( base, tint ) in DERIVED.items():
            if p == "vr_palm_mulch":
                from veridant_palm_mulch import write_materials
                write_materials( out )
                continue
            write_text( out / f"{p}.vmat", vmat( f"{RESOURCE_DIR}/{base}_color.jpg", f"{RESOURCE_DIR}/{base}_normal.jpg",
                                                 f"{RESOURCE_DIR}/{base}_rough.png", tint=tint ) )
        print( f"wrote {len( DERIVED )} derived materials" )
    elif name == "painted":
        for p, ( rgb, metal, rough, glow ) in PAINTED.items():
            write_text( out / f"{p}.vmat", painted_vmat( rgb, metal, rough, glow ) )
        print( f"wrote {len( PAINTED )} flat paints" )
    else:
        raise SystemExit( f"unknown texture {name}" )
    return done


def atlas_uv( table, size, name, s, t ):
    """ ( u, v ) in an atlas for ( s, t ) 0..1 across a region (s right, t up). """
    x, y, w, h = table[name]
    return ( x + s * w ) / size[0], 1.0 - ( y + ( 1.0 - t ) * h ) / size[1]


def aspect( table, name ):
    x, y, w, h = table[name]
    return w / h


def main():
    global SCALE
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to draw (default all: {', '.join( NAMES )})" )
    parser.add_argument( "--out", help="write somewhere else" )
    parser.add_argument( "--sheet", help="also write a contact sheet here" )
    parser.add_argument( "--scale", type=float, default=1.0 )
    args = parser.parse_args()
    SCALE = args.scale
    RM.SCALE = args.scale
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    results = {}
    for name in args.names or NAMES:
        results.update( build( name, out ) )
    if args.sheet and results:
        RM.write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
