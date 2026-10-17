"""
Riverdale's materials: a nuclear plant's concrete, steel and signage, drawn with numpy into Assets/materials/riverdale/.

    python Tools/riverdale_materials.py [names ...] [--out <dir>] [--sheet <png>] [--lit <png>] [--scale 0.25]

Drawn at their real size, as Boxyard's are (Tools/boxyard_materials.py's helpers draw them), as physically plausible
PBR: albedo (paint 30-80 %, nothing black), roughness, normals from a height in inches, and where it helps an AO map and a
metal map (F_METALNESS_TEXTURE: painted steel is not metal, the steel showing through its chips is). Colour is JPG, the
rest PNG: JPG's blocks show in a glossy surface's normals. Every name and marking is the map's own: Riverdale Nuclear is
a made-up operator, its logo a triangle round an orbit, and the plant's slogans are plain words. The scene is at sunrise
just after rain. Run this before Tools/riverdale_map.py. It writes (tile in inches; 2048 px for the first five, 1024 for
the rest):
    rv_wall         cast-in-place concrete off 4 x 8 ft plywood forms: each face its own tone with the ply's grain
                    printed in it, fins and steps at the joints, a tie hole every 2 ft (open cones, some grouted), pour
                    lines, bug holes, chipped arrises, hairline cracks; rain grime running down from the joints and rust
                    from the ties' ends, still damp under the joints (192)
    rv_plinth       the same, darker, grimier and more chipped, few ties: bases, the pool's coping, barriers (192)
    rv_wall_clean   the same, indoors: no weather (192)
    rv_floor        the reactor hall's hard-trowelled slab under a satin epoxy sealer (rough 0.25-0.4): trowel swirls,
                    filled saw joints every 16 ft, worn traffic lanes, forklift tyre marks, stains (384)
    rv_yard         the yard's 128 in slabs after rain: damp and dark (rough 0.35-0.5), sealed joints, tar-sealed cracks,
                    an asphalt repair, oil drips, tyre tracks, a worn walkway line, and water standing where the slabs dip
                    (rough 0.03-0.06, darker, flat) with a saturated rim (512)
    rv_asphalt      wet asphalt for roads, water in its wheel ruts (256)
    rv_yellow, rv_steel, rv_white, rv_dark, rv_frame, rv_door, rv_door_yellow, rv_louvre, rv_desk
                    paint on steel (paint_on_steel): chips gathered where things get knocked, through the primer to bare
                    steel at their middles, rust blooming round them, bunched scratches, touch-ups, blisters, rust and
                    grime runs, chalking, dust, the orange peel of a sprayed coat (48; rv_white, the doors 96)
    rv_hazard       yellow and black hazard stripes on that paint (32)
    rv_olive, rv_case   rotomoulded polyethylene cases: stipple, whitened scuffs, dents (48)
    rv_chair        woven upholstery (24)
    rv_pipe         aluminium jacketing: laps every 48 in along u held by stainless bands, a screwed seam along v, dents,
                    oxidation, grime (48). Laid out for u along a pipe; on planar UVs the bands still read as laps.
    rv_liner        the fuel pool's stainless liner: 48 in plates, rippled welds with heat tint, scratches (96)
    rv_galv         hot-dip galvanised steel: spangle, dull patina, white rust (48)
    rv_stainless    brushed stainless (48)
    rv_rust         steel left to rust (48)
    rv_grating      galvanised bar grating, alpha tested: 3/16 in bearing bars at 1.2 in, twisted cross bars every 4 in (24)
    rv_line_yellow, rv_line_white   floor paint, alpha tested where it's worn through: lay on a quad over the floor (96)
    rv_window_dark, rv_window_lit   windows on planar UVs: glass (rough 0.04, rain spots) over a room with blinds let
                    down to different heights; lit is self-illuminated, warm (96)
    rv_window_office, _plant, _corridor (and _lit)   rooms behind glass on shaders/belltower_window.shader, traced in
                    the shader; their quads need UVs 0-1 across (ROOM_UVS)
    rv_grime_foot, rv_grime_top     blended grime (F_TRANSLUCENT) on a quad of its own over a wall, UVs 0-1 up it and u
                    as far as the wall runs (192 in a repeat): foot is the bottom 4 ft after rain (mud, algae, damp), top
                    is grime running 8 ft down from a roof's or ledge's edge
    rv_puddle       four puddles in a 2 x 2 atlas (PUDDLES), alpha tested near-mirror water, for a quad by a drain
    rv_rack         the spent fuel racks' cells, their insides lit as the pool's light catches them
    rv_letters_dark, rv_letters_light   painted lettering and the logo, alpha tested, from one atlas (LETTERS)
    rv_plates       signs: the radiation caution sign, the UNIT banners, door placards, a clipboard (PLATES)
    rv_screens      the control room's monitors, self-lit (SCREENS)
    rv_pool_water   the pool's surface on hc1_tank_glass.shader: the water's colour by the path through it
and flat paints (PAINTED), the lamps among them self-lit. --lit writes lit swatches (GGX under a low warm sun, as walls
and laid flat towards the sun) to judge roughness and normals by. Other Riverdale modules add their own materials
(EXTRA_MODULES, load_extras).
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage, signal

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import boxyard_materials as BM  # noqa: E402

T = BM.T
lin, mix, smoothstep = BM.lin, BM.mix, BM.smoothstep

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/riverdale"
RESOURCE_DIR = "materials/riverdale"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT = ROOT / "Assets/fonts/Dinish-Bold.ttf"
FONT_LIGHT = ROOT / "Assets/fonts/Dinish-Regular.ttf"

SCALE = 1.0

# Tile sizes (inches) for the map's UVs.
TILES = { "rv_wall": 192.0, "rv_plinth": 192.0, "rv_floor": 384.0, "rv_yard": 512.0, "rv_grating": 24.0,
          "rv_yellow": 48.0, "rv_steel": 48.0, "rv_pipe": 48.0, "rv_white": 96.0, "rv_liner": 96.0, "rv_rack": 30.0,
          "rv_hazard": 32.0, "rv_olive": 48.0, "rv_case": 48.0,
          "rv_wall_clean": 192.0, "rv_dark": 48.0, "rv_frame": 48.0, "rv_door": 96.0, "rv_door_yellow": 96.0,
          "rv_louvre": 48.0, "rv_desk": 48.0, "rv_chair": 24.0, "rv_galv": 48.0, "rv_stainless": 48.0, "rv_rust": 48.0,
          "rv_asphalt": 256.0, "rv_line_yellow": 96.0, "rv_line_white": 96.0, "rv_window_dark": 96.0,
          "rv_window_lit": 96.0, "rv_grime_foot": 192.0, "rv_grime_top": 192.0, "rv_puddle": 96.0 }
WATER_Z = -30.0          # riverdale_map's pool surface (world z)


def px( n ):
    return max( 16, int( round( n * SCALE ) ) )


def field( rng, n, tile ):
    """ A square tile's noise maker and its x, z (inches, z up) grids. """
    ppi = n / tile

    def nz( beta, longest, shortest=None ):
        return BM.noise( rng, ( n, n ), ( ppi, ppi ), beta, longest, shortest )

    y, x = np.mgrid[0:n, 0:n].astype( np.float32 ) / ppi
    return nz, x, tile - y, ppi


def runs_down( sources, ppi, length ):
    """ Stains running down from sources (a picture, 1 at the top of a run): each pixel takes what's above it, decaying
    over length inches. Periodic (the tile repeats). """
    a = math.exp( -1.0 / max( 1.0, length * ppi ) )
    twice = np.concatenate( [ sources, sources ], 0 )
    out = signal.lfilter( [ 1.0 - a ], [ 1.0, -a ], twice, axis=0 )
    return out[sources.shape[0]:].astype( np.float32 )


def wobble( rng, shape, sigma ):
    return ndimage.gaussian_filter( rng.standard_normal( shape ).astype( np.float32 ), sigma, mode="wrap" )


# ---------------------------------------------------------------------------------------------------------------------
# Concrete

def concrete_wall( seed=11, base=( 148, 149, 146 ), grime=0.0, n=None ):
    """ Cast-in-place concrete: 96 in square formwork panels (a little different each), their seams' fins, four tie
    holes each, bug holes, efflorescence and rain runs from the ties. """
    n = n or px( 2048 )
    tile = TILES["rv_wall"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    panel = 96.0
    cure, mid, grit = nz( 2.8, 160, 16 ), nz( 2.0, 24, 1.5 ), nz( 0.6, 0.6, 0.1 )
    colour = lin( base )[None, None, :] * ( 1.0 + 0.055 * cure + 0.03 * mid + 0.035 * grit )[..., None]
    colour *= ( 1.0 + 0.02 * nz( 3.0, 200, 40 )[..., None] * np.array( [ 0.6, 0.2, -0.7 ], np.float32 ) )
    pi, pj = np.floor( x / panel ).astype( int ), np.floor( z / panel ).astype( int )
    offsets = rng.normal( 0, 0.035, ( 4, 4 ) ).astype( np.float32 )
    colour *= ( 1.0 + offsets[pi % 4, pj % 4] )[..., None]
    rough = 0.86 + 0.04 * mid
    height = 0.03 * mid + 0.02 * grit + 0.05 * cure * 0.2
    # Seams: a thin fin where the panels met, and a slight step.
    sx = np.minimum( x % panel, panel - x % panel )
    sz = np.minimum( z % panel, panel - z % panel )
    seam = np.minimum( sx, sz )
    fin = np.exp( -( seam / 0.18 ) ** 2 )
    colour *= ( 1.0 - 0.18 * fin + 0.06 * np.exp( -( ( seam - 0.5 ) / 0.35 ) ** 2 ) )[..., None]
    height += 0.06 * fin
    # Tie holes: four a panel, plugged with darker grout, a little sunk.
    hx, hz = x % panel, z % panel
    holes = np.zeros_like( x )
    for cx in ( panel * 0.25, panel * 0.75 ):
        for cz in ( panel * 0.25, panel * 0.75 ):
            d = np.sqrt( ( hx - cx ) ** 2 + ( hz - cz ) ** 2 )
            holes = np.maximum( holes, smoothstep( 0.75, 0.55, d ) )
    colour = mix( colour, lin( ( 92, 92, 90 ) ), holes * 0.85 )
    height -= 0.25 * holes
    # Rain runs: from the ties and the seams' tops, and anywhere a little.
    src = np.zeros_like( x )
    src[( holes > 0.5 )] = 0.6
    dots = ( rng.random( src.shape ) < 0.00004 ).astype( np.float32 )
    src = np.maximum( src, ndimage.grey_dilation( dots, size=( 1, 3 ) ) * rng.uniform( 0.3, 0.9 ) )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.2 ), mode="wrap" )
    runs = np.clip( runs_down( src, ppi, 40.0 ) * 6.0, 0, 1 ) * smoothstep( -0.8, 0.8, nz( 1.6, 30, 3 ) )
    colour = mix( colour, colour * 0.72, runs[..., None] * 0.7 )
    # Bug holes: small air voids.
    pits = smoothstep( 2.9, 3.4, nz( 0.4, 0.5, 0.08 ) )
    colour = mix( colour, colour * 0.45, pits[..., None] )
    height -= 0.08 * pits
    # Efflorescence and dirt in broad clouds.
    salts = smoothstep( 1.4, 2.6, nz( 2.2, 40, 4 ) )
    colour = mix( colour, lin( ( 196, 196, 190 ) ), salts[..., None] * 0.25 )
    dirt = smoothstep( 0.0, 2.0, nz( 2.4, 60, 6 ) ) * ( 0.25 + grime )
    colour = mix( colour, colour * lin( ( 150, 138, 120 ) ) * 3.4, dirt[..., None] * 0.35 )
    if grime:
        colour *= ( 1.0 - 0.25 * grime )
    rough = np.clip( rough + 0.05 * salts - 0.06 * runs, 0.4, 1.0 )
    return colour, rough, height, ppi


def floor_hall( seed=21, n=None ):
    """ A power-floated slab under a clear sealer: dark grey, burnished where the trowel went, sawn joints every 16 ft,
    tyre scuffs, and damp near the pool. """
    n = n or px( 2048 )
    tile = TILES["rv_floor"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cure, mid, grit = nz( 2.6, 200, 20 ), nz( 1.8, 20, 1.5 ), nz( 0.6, 0.5, 0.1 )
    colour = lin( ( 104, 106, 106 ) )[None, None, :] * ( 1.0 + 0.08 * cure + 0.04 * mid + 0.03 * grit )[..., None]
    swirl = smoothstep( -1.0, 1.4, nz( 1.4, 6, 0.6 ) )
    rough = 0.42 + 0.12 * swirl + 0.06 * cure
    height = 0.01 * mid + 0.006 * grit
    slab = 192.0
    joint = np.minimum( np.minimum( x % slab, slab - x % slab ), np.minimum( z % slab, slab - z % slab ) )
    groove = smoothstep( 0.2, 0.08, joint )
    colour = mix( colour, lin( ( 26, 26, 26 ) ), groove[..., None] * 0.9 )
    height -= 0.25 * groove
    # Tyre scuffs: long soft strokes.
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( 40 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.uniform( 0, math.pi )
        L = rng.uniform( 30, 160 )
        pts = [ ( cx + math.cos( a ) * L * t + rng.normal( 0, 0.4 ), cz + math.sin( a ) * L * t + 6 * math.sin( t * 3 ) ) for t in np.linspace( 0, 1, 12 ) ]
        cv.line( pts, rng.uniform( 2, 5 ), rng.uniform( 0.2, 0.7 ) )
    scuff = ndimage.gaussian_filter( cv.result(), 2.0, mode="wrap" )
    colour = mix( colour, colour * 0.6, scuff[..., None] * 0.6 )
    wet = smoothstep( 1.0, 2.0, nz( 2.6, 120, 12 ) )
    colour = mix( colour, colour * 0.7, wet[..., None] * 0.6 )
    rough = np.clip( mix( rough, 0.12, wet ) + 0.15 * scuff, 0.08, 1.0 )
    return colour, rough, height, ppi


def yard( seed=31, n=None ):
    """ The yard after rain: 16 ft slabs, darker where they're wet, sawn joints with black sealant, oil and tyre marks,
    and standing water where the slabs dip (glassy, darker, the texture flat under it). """
    n = n or px( 4096 )
    tile = TILES["rv_yard"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cure, mid, grit = nz( 2.8, 300, 30 ), nz( 2.0, 30, 2 ), nz( 0.6, 0.6, 0.19 )
    colour = lin( ( 128, 126, 122 ) )[None, None, :] * ( 1.0 + 0.08 * cure + 0.04 * mid + 0.05 * grit )[..., None]
    slab = 192.0
    joint = np.minimum( np.minimum( x % slab, slab - x % slab ), np.minimum( z % slab, slab - z % slab ) )
    spall = smoothstep( 1.4, 2.6, nz( 1.4, 10, 0.4 ) ) * 1.0
    groove = smoothstep( 0.24 + spall, 0.1, joint )
    colour = mix( colour, lin( ( 18, 18, 18 ) ), groove[..., None] * 0.9 )
    height = 0.03 * mid + 0.03 * grit - 0.4 * groove
    # Damp everywhere (rain): concrete darkens to ~60% wet.
    damp = 0.55 + 0.45 * smoothstep( -1.2, 1.0, nz( 2.4, 200, 20 ) )
    colour = colour * ( 1.0 - 0.4 * damp )[..., None]
    rough = 0.62 - 0.22 * damp + 0.05 * mid
    # Oil and tyre marks.
    oil = smoothstep( 1.6, 2.8, nz( 2.0, 40, 3 ) )
    colour = mix( colour, lin( ( 22, 20, 18 ) ), oil[..., None] * 0.6 )
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( 70 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.choice( [ 0.0, math.pi / 2 ] ) + rng.normal( 0, 0.2 )
        L = rng.uniform( 60, 300 )
        bend = rng.normal( 0, 0.002 )
        for off in ( -14.0, 14.0 ):
            pts = []
            for t in np.linspace( 0, 1, 16 ):
                s = L * t
                ang = a + bend * s
                pts.append( ( cx + math.cos( ang ) * s - math.sin( a ) * off, cz + math.sin( ang ) * s + math.cos( a ) * off ) )
            cv.line( pts, rng.uniform( 4, 7 ), rng.uniform( 0.15, 0.45 ) )
    tyres = ndimage.gaussian_filter( cv.result(), 1.5, mode="wrap" )
    colour = mix( colour, colour * 0.55, tyres[..., None] * 0.7 )
    # Puddles: where the slab dips (a low-frequency field), shallow and glassy.
    dip = nz( 2.4, 260, 20 ) + 0.35 * nz( 1.8, 40, 4 )
    puddle = smoothstep( 1.05, 1.3, dip )
    colour = mix( colour, colour * 0.55 + lin( ( 8, 10, 12 ) ), puddle[..., None] * 0.85 )
    rough = mix( rough, 0.02, puddle )
    height = mix( height, -0.05, puddle )
    rough = np.clip( rough + 0.1 * oil * 0 - 0.05 * tyres, 0.02, 1.0 )
    return colour, rough, height, ppi


# ---------------------------------------------------------------------------------------------------------------------
# Steel

def painted( seed, colour, chips=0.4, tile=48.0, rough=0.45, grime=0.4, n=None, bare=( 64, 64, 66 ) ):
    """ Paint on steel: mottled, chipped to dark steel at edges (anywhere, since the UVs are planar), grime runs. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    c = lin( colour )[None, None, :] * ( 1.0 + 0.04 * nz( 2.4, 30, 2 ) + 0.015 * nz( 0.8, 0.8, 0.1 ) )[..., None]
    r = np.full( ( n, n ), rough, np.float32 ) + 0.04 * nz( 2.0, 10, 1 )
    h = 0.004 * nz( 1.0, 1, 0.1 )
    chip = smoothstep( 2.4 - chips, 2.7 - chips, nz( 1.6, 6, 0.15 ) + 0.4 * nz( 0.8, 0.6, 0.08 ) )
    c = mix( c, lin( bare ), chip[..., None] )
    r = mix( r, 0.55, chip )
    h -= 0.01 * chip
    rust = smoothstep( 2.6, 3.0, nz( 1.6, 4, 0.2 ) ) * chip
    c = mix( c, BM.RUST, rust[..., None] * 0.8 )
    src = ( rng.random( ( n, n ) ) < 0.0002 ).astype( np.float32 )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.5 ), mode="wrap" ) * 4
    runs = np.clip( runs_down( src, ppi, 10.0 ) * 4.0, 0, 1 )
    c = mix( c, c * 0.7, runs[..., None] * grime )
    dirt = smoothstep( 0.4, 2.2, nz( 2.4, 20, 2 ) ) * grime
    c = mix( c, BM.GRIME, dirt[..., None] * 0.3 )
    r = np.clip( r + 0.15 * dirt, 0.05, 1 )
    return c, r, h, ppi


def pipe_jacket( seed=51, n=None ):
    n = n or px( 1024 )
    tile = TILES["rv_pipe"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    brush = ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 0.4, 18 ), mode="wrap" )
    brush /= brush.std() + 1e-6
    c = lin( ( 182, 186, 188 ) )[None, None, :] * ( 1.0 + 0.03 * brush + 0.06 * nz( 2.4, 30, 3 ) )[..., None]
    r = 0.32 + 0.05 * brush + 0.1 * smoothstep( 0.5, 2.0, nz( 2.2, 16, 2 ) )
    h = -0.04 * smoothstep( 2.0, 2.6, nz( 2.4, 8, 1.5 ) ) + 0.002 * brush
    smudge = smoothstep( 1.0, 2.4, nz( 2.2, 20, 2 ) )
    c = mix( c, c * 0.75, smudge[..., None] * 0.6 )
    return c, np.clip( r, 0.1, 1 ), h, ppi


def liner( seed=61, n=None ):
    n = n or px( 1024 )
    tile = TILES["rv_liner"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    plate = 48.0
    off = rng.normal( 0, 0.04, ( 2, 2 ) ).astype( np.float32 )
    pi, pj = ( x // plate ).astype( int ) % 2, ( z // plate ).astype( int ) % 2
    c = lin( ( 168, 172, 174 ) )[None, None, :] * ( 1.0 + off[pi, pj] + 0.04 * nz( 2.2, 20, 1 ) )[..., None]
    r = 0.26 + 0.06 * nz( 2.0, 12, 1 ) + 0.04 * off[pi, pj] * 10
    d = np.minimum( np.minimum( x % plate, plate - x % plate ), np.minimum( z % plate, plate - z % plate ) )
    weld = np.exp( -( d / 0.3 ) ** 2 )
    c = mix( c, lin( ( 120, 112, 100 ) ), weld[..., None] * 0.6 )
    h = 0.05 * weld + 0.004 * nz( 0.8, 0.5, 0.1 )
    r = mix( r, 0.55, weld )
    return c, np.clip( r, 0.08, 1 ), h, ppi


def rack( seed=71, n=None ):
    """ Square fuel storage cells, 10 in a side in a 30 in tile: bright steel walls, dark cells whose depth glows. """
    n = n or px( 512 )
    tile = TILES["rv_rack"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cell = 10.0
    d = np.minimum( np.minimum( x % cell, cell - x % cell ), np.minimum( z % cell, cell - z % cell ) )
    wall = smoothstep( 0.55, 0.35, d )
    inner = smoothstep( 0.6, 2.4, d )
    c = mix( lin( ( 10, 26, 32 ) )[None, None, :] * np.ones( ( n, n, 1 ), np.float32 ), lin( ( 180, 188, 190 ) ), wall[..., None] )
    c *= ( 1.0 + 0.05 * nz( 2.0, 10, 1 ) )[..., None]
    illum = inner * ( 0.7 + 0.3 * smoothstep( -1, 1, nz( 2.0, 20, 2 ) ) )
    r = mix( np.full( ( n, n ), 0.5, np.float32 ), 0.25, wall )
    h = 0.3 * wall
    return c, r, h, ppi, illum


def hazard( seed=81, n=None ):
    n = n or px( 512 )
    tile = TILES["rv_hazard"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    stripe = ( ( x + z ) % 16.0 ) < 8.0
    edge = smoothstep( 0.0, 0.15, np.minimum( ( x + z ) % 8.0, 8.0 - ( x + z ) % 8.0 ) )
    yellow, black = lin( ( 230, 178, 22 ) ), lin( ( 22, 22, 22 ) )
    c = np.where( stripe[..., None], yellow, black ) * ( 1.0 + 0.05 * nz( 2.2, 10, 1 ) )[..., None]
    wear = smoothstep( 1.6, 2.4, nz( 1.6, 4, 0.2 ) )
    c = mix( c, lin( ( 80, 80, 80 ) ), wear[..., None] * 0.7 )
    c = mix( c, BM.GRIME, smoothstep( 0.5, 2.2, nz( 2.4, 16, 2 ) )[..., None] * 0.25 )
    r = 0.55 + 0.1 * wear
    h = 0.01 * edge - 0.02 * wear
    return c, np.full( ( n, n ), 1.0, np.float32 ) * r, h, ppi


def grating( seed=91, n=None ):
    """ Bar grating seen from above: bearing bars every 1.18 in (30 mm), 3/16 in thick, cross bars every 4 in. Returns
    the colour, roughness, height and the alpha (1 on steel). """
    n = n or px( 512 )
    tile = TILES["rv_grating"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    pitch = tile / 20.0                      # 1.2 in, a whole number in the tile
    bx = np.minimum( x % pitch, pitch - x % pitch )
    bearing = smoothstep( 0.13, 0.08, bx )
    cz = np.minimum( z % 4.0, 4.0 - z % 4.0 )
    cross = smoothstep( 0.14, 0.09, cz )
    steel = np.maximum( bearing, cross )
    c = lin( ( 96, 98, 98 ) )[None, None, :] * ( 1.0 + 0.08 * nz( 2.2, 8, 0.5 ) )[..., None]
    dirt = smoothstep( 0.2, 2.0, nz( 2.4, 12, 1 ) )
    c = mix( c, BM.GRIME, dirt[..., None] * 0.4 )
    c = mix( c, lin( ( 214, 168, 30 ) ), cross[..., None] * 0.0 )
    r = 0.55 + 0.15 * dirt
    h = 0.15 * steel + 0.1 * cross
    return c, np.full( ( n, n ), 1.0, np.float32 ) * r, h, ppi, steel


# ---------------------------------------------------------------------------------------------------------------------
# The surfaces Riverdale uses since 2026-10-16. The functions above stay as they were: Veridant, Orion, Collider and
# Spillway draw some of their own materials with them.
#
# Each of these returns a dict: colour (linear 0-1), rough, height (inches), ppi, and any of metal (a 0-1 map, for
# F_METALNESS_TEXTURE), ao, alpha (alpha tested), trans (blended: F_TRANSLUCENT), illum and its brightness and tint.
# Everything is periodic: the tile repeats, so strokes and stains that cross an edge come back on the other side.

def blur( a, sigma ):
    """ A wrapped Gaussian blur, sigma in pixels (or ( down, across )), done in the frequency domain so big ones are
    cheap. """
    sy, sx = ( sigma, sigma ) if np.isscalar( sigma ) else sigma
    h, w = a.shape
    fy = np.fft.fftfreq( h )[:, None]
    fx = np.fft.rfftfreq( w )[None, :]
    g = np.exp( -2.0 * math.pi ** 2 * ( ( sy * fy ) ** 2 + ( sx * fx ) ** 2 ) )
    return np.fft.irfft2( np.fft.rfft2( a ) * g, s=( h, w ) ).astype( np.float32 )


def runs( sources, ppi, length, thick ):
    """ runs_down, scaled so a source thick pixels deep starts its run at its own strength. """
    a = math.exp( -1.0 / max( 1.0, length * ppi ) )
    return runs_down( sources, ppi, length ) / ( 1.0 - a ** max( 1.0, thick ) )


def wrap_normals( height, ppi ):
    """ OpenGL tangent normals (green up the picture) from heights in inches, wrapped at the tile's edges. """
    gx = ( np.roll( height, -1, 1 ) - np.roll( height, 1, 1 ) ) * 0.5
    gy = ( np.roll( height, -1, 0 ) - np.roll( height, 1, 0 ) ) * 0.5
    n = np.stack( [ -gx * ppi, gy * ppi, np.ones_like( height ) ], -1 )
    return ( n / np.linalg.norm( n, axis=-1, keepdims=True ) ).astype( np.float32 )


def cavity_ao( height, ppi, radii=( 0.25, 0.8, 2.5 ), strength=1.0, floor=0.25 ):
    """ Ambient occlusion from the height: how far a pixel sits below its surroundings at a few radii (inches). """
    occ = np.zeros_like( height )
    for r in radii:
        occ += np.clip( blur( height, max( 0.6, r * ppi ) ) - height, 0, None ) / ( r * 0.9 )
    return np.clip( 1.0 - strength * occ / len( radii ), floor, 1.0 ).astype( np.float32 )


def wave( rng, x, tile, amp, terms=4 ):
    """ A periodic wobble along x (inches): a few whole waves across the tile. """
    out = np.zeros_like( x )
    for k in range( 1, terms + 1 ):
        out += rng.normal( 0, amp / k ) * np.sin( 2 * math.pi * k * x / tile + rng.uniform( 0, 6.3 ) )
    return out


class Pen:
    """ Strokes and shapes on a tile in inches (x right, z up), drawn ss times larger and wrapped, read back as 0-1
    coverage. Overlaps keep the larger value. """

    def __init__( self, n, tile, ss=2 ):
        self.n, self.tile, self.ss = n, tile, ss
        self.k = n * ss / tile
        self.image = Image.new( "L", ( n * ss, n * ss ), 0 )
        self.draw = ImageDraw.Draw( self.image )

    def _copies( self ):
        t = self.tile
        return [ ( dx, dz ) for dx in ( -t, 0.0, t ) for dz in ( -t, 0.0, t ) ]

    def _p( self, x, z, dx, dz ):
        return ( ( x + dx ) * self.k, ( self.tile - z - dz ) * self.k )

    def line( self, pts, width, value=1.0 ):
        w = max( 1, int( round( width * self.k ) ) )
        for dx, dz in self._copies():
            self.draw.line( [ self._p( x, z, dx, dz ) for x, z in pts ], fill=int( value * 255 ), width=w, joint="curve" )

    def polygon( self, pts, value=1.0 ):
        for dx, dz in self._copies():
            self.draw.polygon( [ self._p( x, z, dx, dz ) for x, z in pts ], fill=int( value * 255 ) )

    def ellipse( self, x, z, rx, rz, value=1.0 ):
        for dx, dz in self._copies():
            ( a, b ), ( c, d ) = self._p( x - rx, z + rz, dx, dz ), self._p( x + rx, z - rz, dx, dz )
            self.draw.ellipse( ( a, b, c, d ), fill=int( value * 255 ) )

    def result( self ):
        a = np.asarray( self.image, np.float32 ) / 255.0
        s = self.ss
        return a.reshape( self.n, s, self.n, s ).mean( axis=( 1, 3 ) )


def splat( n, tile, pts, amps, radius, profile ):
    """ The sum of one shape (radius inches, profile( d ) for d = distance / radius) at each point (inches, x right, z up),
    wrapped. """
    ppi = n / tile
    img = np.zeros( ( n, n ), np.float32 )
    pts = np.asarray( pts, np.float64 ).reshape( -1, 2 )
    if not len( pts ):
        return img
    c = np.floor( pts[:, 0] * ppi ).astype( int ) % n
    r = np.floor( ( tile - pts[:, 1] ) * ppi ).astype( int ) % n
    np.add.at( img, ( r, c ), np.broadcast_to( np.asarray( amps, np.float32 ), ( len( pts ), ) ) )
    R = int( math.ceil( radius * ppi ) ) + 1
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype( np.float32 )
    k = profile( np.sqrt( xx * xx + yy * yy ) / ( radius * ppi ) ).astype( np.float32 )
    kern = np.zeros( ( n, n ), np.float32 )
    kern[yy.astype( int ) % n, xx.astype( int ) % n] = k
    return np.fft.irfft2( np.fft.rfft2( img ) * np.fft.rfft2( kern ), s=( n, n ) ).astype( np.float32 )


def cone( d ):
    return np.clip( 1.0 - d, 0, 1 )


def dome( d ):
    return np.sqrt( np.clip( 1.0 - d * d, 0, 1 ) )


def soft( d ):
    return np.exp( -3.0 * d * d ) * ( d < 1.6 )


def lin3( rgb ):
    return lin( rgb )[None, None, :]


def grey( a ):
    return np.repeat( a[..., None], 3, -1 )


def streaks( sources, ppi, lengths, thick=3.0 ):
    """ Stains running down from a source picture (each pixel's strength at the top of its run, sources thick pixels
    deep), lengths ( ( inches, share ), ... ). """
    out = np.zeros( sources.shape, np.float32 )
    for length, share in lengths:
        out += share * runs( sources, ppi, length, thick )
    return out


def finger_field( rng, n, ppi, across=0.6, along=40.0, contrast=1.2 ):
    """ Noise stretched down the picture (across and along in inches): streaks' fingers, 0-1. """
    f = blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( along * ppi * 0.25, across * ppi ) )
    f /= f.std() + 1e-6
    return smoothstep( -contrast, contrast, f )


# ---------------------------------------------------------------------------------------------------------------------
# Concrete

FORM_PANEL = ( 48.0, 96.0 )     # a 4 x 8 ft plywood form face, its long side up
TIE_PITCH = 24.0                # snap ties at 2 ft both ways, 1 ft in from each panel's edges


def formwork( seed=101, base=( 140, 140, 136 ), weather=1.0, ties=1.0, grime=0.0, chips=1.0, tile=None, n=None ):
    """ Cast-in-place concrete off plywood forms, as a plant's walls are poured: 4 x 8 ft form faces (each a little
    different: its own tone, a step at its edges and a fin of paste where it met the next), the plywood's grain printed
    in the face, pour lines where one layer of concrete met the next, a tie hole every 2 ft (most left open as cone holes,
    some grouted), bug holes (air voids, most near the top of each lift), chipped arrises along the joints and a few
    hairline cracks. Weathered by weather: rain runs down from the joints and the ties (grime, rust from the tie ends,
    a little efflorescence), and the wall is still damp under the joints after the rain. """
    tile = tile or TILES["rv_wall"]
    n = n or px( 2048 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    PW, PH = FORM_PANEL
    cols, rows = max( 1, int( round( tile / PW ) ) ), max( 1, int( round( tile / PH ) ) )
    pi = np.floor( x / PW ).astype( int ) % cols
    pj = np.floor( ( z % tile ) / PH ).astype( int ) % rows
    pid = pj * cols + pi
    count = cols * rows
    lx, lz = x - np.floor( x / PW ) * PW, ( z % tile ) % PH
    tone = rng.normal( 0, 0.03, count ).astype( np.float32 )
    warm = rng.normal( 0, 0.012, count ).astype( np.float32 )
    reuse = rng.uniform( 0.0, 1.0, count ).astype( np.float32 )
    step = rng.normal( 0, 0.018, count ).astype( np.float32 )

    broad, mottle, grit = nz( 3.0, tile, 20 ), nz( 2.2, 14, 0.8 ), nz( 0.5, 0.4, 0.09 )
    shade = 1.0 + tone[pid] + 0.04 * broad + 0.022 * mottle + 0.03 * grit
    shade *= 1.0 - 0.012 * ( 1.0 - lz / PH )            # paste a shade darker low in each lift
    height = 0.012 * mottle + 0.006 * grit + step[pid]
    rough = 0.86 + 0.035 * mottle + 0.02 * grit

    # The plywood's face: rotary-cut veneer grain running up each sheet, wavy, each sheet its own.
    w = rng.standard_normal( ( n, n ) ).astype( np.float32 )
    grain = blur( w, ( 9.0 * ppi, 0.07 * ppi + 0.5 ) )
    grain /= grain.std() + 1e-6
    wob = blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), 6 * ppi )
    wob = wob / ( wob.std() + 1e-6 ) * 0.8 * ppi
    rr, cc = np.mgrid[0:n, 0:n]
    shift_r = rng.integers( 0, n, count )
    shift_c = rng.integers( 0, n, count )
    grain = grain[( rr + shift_r[pid] ) % n, ( cc + shift_c[pid] + wob.astype( int ) ) % n]
    figure = blur( grain, 1.2 * ppi )
    shade *= 1.0 + 0.012 * grain + 0.02 * figure
    height += 0.004 * grain
    # Release agent and the forms' wear: cloudy darker marks on the more used sheets.
    blot = smoothstep( 0.5, 1.9, nz( 2.0, 12, 0.8 ) ) * reuse[pid]
    shade *= 1.0 - 0.06 * blot
    rough -= 0.04 * blot

    # Joints between form faces: paste leaked into a thin fin, a dark line, and sandy grout loss here and there.
    ex, ez = np.minimum( lx, PW - lx ), np.minimum( lz, PH - lz )
    seam = np.minimum( ex, ez )
    fin = np.exp( -( seam / 0.09 ) ** 2 )
    height += 0.03 * fin
    shade *= 1.0 - 0.13 * np.exp( -( seam / 0.16 ) ** 2 ) + 0.035 * np.exp( -( ( seam - 0.45 ) / 0.3 ) ** 2 )
    leak = smoothstep( 1.0, 2.2, nz( 1.6, 18, 0.6 ) ) * smoothstep( 1.4, 0.2, seam )
    leak *= smoothstep( -0.2, 0.9, nz( 0.8, 0.5, 0.08 ) )
    shade *= 1.0 - 0.28 * leak
    height -= 0.05 * leak
    rough += 0.06 * leak

    # Pour lines: where one layer met the next, a wavy darker line with lighter laitance over it, across the whole wall.
    for zp in sorted( rng.uniform( 0.0, tile, max( 1, int( tile // 70 ) ) ) ):
        line_z = zp + wave( rng, x, tile, 1.4 ) + 0.4 * nz( 1.4, 6, 0.6 )
        dz_ = ( z - line_z + tile / 2 ) % tile - tile / 2
        shade *= 1.0 - 0.09 * np.exp( -( dz_ / 0.35 ) ** 2 ) + 0.035 * np.exp( -( ( dz_ - 3.0 ) / 3.0 ) ** 2 ) - 0.02 * smoothstep( 0, -10, dz_ ) * smoothstep( -24, -10, dz_ )
        height -= 0.012 * np.exp( -( dz_ / 0.3 ) ** 2 )

    # Bug holes: small air voids, sized 1-8 mm, more of them near the top of each lift.
    pits = np.zeros( ( n, n ), np.float32 )
    for radius, count_, depth in ( ( 0.05, 12000, 0.03 ), ( 0.11, 2600, 0.06 ), ( 0.2, 600, 0.12 ), ( 0.34, 90, 0.18 ) ):
        p = np.column_stack( [ rng.uniform( 0, tile, count_ * 2 ), rng.uniform( 0, tile, count_ * 2 ) ] )
        keep = rng.random( len( p ) ) < 0.25 + 0.75 * ( ( p[:, 1] % PH ) / PH ) ** 1.6
        p = p[keep][:count_]
        pits += splat( n, tile, p, rng.uniform( 0.5, 1.0, len( p ) ) * depth, radius, dome )
    height -= pits
    shade *= 1.0 - np.clip( pits * 4.0, 0, 0.55 )

    # Tie holes: snap-tie cones, 1 1/4 in across at the face and 1 in deep, the tie's cut end rusty at the bottom; about
    # a third were grouted flush, a slightly paler disc with a ring of shrinkage round it.
    rust = np.zeros( ( n, n ), np.float32 )
    rust_src = np.zeros( ( n, n ), np.float32 )
    salts_src = np.zeros( ( n, n ), np.float32 )
    if ties:
        k = int( round( tile / TIE_PITCH ) )
        hx, hz = ( x - TIE_PITCH / 2 ) / TIE_PITCH, ( ( z % tile ) - TIE_PITCH / 2 ) / TIE_PITCH
        ix, iz = np.floor( hx + 0.5 ).astype( int ) % k, np.floor( hz + 0.5 ).astype( int ) % k
        hid = iz * k + ix
        state = rng.random( k * k )
        jitter = rng.normal( 0, 0.12, ( k * k, 2 ) ).astype( np.float32 )
        gx = ( hx - np.round( hx ) ) * TIE_PITCH - jitter[hid, 0]
        gz = ( hz - np.round( hz ) ) * TIE_PITCH - jitter[hid, 1]
        r = np.sqrt( gx * gx + gz * gz )
        is_open = ( state[hid] < 0.66 * ties ).astype( np.float32 )
        grouted = ( ( state[hid] >= 0.66 * ties ) & ( state[hid] < 0.98 * ties ) ).astype( np.float32 )
        r0, r1, deep = 0.62, 0.26, 1.0
        hole = np.clip( ( r0 - r ) / ( r0 - r1 ), 0, 1 ) * is_open
        lip = np.exp( -( ( r - r0 ) / 0.08 ) ** 2 ) * is_open
        height += -deep * hole ** 1.2 + 0.015 * lip
        shade *= 1.0 - 0.6 * hole ** 0.7
        end = smoothstep( 0.2, 0.1, r ) * is_open
        rust = np.maximum( rust, end )
        disc = smoothstep( 0.68, 0.6, r ) * grouted
        ring = np.exp( -( ( r - 0.64 ) / 0.04 ) ** 2 ) * grouted
        shade = shade * ( 1.0 - disc ) + disc * shade * ( 1.05 + 0.04 * np.sin( hid * 7.1 ) )
        shade *= 1.0 - 0.3 * ring
        height += -0.02 * disc - 0.03 * ring
        rough += 0.05 * disc
        # Sources of runs: just under each open hole (rust from the tie's end), some grouted ones (salts).
        leaks = rng.random( k * k ) < 0.45
        below = np.exp( -( gx / 0.25 ) ** 2 ) * np.exp( -( ( gz + r0 + 0.1 ) / 0.15 ) ** 2 )
        rust_src += below * is_open * leaks[hid]
        salts_src += below * grouted * ( rng.random( k * k ) < 0.3 )[hid]

    # Chipped arrises along the joints, and a few knocks elsewhere: paler, rougher broken concrete.
    chip_n = nz( 1.6, 3, 0.15 ) + 0.35 * nz( 0.6, 0.4, 0.08 )
    chip = smoothstep( 2.3, 2.55, chip_n + 1.9 * np.exp( -seam / 0.5 ) * smoothstep( 0.8, 1.6, nz( 1.6, 30, 3 ) ) * chips )
    chip = np.maximum( chip, smoothstep( 3.1, 3.3, chip_n ) * chips )
    shade = shade * ( 1.0 - chip ) + chip * ( 1.12 + 0.05 * grit )
    height -= 0.14 * chip * ( 0.6 + 0.4 * smoothstep( -1, 1, grit ) )
    rough += 0.08 * chip

    # Hairline cracks: shrinkage, mostly up and down, from a joint or a tie hole.
    pen = Pen( n, tile, ss=2 )
    for _ in range( 3 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        pts, ang = [ ( cx, cz ) ], -math.pi / 2 + rng.normal( 0, 0.3 )
        for _ in range( int( rng.uniform( 10, 40 ) ) ):
            ang += rng.normal( 0, 0.35 ) - 0.15 * ( ang + math.pi / 2 )
            cx, cz = cx + math.cos( ang ) * 1.2, cz + math.sin( ang ) * 1.2
            pts.append( ( cx, cz ) )
        pen.line( pts, 0.05, 0.9 )
    crack = pen.result()
    shade *= 1.0 - 0.45 * crack
    height -= 0.04 * crack
    salts_src += blur( crack, 1.5 ) * 0.35

    colour = lin3( base ) * shade[..., None]
    colour *= 1.0 + warm[pid][..., None] * np.array( [ 1.0, 0.2, -0.9 ], np.float32 )

    if weather:
        # Rain sheets down the face and drops off each form joint's fin; under every horizontal joint the wall stays
        # damp longer, and grime runs down from it in fingers of different widths and lengths.
        rows_src = blur( ( PH - lz < 0.45 ).astype( np.float32 ), 0.6 )
        along = smoothstep( -0.4, 1.3, nz( 1.2, 30, 0.8 ) ) * ( 0.4 + 0.6 * smoothstep( -1.2, 1.2, nz( 1.0, 4, 0.3 ) ) )
        src = rows_src * along
        fingers = finger_field( rng, n, ppi, across=0.5, along=50, contrast=1.0 )
        wash = streaks( src, ppi, ( ( 14.0, 0.45 ), ( 45.0, 0.35 ), ( 110.0, 0.2 ) ), 0.45 * ppi ) * ( 0.3 + 0.7 * fingers )
        wash = np.clip( wash * 1.7, 0, 1 ) * weather
        grime_c = lin3( ( 84, 82, 74 ) )
        colour = mix( colour, colour * 0.5 + grime_c * 0.22, wash[..., None] * 0.62 )
        bio = wash * smoothstep( 0.2, 1.6, nz( 1.8, 40, 2 ) )
        colour = mix( colour, colour * lin3( ( 120, 128, 104 ) ) * 2.4, bio[..., None] * 0.25 * weather )
        rough -= 0.07 * wash
        # Damp: the band under each joint dries last, with soft patches where the water soaked in.
        damp_band = runs( rows_src, ppi, 16.0, 0.45 * ppi ) * smoothstep( -1.0, 1.2, nz( 1.6, 24, 2 ) )
        damp = np.clip( damp_band * 0.7 + 0.6 * smoothstep( 1.2, 2.4, nz( 2.6, 90, 8 ) ), 0, 1 ) * weather
        colour *= ( 1.0 - 0.22 * damp )[..., None]
        rough -= 0.12 * damp
        # Rust from the ties' cut ends, and salts out of the grouted holes and the cracks.
        if ties:
            rust_runs = np.clip( streaks( rust_src, ppi, ( ( 4.0, 0.6 ), ( 12.0, 0.4 ) ), 0.27 * ppi ), 0, 1 )
            rust_runs *= finger_field( rng, n, ppi, across=0.25, along=12, contrast=0.8 )
            colour = mix( colour, colour * lin3( ( 176, 112, 70 ) ) * 2.0, rust_runs[..., None] * 0.45 * weather )
        salts = np.clip( streaks( salts_src, ppi, ( ( 6.0, 0.6 ), ( 20.0, 0.4 ) ), 0.27 * ppi ), 0, 1 ) * weather
        salts = blur( salts, 0.12 * ppi ) * ( 0.5 + 0.5 * finger_field( rng, n, ppi, across=0.3, along=6, contrast=1.0 ) )
        colour = mix( colour, lin3( ( 188, 186, 178 ) ), salts[..., None] * 0.16 )
        rough += 0.05 * salts
        dirt = smoothstep( 0.0, 2.0, nz( 2.4, 60, 6 ) ) * ( 0.25 + grime )
        colour = mix( colour, colour * lin3( ( 150, 138, 120 ) ) * 3.4, dirt[..., None] * 0.3 )
    rust = rust * ( 0.7 + 0.3 * smoothstep( -1, 1, grit ) )
    colour = mix( colour, lin3( ( 96, 52, 30 ) ), rust[..., None] * 0.8 )
    if grime:
        colour *= 1.0 - 0.18 * grime
    ao = cavity_ao( height, ppi, ( 0.2, 0.6, 1.6 ), 1.4 )
    colour *= ( 0.55 + 0.45 * ao ** 0.8 )[..., None]
    return dict( colour=colour.astype( np.float32 ), rough=np.clip( rough, 0.45, 0.97 ), height=height, ppi=ppi, ao=ao )


def aggregate( rng, n, tile, density, radius=( 0.08, 0.3 ) ):
    """ Stones of the mix showing at a worn surface: light quartz, dark basalt, warm sandstone and grey. Returns their
    tint (a multiplier per channel) and a height. """
    tint = np.ones( ( n, n, 3 ), np.float32 )
    height = np.zeros( ( n, n ), np.float32 )
    area = tile * tile
    for colour, share in ( ( ( 1.28, 1.26, 1.2 ), 0.35 ), ( ( 0.62, 0.62, 0.64 ), 0.3 ), ( ( 1.12, 1.0, 0.86 ), 0.2 ),
                           ( ( 0.9, 0.92, 0.95 ), 0.15 ) ):
        for r in ( radius[0], ( radius[0] + radius[1] ) / 2, radius[1] ):
            count = int( density * share * area / ( r * r * 40 ) )
            pts = rng.uniform( 0, tile, ( count, 2 ) )
            cover = np.clip( splat( n, tile, pts, 1.0, r, soft ), 0, 1 )
            tint = tint * ( 1 - cover[..., None] ) + cover[..., None] * np.array( colour, np.float32 )
            height += 0.02 * cover * r / radius[1]
    return tint, height


def wet_yard( seed=131, tile=None, n=None ):
    """ The yard's slabs just after rain, at sunrise: 128 in slabs (each its own tone, tilt and curl), sawn joints sealed
    black (cracked and weedy here and there), a light broom finish worn to the aggregate, a few cracks sealed with tar,
    an asphalt patch, oil drips, tyre tracks, a worn walkway line. The whole slab is damp and dark (rough 0.35-0.5) and
    water stands where the slabs dip: near mirrors (rough 0.03-0.06), darker underneath and flat, with a saturated rim
    and silt at their edges. """
    tile = tile or TILES["rv_yard"]
    n = n or px( 2048 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    SL = 128.0
    k = max( 1, int( round( tile / SL ) ) )
    zz = z % tile
    si, sj = np.floor( x / SL ).astype( int ) % k, np.floor( zz / SL ).astype( int ) % k
    sid = sj * k + si
    lx, lz = x - np.floor( x / SL ) * SL, zz - np.floor( zz / SL ) * SL
    count = k * k
    tone = rng.normal( 0, 0.05, count ).astype( np.float32 )
    warm = rng.normal( 0, 0.02, count ).astype( np.float32 )
    tilt = rng.normal( 0, 1.0, ( count, 2 ) ).astype( np.float32 )
    curl = rng.uniform( 0.3, 1.0, count ).astype( np.float32 )
    broom = rng.integers( 0, 2, count )
    worn = rng.uniform( 0.2, 1.0, count ).astype( np.float32 )

    broad, mid, grit = nz( 2.8, tile, 30 ), nz( 2.0, 24, 1.5 ), nz( 0.6, 0.5, 0.12 )
    shade = 1.0 + tone[sid] + 0.05 * broad + 0.03 * mid + 0.05 * grit
    height = 0.012 * mid + 0.008 * grit
    # A light broom finish across each slab, its direction slab by slab, worn back to the aggregate where it's driven on.
    w = rng.standard_normal( ( n, n ) ).astype( np.float32 )
    along_x = blur( w, ( 0.5, 6.0 * ppi ) )
    along_z = blur( w, ( 6.0 * ppi, 0.5 ) )
    lines = np.where( broom[sid] == 0, along_x, along_z )
    lines /= lines.std() + 1e-6
    wear = smoothstep( -0.6, 1.2, nz( 2.2, 60, 4 ) ) * worn[sid]
    shade *= 1.0 + 0.025 * lines * ( 1 - wear )
    height += 0.006 * lines * ( 1 - wear )
    stones, stone_h = aggregate( rng, n, tile, 0.4 )
    expose = 0.35 + 0.65 * wear
    colour = lin3( ( 150, 147, 140 ) ) * shade[..., None]
    colour = colour * ( 1 - expose[..., None] * 0.55 ) + colour * stones * expose[..., None] * 0.55
    colour *= 1.0 + warm[sid][..., None] * np.array( [ 1.0, 0.3, -0.8 ], np.float32 )
    height += stone_h * expose
    rough = 0.85 + 0.03 * mid

    # Sawn joints sealed with black polyurethane; spalled at places, the sealant split or gone and the gap full of grit or
    # moss.
    ex, ez = np.minimum( lx, SL - lx ), np.minimum( lz, SL - lz )
    seam = np.minimum( ex, ez )
    spall = smoothstep( 1.6, 2.4, nz( 1.4, 10, 0.4 ) ) * smoothstep( 1.5, 0.3, seam )
    groove = smoothstep( 0.24 + 1.2 * spall, 0.12, seam )
    gone = smoothstep( 0.8, 1.6, nz( 1.2, 30, 1.5 ) )
    moss = gone * smoothstep( 0.4, 1.4, nz( 1.6, 12, 0.6 ) )
    seal = lin3( ( 30, 30, 32 ) )
    gap = mix( lin3( ( 70, 64, 56 ) ), lin3( ( 46, 58, 34 ) ), moss[..., None] )
    colour = mix( colour, mix( seal, gap, gone[..., None] ), groove[..., None] * 0.92 )
    height -= 0.25 * groove + 0.12 * spall
    rough = mix( rough, 0.55, groove * ( 1 - gone ) )
    colour = mix( colour, colour * 1.08, ( spall * ( 1 - groove ) )[..., None] * 0.5 )

    pen = Pen( n, tile, ss=2 )
    # Cracks: random walks from slab corners and edges; most sealed with tar (a glossy black band), some still open.
    tar = Pen( n, tile, ss=2 )
    for c in range( 7 ):
        cx, cz = ( rng.integers( 0, k ) * SL + rng.choice( [ 0.0, rng.uniform( 20, 100 ) ] ), rng.integers( 0, k ) * SL + rng.uniform( 0, SL ) )
        if rng.random() < 0.5:
            cx, cz = cz, cx
        ang = rng.uniform( 0, 2 * math.pi )
        pts = [ ( cx, cz ) ]
        for _ in range( int( rng.uniform( 20, 70 ) ) ):
            ang += rng.normal( 0, 0.3 )
            cx, cz = cx + math.cos( ang ) * 1.6, cz + math.sin( ang ) * 1.6
            pts.append( ( cx, cz ) )
        if c < 4:
            tar.line( pts, rng.uniform( 0.8, 1.4 ), 1.0 )
        pen.line( pts, 0.08, 1.0 )
    crack = pen.result()
    tarred = blur( tar.result(), 0.5 ) * ( 0.75 + 0.25 * smoothstep( -1, 1, nz( 1.0, 2, 0.2 ) ) )
    colour *= ( 1.0 - 0.5 * crack )[..., None]
    height -= 0.06 * crack
    colour = mix( colour, lin3( ( 40, 39, 38 ) ), tarred[..., None] * 0.85 )
    height += 0.03 * tarred
    rough = mix( rough, 0.32, tarred )

    # A saw-cut repair over a broken corner, filled with asphalt: a rectangle, its edges a little chipped and its seam
    # sealed.
    patch = Pen( n, tile, ss=2 )
    seam_p = Pen( n, tile, ss=2 )
    px0, pz0 = rng.integers( 0, k ) * SL + rng.uniform( 6, 30 ), rng.integers( 0, k ) * SL + rng.uniform( 6, 30 )
    pw, ph = rng.uniform( 34, 56 ), rng.uniform( 26, 44 )
    corners = [ ( px0, pz0 ), ( px0 + pw, pz0 ), ( px0 + pw, pz0 + ph ), ( px0, pz0 + ph ) ]
    patch.polygon( corners, 1.0 )
    seam_p.line( corners + corners[:1], 1.0, 1.0 )
    asphalt = smoothstep( 0.35, 0.65, blur( patch.result(), 0.5 ) + 0.12 * nz( 0.8, 0.6, 0.1 ) )
    chips_a = smoothstep( 1.0, 2.2, nz( 0.6, 0.6, 0.12 ) )
    tar_tint = lin3( ( 84, 82, 78 ) ) * ( 1.0 + 0.2 * nz( 0.5, 0.3, 0.1 ) + 0.1 * nz( 2.0, 20, 2 ) )[..., None]
    tar_tint = mix( tar_tint, lin3( ( 150, 146, 138 ) ), chips_a[..., None] * 0.6 )
    colour = mix( colour, tar_tint, asphalt[..., None] )
    pseam = blur( seam_p.result(), 0.5 )
    colour = mix( colour, lin3( ( 34, 34, 34 ) ), pseam[..., None] * 0.7 )
    height += asphalt * ( 0.05 + 0.03 * grit ) - 0.04 * pseam
    rough = mix( rough, 0.88, asphalt )

    # Oil: drips under where vehicles stood, in a few slabs, each a dark drop with a browner halo.
    oil = np.zeros( ( n, n ), np.float32 )
    for _ in range( 5 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        pts = np.column_stack( [ cx + rng.normal( 0, 10, 60 ), cz + rng.normal( 0, 6, 60 ) ] )
        oil += splat( n, tile, pts, rng.uniform( 0.3, 1.0, 60 ), rng.uniform( 1.2, 3.0 ), soft )
    oil += 0.3 * smoothstep( 1.9, 2.9, nz( 2.2, 30, 2 ) )
    oil = np.clip( oil, 0, 1 )
    colour = mix( colour, colour * lin3( ( 86, 76, 64 ) ) * 1.6, oil[..., None] * 0.75 )

    # Tyre tracks: pairs of tracks 70 in apart across the tile, rubber and dried mud, the tread's blocks showing.
    tracks = Pen( n, tile, ss=1 )
    mud = Pen( n, tile, ss=1 )
    for _ in range( 6 ):
        horizontal = rng.random() < 0.5
        c0 = rng.uniform( 0, tile )
        bend = rng.normal( 0, 8 )
        start, length = rng.uniform( 0, tile ), rng.uniform( 120, tile )
        for off in ( -35.0, 35.0 ):
            pts = []
            for t in np.linspace( 0, 1, 24 ):
                a = start + length * t
                b = c0 + off + bend * math.sin( math.pi * t )
                pts.append( ( a, b ) if horizontal else ( b, a ) )
            ( mud if rng.random() < 0.4 else tracks ).line( pts, rng.uniform( 7, 11 ), rng.uniform( 0.3, 0.7 ) )
    tread = smoothstep( -0.3, 0.6, np.sin( ( x + z ) * 2.4 ) * np.sin( ( x - z ) * 2.4 ) )
    tyre = blur( tracks.result(), 1.5 ) * ( 0.6 + 0.4 * tread )
    muddy = blur( mud.result(), 2.0 ) * ( 0.5 + 0.5 * tread ) * smoothstep( -0.6, 1.0, nz( 1.6, 20, 1 ) )
    colour = mix( colour, colour * 0.72, tyre[..., None] * 0.6 )
    colour = mix( colour, lin3( ( 112, 94, 72 ) ), muddy[..., None] * 0.45 )

    # A walkway line, worn nearly away, and the scarified ghost of one ground off.
    line = Pen( n, tile, ss=2 )
    ghost = Pen( n, tile, ss=2 )
    lz0 = rng.uniform( 0, tile )
    lx0 = rng.uniform( 0, tile )
    line.line( [ ( lx0, lz0 ), ( lx0 + rng.uniform( 160, 260 ), lz0 ) ], 4.0, 1.0 )
    gz = rng.uniform( 0, tile )
    ghost.line( [ ( gz, lx0 ), ( gz, lx0 + 200 ) ], 6.0, 1.0 )
    paint = blur( line.result(), 0.6 ) * smoothstep( 0.2, 1.4, nz( 1.2, 3, 0.15 ) + 0.6 )
    colour = mix( colour, lin3( ( 196, 156, 40 ) ) * ( 0.8 + 0.2 * shade[..., None] ), paint[..., None] * 0.8 )
    rough = mix( rough, 0.6, paint )
    height += 0.01 * paint
    scar = blur( ghost.result(), 1.0 )
    colour = mix( colour, colour * 1.12, scar[..., None] * 0.6 )
    height -= 0.03 * scar * smoothstep( -1, 1, grit )

    # After the rain: everything's damp and dark, drier on the slabs' high spots.
    level = ( tilt[sid, 0] * ( lx / SL - 0.5 ) + tilt[sid, 1] * ( lz / SL - 0.5 ) ) * 0.6
    level += curl[sid] * ( 1.0 - ( ( 2 * lx / SL - 1 ) ** 2 + ( 2 * lz / SL - 1 ) ** 2 ) * 0.5 ) * 0.9
    level += 0.55 * broad + 0.3 * nz( 2.4, 60, 6 )
    level = blur( level, 1.5 * ppi )
    dry = smoothstep( -1.0, -2.0, level ) * 0.6 + 0.25 * smoothstep( 0.4, 1.8, nz( 2.4, 120, 10 ) )
    dry = np.clip( dry, 0, 0.75 )
    wet_c = colour * 0.56
    colour = mix( wet_c, colour * 0.8, dry[..., None] )
    rough = np.clip( mix( mix( 0.38, 0.5, smoothstep( -1, 1, mid ) ), 0.62, dry ) + 0.25 * ( rough - 0.85 ), 0.3, 0.75 )
    rough = mix( rough, 0.88, asphalt * dry )
    rough = mix( rough, 0.3, tarred )
    # Standing water: where the slab dips below the waterline, the edge wavy with the surface's own small relief.
    surface = level + 0.05 * nz( 1.6, 5, 0.4 ) + 0.15 * height
    depth = surface - np.quantile( surface, 0.84 )
    water = smoothstep( 0.0, 0.025, depth )
    rim = smoothstep( -0.18, 0.0, depth ) * ( 1 - water )
    silt = np.exp( -( ( depth + 0.02 ) / 0.015 ) ** 2 ) * smoothstep( -0.5, 1.0, nz( 1.4, 6, 0.4 ) )
    colour = mix( colour, colour * 0.82, rim[..., None] )
    colour = mix( colour, lin3( ( 120, 108, 88 ) ) * 0.7, silt[..., None] * 0.25 )
    under = colour * 0.62 * ( 1.0 - 0.25 * smoothstep( 0.0, 0.8, depth ) )[..., None]
    colour = mix( colour, under, water[..., None] )
    rough = mix( rough, 0.18, rim * 0.6 )
    rough = mix( rough, 0.035 + 0.02 * smoothstep( -1, 1, nz( 1.6, 20, 2 ) ), water )
    flat_h = blur( height, 2.0 * ppi )
    height = mix( height, flat_h - 0.08, water )
    ao = cavity_ao( height, ppi, ( 0.3, 1.0, 3.0 ), 1.0 )
    colour *= ( 0.7 + 0.3 * ao )[..., None]
    return dict( colour=colour.astype( np.float32 ), rough=np.clip( rough, 0.02, 1 ).astype( np.float32 ), height=height,
                 ppi=ppi, ao=ao, water=water )


def hall_floor( seed=141, tile=None, n=None ):
    """ The reactor hall's floor: a hard-trowelled slab under a satin epoxy sealer (rough 0.25-0.4). The power trowel's
    swirls burnished darker and glossier, sawn joints every 16 ft filled with grey semi-rigid filler (spalled a little),
    forklift tyre marks and black scuffs, lanes where traffic has worn the sealer dull, a few oil and drum-ring stains and
    hairline shrinkage cracks from the joints' corners. """
    tile = tile or TILES["rv_floor"]
    n = n or px( 2048 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    broad, mid, grit = nz( 2.6, tile, 24 ), nz( 1.8, 20, 1.5 ), nz( 0.6, 0.5, 0.12 )
    colour = lin3( ( 122, 123, 121 ) ) * ( 1.0 + 0.06 * broad + 0.03 * mid + 0.025 * grit )[..., None]
    rough = 0.3 + 0.03 * mid
    height = 0.004 * mid + 0.003 * grit
    # Trowel swirls: overlapping arcs of the blades, darker and glossier where they burnished.
    swirl = np.zeros( ( n, n ), np.float32 )
    for _ in range( 3 ):
        pen = Pen( n, tile, ss=2 )
        for _ in range( int( 700 * ( tile / 384.0 ) ** 2 ) ):
            cx, cz = rng.uniform( 0, tile, 2 )
            r = rng.uniform( 9, 22 )
            a0 = rng.uniform( 0, 2 * math.pi )
            span = rng.uniform( 0.6, 2.2 )
            pts = [ ( cx + r * math.cos( a0 + span * t ), cz + r * math.sin( a0 + span * t ) ) for t in np.linspace( 0, 1, 14 ) ]
            pen.line( pts, rng.uniform( 0.6, 2.0 ), rng.uniform( 0.1, 0.35 ) )
        swirl += blur( pen.result(), 2.0 ) / 3.0
    swirl = swirl / ( swirl.max() + 1e-6 )
    burn = smoothstep( 0.0, 1.6, nz( 2.2, 40, 4 ) ) * 0.6 + 0.4
    colour *= ( 1.0 - 0.12 * swirl * burn - 0.05 * smoothstep( 0.6, 2.0, nz( 2.4, 30, 3 ) ) )[..., None]
    rough -= 0.06 * swirl * burn
    height += 0.002 * swirl
    # Sawn joints, 1/8 in filled with grey filler, the arrises chipped here and there.
    slab = 192.0
    joint = np.minimum( np.minimum( x % slab, slab - x % slab ), np.minimum( z % slab, slab - z % slab ) )
    chip = smoothstep( 2.0, 2.6, nz( 1.4, 6, 0.3 ) ) * smoothstep( 0.9, 0.2, joint )
    groove = smoothstep( 0.18 + 0.5 * chip, 0.06, joint )
    colour = mix( colour, lin3( ( 64, 64, 64 ) ), groove[..., None] * 0.85 )
    colour = mix( colour, colour * 1.1, ( chip * ( 1 - groove ) )[..., None] )
    height -= 0.12 * groove + 0.06 * chip
    rough = mix( rough, 0.75, groove * 0.6 + chip * 0.5 )
    # Traffic lanes: the sealer worn duller and paler, along the hall.
    lane = np.zeros( ( n, n ), np.float32 )
    for _ in range( 3 ):
        c = rng.uniform( 0, tile )
        width = rng.uniform( 30, 60 )
        d = np.abs( ( ( z if rng.random() < 0.5 else x ) - c + tile / 2 ) % tile - tile / 2 )
        lane = np.maximum( lane, smoothstep( width, width * 0.3, d ) * rng.uniform( 0.5, 1.0 ) )
    lane *= smoothstep( -0.8, 1.2, nz( 1.8, 30, 2 ) )
    colour = mix( colour, colour * 1.07, lane[..., None] * 0.6 )
    rough += 0.16 * lane
    # Tyre marks: forklift arcs, paired, and black scuffs.
    tyres = Pen( n, tile, ss=2 )
    for _ in range( 26 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        r = rng.uniform( 40, 220 )
        a0 = rng.uniform( 0, 2 * math.pi )
        span = rng.uniform( 0.3, 1.2 ) * rng.choice( [ -1, 1 ] )
        val = rng.uniform( 0.2, 0.6 )
        for off in ( 0.0, rng.choice( [ 34.0, 40.0 ] ) ):
            pts = [ ( cx + ( r + off ) * math.cos( a0 + span * t ), cz + ( r + off ) * math.sin( a0 + span * t ) ) for t in np.linspace( 0, 1, 20 ) ]
            tyres.line( pts, rng.uniform( 3, 6 ), val * rng.uniform( 0.6, 1.0 ) )
    for _ in range( 120 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        a = rng.uniform( 0, math.pi )
        L = rng.uniform( 2, 14 )
        tyres.line( [ ( cx, cz ), ( cx + math.cos( a ) * L, cz + math.sin( a ) * L ) ], rng.uniform( 0.4, 1.4 ), rng.uniform( 0.3, 0.8 ) )
    marks = blur( tyres.result(), 1.6 ) * smoothstep( -1.4, 1.0, nz( 1.8, 60, 4 ) )
    colour = mix( colour, lin3( ( 40, 39, 38 ) ), marks[..., None] * 0.4 )
    rough = mix( rough, 0.48, marks * 0.5 )
    # Stains: an oil drip or two, a drum's rust ring, tide marks where puddles of wash water dried.
    oil = splat( n, tile, rng.uniform( 0, tile, ( 30, 2 ) ), rng.uniform( 0.2, 0.8, 30 ), 3.0, soft )
    oil = np.clip( oil + 0.5 * smoothstep( 2.2, 3.0, nz( 2.2, 30, 2 ) ), 0, 1 )
    colour = mix( colour, colour * 0.6, oil[..., None] * 0.7 )
    rough -= 0.08 * oil
    ringp = Pen( n, tile, ss=2 )
    for _ in range( 3 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        ringp.ellipse( cx, cz, 11.5, 11.5, 1.0 )
        ringp.ellipse( cx, cz, 10.6, 10.6, 0.0 )
    ring = blur( ringp.result(), 1.2 ) * smoothstep( -1.0, 1.0, nz( 1.2, 4, 0.3 ) )
    colour = mix( colour, lin3( ( 120, 70, 40 ) ) * 0.8, ring[..., None] * 0.5 )
    tide = np.abs( nz( 2.4, 60, 4 ) - 1.4 )
    tide = np.exp( -( tide / 0.05 ) ** 2 ) * smoothstep( 0.8, 1.6, nz( 2.4, 80, 6 ) )
    colour = mix( colour, colour * 1.15, tide[..., None] * 0.5 )
    # Hairline cracks from the joints' corners.
    cracks = Pen( n, tile, ss=2 )
    for _ in range( 5 ):
        cx, cz = rng.integers( 0, 3 ) * slab, rng.integers( 0, 3 ) * slab
        ang = rng.uniform( 0, 2 * math.pi )
        pts = [ ( cx, cz ) ]
        for _ in range( int( rng.uniform( 10, 40 ) ) ):
            ang += rng.normal( 0, 0.3 )
            cx, cz = cx + math.cos( ang ) * 1.5, cz + math.sin( ang ) * 1.5
            pts.append( ( cx, cz ) )
        cracks.line( pts, 0.08, 0.9 )
    crack = cracks.result()
    colour *= ( 1.0 - 0.4 * crack )[..., None]
    height -= 0.03 * crack
    ao = cavity_ao( height, ppi, ( 0.3, 1.0 ), 1.0 )
    return dict( colour=colour.astype( np.float32 ), rough=np.clip( rough, 0.18, 0.85 ).astype( np.float32 ), height=height,
                 ppi=ppi, ao=ao )


# ---------------------------------------------------------------------------------------------------------------------
# Metal, paint and plastic. Painted steel isn't metal (metalness 0); where the paint's chipped through to the steel it
# is (a metal map, F_METALNESS_TEXTURE).

STEEL_BARE = ( 168, 168, 170 )      # weathered mild steel's reflectance (metal: the colour is its F0)
PRIMER_GREY = ( 128, 126, 120 )     # zinc phosphate primer
PRIMER_RED = ( 124, 62, 46 )        # red oxide


def paint_on_steel( seed, colour, tile=48.0, n=None, rough=0.42, chips=0.4, primer=PRIMER_GREY, rust=0.5, grime=0.35,
                    chalk=0.3, dust=0.3, scratches=0.4, blisters=0.3, runs_from=0.4 ):
    """ Paint on steel, chipped the way it is in service: knocks take the topcoat off to the primer and, at their middles,
    the primer to bare steel, which rusts and blooms orange under the paint round it; scratches, underfilm blisters with
    a rust pinhole, rust and grime running down from them, the sun's chalking on the topcoat, dust. colour is an sRGB
    triple, or a picture (linear) for patterned paint. The orange peel of a sprayed coat is in the normals. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    grit = nz( 0.6, 0.5, 0.06 )
    if isinstance( colour, np.ndarray ):
        c = colour.astype( np.float32 ).copy()
    else:
        c = lin3( colour ) * np.ones( ( n, n, 1 ), np.float32 )
    c *= ( 1.0 + 0.035 * nz( 2.4, 30, 2 ) + 0.012 * grit )[..., None]
    peel = nz( 1.0, 0.3, 0.04 )
    h = 0.0012 * peel
    r = rough + 0.025 * nz( 2.0, 10, 1 ) + 0.01 * peel
    chalk_m = smoothstep( -0.6, 1.6, nz( 2.6, tile, 6 ) ) * chalk
    c = mix( c, c * 1.1 + lin3( ( 200, 200, 196 ) ) * 0.05, chalk_m[..., None] * 0.7 )
    r += 0.16 * chalk_m
    # Knocks, gathered where things get knocked: the topcoat off to the primer, and at their middles the primer off to
    # the steel. Chips a quarter inch to an inch or two across, their edges crisp.
    zone = smoothstep( 0.2, 1.8, nz( 2.4, tile, 5 ) )
    cn = nz( 2.0, 3.0, 0.12 ) + 0.28 * nz( 0.8, 0.35, 0.04 )
    thr = 2.9 - 1.7 * chips * ( 0.35 + 0.65 * zone )
    top_off = smoothstep( thr, thr + 0.05, cn )
    bare = smoothstep( thr + 0.45, thr + 0.5, cn )
    # Scratches in bunches, near-parallel in each: through to the primer, the deepest to the steel.
    pen, deep = Pen( n, tile, ss=2 ), Pen( n, tile, ss=2 )
    for _ in range( int( 6 * scratches * ( tile / 48.0 ) ** 2 ) ):
        gx, gz = rng.uniform( 0, tile, 2 )
        a0 = rng.uniform( 0, math.pi )
        for _ in range( int( rng.integers( 2, 7 ) ) ):
            cx, cz = gx + rng.normal( 0, 1.5 ), gz + rng.normal( 0, 1.5 )
            a = a0 + rng.normal( 0, 0.08 )
            L = rng.uniform( 0.8, 5.0 )
            pts = [ ( cx + math.cos( a ) * L * t, cz + math.sin( a ) * L * t + rng.normal( 0, 0.02 ) ) for t in np.linspace( 0, 1, 5 ) ]
            ( deep if rng.random() < 0.2 else pen ).line( pts, rng.uniform( 0.02, 0.05 ), rng.uniform( 0.6, 1.0 ) )
    top_off = np.maximum( top_off, pen.result() * 0.85 )
    bare = np.maximum( bare, deep.result() * 0.8 )
    top_off = np.maximum( top_off, bare )
    # A touch-up or two: a brushed patch of newer paint over old chips, a shade off the rest and a little glossier.
    touch = np.zeros( ( n, n ), np.float32 )
    if chips > 0.1 and not isinstance( colour, np.ndarray ):
        tp = Pen( n, tile, ss=2 )
        for _ in range( 2 ):
            cx, cz = rng.uniform( 0, tile, 2 )
            w, hh = rng.uniform( 3, 12 ), rng.uniform( 3, 10 )
            tp.polygon( [ ( cx, cz ), ( cx + w, cz + rng.normal( 0, 0.4 ) ), ( cx + w + rng.normal( 0, 0.6 ), cz + hh ), ( cx + rng.normal( 0, 0.6 ), cz + hh ) ] )
        touch = blur( tp.result(), 0.08 * ppi ) * smoothstep( -1.5, 0.5, nz( 1.2, 1.5, 0.1 ) )
        top_off *= 1 - touch
        bare *= 1 - touch
        c *= ( 1.0 + touch * rng.uniform( -0.08, 0.06 ) )[..., None]
        r = r - 0.06 * touch
        h += 0.002 * touch
    c = mix( c, lin3( primer ) * ( 1.0 + 0.05 * grit )[..., None], top_off[..., None] )
    r = mix( r, 0.62, top_off )
    h -= 0.004 * top_off + 0.002 * bare
    steel = lin3( STEEL_BARE ) * ( 1.0 + 0.1 * nz( 1.2, 2, 0.1 ) )[..., None]
    c = mix( c, steel, bare[..., None] )
    r = mix( r, 0.36 + 0.08 * grit, bare )
    # Rust: on the bare steel, blooming under the paint round it, and from blisters' pinholes.
    bloom = np.clip( blur( bare, 0.25 * ppi ) * 2.5, 0, 1 ) * smoothstep( -0.8, 1.2, nz( 1.4, 3, 0.2 ) )
    bl = np.zeros( ( n, n ), np.float32 )
    if blisters:
        count = int( 300 * blisters * ( tile / 48.0 ) ** 2 )
        pts = rng.uniform( 0, tile, ( count, 2 ) )
        keep = rng.random( count ) < 0.5 + 0.5 * ( pts[:, 1] / tile )
        bl = splat( n, tile, pts[keep], rng.uniform( 0.4, 1.0, keep.sum() ), rng.uniform( 0.06, 0.12 ), dome )
        h += 0.006 * bl
    rust_m = np.clip( bare * smoothstep( -0.6, 0.8, nz( 1.6, 2, 0.1 ) ) + 0.6 * bloom * ( 1 - bare ) + bl * 0.8, 0, 1 ) * rust
    rust_c = mix( BM.RUST_DARK * np.ones_like( c ), BM.RUST, smoothstep( -1, 1, grit )[..., None] )
    c = mix( c, rust_c, rust_m[..., None] * 0.85 )
    r = mix( r, 0.82, rust_m )
    h += 0.003 * rust_m * grit
    metal = bare * ( 1.0 - rust_m )
    # Runs: rust and grime down from the chips, the blisters and anywhere a little.
    src = np.clip( rust_m * 0.8, 0, 1 )
    stain = np.clip( streaks( src, ppi, ( ( 3.0, 0.6 ), ( 10.0, 0.4 ) ), 0.15 * ppi ), 0, 1 ) * runs_from
    stain *= finger_field( rng, n, ppi, across=0.15, along=8, contrast=1.0 ) * ( 1 - top_off )
    c = mix( c, c * lin3( ( 176, 120, 84 ) ) * 1.9, stain[..., None] * 0.5 )
    dots = ( rng.random( ( n, n ) ) < 0.0004 * grime ).astype( np.float32 )
    gsrc = blur( dots, ( 0.6, 1.2 ) ) * 6
    grime_runs = np.clip( streaks( gsrc, ppi, ( ( 6.0, 0.5 ), ( 18.0, 0.5 ) ), 2.0 ), 0, 1 )
    grime_runs *= finger_field( rng, n, ppi, across=0.3, along=12, contrast=1.0 )
    c = mix( c, c * 0.72, grime_runs[..., None] * grime )
    dirt = smoothstep( 0.2, 2.2, nz( 2.4, 20, 2 ) ) * grime
    c = mix( c, BM.GRIME * np.ones_like( c ), dirt[..., None] * 0.22 )
    r = r + 0.12 * dirt
    # Dust: fine and pale, lying in the paint's texture.
    dust_m = ( smoothstep( -0.4, 1.6, nz( 2.2, 16, 1 ) ) * 0.6 + 0.4 * smoothstep( 1.2, 2.0, grit ) ) * dust * ( 1 - metal )
    c = mix( c, lin3( ( 168, 160, 146 ) ) * np.ones_like( c ), dust_m[..., None] * 0.18 )
    r = r + 0.18 * dust_m
    ao = cavity_ao( h, ppi, ( 0.05, 0.2 ), 6.0, floor=0.6 )
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.08, 0.95 ).astype( np.float32 ), height=h, ppi=ppi,
                 metal=np.clip( metal, 0, 1 ), ao=ao )


def moulded( seed, colour, tile=48.0, n=None, rough=0.6 ):
    """ Rotomoulded polyethylene, as equipment cases are: a fine stipple, whitened scuffs and scratches where it's been
    dragged and stacked (glossier, the stipple worn off), a dent or two, dust in the texture. Not metal. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    stipple = nz( 0.8, 0.12, 0.03 )
    c = lin3( colour ) * ( 1.0 + 0.04 * nz( 2.4, 30, 3 ) + 0.02 * stipple )[..., None]
    h = 0.003 * stipple
    r = rough + 0.05 * stipple
    pen = Pen( n, tile, ss=2 )
    for _ in range( int( 220 * ( tile / 48.0 ) ** 2 ) ):
        cx, cz = rng.uniform( 0, tile, 2 )
        a = rng.uniform( 0, math.pi )
        L = rng.uniform( 0.3, 4.0 )
        pen.line( [ ( cx, cz ), ( cx + math.cos( a ) * L, cz + math.sin( a ) * L ) ], rng.uniform( 0.02, 0.15 ), rng.uniform( 0.3, 1.0 ) )
    scuff = blur( pen.result(), 0.6 ) * smoothstep( -1.0, 1.0, nz( 1.8, 12, 1 ) )
    scuff = np.clip( scuff + 0.25 * smoothstep( 2.0, 2.8, nz( 1.8, 4, 0.3 ) ), 0, 1 )
    c = mix( c, c * 1.3 + lin3( ( 150, 150, 146 ) ) * 0.06, scuff[..., None] * 0.55 )
    r = mix( r, 0.42, scuff )
    h = mix( h, h * 0.2, scuff )
    dents = splat( n, tile, rng.uniform( 0, tile, ( 6, 2 ) ), rng.uniform( 0.02, 0.06, 6 ), rng.uniform( 2.0, 5.0 ), soft )
    h -= dents
    dust = smoothstep( -0.5, 2.0, nz( 1.8, 8, 0.5 ) ) * 0.4
    c = mix( c, lin3( ( 140, 136, 126 ) ) * np.ones_like( c ), dust[..., None] * 0.1 )
    r += 0.1 * dust
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.3, 0.9 ).astype( np.float32 ), height=h, ppi=ppi )


def jacketing( seed=151, tile=None, n=None ):
    """ Aluminium jacketing over pipe insulation: sheets lapped every 48 in along the pipe (u), each lap held by a stainless
    band with its crimp seal and a midway band between, and a lapped longitudinal seam screwed every 6 in (v at a quarter of
    the tile). Mill finish, each sheet a little different; dents, chalky white oxidation, grime running down, dirt dulling
    it to a part-metal. Laid out for u along a pipe and v round it: on planar UVs the bands still read as laps. """
    tile = tile or TILES["rv_pipe"]
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    w = rng.standard_normal( ( n, n ) ).astype( np.float32 )
    roll = blur( w, ( 1.0, 3.0 * ppi ) )
    roll /= roll.std() + 1e-6
    c = lin3( ( 182, 184, 186 ) ) * ( 1.0 + 0.03 * nz( 2.6, tile, 6 ) + 0.006 * roll )[..., None]
    # Mill finish weathered dull: broad soft highlights, not a mirror (at 0.38 the jacketing read as chrome).
    r = 0.54 + 0.01 * roll + 0.04 * nz( 2.2, 16, 2 )
    h = 0.00005 * roll
    metal = np.ones( ( n, n ), np.float32 )
    # The circumferential lap at u = 0: the outer sheet's edge, its shadow line and a raised step.
    du = ( x + tile / 2 ) % tile - tile / 2
    edge = smoothstep( 0.05, -0.05, du )
    h += 0.03 * edge
    c *= ( 1.0 - 0.45 * np.exp( -( du / 0.06 ) ** 2 ) )[..., None]
    # Bands: at the lap and halfway, 3/4 in stainless, raised, a crimp seal on each.
    band = np.zeros( ( n, n ), np.float32 )
    for u0 in ( 0.0, tile / 2 ):
        d = ( x - u0 + tile / 2 ) % tile - tile / 2
        band = np.maximum( band, smoothstep( 0.42, 0.34, np.abs( d - 1.0 ) ) )
        seal_z = rng.uniform( 0, tile )
        dz_ = ( z - seal_z + tile / 2 ) % tile - tile / 2
        seal = smoothstep( 0.55, 0.45, np.abs( d - 1.0 ) ) * smoothstep( 0.9, 0.8, np.abs( dz_ ) )
        band = np.maximum( band, seal )
        h += 0.03 * seal
    h += 0.035 * band
    c = mix( c, lin3( ( 204, 204, 206 ) ), band[..., None] )
    r = mix( r, 0.42, band )
    c *= ( 1.0 - 0.35 * ( np.exp( -( ( ( x + tile / 2 - 0.62 ) % tile - tile / 2 ) / 0.05 ) ** 2 ) ) )[..., None]
    # The longitudinal seam: a lap and a screw every 6 in.
    v0 = tile * 0.25
    dv = ( z - v0 + tile / 2 ) % tile - tile / 2
    h += 0.03 * smoothstep( 0.05, -0.05, dv )
    c *= ( 1.0 - 0.4 * np.exp( -( dv / 0.06 ) ** 2 ) )[..., None]
    screw_u = ( x % 6.0 ) - 3.0
    screw = smoothstep( 0.22, 0.16, np.sqrt( screw_u ** 2 + ( dv + 0.5 ) ** 2 ) )
    h += 0.04 * screw
    c = mix( c, lin3( ( 150, 150, 152 ) ), screw[..., None] )
    # Dents, oxidation, grime.
    pts = rng.uniform( 0, tile, ( 5, 2 ) )
    h -= 0.6 * splat( n, tile, pts, rng.uniform( 0.04, 0.1, 5 ), rng.uniform( 2.5, 5.0 ), soft )
    crease = Pen( n, tile, ss=2 )
    for _ in range( 4 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        a = rng.uniform( 0, math.pi )
        L = rng.uniform( 2, 7 )
        crease.line( [ ( cx, cz ), ( cx + math.cos( a ) * L, cz + math.sin( a ) * L ) ], 0.3, 1.0 )
    h -= 0.04 * blur( crease.result(), 0.15 * ppi )
    ox = smoothstep( 0.8, 2.2, nz( 2.0, 10, 0.5 ) ) * smoothstep( -0.5, 1.0, nz( 0.8, 1, 0.1 ) )
    c = mix( c, lin3( ( 206, 206, 202 ) ), ox[..., None] * 0.3 )
    r = mix( r, 0.68, ox * 0.7 )
    metal *= 1.0 - 0.45 * ox
    src = ( rng.random( ( n, n ) ) < 0.00012 ).astype( np.float32 )
    src = blur( src, ( 0.6, 4.0 ) ) * 14 + 0.25 * band * smoothstep( 0.5, 1.5, nz( 1.0, 4, 0.5 ) )
    dirty = np.clip( streaks( src, ppi, ( ( 5.0, 0.5 ), ( 16.0, 0.5 ) ), 2.0 ), 0, 1 ) * 0.7
    dirty *= finger_field( rng, n, ppi, across=0.6, along=10, contrast=1.0 )
    dirty = np.clip( dirty + 0.5 * smoothstep( 0.6, 2.2, nz( 2.4, 30, 3 ) ), 0, 1 )
    c = mix( c, lin3( ( 104, 100, 92 ) ), dirty[..., None] * 0.4 )
    r = mix( r, 0.72, dirty * 0.6 )
    metal *= 1.0 - 0.65 * dirty
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.15, 0.9 ).astype( np.float32 ), height=h, ppi=ppi,
                 metal=np.clip( metal, 0, 1 ) )


def stainless_liner( seed=161, tile=None, n=None ):
    """ The fuel pool's liner: 48 in stainless plates (2B finish, each a little different), welded: a rippled bead, a
    straw-to-blue heat tint either side, a ground-flush stretch here and there, and the scratches of fuel handling. """
    tile = tile or TILES["rv_liner"]
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    plate = 48.0
    pi, pj = ( np.floor( x / plate ).astype( int ) % 2 ), ( np.floor( ( z % tile ) / plate ).astype( int ) % 2 )
    off = rng.normal( 0, 0.035, ( 2, 2 ) ).astype( np.float32 )
    c = lin3( ( 176, 178, 180 ) ) * ( 1.0 + off[pi, pj] + 0.03 * nz( 2.2, 20, 1 ) )[..., None]
    r = 0.3 + 0.05 * nz( 2.0, 12, 1 ) + 0.6 * off[pi, pj]
    dx = ( x + plate / 2 ) % plate - plate / 2
    dz = ( z + plate / 2 ) % plate - plate / 2
    vertical = np.abs( dx ) < np.abs( dz )
    d = np.where( vertical, dx, dz )
    along = np.where( vertical, z, x )
    ground = smoothstep( 0.5, 1.5, nz( 1.6, 40, 4 ) )
    bead = np.exp( -( d / 0.18 ) ** 2 )
    ripple = 0.5 + 0.5 * np.cos( ( along * 9.0 ) - np.abs( d ) * 12.0 )
    h = ( 0.05 * bead * ( 0.8 + 0.2 * ripple ) ) * ( 1 - ground ) + 0.0008 * nz( 0.8, 0.5, 0.1 )
    c = mix( c, lin3( ( 150, 146, 138 ) ), ( bead * ( 1 - ground ) )[..., None] * 0.6 )
    tint_d = np.abs( d )
    straw = np.exp( -( ( tint_d - 0.35 ) / 0.2 ) ** 2 ) * ( 1 - ground )
    blue = np.exp( -( ( tint_d - 0.2 ) / 0.1 ) ** 2 ) * ( 1 - ground )
    c = mix( c, lin3( ( 196, 170, 112 ) ), straw[..., None] * 0.35 )
    c = mix( c, lin3( ( 110, 112, 150 ) ), blue[..., None] * 0.3 )
    r = mix( r, 0.5, bead * ( 1 - ground ) )
    pen = Pen( n, tile, ss=2 )
    for _ in range( 140 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        a = rng.normal( math.pi / 2, 0.15 )
        L = rng.uniform( 2, 18 )
        pen.line( [ ( cx, cz ), ( cx + math.cos( a ) * L, cz + math.sin( a ) * L ) ], rng.uniform( 0.02, 0.05 ), rng.uniform( 0.3, 1.0 ) )
    scr = pen.result()
    c = mix( c, c * 1.12, scr[..., None] * 0.5 )
    r = mix( r, 0.18, scr * 0.6 )
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.08, 0.8 ).astype( np.float32 ), height=h, ppi=ppi,
                 metal=np.full( ( n, n ), 1.0, np.float32 ) - 0.3 * bead * ( 1 - ground ) )


def galvanised( seed=171, tile=48.0, n=None, age=0.5 ):
    """ Hot-dip galvanised steel: the zinc's spangle (crystals an inch or so across, each its own brightness), dulled
    grey with age, white rust where water stood, and rust spots where the zinc's worn through. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    from scipy.spatial import cKDTree
    pts = rng.uniform( 0, tile, ( int( tile * tile / 0.9 ), 2 ) )
    tree = cKDTree( pts, boxsize=tile )
    _, idx = tree.query( np.stack( [ x.ravel() % tile, z.ravel() % tile ], -1 ), k=1 )
    cell = rng.normal( 0, 1, len( pts ) ).astype( np.float32 )[idx].reshape( n, n )
    c = lin3( ( 176, 178, 178 ) ) * ( 1.0 + 0.06 * cell * ( 1 - 0.6 * age ) + 0.04 * nz( 2.4, 30, 3 ) )[..., None]
    r = 0.34 + 0.06 * cell + 0.22 * age + 0.04 * nz( 2.0, 10, 1 )
    h = 0.0015 * cell + 0.002 * nz( 0.8, 0.5, 0.1 )
    patina = smoothstep( -0.5, 1.5, nz( 2.4, 30, 3 ) ) * age
    c = mix( c, lin3( ( 150, 152, 150 ) ), patina[..., None] * 0.6 )
    white = smoothstep( 1.2, 2.4, nz( 2.0, 8, 0.4 ) ) * age
    c = mix( c, lin3( ( 210, 210, 204 ) ), white[..., None] * 0.6 )
    r = mix( r, 0.8, white )
    metal = 1.0 - 0.6 * white - 0.25 * patina
    rust = smoothstep( 2.4, 2.9, nz( 1.6, 4, 0.2 ) ) * age
    c = mix( c, BM.RUST * np.ones_like( c ), rust[..., None] * 0.8 )
    r = mix( r, 0.85, rust )
    metal *= 1.0 - rust
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.15, 0.9 ).astype( np.float32 ), height=h, ppi=ppi,
                 metal=np.clip( metal, 0, 1 ) )


def bar_grating( seed=181, tile=None, n=None ):
    """ Galvanised welded bar grating seen from above: 3/16 in bearing bars at 1.2 in centres (up the picture), twisted
    1/4 in cross bars every 4 in. The bars' tops are rounded in the normals, worn brighter where they're walked on, dirt
    and grit lie at the crossings. Alpha-tested: alpha is 1 on steel. """
    tile = tile or TILES["rv_grating"]
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    pitch = tile / max( 1, round( tile / 1.2 ) )
    bx = ( x + pitch / 2 ) % pitch - pitch / 2
    bearing = smoothstep( 0.105, 0.085, np.abs( bx ) )
    cz = ( z + 2.0 ) % 4.0 - 2.0
    twist = 0.02 * np.sin( x * 2 * math.pi / 0.9 )
    cross = smoothstep( 0.14, 0.11, np.abs( cz + twist ) )
    steel = np.maximum( bearing, cross )
    galv = galvanised( seed + 1, tile=tile, n=n, age=0.6 )
    c = galv["colour"]
    r, metal = galv["rough"], galv["metal"]
    crown = np.where( bearing >= cross, np.sqrt( np.clip( 1 - ( bx / 0.095 ) ** 2, 0, 1 ) ),
                      np.sqrt( np.clip( 1 - ( cz / 0.125 ) ** 2, 0, 1 ) ) )
    h = 0.04 * crown * steel + 0.04 * cross + galv["height"]
    walked = smoothstep( -0.5, 1.5, nz( 2.2, 30, 3 ) ) * crown
    c = mix( c, c * 1.12, walked[..., None] * 0.5 )
    r = mix( r, 0.3, walked * 0.6 )
    metal = np.clip( metal + 0.3 * walked, 0, 1 )
    near = smoothstep( 0.7, 0.0, np.minimum( np.abs( cz ), 1.0 ) ) * bearing
    dirt = near * smoothstep( -0.6, 1.2, nz( 1.6, 4, 0.3 ) ) + 0.4 * smoothstep( 0.4, 2.0, nz( 2.2, 20, 2 ) )
    dirt = np.clip( dirt, 0, 1 )
    c = mix( c, lin3( ( 74, 68, 58 ) ), dirt[..., None] * 0.6 )
    r = mix( r, 0.85, dirt * 0.7 )
    metal *= 1.0 - 0.7 * dirt
    c *= ( 0.75 + 0.25 * crown )[..., None]
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.15, 0.95 ).astype( np.float32 ), height=h, ppi=ppi,
                 metal=np.clip( metal, 0, 1 ), alpha=np.clip( steel * 1.15, 0, 1 ) )


def hazard_stripes( seed=191, tile=None, n=None ):
    """ Yellow and black hazard stripes painted on steel, 8 in each at 45 degrees (as rv_hazard always was), chipped,
    scuffed and grimed as a step edge's or a bollard's paint is. """
    tile = tile or TILES["rv_hazard"]
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    stripe = smoothstep( -0.04, 0.04, np.minimum( ( x + z ) % 16.0, 16.0 - ( x + z ) % 16.0 ) - 4.0 )
    yellow, black = lin( ( 222, 168, 24 ) ), lin( ( 46, 46, 44 ) )
    c = black + ( yellow - black ) * ( 1 - stripe )[..., None]
    s = paint_on_steel( seed, c, tile=tile, n=n, rough=0.48, chips=0.75, rust=0.6, grime=0.5, dust=0.4, scratches=1.2 )
    return s


def brushed( seed=211, tile=48.0, n=None ):
    """ Brushed stainless (No. 4 finish): fine grain along u, handled smudges a little rougher, a few scratches across. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    w = rng.standard_normal( ( n, n ) ).astype( np.float32 )
    grain = blur( w, ( 0.25, 4.0 * ppi ) )
    grain /= grain.std() + 1e-6
    c = lin3( ( 186, 186, 188 ) ) * ( 1.0 + 0.04 * grain + 0.03 * nz( 2.4, 20, 2 ) )[..., None]
    r = 0.3 + 0.05 * grain
    h = 0.0015 * grain
    smudge = smoothstep( 0.6, 2.0, nz( 2.2, 6, 0.4 ) )
    r = r + 0.12 * smudge
    c *= ( 1.0 - 0.06 * smudge )[..., None]
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.15, 0.7 ).astype( np.float32 ), height=h, ppi=ppi,
                 metalness=1.0 )


def rusted( seed=221, tile=48.0, n=None ):
    """ Steel left to rust: flaking scale over orange and brown, pitted, darker and blacker where water sits. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    broad, mid, fine = nz( 2.4, 30, 3 ), nz( 1.6, 4, 0.2 ), nz( 0.6, 0.4, 0.05 )
    c = mix( lin3( ( 68, 46, 36 ) ) * np.ones( ( n, n, 3 ), np.float32 ), lin3( ( 120, 74, 48 ) ),
             smoothstep( -1.4, 1.6, mid + 0.4 * broad )[..., None] )
    c = mix( c, lin3( ( 62, 52, 46 ) ), smoothstep( 0.4, 1.8, broad )[..., None] * 0.6 )
    c *= ( 1.0 + 0.1 * fine )[..., None]
    flakes = smoothstep( 1.0, 1.3, nz( 1.2, 2, 0.1 ) )
    h = 0.02 * flakes + 0.008 * fine - 0.03 * smoothstep( 2.2, 2.8, nz( 0.8, 0.5, 0.05 ) )
    r = 0.82 + 0.06 * fine - 0.1 * smoothstep( 0.6, 1.8, broad )
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.55, 0.95 ).astype( np.float32 ), height=h, ppi=ppi )


def wet_asphalt( seed=231, tile=None, n=None ):
    """ The access road's asphalt after rain: dark, its aggregate showing grey where traffic's worn the binder, cracks
    sealed with tar, wet and glossy (rough 0.3-0.5) with water standing in the wheel ruts. """
    tile = tile or TILES["rv_asphalt"]
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    broad, mid = nz( 2.6, tile, 20 ), nz( 1.8, 12, 1 )
    stones, stone_h = aggregate( rng, n, tile, 0.6, ( 0.1, 0.35 ) )
    worn = smoothstep( -0.6, 1.4, nz( 2.2, 60, 4 ) )
    base = lin3( ( 70, 68, 66 ) ) * ( 1.0 + 0.05 * broad + 0.05 * mid )[..., None]
    c = base * ( 1 - worn[..., None] * 0.5 ) + base * stones * 1.5 * worn[..., None] * 0.5
    h = stone_h * ( 0.4 + 0.6 * worn ) + 0.006 * mid
    tar = Pen( n, tile, ss=2 )
    for _ in range( 5 ):
        cx, cz = rng.uniform( 0, tile, 2 )
        ang = rng.uniform( 0, 2 * math.pi )
        pts = [ ( cx, cz ) ]
        for _ in range( int( rng.uniform( 20, 60 ) ) ):
            ang += rng.normal( 0, 0.3 )
            cx, cz = cx + math.cos( ang ) * 1.6, cz + math.sin( ang ) * 1.6
            pts.append( ( cx, cz ) )
        tar.line( pts, rng.uniform( 0.8, 1.6 ), 1.0 )
    tarred = blur( tar.result(), 0.5 )
    c = mix( c, lin3( ( 30, 30, 30 ) ), tarred[..., None] * 0.85 )
    c *= 0.62
    r = np.clip( 0.42 + 0.06 * mid - 0.08 * smoothstep( 0, 1.5, broad ), 0.3, 0.55 )
    r = mix( r, 0.28, tarred )
    rut = np.zeros( ( n, n ), np.float32 )
    for c0 in rng.uniform( 0, tile, 2 ):
        d = np.abs( ( x - c0 + tile / 2 ) % tile - tile / 2 )
        rut = np.maximum( rut, smoothstep( 14, 4, d ) )
    depth = rut * 0.35 * smoothstep( -0.5, 1.0, nz( 2.0, 60, 6 ) ) + 0.6 * broad + 0.1 * nz( 1.6, 4, 0.3 )
    water = smoothstep( 0.0, 0.03, depth - np.quantile( depth, 0.9 ) )
    c = mix( c, c * 0.6, water[..., None] )
    r = mix( r, 0.04, water )
    h = mix( h, blur( h, 2 * ppi ) - 0.05, water )
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.02, 1 ).astype( np.float32 ), height=h, ppi=ppi,
                 ao=cavity_ao( h, ppi, ( 0.2, 0.6 ), 1.0, floor=0.5 ) )


def line_paint( seed, colour, tile=96.0, n=None ):
    """ Road paint for floor lines, alpha-tested: worn through to whatever's under it where wheels and boots cross it
    (about a sixth gone), chipped at its edges, damp and glossy after the rain. Lay it on a quad just over the floor. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    c = lin3( colour ) * ( 1.0 + 0.05 * nz( 2.2, 20, 2 ) + 0.03 * nz( 0.6, 0.4, 0.08 ) )[..., None]
    wear = 0.6 * nz( 2.2, 30, 2.0 ) + 0.8 * nz( 1.4, 3, 0.1 )
    alpha = smoothstep( 1.65, 1.55, wear )
    thin = smoothstep( 0.5, 1.3, wear )
    c = mix( c, c * 0.72 + lin3( ( 90, 88, 84 ) ) * 0.2, thin[..., None] * 0.6 )
    dirt = smoothstep( 0.0, 2.0, nz( 2.4, 30, 3 ) )
    c = mix( c, c * lin3( ( 150, 140, 120 ) ) * 2.8, dirt[..., None] * 0.35 )
    h = 0.01 * nz( 0.6, 0.3, 0.06 ) + 0.01 * alpha
    r = 0.42 + 0.1 * thin + 0.08 * dirt
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.2, 0.8 ).astype( np.float32 ), height=h, ppi=ppi,
                 alpha=alpha )


def window_glass( seed, lit=False, tile=None, n=None ):
    """ A window seen from outside, on planar UVs (so nothing in it has to line up with its frame): flat glass (rough
    0.04, faint rain spots and run marks), behind it a room. Venetian blinds hang in bands of the picture, let down to
    different heights, so each window shows a blind part way down; elsewhere the room's dim shapes. Dark: daylight only,
    the room near black. Lit (self-illuminated): warm lights on inside, ceiling strips and the blinds glowing. """
    tile = tile or TILES["rv_window_dark"]
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    zz = z % tile
    # Bands across the picture, each with its blind let down to its own height (or not at all), the slats tilted
    # their own way.
    widths = rng.uniform( 30, 70, 6 )
    bands = np.cumsum( widths / widths.sum() * tile )
    band_id = np.searchsorted( bands, x % tile ) % len( bands )
    drop = np.where( rng.random( len( bands ) ) < 0.3, -1.0, rng.uniform( 0.15, 0.95, len( bands ) ) ) * tile
    edge_wob = 0.6 * nz( 1.4, 6, 0.6 )
    blind = smoothstep( -0.3, 0.3, zz - ( tile - drop[band_id] ) + edge_wob )
    blind *= smoothstep( 0.0, 1.0, np.abs( ( x % tile ) - np.concatenate( [ [ 0 ], bands ] )[band_id] ) )
    slat = 0.5 + 0.5 * np.cos( 2 * math.pi * zz / 1.0 )
    tilt = rng.uniform( 0.3, 0.85, len( bands ) )[band_id]
    gap = smoothstep( tilt, tilt + 0.2, slat )
    # The room behind: dim and soft, darker low down where desks and cabinets stand, lighter towards the ceiling.
    up = zz / tile
    room_v = smoothstep( -1.2, 1.4, nz( 2.6, tile, 8 ) )
    shapes = Pen( n, tile, ss=1 )
    for _ in range( 7 ):
        cx, w_ = rng.uniform( 0, tile ), rng.uniform( 14, 34 )
        top = rng.uniform( 0.3, 0.75 ) * tile
        shapes.polygon( [ ( cx, 0 ), ( cx + w_, 0 ), ( cx + w_, top ), ( cx, top ) ], rng.uniform( 0.25, 0.6 ) )
    tall = blur( shapes.result(), 1.5 * ppi )
    low = smoothstep( 0.42, 0.3, up ) * ( 0.6 + 0.4 * room_v )
    furniture = np.clip( tall * 0.8 + low * 0.5, 0, 1 )
    lights = np.zeros( ( n, n ), np.float32 )
    for k in range( len( bands ) ):
        cx = ( bands[k] - widths[k] / widths.sum() * tile * 0.5 ) % tile
        dxl = ( x - cx + tile / 2 ) % tile - tile / 2
        lights = np.maximum( lights, np.exp( -( dxl / 9.0 ) ** 2 ) * np.exp( -( ( up - 0.9 ) / 0.035 ) ** 2 ) * rng.uniform( 0.5, 1.0 ) )
    if lit:
        wall = lin3( ( 222, 196, 158 ) ) * ( 0.7 + 0.2 * room_v + 0.25 * up )[..., None]
        room = wall * ( 1 - 0.7 * furniture )[..., None] + lin3( ( 255, 244, 222 ) ) * lights[..., None]
        slats = lin3( ( 226, 210, 182 ) ) * ( 0.6 + 0.4 * gap )[..., None]
        c = mix( room, slats, blind[..., None] )
        illum = ( 0.4 + 0.3 * room_v + 0.3 * up ) * ( 1 - 0.65 * furniture ) + lights
        illum = mix( illum, 0.3 + 0.45 * gap, blind )
    else:
        room = lin3( ( 30, 32, 34 ) ) * ( 0.7 + 0.25 * room_v + 0.4 * up )[..., None] * ( 1 - 0.45 * furniture )[..., None]
        room += lin3( ( 70, 70, 68 ) ) * lights[..., None] * 0.15
        slats = lin3( ( 78, 80, 82 ) ) * ( 0.5 + 0.3 * gap )[..., None]
        c = mix( room, slats, blind[..., None] )
        illum = None
    # The glass: dried rain spots and runs, a little rougher; float glass's faint waviness in the normals.
    spots = splat( n, tile, rng.uniform( 0, tile, ( 1800, 2 ) ), rng.uniform( 0.3, 1.0, 1800 ), 0.12, soft )
    src = ( rng.random( ( n, n ) ) < 0.0006 ).astype( np.float32 )
    rain = np.clip( streaks( blur( src, ( 0.5, 1.0 ) ) * 6, ppi, ( ( 3.0, 0.5 ), ( 9.0, 0.5 ) ), 2.0 ), 0, 1 )
    marks = np.clip( spots * 0.8 + rain * 0.6, 0, 1 )
    r = 0.04 + 0.1 * marks
    c = c + lin3( ( 120, 118, 110 ) ) * marks[..., None] * 0.06
    h = 0.003 * nz( 3.0, 40, 10 )
    s = dict( colour=c.astype( np.float32 ), rough=r.astype( np.float32 ), height=h, ppi=ppi )
    if lit:
        s.update( illum=np.clip( illum, 0, 1 ), illum_brightness=4.0, illum_tint=( 1.0, 0.92, 0.8 ) )
    return s


def grime_decal( seed, kind, n=None ):
    """ Blended (F_TRANSLUCENT) grime to lay over a wall on a quad of its own, its UVs 0-1 up it (u may run past 1 along
    the wall: it repeats sideways). foot: the bottom 4 ft of a wall after rain (2048 x 512 = 192 x 48 in): splashback
    mud and wet darkening strongest at the ground, green-black algae in its lowest inches, fading up in a ragged edge.
    top: grime running down 8 ft from a roof's or a ledge's edge (2048 x 1024 = 192 x 96 in) in fingers of all widths. """
    rng = np.random.default_rng( seed )
    W = n or px( 2048 )
    H = W // 4 if kind == "foot" else W // 2
    tile_w = 192.0
    ppi = W / tile_w
    tall = H / ppi
    y, xg = np.mgrid[0:H, 0:W].astype( np.float32 )
    up = ( H - y ) / ppi                                   # inches above the decal's foot
    def nz( beta, longest, shortest=None ):
        return BM.noise( rng, ( H, W ), ( ppi, ppi ), beta, longest, shortest )
    if kind == "foot":
        # Damp drawn up from the ground, its top a soft wavy line with a faint tide mark; splashback specks thickest
        # at the foot; a thin band of algae in the lowest inches.
        edge = 15.0 + 5.0 * nz( 2.2, 80, 6 ) + 1.2 * nz( 1.2, 4, 0.4 )
        damp = smoothstep( edge, edge - 7.0, up ) * 0.42
        tide = np.exp( -( ( up - edge + 1.0 ) / 0.6 ) ** 2 ) * 0.18
        specks = np.zeros( ( H, W ), np.float32 )
        for radius, count in ( ( 0.05, 9000 ), ( 0.1, 3000 ), ( 0.18, 600 ) ):
            px_ = rng.uniform( 0, tile_w, count )
            pz_ = np.abs( rng.exponential( 4.0, count ) )
            keep = pz_ < tall
            img = np.zeros( ( H, W ), np.float32 )
            np.add.at( img, ( np.clip( ( H - pz_[keep] * ppi ).astype( int ), 0, H - 1 ), ( px_[keep] * ppi ).astype( int ) % W ),
                       rng.uniform( 0.5, 1.0, keep.sum() ).astype( np.float32 ) )
            specks += np.clip( blur( img, radius * ppi ) * ( radius * ppi ) ** 2 * 6.0, 0, 1 )
        specks = np.clip( specks, 0, 1 )
        algae = smoothstep( 4.0, 0.5, up + 1.2 * nz( 1.6, 10, 1 ) ) * smoothstep( -0.6, 1.0, nz( 1.8, 30, 2 ) )
        a = np.clip( damp + tide + specks * 0.75 + algae * 0.6, 0, 0.9 )
        c = lin3( ( 44, 44, 42 ) ) * np.ones( ( H, W, 3 ), np.float32 )
        c = mix( c, lin3( ( 92, 82, 66 ) ), ( specks / np.maximum( a, 1e-3 ) * 0.75 ).clip( 0, 1 )[..., None] )
        c = mix( c, lin3( ( 38, 46, 32 ) ), algae[..., None] * 0.8 )
        r = 0.5 - 0.15 * smoothstep( 10, 0, up ) - 0.1 * algae + 0.2 * specks
        h = 0.01 * specks
    else:
        src = np.zeros( ( H, W ), np.float32 )
        along = smoothstep( -0.6, 1.2, nz( 1.2, 30, 0.8 ) ) * ( 0.4 + 0.6 * smoothstep( -1.2, 1.2, nz( 1.0, 3, 0.3 ) ) )
        src[:4] = along[:4]
        twice = np.concatenate( [ src, np.zeros_like( src ) ], 0 )
        fingers = blur( rng.standard_normal( ( 2 * H, W ) ).astype( np.float32 ), ( 20 * ppi * 0.25, 0.4 * ppi ) )
        fingers = smoothstep( -1.0, 1.0, fingers / ( fingers.std() + 1e-6 ) )
        out = np.zeros( ( H, W ), np.float32 )
        for length, share in ( ( 10.0, 0.4 ), ( 30.0, 0.35 ), ( 80.0, 0.25 ) ):
            aa = math.exp( -1.0 / ( length * ppi ) )
            out += share * ( signal.lfilter( [ 1.0 - aa ], [ 1.0, -aa ], twice, axis=0 )[:H] / ( 1.0 - aa ** 4 ) )
        a = np.clip( out, 0, 1 ) * ( 0.25 + 0.75 * fingers[:H] )
        a = np.clip( a * 1.3, 0, 0.9 )
        c = lin3( ( 62, 60, 54 ) ) * ( 1.0 + 0.15 * nz( 1.2, 6, 0.3 ) )[..., None]
        c = mix( c, lin3( ( 44, 48, 38 ) ), smoothstep( 0.3, 1.5, nz( 1.8, 30, 2 ) )[..., None] * 0.5 )
        r = 0.7 - 0.1 * a
        h = np.zeros( ( H, W ), np.float32 )
    return dict( colour=c.astype( np.float32 ), rough=np.clip( r, 0.2, 0.9 ).astype( np.float32 ), height=h.astype( np.float32 ),
                 ppi=ppi, trans=np.clip( a, 0, 1 ).astype( np.float32 ) )


PUDDLES = { "a": ( 0, 0, 512, 512 ), "b": ( 512, 0, 512, 512 ), "c": ( 0, 512, 512, 512 ), "d": ( 512, 512, 512, 512 ) }


def puddle_atlas( seed=241, n=None ):
    """ Four puddles (2 x 2, PUDDLES' pixel boxes in a 1024 atlas), alpha-tested, for a yard to lay where water would
    stand (by a drain, in a dip): near-mirror water (rough 0.03) over dark wet concrete, flat, the shape irregular. A quad
    of the region's aspect, a little over the ground, UVs from RM.atlas_uv( RM.PUDDLES, ( 1024, 1024 ), name, s, t ). """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    half = n // 2
    alpha = np.zeros( ( n, n ), np.float32 )
    for k in range( 4 ):
        oy, ox = ( k // 2 ) * half, ( k % 2 ) * half
        yy, xx = np.mgrid[0:half, 0:half].astype( np.float32 ) / half * 2 - 1
        f = np.zeros( ( half, half ), np.float32 )
        for _ in range( 4 ):
            cx, cy = rng.uniform( -0.4, 0.4, 2 )
            sx, sy = rng.uniform( 0.25, 0.55, 2 )
            f += np.exp( -( ( xx - cx ) ** 2 / sx ** 2 + ( yy - cy ) ** 2 / sy ** 2 ) )
        f += 0.12 * BM.noise( rng, ( half, half ), ( half / 40, half / 40 ), 1.8, 20, 0.4 )
        f *= smoothstep( 1.0, 0.8, np.maximum( np.abs( xx ), np.abs( yy ) ) )
        alpha[oy:oy + half, ox:ox + half] = smoothstep( 0.55, 0.6, f )
    c = lin3( ( 40, 40, 40 ) ) * np.ones( ( n, n, 3 ), np.float32 )
    r = np.full( ( n, n ), 0.03, np.float32 )
    h = np.zeros( ( n, n ), np.float32 )
    return dict( colour=c, rough=r, height=h, ppi=n / 96.0, alpha=alpha )


# Rooms behind windows, on shaders/belltower_window.shader (glass over an interior traced in the shader: the back wall
# is the picture, the side walls, floor and ceiling the shared wall picture). Each needs its window quad's UVs 0-1 across
# it, ( 0, 0 ) bottom left: P.quad( m, "rv_window_office", centre, right, UP, w, h, uv=ROOM_UVS ). On planar UVs it
# breaks: use rv_window_dark / rv_window_lit there. name -> ( back wall, room depth in, brightness dark, brightness lit )
ROOMS = { "office": ( "rv_room_office", 40, 0.12, 0.5 ), "plant": ( "rv_room_plant", 90, 0.1, 0.42 ),
          "corridor": ( "rv_room_corridor", 60, 0.12, 0.5 ) }
ROOM_UVS = [ ( 0.0, 0.0 ), ( 1.0, 0.0 ), ( 1.0, 1.0 ), ( 0.0, 1.0 ) ]


def room_picture( kind, n=None ):
    """ A room's back wall as seen face on through the window (sRGB, square): an office, a plant room, a corridor drawn
    in one-point perspective. """
    n = n or px( 1024 )
    ss = 2
    N = n * ss
    img = Image.new( "RGB", ( N, N ), ( 0, 0, 0 ) )
    d = ImageDraw.Draw( img )
    rng = np.random.default_rng( { "office": 1, "plant": 2, "corridor": 3, "wall": 4 }[kind] )
    S = lambda *v: tuple( int( a * N ) for a in v )
    if kind == "office":
        d.rectangle( S( 0, 0, 1, 1 ), fill=( 196, 192, 182 ) )
        d.rectangle( S( 0, 0.9, 1, 1 ), fill=( 96, 100, 96 ) )
        d.rectangle( S( 0, 0.885, 1, 0.9 ), fill=( 70, 70, 70 ) )
        d.rectangle( S( 0.06, 0.22, 0.4, 0.5 ), fill=( 232, 232, 228 ), outline=( 150, 150, 150 ), width=int( 0.006 * N ) )
        for k in range( 9 ):
            y0 = 0.27 + 0.025 * k
            d.line( S( 0.09, y0, 0.09 + rng.uniform( 0.1, 0.27 ), y0 ), fill=( 60, 90, 150 ) if k % 3 else ( 170, 50, 50 ), width=int( 0.004 * N ) )
        d.rectangle( S( 0.48, 0.25, 0.64, 0.45 ), fill=( 150, 110, 70 ) )
        for k in range( 6 ):
            x0, y0 = 0.49 + rng.uniform( 0, 0.11 ), 0.26 + rng.uniform( 0, 0.14 )
            d.rectangle( S( x0, y0, x0 + 0.035, y0 + 0.045 ), fill=( 240, 238, 228 ) if k % 2 else ( 240, 220, 120 ) )
        d.ellipse( S( 0.7, 0.18, 0.76, 0.24 ), fill=( 236, 236, 236 ), outline=( 40, 40, 40 ), width=int( 0.005 * N ) )
        for i in range( 3 ):
            d.rectangle( S( 0.04 + 0.09 * i, 0.58, 0.12 + 0.09 * i, 0.885 ), fill=( 140, 146, 150 ), outline=( 100, 104, 108 ), width=int( 0.004 * N ) )
            for j in range( 3 ):
                d.line( S( 0.06 + 0.09 * i, 0.64 + 0.085 * j, 0.1 + 0.09 * i, 0.64 + 0.085 * j ), fill=( 90, 94, 98 ), width=int( 0.006 * N ) )
        d.rectangle( S( 0.36, 0.66, 0.9, 0.7 ), fill=( 120, 104, 84 ) )
        d.rectangle( S( 0.38, 0.7, 0.4, 0.885 ), fill=( 70, 70, 74 ) )
        d.rectangle( S( 0.86, 0.7, 0.88, 0.885 ), fill=( 70, 70, 74 ) )
        d.rectangle( S( 0.5, 0.5, 0.66, 0.64 ), fill=( 30, 32, 36 ) )
        d.rectangle( S( 0.51, 0.51, 0.65, 0.63 ), fill=( 40, 80, 120 ) )
        d.rectangle( S( 0.56, 0.64, 0.6, 0.66 ), fill=( 30, 32, 36 ) )
        d.rectangle( S( 0.7, 0.53, 0.84, 0.64 ), fill=( 30, 32, 36 ) )
        d.rectangle( S( 0.71, 0.54, 0.83, 0.63 ), fill=( 50, 90, 70 ) )
        d.rounded_rectangle( S( 0.6, 0.6, 0.7, 0.72 ), radius=int( 0.015 * N ), fill=( 44, 46, 54 ) )
        d.rectangle( S( 0.59, 0.74, 0.71, 0.765 ), fill=( 40, 42, 50 ) )
        d.rectangle( S( 0.645, 0.765, 0.655, 0.86 ), fill=( 60, 62, 66 ) )
        d.line( S( 0.6, 0.875, 0.7, 0.875 ), fill=( 60, 62, 66 ), width=int( 0.01 * N ) )
    elif kind == "plant":
        d.rectangle( S( 0, 0, 1, 1 ), fill=( 146, 146, 142 ) )
        d.rectangle( S( 0, 0.55, 1, 0.9 ), fill=( 104, 120, 108 ) )
        d.rectangle( S( 0, 0.54, 1, 0.555 ), fill=( 210, 168, 30 ) )
        d.rectangle( S( 0, 0.9, 1, 1 ), fill=( 90, 92, 90 ) )
        d.rectangle( S( 0, 0.05, 1, 0.09 ), fill=( 120, 122, 124 ) )
        for y0, r_, col in ( ( 0.2, 0.06, ( 186, 188, 190 ) ), ( 0.36, 0.04, ( 70, 110, 160 ) ) ):
            for k in range( 12 ):
                t = k / 11
                shade = int( 60 * ( 1 - abs( 2 * t - 1 ) ) )
                d.rectangle( S( 0, y0 - r_ + 2 * r_ * t, 1, y0 - r_ + 2 * r_ * ( t + 1 / 11 ) ), fill=tuple( max( 0, min( 255, c - 50 + shade ) ) for c in col ) )
            for xx in ( 0.15, 0.55, 0.85 ):
                d.rectangle( S( xx, y0 - r_ - 0.008, xx + 0.012, y0 + r_ + 0.008 ), fill=( 120, 124, 126 ) )
        for k in range( 10 ):
            t = k / 9
            shade = int( 60 * ( 1 - abs( 2 * t - 1 ) ) )
            d.rectangle( S( 0.28 + 0.06 * t, 0.36, 0.28 + 0.06 * ( t + 1 / 9 ), 0.9 ), fill=( 126 + shade, 128 + shade, 130 + shade ) )
        d.ellipse( S( 0.255, 0.55, 0.365, 0.66 ), outline=( 190, 40, 30 ), width=int( 0.012 * N ) )
        d.line( S( 0.31, 0.55, 0.31, 0.66 ), fill=( 190, 40, 30 ), width=int( 0.008 * N ) )
        d.rectangle( S( 0.5, 0.48, 0.74, 0.88 ), fill=( 150, 154, 152 ), outline=( 100, 104, 104 ), width=int( 0.005 * N ) )
        d.line( S( 0.62, 0.48, 0.62, 0.88 ), fill=( 100, 104, 104 ), width=int( 0.004 * N ) )
        for k in range( 4 ):
            d.rectangle( S( 0.53, 0.52 + 0.04 * k, 0.58, 0.54 + 0.04 * k ), fill=( 230, 230, 226 ) )
            d.ellipse( S( 0.66, 0.52 + 0.04 * k, 0.68, 0.54 + 0.04 * k ), fill=( 60, 200, 90 ) if k else ( 220, 60, 40 ) )
        d.rectangle( S( 0.78, 0.72, 0.96, 0.88 ), fill=( 50, 96, 110 ) )
        d.ellipse( S( 0.82, 0.66, 0.92, 0.78 ), fill=( 56, 104, 118 ) )
        d.rectangle( S( 0.76, 0.88, 0.98, 0.9 ), fill=( 60, 60, 62 ) )
        d.rectangle( S( 0.04, 0.6, 0.12, 0.7 ), fill=( 222, 186, 40 ) )
    elif kind == "corridor":
        end = ( 0.38, 0.33, 0.62, 0.6 )
        d.rectangle( S( 0, 0, 1, 1 ), fill=( 186, 182, 170 ) )
        d.polygon( [ S( 0, 1 ), S( 1, 1 ), S( end[2], end[3] ), S( end[0], end[3] ) ], fill=( 118, 124, 118 ) )
        d.polygon( [ S( 0, 0 ), S( 1, 0 ), S( end[2], end[1] ), S( end[0], end[1] ) ], fill=( 214, 212, 206 ) )
        d.polygon( [ S( 0, 0 ), S( end[0], end[1] ), S( end[0], end[3] ), S( 0, 1 ) ], fill=( 176, 170, 158 ) )
        d.polygon( [ S( 1, 0 ), S( end[2], end[1] ), S( end[2], end[3] ), S( 1, 1 ) ], fill=( 168, 162, 150 ) )
        d.rectangle( S( *end ), fill=( 150, 146, 136 ) )
        d.rectangle( S( 0.47, 0.38, 0.53, 0.6 ), fill=( 110, 92, 70 ) )
        d.rectangle( S( 0.475, 0.345, 0.525, 0.365 ), fill=( 40, 170, 90 ) )
        for k in range( 5 ):
            t0, t1 = ( k + 0.2 ) / 5.5, ( k + 0.5 ) / 5.5
            lerp = lambda a, b, t: a + ( b - a ) * t
            for side in ( 0, 1 ):
                xa0 = lerp( 0.0 if side == 0 else 1.0, end[0] if side == 0 else end[2], t0 )
                xa1 = lerp( 0.0 if side == 0 else 1.0, end[0] if side == 0 else end[2], t1 )
                d.polygon( [ S( xa0, lerp( 0.25, end[1] + 0.06, t0 ) ), S( xa1, lerp( 0.25, end[1] + 0.06, t1 ) ),
                             S( xa1, lerp( 1.0, end[3], t1 ) ), S( xa0, lerp( 1.0, end[3], t0 ) ) ], fill=( 112, 96, 76 ) if side else ( 96, 104, 112 ) )
            ya, yb = lerp( 0.0, end[1], t0 ), lerp( 0.0, end[1], t1 )
            d.polygon( [ S( lerp( 0.3, 0.46, t0 ), ya ), S( lerp( 0.7, 0.54, t0 ), ya ), S( lerp( 0.7, 0.54, t1 ), yb ), S( lerp( 0.3, 0.46, t1 ), yb ) ],
                       fill=( 255, 250, 236 ) )
    else:
        d.rectangle( S( 0, 0, 1, 1 ), fill=( 190, 186, 176 ) )
        for k in range( 1, 8 ):
            d.line( S( 0, k / 8, 1, k / 8 ), fill=( 170, 166, 156 ), width=int( 0.004 * N ) )
            off = 0.0 if k % 2 else 0.25
            for i in range( 3 ):
                d.line( S( off + 0.5 * i, ( k - 1 ) / 8, off + 0.5 * i, k / 8 ), fill=( 170, 166, 156 ), width=int( 0.004 * N ) )
    img = img.resize( ( n, n ), Image.LANCZOS )
    a = np.asarray( img, np.float32 )
    yy, xx = np.mgrid[0:n, 0:n].astype( np.float32 ) / n
    light = 0.82 + 0.18 * ( 1 - yy ) - 0.25 * ( ( xx - 0.5 ) ** 2 + ( yy - 0.45 ) ** 2 ) * 2
    noise = BM.noise( rng, ( n, n ), ( n / 64, n / 64 ), 2.0, 20, 0.3 )
    a = a * ( light * ( 1 + 0.03 * noise ) )[..., None]
    a = ndimage.gaussian_filter( a, ( 1.2, 1.2, 0 ) )
    return np.clip( a, 0, 255 )


def room_vmat( back, wall, depth, brightness ):
    return ( '// Tools/riverdale_materials.py: a room behind glass (Belltower\'s window shader); its quad needs UVs 0-1\n'
             '"Layer0"\n{\n    shader "shaders/belltower_window.shader"\n'
             f'    TextureRoomBack "{back}"\n    TextureRoomWall "{wall}"\n'
             f'    g_flRoomDepth "{depth}"\n    g_flInteriorBrightness "{brightness:.2f}"\n}}\n' )


def fabric( seed=201, colour=( 56, 58, 64 ), tile=24.0, n=None ):
    """ Woven upholstery, as an operator's chair is covered in: a plain weave of slightly varying yarns, pilled and a
    little shiny where it's sat on. """
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    p = tile / round( tile / 0.16 )
    wx, wz = np.sin( 2 * math.pi * x / p ), np.sin( 2 * math.pi * z / p )
    over = ( np.sign( np.sin( math.pi * x / p ) * np.sin( math.pi * z / p ) ) * 0.5 + 0.5 )
    yarn = blur( over * np.abs( wz ) + ( 1 - over ) * np.abs( wx ), 0.6 )
    c = lin3( colour ) * ( 1.0 + 0.06 * ( yarn - 0.5 ) + 0.05 * nz( 2.0, 6, 0.5 ) + 0.03 * nz( 0.5, 0.3, 0.12 ) )[..., None]
    h = 0.0012 * yarn
    worn = smoothstep( 0.4, 1.8, nz( 2.6, tile, 4 ) )
    r = 0.88 - 0.12 * worn
    c *= ( 1.0 + 0.05 * worn )[..., None]
    return dict( colour=c.astype( np.float32 ), rough=r.astype( np.float32 ), height=h, ppi=ppi )


# ---------------------------------------------------------------------------------------------------------------------
# Lettering and the logo (alpha atlas): white on transparent; two materials tint it dark or light.

LETTER_ATLAS = ( 4096, 4096 )
# name -> ( x, y, w, h ) in pixels
LETTERS = {
    "A1": ( 0, 0, 1024, 640 ), "A2": ( 1024, 0, 1024, 640 ), "B1": ( 2048, 0, 1024, 640 ), "B2": ( 3072, 0, 1024, 640 ),
    "reactor_hall_r": ( 0, 640, 1024, 512 ), "reactor_hall_l": ( 1024, 640, 1024, 512 ),
    "turbine_r": ( 2048, 640, 1024, 512 ), "turbine_l": ( 3072, 640, 1024, 512 ),
    "clean_energy": ( 0, 1152, 1536, 896 ), "safety": ( 1536, 1152, 1024, 896 ),
    "logo": ( 2560, 1152, 896, 896 ), "n02": ( 3456, 1152, 640, 448 ), "n04": ( 3456, 1600, 640, 448 ),
    "wordmark": ( 0, 2048, 1280, 640 ), "logo_wordmark": ( 1280, 2048, 2816, 640 ),
    "water_purification": ( 0, 2688, 1536, 896 ), "swl": ( 1536, 2688, 1280, 256 ),
    "unit_text": ( 2816, 2688, 1280, 256 ), "pool_level": ( 1536, 2944, 1280, 256 ),
    "fuel_handling": ( 2816, 2944, 1280, 256 ), "C1": ( 0, 3584, 1024, 512 ),
    "control_room": ( 1024, 3584, 1536, 256 ), "turbine_hall": ( 1024, 3840, 1536, 256 ), "unit1": ( 2560, 3200, 768, 896 ),
    "unit2": ( 3328, 3200, 768, 896 ),
}


def font( size, light=False ):
    return ImageFont.truetype( str( FONT_LIGHT if light else FONT ), max( 6, int( size ) ) )


def text_block( draw, box, lines, fill=255, align="left", light=False, spacing=0.22, track=0.06, pad=0.08 ):
    """ Lines of capitals fitted into box ( x, y, w, h ), as large as fit. """
    x, y, w, h = box
    iw, ih = w * ( 1 - 2 * pad ), h * ( 1 - 2 * pad )
    size = ih / ( len( lines ) + spacing * ( len( lines ) - 1 ) ) / 0.72
    for _ in range( 40 ):
        f = font( size, light )
        widths = [ sum( f.getlength( ch ) for ch in ln ) + track * size * ( len( ln ) - 1 ) for ln in lines ]
        if max( widths ) <= iw:
            break
        size *= 0.95
    cap = 0.72 * size
    total = cap * len( lines ) + spacing * cap * ( len( lines ) - 1 )
    top = y + ( h - total ) / 2
    for k, ( ln, lw ) in enumerate( zip( lines, widths ) ):
        if align == "left":
            cx = x + w * pad
        elif align == "right":
            cx = x + w * ( 1 - pad ) - lw
        else:
            cx = x + ( w - lw ) / 2
        cy = top + k * cap * ( 1 + spacing ) - 0.26 * size
        for ch in ln:
            draw.text( ( cx, cy ), ch, font=f, fill=fill )
            cx += f.getlength( ch ) + track * size


def logo( draw, box, size, fill=255 ):
    """ Riverdale Nuclear's mark: a solid triangle, cut through by an orbit ring, a stem from the apex and a core. Draws
    the triangle and returns the cuts (a mask the size of the atlas). """
    x, y, w, h = box
    s = min( w, h ) * 0.9
    cx, base = x + w / 2, y + ( h + s * 0.866 ) / 2
    top = base - s * 0.866
    draw.polygon( [ ( cx, top ), ( cx + s / 2, base ), ( cx - s / 2, base ) ], fill=fill )
    ring = Image.new( "L", size, 0 )
    rd = ImageDraw.Draw( ring )
    w_ = max( 2, int( s * 0.05 ) )
    # An A: a notch up from the base's middle between its legs...
    rd.polygon( [ ( cx - s * 0.15, base + 2 ), ( cx + s * 0.15, base + 2 ), ( cx, base - s * 0.30 ) ], fill=255 )
    # ...and a swoosh sweeping up across it from the left edge to the right: an orbit seen edge-on.
    rd.arc( ( cx - s * 0.62, base - s * 0.62, cx + s * 0.38, base - s * 0.12 ), 250, 340, fill=255, width=w_ )
    rd.arc( ( cx - s * 0.55, base - s * 0.50, cx + s * 0.45, base - s * 0.02 ), 255, 335, fill=255, width=max( 2, w_ // 2 ) )
    return ring


def letters_atlas():
    W, H = px( LETTER_ATLAS[0] ), px( LETTER_ATLAS[1] )
    k = W / LETTER_ATLAS[0]
    img = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( img )
    cuts = Image.new( "L", ( W, H ), 0 )

    def box( name ):
        x, y, w, h = LETTERS[name]
        return ( x * k, y * k, w * k, h * k )

    for name in ( "A1", "A2", "B1", "B2" ):
        text_block( d, box( name ), [ name ], align="center", track=0.02, pad=0.06 )
    text_block( d, box( "reactor_hall_r" ), [ "> REACTOR", "  HALL" ], align="left" )
    text_block( d, box( "reactor_hall_l" ), [ "REACTOR <", "HALL  " ], align="right" )
    text_block( d, box( "turbine_r" ), [ "TURBINE", "BUILDING >" ], align="left" )
    text_block( d, box( "turbine_l" ), [ "TURBINE", "< BUILDING" ], align="right" )
    text_block( d, box( "clean_energy" ), [ "CLEAN ENERGY", "A BRIGHTER", "TOMORROW" ], align="left", light=True, track=0.12 )
    text_block( d, box( "safety" ), [ "SAFETY", "PEOPLE", "PROGRESS" ], align="left", light=True, track=0.12 )
    ring = logo( d, box( "logo" ), ( W, H ) )
    cuts.paste( ring, ( 0, 0 ), ring )
    text_block( d, box( "n02" ), [ "02" ], align="center", track=0.02 )
    text_block( d, box( "n04" ), [ "04" ], align="center", track=0.02 )
    text_block( d, box( "wordmark" ), [ "RIVERDALE", "NUCLEAR" ], align="center", track=0.08 )
    x, y, w, h = box( "logo_wordmark" )
    lb = ( x, y, h, h )
    ring = logo( d, lb, ( W, H ) )
    cuts.paste( ring, ( 0, 0 ), ring )
    text_block( d, ( x + h * 1.02, y, w - h * 1.02, h ), [ "RIVERDALE", "NUCLEAR" ], align="left", track=0.08, pad=0.1 )
    text_block( d, box( "water_purification" ), [ "WATER", "PURIFICATION", "SYSTEM" ], align="center", track=0.06 )
    text_block( d, box( "swl" ), [ "SWL 125 T" ], align="center", track=0.1 )
    text_block( d, box( "unit_text" ), [ "UNIT 1" ], align="center", track=0.1 )
    text_block( d, box( "pool_level" ), [ "SPENT FUEL POOL" ], align="center", track=0.1 )
    text_block( d, box( "fuel_handling" ), [ "FUEL HANDLING" ], align="center", track=0.1 )
    text_block( d, box( "C1" ), [ "C1" ], align="center", track=0.02, pad=0.06 )
    text_block( d, box( "control_room" ), [ "CONTROL ROOM" ], align="center", track=0.1 )
    text_block( d, box( "turbine_hall" ), [ "TURBINE HALL" ], align="center", track=0.1 )
    text_block( d, box( "unit1" ), [ "UNIT", "1" ], align="center" )
    text_block( d, box( "unit2" ), [ "UNIT", "2" ], align="center" )
    a = np.asarray( img, np.float32 ) / 255.0
    a = a * ( 1.0 - np.asarray( cuts, np.float32 ) / 255.0 )
    rng = np.random.default_rng( 5 )
    wear = BM.noise( rng, a.shape, ( k * 8, k * 8 ), 1.6, 40, 0.5 )
    a *= 1.0 - smoothstep( 1.8, 2.6, wear )
    return a


# ---------------------------------------------------------------------------------------------------------------------
# Plates: opaque signs

PLATE_ATLAS = ( 2048, 2048 )
PLATES = {
    "caution": ( 0, 0, 640, 768 ), "unit1": ( 640, 0, 448, 1024 ), "unit2": ( 1088, 0, 448, 1024 ),
    "door_sign": ( 1536, 0, 256, 320 ), "clipboard": ( 1792, 0, 256, 352 ), "exit": ( 1536, 320, 512, 192 ),
    "lifering_sign": ( 1536, 512, 256, 256 ), "notice": ( 1792, 512, 256, 352 ), "danger": ( 0, 768, 640, 384 ),
    "red": ( 0, 1152, 256, 256 ), "yellow": ( 256, 1152, 256, 256 ), "board": ( 640, 1024, 896, 512 ),
}


def trefoil( d, cx, cy, r, fill ):
    d.ellipse( ( cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18 ), fill=fill )
    for k in range( 3 ):
        a0 = -90 + 120 * k - 30
        d.pieslice( ( cx - r, cy - r, cx + r, cy + r ), a0, a0 + 60, fill=fill )
    hole = r * 0.3
    return hole


def plates_atlas():
    W, H = px( PLATE_ATLAS[0] ), px( PLATE_ATLAS[1] )
    k = W / PLATE_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 60, 60, 60 ) )
    d = ImageDraw.Draw( img )

    def box( name ):
        x, y, w, h = PLATES[name]
        return ( x * k, y * k, w * k, h * k )

    yellow, black, red, white = ( 232, 186, 30 ), ( 22, 22, 22 ), ( 156, 30, 26 ), ( 236, 236, 230 )
    x, y, w, h = box( "caution" )
    d.rectangle( ( x, y, x + w, y + h ), fill=yellow )
    d.rectangle( ( x + w * 0.04, y + w * 0.04, x + w * 0.96, y + h - w * 0.04 ), outline=black, width=int( w * 0.03 ) )
    text_block( d, ( x, y + h * 0.04, w, h * 0.2 ), [ "CAUTION" ], fill=black, align="center", track=0.04 )
    cx, cy, r = x + w / 2, y + h * 0.47, w * 0.26
    d.ellipse( ( cx - r * 1.12, cy - r * 1.12, cx + r * 1.12, cy + r * 1.12 ), fill=black )
    d.ellipse( ( cx - r * 1.02, cy - r * 1.02, cx + r * 1.02, cy + r * 1.02 ), fill=yellow )
    trefoil( d, cx, cy, r * 0.92, black )
    d.ellipse( ( cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3 ), fill=yellow )
    d.ellipse( ( cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18 ), fill=black )
    text_block( d, ( x, y + h * 0.74, w, h * 0.2 ), [ "RADIATION AREA" ], fill=black, align="center", track=0.02 )
    for name, num in ( ( "unit1", "1" ), ( "unit2", "2" ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=red )
        d.rectangle( ( x + w * 0.05, y + w * 0.05, x + w * 0.95, y + h - w * 0.05 ), outline=( 120, 22, 20 ), width=int( w * 0.012 ) )
        text_block( d, ( x, y + h * 0.12, w, h * 0.12 ), [ "UNIT" ], fill=white, align="center" )
        text_block( d, ( x, y + h * 0.26, w, h * 0.22 ), [ num ], fill=white, align="center" )
    x, y, w, h = box( "door_sign" )
    d.rectangle( ( x, y, x + w, y + h ), fill=yellow )
    d.rectangle( ( x + 6 * k, y + 6 * k, x + w - 6 * k, y + h - 6 * k ), outline=black, width=int( 6 * k ) )
    cx = x + w / 2
    d.ellipse( ( cx - w * 0.1, y + h * 0.22, cx + w * 0.1, y + h * 0.22 + w * 0.2 ), fill=black )
    d.polygon( [ ( cx - w * 0.18, y + h * 0.75 ), ( cx - w * 0.12, y + h * 0.42 ), ( cx + w * 0.12, y + h * 0.42 ), ( cx + w * 0.18, y + h * 0.75 ) ], fill=black )
    x, y, w, h = box( "clipboard" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 120, 84, 48 ) )
    d.rectangle( ( x + w * 0.08, y + h * 0.1, x + w * 0.92, y + h * 0.96 ), fill=( 236, 234, 226 ) )
    for j in range( 14 ):
        yy = y + h * ( 0.2 + 0.052 * j )
        d.line( ( x + w * 0.14, yy, x + w * ( 0.86 if j % 3 else 0.6 ), yy ), fill=( 90, 90, 100 ), width=max( 1, int( 2 * k ) ) )
    d.rectangle( ( x + w * 0.3, y + h * 0.02, x + w * 0.7, y + h * 0.12 ), fill=( 160, 160, 164 ) )
    x, y, w, h = box( "exit" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 26, 140, 70 ) )
    text_block( d, ( x, y, w, h ), [ "EXIT" ], fill=white, align="center", track=0.12 )
    x, y, w, h = box( "lifering_sign" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 26, 120, 70 ) )
    d.ellipse( ( x + w * 0.2, y + h * 0.2, x + w * 0.8, y + h * 0.8 ), outline=white, width=int( w * 0.1 ) )
    x, y, w, h = box( "notice" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 230, 230, 224 ) )
    d.rectangle( ( x, y, x + w, y + h * 0.2 ), fill=( 30, 80, 150 ) )
    for j in range( 10 ):
        yy = y + h * ( 0.3 + 0.06 * j )
        d.line( ( x + w * 0.1, yy, x + w * 0.9, yy ), fill=( 110, 110, 116 ), width=max( 1, int( 3 * k ) ) )
    x, y, w, h = box( "danger" )
    d.rectangle( ( x, y, x + w, y + h ), fill=white )
    d.rectangle( ( x, y, x + w, y + h * 0.36 ), fill=( 190, 24, 24 ) )
    text_block( d, ( x, y, w, h * 0.36 ), [ "DANGER" ], fill=white, align="center", track=0.06 )
    text_block( d, ( x, y + h * 0.4, w, h * 0.56 ), [ "AUTHORISED", "PERSONNEL ONLY" ], fill=black, align="center" )
    for name, col in ( ( "red", red ), ( "yellow", yellow ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=col )
    x, y, w, h = box( "board" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 236, 236, 232 ) )
    d.rectangle( ( x, y, x + w, y + h * 0.18 ), fill=( 40, 46, 54 ) )
    text_block( d, ( x, y, w, h * 0.18 ), [ "DAYS WITHOUT A LOST-TIME INCIDENT" ], fill=white, align="center", track=0.04 )
    text_block( d, ( x, y + h * 0.24, w, h * 0.6 ), [ "1462" ], fill=( 30, 110, 60 ), align="center" )
    c = np.asarray( img, np.float32 )
    rng = np.random.default_rng( 9 )
    dirt = smoothstep( 0.2, 2.4, BM.noise( rng, c.shape[:2], ( k * 4, k * 4 ), 2.2, 60, 1 ) )
    c = c * ( 1.0 - 0.18 * dirt[..., None] )
    rough = 0.5 + 0.2 * dirt
    return c, rough


# ---------------------------------------------------------------------------------------------------------------------
# Screens: the control room's monitors (self-lit)

SCREEN_ATLAS = ( 2048, 1024 )
SCREENS = { "schematic": ( 0, 0, 1024, 576 ), "graphs": ( 1024, 0, 1024, 576 ), "table": ( 0, 576, 768, 448 ),
            "camera": ( 768, 576, 768, 448 ), "panel": ( 1536, 576, 512, 448 ) }


def screens_atlas():
    W, H = px( SCREEN_ATLAS[0] ), px( SCREEN_ATLAS[1] )
    k = W / SCREEN_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 6, 12, 20 ) )
    d = ImageDraw.Draw( img )
    rng = np.random.default_rng( 13 )

    def box( name ):
        x, y, w, h = SCREENS[name]
        return ( x * k, y * k, w * k, h * k )

    cyan, blue, amber, green, white = ( 60, 210, 240 ), ( 40, 110, 200 ), ( 240, 170, 40 ), ( 60, 220, 120 ), ( 210, 230, 240 )
    x, y, w, h = box( "schematic" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 8, 24, 44 ) )
    d.rectangle( ( x, y, x + w, y + h * 0.08 ), fill=( 20, 60, 110 ) )
    cx, cy = x + w * 0.35, y + h * 0.55
    for r in ( 0.32, 0.24, 0.12 ):
        d.ellipse( ( cx - h * r, cy - h * r, cx + h * r, cy + h * r ), outline=cyan, width=max( 1, int( 3 * k ) ) )
    for j in range( 7 ):
        for i in range( 7 ):
            if ( i - 3 ) ** 2 + ( j - 3 ) ** 2 <= 10:
                col = green if rng.random() < 0.8 else amber
                d.rectangle( ( cx + ( i - 3.5 ) * h * 0.045, cy + ( j - 3.5 ) * h * 0.045, cx + ( i - 2.6 ) * h * 0.045, cy + ( j - 2.6 ) * h * 0.045 ), fill=col )
    for j in range( 8 ):
        yy = y + h * ( 0.16 + 0.1 * j )
        d.rectangle( ( x + w * 0.66, yy, x + w * ( 0.7 + 0.25 * rng.random() ), yy + h * 0.05 ), fill=blue )
    x, y, w, h = box( "graphs" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 6, 18, 30 ) )
    for g in range( 3 ):
        gy = y + h * ( 0.08 + 0.31 * g )
        d.rectangle( ( x + w * 0.04, gy, x + w * 0.96, gy + h * 0.27 ), outline=( 30, 70, 100 ), width=max( 1, int( 2 * k ) ) )
        pts, v = [], 0.5
        for t in np.linspace( 0, 1, 60 ):
            v = np.clip( v + rng.normal( 0, 0.06 ), 0.1, 0.9 )
            pts.append( ( x + w * ( 0.05 + 0.9 * t ), gy + h * 0.27 * ( 1 - v ) ) )
        d.line( pts, fill=( cyan, green, amber )[g], width=max( 1, int( 3 * k ) ) )
    x, y, w, h = box( "table" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 10, 14, 22 ) )
    for j in range( 14 ):
        yy = y + h * ( 0.05 + 0.065 * j )
        for i in range( 4 ):
            col = white if i == 0 else ( green if rng.random() < 0.85 else amber )
            d.rectangle( ( x + w * ( 0.05 + 0.24 * i ), yy, x + w * ( 0.05 + 0.24 * i + 0.08 + 0.1 * rng.random() ), yy + h * 0.03 ), fill=col )
    x, y, w, h = box( "camera" )
    arr = np.zeros( ( int( h ), int( w ), 3 ), np.float32 )
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]] / max( arr.shape )
    pool = np.clip( 1.0 - ( ( xx - 0.5 ) ** 2 * 3 + ( yy - 0.65 ) ** 2 * 6 ), 0, 1 )
    arr[..., 0] = 20 + 20 * pool
    arr[..., 1] = 40 + 160 * pool
    arr[..., 2] = 60 + 180 * pool
    arr += rng.normal( 0, 6, arr.shape )
    img.paste( Image.fromarray( np.clip( arr, 0, 255 ).astype( np.uint8 ) ), ( int( x ), int( y ) ) )
    d.text( ( x + 8 * k, y + 8 * k ), "CAM 04  POOL", fill=white, font=font( 26 * k ) )
    x, y, w, h = box( "panel" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 40, 44, 48 ) )
    for j in range( 6 ):
        for i in range( 8 ):
            col = [ ( 200, 40, 30 ), green, amber, ( 30, 30, 34 ), white ][int( rng.integers( 0, 5 ) )]
            d.ellipse( ( x + w * ( 0.06 + 0.115 * i ), y + h * ( 0.08 + 0.15 * j ), x + w * ( 0.06 + 0.115 * i + 0.06 ), y + h * ( 0.08 + 0.15 * j + 0.08 ) ), fill=col )
    c = np.asarray( img, np.float32 )
    # Scanlines and a soft vignette per screen read as glass and pixels.
    c *= ( 0.92 + 0.08 * ( np.arange( H )[:, None, None] % 3 > 0 ) )
    return c


# ---------------------------------------------------------------------------------------------------------------------
# Writing

# Flat paints: colour (sRGB), metalness, roughness, self-illumination brightness (0 for none)
PAINTED = {
    "rv_black": ( ( 40, 40, 42 ), 0.0, 0.55, 0 ),          # black paint and plastic: no paint is darker than ~4%
    "rv_rubber": ( ( 36, 36, 36 ), 0.0, 0.82, 0 ),
    "rv_cable": ( ( 34, 34, 36 ), 0.0, 0.6, 0 ),           # PVC cable sheath
    "rv_ring_orange": ( ( 222, 92, 30 ), 0.0, 0.45, 0 ),
    "rv_ring_white": ( ( 226, 226, 220 ), 0.0, 0.45, 0 ),
    "rv_valve_red": ( ( 164, 38, 30 ), 0.0, 0.45, 0 ),      # handwheels, fire equipment
    "rv_pump_blue": ( ( 44, 86, 136 ), 0.0, 0.42, 0 ),      # pump and motor casings
    "rv_safety_green": ( ( 36, 118, 72 ), 0.0, 0.45, 0 ),   # first aid, eyewash, emergency stops' surrounds
    "rv_copper": ( ( 196, 132, 104 ), 1.0, 0.38, 0 ),       # busbars, earthing tape (metal: the colour is its F0)
    "rv_lamp_warm": ( ( 255, 214, 160 ), 0.0, 0.3, 10 ),
    "rv_lamp_cool": ( ( 220, 236, 255 ), 0.0, 0.3, 10 ),
    "rv_lamp_cyan": ( ( 90, 230, 255 ), 0.0, 0.3, 3 ),
    "rv_beacon": ( ( 255, 40, 30 ), 0.0, 0.3, 12 ),
    "rv_cyan_glow": ( ( 70, 220, 255 ), 0.0, 0.3, 2 ),
    "rv_canvas": ( ( 72, 78, 60 ), 0.0, 0.85, 0 ),
    "rv_forest": ( ( 24, 36, 26 ), 0.0, 0.9, 0 ),
    "rv_pine": ( ( 38, 58, 40 ), 0.0, 0.85, 0 ),
    "rv_pine_far": ( ( 46, 60, 58 ), 0.0, 0.9, 0 ),
    "rv_rock": ( ( 104, 100, 98 ), 0.0, 0.9, 0 ),
    "rv_rock_far": ( ( 128, 136, 150 ), 0.0, 0.9, 0 ),
    "rv_snow": ( ( 236, 240, 246 ), 0.0, 0.7, 0 ),
    "rv_grass": ( ( 70, 78, 50 ), 0.0, 0.9, 0 ),
    "rv_gravel": ( ( 110, 106, 100 ), 0.0, 0.9, 0 ),
    "rv_zinc": ( ( 166, 170, 170 ), 1.0, 0.5, 0 ),         # galvanised, flat (rv_galv is the textured one)
    "rv_porcelain": ( ( 92, 50, 34 ), 0.0, 0.22, 0 ),      # glazed brown porcelain: transformer bushings
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
          tint=( 1.0, 1.0, 1.0 ), metal_map=None, ao=None, translucent=None, backfaces=False,
          alpha_test_reference=0.5 ):
    """ complex.shader's material. metal_map (a 0-1 picture) turns on F_METALNESS_TEXTURE; translucent is a blended
    alpha picture (F_TRANSLUCENT), alpha an alpha-tested one. """
    lines = [ "// Tools/riverdale_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha:
        lines += [ '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{alpha}"',
                   f'    g_flAlphaTestReference "{alpha_test_reference:.3f}"',
                   '    g_flAntiAliasedEdgeStrength "1"' ]
    if translucent:
        lines += [ '    F_TRANSLUCENT "1"', f'    TextureTranslucency "{translucent}"' ]
    if backfaces:
        lines += [ '    F_RENDER_BACKFACES "1"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{illum}"', f'    g_flSelfIllumBrightness "{illum_brightness:.2f}"',
                   '    g_flSelfIllumAlbedoFactor "1.0"',
                   f'    g_vSelfIllumTint "[{illum_tint[0]:.6f} {illum_tint[1]:.6f} {illum_tint[2]:.6f} 0.000000]"' ]
    if metal_map:
        lines += [ '    F_METALNESS_TEXTURE "1"', f'    TextureMetalness "{metal_map}"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metalness:.2f}"', f'    TextureColor "{colour}"',
               f'    TextureNormal "{normal}"', f'    TextureRoughness "{rough}"', f'    TextureAmbientOcclusion "{ao or DEFAULT_AO}"',
               f'    g_vColorTint "[{tint[0]:.6f} {tint[1]:.6f} {tint[2]:.6f} 1.000000]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines ) + "\n"


def painted_vmat( colour, metalness, roughness, glow ):
    r, g, b = ( c / 255.0 for c in colour )
    illum = ""
    if glow:
        illum = ( '    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"\n'
                  f'    g_flSelfIllumBrightness "{glow:.2f}"\n    g_flSelfIllumAlbedoFactor "1.0"\n'
                  '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"\n' )
    return ( '// Tools/riverdale_materials.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n' + illum +
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             '    TextureColor "materials/default/default_color.tga"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             '    g_flModelTintAmount "1.0"\n}\n' )


def water_vmat():
    return ( '// Tools/riverdale_materials.py: the fuel pool\'s surface (Reef Hall\'s tank glass, looking down)\n"Layer0"\n{\n'
             '    shader "shaders/hc1_tank_glass.shader"\n'
             '    g_vWaterAbsorb "[0.004200 0.000900 0.000420 0.000000]"\n'
             '    g_flTurbidity "0.0004"\n'
             '    g_vWaterScatter "[0.030000 0.320000 0.460000 0.000000]"\n'
             '    g_vWaterDeep "[0.006000 0.100000 0.200000 0.000000]"\n'
             f'    g_flSurfaceZ "{WATER_Z:.1f}"\n'
             '    g_flDeepRange "340.0"\n'
             '    g_flMaxWater "900.0"\n'
             '    g_flCaustics "0.90"\n'
             '    g_flCausticScale "56.0"\n'
             '    g_flShafts "0.35"\n'
             '    g_flRefraction "0.0030"\n'
             '    g_flGlassRoughness "0.02"\n'
             '    g_vGlassEdge "[0.780000 0.920000 0.960000 0.000000]"\n}\n' )


def write_text( path, text ):
    for attempt in range( 40 ):
        try:
            tmp = path.with_suffix( path.suffix + ".tmp" )
            tmp.write_text( text, encoding="utf-8", newline="\n" )
            tmp.replace( path )
            return
        except PermissionError:
            import time
            time.sleep( 0.25 )
    raise PermissionError( path )


def normal_map( height, ppi ):
    return BM.normals( height, ( ppi, ppi ) )


def write_surface( out, name, colour, rough, height, ppi, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0,
                   illum_tint=( 1, 1, 1 ) ):
    srgb = T.linear_to_srgb( colour )
    save_rgb( out / f"{name}_color.jpg", srgb )
    save_rgb( out / f"{name}_normal.jpg", ( normal_map( height, ppi ) * 0.5 + 0.5 ) * 255, quality=94 )
    save_grey( out / f"{name}_rough.png", rough )
    alpha_path = illum_path = None
    if alpha is not None:
        save_grey( out / f"{name}_trans.png", alpha )
        alpha_path = f"{RESOURCE_DIR}/{name}_trans.png"
    if illum is not None:
        save_grey( out / f"{name}_illum.png", illum )
        illum_path = f"{RESOURCE_DIR}/{name}_illum.png"
    write_text( out / f"{name}.vmat", vmat( f"{RESOURCE_DIR}/{name}_color.jpg", f"{RESOURCE_DIR}/{name}_normal.jpg",
                                            f"{RESOURCE_DIR}/{name}_rough.png", metalness, alpha_path, illum_path,
                                            illum_brightness, illum_tint ) )
    print( f"wrote {name}" )
    return srgb


def write_material( out, name, s ):
    """ Writes a surface's pictures (colour JPG, the rest PNG: JPG blocks show in a glossy surface's normals) and its
    vmat, from a dict as the surfaces above return. Returns the colour (sRGB) for the contact sheet. """
    R = RESOURCE_DIR
    srgb = T.linear_to_srgb( s["colour"] )
    save_rgb( out / f"{name}_color.jpg", srgb, quality=94 )
    save_rgb( out / f"{name}_normal.png", ( wrap_normals( s["height"], s["ppi"] ) * 0.5 + 0.5 ) * 255 )
    save_grey( out / f"{name}_rough.png", np.clip( s["rough"], 0, 1 ) )
    paths = {}
    for key, suffix in ( ( "ao", "ao" ), ( "metal", "metal" ), ( "alpha", "trans" ), ( "trans", "trans" ), ( "illum", "illum" ) ):
        if s.get( key ) is not None:
            save_grey( out / f"{name}_{suffix}.png", np.clip( s[key], 0, 1 ) )
            paths[key] = f"{R}/{name}_{suffix}.png"
    write_text( out / f"{name}.vmat", vmat( f"{R}/{name}_color.jpg", f"{R}/{name}_normal.png", f"{R}/{name}_rough.png",
                                            s.get( "metalness", 0.0 ), paths.get( "alpha" ), paths.get( "illum" ),
                                            s.get( "illum_brightness", 0.0 ), s.get( "illum_tint", ( 1, 1, 1 ) ),
                                            metal_map=paths.get( "metal" ), ao=paths.get( "ao" ), translucent=paths.get( "trans" ),
                                            backfaces=s.get( "backfaces", False ),
                                            alpha_test_reference=0.15 if name == "rv_grating" else 0.5 ) )
    if LIT is not None and s["colour"].shape[0] == s["colour"].shape[1] and s.get( "trans" ) is None:
        LIT.append( lit_swatch( name, s ) )
    print( f"wrote {name}" )
    return srgb


def as_surface( result ):
    """ A surface function's result as a dict: the old four ( colour, roughness, height, ppi ) too. A colour given
    0-255 (as the extra modules' were once described) is brought to 0-1. """
    if isinstance( result, dict ):
        return result
    c, r, h, ppi = result[:4]
    c = np.asarray( c, np.float32 )
    if c.max() > 1.5:
        c = c / 255.0
    return dict( colour=c, rough=np.asarray( r, np.float32 ), height=np.asarray( h, np.float32 ), ppi=ppi )


LIT = None              # a list of lit swatches while --lit is given


SURFACES = {
    "rv_wall": lambda: formwork(),
    "rv_plinth": lambda: formwork( seed=102, base=( 124, 123, 118 ), weather=1.3, ties=0.25, grime=0.5, chips=1.8 ),
    "rv_wall_clean": lambda: formwork( seed=103, base=( 152, 151, 146 ), weather=0.0, chips=0.5 ),
    "rv_floor": lambda: hall_floor(),
    "rv_yard": lambda: wet_yard(),
    "rv_asphalt": lambda: wet_asphalt(),
    "rv_yellow": lambda: paint_on_steel( 41, ( 226, 170, 22 ), chips=0.55, rust=0.5, grime=0.35 ),
    "rv_steel": lambda: paint_on_steel( 42, ( 90, 94, 98 ), chips=0.35, primer=PRIMER_RED, rough=0.45 ),
    "rv_white": lambda: paint_on_steel( 43, ( 212, 210, 202 ), tile=96.0, chips=0.15, rough=0.5, grime=0.6, chalk=0.6 ),
    "rv_dark": lambda: paint_on_steel( 44, ( 60, 62, 66 ), chips=0.3, rough=0.48 ),
    "rv_frame": lambda: paint_on_steel( 45, ( 76, 80, 84 ), chips=0.2, rough=0.4, scratches=0.6, rust=0.3 ),
    "rv_door": lambda: paint_on_steel( 46, ( 100, 112, 122 ), tile=96.0, chips=0.15, rough=0.4, grime=0.5, scratches=0.8 ),
    "rv_door_yellow": lambda: paint_on_steel( 47, ( 214, 164, 30 ), tile=96.0, chips=0.25, rough=0.42, grime=0.45 ),
    "rv_louvre": lambda: paint_on_steel( 48, ( 112, 116, 118 ), chips=0.15, rough=0.5, dust=0.7, grime=0.5 ),
    "rv_desk": lambda: paint_on_steel( 49, ( 84, 88, 94 ), chips=0.02, rust=0.0, grime=0.1, dust=0.15, scratches=1.0,
                                       rough=0.4, chalk=0.0, blisters=0.0, runs_from=0.0 ),
    "rv_chair": lambda: fabric(),
    "rv_olive": lambda: moulded( 50, ( 80, 86, 62 ) ),
    "rv_case": lambda: moulded( 51, ( 54, 56, 58 ), rough=0.55 ),
    "rv_pipe": lambda: jacketing(),
    "rv_liner": lambda: stainless_liner(),
    "rv_galv": lambda: galvanised(),
    "rv_stainless": lambda: brushed(),
    "rv_rust": lambda: rusted(),
    "rv_hazard": lambda: hazard_stripes(),
    "rv_grating": lambda: bar_grating(),
    "rv_line_yellow": lambda: line_paint( 61, ( 214, 164, 34 ) ),
    "rv_line_white": lambda: line_paint( 62, ( 222, 222, 216 ) ),
    "rv_window_dark": lambda: window_glass( 71 ),
    "rv_window_lit": lambda: window_glass( 72, lit=True ),
    "rv_grime_foot": lambda: grime_decal( 81, "foot" ),
    "rv_grime_top": lambda: grime_decal( 82, "top" ),
    "rv_puddle": lambda: puddle_atlas(),
}
METALNESS = {}
NAMES = list( SURFACES ) + [ "rv_rack", "rooms", "letters", "rv_plates", "rv_screens", "rv_pool_water", "painted" ]


# Other Riverdale modules can bring their own materials, so each keeps them beside the geometry that uses them:
# - EXTRA_PAINTS = { "rv_name": ( ( r, g, b ), metalness, roughness, glow ) }: flat paints, as PAINTED;
# - EXTRA_SURFACES = { "rv_name": ( tile_inches, metalness, fn ) }: textured surfaces, fn() returning
#   ( colour (linear, 0-1; a colour given 0-255 is brought to 0-1), roughness (0-1), height (inches), pixels per inch ),
#   or a dict as SURFACES' functions return (metal, ao, alpha, trans, illum maps; see write_material).
# Their modules mustn't import riverdale_map at their top level (riverdale_map loads these while it's being imported).
EXTRA_MODULES = ( "riverdale_parts", "riverdale_hall", "riverdale_backdrop", "riverdale_facades", "riverdale_yard",
                  "riverdale_vapor" )
_extras_loaded = False


def load_extras():
    global _extras_loaded
    if _extras_loaded:
        return
    _extras_loaded = True
    import importlib
    for module_name in EXTRA_MODULES:
        try:
            module = importlib.import_module( module_name )
        except ModuleNotFoundError as error:
            if error.name != module_name:
                raise
            continue
        for paint, spec in getattr( module, "EXTRA_PAINTS", {} ).items():
            PAINTED[paint] = spec
        for paint, ( tile, metalness, fn ) in getattr( module, "EXTRA_SURFACES", {} ).items():
            SURFACES[paint] = fn
            TILES[paint] = tile
            if metalness:
                METALNESS[paint] = metalness
            if paint not in NAMES:
                NAMES.insert( NAMES.index( "rv_rack" ), paint )


def all_paints():
    load_extras()
    names = list( SURFACES ) + [ "rv_rack", "rv_letters_dark", "rv_letters_light", "rv_plates", "rv_screens",
                                 "rv_pool_water" ] + room_paints() + list( PAINTED )
    return names


def room_paints():
    return [ f"rv_window_{room}{suffix}" for room in ROOMS for suffix in ( "", "_lit" ) ]


def build( name, out ):
    done = {}
    if name in SURFACES:
        surface = as_surface( SURFACES[name]() )
        surface.setdefault( "metalness", METALNESS.get( name, 0.0 ) )
        done[name] = write_material( out, name, surface )
    elif name == "rv_rack":
        c, r, h, ppi, illum = rack()
        done[name] = write_surface( out, name, c, r, h, ppi, 0.5, illum=illum, illum_brightness=2.5, illum_tint=( 0.35, 0.9, 1.0 ) )
    elif name == "rooms":
        wall = room_picture( "wall", px( 512 ) )
        save_rgb( out / "rv_room_wall_color.png", wall )
        for room, ( picture, depth, dim, bright ) in ROOMS.items():
            c = room_picture( room )
            save_rgb( out / f"{picture}_color.png", c )
            back, wall_path = f"{RESOURCE_DIR}/{picture}_color.png", f"{RESOURCE_DIR}/rv_room_wall_color.png"
            write_text( out / f"rv_window_{room}.vmat", room_vmat( back, wall_path, depth, dim ) )
            write_text( out / f"rv_window_{room}_lit.vmat", room_vmat( back, wall_path, depth, bright ) )
            done[f"rv_window_{room}"] = c
        print( f"wrote {len( ROOMS ) * 2} room windows" )
    elif name == "letters":
        a = letters_atlas()
        save_grey( out / "rv_letters_trans.png", a )
        for tone, tint, rough in ( ( "dark", ( 0.030, 0.032, 0.034 ), 0.7 ), ( "light", ( 0.86, 0.87, 0.86 ), 0.6 ) ):
            text = vmat( "[1.000000 1.000000 1.000000 0.000000]", "materials/default/default_normal.tga",
                         f"[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]", 0.0, f"{RESOURCE_DIR}/rv_letters_trans.png", tint=tint )
            write_text( out / f"rv_letters_{tone}.vmat", text )
        done["rv_letters"] = np.repeat( a[..., None] * 255, 3, -1 )
        print( "wrote rv_letters" )
    elif name == "rv_plates":
        c, r = plates_atlas()
        save_rgb( out / "rv_plates_color.png", c )
        save_grey( out / "rv_plates_rough.png", r )
        write_text( out / "rv_plates.vmat", vmat( f"{RESOURCE_DIR}/rv_plates_color.png", "materials/default/default_normal.tga",
                                                   f"{RESOURCE_DIR}/rv_plates_rough.png" ) )
        done[name] = c
        print( "wrote rv_plates" )
    elif name == "rv_screens":
        c = screens_atlas()
        save_rgb( out / "rv_screens_color.png", c )
        write_text( out / "rv_screens.vmat", vmat( f"{RESOURCE_DIR}/rv_screens_color.png", "materials/default/default_normal.tga",
                                                    "[0.200000 0.200000 0.200000 0.000000]", illum="[1.000000 1.000000 1.000000 0.000000]",
                                                    illum_brightness=3.0 ) )
        done[name] = c
        print( "wrote rv_screens" )
    elif name == "rv_pool_water":
        write_text( out / "rv_pool_water.vmat", water_vmat() )
        print( "wrote rv_pool_water" )
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


def write_sheet( results, path ):
    tiles = []
    for name, colour in results.items():
        img = Image.fromarray( np.clip( colour, 0, 255 ).astype( np.uint8 ) ).convert( "RGB" )
        img.thumbnail( ( 512, 512 ), Image.LANCZOS )
        canvas = Image.new( "RGB", ( 512, 512 ), ( 16, 16, 16 ) )
        canvas.paste( img, ( 0, 0 ) )
        ImageDraw.Draw( canvas ).text( ( 6, 6 ), name, fill=( 255, 60, 60 ) )
        tiles.append( canvas )
    cols = 4
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( 512 * cols, 512 * rows ), ( 16, 16, 16 ) )
    for k, tl in enumerate( tiles ):
        sheet.paste( tl, ( 512 * ( k % cols ), 512 * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


# ---------------------------------------------------------------------------------------------------------------------
# Lit swatches (--lit): how each surface takes the light, so roughness and normals can be judged and not only colour.
# Shaded with GGX under a low warm sunrise sun and a clear sky, in three panels: two tiles across (tiling) and a patch at
# full size, both lit raking from the left as a wall would be at sunrise, then the surface laid flat and seen from a
# standing player's eye towards the sun, mipmapped, where wet ground and puddles show what they reflect.

SUN = np.array( ( 1.0, 0.78, 0.56 ), np.float32 ) * 2.6
SKY_ZENITH = np.array( ( 0.16, 0.27, 0.52 ), np.float32 )
SKY_HORIZON = np.array( ( 0.78, 0.62, 0.48 ), np.float32 )
GROUND = np.array( ( 0.09, 0.085, 0.08 ), np.float32 )


def _norm( v ):
    return v / np.maximum( np.linalg.norm( v, axis=-1, keepdims=True ), 1e-8 )


def _sky( d, sun, rough ):
    """ The sky's radiance along d, blurred as a surface of this roughness sees it in its reflection. """
    up = np.clip( d[..., 2], -1, 1 )
    t = np.sqrt( np.clip( up, 0, 1 ) )[..., None]
    c = SKY_HORIZON * ( 1 - t ) + SKY_ZENITH * t
    above = smoothstep( -0.12, 0.04, up )[..., None]
    c = GROUND * ( 1 - above ) + c * above
    avg = 0.5 * ( SKY_HORIZON + SKY_ZENITH ) * 0.7 + 0.3 * GROUND
    r = np.asarray( rough )[..., None]
    c = c * ( 1 - r ) + avg * r
    cosg = np.clip( ( d * sun ).sum( -1 ), -1, 1 )
    glow = np.exp( ( cosg - 1 ) / ( 0.05 + 0.4 * np.asarray( rough ) ** 2 ) )[..., None] * 0.5
    return c + SUN * glow * 0.12


def _shade( albedo, n, v, l, rough, metal, ao ):
    rough = np.clip( rough, 0.03, 1.0 )
    metal = metal[..., None]
    f0 = 0.04 * ( 1 - metal ) + albedo * metal
    diffuse = albedo * ( 1 - metal )
    nl = np.clip( ( n * l ).sum( -1 ), 0, 1 )
    nv = np.clip( ( n * v ).sum( -1 ), 1e-3, 1 )
    h = _norm( v + l )
    nh = np.clip( ( n * h ).sum( -1 ), 0, 1 )
    vh = np.clip( ( v * h ).sum( -1 ), 0, 1 )
    a2 = ( rough * rough ) ** 2
    D = a2 / ( math.pi * ( nh * nh * ( a2 - 1 ) + 1 ) ** 2 )
    k = ( rough + 1 ) ** 2 / 8
    G = nv / ( nv * ( 1 - k ) + k ) * nl / ( nl * ( 1 - k ) + k )
    F = f0 + ( 1 - f0 ) * ( ( 1 - vh ) ** 5 )[..., None]
    spec = ( D * G / ( 4 * nv * nl + 1e-4 ) * nl )[..., None] * F
    # The sky's light: irradiance by the normal, and its reflection through Karis's split-sum fit.
    irr = GROUND * ( 0.5 - 0.5 * n[..., 2:3] ) + 0.5 * ( SKY_HORIZON + SKY_ZENITH ) * 0.55 * ( 0.5 + 0.5 * n[..., 2:3] )
    rdir = _norm( 2 * ( n * v ).sum( -1, keepdims=True ) * n - v )
    env = _sky( rdir, l, rough )
    c0, c1 = np.array( ( -1, -0.0275, -0.572, 0.022 ) ), np.array( ( 1, 0.0425, 1.04, -0.04 ) )
    r4 = rough[..., None] * c0 + c1
    a004 = np.minimum( r4[..., 0] ** 2, np.exp2( -9.28 * nv ) ) * r4[..., 0] + r4[..., 1]
    A = -1.04 * a004 + r4[..., 2]
    B = 1.04 * a004 + r4[..., 3]
    spec_env = env * ( f0 * A[..., None] + B[..., None] )
    aoc = ao[..., None]
    return diffuse / math.pi * SUN * nl[..., None] + diffuse * irr * aoc + spec * SUN + spec_env * np.clip( aoc * 1.2, 0, 1 )


def _tonemap( c, exposure=1.0 ):
    x = np.clip( c * exposure, 0, None )
    x = x * ( 2.51 * x + 0.03 ) / ( x * ( 2.43 * x + 0.59 ) + 0.14 )
    return T.linear_to_srgb( np.clip( x, 0, 1 ) )


def _pyramid( a ):
    levels = [ a ]
    while levels[-1].shape[0] > 8:
        b = levels[-1]
        levels.append( 0.25 * ( b[0::2, 0::2] + b[1::2, 0::2] + b[0::2, 1::2] + b[1::2, 1::2] ) )
    return levels


def _sample( level, u, v ):
    """ Bilinear, wrapped; u right, v up the picture, 0-1 a tile. """
    h, w = level.shape[:2]
    x = u * w - 0.5
    y = ( 1.0 - v ) * h - 0.5
    x0, y0 = np.floor( x ).astype( int ), np.floor( y ).astype( int )
    fx, fy = x - x0, y - y0
    if level.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    g = lambda yy, xx: level[yy % h, xx % w]
    return ( g( y0, x0 ) * ( 1 - fx ) * ( 1 - fy ) + g( y0, x0 + 1 ) * fx * ( 1 - fy ) + g( y0 + 1, x0 ) * ( 1 - fx ) * fy +
             g( y0 + 1, x0 + 1 ) * fx * fy )


def lit_swatch( name, s, size=360 ):
    """ Three panels of one surface (s: build's dict), as an sRGB picture. """
    colour = np.clip( s["colour"], 0, 1 ).astype( np.float32 )
    nrm = wrap_normals( s["height"], s["ppi"] )
    n = colour.shape[0]
    rough = np.clip( s["rough"], 0, 1 ).astype( np.float32 )
    metal = s.get( "metal" )
    metal = np.full( ( n, n ), float( s.get( "metalness", 0.0 ) ), np.float32 ) if metal is None else metal.astype( np.float32 )
    ao = s.get( "ao" )
    ao = np.ones( ( n, n ), np.float32 ) if ao is None else ao.astype( np.float32 )
    alpha = s.get( "alpha" )
    tile = n / s["ppi"]
    wall_l = _norm( np.array( ( -0.82, 0.32, 0.47 ), np.float32 ) )
    panels = []
    # Two tiles across, and a patch at full size.
    for crop in ( "tiles", "patch" ):
        if crop == "tiles":
            idx = ( np.arange( size ) * ( 2 * n / size ) ).astype( int ) % n
            k = max( 1, int( 2 * n / size ) )
            pick = lambda a: blur( a, k * 0.5 )[np.ix_( idx, idx )] if a.ndim == 2 else np.stack( [ blur( a[..., c], k * 0.5 )[np.ix_( idx, idx )] for c in range( a.shape[-1] ) ], -1 )
        else:
            o = ( n - size ) // 3 if n > size else 0
            sl = ( o + np.arange( size ) ) % n
            pick = lambda a: a[np.ix_( sl, sl )]
        al, nn, rr, mm, oo = pick( colour ), _norm( pick( nrm ) ), pick( rough ), pick( metal ), pick( ao )
        # A wall facing the viewer (-y): the picture's right is x, its up is z, its outward normal -y.
        nw = np.stack( [ nn[..., 0], -nn[..., 2], nn[..., 1] ], -1 )
        v = np.zeros_like( nw )
        v[..., 1] = -1
        lw = np.array( ( wall_l[0], -wall_l[2], wall_l[1] ), np.float32 )
        c = _shade( al, nw, v, np.broadcast_to( lw, nw.shape ), rr, mm, oo )
        img = _tonemap( c, 0.9 )
        if alpha is not None:
            back = np.array( ( 40, 40, 44 ), np.float32 )
            a = pick( alpha )[..., None]
            img = img * a + back * ( 1 - a )
        panels.append( img )
    # Laid flat, seen from 64 in up looking towards the sun.
    W, H = size * 2, size
    eye = 64.0
    pitch, fov = math.radians( -11 ), math.radians( 60 )
    yy, xx = np.mgrid[0:H, 0:W].astype( np.float32 )
    px_ang = fov / W
    dx = ( xx - W / 2 ) * px_ang
    dy = -( yy - H / 2 ) * px_ang
    d = _norm( np.stack( [ dx, np.cos( pitch ) - dy * math.sin( pitch ), math.sin( pitch ) + dy * math.cos( pitch ) ], -1 ) )
    sun = _norm( np.array( ( math.sin( math.radians( 18 ) ), math.cos( math.radians( 18 ) ), math.tan( math.radians( 15 ) ) ), np.float32 ) )
    ground = d[..., 2] < -1e-3
    t = np.where( ground, eye / np.maximum( -d[..., 2], 1e-3 ), 0 )
    hx, hy = d[..., 0] * t, d[..., 1] * t
    u, vv = hx / tile, hy / tile
    foot_across = t * px_ang
    foot_along = foot_across / np.maximum( -d[..., 2], 1e-3 )
    lod = np.log2( np.maximum( np.maximum( foot_across, foot_along / 8 ) * s["ppi"], 1.0 ) )
    pyr = { "c": _pyramid( colour ), "n": _pyramid( nrm ), "r": _pyramid( rough ), "m": _pyramid( metal ), "o": _pyramid( ao ) }
    if alpha is not None:
        pyr["a"] = _pyramid( alpha.astype( np.float32 ) )
    out = np.zeros( ( H, W, 3 ), np.float32 )
    li = np.clip( np.round( lod ).astype( int ), 0, len( pyr["c"] ) - 1 )
    for k in range( len( pyr["c"] ) ):
        sel = ground & ( li == k )
        if not sel.any():
            continue
        su, sv = u[sel], vv[sel]
        al = _sample( pyr["c"][k], su, sv )
        nn = _norm( _sample( pyr["n"][k], su, sv ) )
        # Tangent space to the floor's: x right, y ahead, z up.
        rr = _sample( pyr["r"][k], su, sv )
        # Mipped normals spread the highlight: Toksvig, as the engine's own normal-aware mips would.
        rr = np.sqrt( np.clip( rr ** 2 + ( 1 - np.linalg.norm( _sample( pyr["n"][k], su, sv ), axis=-1 ) ) * 2.0, 0, 1 ) )
        mm, oo = _sample( pyr["m"][k], su, sv ), _sample( pyr["o"][k], su, sv )
        vdir = -d[sel]
        c = _shade( al, nn, vdir, np.broadcast_to( sun, nn.shape ), rr, mm, oo )
        if alpha is not None:
            a = _sample( pyr["a"][k], su, sv )[..., None]
            c = c * a + ( 1 - a ) * np.array( ( 0.03, 0.03, 0.035 ), np.float32 )
        out[sel] = c
    skyp = ~ground
    out[skyp] = _sky( d[skyp], sun, np.zeros( skyp.sum() ) ) + SUN * np.exp( ( np.clip( ( d[skyp] * sun ).sum( -1 ), -1, 1 ) - 1 ) / 0.0004 )[..., None] * 3
    flat = _tonemap( out, 0.9 )
    top = np.concatenate( panels, 1 )
    img = np.concatenate( [ top, flat ], 0 )
    pic = Image.fromarray( np.clip( img, 0, 255 ).astype( np.uint8 ) )
    ImageDraw.Draw( pic ).text( ( 6, 4 ), name, fill=( 255, 70, 70 ) )
    return pic


def write_lit( swatches, path ):
    if not swatches:
        return
    cols = 2
    w, h = swatches[0].size
    rows = ( len( swatches ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( w * cols, h * rows ), ( 16, 16, 16 ) )
    for k, sw in enumerate( swatches ):
        sheet.paste( sw, ( w * ( k % cols ), h * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote lit swatches {path}" )


def main():
    global SCALE, LIT
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to draw (default all: {', '.join( NAMES )})" )
    parser.add_argument( "--out", help="write somewhere else" )
    parser.add_argument( "--sheet", help="also write a contact sheet here" )
    parser.add_argument( "--scale", type=float, default=1.0 )
    parser.add_argument( "--lit", help="also write lit swatches of the surfaces here (a PNG)" )
    args = parser.parse_args()
    SCALE = args.scale
    LIT = [] if args.lit else None
    load_extras()
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    results = {}
    for name in args.names or NAMES:
        results.update( build( name, out ) )
    if args.sheet and results:
        write_sheet( results, args.sheet )
    if LIT:
        write_lit( LIT, args.lit )


if __name__ == "__main__":
    main()
