"""
Cerro Blanco's woods, for Tools/cerroblanco_landscape.py: the encinos and the scrub on the hill and the sierra, drawn
as photographic tree cards (alpha tested, no collision), where the landscape drew veridant_backdrop.blob domes that read
as dark balls from the galleries' upper floors and from the air.

- The atlas is Belltower's generated forest-trees-v1.png (Sources/Belltower/generated: a broad holm oak, a deciduous
  oak, an olive and a rounded holm oak, its .json has the prompt). Each tree is cut out by its own alpha (the bottom
  two touch), repacked into a quarter of a 2048 atlas standing on its foot, and its colour bled into the clear texels,
  so the mips don't halo dark. Three tints share the alpha: green (as photographed), dry (the dry season's dusty olive)
  and dark (the evergreen encinos in the hollows).
- Where the blobs were: the landscape's woodland noise, slope and height rules, 700-22000 out. But spread evenly over
  the land (a little thicker near the play), where the blobs' distances were drawn as 900 + 21000 u^1.7, which made
  them ~30 times as thick by the walls as 15000 out (crowns about four deep there: a wall of them). Trees (6-12 m,
  the olives lower) where the woodland is thick, scrub (a tree's crown alone, 1.5-3 m, sunk to the ground) at its
  edges, on the steep and high ground and mostly near the play, where a bush is still bigger than a few pixels. Both a
  little larger far out.
- Each card stands on its base, sunk a few inches, facing the play's centre (a little off it), with a random tree,
  mirroring, lean and size. Scrub follows the ground across its width. The nearest trees (< NEAR out) get a second
  layer of crown, set back and turned off the first, so they don't go paper-thin seen from the side. (A card across
  the first, as an X, showed as a spike wherever it was edge-on to the play.)
- Both faces are drawn, the back a quarter-inch behind the front (coincident, they fight, and a ray tracer skips the
  front after stepping through the culled back: the woods rendered half see-through). Their normals point mostly up
  and bow out like a crown's (the same on both layers of a tree), so the sun lights the woods as foliage rather than as
  signs. The woods cast no shadows (cerroblanco_map's "Backdrop Woods" renderer).

build( C, height, seed=27, avoid=() ) returns the model (height is cerroblanco_landscape.height; avoid: plan points,
the cloud oaks', to keep the cards off). write_materials( root ) writes the atlas and its vmats under root / RESOURCE.

    python Tools/cerroblanco_trees.py [--out output/cerroblanco/trees-preview]

writes the model and the materials there, laid out like Assets, and a sheet of the atlas's tints.
"""
import argparse
import functools
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

import map_kit as K
from map_kit import Model
import veridant_backdrop as VB

RESOURCE = "materials/cerroblanco/fitout"
SOURCE = K.ROOT / "Sources/Belltower/generated/forest-trees-v1.png"
SIZE = 2048                         # the atlas: a power of two (others failed to compile in this engine)
MARGIN = 24                         # clear texels round each tree in its quarter, for the mips
# The source's trees, by quarter ( column, row from the top ), as they're packed.
SPECIES = ( ( "holm", 0, 0 ), ( "oak", 1, 0 ), ( "olive", 0, 1 ), ( "holm_round", 1, 1 ) )
# A tree's height in inches: holm and live oaks 6-12 m, the deciduous oak taller, the olives low and wide.
TREE_HEIGHT = { "holm": ( 240, 440 ), "oak": ( 300, 470 ), "olive": ( 190, 320 ), "holm_round": ( 230, 400 ) }
TREE_SHARE = { "holm": 0.36, "oak": 0.14, "olive": 0.14, "holm_round": 0.36 }
SCRUB_SHARE = { "holm": 0.36, "oak": 0.04, "olive": 0.26, "holm_round": 0.34 }
SCRUB_HEIGHT = ( 59, 118 )          # 1.5-3 m above the ground
# The tints, multiplying the photograph's colour: ( paint, ( r, g, b ) gain, share of the way to its dusty grey ).
TINTS = {
    "cbf_tree_green": ( ( 0.97, 1.0, 0.97 ), 0.0 ),
    "cbf_tree_dry": ( ( 1.07, 1.03, 0.9 ), 0.45 ),
    "cbf_tree_dark": ( ( 0.70, 0.79, 0.74 ), 0.0 ),
}
TRANS = "cbf_tree_trans"
TREES, SCRUB = 6500, 6000           # how many of each
REACH = 22000.0                     # the woods' reach from the play's edge, as the blobs had
NEAR = 3000.0                       # nearer than this (from the play's edge), a tree has a second layer of crown
SCRUB_REACH = 9000.0                # no scrub further out than this
UP = np.array( ( 0.0, 0.0, 1.0 ) )


def unit( a ):
    return a / np.linalg.norm( a )


# ---------------------------------------------------------------------------------------------------------------------
# The atlas

@functools.lru_cache( None )
def cutouts():
    """ The four trees, each cut out by its own alpha: ( name, straight RGBA crop, crown's foot as a share of its height
    up from the trunk's foot ). """
    src = np.asarray( Image.open( SOURCE ).convert( "RGBA" ), float ) / 255.0
    a = src[..., 3]
    lab, count = ndimage.label( a > 0.3 )
    sizes = ndimage.sum( np.ones_like( a ), lab, range( 1, count + 1 ) )
    big = list( np.argsort( sizes )[-4:] + 1 )
    centres = ndimage.center_of_mass( np.ones_like( a ), lab, big )
    # Every texel belongs to the nearest of the four; specks far from all of them are dropped.
    dist, ( iy, ix ) = ndimage.distance_transform_edt( ~np.isin( lab, big ), return_indices=True )
    owner = lab[iy, ix]
    keep = ( a > 0.0 ) & ( dist < 24 )
    h, w = a.shape
    out = []
    for name, col, row in SPECIES:
        k = next( big[i] for i, ( y, x ) in enumerate( centres ) if int( x >= w / 2 ) == col and int( y >= h / 2 ) == row )
        alpha = np.where( keep & ( owner == k ), a, 0.0 )
        ys, xs = np.nonzero( alpha > 0.05 )
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crop = src[y0:y1, x0:x1].copy()
        crop[..., 3] = alpha[y0:y1, x0:x1]
        # The crown's foot: from the trunk's foot up, the first row at least 40% as wide as the widest.
        width = ( crop[..., 3] > 0.3 ).sum( 1 )
        rows = np.nonzero( width >= 0.4 * width.max() )[0]
        out.append( ( name, crop, float( ( crop.shape[0] - rows.max() ) / crop.shape[0] ) ) )
    return tuple( out )


def resize_rgba( rgba, size ):
    """ Lanczos, premultiplied, so the clear texels' black doesn't creep into the edges. """
    w, h = size
    a = rgba[..., 3]
    chans = [ rgba[..., c] * a for c in range( 3 ) ] + [ a ]
    out = np.stack( [ np.asarray( Image.fromarray( c.astype( np.float32 ), "F" ).resize( ( w, h ), Image.LANCZOS ) )
                      for c in chans ], -1 ).astype( float )
    out[..., 3] = np.clip( out[..., 3], 0.0, 1.0 )
    out[..., :3] = np.clip( out[..., :3] / np.maximum( out[..., 3:], 1e-4 ), 0.0, 1.0 )
    return out


def bleed( rgb, solid ):
    """ The clear texels take the colour of the nearest leaves, pulled down a pyramid and pushed back up, smoothed. """
    levels = [ ( rgb * solid[..., None], solid.astype( float ) ) ]
    while levels[-1][1].shape[0] > 1:
        c, wt = levels[-1]
        h, w = wt.shape
        levels.append( ( c.reshape( h // 2, 2, w // 2, 2, 3 ).sum( ( 1, 3 ) ), wt.reshape( h // 2, 2, w // 2, 2 ).sum( ( 1, 3 ) ) ) )
    fill = levels[-1][0] / np.maximum( levels[-1][1], 1e-9 )[..., None]
    for c, wt in reversed( levels[:-1] ):
        up = ndimage.uniform_filter( np.repeat( np.repeat( fill, 2, 0 ), 2, 1 ), size=( 3, 3, 1 ), mode="nearest" )
        here = c / np.maximum( wt, 1e-9 )[..., None]
        fill = np.where( ( wt > 0 )[..., None], here, up )
    return np.where( solid[..., None], rgb, fill )


@functools.lru_cache( None )
def packed():
    """ The atlas ( straight RGBA, SIZE square, bled ) and each tree's cell: ( name, ( u0, v0, u1, v1 ) with v up the
    picture as the OBJ has it, width over height, crown's foot ). """
    cell = SIZE // 2
    rgba = np.zeros( ( SIZE, SIZE, 4 ) )
    cells = []
    for i, ( name, crop, crown ) in enumerate( cutouts() ):
        col, row = i % 2, i // 2
        h, w = crop.shape[:2]
        s = min( ( cell - 2 * MARGIN ) / w, ( cell - 2 * MARGIN ) / h )
        W, H = int( round( w * s ) ), int( round( h * s ) )
        x0 = col * cell + ( cell - W ) // 2
        y1 = row * cell + cell - MARGIN
        rgba[y1 - H:y1, x0:x0 + W] = resize_rgba( crop, ( W, H ) )
        cells.append( ( name, ( x0 / SIZE, 1 - y1 / SIZE, ( x0 + W ) / SIZE, 1 - ( y1 - H ) / SIZE ), W / H, crown ) )
    rgba[..., :3] = bleed( rgba[..., :3], rgba[..., 3] > 0.02 )
    return rgba, tuple( cells )


def tinted( rgb, gain, dust ):
    grey = ( rgb @ np.array( ( 0.3, 0.59, 0.11 ) ) )[..., None] * np.array( ( 1.04, 1.0, 0.88 ) )
    return np.clip( ( rgb * ( 1 - dust ) + grey * dust ) * np.array( gain ), 0.0, 1.0 )


def write_materials( root ):
    """ The atlas's tints as colour PNGs, its alpha, and a vmat per tint (complex.shader, alpha tested), under root /
    RESOURCE. """
    out = Path( root ) / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    rgba, _ = packed()

    def save( path, array, mode ):
        image = Image.fromarray( np.clip( np.rint( array * 255 ), 0, 255 ).astype( np.uint8 ), mode )
        temp = path.with_name( f"{path.name}.writing.png" )
        image.save( temp, optimize=True )
        if path.exists() and path.read_bytes() == temp.read_bytes():
            temp.unlink()
        else:
            temp.replace( path )

    save( out / f"{TRANS}.png", rgba[..., 3], "L" )
    for paint, ( gain, dust ) in TINTS.items():
        save( out / f"{paint}_color.png", tinted( rgba[..., :3], gain, dust ), "RGB" )
        text = "\n".join( [
            "// Tools/cerroblanco_trees.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"',
            '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{RESOURCE}/{TRANS}.png"', '    g_flAlphaTestReference "0.40"',
            '    g_flAntiAliasedEdgeStrength "1"', '    g_flRoughnessScaleFactor "1"', '    g_flMetalness "0.00"',
            f'    TextureColor "{RESOURCE}/{paint}_color.png"', '    TextureNormal "materials/default/default_normal.tga"',
            '    TextureRoughness "[0.900000 0.900000 0.900000 0.000000]"',
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"', '    g_vColorTint "[1.000000 1.000000 1.000000 1.000000]"',
            '    g_flModelTintAmount "1.0"', "}" ] ) + "\n"
        K.write_text( out / f"{paint}.vmat", text )


# ---------------------------------------------------------------------------------------------------------------------
# The woods

def places( C, height, rng, count, reach, weight ):
    """ Points the woods grow on, by cerroblanco_landscape's rules: 700 or more from the play's edge, where the woodland
    noise is high enough, the slope under 0.75 and the ground under 3200. Spread evenly over the land out to reach,
    each kept by weight( d ) (at most 1) of its distance from the play's edge. ( e, n, z, d, woodland noise, slope ). """
    rect = ( C.PLAY[0], C.PLAY[1], C.PLAY[2], C.PLAY[3] )
    found = []
    total = 0
    while total < count:
        k = 60000
        e = rng.uniform( C.PLAY[0] - reach, C.PLAY[1] + reach, k )
        n = rng.uniform( C.PLAY[2] - reach, C.PLAY[3] + reach, k )
        d = VB.rect_distance( e, n, rect )
        keep = ( d >= 700 ) & ( d <= reach ) & ( rng.random( k ) < weight( d ) )
        e, n, d = e[keep], n[keep], d[keep]
        w = VB.vfbm( e, n, 2200.0, 3, 1301 )
        ok = w >= -0.1 + 0.2 * rng.random( len( e ) )
        e, n, d, w = e[ok], n[ok], d[ok], w[ok]
        z = height( e, n, C )
        slope = np.hypot( height( e + 80, n, C ) - height( e - 80, n, C ), height( e, n + 80, C ) - height( e, n - 80, C ) ) / 160.0
        ok = ( slope <= 0.75 ) & ( z <= 3200 )
        found.append( np.stack( [ e[ok], n[ok], z[ok], d[ok], w[ok], slope[ok] ], -1 ) )
        total += int( ok.sum() )
    return np.concatenate( found )[:count]


def card( m, paint, bottom, top, uv, face, f, centre, half, tall, sides=( 1, -1 ) ):
    """ One upright card, both faces: bottom ( left, right ) and top ( left, right ) corners as seen from in front (face
    towards the viewer), uv ( u_left, v_bottom, u_right, v_top ). Its normals bow out from the crown's middle, mostly
    up, leaning a little towards the play (f) on the front and away from it on the back (sides). centre, half and tall
    are the tree's (its first card's), so every layer of a tree is lit alike. """
    ( bl, br ), ( tl, tr ) = bottom, top
    u0, v0, u1, v1 = uv
    pts = [ bl, br, tr, tl ]
    uvs = [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]
    side_axis = np.cross( -f, UP )

    def normals( side ):
        out = []
        for p in pts:
            off = p - centre
            across = side_axis * float( np.dot( off, side_axis ) ) / half * 0.45
            rise = UP * ( 1.0 + float( np.clip( off[2] / ( tall / 2 ), -1.0, 1.0 ) ) * 0.35 )
            out.append( unit( rise + across + f * 0.3 * side ) )
        return out

    m.polygon( paint, pts, normal=face, uv=uvs, normals=normals( sides[0] ) )
    # The back a quarter-inch behind the front, not on it: coincident faces fight where both are drawn, and a ray
    # tracer stepping through the culled one skips the other.
    back = [ p - face * 0.25 for p in ( pts[0], pts[3], pts[2], pts[1] ) ]
    ns = normals( sides[1] )
    m.polygon( paint, back, normal=-face, uv=[ uvs[0], uvs[3], uvs[2], uvs[1] ], normals=[ ns[0], ns[3], ns[2], ns[1] ] )


def build( C, height, seed=27, avoid=() ):
    """ The woods as cards (see the module's docstring). height: cerroblanco_landscape.height. avoid: plan ( e, n )
    points (the cloud oaks) that trees keep 200 off (about a crown) and scrub 100. """
    _, cells = packed()
    by_name = { c[0]: c for c in cells }
    rng = np.random.default_rng( seed + 7000 )
    # Trees all the way out, a little thicker near the play; where the woodland is thin, on the steep ground and up
    # high, most of them are scrub instead. The scrub's own, thickest near the play, where it's seen (a bush past
    # SCRUB_REACH is a few pixels), and thinner under the trees.
    tree_pts = places( C, height, rng, int( TREES * 2.5 ), REACH, lambda d: ( 1 + 0.8 * np.exp( -d / 5000.0 ) ) / 1.8 )
    scrub_pts = places( C, height, rng, SCRUB * 2, SCRUB_REACH, lambda d: np.exp( -( d - 700 ) / 3500.0 ) )

    def treeland( q ):
        w, slope, z = q[:, 4], q[:, 5], q[:, 2]
        return np.clip( 0.35 + 1.6 * w, 0.15, 1.0 ) * np.where( slope > 0.45, 0.45, 1.0 ) * np.where( z > 2400, 0.5, 1.0 )

    t = tree_pts[rng.random( len( tree_pts ) ) < treeland( tree_pts )][:TREES]
    sc = scrub_pts[rng.random( len( scrub_pts ) ) < 1.0 - 0.6 * treeland( scrub_pts )][:SCRUB]
    pts = np.concatenate( [ t, sc ] )
    trees, scrub = list( range( len( t ) ) ), list( range( len( t ), len( pts ) ) )
    cx, cy = ( C.PLAY[0] + C.PLAY[1] ) / 2, ( C.PLAY[2] + C.PLAY[3] ) / 2
    green = VB.vfbm( pts[:, 0], pts[:, 1], 2400.0, 3, 1201 ) + \
        0.3 * np.clip( -VB.vfbm( pts[:, 0], pts[:, 1], 1100.0, 3, 1103 ), 0, 1 )
    if len( avoid ):
        near = cKDTree( np.asarray( avoid, float )[:, :2] )
        clear = lambda i, r: not near.query_ball_point( pts[i, :2], r )
        trees = [ i for i in trees if clear( i, 200.0 ) ]
        scrub = [ i for i in scrub if clear( i, 100.0 ) ]
    pending = []
    for kind, chosen in ( ( "tree", trees ), ( "scrub", scrub ) ):
        shares = TREE_SHARE if kind == "tree" else SCRUB_SHARE
        names = list( shares )
        for i in chosen:
            e, n, zb, d, _, _ = pts[i]
            g = green[i]
            name = names[int( rng.choice( len( names ), p=[ shares[x] for x in names ] ) )]
            _, ( u0, v0, u1, v1 ), aspect, crown = by_name[name]
            if g > 0.15:
                tint_p = ( 0.35, 0.15, 0.5 )
            elif g < -0.1:
                tint_p = ( 0.3, 0.5, 0.2 )
            else:
                tint_p = ( 0.42, 0.3, 0.28 )
            if kind == "scrub":
                tint_p = ( tint_p[0] * 0.8, tint_p[1] * 1.4, tint_p[2] )
            tint_p = np.array( tint_p ) / sum( tint_p )
            paint = ( "cbf_tree_green", "cbf_tree_dry", "cbf_tree_dark" )[int( rng.choice( 3, p=tint_p ) )]
            far = 1.0 + 0.45 * min( 1.0, d / 15000.0 )
            # Facing the play's centre, a little off it, so neighbours aren't all one plane.
            heading = math.atan2( cy - n, cx - e ) + rng.normal( 0, math.radians( 9 ) )
            f = np.array( ( math.cos( heading ), math.sin( heading ), 0.0 ) )
            if kind == "tree":
                lo, hi = TREE_HEIGHT[name]
                tall = ( lo + ( hi - lo ) * rng.beta( 2.0, 2.4 ) ) * far
                sink = 4.0 + 0.02 * tall
                vb = v0
                follow = 0.35
            else:
                # The crown alone (from a little under its foot), sunk so it meets the ground as a bush.
                cut = max( 0.0, crown - 0.05 )
                vb = v0 + cut * ( v1 - v0 )
                aspect = aspect / ( 1 - cut )
                tall = rng.uniform( *SCRUB_HEIGHT ) * far / 0.82
                sink = 0.18 * tall
                follow = 1.0
            wide = tall * aspect * rng.uniform( 0.88, 1.12 )
            mirror = rng.random() < 0.5
            uv = ( u1, vb, u0, v1 ) if mirror else ( u0, vb, u1, v1 )
            lean = rng.normal( 0, 0.035 ) * tall
            tilt = rng.normal( 0, 0.03 ) * tall
            base = np.array( ( e, n, zb ) )
            centre = base + UP * ( tall * 0.5 - sink )
            shift = np.cross( -f, UP ) * lean + f * tilt
            lit = ( f, centre, wide / 2, tall )
            pending.append( ( paint, base, f, wide / 2, zb, follow, sink, tall, shift, uv, lit ) )
            if kind == "tree" and d < NEAR:
                # A second layer of crown a little behind the first, turned off it and mirrored, so the tree has some
                # depth seen from the side without a card ever going edge-on to the play (a card across the first
                # showed as a spike). Lit as the first is.
                cut = max( 0.0, crown - 0.05 )
                back_uv = ( uv[2], v0 + cut * ( v1 - v0 ), uv[0], v1 )
                turn = math.radians( rng.uniform( 18, 32 ) * rng.choice( ( -1, 1 ) ) )
                face = np.array( ( math.cos( heading + turn ), math.sin( heading + turn ), 0.0 ) )
                raise_ = tall * cut * 0.85
                layer = tall * ( 1 - cut ) * 0.92
                pending.append( ( paint, base - f * wide * 0.2 + UP * raise_, face, wide * 0.4, zb + raise_, 0.0, sink,
                                  layer, shift * 0.92, back_uv, lit ) )
    # The ground under every card's two bottom corners, at once.
    ends = []
    for paint, base, face, half, *_ in pending:
        right = np.cross( -face, UP )
        ends += [ base - right * half, base + right * half ]
    ends = np.array( ends )
    ground = height( ends[:, 0], ends[:, 1], C ).reshape( -1, 2 )
    m = Model()
    for k, ( paint, base, face, half, zb, follow, sink, tall, shift, uv, lit ) in enumerate( pending ):
        pair = ends[2 * k:2 * k + 2]
        bottom = [ p * ( 1, 1, 0 ) + UP * ( zb + follow * ( g - zb ) - sink ) for p, g in zip( pair, ground[k] ) ]
        top = [ b + UP * tall + shift for b in bottom ]
        card( m, paint, bottom, top, uv, face, *lit )
    cards = len( pending )
    for paint in m.polygons:
        m.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
        m.tile_overrides[paint] = 64.0
    print( f"woods: {len( trees )} trees and {len( scrub )} scrub as {cards} cards, {m.triangle_count()} triangles" )
    return m


# ---------------------------------------------------------------------------------------------------------------------

def sheet( path ):
    """ The atlas's tints side by side over a mid grey, the cells' UV boxes drawn, to check the cut-outs. """
    rgba, cells = packed()
    small = 768
    tiles = []
    for paint, ( gain, dust ) in TINTS.items():
        rgb = tinted( rgba[..., :3], gain, dust )
        a = ( rgba[..., 3] > 0.4 )[..., None]
        tile = np.where( a, rgb, np.array( ( 0.55, 0.6, 0.66 ) ) )
        image = Image.fromarray( np.rint( tile * 255 ).astype( np.uint8 ) ).resize( ( small, small ), Image.LANCZOS )
        from PIL import ImageDraw
        draw = ImageDraw.Draw( image )
        for _, ( u0, v0, u1, v1 ), _, crown in cells:
            box = ( u0 * small, ( 1 - v1 ) * small, u1 * small, ( 1 - v0 ) * small )
            draw.rectangle( box, outline=( 255, 60, 60 ) )
            yc = ( 1 - ( v0 + crown * ( v1 - v0 ) ) ) * small
            draw.line( ( box[0], yc, box[2], yc ), fill=( 60, 160, 255 ) )
        tiles.append( np.asarray( image ) )
    Image.fromarray( np.concatenate( tiles, 1 ) ).save( path )


def main( argv=None ):
    import sys
    import cerroblanco_landscape as L
    ap = argparse.ArgumentParser( prog="cerroblanco_trees.py" )
    ap.add_argument( "--out", default=str( K.ROOT / "output/cerroblanco/trees-preview" ) )
    args = ap.parse_args( argv )
    out = Path( args.out ).resolve()
    assert K.ASSETS not in ( out, *out.parents ), "the preview doesn't go in Assets"
    sys.path.insert( 0, str( Path( __file__ ).parent ) )
    import cerroblanco_map as C
    model = build( C, L.height )
    folder = out / "models/maps/cerroblanco"
    K.write_model( folder, "models/maps/cerroblanco", "cerroblanco_backdrop_woods", model )
    write_materials( out )
    sheet( out / "atlas_sheet.png" )
    size = ( folder / "cerroblanco_backdrop_woods.obj" ).stat().st_size
    print( f"OBJ {size / 1e6:.1f} MB -> {folder}" )


if __name__ == "__main__":
    main()
