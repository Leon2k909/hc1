"""
Belltower's finishes, drawn from scratch with numpy and PIL into Assets/materials/belltower/ beside
Tools/belltower_materials.py's stone, which this builds on.

    python Tools/belltower_finishes.py [name ...] [--out <dir>] [--sheet <png>]

- plaster_<colour>: the houses' lime render (PLASTERS), one tile 512 units (13 m) across and as high as the tallest
  gable, so a wall shows it once. Its picture starts at the ground (map_kit's anchored paints: v 0 at z 0), so what's
  drawn at its foot stays at the foot of every wall: rising damp to an irregular tide line ~3-4 ft up with a crust of
  salts along it, mud splashed up the bottom foot, the render blown off in places down there and the rubble walling
  showing through. Above that: a hand-floated surface out of true, trowel arcs, sand grain, hairline cracks, a few
  patched repairs in a mismatched lime, limewash worn through to the coat under it, grime washed down in streaks, and
  sun bleaching up high. Every colour shares the normal, roughness and AO maps; only the colour maps differ.
- street_cobbles: the streets' paving, laid as river cobbles 5-8 inches across bedded in packed dirt and sand, the
  tops worn smooth and paler by traffic, one tile 256 units (6.5 m) across: the old 64-unit scan repeated every 1.6 m.

As in belltower_materials, a .vmat is only rewritten when its text changes. --out writes somewhere else to try things
out; --sheet writes a picture of each material lit from the top left (a 2x2 repeat, a close-up and the height).
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

import belltower_materials as M

SHEETS = {}


def out_dir():
    return M.OUT_DIR


def write( name, colour, normal, rough, ao, metal=0.0 ):
    """ The maps and the .vmat of one opaque material. colour may be a dict { paint: colour } sharing the rest. """
    colours = colour if isinstance( colour, dict ) else { name: colour }
    M.save_rgb( out_dir() / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    M.save_grey( out_dir() / f"{name}_rough.png", rough )
    M.save_grey( out_dir() / f"{name}_ao.png", ao )
    for paint, rgb in colours.items():
        M.save_rgb( out_dir() / f"{paint}_color.png", rgb )
        text = M.vmat( f"{M.RESOURCE_DIR}/{paint}_color.png", f"{M.RESOURCE_DIR}/{name}_normal.png",
                       f"{M.RESOURCE_DIR}/{name}_rough.png", f"{M.RESOURCE_DIR}/{name}_ao.png" )
        text = text.replace( "Tools/belltower_materials.py", "Tools/belltower_finishes.py" )
        if metal:
            text = text.replace( 'g_flMetalness "0.00"', f'g_flMetalness "{metal:.2f}"' )
        M.write_vmat( paint, text )


def luminance( c ):
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def saturate( c, amount ):
    """ amount < 1 greys the colour towards its own luminance. """
    y = luminance( c )[..., None]
    a = amount[..., None] if np.ndim( amount ) == 2 else amount
    return y + ( c - y ) * a


def streaks( rng, n, length, width ):
    """ Tileable vertical streaks: white noise smeared down the picture, unit deviation. """
    s = M.blur( rng.standard_normal( ( n, n ) ), ( length, width ) )
    return ( s - s.mean() ) / s.std()


def contours( field, spacing ):
    """ Parallel ridges following the field's contours, spacing apart (in the field's units): trowel arcs. """
    return np.sin( 2 * math.pi * field / spacing )


def tide( n, ppu, rng, mean, swing ):
    """ An irregular line across the picture: a height in inches for each column, tileable. """
    x = rng.standard_normal( n )
    line = np.zeros( n )
    for sigma, weight in ( ( 80.0, 1.0 ), ( 20.0, 0.3 ), ( 4.0, 0.06 ) ):
        part = ndimage.gaussian_filter1d( x, sigma * ppu / 4.0, mode="wrap" )
        line += weight * part / ( part.std() + 1e-9 )
        x = rng.standard_normal( n )
    return mean + swing * line / line.std()


# ---------------------------------------------------------------------------------------------------------------------
# Lime render

PLASTER_TILE = 512.0
PLASTER_PX = 2048
# paint: ( the limewash's colour, the older coat under it where it's worn through ), sRGB. Warmer than building_textures'
# flat renders, which in the late sun read as grey pastels.
PLASTERS = {
    "render_rose": ( ( 206, 140, 118 ), ( 216, 182, 132 ) ),
    "render_terracotta": ( ( 196, 116, 82 ), ( 214, 168, 120 ) ),
    "render_ochre": ( ( 218, 170, 104 ), ( 224, 210, 180 ) ),
    "render_cream": ( ( 232, 214, 170 ), ( 204, 186, 156 ) ),
    "render_blue": ( ( 150, 176, 194 ), ( 222, 214, 194 ) ),
    "render_sage": ( ( 164, 182, 142 ), ( 216, 206, 178 ) ),
    "render_pale": ( ( 228, 220, 198 ), ( 200, 184, 158 ) ),
    "whitewash": ( ( 226, 222, 210 ), ( 196, 184, 162 ) ),
}
RENDER_THICK = 0.75        # inches of render over the walling
LIME = ( 222, 216, 200 )    # bare lime, at the render's broken edges
BARE = ( 196, 188, 170 )    # the render's own lime and sand, where both coats of wash are gone
REPAIR = ( 206, 202, 190 )  # a later patch in a greyer, cement-gauged lime


def plaster_paint( paint ):
    return "plaster_" + paint.replace( "render_", "" )


def plaster():
    n, tile = PLASTER_PX, PLASTER_TILE
    ppu = n / tile
    rng = np.random.default_rng( 512 )
    z = ( n - 0.5 - np.arange( n ) )[:, None] / ppu * np.ones( ( 1, n ) )      # inches up the wall
    noise = lambda beta, fmin, fmax=None: M.noise( rng, n, beta, fmin, fmax )

    # The walling under it: belltower_materials' rubble at the same scale, tiled to fit.
    M.RUBBLE_TILE, keep = 256.0, M.RUBBLE_TILE
    walling, wall_h, wall_rough, wall_hollow, _ = M.rubble( np.random.default_rng( 513 ), n // 2 )
    M.RUBBLE_TILE = keep
    walling = np.tile( M.to_linear( walling["rubble"] ), ( 2, 2, 1 ) )
    wall_h, wall_rough = np.tile( wall_h, ( 2, 2 ) ), np.tile( wall_rough, ( 2, 2 ) )

    # The render's face: floated by hand, so out of true by a quarter inch over a few feet, with trowel arcs and sand.
    body = 0.16 * noise( 2.8, 1, 16 ) + 0.05 * noise( 2.0, 10, 80 )
    swirl = noise( 3.0, 2, 24 )
    trowel = contours( swirl, 0.11 ) * M.smoothstep( 0.6, 1.8, noise( 2.0, 4, 40 ) )
    sand = noise( 1.0, 280, None )
    pits = np.maximum( noise( 1.2, 160, None ) - 2.8, 0.0 )
    face = body + 0.006 * trowel + 0.007 * sand - 0.02 * pits

    # Spalls, where the render has blown off: mostly in the damp at the foot, a few up the wall.
    ragged = noise( 1.8, 12, 120 )
    spall_field = ( 0.75 * noise( 2.6, 1, 14 ) + 0.22 * ragged + 1.0 * np.exp( -z / 30.0 ) + 0.35 * np.exp( -z / 110.0 )
                    - 0.6 * M.smoothstep( 160, 320, z ) )
    spall = M.smoothstep( 1.78, 1.86, spall_field )
    rim = M.smoothstep( 1.62, 1.78, spall_field ) * ( 1 - spall )      # the cracked, lifted render round a spall

    # Hairline cracks: a few contours of a smooth field, kept in places.
    crack_field = noise( 2.0, 5, 60 )
    crack = M.smoothstep( 0.03, 0.0, np.abs( crack_field ) ) * M.smoothstep( 1.0, 1.6, noise( 2.0, 2, 16 ) )
    crack = np.maximum( crack, M.smoothstep( 0.02, 0.0, np.abs( noise( 2.2, 8, 90 ) ) )
                        * M.smoothstep( 1.4, 2.0, noise( 2.0, 2, 12 ) ) * 0.7 )

    # Patched repairs: a few irregular patches of newer render, a little proud, limewashed over in a shade off.
    patch_field = noise( 2.8, 2, 14 ) + 0.05 * noise( 1.6, 20, 120 )
    patch = M.smoothstep( 2.1, 2.13, patch_field )
    patch *= 1 - spall

    # The limewash worn through to the coat under it. It chalks away in broad patches with frayed but continuous edges,
    # where salts push it off above the damp and under the eaves where the roof drips, and in a few places on the open
    # wall; not in a dust of flakes, which read as white speckle from the street.
    cluster = M.smoothstep( 1.2, 2.2, noise( 2.8, 1, 6 ) + 0.5 * np.exp( -( ( z - 52.0 ) / 26.0 ) ** 2 )
                            + 0.35 * M.smoothstep( 300, 420, z ) )
    flake_field = noise( 2.6, 3, 48 ) + 0.18 * noise( 1.8, 40, 220 )
    flake = M.smoothstep( -0.08, 0.08, flake_field - ( 2.6 - 2.4 * cluster ) )
    bare = M.smoothstep( -0.06, 0.06, flake_field - ( 3.4 - 2.2 * cluster ) )     # both coats gone: the render
    flake *= ( 1 - spall ) * ( 1 - patch )
    bare *= flake
    flake_edge = np.clip( M.blur( flake, 0.8 * ppu ) - flake, 0, 1 ) * 3.0

    # Height, in inches.
    height = face * ( 1 - 0.6 * patch ) + 0.05 * patch - 0.012 * flake - 0.01 * bare - 0.08 * crack + 0.04 * rim * ragged
    under = -RENDER_THICK + 0.45 * ( wall_h - wall_h.mean() )
    spall_soft = M.blur( spall, 0.25 * ppu )
    height = height * ( 1 - spall_soft ) + under * spall_soft
    normal = M.gl_normal( height, ppu, 1.0 )
    hollow = M.cavity( height, ppu, radii=( 0.3, 1.0, 3.0 ), weights=( 1.0, 0.6, 0.3 ) )
    ao = np.clip( np.exp( -1.6 * hollow ), 0, 1 ) * ( 1 - 0.25 * spall_soft * np.exp( -1.0 * wall_hollow.mean() ) )

    # Weathering shared by every colour (multipliers and blends in linear light).
    mottle = noise( 3.0, 1, 12 )
    stains = M.smoothstep( 0.2, 2.0, noise( 2.8, 1, 8 ) )
    mid = noise( 1.8, 20, 200 )
    bleach = 0.16 * M.smoothstep( 90, 420, z ) * ( 0.6 + 0.4 * M.smoothstep( -1, 1, noise( 2.5, 1, 8 ) ) )
    rain = 0.8 * streaks( rng, n, 60 * ppu, 4.0 * ppu ) + 0.45 * streaks( rng, n, 24 * ppu, 1.6 * ppu )
    runs = M.smoothstep( 0.7, 2.4, rain ) * ( 0.4 + 0.6 * M.smoothstep( -0.5, 1.0, noise( 2.0, 2, 10 ) ) )
    washed = M.smoothstep( 1.0, 2.6, -rain )
    damp_top = tide( n, ppu, rng, 36.0, 8.0 )[None, :]
    damp = M.smoothstep( 2.0, -7.0, z - damp_top ) * ( 0.75 + 0.25 * M.smoothstep( -1, 1, noise( 2.2, 6, 60 ) ) )
    # The damp's top: a thin brown tide mark where the water evaporates and leaves its dirt, and above it a bloom of
    # salts that feathers out upwards in drifts, not a dotted line.
    above = z - damp_top
    tide_mark = np.exp( -( above / 1.4 ) ** 2 ) * ( 0.6 + 0.4 * M.smoothstep( -1, 1, noise( 2.2, 4, 60 ) ) )
    salts = ( M.smoothstep( -1.5, 0.5, above ) * np.exp( -np.maximum( above, 0.0 ) / 6.0 )
              * M.smoothstep( -0.6, 1.4, noise( 2.6, 2, 30 ) ) * ( 0.85 + 0.15 * noise( 1.4, 60, 300 ) ) )
    algae = M.spots( rng, n, 140, ( 1.0 * ppu, 4.0 * ppu ) ) * M.smoothstep( 22, 6, z )
    splash = M.smoothstep( 1.4, 2.4, noise( 0.8, 90, None ) ) * M.smoothstep( 16, 2, z )
    mud = M.smoothstep( 12, 0, z ) * ( 0.6 + 0.4 * noise( 1.4, 20, 200 ) )
    grime = np.exp( -1.2 * hollow ) * ( 1 - 0.18 * runs ) * ( 1 - 0.12 * M.smoothstep( 0.3, 1.0, rim ) )
    crack_halo = M.blur( crack, 0.6 * ppu )

    colours = {}
    for paint, ( wash, coat ) in PLASTERS.items():
        base = M.to_linear( wash ) * ( 1 + 0.1 * mottle + 0.03 * mid - 0.15 * stains )[..., None]
        # The wash goes on unevenly: a little warmer here, cooler there.
        base = base * ( 1 + 0.035 * np.stack( [ mid, 0 * mid, -mid ], -1 ) * M.smoothstep( -1, 1, mottle )[..., None] )
        old = M.lerp( M.to_linear( coat ), M.to_linear( LIME ), 0.15 ) * ( 1 + 0.05 * mid )[..., None]
        c = M.lerp( base, old, 0.7 * flake )
        c = M.lerp( c, M.to_linear( BARE ) * ( 1 + 0.05 * mid )[..., None], 0.75 * bare )
        c = M.lerp( c, M.to_linear( LIME ), np.clip( flake_edge, 0, 1 ) * 0.12 )
        c = M.lerp( c, M.lerp( base, M.to_linear( REPAIR ), 0.16 ) * ( 0.97 + 0.04 * mid )[..., None], 0.9 * patch )
        c = M.lerp( c, saturate( c, 0.6 ) * 1.18, bleach )
        c = M.lerp( c, c * 1.07, 0.5 * washed )
        c = c * ( 1 - 0.15 * runs )[..., None] * grime[..., None]
        c = c * ( 1 - 0.4 * crack )[..., None] * ( 1 - 0.12 * np.clip( crack_halo * 3, 0, 1 ) )[..., None]
        # Rising damp: darker, greyer and greener below its line, salts crusted white along it.
        wet = saturate( c * np.array( ( 0.6, 0.63, 0.6 ) ), 0.7 )
        c = M.lerp( c, wet, damp )
        c = c * ( 1 - 0.14 * tide_mark * ( 1 - spall_soft ) )[..., None] * ( 1 + 0.02 * tide_mark )[..., None]
        c = M.lerp( c, M.to_linear( ( 222, 218, 206 ) ) * ( 0.92 + 0.08 * mid )[..., None], 0.3 * np.clip( salts, 0, 1 ) )
        c = M.lerp( c, M.to_linear( ( 92, 104, 70 ) ), 0.5 * algae )
        c = M.lerp( c, c * np.array( ( 0.55, 0.5, 0.45 ) ), np.clip( 0.7 * splash + 0.35 * mud, 0, 1 ) )
        # Where the render's gone: the walling, dusty with lime, the broken edge pale.
        stone = walling * 0.92 + M.to_linear( LIME ) * 0.08
        c = M.lerp( c, M.lerp( stone, stone * 0.7, damp ), spall_soft )
        c = M.lerp( c, M.to_linear( LIME ) * 0.95, 0.35 * M.smoothstep( 0.05, 0.4, spall_soft ) * ( 1 - spall_soft ) )
        colours[plaster_paint( paint )] = M.to_srgb( np.clip( c, 0, 1 ) )

    rough = np.clip( 0.9 + 0.035 * noise( 1.2, 40, None ) - 0.03 * flake - 0.025 * patch - 0.04 * damp
                     + 0.02 * crack, 0, 1 )
    rough = rough * ( 1 - spall_soft ) + wall_rough * spall_soft
    write( "plaster", colours, normal, rough, ao )
    SHEETS["plaster"] = ( colours, normal, height )
    return rough


# ---------------------------------------------------------------------------------------------------------------------
# River cobbles

COBBLE_TILE = 256.0
COBBLE_PX = 2048
COBBLE_STONES = [ ( 150, 144, 136 ), ( 160, 152, 138 ), ( 138, 134, 128 ), ( 168, 158, 142 ), ( 130, 124, 116 ),
                  ( 156, 142, 124 ), ( 144, 140, 132 ), ( 172, 164, 150 ), ( 124, 120, 114 ), ( 162, 148, 128 ) ]
COBBLE_DIRT = ( 112, 98, 80 )


def cobbles():
    """ River cobbles 5-8 inches across (about 6 apart), each a rounded dome a little out of round, set in a bed of packed
    dirt that sits under their tops, with sand and grit in it. Per stone: its own colour (granite, limestone, a few dark
    basalts), how proud it stands, and how worn: traffic polishes the crowns smooth and pale. """
    n, tile = COBBLE_PX, COBBLE_TILE
    ppu = n / tile
    rng = np.random.default_rng( 256 )
    noise = lambda beta, fmin, fmax=None: M.noise( rng, n, beta, fmin, fmax )

    # Stones on a jittered grid, laid in loose rows across the street (the picture's u).
    spacing = 6.0 * ppu
    cells = int( round( n / spacing ) )
    spacing = n / cells
    gy, gx = np.mgrid[0:cells, 0:cells]
    px = ( gx + 0.5 + rng.uniform( -0.32, 0.32, gx.shape ) + 0.5 * ( gy % 2 ) ) * spacing
    py = ( gy + 0.5 + rng.uniform( -0.26, 0.26, gy.shape ) ) * spacing
    pts = np.stack( [ px.ravel() % n, py.ravel() % n ], -1 )
    count = len( pts )
    # A power diagram: a bigger stone's weight pushes its borders out, so sizes vary while the borders stay straight.
    size = rng.uniform( 0.84, 1.18, count )
    weight = ( size ** 2 - 1 ) * ( 0.8 * spacing ) ** 2
    offsets = np.array( [ ( dx, dy ) for dx in ( -n, 0, n ) for dy in ( -n, 0, n ) ] )
    every = ( pts[None, :, :] + offsets[:, None, :] ).reshape( -1, 2 )
    owner = np.tile( np.arange( count ), len( offsets ) )
    tree = cKDTree( every )
    # Bend the borders a little: stones, not tiles.
    warp_x = noise( 2.6, 12, 60 ) * 0.2 * ppu
    warp_y = noise( 2.6, 12, 60 ) * 0.2 * ppu
    yy, xx = np.mgrid[0:n, 0:n].astype( float )
    q = np.stack( [ ( xx + 0.5 + warp_x ).ravel(), ( yy + 0.5 + warp_y ).ravel() ], -1 )
    cell = np.empty( n * n, int )
    edge = np.empty( n * n )
    round_off = 0.5 * ppu       # corners rounded over about this much
    chunk = 1 << 18
    for s in range( 0, n * n, chunk ):
        qq = q[s:s + chunk]
        d, i = tree.query( qq, k=5 )
        pd = d ** 2 - weight[owner[i]]
        order = np.argsort( pd, axis=1 )
        i = np.take_along_axis( i, order, 1 )
        pd = np.take_along_axis( pd, order, 1 )
        p0 = every[i[:, 0]]
        # The exact distance to each power bisector, then a smooth minimum so the corners come out round.
        gap = np.linalg.norm( every[i[:, 1:]] - p0[:, None, :], axis=-1 )
        e = ( pd[:, 1:] - pd[:, :1] ) / ( 2 * np.maximum( gap, 1e-6 ) )
        e_min = e.min( 1 )
        soft = e_min - round_off * np.log( np.sum( np.exp( -( e - e_min[:, None] ) / round_off ), 1 ) )
        cell[s:s + chunk] = owner[i[:, 0]]
        edge[s:s + chunk] = soft
    cell, edge = cell.reshape( n, n ), edge.reshape( n, n ) / ppu

    # The stones: domes, steep at the bed and rounded right over, polished on top by wear.
    joint = 0.15 + 0.06 * noise( 2.0, 10, 80 )
    stone_edge = edge - joint
    inside = M.smoothstep( -0.04, 0.06, stone_edge )
    inradius = ndimage.maximum( stone_edge, labels=cell, index=np.arange( count ) )
    inradius = np.maximum( np.nan_to_num( inradius, nan=1.0 ), 0.8 )[cell]
    proud = rng.uniform( 0.55, 0.95, count )[cell] * ( inradius / 2.6 ) ** 0.5
    t = np.clip( stone_edge / inradius, 0, 1 )
    lopsided = 1 + 0.14 * noise( 2.4, 20, 160 )
    dome = proud * lopsided * ( 1 - ( 1 - t ) ** 2 ) ** 0.75
    wear = rng.uniform( 0.3, 1.0, count )[cell]
    top = dome * ( 1 - 0.08 * wear * M.smoothstep( 0.55, 1.0, t ) )
    pitting = np.maximum( noise( 1.3, 200, None ) - 2.0, 0.0 )
    stone_h = top + 0.02 * noise( 2.0, 40, 400 ) + 0.004 * noise( 1.0, 400, None ) - 0.03 * pitting

    # The bed: packed dirt and sand, grit and the odd pebble, well under the stones' tops.
    grit = M.smoothstep( 1.5, 2.6, noise( 0.6, 300, None ) )
    bed_h = 0.12 + 0.05 * noise( 2.0, 20, 200 ) + 0.02 * noise( 1.0, 300, None ) + 0.04 * grit
    height = bed_h * ( 1 - inside ) + np.maximum( stone_h, bed_h ) * inside
    normal = M.gl_normal( height, ppu, 1.0 )
    hollow = M.cavity( height, ppu, radii=( 0.25, 0.8, 2.4 ), weights=( 1.0, 0.6, 0.3 ) )
    ao = np.clip( np.exp( -2.0 * hollow ), 0, 1 )

    base = M.to_linear( COBBLE_STONES )[rng.integers( 0, len( COBBLE_STONES ), count )]
    base *= rng.uniform( 0.9, 1.08, ( count, 1 ) )
    dark = rng.random( count ) < 0.03
    base[dark] = M.to_linear( ( 78, 76, 74 ) ) * rng.uniform( 0.85, 1.1, ( dark.sum(), 1 ) )
    stone = base[cell] * ( 1 + 0.08 * noise( 2.2, 30, 300 ) + 0.05 * noise( 1.0, 300, None ) )[..., None]
    # Veins and speckle in some stones.
    vein = M.smoothstep( 0.04, 0.0, np.abs( noise( 2.2, 30, 300 ) ) ) * ( rng.random( count ) < 0.3 )[cell]
    stone = M.lerp( stone, stone * 1.35, 0.6 * vein )
    speck = M.smoothstep( 1.8, 2.6, noise( 0.4, 400, None ) )
    stone = M.lerp( stone, stone * 0.55, 0.5 * speck )
    crown = M.smoothstep( 0.3, 1.0, top / np.maximum( proud, 1e-3 ) ) * wear
    stone = M.lerp( stone, stone * 1.18 + 0.01, 0.55 * crown )
    # Dirt clings round the stones' feet.
    foot = M.smoothstep( 0.45, 0.0, stone_edge ) * inside
    dirt = M.to_linear( COBBLE_DIRT ) * ( 1 + 0.15 * noise( 2.0, 20, 300 ) + 0.1 * noise( 0.8, 300, None ) )[..., None]
    sand = M.to_linear( ( 170, 156, 128 ) ) * ( 1 + 0.08 * noise( 1.0, 300, None ) )[..., None]
    bed = M.lerp( dirt, sand, 0.4 * M.smoothstep( -0.5, 1.5, noise( 1.6, 40, 400 ) ) )
    bed = M.lerp( bed, M.to_linear( ( 150, 146, 140 ) ), 0.7 * grit )
    stone = M.lerp( stone, stone * 0.62 + bed * 0.3, 0.6 * foot )
    c = M.lerp( bed, stone, inside )
    # Big, faint stains across the street: oil, wet patches drying, old dirt.
    stain = M.smoothstep( 0.6, 2.2, noise( 2.8, 1, 12 ) )
    c = c * ( 1 - 0.18 * stain )[..., None] * ( 1 + 0.05 * noise( 2.6, 1, 8 ) )[..., None]
    c = c * np.exp( -1.3 * hollow )[..., None]
    colour = M.to_srgb( np.clip( c, 0, 1 ) )

    rough = np.clip( ( 0.78 - 0.2 * crown + 0.04 * noise( 1.0, 200, None ) ) * inside + 0.95 * ( 1 - inside ), 0, 1 )
    write( "street_cobbles", colour, normal, rough, ao )
    SHEETS["street_cobbles"] = ( { "street_cobbles": colour }, normal, height )
    return rough


# ---------------------------------------------------------------------------------------------------------------------

MATERIALS = { "plaster": plaster, "cobbles": cobbles }


def write_sheet( path ):
    """ Each material tiled 2x2 and lit from the top left, a close-up of an eighth of a tile, and the height. """
    light = np.array( ( -0.45, 0.55, 0.7 ) )
    light /= np.linalg.norm( light )
    rows = []
    for name, ( colours, normal, height ) in SHEETS.items():
        ndl = np.clip( np.sum( normal * light, -1 ), 0, 1 )
        for paint, colour in colours.items():
            shaded = np.clip( colour * ( 0.35 + 0.8 * ndl )[..., None], 0, 255 ).astype( np.uint8 )
            tiled = Image.fromarray( np.tile( shaded, ( 2, 2, 1 ) ) ).resize( ( 768, 768 ), Image.LANCZOS )
            q = shaded.shape[0] // 8
            close = Image.fromarray( shaded[-q:, :q] ).resize( ( 768, 768 ), Image.LANCZOS )
            h = ( height - height.min() ) / ( np.ptp( height ) + 1e-9 )
            hmap = Image.fromarray( ( h * 255 ).astype( np.uint8 ) ).resize( ( 384, 384 ) ).convert( "RGB" )
            row = Image.new( "RGB", ( 768 * 2 + 384, 768 ), ( 16, 16, 16 ) )
            row.paste( tiled, ( 0, 0 ) )
            row.paste( close, ( 768, 0 ) )
            row.paste( hmap, ( 1536, 0 ) )
            rows.append( row )
    if not rows:
        return
    sheet = Image.new( "RGB", ( rows[0].width, 768 * len( rows ) ) )
    for k, row in enumerate( rows ):
        sheet.paste( row, ( 0, 768 * k ) )
    sheet.save( path, quality=90 )
    print( f"wrote {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"materials to write (default all: {', '.join( MATERIALS )})" )
    parser.add_argument( "--out", help="write here instead of Assets/materials/belltower" )
    parser.add_argument( "--sheet", help="also write a lit picture of each material here" )
    args = parser.parse_args()
    if args.out:
        M.OUT_DIR = Path( args.out )
    M.OUT_DIR.mkdir( parents=True, exist_ok=True )
    for name in args.names or list( MATERIALS ):
        rough = MATERIALS[name]()
        print( f"{name}: roughness mean {rough.mean():.2f}, 5-95% {np.percentile( rough, 5 ):.2f}-"
               f"{np.percentile( rough, 95 ):.2f}" )
    if args.sheet:
        write_sheet( args.sheet )


if __name__ == "__main__":
    main()
