"""
Belltower's own materials (Assets/materials/belltower/), which Tools/belltower_detail.py maps its paints onto.

    python Tools/belltower_materials.py [name ...] [--out <dir>] [--sheet <png>]

- cobbles, flagstones: the project's cobble and pavement scans (Assets/materials/stone) are wet ones, with a mean
  roughness of 0.45 and 0.25 and joints as smooth as a mirror, so in the sun every stone shone like wet plastic. These
  keep the scans' colour, normals and AO and give them roughness maps of their own for a dry day: the stones 0.65-0.9,
  the joints' dirt rougher.
- rubble, ashlar, ashlar_grey: stone drawn from scratch (see STONES), since the project has no stone walling scan. They
  replace base_stonework's yellow brick, which stood in for both.
- parasol_red, parasol_cream, parasol_blue: plain dyed canvas for the café's parasols, whose gores are each one colour
  (building_textures' canvas is striped, and stripes on a cone's facets came out as chevrons).
- produce_<kind>: the market stalls' crates of fruit and vegetables (PRODUCE), seen from above: a tiling picture of the
  heaped fruit with its height as the normals, laid over a low mound, the way games draw a crate of produce. A few whole
  fruit on top are mapped onto the one at the tile's middle.

A material's .vmat is only rewritten when its text changes, and its maps only when drawn, so re-running it doesn't make
the editor recompile what hasn't changed. --out writes somewhere else to try things out; --sheet writes a picture of each
material lit from the top left.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/belltower"
RESOURCE_DIR = "materials/belltower"
STONE = ROOT / "Assets/materials/stone"


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def load_grey( path ):
    """ A greyscale map (8- or 16-bit) as floats 0..1. """
    image = Image.open( path )
    a = np.asarray( image ).astype( float )
    if image.mode.startswith( "I" ):
        a /= 65535.0
    else:
        a /= 255.0
    return a[..., 0] if a.ndim == 3 else a


def resized( a, n ):
    if a.shape[0] == n:
        return a
    return np.asarray( Image.fromarray( a.astype( np.float32 ), "F" ).resize( ( n, n ), Image.LANCZOS ) )


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def save_grey( path, a ):
    Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save( path, optimize=True )


def save_rgb( path, a ):
    Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( path, optimize=True )


def vmat( color, normal, rough, ao ):
    return ( "// Tools/belltower_materials.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/complex.shader"\n'
             '    F_SPECULAR "1"\n'
             '    g_flRoughnessScaleFactor "1"\n'
             '    g_flMetalness "0.00"\n'
             f'    TextureColor "{color}"\n'
             f'    TextureNormal "{normal}"\n'
             f'    TextureRoughness "{rough}"\n'
             f'    TextureAmbientOcclusion "{ao}"\n'
             '    g_vColorTint "[1.0 1.0 1.0 1.0]"\n'
             '    g_flModelTintAmount "1.0"\n'
             "}\n" )


def write_vmat( name, text ):
    path = OUT_DIR / f"{name}.vmat"
    if path.exists() and path.read_text( encoding="utf-8" ) == text:
        return
    path.write_text( text, encoding="utf-8", newline="\n" )


# ---------------------------------------------------------------------------------------------------------------------
# The scans, dried

def cobbles():
    """ The joints are the scan's darkest roughness (water standing in them), so they become the roughest part:
    packed dirt. The stones keep their own variation, lifted to worn, dry granite. """
    r = resized( load_grey( STONE / "cobble_stones_tight_roughness.png" ), 2048 )
    joint = 1.0 - smoothstep( 0.1, 0.35, r )
    rough = ( 0.64 + 0.24 * r ) * ( 1.0 - joint ) + 0.93 * joint
    save_grey( OUT_DIR / "cobbles_rough.png", rough )
    write_vmat( "cobbles", vmat( "materials/stone/cobble_stones_tight_basecolor.png",
                                 "materials/stone/cobble_stones_tight_normal.png",
                                 f"{RESOURCE_DIR}/cobbles_rough.png",
                                 "materials/stone/cobble_stones_tight_ambientocclusion.png" ) )
    return rough


def flagstones():
    r = load_grey( STONE / "wet_pavement_Roughness.tga" )
    rough = 0.62 + 0.45 * r
    save_grey( OUT_DIR / "flagstones_rough.png", rough )
    write_vmat( "flagstones", vmat( "materials/stone/wet_pavement_BaseColor.tga",
                                    "materials/stone/wet_pavement_Normal.tga",
                                    f"{RESOURCE_DIR}/flagstones_rough.png",
                                    "materials/stone/wet_pavement_AmbientOcclusion.tga" ) )
    return rough


# ---------------------------------------------------------------------------------------------------------------------
# Stone walling, drawn from a height field in inches (1 unit): the normals, AO and cavity darkening all come from it.

def noise( rng, n, beta, fmin, fmax=None ):
    """ Tileable fractal noise, unit deviation (terrain_textures' spectral noise). """
    import terrain_textures as T
    return T.spectral( rng, n, beta, fmin, fmax )


def blur( a, sigma ):
    return ndimage.gaussian_filter( a, sigma, mode="wrap" )


def to_linear( rgb ):
    c = np.clip( np.asarray( rgb, float ) / 255.0, 0.0, 1.0 )
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def to_srgb( c ):
    c = np.clip( c, 0.0, 1.0 )
    return 255.0 * np.where( c <= 0.0031308, c * 12.92, 1.055 * c ** ( 1 / 2.4 ) - 0.055 )


def lerp( a, b, t ):
    t = np.asarray( t )
    colour = np.ndim( a ) != 2 or np.ndim( b ) != 2
    return a + ( b - a ) * ( t[..., None] if t.ndim == 2 and colour else t )


def gl_normal( height, ppu, strength=1.0 ):
    """ OpenGL tangent normals (green up the picture) from a height field in inches, ppu px to the inch. """
    hx = ( np.roll( height, -1, 1 ) - np.roll( height, 1, 1 ) ) * 0.5 * ppu * strength
    hr = ( np.roll( height, -1, 0 ) - np.roll( height, 1, 0 ) ) * 0.5 * ppu * strength
    n = np.stack( [ -hx, hr, np.ones_like( height ) ], -1 )
    return n / np.linalg.norm( n, axis=-1, keepdims=True )


def cavity( height, ppu, radii=( 0.4, 1.2, 3.5 ), weights=( 1.0, 0.7, 0.35 ) ):
    """ How far each px sits below its surroundings (inches), at a few scales: mortar joints, pits, the gaps round a
    stone. """
    return sum( w * np.maximum( blur( height, r * ppu ) - height, 0.0 ) for r, w in zip( radii, weights ) )


def spots( rng, n, count, radius, softness=0.6 ):
    """ Tileable round patches (lichen, stains): count of them, radius a (min, max) range in px, edges frayed by noise. """
    field = np.zeros( ( n, n ) )
    y, x = np.mgrid[0:n, 0:n] + 0.5
    fray = noise( rng, n, 1.4, 8, None )
    for _ in range( count ):
        cx, cy, r = rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( *radius )
        x0, x1, y0, y1 = int( cx - 2 * r ), int( cx + 2 * r ) + 1, int( cy - 2 * r ), int( cy + 2 * r ) + 1
        ys, xs = np.arange( y0, y1 ) % n, np.arange( x0, x1 ) % n
        yy, xx = np.meshgrid( np.arange( y0, y1 ) + 0.5, np.arange( x0, x1 ) + 0.5, indexing="ij" )
        d = np.hypot( xx - cx, yy - cy ) / r
        patch = smoothstep( 1.0 + softness * 0.5, 1.0 - softness * 0.5, d + 0.25 * fray[np.ix_( ys, xs )] )
        field[np.ix_( ys, xs )] = np.maximum( field[np.ix_( ys, xs )], patch )
    return field


def segment_cells( rng, n, stones, squash, warp, k=12, chunk=128 ):
    """ Stones as short tilted segments (a centre, half-length, angle and weight each): every px goes to the stone whose
    segment is nearest (y counted squash times), less its weight. Tiles, as the stones are copied round the tile.
    Returns per px the stone, the distance to the next stone's cell (px, halved: to the joint's centre line) and the
    px's position along and across its stone. """
    from scipy.spatial import cKDTree
    centres = np.array( [ s[0] for s in stones ] )
    half = np.array( [ s[1] for s in stones ] )
    angle = np.array( [ s[2] for s in stones ] )
    weight = np.array( [ s[3] for s in stones ] )
    m = len( stones )
    shifts = [ ( ox * n, oy * n ) for ox in ( -1, 0, 1 ) for oy in ( -1, 0, 1 ) ]
    tiled = np.concatenate( [ centres + s for s in shifts ] )
    scale = np.array( ( 1.0, squash ) )
    tree = cKDTree( tiled * scale )
    cos, sin = np.cos( angle ), np.sin( angle )
    wx, wy = warp
    cell = np.empty( ( n, n ), int )
    border = np.empty( ( n, n ) )
    along = np.empty( ( n, n ) )
    across = np.empty( ( n, n ) )
    for r0 in range( 0, n, chunk ):
        y, x = np.mgrid[r0:r0 + chunk, 0:n] + 0.5
        px = np.stack( [ ( x + wx[r0:r0 + chunk] ).ravel(), ( y + wy[r0:r0 + chunk] ).ravel() ], -1 )
        _, idx = tree.query( px * scale, k=k )
        s = idx % m
        d = px[:, None, :] - tiled[idx]
        u = d[..., 0] * cos[s] + d[..., 1] * sin[s]
        v = -d[..., 0] * sin[s] + d[..., 1] * cos[s]
        dist = np.hypot( np.maximum( np.abs( u ) - half[s], 0.0 ), v * squash ) - weight[s]
        order = np.argsort( dist, axis=1 )
        first, second = order[:, 0], order[:, 1]
        rows = np.arange( len( px ) )
        cell[r0:r0 + chunk] = s[rows, first].reshape( chunk, n )
        border[r0:r0 + chunk] = ( ( dist[rows, second] - dist[rows, first] ) * 0.5 ).reshape( chunk, n )
        along[r0:r0 + chunk] = u[rows, first].reshape( chunk, n )
        across[r0:r0 + chunk] = v[rows, first].reshape( chunk, n )
    return cell, border, along, across


def per_stone( rng, count, *shape ):
    return rng.standard_normal( ( count, *shape ) )


# Rubble: the town wall, the garden and terrace walls. Limestone that weathers to warm greys and buffs, a few stones
# iron-stained or darker, in lime mortar.
RUBBLE_TILE = 160.0
RUBBLE_STONE = [ ( 170, 163, 150 ), ( 186, 178, 162 ), ( 154, 148, 138 ), ( 178, 162, 134 ), ( 142, 138, 131 ),
                 ( 198, 190, 174 ), ( 160, 138, 110 ), ( 128, 124, 118 ), ( 176, 170, 160 ), ( 168, 150, 128 ) ]
RUBBLE_MORTAR = ( 168, 160, 146 )


def rubble( rng, n ):
    """ Roughly coursed rubble: courses 4-11 inches high of stones one to three times as long as they're high, pinning
    stones between some. Each stone is a broken block bedded in lime mortar: its face split into a few flat planes,
    its arrises worn round and now and then chipped, its flanks going down into joints raked back half an inch to an
    inch. The shading comes from that shape (the normals and a broad AO), not from lines drawn round the stones: an
    earlier version darkened a thin ring round every stone, which read as an ink outline in the sun. """
    ppu = n / RUBBLE_TILE
    heights = []
    while sum( heights ) < RUBBLE_TILE:
        heights.append( rng.uniform( 4.5, 12.0 ) )
    heights = np.array( heights ) * RUBBLE_TILE / sum( heights ) * ppu
    stones = []
    top = 0.0
    for h in heights:
        start, covered = rng.uniform( 0, n ), 0.0
        while covered < n - 0.6 * h:
            length = min( h * rng.uniform( 0.9, 2.8 ), n - covered )
            if n - covered - length < 0.6 * h:
                length = n - covered
            cx = ( start + covered + length / 2 ) % n
            cy = ( top + h / 2 + rng.uniform( -0.15, 0.15 ) * h ) % n
            # A segment as long as the stone less its rounded ends, tilted up to 7 degrees.
            stones.append( ( ( cx, cy ), max( length / 2 - h * 0.45, 0.0 ), math.radians( rng.normal( 0, 3.5 ) ),
                             rng.uniform( -0.05, 0.12 ) * h, h, length ) )
            covered += length
        top += h
    # Pinning stones (galletting) squeezed into some joints.
    for _ in range( len( stones ) // 7 ):
        stones.append( ( ( rng.uniform( 0, n ), rng.uniform( 0, n ) ), 0.0, rng.uniform( 0, math.pi ),
                         -rng.uniform( 1.2, 2.2 ) * ppu, 2.4 * ppu, 2.4 * ppu ) )
    count = len( stones )
    size_h = np.array( [ s[4] for s in stones ] ) / ppu          # inches
    # Broken stone has straight-ish edges and blunt corners: the outline only wanders a little, and slowly.
    warp = ( noise( rng, n, 2.6, 3, 30 ) * 0.45 * ppu + noise( rng, n, 2.0, 16, 70 ) * 0.06 * ppu,
             noise( rng, n, 2.6, 3, 30 ) * 0.45 * ppu + noise( rng, n, 2.0, 16, 70 ) * 0.06 * ppu )
    cell, border, along, across = segment_cells( rng, n, [ s[:4] for s in stones ], 1.15, warp )
    b = border / ppu                                            # inches to the joint's centre line

    # Joints 0.4-0.75" each side of the line; now and then a bite out of an arris.
    joint = 0.55 + 0.12 * noise( rng, n, 2.4, 3, 30 )
    chips = np.maximum( noise( rng, n, 2.4, 6, 50 ) - 1.4, 0.0 ) * 0.7
    edge = b - joint - chips                                    # inches in from the stone's outline
    inside = smoothstep( -0.04, 0.04, edge )

    # How far the joints are raked back from the stones' arrises, and the mortar's own face: a little proud where it
    # was pointed up to the stones, sandy, with grit and the odd hole.
    recess = 0.75 + 0.22 * noise( rng, n, 2.4, 2, 24 ) + 0.25 * smoothstep( 0.8, 2.2, noise( rng, n, 2.8, 1, 10 ) )
    # Pressed up against each stone and hollowed between, flattening out (no slope) on the joint's centre line however
    # wide the joint is there, so no crease shows down the middle of a joint.
    u = np.clip( -edge / np.maximum( joint + chips, 0.2 ), 0.0, 1.0 )
    near = ( 1.0 - u ) ** 2                                     # 1 against a stone, 0 on the joint's centre line
    sand = noise( rng, n, 1.0, 120, None )
    holes = np.maximum( noise( rng, n, 1.6, 40, 300 ) - 2.2, 0.0 )
    mortar_h = -recess + 0.22 * near + 0.015 * sand + 0.04 * noise( rng, n, 2.2, 8, 80 ) - 0.12 * holes

    # The face: split planes over a low dome, standing 0.4-1.4" proud of the arrises.
    hs = size_h[cell]
    u_in, v_in = along / ppu, across / ppu
    crown = ( 0.55 + 0.6 * rng.random( count ) )[cell] * np.clip( hs / 8.0, 0.5, 1.35 )
    dome = crown * ( 1.0 - np.exp( -np.maximum( edge, 0.0 ) / ( 0.3 * hs ) ) )
    facets = np.full( ( n, n ), np.inf )
    for _ in range( 3 ):
        theta = rng.uniform( 0, 2 * math.pi, count )
        slope = np.tan( np.radians( rng.uniform( 4, 20, count ) ) )
        level = rng.uniform( 0.55, 1.0, count ) * ( 0.75 + 0.5 * rng.random( count ) )
        plane = ( level * np.clip( size_h / 8.0, 0.4, 1.3 ) )[cell] - slope[cell] * (
            np.cos( theta )[cell] * u_in + np.sin( theta )[cell] * v_in )
        facets = np.minimum( facets, plane )
    face = np.minimum( dome, np.maximum( facets, 0.35 * dome ) )
    # Broken stone isn't smooth: shallow conchoidal hollows and the ridges between them, an inch to a few across.
    ridges = 1.0 - np.abs( noise( rng, n, 2.0, 8, 60 ) )
    face += 0.14 * ( ridges - 0.6 ) + 0.06 * noise( rng, n, 1.8, 12, 160 )
    grain = noise( rng, n, 1.3, 40, None )
    pits = np.maximum( noise( rng, n, 1.4, 60, 500 ) - 2.0, 0.0 )
    face += 0.05 * noise( rng, n, 2.2, 6, 120 ) + 0.003 * grain - 0.04 * pits

    # The arris worn round: the flank comes up out of the mortar on a quarter circle about an inch across (less on
    # small stones), then the face carries on from there.
    radius = np.clip( 0.16 * hs, 0.5, 1.2 )
    t = np.clip( edge / radius, 0.0, 1.0 )
    arris = np.sqrt( 1.0 - ( 1.0 - t ) ** 2 )
    stone_h = mortar_h + ( recess - 0.22 * near + 0.1 ) * arris + face * smoothstep( 0.0, 1.0, t )
    height = np.where( edge > 0.0, np.maximum( stone_h, mortar_h ), mortar_h )

    # Colour, in linear light.
    base = to_linear( RUBBLE_STONE )[rng.integers( 0, len( RUBBLE_STONE ), count )]
    base *= rng.uniform( 0.7, 1.0, ( count, 1 ) ) * np.where( rng.random( ( count, 1 ) ) < 0.08, 0.72, 1.0 )
    stone = base[cell]
    mottle = noise( rng, n, 2.4, 3, 80 )
    fine = noise( rng, n, 1.1, 80, None )
    stone = stone * ( 1.0 + 0.07 * mottle + 0.035 * fine )[..., None]
    stain = smoothstep( 0.6, 2.2, noise( rng, n, 2.6, 3, 40 ) ) * ( rng.random( count ) < 0.3 )[cell]
    stone = lerp( stone, stone * to_linear( ( 214, 168, 118 ) ) / to_linear( ( 190, 190, 190 ) ), 0.55 * stain )
    # The weathered planes a touch lighter than the flanks, where dust and soot settle; chips show fresher stone.
    stone = stone * ( 0.86 + 0.16 * smoothstep( 0.0, 0.8, t ) )[..., None]
    stone = lerp( stone, base[cell] * 1.12, 0.6 * smoothstep( 0.05, 0.3, chips ) * inside )
    specks = smoothstep( 2.4, 3.2, noise( rng, n, 0.6, 200, None ) )
    stone = lerp( stone, stone * 0.6, specks * 0.5 )
    mortar = to_linear( RUBBLE_MORTAR ) * ( 0.93 + 0.07 * sand )[..., None]
    mortar = mortar * ( 0.84 + 0.1 * noise( rng, n, 2.0, 4, 60 ) )[..., None]
    # Dust and soot held in the mortar's sandy face, patchy across the wall.
    mortar = lerp( mortar, mortar * to_linear( ( 150, 146, 138 ) ) / to_linear( ( 184, 176, 160 ) ),
                   smoothstep( -0.5, 1.5, noise( rng, n, 2.6, 2, 30 ) ) )
    # Grit in the mortar: small dark and light grains.
    grit = noise( rng, n, 0.4, 300, None )
    mortar = lerp( mortar, mortar * 0.62, 0.5 * smoothstep( 1.6, 2.4, grit ) )
    mortar = lerp( mortar, mortar * 1.15, 0.5 * smoothstep( 1.6, 2.4, -grit ) )
    # Dirt lodged deep in the raked joints, and the holes.
    mortar = mortar * ( 1.0 - 0.22 * smoothstep( 0.8, 1.3, recess ) - 0.3 * smoothstep( 0.0, 0.08, holes ) )[..., None]
    colour = lerp( mortar, stone, inside )

    lichen_grey = spots( rng, n, 70, ( 0.6 * ppu, 2.4 * ppu ) ) * smoothstep( -0.2, 1.0, noise( rng, n, 3.0, 1, 6 ) )
    lichen_gold = spots( rng, n, 22, ( 0.4 * ppu, 1.3 * ppu ) )
    colour = lerp( colour, to_linear( ( 172, 176, 150 ) ) * ( 0.9 + 0.1 * fine )[..., None], 0.7 * lichen_grey * inside )
    colour = lerp( colour, to_linear( ( 196, 160, 84 ) ) * ( 0.9 + 0.1 * fine )[..., None], 0.75 * lichen_gold * inside )

    # Rain carries grime down from each joint: darker streaks under them, fading down the stone.
    runs = smoothstep( 0.5, 2.0, blur( noise( rng, n, 1.5, 20, 200 ), ( 0.1 * ppu, 0.02 * ppu ) ) )
    under = np.clip( 1.0 - np.abs( v_in ) / ( hs * 0.5 ), 0, 1 ) * ( v_in < 0 )
    grime = runs * smoothstep( 0.0, 1.0, np.roll( 1.0 - inside, int( 0.6 * ppu ), 0 ) + under * 0.3 )
    colour = colour * ( 1.0 - 0.15 * grime )[..., None]

    # The AO: broad, from how far each px sits below its surroundings over an inch or more, so a joint darkens across
    # its width rather than along the stones' edges.
    hollow = cavity( height, ppu, radii=( 1.0, 2.5, 5.0 ), weights=( 0.35, 0.3, 0.15 ) )
    colour = colour * np.exp( -0.35 * hollow )[..., None]
    rough = np.clip( 0.84 + 0.05 * fine - 0.05 * smoothstep( 0.2, 0.7, face ) * inside + 0.08 * ( 1 - inside )
                     + 0.04 * lichen_grey, 0.0, 1.0 )
    return { "rubble": to_srgb( colour ) }, height, rough, hollow, ppu


# Ashlar: the town hall, the belltower and the church, sills and string courses. Dressed limestone (warm) and granite
# (grey) blocks in thin lime joints.
ASHLAR_TILE = 128.0
ASHLAR_STONE = {
    "ashlar": [ ( 206, 194, 168 ), ( 196, 184, 160 ), ( 214, 204, 182 ), ( 188, 174, 150 ), ( 200, 186, 156 ),
                ( 182, 172, 152 ) ],
    "ashlar_grey": [ ( 150, 150, 146 ), ( 138, 139, 137 ), ( 160, 158, 152 ), ( 128, 130, 130 ), ( 146, 142, 136 ),
                     ( 156, 154, 150 ) ],
}


def ashlar( rng, n ):
    """ Courses 11-17 inches high, blocks 16-42 long, 3/8" joints. Each block's face a little out of true, dressed with
    fine parallel tool marks at its own angle, its arrises worn and chipped and now and then a corner spalled off;
    soot-dark and rain-washed patches, lichen. The granite is flecked. """
    import building_textures as BT
    ppu = n / ASHLAR_TILE
    block, u, v, length, course, row, count = BT.coursed( rng, n, ( 11 * ppu, 17 * ppu ), ( 16 * ppu, 42 * ppu ) )
    u_in, v_in, l_in, c_in = u / ppu, v / ppu, length / ppu, course / ppu
    wob = noise( rng, n, 2.0, 8, 120 ) * 0.025 + noise( rng, n, 1.5, 60, 400 ) * 0.01
    edge = np.minimum( np.minimum( u_in, l_in - u_in ), np.minimum( v_in, c_in - v_in ) ) + wob
    joint = 0.19
    # Chipped arrises: bites out of the blocks' edges, the stone's colour, not the mortar's.
    chips = np.maximum( noise( rng, n, 2.0, 6, 120 ) - 1.2, 0.0 ) * 0.2 + np.maximum( noise( rng, n, 1.8, 30, 250 ) - 1.8, 0.0 ) * 0.1
    # Spalls: a bite out of about one block in six, at one of its corners.
    spall = np.zeros( ( n, n ) )
    corner_u = rng.integers( 0, 2, count )[block] * l_in
    corner_v = rng.integers( 0, 2, count )[block] * c_in
    reach = ( rng.uniform( 1.5, 4.5, count ) * ( rng.random( count ) < 0.17 ) )[block]
    d_corner = np.hypot( u_in - corner_u, v_in - corner_v ) + 0.6 * noise( rng, n, 2.0, 12, 120 )
    spall = smoothstep( np.maximum( reach, 1e-3 ), np.maximum( reach, 1e-3 ) * 0.6, d_corner ) * ( reach > 0 )
    inside_edge = edge - joint - chips
    inside = smoothstep( -0.04, 0.04, inside_edge )
    in_block = smoothstep( -0.03, 0.03, edge - joint )
    broken = np.clip( in_block - inside, 0.0, 1.0 )
    bevel = smoothstep( 0.0, 0.45, inside_edge )

    tilt_u = rng.normal( 0, 0.05, count )[block] * ( u_in / l_in - 0.5 )
    tilt_v = rng.normal( 0, 0.05, count )[block] * ( v_in / c_in - 0.5 )
    bow = 0.04 * ( 1 - ( 2 * u_in / l_in - 1 ) ** 2 ) * ( 1 - ( 2 * v_in / c_in - 1 ) ** 2 )
    theta = rng.uniform( 0, math.pi, count )[block]
    period = rng.uniform( 0.28, 0.5, count )[block]
    phase = u_in * np.cos( theta ) + v_in * np.sin( theta )
    tooling = np.sin( 2 * math.pi * phase / period ) * ( 0.6 + 0.4 * noise( rng, n, 1.5, 20, 200 ) )
    tooled = ( rng.random( count ) < 0.75 )[block]
    face = 0.18 + tilt_u + tilt_v + bow + 0.012 * tooling * tooled
    face += 0.02 * noise( rng, n, 2.2, 4, 80 ) + 0.003 * noise( rng, n, 1.2, 60, None ) - 0.04 * np.maximum( noise( rng, n, 1.4, 80, 600 ) - 2.1, 0 )
    face -= spall * ( 0.35 + 0.08 * noise( rng, n, 1.5, 40, None ) )
    height = -0.1 + 0.006 * noise( rng, n, 1.0, 100, None ) + inside * ( 0.1 + bevel * ( face + 0.02 ) )

    fine = noise( rng, n, 1.1, 80, None )
    mottle = noise( rng, n, 2.6, 2, 60 )
    blotch = smoothstep( 0.2, 2.2, noise( rng, n, 3.0, 1, 10 ) )
    washed = smoothstep( 0.4, 2.0, blur( noise( rng, n, 1.6, 4, 120 ), ( 3.0 * ppu, 0.15 * ppu ) ) )
    runs = smoothstep( 0.8, 2.4, blur( noise( rng, n, 1.5, 20, 200 ), ( 1.2 * ppu, 0.05 * ppu ) ) )
    lichen = spots( rng, n, 45, ( 0.5 * ppu, 2.0 * ppu ) ) * smoothstep( 0.0, 1.2, noise( rng, n, 3.0, 1, 5 ) )
    hollow = cavity( height, ppu, radii=( 0.3, 1.0, 3.0 ), weights=( 1.0, 0.6, 0.3 ) )
    flecks = smoothstep( 1.6, 2.6, noise( rng, n, 0.2, 300, None ) )
    colours = {}
    for name, palette in ASHLAR_STONE.items():
        base = to_linear( palette )[rng.integers( 0, len( palette ), count )]
        base *= rng.uniform( 0.94, 1.05, ( count, 1 ) )
        stone = base[block] * ( 1.0 + 0.05 * mottle + 0.03 * fine )[..., None]
        if name == "ashlar_grey":
            stone = lerp( stone, stone * 1.5, flecks * 0.5 )
            stone = lerp( stone, stone * 0.45, smoothstep( 1.8, 2.8, -noise( rng, n, 0.2, 300, None ) ) * 0.6 )
        stone = lerp( stone, stone * 0.62, 0.45 * blotch )                   # soot and old grime
        stone = lerp( stone, stone * 1.12, 0.5 * washed )                    # washed clean by the rain
        stone = stone * ( 1.0 - 0.14 * runs )[..., None]
        stone = stone * ( 0.9 + 0.1 * bevel )[..., None]
        stone = lerp( stone, stone * 0.8, spall * 0.7 )
        stone = lerp( stone, to_linear( ( 176, 178, 154 ) ) * ( 0.92 + 0.08 * fine )[..., None], 0.6 * lichen )
        # Fresh breaks are a little lighter than the weathered face.
        stone = lerp( stone, base[block] * 1.15, 0.6 * broken )
        mortar = to_linear( ( 150, 146, 136 ) ) * ( 0.85 + 0.06 * fine )[..., None]
        colour = lerp( mortar, stone, in_block ) * np.exp( -1.2 * hollow )[..., None]
        colours[name] = to_srgb( colour )
    rough = np.clip( 0.8 + 0.05 * fine + 0.08 * ( 1 - in_block ) + 0.05 * broken + 0.04 * spall - 0.04 * washed, 0.0, 1.0 )
    return colours, height, rough, hollow, ppu


STONES = { "rubble": ( rubble, 2048, 71, 1.0 ), "ashlar": ( ashlar, 2048, 72, 1.0 ) }


def stone_material( name ):
    draw, size, seed, strength = STONES[name]
    colours, height, rough, hollow, ppu = draw( np.random.default_rng( seed ), size )
    normal = gl_normal( height, ppu, strength )
    ao = np.clip( np.exp( -1.6 * hollow ), 0.0, 1.0 )
    save_rgb( OUT_DIR / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( OUT_DIR / f"{name}_rough.png", rough )
    save_grey( OUT_DIR / f"{name}_ao.png", ao )
    for paint, colour in colours.items():
        save_rgb( OUT_DIR / f"{paint}_color.png", colour )
        write_vmat( paint, vmat( f"{RESOURCE_DIR}/{paint}_color.png", f"{RESOURCE_DIR}/{name}_normal.png",
                                 f"{RESOURCE_DIR}/{name}_rough.png", f"{RESOURCE_DIR}/{name}_ao.png" ) )
    SHEETS[name] = ( colours, normal, height )
    return rough


# ---------------------------------------------------------------------------------------------------------------------
# Canvas and produce

PARASOL_TILE = 48.0
PARASOLS = { "parasol_red": ( 146, 38, 36 ), "parasol_cream": ( 216, 206, 182 ), "parasol_blue": ( 36, 70, 122 ) }


def parasol():
    """ Heavy cotton duck, one colour a gore: the weave's ribs, slubs and a little sun-fading and grime. 48 units a
    tile, 1024 px. """
    rng = np.random.default_rng( 81 )
    n = 1024
    ppu = n / PARASOL_TILE
    y, x = np.mgrid[0:n, 0:n] + 0.5
    # Warp and weft at 2.5 threads to the unit (a canvas's ribs seen from a few feet), each thread a little uneven.
    period = n / 120
    warp = np.sin( 2 * np.pi * x / period + 0.6 * noise( rng, n, 1.5, 8, 64 ) )
    weft = np.sin( 2 * np.pi * y / period + 0.6 * noise( rng, n, 1.5, 8, 64 ) )
    slub = np.maximum( noise( rng, n, 1.2, 40, 200 ) - 1.2, 0.0 )
    height = 0.012 * np.where( weft > 0, warp, weft ) + 0.01 * slub
    blotch = noise( rng, n, 2.6, 1, 10 )
    # In linear light even a little of the sun-bleached colour lifts a dark dye's weak channels a lot.
    fade = smoothstep( -1.5, 2.5, noise( rng, n, 3.2, 1, 4 ) ) * 0.035
    grime = smoothstep( 1.2, 2.8, noise( rng, n, 2.6, 1, 8 ) ) * 0.1
    lum = 1.0 + 0.035 * warp * weft + 0.03 * blotch - 0.05 * slub
    colours = {}
    for name, rgb in PARASOLS.items():
        dyed = to_linear( np.array( rgb, float ) ) * lum[..., None]
        sun = to_linear( np.array( ( 226, 214, 192 ), float ) ) * lum[..., None]
        dirty = to_linear( np.array( ( 92, 84, 70 ), float ) ) * lum[..., None]
        faded = lerp( dyed, sun, fade * ( 0.6 if name == "parasol_cream" else 1.0 ) )
        colours[name] = to_srgb( lerp( faded, dirty, grime ) )
    normal = gl_normal( height, ppu, 1.0 )
    rough = np.clip( 0.86 + 0.04 * warp * weft - 0.03 * grime + 0.02 * blotch, 0.0, 1.0 )
    save_rgb( OUT_DIR / "parasol_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( OUT_DIR / "parasol_rough.png", rough )
    for paint, colour in colours.items():
        save_rgb( OUT_DIR / f"{paint}_color.png", colour )
        write_vmat( paint, vmat( f"{RESOURCE_DIR}/{paint}_color.png", f"{RESOURCE_DIR}/parasol_normal.png",
                                 f"{RESOURCE_DIR}/parasol_rough.png", "materials/default/default_ao.tga" ) )
    return rough


# kind: ( radius in inches, height / width, length / width seen from above ). A kind's pile repeats every PILE_ACROSS
# fruit across and PILE_ROWS rows down, each row shifted by half a fruit: hexagonal packing, in a square tile of
# produce_tile( kind ) inches.
PRODUCE = {
    "apple_red": ( 1.6, 0.9, 1.0 ), "apple_green": ( 1.6, 0.9, 1.0 ), "orange": ( 1.65, 0.95, 1.0 ),
    "lemon": ( 1.25, 0.85, 1.3 ), "tomato": ( 1.35, 0.8, 1.0 ), "potato": ( 1.35, 0.7, 1.4 ),
    "onion": ( 1.5, 0.95, 1.0 ), "cabbage": ( 3.2, 0.85, 1.0 ),
}
PILE_ACROSS, PILE_ROWS = 7, 8
PILE_PX = 1024
# The skins are drawn this size, tiling, and each fruit takes its piece from anywhere on it.
SKIN_SOURCE_PX = 512


def produce_tile( kind ):
    return PRODUCE[kind][0] * 2 * PILE_ACROSS * PRODUCE[kind][2] ** 0.5


def produce_skin( rng, kind, n ):
    """ One kind's skin, n px square: colour (linear), height (inches) and roughness. The cabbage's whole square is
    one head, its veins spreading from the middle. """
    y, x = np.mgrid[0:n, 0:n] + 0.5
    low = noise( rng, n, 2.6, 1, 6 )
    mid = noise( rng, n, 2.0, 4, 24 )
    fine = noise( rng, n, 1.2, 30, 128 )

    def dots( count, r ):
        return spots( rng, n, count, r, 0.3 )

    def rgb( c ):
        return to_linear( np.array( c, float ) )

    height = 0.004 * fine
    if kind in ( "apple_red", "apple_green" ):
        base, blush = ( ( 132, 18, 24 ), ( 178, 70, 36 ) ) if kind == "apple_red" else ( ( 150, 176, 62 ), ( 186, 150, 58 ) )
        # The blush in soft flecks drawn out one way, as on a real apple, never hard patches.
        streak = ndimage.gaussian_filter( noise( rng, n, 1.6, 2, 60 ), ( 10.0, 1.5 ), mode="wrap" )
        streak /= streak.std() + 1e-9
        t = np.clip( 0.35 + 0.25 * low + 0.2 * streak, 0.0, 1.0 ) * ( 0.7 if kind == "apple_red" else 0.4 )
        colour = lerp( rgb( base ), rgb( blush ), t ) * ( 1.0 + 0.08 * mid + 0.03 * fine )[..., None]
        lenticel = dots( 180, ( 0.8, 1.8 ) )
        colour = lerp( colour, rgb( ( 214, 196, 150 ) ), 0.35 * lenticel )
        rough = 0.44 + 0.06 * mid + 0.2 * lenticel
    elif kind in ( "orange", "lemon" ):
        base = ( 222, 110, 18 ) if kind == "orange" else ( 222, 192, 42 )
        colour = rgb( base ) * ( 1.0 + 0.07 * low + 0.05 * mid )[..., None]
        pores = dots( 1400, ( 1.2, 2.4 ) )
        height = height - 0.03 * pores + 0.01 * mid
        colour *= ( 1.0 - 0.18 * pores )[..., None]
        rough = 0.48 + 0.12 * pores + 0.04 * mid
    elif kind == "tomato":
        colour = rgb( ( 176, 24, 16 ) ) * ( 1.0 + 0.1 * low + 0.04 * mid )[..., None]
        colour = lerp( colour, rgb( ( 206, 96, 30 ) ), smoothstep( 1.2, 2.4, low ) * 0.5 )
        rough = 0.32 + 0.05 * mid
    elif kind == "potato":
        colour = rgb( ( 168, 132, 88 ) ) * ( 1.0 + 0.12 * mid + 0.06 * fine )[..., None]
        soil = smoothstep( 0.6, 2.0, mid + 0.6 * low )
        colour = lerp( colour, rgb( ( 96, 72, 50 ) ), 0.6 * soil )
        eyes = dots( 40, ( 3.0, 6.0 ) )
        colour *= ( 1.0 - 0.45 * eyes )[..., None]
        height = 0.03 * mid + 0.012 * fine - 0.06 * eyes
        rough = 0.86 + 0.06 * soil
    elif kind == "onion":
        # Papery skin in streaks round the bulb.
        streak = ndimage.gaussian_filter( noise( rng, n, 1.4, 2, 90 ), ( 0.0, 12.0 ), mode="wrap" )
        streak /= streak.std() + 1e-9
        colour = rgb( ( 176, 98, 46 ) ) * ( 1.0 + 0.16 * streak + 0.06 * low )[..., None]
        flake = smoothstep( 1.4, 2.4, mid )
        colour = lerp( colour, rgb( ( 214, 176, 128 ) ), 0.5 * flake )
        height = 0.01 * streak
        rough = 0.62 + 0.1 * flake + 0.04 * streak
    else:
        # Cabbage: veins branching from the centre, pale against the leaf.
        angle = np.arctan2( y - n / 2, x - n / 2 )
        radius = np.hypot( x - n / 2, y - n / 2 ) / n
        vein = np.exp( -( np.sin( angle * 7 + 3.0 * radius + 0.4 * low ) ** 2 ) / 0.006 ) * smoothstep( 0.02, 0.1, radius )
        branch = np.exp( -( np.sin( angle * 23 - 9.0 * radius + 0.6 * mid ) ** 2 ) / 0.01 ) * 0.5
        veins = np.clip( vein + branch * smoothstep( 0.15, 0.4, radius ), 0.0, 1.0 )
        colour = rgb( ( 96, 138, 64 ) ) * ( 1.0 + 0.12 * low + 0.08 * mid )[..., None]
        colour = lerp( colour, rgb( ( 186, 206, 140 ) ), 0.6 * veins )
        height = 0.02 * veins + 0.015 * mid + 0.004 * fine
        rough = 0.52 + 0.1 * mid - 0.1 * veins
    return colour, height, np.clip( rough, 0.0, 1.0 )


# Kinds whose skin is streaked from the stalk: ( the skin axis the streaks run along (0: down its rows, 1: along them),
# how much of the skin a fruit radius covers along them ).
STREAKED = { "apple_red": ( 0, 0.15 ), "apple_green": ( 0, 0.15 ), "onion": ( 1, 0.45 ) }
# Kinds that show a stalk end where it's turned up (stem_end).
POLED = ( "apple_red", "apple_green", "tomato", "onion", "orange" )


def streak_lookup( kind, du, dv, n, oy, ox ):
    """ Skin rows and columns for a streaked kind, du and dv from the stalk in fruit radii: the streaks radiate from it. """
    axis, reach = STREAKED[kind]
    radial = ( np.hypot( du, dv ) * n * reach ).astype( int ) + oy
    around = ( ( np.arctan2( dv, du ) / ( 2 * np.pi ) + 0.5 ) * n ).astype( int ) + ox
    return ( radial % n, around % n ) if axis == 0 else ( around % n, radial % n )


def stem_end( rng, kind, du, dv, radius ):
    """ What a fruit shows at its stalk end, du and dv from it in fruit radii: [ ( weight, linear colour, roughness ) ]
    to paint over the skin in order, and the height it adds (inches). """
    rho = np.hypot( du, dv )
    layers, height = [], np.zeros_like( rho )

    def rgb( c ):
        return to_linear( np.array( c, float ) )

    if kind in ( "apple_red", "apple_green" ):
        # The hollow round the stalk, russeted, and the stalk lying in it.
        hollow = np.exp( -( rho / 0.24 ) ** 2 )
        b = rng.uniform( 0, 2 * np.pi )
        along = du * np.cos( b ) + dv * np.sin( b )
        across = -du * np.sin( b ) + dv * np.cos( b )
        stalk = smoothstep( 0.065, 0.035, np.abs( across ) ) * smoothstep( -0.04, 0.0, along ) * smoothstep( 0.26, 0.21, along )
        height = -0.2 * radius * hollow * ( 1.0 - stalk ) + 0.04 * radius * stalk
        layers += [ ( 0.7 * hollow, rgb( ( 112, 100, 48 ) ), 0.7 ), ( stalk, rgb( ( 72, 50, 28 ) ), 0.75 ) ]
    elif kind == "tomato":
        # The calyx: a five-pointed star of sepals round a stub of stalk.
        theta = np.arctan2( dv, du ) + rng.uniform( 0, 2 * np.pi )
        star = smoothstep( 1.0, 0.8, rho / ( 0.3 * ( 0.28 + 0.72 * np.abs( np.cos( 2.5 * theta ) ) ** 3 ) ) )
        stub = smoothstep( 0.07, 0.045, rho )
        height = 0.025 * radius * star + 0.05 * radius * stub
        layers += [ ( star, rgb( ( 52, 84, 26 ) ), 0.7 ), ( stub, rgb( ( 88, 110, 48 ) ), 0.75 ) ]
    elif kind == "onion":
        # The dry neck the leaves grew from.
        tip = smoothstep( 0.16, 0.06, rho )
        height = -0.06 * radius * np.exp( -( rho / 0.22 ) ** 2 ) + 0.03 * radius * tip
        layers += [ ( tip, rgb( ( 104, 66, 34 ) ), 0.85 ) ]
    elif kind == "orange":
        # The button where the stalk was.
        button = smoothstep( 0.08, 0.04, rho )
        height = -0.01 * radius * button
        layers += [ ( 0.8 * button, rgb( ( 120, 112, 46 ) ), 0.7 ) ]
    return layers, height


def produce_pile( kind ):
    """ A kind's crate seen from above, tiling: two layers of fruit packed a little unevenly, each fruit with its own
    piece of skin, the lower layer showing dark in the top one's gaps.
    Returns colour (sRGB), height (inches), roughness, px to the inch and the skin (produce_skin's). """
    rng = np.random.default_rng( 90 + list( PRODUCE ).index( kind ) )
    radius, squash, aspect = PRODUCE[kind]
    n = PILE_PX
    m = SKIN_SOURCE_PX
    ppu = n / produce_tile( kind )
    skin = produce_skin( rng, kind, m )
    skin_colour, skin_height, skin_rough = skin
    centres = []
    # ( lattice shift across and down, lift range, scale range, shade ): the layer below sits in the top one's hollows.
    for shift, lifts, scales, shade in ( ( ( 0.5, 1 / 3 ), ( -1.0, -0.75 ), ( 0.95, 1.05 ), 0.45 ),
                                         ( ( 0.0, 0.0 ), ( -0.2, 0.15 ), ( 0.92, 1.03 ), 1.0 ) ):
        for j in range( PILE_ROWS ):
            for i in range( PILE_ACROSS ):
                x = ( i + 0.5 + 0.5 * ( j % 2 ) + shift[0] + rng.normal( 0, 0.05 ) ) * n / PILE_ACROSS
                y = ( j + 0.5 + shift[1] + rng.normal( 0, 0.05 ) ) * n / PILE_ROWS
                centres.append( ( x % n, y % n, rng.uniform( *scales ), rng.uniform( *lifts ), rng.uniform( 0, np.pi ),
                                  shade ) )

    height = np.full( ( n, n ), -2.0 * radius * squash )
    colour = np.tile( skin_colour, ( n // m, n // m, 1 ) ) * 0.03
    rough = np.full( ( n, n ), 0.85 )
    for cx, cy, scale, lift, turn, shade in centres:
        a = radius * scale * ppu
        reach = int( a * aspect ) + 2
        ys = np.arange( int( cy ) - reach, int( cy ) + reach + 1 )
        xs = np.arange( int( cx ) - reach, int( cx ) + reach + 1 )
        yy, xx = np.meshgrid( ys + 0.5 - cy, xs + 0.5 - cx, indexing="ij" )
        u = ( xx * np.cos( turn ) + yy * np.sin( turn ) ) / ( a * aspect )
        v = ( -xx * np.sin( turn ) + yy * np.cos( turn ) ) / a
        d2 = u * u + v * v
        dome = radius * scale * squash * ( np.sqrt( np.clip( 1 - d2, 0, 1 ) ) + lift )
        window = np.ix_( ys % n, xs % n )
        on_top = ( d2 < 1 ) & ( dome > height[window] )
        # Each fruit's stalk end is somewhere on it, often round the side, out of sight.
        if kind in POLED:
            b, reach_out = rng.uniform( 0, 2 * np.pi ), rng.uniform( 0.0, 1.3 )
            du, dv = u - reach_out * np.cos( b ), v - reach_out * np.sin( b )
        if kind in STREAKED:
            oy, ox = rng.integers( 0, m, 2 )
            sy, sx = streak_lookup( kind, du, dv, m, oy, ox )
        elif kind == "cabbage":
            # The head's veins spread from its own middle.
            sy = np.clip( ( m / 2 + v * m * 0.42 ).astype( int ), 0, m - 1 )
            sx = np.clip( ( m / 2 + u * m * 0.42 ).astype( int ), 0, m - 1 )
        else:
            oy, ox = rng.integers( 0, m, 2 )
            sy, sx = ( ys[:, None] + oy ) % m + 0 * xs[None, :], ( xs[None, :] + ox ) % m + 0 * ys[:, None]
        # The sides that turn down into the heap get less of the sky.
        tint = shade * rng.uniform( 0.86, 1.1 ) * ( 1.0 - 0.4 * np.clip( d2, 0, 1 ) ** 1.5 )
        fruit_colour, fruit_height, fruit_rough = skin_colour[sy, sx], skin_height[sy, sx], skin_rough[sy, sx]
        if kind in POLED:
            layers, lift_by = stem_end( rng, kind, du, dv, radius * scale )
            fruit_height = fruit_height + lift_by
            for weight, paint, roughness in layers:
                fruit_colour = lerp( fruit_colour, paint, weight )
                fruit_rough = fruit_rough + ( roughness - fruit_rough ) * weight
        h = height[window]
        c = colour[window]
        r = rough[window]
        h[on_top] = dome[on_top] + fruit_height[on_top]
        c[on_top] = fruit_colour[on_top] * tint[on_top][:, None]
        r[on_top] = fruit_rough[on_top]
        height[window], colour[window], rough[window] = h, c, r
    # The gaps between the fruit, and the undersides of the ones leaning on their neighbours, darken.
    hollow = cavity( height, ppu, radii=( 0.25 * radius, 0.6 * radius ), weights=( 1.0, 0.6 ) )
    colour = colour * np.clip( np.exp( -1.2 * hollow / radius ), 0.15, 1.0 )[..., None]
    return to_srgb( colour ), height, rough, ppu, skin


# The loose fruit's skins, one square each in a row (produce_skin.vmat), so a V flip leaves each in its square.
SKIN_PX = 256


def skin_window( kind ):
    """ Where a kind's loose fruit sits in produce_skin's atlas: ( u, v ) of its middle and its half width and height
    in UV, seen from above. """
    radius, _, aspect = PRODUCE[kind]
    k = list( PRODUCE ).index( kind )
    # The skin at the pile's own px to the inch; the cabbage's whole head is shrunk into its square.
    half = 0.42 * SKIN_PX if kind == "cabbage" else radius * PILE_PX / produce_tile( kind )
    return ( k + 0.5 ) / len( PRODUCE ), 0.5, half * ( 1.0 if kind == "cabbage" else aspect ) / ( SKIN_PX * len( PRODUCE ) ), \
        half / SKIN_PX


def produce():
    """ A material per kind, produce_<kind>.vmat (PILE_PX square), and the loose fruit's produce_skin.vmat. """
    skins, skin_normals, skin_roughs = [], [], []
    for kind in PRODUCE:
        colour, height, rough, ppu, ( skin, skin_height, skin_rough ) = produce_pile( kind )
        normal = gl_normal( height, ppu, 1.0 )
        name = f"produce_{kind}"
        save_rgb( OUT_DIR / f"{name}_color.png", colour )
        save_rgb( OUT_DIR / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
        save_grey( OUT_DIR / f"{name}_rough.png", rough )
        write_vmat( name, vmat( f"{RESOURCE_DIR}/{name}_color.png", f"{RESOURCE_DIR}/{name}_normal.png",
                                f"{RESOURCE_DIR}/{name}_rough.png", "materials/default/default_ao.tga" ) )
        SHEETS[name] = ( { name: colour }, normal, height )
        if kind == "cabbage":
            half = SKIN_SOURCE_PX // 2
            skins.append( skin.reshape( half, 2, half, 2, 3 ).mean( ( 1, 3 ) ) )
            skin_height = skin_height.reshape( half, 2, half, 2 ).mean( ( 1, 3 ) )
            skin_rough = skin_rough.reshape( half, 2, half, 2 ).mean( ( 1, 3 ) )
            skin_ppu = 0.42 * SKIN_PX / PRODUCE[kind][0]
        else:
            skin_ppu = ppu
            full = ( skin, skin_height, skin_rough )
            skin, skin_height, skin_rough = ( a[:SKIN_PX, :SKIN_PX] for a in full )
            if kind in POLED:
                rng = np.random.default_rng( 190 + list( PRODUCE ).index( kind ) )
                _, _, hu, hv = skin_window( kind )
                yy, xx = np.mgrid[0:SKIN_PX, 0:SKIN_PX] + 0.5 - SKIN_PX / 2
                du, dv = xx / ( hu * SKIN_PX * len( PRODUCE ) ), yy / ( hv * SKIN_PX )
                if kind in STREAKED:
                    sy, sx = streak_lookup( kind, du, dv, SKIN_SOURCE_PX, 0, 0 )
                    skin, skin_height, skin_rough = ( a[sy, sx] for a in full )
                layers, lift_by = stem_end( rng, kind, du, dv, PRODUCE[kind][0] )
                skin_height = skin_height + lift_by
                for weight, paint, roughness in layers:
                    skin = lerp( skin, paint, weight )
                    skin_rough = skin_rough + ( roughness - skin_rough ) * weight
            skins.append( skin )
        skin_normals.append( gl_normal( skin_height, skin_ppu, 1.0 ) )
        skin_roughs.append( skin_rough )
    colour = to_srgb( np.concatenate( skins, axis=1 ) )
    normal = np.concatenate( skin_normals, axis=1 )
    save_rgb( OUT_DIR / "produce_skin_color.png", colour )
    save_rgb( OUT_DIR / "produce_skin_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( OUT_DIR / "produce_skin_rough.png", np.concatenate( skin_roughs, axis=1 ) )
    write_vmat( "produce_skin", vmat( f"{RESOURCE_DIR}/produce_skin_color.png", f"{RESOURCE_DIR}/produce_skin_normal.png",
                                      f"{RESOURCE_DIR}/produce_skin_rough.png", "materials/default/default_ao.tga" ) )
    return rough


SHEETS = {}
MATERIALS = { "cobbles": cobbles, "flagstones": flagstones, "rubble": lambda: stone_material( "rubble" ),
              "ashlar": lambda: stone_material( "ashlar" ), "parasol": parasol, "produce": produce }


def write_sheet( path ):
    """ Each stone paint tiled 2x2 and lit from the top left, then a close-up of a quarter tile, then the height. """
    light = np.array( ( -0.45, 0.55, 0.7 ) )
    light /= np.linalg.norm( light )
    rows = []
    for name, ( colours, normal, height ) in SHEETS.items():
        ndl = np.clip( np.sum( normal * light, -1 ), 0, 1 )
        for paint, colour in colours.items():
            shaded = np.clip( colour * ( 0.35 + 0.8 * ndl )[..., None], 0, 255 ).astype( np.uint8 )
            tiled = Image.fromarray( np.tile( shaded, ( 2, 2, 1 ) ) ).resize( ( 768, 768 ), Image.LANCZOS )
            q = shaded.shape[0] // 4
            close = Image.fromarray( shaded[:q, :q] ).resize( ( 768, 768 ), Image.LANCZOS )
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
    global OUT_DIR
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"materials to write (default all: {', '.join( MATERIALS )})" )
    parser.add_argument( "--out", help="write here instead of Assets/materials/belltower" )
    parser.add_argument( "--sheet", help="also write a lit picture of the stone here" )
    args = parser.parse_args()
    if args.out:
        OUT_DIR = Path( args.out )
    OUT_DIR.mkdir( parents=True, exist_ok=True )
    for name in args.names or list( MATERIALS ):
        rough = MATERIALS[name]()
        print( f"{name}: roughness mean {rough.mean():.2f}, 5-95% {np.percentile( rough, 5 ):.2f}-"
               f"{np.percentile( rough, 95 ):.2f}" )
    if args.sheet:
        write_sheet( args.sheet )


if __name__ == "__main__":
    main()
