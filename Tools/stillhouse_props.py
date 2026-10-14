"""
Stillhouse's props (Tools/stillhouse_map.py): the Camas Roin distillery's casks and dunnage stows, its pot stills,
condensers, spirit safe, washbacks and mash tun, the pipework, the road tanker, the puffer at the pier, the creel boat
and the dinghy, and the yard's and the pier's clutter. Each is a function that draws into a map_kit.Model in plan
coordinates (inches; e east, n north, z up), with collision where it stops a player.

    python Tools/stillhouse_props.py --preview <dir> [view ...]     (renders a showcase of every prop; writes no assets)

Conventions (railhead_props.py's)
- ( e, n ) is a prop's footprint centre on the floor at z0 unless its docstring says otherwise. facing is the way its
  front looks: "+e", "-e", "+n" or "-n"; a boat faces its bow that way.
- Paints are the design doc's sh_* paints, building_textures' iron_black for cast iron, and railhead's rw_* ones only
  inside the railhead_props vehicles that aren't repainted. Atlas faces get explicit UVs from
  stillhouse_materials.rect_uv() (the whole texture until that exists).
- Collision: whatever a player could stand behind gets collision with its surface: "wood" casks, washbacks, pallets,
  the bench and the wooden boats; "metal" the stills, condenser, safe, mash tun, vehicles, puffer, crane, bollards,
  drums, lamp posts, barrow and the boat trailer; "dirt" peat; "fabric" sacks; "plastic" fish boxes, creels and
  buoys; "default" (stone) the trough. Small things get one small box (a buoy, a drum) or none (rope coils, wall
  lanterns, ladders, pipes).
- Sizes are real ones: Scotch whisky casks (the American standard barrel, the hogshead and the butt), a mid-sized
  island distillery's stills, washbacks and mash tun, a 66 ft Clyde puffer, a 7 m creel boat, a 4 m clinker dinghy, the
  EPAL pallet, 25 kg malt sacks, a 200 l drum and an 8x4 road tanker.
- Deterministic: every random choice is a crc32 of the prop's own arguments (never Python's hash()).
"""
import argparse
import math
import zlib
from pathlib import Path

import numpy as np

import map_kit as K
import railhead_props as RP
from railhead_props import _ring_axes, _unit, disc, frame_for, outward, quad, rod

M = 39.37                       # inches in a metre
GRAIN = ( "sh_cask_oak", "sh_cask_dark", "sh_pine", "sh_timber_tar", "sh_planks_grey", "sh_deck", "sh_rope",
          "sh_floorboards" )
# the design doc's tile sizes for the grain paints given their own UVs here (staves that run along a curved surface)
TILES = { "sh_cask_oak": 64.0, "sh_cask_dark": 64.0, "sh_pine": 128.0, "sh_timber_tar": 128.0, "sh_planks_grey": 128.0,
          "sh_deck": 128.0, "sh_rope": 16.0, "sh_floorboards": 128.0 }
WOOD, METAL = "wood", "metal"
IRON = "iron_black"             # building_textures' painted cast iron

# ( length, bilge diameter, head diameter ): ASB barrel 200 l, hogshead 250 l, butt 500 l
CASKS = { "barrel": ( 34.6, 25.6, 21.6 ), "hogshead": ( 32.3, 28.7, 25.2 ), "butt": ( 50.0, 34.0, 28.3 ) }
STAVE_END = 1.1                 # the staves' thickness at the chime
HEAD_SET = 0.9                  # the head sits this far in from the stave ends (in the croze)
HEADS = tuple( f"head_{k}" for k in range( 8 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Dice: the same arguments always give the same prop

def _key( k ):
    return f"{k:.3f}" if isinstance( k, float ) else str( k )


def unit( *key ):
    """ A number in [0, 1) from the key. """
    return zlib.crc32( "/".join( _key( k ) for k in key ).encode() ) / 2 ** 32


def between( lo, hi, *key ):
    return lo + ( hi - lo ) * unit( *key )


def pick( seq, *key ):
    return seq[min( int( unit( *key ) * len( seq ) ), len( seq ) - 1 )]


def chance( p, *key ):
    return unit( *key ) < p


# ---------------------------------------------------------------------------------------------------------------------
# Atlases (stillhouse_materials, once it exists)

ASPECTS = { "boat_mairi_ros": 6.0, "boat_cr47": 3.5, "boat_cr112": 4.2, "flammable": 1.0 }


def _rect( atlas, name ):
    """ An atlas entry's ( u0, v0, u1, v1 ) from stillhouse_materials, or the whole texture while it isn't there. """
    try:
        import stillhouse_materials as SM
        return tuple( float( x ) for x in SM.rect_uv( atlas, name ) )
    except Exception:
        return ( 0.0, 0.0, 1.0, 1.0 )


def aspect( atlas, name ):
    """ Width over height of an atlas entry: its rectangle's in stillhouse_materials, else the design doc's. """
    u0, v0, u1, v1 = _rect( atlas, name )
    if ( u0, v0, u1, v1 ) != ( 0.0, 0.0, 1.0, 1.0 ):
        try:
            import stillhouse_materials as SM
            W, H = SM.ATLASES[atlas][:2]
            return ( u1 - u0 ) * W / ( ( v1 - v0 ) * H )
        except Exception:
            pass
    if atlas == "sh_cask_head":
        return 1.0
    return ASPECTS.get( name, 4.0 if atlas == "sh_signs" else 5.0 )


def _quad_uv( rect ):
    u0, v0, u1, v1 = rect
    return [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]


def atlas_quad( model, atlas, name, centre, right, up, w, h ):
    """ An atlas entry on a w x h rectangle facing cross( right, up ), reading the right way round from in front. """
    quad( model, atlas, centre, right, up, w, h, uv=_quad_uv( _rect( atlas, name ) ) )


def _grain( model, *paints ):
    model.grain_paints.update( p for p in paints if p in GRAIN )


# ---------------------------------------------------------------------------------------------------------------------
# Round things

def revolve( model, base, axis, profile, paint, sides=16, turn=0.0, crease=40.0, uv=None ):
    """ A surface of revolution about the line through base along axis: profile [ ( r, t ) ], t along the axis, each
    band facing away from the axis on the profile's right-hand side (list it bottom to top for an outside). Shaded
    smooth around, and along it except where two bands meet at more than crease degrees. paint: one paint, or
    paint( k ) for the band from profile point k to k + 1 (None leaves it out). uv( k, i, t ), if given, is band k's
    texture coordinate at ring step i (0 to sides, unwrapped) and height t, or None to leave band k to map_kit. """
    base, ax = np.asarray( base, float ), _unit( axis )
    u, v = _ring_axes( ax )
    dirs = [ math.cos( turn + 2 * math.pi * i / sides ) * u + math.sin( turn + 2 * math.pi * i / sides ) * v
             for i in range( sides ) ]
    prof = [ ( float( r ), float( t ) ) for r, t in profile ]
    seg = []
    for ( r0, t0 ), ( r1, t1 ) in zip( prof, prof[1:] ):
        length = math.hypot( r1 - r0, t1 - t0 )
        seg.append( ( ( t1 - t0 ) / length, ( r0 - r1 ) / length ) if length > 1e-9 else None )
    limit = math.cos( math.radians( crease ) )

    def normal_at( k, j ):
        if prof[j][0] < 1e-6:                               # a pole: along the axis
            return ( 0.0, 1.0 if seg[k][1] > 0 else -1.0 )
        own = seg[k]
        other = k - 1 if j == k else k + 1
        if 0 <= other < len( seg ) and seg[other] is not None:
            o = seg[other]
            if own[0] * o[0] + own[1] * o[1] >= limit:
                s0, s1 = own[0] + o[0], own[1] + o[1]
                length = math.hypot( s0, s1 )
                return ( s0 / length, s1 / length )
        return own

    for k in range( len( prof ) - 1 ):
        if seg[k] is None:
            continue
        p = paint( k ) if callable( paint ) else paint
        if p is None:
            continue
        ( r0, t0 ), ( r1, t1 ) = prof[k], prof[k + 1]
        na, nb = normal_at( k, k ), normal_at( k, k + 1 )
        for i in range( sides ):
            d0, d1 = dirs[i], dirs[( i + 1 ) % sides]
            a0, a1 = base + ax * t0 + r0 * d0, base + ax * t0 + r0 * d1
            b0, b1 = base + ax * t1 + r1 * d0, base + ax * t1 + r1 * d1
            ma0, ma1 = na[0] * d0 + na[1] * ax, na[0] * d1 + na[1] * ax
            mb0, mb1 = nb[0] * d0 + nb[1] * ax, nb[0] * d1 + nb[1] * ax
            corners = None
            if uv is not None and uv( k, i, t0 ) is not None:
                corners = [ uv( k, i, t0 ), uv( k, i + 1, t0 ), uv( k, i + 1, t1 ), uv( k, i, t1 ) ]
            if r0 < 1e-6:
                pts, nrm, sel = [ a0, b0, b1 ], [ ma0, mb0, mb1 ], ( 0, 3, 2 )
            elif r1 < 1e-6:
                pts, nrm, sel = [ a0, a1, b0 ], [ ma0, ma1, mb0 ], ( 0, 1, 3 )
            else:
                pts, nrm, sel = [ a0, a1, b1, b0 ], [ ma0, ma1, mb1, mb0 ], ( 0, 1, 2, 3 )
            outward( model, p, pts, sum( nrm ), normals=nrm,
                     uv=None if corners is None else [ corners[s] for s in sel ] )


def ring_points( centre, axis, r, sides, turn=0.0 ):
    """ The points revolve() puts round a ring of radius r at centre. """
    c, ax = np.asarray( centre, float ), _unit( axis )
    u, v = _ring_axes( ax )
    return [ c + r * ( math.cos( turn + 2 * math.pi * i / sides ) * u + math.sin( turn + 2 * math.pi * i / sides ) * v )
             for i in range( sides ) ]


def sphere( model, centre, r, paint, sides=12, rings=6, axis=( 0.0, 0.0, 1.0 ) ):
    prof = [ ( r * math.sin( math.pi * j / rings ), -r * math.cos( math.pi * j / rings ) ) for j in range( rings + 1 ) ]
    prof[0], prof[-1] = ( 0.0, -r ), ( 0.0, r )
    revolve( model, centre, axis, prof, paint, sides )


def _dedupe( points, tol=1e-3 ):
    out = []
    for p in points:
        p = np.asarray( p, float )
        if not out or np.linalg.norm( p - out[-1] ) > tol:
            out.append( p )
    return out


def tube( model, points, r, paint, sides=8, caps=( False, False ), cap_paint=None ):
    """ A round tube swept along a polyline (r: one radius or one per point), its rings carried along without
    twisting, shaded smooth. Round its corners first (_bend_path) unless they're gentle. """
    pts = _dedupe( points )
    if len( pts ) < 2:
        return
    rs = [ float( x ) for x in r ] if isinstance( r, ( list, tuple ) ) else [ float( r ) ] * len( pts )
    if len( rs ) != len( pts ):
        rs = [ rs[0] ] * len( pts )
    n = len( pts )
    tans = []
    for i in range( n ):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = _unit( pts[i] - pts[i - 1] ) + _unit( pts[i + 1] - pts[i] )
        tans.append( _unit( t ) )
    u = _ring_axes( tans[0] )[0]
    rings, dirs = [], []
    for i in range( n ):
        u = u - tans[i] * np.dot( u, tans[i] )
        if np.linalg.norm( u ) < 1e-6:
            u = _ring_axes( tans[i] )[0]
        u = _unit( u )
        w = np.cross( tans[i], u )
        ds = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * w for k in range( sides ) ]
        dirs.append( ds )
        rings.append( [ pts[i] + rs[i] * d for d in ds ] )
    for i in range( n - 1 ):
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            nrm = [ dirs[i][k], dirs[i][k1], dirs[i + 1][k1], dirs[i + 1][k] ]
            outward( model, paint, [ rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k] ], sum( nrm ),
                     normals=nrm )
    if caps[0]:
        outward( model, cap_paint or paint, rings[0], -tans[0] )
    if caps[1]:
        outward( model, cap_paint or paint, rings[-1], tans[-1] )


def _bend_path( points, radius, steps=4 ):
    """ The polyline with each corner rounded into an arc of radius (less where the legs are short), and the points
    where each arc starts and ends with the way the pipe runs there ( point, direction ). """
    pts = _dedupe( points )
    out, joints = [ pts[0] ], []
    for i in range( 1, len( pts ) - 1 ):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = _unit( b - a ), _unit( c - b )
        angle = math.acos( float( np.clip( np.dot( d0, d1 ), -1.0, 1.0 ) ) )
        if angle < 1e-3:
            out.append( b )
            continue
        reach = min( radius * math.tan( angle / 2 ), 0.45 * np.linalg.norm( b - a ), 0.45 * np.linalg.norm( c - b ) )
        rr = reach / math.tan( angle / 2 )
        p0 = b - d0 * reach
        nvec = _unit( d1 - d0 * np.dot( d1, d0 ) )
        centre = p0 + nvec * rr
        for s in range( steps + 1 ):
            th = angle * s / steps
            out.append( centre - nvec * rr * math.cos( th ) + d0 * rr * math.sin( th ) )
        joints += [ ( p0, d0 ), ( b + d1 * reach, d1 ) ]
    out.append( pts[-1] )
    return _dedupe( out ), joints


def _hull2d( points ):
    """ The convex hull of 2D points, counter-clockwise. """
    pts = sorted( set( ( round( float( x ), 4 ), round( float( y ), 4 ) ) for x, y in points ) )
    if len( pts ) <= 2:
        return pts

    def cross( o, a, b ):
        return ( a[0] - o[0] ) * ( b[1] - o[1] ) - ( a[1] - o[1] ) * ( b[0] - o[0] )

    lower, upper = [], []
    for p in pts:
        while len( lower ) >= 2 and cross( lower[-2], lower[-1], p ) <= 0:
            lower.pop()
        lower.append( p )
    for p in reversed( pts ):
        while len( upper ) >= 2 and cross( upper[-2], upper[-1], p ) <= 0:
            upper.pop()
        upper.append( p )
    return lower[:-1] + upper[:-1]


def _round_hull( model, e, n, rings, surface, sides=12 ):
    """ Collision: the convex hull of horizontal rings ( r, z ) round ( e, n ). """
    model.hull( [ ( e + r * math.cos( 2 * math.pi * k / sides ), n + r * math.sin( 2 * math.pi * k / sides ), z )
                  for r, z in rings for k in range( sides ) ], surface )


def _horizontal( facing ):
    return { "+e": ( 1.0, 0.0 ), "-e": ( -1.0, 0.0 ), "+n": ( 0.0, 1.0 ), "-n": ( 0.0, -1.0 ) }[facing]


# ---------------------------------------------------------------------------------------------------------------------
# Casks

def _cask_dims( kind ):
    if kind not in CASKS:
        raise ValueError( f"unknown cask {kind!r}: one of {', '.join( CASKS )}" )
    L, B, H = CASKS[kind]
    return L, B / 2, H / 2, ( 1.75 if kind == "barrel" else 2.0 )


def _cask_radius( kind, t ):
    """ The staves' radius t along the cask: a parabolic bilge from head to head. """
    L, rb, rh, _ = _cask_dims( kind )
    s = 2 * t / L - 1
    return rh + ( rb - rh ) * ( 1 - s * s )


def _hoops( kind ):
    """ Where the hoops start along the cask: the chime hoop half an inch in, the quarter and bilge hoops. """
    L = CASKS[kind][0]
    return 0.55, 0.175 * L, 0.335 * L


def _cask_mid( kind ):
    """ The radius between the bilge hoops, where the cask is widest. """
    _, _, b = _hoops( kind )
    return _cask_radius( kind, b + _cask_dims( kind )[3] )


def _cask_profile( kind, ends=( True, True ), strip=False, hoops=6 ):
    """ The cask's outline ( r, t ) from end to end and each band's part ("stave", "hoop" or "chime": the bevel into a
    head); strip leaves the staves' ends showing past the chime hoops. An end that's False stays open (hidden). The
    band between the bilge hoops is straight at the hoops' inner edge, where the bung stave is.
    hoops 4 is a cask deep in a stow, seen only round the heads facing an aisle: the chime and quarter hoops at each of
    those, no bilge hoops, one straight band across the middle, and a hidden end's half one plain band from the
    middle. """
    L, rb, rh, w = _cask_dims( kind )
    c, q, b = _hoops( kind )
    if not strip:
        c = 0.0
    mid = _cask_mid( kind )
    lead = [ 0.0, c ] if strip else [ 0.0 ]
    lead_parts = [ "stave" ] if strip else []
    if hoops == 6:
        half = lead + [ c + w, q, q + w, b, b + w ]
        parts_half = lead_parts + [ "hoop", "stave", "hoop", "stave", "hoop" ]
        ts = half + [ L - t for t in reversed( half ) ]
        parts = parts_half + [ "stave" ] + list( reversed( parts_half ) )
    else:
        half = lead + [ c + w, q, q + w ]
        parts_half = lead_parts + [ "hoop", "stave", "hoop" ]
        ts0, parts0 = ( half, parts_half ) if ends[0] else ( [ 0.0 ], [] )
        ts1 = [ L - t for t in reversed( half ) ] if ends[1] else [ L ]
        parts1 = list( reversed( parts_half ) ) if ends[1] else []
        middle = [ L / 2 ] if ends[0] != ends[1] else []    # one end shown: the bilge's swell from it
        ts = ts0 + middle + ts1
        parts = parts0 + [ "stave" ] * ( len( middle ) + 1 ) + parts1
    pts = [ ( min( _cask_radius( kind, t ), mid ), t ) for t in ts ]
    if ends[0]:
        pts, parts = [ ( rh - STAVE_END, HEAD_SET ) ] + pts, [ "chime" ] + parts
    if ends[1]:
        pts, parts = pts + [ ( rh - STAVE_END, L - HEAD_SET ) ], parts + [ "chime" ]
    return pts, parts


def _cask( model, centre, axis, kind, staves="sh_cask_oak", heads=( "oak", "oak" ), sides=16, bung=True, strip=False,
           up=( 0.0, 0.0, 1.0 ), bung_dir=None, hoops=6 ):
    """ One cask about its middle, its axis along axis (a plan vector): heads[0] at the end towards -axis, heads[1]
    towards +axis, each None (left open: hidden against another cask), "oak" (a plain head in the staves' wood) or an
    sh_cask_head entry, its picture upright along up. The bung, on a facet's middle, faces bung_dir (default up). The
    staves' grain runs along the cask. No collision. """
    L, rb, rh, w = _cask_dims( kind )
    c, ax = np.asarray( centre, float ), _unit( axis )
    base = c - ax * L / 2
    pts, parts = _cask_profile( kind, ( heads[0] is not None, heads[1] is not None ), strip, hoops )
    bdir = np.asarray( bung_dir if bung_dir is not None else up, float )
    bdir = _unit( bdir - ax * np.dot( bdir, ax ) )
    u, v = _ring_axes( ax )
    turn = math.atan2( np.dot( bdir, v ), np.dot( bdir, u ) ) - math.pi / sides
    paints = { "stave": staves, "chime": staves, "hoop": "sh_hoop" }
    tile = TILES[staves]
    width = 2 * math.pi * _cask_mid( kind ) / sides / tile

    def stave_uv( k, i, t ):
        return None if parts[k] == "hoop" else ( i * width, t / tile )

    revolve( model, base, ax, pts, lambda k: paints[parts[k]], sides, turn, crease=35.0, uv=stave_uv )
    rad = rh - STAVE_END
    for end, spec in enumerate( heads ):
        if spec is None:
            continue
        hc = base + ax * ( HEAD_SET if end == 0 else L - HEAD_SET )
        normal = -ax if end == 0 else ax
        ring = ring_points( hc, ax, rad, sides, turn )
        if spec == "oak":
            outward( model, staves, ring, normal )
            continue
        upv = np.asarray( up, float ) - normal * np.dot( up, normal )
        upv = _unit( upv ) if np.linalg.norm( upv ) > 1e-6 else v
        right = np.cross( upv, normal )
        u0, v0, u1, v1 = _rect( "sh_cask_head", spec )
        uv = [ ( u0 + ( u1 - u0 ) * ( 0.5 + 0.5 * np.dot( p - hc, right ) / rad ),
                 v0 + ( v1 - v0 ) * ( 0.5 + 0.5 * np.dot( p - hc, upv ) / rad ) ) for p in ring ]
        outward( model, "sh_cask_head", ring, normal, uv=uv )
    if bung:
        p0 = c + bdir * ( _cask_mid( kind ) * math.cos( math.pi / sides ) - 0.3 )
        rod( model, p0, p0 + bdir * 0.85, 1.05, "sh_pine", 6, caps=( False, True ) )


def _head_spec( *key ):
    """ A head facing an aisle: stencilled with a cask number and fill (head_0..7) more often than not. """
    return pick( HEADS, "which", *key ) if chance( 0.6, "stencil", *key ) else "head_plain"


def cask( model, e, n, z0, axis="n", kind="hogshead", head=None, dark=False, standing=False ):
    """ A cask lying on the floor at z0 with its axis along axis ("e" or "n"), bung up, or stood on end: 16 sides,
    six hoops, a recessed head at each end. head: 0..7 stencils the +axis head (the top one standing), "plain" gives it
    the atlas's plain head, None leaves both heads plain oak. Collision: one box, "wood". Returns its top z. """
    L, rb, rh, w = _cask_dims( kind )
    staves = "sh_cask_dark" if dark else "sh_cask_oak"
    _grain( model, staves, "sh_pine" )
    sides = 16
    spec = None if head is None else ( "head_plain" if head == "plain" else HEADS[int( head ) % 8] )
    rm = _cask_mid( kind )
    if standing:
        turn = pick( ( ( 1, 0, 0 ), ( 0, 1, 0 ), ( -1, 0, 0 ), ( 0, -1, 0 ) ), "up", e, n, z0 )
        _cask( model, ( e, n, z0 + L / 2 ), ( 0, 0, 1 ), kind, staves, ( None, spec or "oak" ), sides, up=turn,
               bung_dir=( turn[1], -turn[0], 0 ) )
        model.collision_box( ( e - rm, n - rm, z0 ), ( e + rm, n + rm, z0 + L ), WOOD )
        return z0 + L
    ax = ( 0.0, 1.0, 0.0 ) if axis == "n" else ( 1.0, 0.0, 0.0 )
    z_axis = z0 + rm * math.cos( math.pi / sides )
    _cask( model, ( e, n, z_axis ), ax, kind, staves, ( "head_plain" if spec else "oak", spec or "oak" ), sides )
    half = np.array( ( rm, L / 2, 0 ) if axis == "n" else ( L / 2, rm, 0 ) )
    model.collision_box( ( e - half[0], n - half[1], z0 ), ( e + half[0], n + half[1], z_axis + rm ), WOOD )
    return z_axis + rm


def cask_stow( model, e0, e1, n, z0, tiers=3, depth=1, kind="hogshead", seed=0, gaps=0.05 ):
    """ A dunnage stow: casks lying side by side along e from e0 to e1 with their axes along n, depth casks end to end
    centred on n, tiers high. Each tier lies on two 4 x 4 runners per cask under its quarters, laid along e on the tier
    below (the bottom tier's on the floor). A few casks are missing (gaps of them) or darker refills; the heads facing
    the aisles are stencilled or plain, the hidden ones left out. Casks in the open (the top tier, the rows' ends, beside
    a gap) have 12 sides and six hoops; the rest, seen only round their heads, 10 sides and hoops only near the heads
    that show. Collision: one box, "wood". Returns the stow's top z. """
    L, rb, rh, w = _cask_dims( kind )
    e0, e1 = min( e0, e1 ), max( e0, e1 )
    rm = _cask_mid( kind )
    pitch, end_gap, runner = 2 * rm + 1.0, 3.0, 4.0
    count = max( 1, int( ( e1 - e0 - 2 * rm ) // pitch ) + 1 )
    first = ( e0 + e1 ) / 2 - ( count - 1 ) * pitch / 2
    rows = [ n + ( k - ( depth - 1 ) / 2 ) * ( L + end_gap ) for k in range( depth ) ]
    t_q = 0.27 * L
    r_q = _cask_radius( kind, L / 2 - t_q )
    lo_e, hi_e = first - rm - 3.0, first + ( count - 1 ) * pitch + rm + 3.0
    _grain( model, "sh_cask_oak", "sh_cask_dark", "sh_pine" )
    present = { ( t, k, i ): not chance( gaps, "gap", seed, kind, t, k, i )
                for t in range( tiers ) for k in range( depth ) for i in range( count ) }
    z_run, top = z0, z0
    apothem = math.cos( math.pi / 12 )
    for tier in range( tiers ):
        for row_n in rows:
            for s in ( -1, 1 ):
                model.box( ( lo_e, row_n + s * t_q - 2, z_run ), ( hi_e, row_n + s * t_q + 2, z_run + runner ),
                           { "default": "sh_cask_dark", "-z": None } )
        z_axis = z_run + runner + r_q * apothem
        for k, row_n in enumerate( rows ):
            for i in range( count ):
                if not present[( tier, k, i )]:
                    continue
                # in the open: the top tier, the row's ends, beside a gap
                outer = tier == tiers - 1 or i in ( 0, count - 1 ) or not all(
                    present.get( ( tier + dt, k, i + di ), False ) for dt, di in ( ( 0, -1 ), ( 0, 1 ), ( 1, 0 ) ) )
                key = ( seed, kind, tier, k, i )
                show = ( k == 0 or not present[( tier, k - 1, i )], k == depth - 1 or not present[( tier, k + 1, i )] )
                heads = tuple( _head_spec( "end", s, *key ) if shown else None for s, shown in enumerate( show ) )
                staves = "sh_cask_dark" if chance( 0.15, "dark", *key ) else "sh_cask_oak"
                _cask( model, ( first + i * pitch, row_n, z_axis ), ( 0, 1, 0 ), kind, staves, heads,
                       12 if outer else 10, bung=tier == tiers - 1, hoops=6 if outer else 4 )
        top = z_axis + rm
        z_run = z_axis + r_q * apothem
    model.collision_box( ( lo_e, rows[0] - L / 2, z0 ), ( hi_e, rows[-1] + L / 2, top ), WOOD )
    return top


def _wedge( model, foot, out, along, length=7.0, width=3.5, height=4.0, paint="sh_cask_dark" ):
    """ A chock on the floor: its thin edge at foot, rising away along out to height, width along along. """
    f, o, a = np.asarray( foot, float ), _unit( out ), _unit( along ) * width / 2
    z = np.array( ( 0.0, 0.0, height ) )
    p = [ f - a, f + a, f + o * length - a, f + o * length + a ]
    q = [ p[2] + z, p[3] + z ]
    outward( model, paint, [ p[0], p[1], q[1], q[0] ], -o + _unit( z ) )        # the slope, under the cask
    outward( model, paint, [ p[2], p[3], q[1], q[0] ], o )                      # the back
    outward( model, paint, [ p[0], p[2], q[0] ], -a )
    outward( model, paint, [ p[1], p[3], q[1] ], a )


def cask_pyramid( model, e, n, z0, axis="n", base=3, kind="hogshead", seed=0 ):
    """ Casks lying in a pyramid in the yard, base wide (3-2-1), axes along axis, each row in the hollows of the one
    below, the bottom row's outer casks chocked with oak wedges. Collision: a hull, "wood". Returns its top z. """
    L, rb, rh, w = _cask_dims( kind )
    sides, rm = 12, _cask_mid( kind )
    apothem = rm * math.cos( math.pi / sides )
    pitch = 2 * rm + 1.0
    dz = math.sqrt( max( ( 2 * rm ) ** 2 - ( pitch / 2 ) ** 2, 0.0 ) )
    ax = np.array( ( 0.0, 1.0, 0.0 ) if axis == "n" else ( 1.0, 0.0, 0.0 ) )
    across = np.array( ( 1.0, 0.0, 0.0 ) if axis == "n" else ( 0.0, 1.0, 0.0 ) )
    c0 = np.array( ( e, n, z0 ), float )
    _grain( model, "sh_cask_oak", "sh_cask_dark", "sh_pine" )
    section = []
    for j in range( base ):
        for i in range( base - j ):
            x, z = ( i - ( base - j - 1 ) / 2 ) * pitch, apothem + j * dz
            key = ( seed, kind, e, n, j, i )
            heads = tuple( _head_spec( "end", s, *key ) for s in range( 2 ) )
            staves = "sh_cask_dark" if chance( 0.2, "dark", *key ) else "sh_cask_oak"
            _cask( model, c0 + across * x + ( 0, 0, z ), ax, kind, staves, heads, sides )
            section += [ ( x + rm * math.cos( 2 * math.pi * k / 8 ), z + rm * math.sin( 2 * math.pi * k / 8 ) )
                         for k in range( 8 ) ]
    for side in ( -1, 1 ):
        x_out = side * ( base - 1 ) / 2 * pitch
        for s in ( -1, 1 ):
            _wedge( model, c0 + across * ( x_out + side * 4.0 ) + ax * s * 0.25 * L, across * side, ax )
    section += [ ( -( base - 1 ) / 2 * pitch - rm, 0.0 ), ( ( base - 1 ) / 2 * pitch + rm, 0.0 ) ]
    hull = _hull2d( section )
    model.hull( [ c0 + across * x + ax * s * L / 2 + ( 0, 0, max( z, 0.0 ) ) for x, z in hull for s in ( -1, 1 ) ],
                WOOD )
    return z0 + apothem + ( base - 1 ) * dz + rm


def cask_rank( model, e0, e1, n, z0, kind="hogshead", seed=0 ):
    """ A line of casks stood on end along e from e0 to e1 at n, their stencils turned every way. Collision: one box,
    "wood". Returns its top z. """
    L, rb, rh, w = _cask_dims( kind )
    e0, e1 = min( e0, e1 ), max( e0, e1 )
    rm = _cask_mid( kind )
    pitch = 2 * rm + 2.0
    count = max( 1, int( ( e1 - e0 - 2 * rm ) // pitch ) + 1 )
    first = ( e0 + e1 ) / 2 - ( count - 1 ) * pitch / 2
    _grain( model, "sh_cask_oak", "sh_cask_dark", "sh_pine" )
    for i in range( count ):
        key = ( seed, kind, e0, n, i )
        a = between( 0.0, 2 * math.pi, "turn", *key )
        up = ( math.cos( a ), math.sin( a ), 0.0 )
        staves = "sh_cask_dark" if chance( 0.15, "dark", *key ) else "sh_cask_oak"
        _cask( model, ( first + i * pitch, n, z0 + L / 2 ), ( 0, 0, 1 ), kind, staves, ( None, _head_spec( *key ) ), 12,
               up=up, bung_dir=( -up[1], up[0], 0.0 ) )
    model.collision_box( ( first - rm, n - rm, z0 ), ( first + ( count - 1 ) * pitch + rm, n + rm, z0 + L ), WOOD )
    return z0 + L


# ---------------------------------------------------------------------------------------------------------------------
# Pipework

def _flange( model, centre, axis, r, paint, sides=12, thick=1.2, reach=None ):
    """ A flange ring round a pipe of radius r, centred on centre, thick along axis, out to reach (1.5 r + 0.6). """
    ax = _unit( axis )
    R = reach if reach is not None else 1.5 * r + 0.6
    revolve( model, np.asarray( centre, float ) - ax * thick / 2, ax,
             [ ( r, 0.0 ), ( R, 0.0 ), ( R, thick ), ( r, thick ) ], paint, sides, crease=30.0 )


def _band( model, centre, axis, r, height, paint, sides=16, proud=0.6 ):
    """ A band proud of a round surface of radius r (a hoop, a clamp, a stiffening ring), height along axis. """
    _flange( model, centre, axis, r, paint, sides, height, r + proud )


def _pipe_sides( r ):
    return 8 if r <= 3.5 else ( 12 if r <= 8.0 else 16 )


def _loop( model, centre, a, b, ra, rb, rod_r, paint, steps=12, sides=5 ):
    """ A closed ring of rod (radius rod_r) round centre in the plane of a and b, an ellipse ra x rb. """
    c = np.asarray( centre, float )
    pts = [ c + a * ra * math.cos( 2 * math.pi * k / steps ) + b * rb * math.sin( 2 * math.pi * k / steps )
            for k in range( steps + 1 ) ]
    tube( model, pts, rod_r, paint, sides )


def pipe( model, points, r=3, paint="sh_steel_green", flanges=True ):
    """ A pipe of radius r through points (plan ( e, n, z ), at least two), each corner bent round a long-radius elbow
    (2.5 r), with flanges at its ends and at both ends of every elbow when flanges is set. No collision. """
    pts = _dedupe( points )
    if len( pts ) < 2:
        return
    path, joints = _bend_path( pts, 2.5 * r )
    sides = _pipe_sides( r )
    tube( model, path, r, paint, sides )
    if not flanges:
        return
    thick = max( 0.8, 0.3 * r )
    for c, d, s in ( ( pts[0], _unit( pts[1] - pts[0] ), 1 ), ( pts[-1], _unit( pts[-1] - pts[-2] ), -1 ) ):
        _flange( model, c + d * s * thick / 2, d, r, paint, sides, thick )
    for c, d in joints:
        _flange( model, c, d, r, paint, sides, thick )


def _valve( model, at, along, r, paint="sh_steel", wheel="sh_paint_red", up=( 0.0, 0.0, 1.0 ) ):
    """ A gate valve on a pipe of radius r running along along through at: its body, the bonnet standing up from it
    and the red handwheel on top. """
    at, d, upv = np.asarray( at, float ), _unit( along ), _unit( up )
    rod( model, at - d * ( 1.6 * r + 1 ), at + d * ( 1.6 * r + 1 ), 1.45 * r, paint, _pipe_sides( r ),
         caps=( True, True ) )
    top = at + upv * ( 3.2 * r + 4 )
    rod( model, at, top, 0.45 * r + 0.4, paint, 6, caps=( False, True ) )
    wr = 1.6 * r + 1.5
    a = _ring_axes( upv )[0]
    b = np.cross( upv, a )
    _loop( model, top, a, b, wr, wr, 0.5, wheel, steps=10, sides=4 )
    for s in ( a, b ):
        rod( model, top - s * wr, top + s * wr, 0.35, wheel, 4 )


# ---------------------------------------------------------------------------------------------------------------------
# The stills

# ( r, z over the floor ) up the middle of each: the pot (dull copper under its knuckle), then the neck. A mid-sized
# island distillery's wash still holds ~12,000 l in an onion pot 3.6 m across; its spirit still ~8,000 l, with a boil
# ball under its neck to send more reflux back.
WASH_POT = [ ( 0.0, 20.0 ), ( 26.0, 21.6 ), ( 44.0, 25.0 ), ( 57.0, 30.5 ), ( 65.5, 38.0 ), ( 69.5, 48.0 ),
             ( 70.6, 60.0 ), ( 69.6, 72.0 ), ( 66.5, 83.0 ), ( 61.0, 93.0 ), ( 53.0, 101.5 ), ( 44.0, 108.5 ),
             ( 35.0, 114.0 ), ( 27.5, 118.5 ), ( 22.0, 122.5 ), ( 20.5, 126.0 ) ]
WASH_NECK = [ ( 20.5, 126.0 ), ( 19.0, 138.0 ), ( 17.0, 152.0 ), ( 15.0, 168.0 ), ( 13.0, 186.0 ), ( 11.3, 206.0 ),
              ( 10.0, 226.0 ), ( 9.0, 244.0 ), ( 8.3, 258.0 ) ]
SPIRIT_POT = [ ( 0.0, 20.0 ), ( 22.0, 21.4 ), ( 37.0, 24.5 ), ( 48.0, 29.5 ), ( 55.0, 36.5 ), ( 58.2, 45.0 ),
               ( 58.6, 55.0 ), ( 57.0, 65.0 ), ( 53.0, 74.5 ), ( 46.5, 82.5 ), ( 38.5, 88.5 ), ( 30.5, 93.0 ),
               ( 24.5, 96.5 ), ( 21.0, 100.0 ),
               # the boil ball
               ( 24.5, 103.0 ), ( 29.0, 108.0 ), ( 31.8, 114.5 ), ( 32.5, 121.5 ), ( 31.4, 128.5 ), ( 28.0, 134.5 ),
               ( 23.0, 139.0 ), ( 18.5, 142.5 ), ( 16.5, 145.0 ) ]
SPIRIT_NECK = [ ( 16.5, 145.0 ), ( 15.0, 156.0 ), ( 13.2, 170.0 ), ( 11.6, 186.0 ), ( 10.2, 202.0 ), ( 9.0, 216.0 ),
                ( 8.2, 226.0 ) ]
# profile, neck, the lyne arm's bend (its centre line's corner), the pot's sides, the manway's and the charge
# inlet's heights on the shoulder
STILLS = { "wash": ( WASH_POT, WASH_NECK, 270.0, 32, 96.0, 110.0 ),
           "spirit": ( SPIRIT_POT, SPIRIT_NECK, 236.0, 28, 79.0, 89.0 ) }
LYNE_FALL = math.tan( math.radians( 8.0 ) )
LYNE_R = 7.0


def _profile_at( prof, z ):
    """ A profile's radius at height z, and its outward normal there as ( radial, up ). """
    for ( r0, z0 ), ( r1, z1 ) in zip( prof, prof[1:] ):
        if z0 <= z <= z1 and z1 > z0:
            f, length = ( z - z0 ) / ( z1 - z0 ), math.hypot( r1 - r0, z1 - z0 )
            return r0 + f * ( r1 - r0 ), ( ( z1 - z0 ) / length, ( r0 - r1 ) / length )
    return prof[-1][0], ( 1.0, 0.0 )


def _bottom_z( prof, r ):
    """ The height of a pot's bottom at radius r (its profile rising outwards from the middle). """
    for ( r0, z0 ), ( r1, z1 ) in zip( prof, prof[1:] ):
        if r0 <= r <= r1 and r1 > r0:
            return z0 + ( r - r0 ) / ( r1 - r0 ) * ( z1 - z0 )
    return prof[0][1]


def _manway( model, centre, normal, ra=8.5, rb=10.5 ):
    """ A still's brass manway door on its shoulder: the oval door in its frame, swing bolts round it, the hinge and
    a T handle. """
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    a = _unit( np.cross( up, normal ) )
    b = np.cross( normal, a )
    c = np.asarray( centre, float )
    door = [ c + normal * 0.9 + a * ra * math.cos( 2 * math.pi * k / 14 ) + b * rb * math.sin( 2 * math.pi * k / 14 )
             for k in range( 14 ) ]
    outward( model, "sh_brass", door, normal )
    _loop( model, c + normal * 0.5, a, b, ra + 0.9, rb + 0.9, 0.9, "sh_brass", 14, 5 )
    for k in range( 6 ):
        t = 2 * math.pi * ( k + 0.5 ) / 6
        p = c + a * ( ra + 2.2 ) * math.cos( t ) + b * ( rb + 2.2 ) * math.sin( t )
        rod( model, p, p + normal * 2.4, 0.55, "sh_steel", 5, caps=( False, True ) )
    for s in ( -1, 1 ):
        p = c + normal * 1.6 - a * ( ra + 1.4 ) + b * s * 3.5
        rod( model, p - b * 1.8, p + b * 1.8, 1.0, "sh_brass", 6, caps=( True, True ) )
    h = c + normal * 0.9 + a * ( ra - 3.0 )
    rod( model, h, h + normal * 3.0, 0.5, "sh_brass", 5 )
    rod( model, h + normal * 3.0 - b * 2.6, h + normal * 3.0 + b * 2.6, 0.6, "sh_brass", 5, caps=( True, True ) )


def _sight_glass( model, centre, normal, r=3.2 ):
    """ A round sight glass in its brass ring. """
    upv = np.array( ( 0.0, 0.0, 1.0 ) )
    a = _unit( np.cross( upv, normal ) )
    b = np.cross( normal, a )
    c = np.asarray( centre, float )
    RP.disc( model, "sh_glass", c + normal * 0.4, normal, r, 10 )
    _loop( model, c + normal * 0.6, a, b, r + 0.6, r + 0.6, 0.8, "sh_brass", 10, 5 )


def pot_still( model, e, n, z0, kind="wash", lyne=( 1.0, 0.0 ), lyne_length=120 ):
    """ A copper pot still on its floor at z0: kind "wash" (an onion pot 140 across and ~110 tall, its neck tapering
    from 41 to 17 across up to ~280 over the floor) or "spirit" (a pot 117 across, a boil ball under the neck, ~240
    tall). The swan neck bends over into the lyne arm, 14 across, falling 8 degrees along lyne (a plan direction) to
    lyne_length (plan inches) from the neck's axis. The pot stands on a green-painted steel ring girder on six legs,
    with the steam coils' header and its valve under it, the discharge pipe out of its bottom, a brass manway door on
    the shoulder facing away from the lyne arm, the charge inlet, an anti-vacuum valve and two sight glasses on the
    neck. Collision: the pot (and boil ball) as one 12-sided hull, "metal", the neck as a thin box up to 200 over the
    floor, nothing above. Returns the lyne arm's end ( e, n, z ), the middle of its end flange's face. """
    if kind not in STILLS:
        raise ValueError( f"unknown still {kind!r}: wash or spirit" )
    pot, neck, z_bend, sides, z_manway, z_charge = STILLS[kind]
    c = np.array( ( e, n, z0 ), float )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    d = _unit( ( lyne[0], lyne[1], 0.0 ) )
    front = -d
    side = np.cross( up, d )
    r_pot = max( r for r, z in pot if z < 80 )

    # the pot, the collar at the neck's foot and the neck
    revolve( model, c, up, pot, lambda k: "sh_copper" if k < 4 else "sh_copper_bright", sides, crease=40.0 )
    r_base, z_base = neck[0]
    _flange( model, c + up * ( z_base + 0.5 ), up, r_base - 0.3, "sh_brass", 24, 3.0, r_base + 2.0 )
    revolve( model, c, up, neck, "sh_copper_bright", 20 )
    r_top, z_top = neck[-1]
    _flange( model, c + up * z_top, up, r_top, "sh_brass", 20, 1.6, r_top + 1.8 )

    # the swan neck turning over into the lyne arm, which narrows to 14 across by the end of the bend
    corner = c + up * z_bend
    end = c + d * lyne_length + up * ( z_bend - lyne_length * LYNE_FALL )
    path, joints = _bend_path( [ c + up * ( z_top - 0.4 ), corner, end ], 16.0, steps=7 )
    lengths = np.concatenate( ( [ 0.0 ], np.cumsum( [ np.linalg.norm( q - p ) for p, q in zip( path, path[1:] ) ] ) ) )
    taper = 40.0
    radii = [ r_top + ( LYNE_R - r_top ) * min( 1.0, s / taper ) for s in lengths ]
    tube( model, path, radii, "sh_copper_bright", 16 )
    d_end = _unit( end - corner )
    _flange( model, end - d_end * 0.7, d_end, LYNE_R, "sh_brass", 16, 1.4, LYNE_R + 2.2 )
    # a strap holding the arm, from the bend's top
    _band( model, corner + d_end * 30 + up * ( -30 * LYNE_FALL ), d_end, LYNE_R, 2.0, "sh_steel", 12, 0.4 )

    # the stand: a ring girder under the pot's bottom on six legs with base plates
    r_ring = 0.71 * r_pot
    z_seat = _bottom_z( pot, r_ring ) - 0.2
    revolve( model, c, up, [ ( r_ring - 2.0, 17.0 ), ( r_ring + 2.0, 17.0 ), ( r_ring + 2.0, z_seat ),
                             ( r_ring - 2.0, z_seat ), ( r_ring - 2.0, 17.0 ) ], "sh_steel_green", 24, crease=30.0 )
    for k in range( 6 ):
        t = math.radians( 15.0 + 60.0 * k )
        p = c + r_ring * ( math.cos( t ) * side + math.sin( t ) * front )
        model.box( p + ( -2.5, -2.5, 0.75 ), p + ( 2.5, 2.5, 17.0 ), { "default": "sh_steel_green", "-z": None } )
        model.box( p + ( -4.5, -4.5, 0.0 ), p + ( 4.5, 4.5, 0.75 ), { "default": "sh_steel_green", "-z": None } )

    # the steam coils' header under the pot, fed up out of the floor beside it, with its valve
    x_out = r_pot + 16.0
    riser = c + side * x_out
    pipe( model, [ riser, riser + up * 11.0, c - side * 26.0 + up * 11.0 ], 3.0, "sh_steel" )
    for s in ( 1, -1 ):
        p = c + side * 26.0 * s
        rod( model, p + up * 11.0, p + up * ( _bottom_z( pot, 26.0 ) + 1.0 ), 3.0, "sh_steel", 8 )
    _valve( model, c + side * ( r_pot + 5.0 ) + up * 11.0, side, 3.0 )

    # the discharge pipe out of the bottom, to the drain at the front
    out = c + front * ( r_ring + 14.0 )
    pipe( model, [ c + up * 20.5, c + up * 7.0, out + up * 7.0, out ], 2.5, "sh_copper" )

    # the manway on the shoulder at the front, and the charge inlet and anti-vacuum valve behind it
    rm, ( nr, nz ) = _profile_at( pot, z_manway )
    normal = nr * front + nz * up
    _manway( model, c + up * z_manway + front * rm, normal )
    for angle, what in ( ( 140.0, "charge" ), ( -150.0, "vacuum" ) ):
        t = math.radians( angle )
        radial = math.cos( t ) * front + math.sin( t ) * side
        zz = z_charge if what == "charge" else z_charge + 6.0
        rr, ( nr, nz ) = _profile_at( pot, zz )
        p = c + up * zz + radial * rr
        nrm = nr * radial + nz * up
        if what == "charge":
            q = p + nrm * 7.0
            pipe( model, [ p - nrm * 1.0, q, q + up * 26.0 ], 3.0, "sh_copper" )
        else:
            rod( model, p - up * 1.0, p + up * 6.0, 2.2, "sh_brass", 8 )
            rod( model, p + up * 6.0, p + up * 7.6, 3.1, "sh_brass", 8, caps=( True, True ) )
    # two sight glasses on the neck, either side of the front
    z_s = z_base + 14.0
    rs, ( nr, nz ) = _profile_at( neck, z_s )
    for s in ( -1, 1 ):
        t = math.radians( 40.0 * s )
        radial = math.cos( t ) * front + math.sin( t ) * side
        _sight_glass( model, c + up * z_s + radial * rs, _unit( nr * radial + nz * up ) )

    # collision: the pot as one hull (on its stand), the neck as a thin box, nothing over 200
    rings = [ ( r_ring + 4.5, 0.0 ), ( r_ring + 4.5, 17.0 ) ] + [ ( r, z ) for r, z in pot[2::2] ] + [ pot[-1] ]
    rings.append( max( pot, key=lambda p: p[0] ) )
    _round_hull( model, e, n, [ ( r, z0 + z ) for r, z in rings ], METAL )
    half = 0.75 * r_base
    model.collision_box( ( e - half, n - half, z0 + pot[-1][1] ), ( e + half, n + half, z0 + min( 200.0, z_bend ) ),
                         METAL )
    return tuple( float( x ) for x in end )


def condenser( model, e, n, z0, height=200, r=16 ):
    """ An upright copper shell-and-tube condenser standing on the floor at z0, height tall: the shell on three
    green-painted steel legs clamped round it, a dome at each end on a brass flange, the vapour inlet standing up from
    the top dome, the tail pipe out of the bottom one and the cooling water's pipes (in near the bottom, out near the
    top) running down to the floor. Collision: one box, "metal". Returns ( the vapour inlet's top, the tail pipe's end ),
    each ( e, n, z ). """
    c = np.array( ( e, n, z0 ), float )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    dome = 0.7 * r
    z_b, z_t = 24.0 + dome, height - dome - 1.0
    cap = [ ( 0.0, -dome ), ( 0.42 * r, -0.92 * dome ), ( 0.72 * r, -0.72 * dome ), ( 0.9 * r, -0.45 * dome ),
            ( 0.98 * r, -0.2 * dome ), ( r, 0.0 ) ]
    prof = [ ( rr, z_b + t ) for rr, t in cap ] + [ ( rr, z_t - t ) for rr, t in reversed( cap ) ]
    revolve( model, c, up, prof, "sh_copper", 24, crease=30.0 )
    for z in ( z_b, z_t ):
        _flange( model, c + up * z, up, r, "sh_brass", 24, 2.2, r + 1.4 )
    # legs, clamped by a band round the shell
    _band( model, c + up * ( z_b + 8.0 ), up, r, 4.0, "sh_steel_green", 20, 0.7 )
    for k in range( 3 ):
        t = math.radians( 90.0 + 120.0 * k )
        p = c + ( r + 2.2 ) * np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
        model.box( p + ( -1.75, -1.75, 0.6 ), p + ( 1.75, 1.75, z_b + 10.0 ), { "default": "sh_steel_green",
                                                                               "-z": None } )
        model.box( p + ( -3.5, -3.5, 0.0 ), p + ( 3.5, 3.5, 0.6 ), { "default": "sh_steel_green", "-z": None } )
    # cooling water: in near the bottom, out near the top, both down to the floor on the same side
    for angle, z in ( ( 200.0, z_b + 12.0 ), ( 228.0, z_t - 12.0 ) ):
        t = math.radians( angle )
        w = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
        p = c + w * r + up * z
        q = c + w * ( r + 9.0 ) + up * z
        pipe( model, [ p - w * 0.5, q, c + w * ( r + 9.0 ) ], 2.5, "sh_steel_green" )
    # the vapour inlet on top, and the tail pipe out of the bottom
    inlet = c + up * ( z_t + dome + 8.0 )
    rod( model, c + up * ( z_t + dome - 1.0 ), inlet, LYNE_R, "sh_copper", 16 )
    _flange( model, inlet - up * 0.7, up, LYNE_R, "sh_brass", 16, 1.4, LYNE_R + 2.2 )
    w = np.array( ( math.cos( math.radians( 20.0 ) ), math.sin( math.radians( 20.0 ) ), 0.0 ) )
    low = z_b - dome - 6.0
    tail = c + w * ( r + 12.0 ) + up * low
    pipe( model, [ c + up * ( z_b - dome + 1.0 ), c + up * low, tail ], 1.5, "sh_copper" )
    model.collision_box( ( e - r - 4.0, n - r - 4.0, z0 ), ( e + r + 4.0, n + r + 4.0, z0 + height ), METAL )
    return tuple( float( x ) for x in inlet ), tuple( float( x ) for x in tail )


def spirit_safe( model, e, n, z0, facing="+n" ):
    """ The spirit safe, where the stillman watches the run and cuts the heart: a brass and glass box 59 wide, 24 deep
    and 47 tall on a panelled wooden pedestal, 90 tall in all, its front towards facing. Inside: the spouts running
    into three glass bowls, and two hydrometer jars with their hydrometers. Padlocked on two hasps under the lid,
    which carries the cut's brass lever and the inlets from the condensers; the outlets go down its back. Collision:
    one box, "metal". """
    F = frame_for( e, n, z0, facing )
    W, D = 29.5, 12.0
    # pedestal: a black plinth, a panelled body and a moulded cap
    F.box( model, -27.5, 27.5, -10.5, 10.5, 0.0, 4.0, { "default": "sh_paint_black", "bottom": None } )
    F.box( model, -26.0, 26.0, -9.5, 9.5, 4.0, 40.0, { "default": "sh_pine", "bottom": None, "top": None } )
    for x in ( -13.0, 13.0 ):
        F.box( model, x - 10.5, x + 10.5, 9.5, 10.2, 8.5, 35.5, { "default": "sh_pine", "back": None } )
    for x in ( -26.0, 26.0 ):
        s = 1 if x > 0 else -1
        F.box( model, x - ( 0.0 if s > 0 else 0.7 ), x + ( 0.7 if s > 0 else 0.0 ), -6.5, 6.5, 8.5, 35.5,
               { "default": "sh_pine", "left" if s > 0 else "right": None } )
    F.box( model, -29.0, 29.0, -11.5, 11.5, 40.0, 43.0, { "default": "sh_pine", "bottom": "sh_pine" } )
    # the safe: a brass tray, corner posts, front mullions, a brass back, the lid with its raised top
    F.box( model, -W, W, -D, D, 43.0, 47.0, { "default": "sh_brass", "bottom": None } )
    for x0, x1 in ( ( -W, -W + 2.0 ), ( W - 2.0, W ) ):
        for y0, y1 in ( ( -D, -D + 2.0 ), ( D - 2.0, D ) ):
            F.box( model, x0, x1, y0, y1, 47.0, 85.0, { "default": "sh_brass", "top": None, "bottom": None } )
    for x in ( -9.8, 9.8 ):
        F.box( model, x - 0.6, x + 0.6, D - 1.4, D, 47.0, 85.0, { "default": "sh_brass", "top": None,
                                                                 "bottom": None } )
    F.box( model, -W + 2.0, W - 2.0, -D, -D + 0.4, 47.0, 85.0, { "default": "sh_brass", "top": None,
                                                                "bottom": None } )
    F.box( model, -W - 0.5, W + 0.5, -D - 0.5, D + 0.5, 85.0, 88.0, "sh_brass" )
    F.box( model, -W + 2.0, W - 2.0, -D + 2.0, D - 2.0, 88.0, 90.0, { "default": "sh_brass", "bottom": None } )
    # the glass: three panes in front, one each side
    for x0, x1 in ( ( -W + 2.0, -10.4 ), ( -9.2, 9.2 ), ( 10.4, W - 2.0 ) ):
        F.quad( model, "sh_glass", ( x0 + x1 ) / 2, D - 0.7, 66.0, x1 - x0, 38.0, "front" )
    for s, face in ( ( 1, "right" ), ( -1, "left" ) ):
        F.quad( model, "sh_glass", s * ( W - 0.7 ), 0.0, 66.0, 2 * D - 4.0, 38.0, face )
    # inside: the spouts and bowls, the hydrometer jars
    bowl = [ ( 0.0, 0.0 ), ( 2.6, 0.3 ), ( 4.2, 1.3 ), ( 5.0, 2.8 ), ( 5.3, 4.4 ) ]
    for x in ( -16.0, 0.0, 16.0 ):
        revolve( model, F.p( x, 2.0, 47.0 ), F.z, bowl, "sh_glass", 10 )
        tube( model, _bend_path( [ F.p( x, -D + 0.4, 72.0 ), F.p( x, 2.0, 72.0 ), F.p( x, 2.0, 55.5 ) ], 2.5 )[0],
              0.8, "sh_brass", 6 )
    for x in ( -8.0, 8.0 ):
        revolve( model, F.p( x, -5.5, 47.0 ), F.z, [ ( 0.0, 0.0 ), ( 2.3, 0.0 ), ( 2.3, 16.0 ) ], "sh_glass", 10 )
        rod( model, F.p( x, -5.5, 49.0 ), F.p( x, -5.5, 71.0 ), 0.3, "sh_brass", 4, caps=( False, True ) )
        sphere( model, F.p( x, -5.5, 52.5 ), 1.2, "sh_brass", 6, 3 )
    # two padlocked hasps under the lid
    for x in ( -16.0, 16.0 ):
        F.box( model, x - 0.8, x + 0.8, D + 0.4, D + 0.9, 81.5, 87.0, "sh_brass" )
        F.box( model, x - 1.3, x + 1.3, D + 0.6, D + 1.8, 77.5, 80.8, "sh_brass" )
        tube( model, [ F.p( x - 0.8, D + 1.2, 80.8 ), F.p( x - 0.8, D + 1.2, 82.6 ), F.p( x + 0.8, D + 1.2, 82.6 ),
                       F.p( x + 0.8, D + 1.2, 80.8 ) ], 0.25, "sh_steel", 4 )
    # the lever on the lid, the inlets from the condensers, the outlets down the back
    rod( model, F.p( -20.0, 0.0, 90.0 ), F.p( -20.0, 7.0, 97.0 ), 0.5, "sh_brass", 5 )
    sphere( model, F.p( -20.0, 7.0, 97.0 ), 1.3, "sh_brass", 6, 3 )
    for x in ( -6.0, 6.0 ):
        rod( model, F.p( x, -4.0, 90.0 ), F.p( x, -4.0, 98.0 ), 1.5, "sh_copper", 8 )
        _flange( model, F.p( x, -4.0, 97.4 ), F.z, 1.5, "sh_copper", 8, 1.0 )
        pipe( model, [ F.p( x, -D + 2.0, 44.0 ), F.p( x, -D - 2.0, 44.0 ), F.p( x, -D - 2.0, 0.0 ) ], 1.2,
              "sh_copper", flanges=False )
    F.collide( model, -W - 0.5, W + 0.5, -D - 0.5, D + 0.5, 0.0, 90.0, METAL )


def washback( model, e, n, floor_z, r=80, top=72 ):
    """ The top of a washback, the rest of it below the tun room's floor at floor_z: Oregon pine staves bound by steel
    hoops up to top over the floor, a planked lid on the rim with its inspection hatch, the switcher's gear motor on a
    beam across the lid, and the wort pipe coming over the rim. Collision: a 12-sided hull, "wood". Returns the lid's
    height. """
    c = np.array( ( e, n, floor_z ), float )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    sides = 28
    _grain( model, "sh_pine" )
    # staves and hoops (flush steel bands), the grain running up the staves
    hoops = [ h for h in ( 8.0, 30.0, 52.0, top - 7.0 ) if h + 3.5 < top - 1.0 ]
    ts, parts = [ 0.0 ], []
    for h in hoops:
        ts += [ h, h + 3.5 ]
        parts += [ "stave", "hoop" ]
    ts.append( top )
    parts.append( "stave" )
    prof = [ ( float( r ), t ) for t in ts ]
    width = 2 * math.pi * r / sides / TILES["sh_pine"]
    revolve( model, c, up, prof, lambda k: "sh_pine" if parts[k] == "stave" else "sh_steel", sides,
             uv=lambda k, i, t: None if parts[k] == "hoop" else ( i * width, t / TILES["sh_pine"] ) )
    # the lid: planks across it overhanging the rim by an inch, its edge, and the rim under the overhang
    R, lid = r + 1.0, top + 2.0
    revolve( model, c, up, [ ( float( r ), top ), ( R, top ), ( R, lid ) ], "sh_pine", sides )
    plank = 11.0
    count = int( math.ceil( 2 * R / plank ) )
    edges = [ -R + 2 * R * k / count for k in range( count + 1 ) ]
    for y0, y1 in zip( edges, edges[1:] ):
        h0, h1 = ( math.sqrt( max( R * R - y * y, 0.0 ) ) for y in ( y0, y1 ) )
        pts = [ ( -h0, y0 ), ( h0, y0 ), ( h1, y1 ), ( -h1, y1 ) ]
        outward( model, "sh_pine", _dedupe( [ c + ( x, y, lid ) for x, y in pts ] ), up )
    # the inspection hatch: a steel frame and a hinged planked door with a handle
    hx = 0.52 * r
    model.box( c + ( hx - 15.0, -12.0, lid ), c + ( hx + 15.0, 12.0, lid + 1.2 ),
               { "default": "sh_steel", "-z": None } )
    model.box( c + ( hx - 13.0, -10.0, lid + 1.2 ), c + ( hx + 13.0, 10.0, lid + 2.4 ),
               { "default": "sh_pine", "-z": None } )
    for y in ( -6.0, 6.0 ):
        rod( model, c + ( hx - 13.5, y - 2.0, lid + 2.0 ), c + ( hx - 13.5, y + 2.0, lid + 2.0 ), 0.8, "sh_steel", 6,
             caps=( True, True ) )
    tube( model, [ c + ( hx + 9.0, -3.5, lid + 2.4 ), c + ( hx + 9.0, -3.5, lid + 4.4 ), c + ( hx + 9.0, 3.5, lid + 4.4 ),
                   c + ( hx + 9.0, 3.5, lid + 2.4 ) ], 0.45, "sh_steel", 5 )
    # the switcher: a beam across the lid on two bearers, the gearbox at the middle with its motor, the shaft down
    model.box( c + ( -4.0, -R + 2.0, lid ), c + ( 4.0, R - 2.0, lid + 1.5 ), { "default": "sh_steel_green",
                                                                               "-z": None } )
    model.box( c + ( -3.0, -R + 2.0, lid + 1.5 ), c + ( 3.0, R - 2.0, lid + 8.0 ), { "default": "sh_steel_green",
                                                                                   "-z": None } )
    model.box( c + ( -8.0, -8.0, lid + 8.0 ), c + ( 8.0, 8.0, lid + 22.0 ), { "default": "sh_steel_green",
                                                                             "-z": None } )
    rod( model, c + ( 8.0, 0.0, lid + 15.0 ), c + ( 24.0, 0.0, lid + 15.0 ), 6.5, "sh_steel_green", 12,
         caps=( False, True ) )
    model.box( c + ( 10.0, -4.0, lid + 21.0 ), c + ( 16.0, 4.0, lid + 25.0 ), { "default": "sh_paint_black",
                                                                               "-z": None } )
    rod( model, c + ( 0.0, 0.0, lid + 22.0 ), c + ( 0.0, 0.0, lid + 26.0 ), 2.2, "sh_steel", 8, caps=( False, True ) )
    # the wort pipe: down through the lid, coming over the rim from the main
    py = -0.42 * r
    px = -0.62 * r
    pipe( model, [ c + ( px, py, lid ), c + ( px, py, lid + 30.0 ), c + ( -( R + 22.0 ), py, lid + 30.0 ),
                   c + ( -( R + 22.0 ), py, 0.0 ) ], 4.0, "sh_copper" )
    _round_hull( model, e, n, [ ( R, floor_z ), ( R, floor_z + lid ) ], WOOD )
    return floor_z + lid


def mash_tun( model, e, n, z0, r=110, height=90 ):
    """ A mash tun standing on the floor at z0: a stainless vessel r round and height tall with two stiffening rings,
    a copper canopy dome on a brass flange at its rim, an inspection hatch in the dome, the rake's gear drive and its
    motor on top, the grist masher's pipe coming down into the dome, and the drains and their valves at its foot.
    Collision: a 12-sided hull, "metal". Returns the gear drive's top z. """
    c = np.array( ( e, n, z0 ), float )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    sides = 40
    H = float( height )
    # the body, its base ring and stiffening rings
    revolve( model, c, up, [ ( float( r ), 4.0 ), ( float( r ), H ) ], "sh_stainless", sides )
    revolve( model, c, up, [ ( r + 1.5, 0.0 ), ( r + 1.5, 4.0 ), ( float( r ), 4.0 ) ], "sh_steel_green", sides )
    for z in ( 0.36 * H, 0.7 * H ):
        _band( model, c + up * z, up, r, 3.0, "sh_stainless", sides, 1.4 )
    # the copper canopy on its flange
    _flange( model, c + up * ( H + 1.0 ), up, r - 0.5, "sh_brass", sides, 2.0, r + 2.5 )
    dome = [ ( float( r ), H + 2.0 ), ( r - 3.0, H + 8.0 ), ( r - 12.0, H + 17.0 ), ( r - 28.0, H + 26.0 ),
             ( r - 50.0, H + 33.0 ), ( r - 75.0, H + 37.5 ), ( 28.0, H + 39.5 ), ( 0.0, H + 40.0 ) ]
    revolve( model, c, up, dome, "sh_copper", sides, crease=30.0 )
    # the hatch in the dome's slope, facing +e
    zh = H + 23.0
    rh, ( nr, nz ) = _profile_at( dome, zh )
    radial = np.array( ( 1.0, 0.0, 0.0 ) )
    normal = nr * radial + nz * up
    along = np.cross( up, radial )
    slope = np.cross( normal, along )
    hc = c + up * zh + radial * rh
    model.oriented_box( hc + normal * 0.8, ( along, slope, normal ), ( 30.0, 26.0, 1.6 ), "sh_stainless" )
    model.oriented_box( hc + normal * 2.0, ( along, slope, normal ), ( 25.0, 21.0, 1.2 ), "sh_copper_bright" )
    rod( model, hc + normal * 2.6 + along * 9.0 - slope * 3.0, hc + normal * 2.6 + along * 9.0 + slope * 3.0, 0.6,
         "sh_brass", 5, caps=( True, True ) )
    # the rake's gear drive on top, its motor and junction box
    zt = H + 39.8
    revolve( model, c, up, [ ( 27.0, zt ), ( 27.0, zt + 4.0 ), ( 24.0, zt + 4.0 ), ( 24.0, zt + 24.0 ),
                             ( 18.0, zt + 27.0 ), ( 0.0, zt + 27.0 ) ], "sh_steel_green", 20, crease=30.0 )
    rod( model, c + ( 0.0, 10.0, zt + 34.0 ), c + ( 0.0, -20.0, zt + 34.0 ), 8.5, "sh_steel_green", 12,
         caps=( True, True ) )
    model.box( c + ( -6.0, -4.0, zt + 27.0 ), c + ( 6.0, 4.0, zt + 26.0 + 9.5 ), { "default": "sh_steel_green",
                                                                                "-z": None } )
    model.box( c + ( 8.5, -6.0, zt + 30.0 ), c + ( 12.5, 2.0, zt + 38.0 ), { "default": "sh_paint_black",
                                                                            "-z": None } )
    # the grist masher's pipe, coming down from the hopper into the dome
    my = 0.25 * r
    pipe( model, [ c + ( -r - 40.0, my, H + 110.0 ), c + ( -r + 34.0, my, H + 110.0 ), c + ( -r + 34.0, my, H + 22.0 ) ],
          7.0, "sh_stainless" )
    # drains at the foot, each through a valve into the floor
    for angle in ( 200.0, 235.0 ):
        t = math.radians( angle )
        w = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
        p = c + w * ( r - 1.0 ) + up * 12.0
        q = c + w * ( r + 16.0 ) + up * 12.0
        pipe( model, [ p, q, c + w * ( r + 16.0 ) ], 4.0, "sh_steel" )
        _valve( model, c + w * ( r + 7.0 ) + up * 12.0, w, 4.0 )
    _round_hull( model, e, n, [ ( r + 2.5, z0 ), ( r + 2.5, z0 + H + 3.0 ), ( r - 50.0, z0 + H + 33.0 ),
                                ( 27.0, z0 + zt + 27.0 ) ], METAL )
    return z0 + zt + 27.0


# ---------------------------------------------------------------------------------------------------------------------
# Road vehicles

# railhead_props' road vehicles repainted: its rw_ paints for the design doc's sh_ ones
RW_TO_SH = { "rw_yellow_paint": "sh_paint_yellow", "rw_steel_dark": "sh_paint_black", "rw_black": "sh_paint_black",
             "rw_rubber": "sh_rubber", "rw_steel_grey": "sh_steel", "rw_white_paint": "sh_paint_white",
             "rw_red_paint": "sh_paint_red", "rw_window_dark": "sh_window_dark", "rw_wood": "sh_planks_grey" }


def _wrap( model, build, paints ):
    """ Draws build( a model of its own ) and copies it into model with each paint repainted by paints (one that isn't
    there stays), keeping its UVs, normals, grain and collision. Returns what build returned. """
    temp = K.Model()
    result = build( temp )
    for paint, faces in temp.polygons.items():
        new = paints.get( paint, paint )
        offset = len( model.polygons[new] )
        for i in range( len( faces ) ):
            if ( paint, i ) in temp.polygon_uvs:
                model.polygon_uvs[( new, offset + i )] = temp.polygon_uvs[( paint, i )]
            if ( paint, i ) in temp.polygon_normals:
                model.polygon_normals[( new, offset + i )] = temp.polygon_normals[( paint, i )]
        model.polygons[new].extend( faces )
    model.boxes.extend( temp.boxes )
    model.hulls.extend( temp.hulls )
    model.props.extend( temp.props )
    model.material_overrides.update( { paints.get( p, p ): v for p, v in temp.material_overrides.items() } )
    model.tile_overrides.update( { paints.get( p, p ): v for p, v in temp.tile_overrides.items() } )
    model.grain_paints.update( paints.get( p, p ) for p in temp.grain_paints )
    return result


def car( model, e, n, along="+n", paint="sh_paint_blue", z0=0.0, kind="hatch" ):
    """ railhead_props.car (a parked compact car, kind "hatch" 4.28 m or "estate" 4.63 m, nose towards along, ( e, n )
    its footprint's middle) in sh_ paints, its body in paint. Collision: one box, "metal". """
    return _wrap( model, lambda m: RP.car( m, e, n, along, "rw_train_grey", z0, kind ),
                  { **RW_TO_SH, "rw_train_grey": paint } )


def van( model, e, n, along="+n", paint="sh_paint_white", z0=0.0 ):
    """ railhead_props.van (a parked 4.9 m panel van) in sh_ paints, its body in paint. Collision: one box,
    "metal". """
    return _wrap( model, lambda m: RP.van( m, e, n, along, "rw_train_white", z0 ),
                  { **RW_TO_SH, "rw_train_white": paint } )


def _superellipse( a, b, p, sides ):
    """ Points ( x, z ) round | x / a |^p + | z / b |^p = 1, from the bottom middle round by +x, and their outward
    normals. """
    pts, nrm = [], []
    for k in range( sides ):
        t = -math.pi / 2 + 2 * math.pi * k / sides
        c, s = math.cos( t ), math.sin( t )
        x = a * math.copysign( abs( c ) ** ( 2.0 / p ), c )
        z = b * math.copysign( abs( s ) ** ( 2.0 / p ), s )
        gx = math.copysign( abs( x / a ) ** ( p - 1 ), x ) / a
        gz = math.copysign( abs( z / b ) ** ( p - 1 ), z ) / b
        length = math.hypot( gx, gz ) or 1.0
        pts.append( ( x, z ) )
        nrm.append( ( gx / length, gz / length ) )
    return pts, nrm


def _section_loft( model, F, sec, nrm, zc, stations, paint ):
    """ A closed section ( its points ( x, z ) and normals ) swept through stations [ ( y, scale, lean ) ] in F: each
    point at ( scale x, y, zc + scale z ), shaded with the section's normal leaned along y by lean (-1..1). Two
    stations at one y make a flat step (a ring standing proud); a scale of 0 closes it to a point. """
    sides = len( sec )

    def ring( y, f ):
        return [ ( f * x, y, zc + f * z ) for x, z in sec ]

    def normals( w ):
        k = 1.0 - abs( w )
        return [ tuple( np.array( ( k * nx, w, k * nz ) ) / math.sqrt( ( k * nx ) ** 2 + w * w + ( k * nz ) ** 2 ) )
                 for nx, nz in nrm ]

    for ( y0, f0, w0 ), ( y1, f1, w1 ) in zip( stations, stations[1:] ):
        r0, r1 = ring( y0, f0 ), ring( y1, f1 )
        n0, n1 = normals( w0 ), normals( w1 )
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            pts = [ r0[k], r0[k1], r1[k1], r1[k] ]
            if abs( y1 - y0 ) < 1e-6:
                RP._fpoly( model, F, paint, pts, ( 0.0, -1.0 if f1 > f0 else 1.0, 0.0 ) )
                continue
            ns = [ n0[k], n0[k1], n1[k1], n1[k] ]
            if f1 == 0:
                pts, ns = pts[:3], ns[:3]
            elif f0 == 0:
                pts, ns = pts[1:], ns[1:]
            RP._fpoly( model, F, paint, pts, tuple( np.sum( ns, axis=0 ) ), normals=ns )


def _on_face( model, F, p0, p1, t0, t1, x0, x1, paint, lift=0.06, uv=None ):
    """ A panel on a side profile's face from ( y, z ) p0 to p1 (a counter-clockwise profile), from t0 to t1 of the
    way along it and from x0 to x1 across, lifted off it. """
    a, d = np.asarray( p0, float ), np.asarray( p1, float ) - np.asarray( p0, float )
    nn = np.array( ( d[1], -d[0] ) ) / np.linalg.norm( d )
    pa, pb = a + d * t0 + nn * lift, a + d * t1 + nn * lift
    RP._fpoly( model, F, paint, [ ( x0, pa[0], pa[1] ), ( x1, pa[0], pa[1] ), ( x1, pb[0], pb[1] ),
                                  ( x0, pb[0], pb[1] ) ], ( 0.0, nn[0], nn[1] ), uv=uv )


def _arch( model, F, y, zc, r, x0, x1, paint, a0=15.0, a1=165.0, steps=7 ):
    """ A mudguard: a strip bent round an arc of radius r about ( y, zc ) from a0 to a1 degrees (0 forward, 90 up),
    from x0 to x1 across, painted both sides. """
    arc = [ ( y + r * math.cos( math.radians( a ) ), zc + r * math.sin( math.radians( a ) ) )
            for a in np.linspace( a0, a1, steps + 1 ) ]
    for ( ya, za ), ( yb, zb ) in zip( arc, arc[1:] ):
        out = ( 0.0, ( ya + yb ) / 2 - y, ( za + zb ) / 2 - zc )
        pts = [ ( x0, ya, za ), ( x1, ya, za ), ( x1, yb, zb ), ( x0, yb, zb ) ]
        RP._fpoly( model, F, paint, pts, out )
        RP._fpoly( model, F, paint, pts, tuple( -v for v in out ) )


TANKER_AXLES = ( 147.0, 70.0, -60.0, -114.0 )      # two steered axles under and behind the cab, then the tandem
TANKER_TYRE = ( 21.0, 12.4 )                        # 315/80 R22.5: 1.07 m across, 315 mm wide


def tanker( model, e, n, z0, facing ):
    """ A rigid 8x4 road tanker, 394 long (10 m), 98 wide (2.49 m) and 138 tall to its handrails, its cab towards
    facing and ( e, n ) its footprint's middle: a plain white forward-control day cab on two steered axles, a tandem
    drive on twin wheels (315/80 R22.5 tyres all round), and a brushed stainless tank of ~22,000 l in three
    compartments (a box-oval section 94 wide and 66 tall, dished heads, a ring at each bulkhead) on a subframe. On top,
    three manlids between the overturn rails, a grating walkway and yellow handrails; up the back a ladder; along the
    chassis the hose tubes, the fuel tank, the battery box and sideguards; the rear valve cabinet, mudwings and flaps,
    the orange ADR plates front and back and the flammable (class 3) labels on both sides and the back; no maker's
    name. Its mirrors stand 8 proud of each side. Collision: "metal" boxes: the cab, the tank on its chassis (from 16
    up) and the two pairs of axles. """
    F = frame_for( e, n, z0, facing )
    WH, BLK = "sh_paint_white", "sh_paint_black"
    r_t, w_t = TANKER_TYRE
    flam = _quad_uv( _rect( "sh_signs", "flammable" ) )

    # the tank: a box-oval section, dished heads, a ring standing proud at each bulkhead
    a, b, sides = 47.0, 33.0, 28
    zc = 46.0 + b
    top = zc + b
    sec, nrm = _superellipse( a, b, 2.5, sides )
    y_r, y_f = -181.0, 92.0
    head = [ ( 0.0, 1.0, 0.0 ), ( 3.2, 0.965, 0.3 ), ( 6.0, 0.86, 0.58 ), ( 8.2, 0.64, 0.8 ), ( 9.5, 0.34, 0.94 ),
             ( 9.9, 0.0, 1.0 ) ]
    stations = [ ( y_r - d, f, -w ) for d, f, w in reversed( head ) ]
    for yb in ( -88.0, 2.0 ):
        stations += [ ( yb - 0.8, 1.0, 0.0 ), ( yb - 0.8, 1.012, 0.0 ), ( yb + 0.8, 1.012, 0.0 ), ( yb + 0.8, 1.0, 0.0 ) ]
    stations += [ ( y_f + d, f, w ) for d, f, w in head ]
    _section_loft( model, F, sec, nrm, zc, stations, "sh_stainless" )

    # the chassis rails, the tank's subframe, axles, springs, the tandem's differentials and the wheels
    for xs in ( -1, 1 ):
        x0, x1 = sorted( ( xs * 13.5, xs * 16.8 ) )
        F.box( model, x0, x1, -190.0, 186.0, 29.0, 41.0, BLK )
        x0, x1 = sorted( ( xs * 14.0, xs * 18.0 ) )
        F.box( model, x0, x1, y_r - 4.0, y_f + 4.0, 41.0, 47.5, BLK, skip=( "top", ) )
    for k, y in enumerate( TANKER_AXLES ):
        twin = k >= 2
        rod( model, F.p( -36.0, y, r_t ), F.p( 36.0, y, r_t ), 3.0, BLK, 6 )
        for xs in ( -1, 1 ):
            x0, x1 = sorted( ( xs * 13.0, xs * 19.0 ) )
            F.box( model, x0, x1, y - 24.0, y + 24.0, 25.0, 30.0, BLK )
            tyres = [ 48.6 ] + ( [ 48.6 - w_t - 1.0 ] if twin else [] )
            for xt in tyres:
                rod( model, F.p( xs * ( xt - w_t ), y, r_t ), F.p( xs * xt, y, r_t ), r_t, "sh_rubber", 14,
                     caps=( True, True ) )
            disc( model, "sh_steel", F.p( xs * 48.65, y, r_t ), xs * F.x, 12.5, sides=12 )
            rod( model, F.p( xs * 48.6, y, r_t ), F.p( xs * 49.6, y, r_t ), 5.0, "sh_steel", 8, caps=( False, True ) )
        if twin:
            F.box( model, -8.0, 8.0, y - 7.0, y + 7.0, 13.0, 29.0, BLK )

    # mudguards: arches over the steered wheels, a mudwing over the tandem, flaps behind
    for y in TANKER_AXLES[:2]:
        for xs in ( -1, 1 ):
            x0, x1 = sorted( ( xs * 35.0, xs * 49.5 ) )
            _arch( model, F, y, r_t, r_t + 3.5, x0, x1, BLK )
    for xs in ( -1, 1 ):
        x0, x1 = sorted( ( xs * 29.0, xs * 49.0 ) )
        F.box( model, x0, x1, -138.0, -37.0, 43.0, 44.5, BLK )
        x0, x1 = sorted( ( xs * 30.0, xs * 48.0 ) )
        F.box( model, x0, x1, -140.0, -139.0, 8.0, 43.0, "sh_rubber" )
        x0, x1 = sorted( ( xs * 35.0, xs * 48.0 ) )
        F.box( model, x0, x1, 46.0, 47.0, 10.0, 44.0, "sh_rubber" )
        # sideguards between the axles
        x0, x1 = sorted( ( xs * 46.8, xs * 48.2 ) )
        for z in ( 17.0, 29.0 ):
            F.box( model, x0, x1, -36.0, 46.0, z, z + 3.5, "sh_steel" )
    # hose tubes, the fuel tank (left) and the battery box (right)
    rod( model, F.p( -37.5, 2.0, 33.0 ), F.p( -37.5, 44.0, 33.0 ), 9.5, "sh_stainless", 14, caps=( True, True ) )
    for y in ( 9.0, 37.0 ):
        rod( model, F.p( -37.5, y - 0.8, 33.0 ), F.p( -37.5, y + 0.8, 33.0 ), 9.9, BLK, 14 )
    rod( model, F.p( -40.0, -36.0, 35.0 ), F.p( -40.0, -4.0, 35.0 ), 4.5, "sh_stainless", 10, caps=( True, True ) )
    rod( model, F.p( 40.0, -36.0, 35.0 ), F.p( 40.0, 16.0, 35.0 ), 4.5, "sh_stainless", 10, caps=( True, True ) )
    F.box( model, 32.0, 45.0, 20.0, 46.0, 24.0, 41.0, BLK )
    F.box( model, 31.5, 45.5, 19.5, 46.5, 41.0, 42.5, BLK )

    # the cab: a forward-control day cab, its front lower panels, the step wells behind the front wheels
    prof = [ ( 105.0, 50.0 ), ( 195.0, 50.0 ), ( 196.0, 72.0 ), ( 193.0, 106.0 ), ( 189.0, 119.0 ), ( 182.0, 124.0 ),
             ( 105.0, 124.0 ) ]
    RP._side_prism( model, F, prof, -49.0, 49.0, lambda k: BLK if k == 0 else WH, WH )
    _on_face( model, F, prof[2], prof[3], 0.05, 0.95, -44.5, 44.5, "sh_window_dark" )
    _on_face( model, F, prof[1], prof[2], 0.15, 0.85, -36.0, 36.0, BLK )
    F.box( model, -49.0, 49.0, 186.0, 196.0, 34.0, 50.0, WH, skip=( "top", ) )
    F.box( model, -49.0, 49.0, 187.0, 197.0, 15.0, 34.0, BLK )
    F.box( model, -46.0, 46.0, 189.5, 196.0, 118.5, 120.5, BLK )                          # sun visor
    for xs in ( -1, 1 ):
        x0, x1 = sorted( ( xs * 41.0, xs * 49.0 ) )
        F.box( model, x0, x1, 170.0, 186.0, 30.0, 50.0, WH, skip=( "top", ) )
        x0, x1 = sorted( ( xs * 43.0, xs * 49.0 ) )
        F.box( model, x0, x1, 105.0, 122.0, 16.0, 50.0, BLK, skip=( "top", ) )
        x0, x1 = sorted( ( xs * 43.5, xs * 49.6 ) )
        for z in ( 18.5, 32.0 ):
            F.box( model, x0, x1, 106.5, 120.5, z, z + 1.5, "sh_steel" )
        # the door over the front wheel, its window, handle and seams; a grab handle on the cab's back pillar
        side = "right" if xs > 0 else "left"
        RP._fpoly( model, F, "sh_window_dark", [ ( xs * 49.06, 116.0, 83.0 ), ( xs * 49.06, 172.0, 83.0 ),
                                                 ( xs * 49.06, 170.5, 109.0 ), ( xs * 49.06, 116.0, 109.0 ) ],
                   ( xs, 0, 0 ) )
        for y in ( 110.5, 177.5 ):
            F.quad( model, BLK, xs * 49.06, y, 85.5, 0.6, 67.0, side )
        F.quad( model, BLK, xs * 49.06, 118.0, 77.0, 5.0, 1.6, side )
        rod( model, F.p( xs * 49.7, 107.0, 56.0 ), F.p( xs * 49.7, 107.0, 100.0 ), 0.6, BLK, 5 )
        # a quarter-light ahead of the door, behind the A-pillar
        RP._fpoly( model, F, "sh_window_dark", [ ( xs * 49.06, 181.0, 92.0 ), ( xs * 49.06, 191.5, 92.0 ),
                                                 ( xs * 49.06, 189.5, 109.0 ), ( xs * 49.06, 181.0, 109.0 ) ],
                   ( xs, 0, 0 ) )
        # mirrors on their arms, lamps and indicators in the bumper
        rod( model, F.p( xs * 48.6, 189.0, 104.0 ), F.p( xs * 55.5, 187.5, 106.0 ), 0.7, BLK, 5 )
        x0, x1 = sorted( ( xs * 53.5, xs * 57.0 ) )
        F.box( model, x0, x1, 185.5, 188.0, 84.0, 110.0, BLK )
        F.quad( model, "sh_stainless", xs * 37.0, 197.05, 27.5, 13.0, 7.0 )
        F.quad( model, "sh_paint_orange", xs * 45.5, 197.05, 27.5, 4.5, 7.0 )
    F.quad( model, WH, 0.0, 197.05, 21.0, 20.5, 4.3 )                                    # number plate
    F.quad( model, "sh_paint_orange", 0.0, 196.05, 42.0, 15.7, 11.8 )                     # ADR plate
    F.quad( model, BLK, 0.0, 196.07, 42.0, 15.0, 0.5 )

    # on top: manlids between the overturn rails, the walkway, the handrails
    for yc in ( -135.0, -43.0, 47.0 ):
        rod( model, F.p( 0.0, yc, top - 2.5 ), F.p( 0.0, yc, top + 2.5 ), 9.5, "sh_stainless", 14, caps=( False, True ) )
        _flange( model, F.p( 0.0, yc, top + 2.0 ), F.z, 9.5, "sh_stainless", 14, 1.0, 10.8 )
        rod( model, F.p( 0.0, yc + 4.0, top + 2.5 ), F.p( 0.0, yc + 4.0, top + 5.0 ), 1.8, "sh_stainless", 8,
             caps=( False, True ) )
        F.box( model, -3.0, 3.0, yc - 11.5, yc - 9.5, top, top + 3.5, "sh_stainless" )
    for xs in ( -1, 1 ):
        x0, x1 = sorted( ( xs * 15.0, xs * 17.5 ) )
        F.box( model, x0, x1, -170.0, 86.0, top - 4.0, top + 6.0, "sh_stainless" )
    for y0, y1 in ( ( -168.0, -147.0 ), ( -123.0, -55.0 ), ( -31.0, 35.0 ), ( 59.0, 84.0 ) ):
        F.box( model, -15.0, 15.0, y0, y1, top + 3.8, top + 4.6, { "default": "sh_grating", "bottom": None } )
    posts = ( -166.0, -112.0, -58.0, -4.0, 50.0, 84.0 )
    for xs in ( -1, 1 ):
        x = xs * 16.25
        for y in posts:
            rod( model, F.p( x, y, top + 6.0 ), F.p( x, y, 137.2 ), 0.8, "sh_paint_yellow", 6 )
        for z in ( 128.0, 137.2 ):
            rod( model, F.p( x, posts[0], z ), F.p( x, posts[-1], z ), 0.85, "sh_paint_yellow", 6,
                 caps=( True, True ) )
        F.quad( model, "sh_signs", xs * 47.4, -150.0, zc, 13.9, 13.9, "right" if xs > 0 else "left", uv=flam )

    # the back: the valve cabinet, the ladder, the bumper with its lamps, plates and the label
    F.box( model, -36.0, 36.0, -193.0, -178.0, 23.0, 46.0, "sh_stainless" )
    F.box( model, -46.0, 46.0, -197.0, -193.0, 14.0, 23.0, BLK )
    for x in ( -34.0, -20.0 ):
        F.box( model, x - 0.7, x + 0.7, -195.6, -194.4, 24.0, top + 6.0, "sh_stainless" )
        for z in ( 64.0, 104.0 ):
            F.box( model, x - 0.5, x + 0.5, -194.4, -184.0, z, z + 1.5, "sh_stainless" )
    for z in np.arange( 30.0, top, 10.5 ):
        rod( model, F.p( -34.0, -195.0, z ), F.p( -20.0, -195.0, z ), 0.55, "sh_stainless", 5 )
    for xs in ( -1, 1 ):
        F.quad( model, "sh_paint_red", xs * 39.0, -197.05, 18.5, 11.0, 6.0, "back" )
        F.quad( model, "sh_paint_orange", xs * 31.5, -197.05, 18.5, 3.0, 6.0, "back" )
    F.quad( model, "sh_paint_yellow", 0.0, -197.05, 18.5, 20.5, 4.3, "back" )
    F.quad( model, "sh_paint_orange", 2.0, -193.05, 36.0, 15.7, 11.8, "back" )
    F.quad( model, BLK, 2.0, -193.07, 36.0, 15.0, 0.5, "back" )
    F.quad( model, "sh_signs", 24.0, -193.05, 35.0, 13.9, 13.9, "back", uv=flam )

    F.collide( model, -49.0, 49.0, 105.0, 197.0, 16.0, 124.0, METAL )
    F.collide( model, -49.0, 49.0, -197.0, 105.0, 16.0, top + 6.0, METAL )
    F.collide( model, -49.0, 49.0, 49.0, 168.0, 0.0, 16.0, METAL )
    F.collide( model, -49.0, 49.0, -135.0, -39.0, 0.0, 16.0, METAL )


# ---------------------------------------------------------------------------------------------------------------------
# Shared by the boats

def _smooth( t ):
    t = min( max( t, 0.0 ), 1.0 )
    return t * t * ( 3.0 - 2.0 * t )


def _fpoly_d( model, F, paint, pts, towards, uv=None, normals=None ):
    """ RP._fpoly with repeated points dropped (a quad closing to a point becomes a triangle; less is left out). """
    keep = []
    for k, p in enumerate( pts ):
        p = np.asarray( p, float )
        if keep and np.linalg.norm( p - keep[-1][0] ) < 1e-4:
            continue
        keep.append( ( p, None if uv is None else uv[k], None if normals is None else normals[k] ) )
    if len( keep ) > 2 and np.linalg.norm( keep[0][0] - keep[-1][0] ) < 1e-4:
        keep.pop()
    if len( keep ) < 3:
        return
    RP._fpoly( model, F, paint, [ k[0] for k in keep ], towards,
               uv=None if uv is None else [ k[1] for k in keep ],
               normals=None if normals is None else [ k[2] for k in keep ] )


def _smooth_poly( model, F, paint, pts, normals, uv=None ):
    """ A polygon in F's coordinates shaded with a ( local ) normal per point, facing their sum. """
    _fpoly_d( model, F, paint, pts, tuple( np.sum( np.asarray( normals, float ), axis=0 ) ), uv, normals )


def _annulus( model, centre, normal, r0, r1, paint, sides=8 ):
    """ A flat ring from r0 to r1 round centre facing normal (world). """
    c, nrm = np.asarray( centre, float ), _unit( normal )
    u, v = _ring_axes( nrm )
    ring = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v for k in range( sides ) ]
    for k in range( sides ):
        a, b = ring[k], ring[( k + 1 ) % sides]
        outward( model, paint, [ c + a * r0, c + b * r0, c + b * r1, c + a * r1 ], nrm )


def _curve_label( model, F, atlas, name, curve, normal_of, h, lift=0.12, pieces=8 ):
    """ An atlas entry h tall laid along a curve (local points in reading order, finely sampled, through the middle
    of the lettering's height), centred on the curve, its width h times the entry's aspect, in pieces that follow the
    curve. normal_of( p ) is the surface's outward ( local ) normal at p. """
    pts = [ np.asarray( p, float ) for p in curve ]
    s = np.concatenate( ( [ 0.0 ], np.cumsum( [ np.linalg.norm( b - a ) for a, b in zip( pts, pts[1:] ) ] ) ) )
    width = h * aspect( atlas, name )
    s0 = ( s[-1] - width ) / 2
    u0, v0, u1, v1 = _rect( atlas, name )
    at = []
    for k in range( pieces + 1 ):
        t = min( max( s0 + width * k / pieces, 0.0 ), s[-1] )
        j = min( int( np.searchsorted( s, t, side="right" ) ) - 1, len( pts ) - 2 )
        f = ( t - s[j] ) / max( s[j + 1] - s[j], 1e-9 )
        p = pts[j] + ( pts[j + 1] - pts[j] ) * f
        at.append( p + normal_of( p ) * lift )
    up = np.array( ( 0.0, 0.0, h / 2 ) )
    for k in range( pieces ):
        a, b = at[k], at[k + 1]
        ua, ub = u0 + ( u1 - u0 ) * k / pieces, u0 + ( u1 - u0 ) * ( k + 1 ) / pieces
        nrm = normal_of( ( a + b ) / 2 )
        _fpoly_d( model, F, atlas, [ a - up, b - up, b + up, a + up ], tuple( nrm ),
                  uv=[ ( ua, v0 ), ( ub, v0 ), ( ub, v1 ), ( ua, v1 ) ] )


def _bitts( model, F, x, y, z, along=( 0.0, 1.0 ), gap=13.0, r=3.2, height=15.0 ):
    """ Cast-iron double bitts on the deck at ( x, y, z ) in F: two posts on a base plate, the pair along along. """
    a = np.array( ( along[0], along[1], 0.0 ) ) / math.hypot( *along )
    side = np.array( ( -a[1], a[0], 0.0 ) )
    c = np.array( ( x, y, z ) )
    _obox( model, F, c + ( 0, 0, 0.6 ), a, side, ( gap + 2 * r + 5.0, 2 * r + 3.0, 1.6 ), IRON )
    for s in ( -1, 1 ):
        p = c + a * s * gap / 2
        rod( model, F.p( *( p + ( 0, 0, 1.2 ) ) ), F.p( *( p + ( 0, 0, height - 1.4 ) ) ), r, IRON, 8 )
        rod( model, F.p( *( p + ( 0, 0, height - 1.4 ) ) ), F.p( *( p + ( 0, 0, height ) ) ), r + 0.8, IRON, 8,
             caps=( True, True ) )


_obox = RP._obox
_world = RP._world


# ---------------------------------------------------------------------------------------------------------------------
# The puffer

# A Clyde puffer's lines in its own frame: x across (+x the port side), y forward from amidships, z up from the
# waterline. 788 over the stem and the counter, 220 in beam, drawing 78 (2 m) loaded; its deck 32 over the water
# amidships with a sheer rising 50 to the bow and 20 to the stern, under bulwarks 30 high. A flat floor and a round
# bilge, a parallel midbody, a bluff bow on a raked stem with a rounded forefoot, and a round counter stern overhanging
# the sternpost.
PF_KEEL = -78.0
PF_MID = ( -190.0, 110.0 )                      # the parallel midbody
PF_COUNTER = ( ( -10.0, -350.0 ), ( -4.0, -356.0 ), ( 4.0, -366.0 ), ( 12.0, -377.0 ), ( 20.0, -386.0 ),
               ( 28.0, -391.5 ), ( 36.0, -394.0 ) )        # ( z, y ): the counter's underside, aft from the sternpost
PF_ROWS = ( -78.0, -74.88, -68.64, -56.16, -39.0, -19.5, 0.0, 10.0, 24.0, "deck", "rail" )
PF_BOOT = 10.0                                  # the red boot-topping's top edge over the water


def _pf_rail( y ):
    a = ( y + 40.0 ) / ( 434.0 if y >= -40.0 else 354.0 )
    return 62.0 + ( 50.0 if y >= -40.0 else 20.0 ) * a * a


def _pf_deck( y ):
    return _pf_rail( y ) - 30.0


def _pf_stem( z ):
    """ The stem's y at height z: raked 14 over the rail's height, the forefoot rounded into the keel. """
    if z >= 0.0:
        return 380.0 + 14.0 * min( z, 112.0 ) / 112.0
    return 345.0 + 35.0 * math.sqrt( max( 0.0, 1.0 - ( z / PF_KEEL ) ** 2 ) )


def _pf_stern( z ):
    return float( np.interp( z, [ p[0] for p in PF_COUNTER ], [ p[1] for p in PF_COUNTER ] ) )


def _pf_mid( z ):
    """ The midship section's half-breadth at height z: a flat floor turning up round the bilge, then the sides flaring
    2 out to the rail. """
    if z <= 0.0:
        u = min( max( ( z - PF_KEEL ) / -PF_KEEL, 0.0 ), 1.0 )
        return 108.0 * ( 1.0 - ( 1.0 - u ) ** 3.2 ) ** ( 1.0 / 3.2 )
    return 108.0 + 2.0 * min( z, 112.0 ) / 112.0


def _pf_half( y, z ):
    """ The hull's half-breadth at ( y, z ): the midship section, narrowing forward to the stem (fuller higher up), and
    aft to the sternpost under the water and round the counter above it. """
    xm = _pf_mid( z )
    if y > PF_MID[1]:
        f = ( y - PF_MID[1] ) / ( _pf_stem( z ) - PF_MID[1] )
        return 0.0 if f >= 1.0 else xm * ( 1.0 - f ** ( 1.5 + ( z - PF_KEEL ) / 190.0 ) )
    if y < PF_MID[0]:
        f = ( PF_MID[0] - y ) / ( PF_MID[0] - _pf_stern( z ) )
        if f >= 1.0:
            return 0.0
        p = 1.6 + 0.4 * _smooth( ( z - PF_KEEL ) / 102.0 )
        q = 1.0 + _smooth( ( z + 4.0 ) / 28.0 )
        return xm * ( 1.0 - f ** p ) ** ( 1.0 / q )
    return xm


def _pf_normal( y, z, side=1.0 ):
    """ The hull's outward normal at ( y, z ) on the side side (+1 or -1), local. """
    h = 0.4
    dy = ( _pf_half( y + h, z ) - _pf_half( y - h, z ) ) / ( 2 * h )
    dz = ( _pf_half( y, z + h ) - _pf_half( y, z - h ) ) / ( 2 * h )
    nrm = np.array( ( side, -dy, -dz ) )
    return nrm / np.linalg.norm( nrm )


def _pf_deck_at( x, y ):
    """ The deck's height at ( x, y ): the sheer, and a camber of 4 on the centreline (less where the deck narrows). """
    z = _pf_deck( y )
    w = max( _pf_half( y, z ) - 2.5, 1e-3 )
    s = min( abs( x ) / w, 1.0 )
    return z + 4.0 * w / 105.5 * ( 1.0 - s * s )


def _pf_row( row ):
    """ One of the hull's rows round the +x side, stern to stem: a height, or "deck" or "rail" (following the sheer).
    25 points: ten round the run or counter, five along the midbody, ten round the bow. """
    height = { "deck": _pf_deck, "rail": _pf_rail }.get( row, lambda y: row )
    yf, ya = 394.0, -394.0
    for _ in range( 30 ):
        yf, ya = _pf_stem( height( yf ) ), _pf_stern( height( ya ) )
    ys = [ PF_MID[0] - ( PF_MID[0] - ya ) * math.sin( math.pi / 2 * k / 10 ) for k in range( 10, 0, -1 ) ]
    ys += [ -190.0, -115.0, -40.0, 35.0, 110.0 ]
    ys += [ PF_MID[1] + ( yf - PF_MID[1] ) * math.sin( math.pi / 2 * k / 10 ) for k in range( 1, 11 ) ]
    return [ ( 0.0 if i in ( 0, len( ys ) - 1 ) else _pf_half( y, height( y ) ), y, height( y ) )
             for i, y in enumerate( ys ) ]


def _pf_on( y, z, side, out=0.0 ):
    """ The point on the hull's side side at ( y, z ), out along its normal. """
    return np.array( ( side * _pf_half( y, z ), y, z ) ) + _pf_normal( y, z, side ) * out


def puffer( model, e, n, z_water, facing ):
    """ A Clyde puffer (a small steam coaster) afloat with its waterline at z_water, its bow towards facing and
    ( e, n ) amidships: 788 long over the stem and the round counter, 220 in beam, drawing 78. Its black hull over a
    red bottom and boot-topping, a tarred rubbing strake along the deck line, white bulwarks inside under a varnished
    rail, a planked deck. Forward: the windlass, its chains and the anchors in their hawse pipes, the bitts, a steam
    winch and the mast with its derrick topped up over the big hatch, whose tarpaulin is battened round the coaming and
    held by locking bars. Aft: the engine casing with the tall black funnel (its whistle and waste steam pipe, four
    stays) and two cowl vents, the varnished wheelhouse with its side lights and a lifebuoy, a skylight and the cabin
    stove's chimney. Rope fenders down both sides (hanging 12 out from the hull: centre it 122 off a quay's face, not
    110), portholes forward and aft, "MAIRI ROS" on both bows and across the counter. Collision: "metal": the hull up to
    the deck and the bulwarks as hull pieces, boxes for the hatch, casing, funnel, wheelhouse, mast, winch, windlass and
    skylight. Returns the deck's height amidships. """
    F = frame_for( e, n, z_water, facing )
    _grain( model, "sh_deck", "sh_pine", "sh_timber_tar", "sh_rope" )
    BLK = "sh_paint_black"
    rows = [ _pf_row( r ) for r in PF_ROWS ]
    deck, rail = rows[-2], rows[-1]
    cols = len( rail )

    def skin( paint, corners, side, inside=False ):
        pts = [ ( side * x, y, z ) for x, y, z in corners ]
        nrm = [ ( -1.0 if inside else 1.0 ) * _pf_normal( y, z, side ) for x, y, z in corners ]
        _smooth_poly( model, F, paint, pts, nrm )

    def inner( p, by=2.5 ):
        return ( max( p[0] - by, 0.0 ), p[1], p[2] )

    # the hull, red up to the boot-topping's top edge, and the inside of the bulwarks
    for side in ( 1.0, -1.0 ):
        for j in range( len( rows ) - 1 ):
            top = PF_ROWS[j + 1]
            paint = "sh_hull_red" if not isinstance( top, str ) and top <= PF_BOOT else "sh_hull_black"
            for i in range( cols - 1 ):
                skin( paint, [ rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i] ], side )
        for i in range( cols - 1 ):
            skin( "sh_paint_white", [ inner( deck[i] ), inner( deck[i + 1] ), inner( rail[i + 1] ), inner( rail[i] ) ],
                  side, inside=True )
            # the rail cap: top, outer and inner faces
            a, b = rail[i], rail[i + 1]
            ot = [ ( side * ( p[0] + 1.0 ), p[1], p[2] + 2.0 ) for p in ( a, b ) ]
            it = [ ( side * max( p[0] - 3.0, 0.0 ), p[1], p[2] + 2.0 ) for p in ( a, b ) ]
            ob = [ ( q[0], q[1], q[2] - 2.6 ) for q in ot ]
            ib = [ ( q[0], q[1], q[2] - 2.6 ) for q in it ]
            n_out = _pf_normal( ( a[1] + b[1] ) / 2, ( a[2] + b[2] ) / 2, side )
            _fpoly_d( model, F, "sh_pine", [ ot[0], ot[1], it[1], it[0] ], ( 0, 0, 1 ),
                      uv=[ ( q[0] / 128.0, q[1] / 128.0 ) for q in ( ot[0], ot[1], it[1], it[0] ) ] )
            _fpoly_d( model, F, "sh_pine", [ ob[0], ob[1], ot[1], ot[0] ], tuple( n_out ),
                      uv=[ ( q[2] / 128.0, q[1] / 128.0 ) for q in ( ob[0], ob[1], ot[1], ot[0] ) ] )
            _fpoly_d( model, F, "sh_pine", [ ib[0], ib[1], it[1], it[0] ], tuple( -n_out ),
                      uv=[ ( q[2] / 128.0, q[1] / 128.0 ) for q in ( ib[0], ib[1], it[1], it[0] ) ] )
        # the rubbing strake along the deck line, and the stem band
        tube( model, [ F.p( *_pf_on( y, z - 1.5, side, 1.7 ) ) for x, y, z in deck ], 2.2, "sh_timber_tar", 6 )
    # bulwark stanchions along the midbody
    for side in ( 1.0, -1.0 ):
        for y in np.arange( -180.0, 101.0, 40.0 ):
            x = _pf_half( y, _pf_deck( y ) ) - 2.5
            x0, x1 = sorted( ( side * x, side * ( x - 2.4 ) ) )
            F.box( model, x0, x1, y - 1.0, y + 1.0, _pf_deck( y ) - 0.5, _pf_rail( y ) - 0.3, "sh_paint_white",
                   skip=( "top", "bottom" ) )
    for z0, z1, paint in ( ( PF_KEEL, PF_BOOT, "sh_hull_red" ), ( PF_BOOT, 112.0, "sh_hull_black" ) ):
        zs = np.linspace( z0, z1, 8 )
        tube( model, [ F.p( 0.0, _pf_stem( z ) + 0.9, z ) for z in zs ], 1.6, paint, 6 )
    F.box( model, -2.5, 2.5, -350.0, 345.0, PF_KEEL - 3.0, PF_KEEL + 0.5, "sh_hull_red" )            # the keel bar
    F.box( model, -1.8, 1.8, -372.0, -351.0, -70.0, -8.0, "sh_hull_red" )                           # the rudder

    # the deck: planks fore and aft over the camber
    for i in range( cols - 1 ):
        strips = []
        for x, y, z in ( deck[i], deck[i + 1] ):
            w = max( x - 2.5, 0.0 )
            strips.append( [ ( s * w, y, z + 4.0 * w / 105.5 * ( 1 - s * s ) ) for s in ( -1.0, -0.5, 0.0, 0.5, 1.0 ) ] )
        for k in range( 4 ):
            pts = [ strips[0][k], strips[0][k + 1], strips[1][k + 1], strips[1][k] ]
            _fpoly_d( model, F, "sh_deck", pts, ( 0, 0, 1 ), uv=[ ( p[0] / 128.0, p[1] / 128.0 ) for p in pts ] )

    # the hatch: the coaming, and the tarpaulin over the hatch boards, its skirt battened down round the coaming
    hx, hy0, hy1, crown = 78.0, -150.0, 210.0, 5.0

    def coaming_top( y ):
        return _pf_deck_at( hx, y ) + 24.0

    ys = np.linspace( hy0, hy1, 7 )
    for side in ( 1.0, -1.0 ):
        for y0, y1 in zip( ys, ys[1:] ):
            _fpoly_d( model, F, BLK, [ ( side * hx, y0, _pf_deck_at( hx, y0 ) - 0.5 ),
                                      ( side * hx, y1, _pf_deck_at( hx, y1 ) - 0.5 ), ( side * hx, y1, coaming_top( y1 ) ),
                                      ( side * hx, y0, coaming_top( y0 ) ) ], ( side, 0, 0 ) )
            for x, z_lo, z_hi, paint in ( ( hx + 0.6, -13.0, 0.0, "sh_canvas" ), ( hx + 1.2, -10.0, -7.5, BLK ) ):
                c0, c1 = coaming_top( y0 ), coaming_top( y1 )
                _fpoly_d( model, F, paint, [ ( side * x, y0, c0 + z_lo ), ( side * x, y1, c1 + z_lo ),
                                             ( side * x, y1, c1 + z_hi ), ( side * x, y0, c0 + z_hi ) ], ( side, 0, 0 ) )
    xs = np.linspace( -hx, hx, 5 )
    for y, toward in ( ( hy0, -1.0 ), ( hy1, 1.0 ) ):
        top = coaming_top( y )
        for x0, x1 in zip( xs, xs[1:] ):
            _fpoly_d( model, F, BLK, [ ( x0, y, _pf_deck_at( x0, y ) - 0.5 ), ( x1, y, _pf_deck_at( x1, y ) - 0.5 ),
                                       ( x1, y, top ), ( x0, y, top ) ], ( 0, toward, 0 ) )
            s0, s1 = x0 / hx, x1 / hx
            yt = y + toward * 0.6
            _fpoly_d( model, F, "sh_canvas", [ ( x0 * 1.008, yt, top - 13.0 ), ( x1 * 1.008, yt, top - 13.0 ),
                                               ( x1 * 1.008, yt, top + crown * ( 1 - s1 * s1 ) ),
                                               ( x0 * 1.008, yt, top + crown * ( 1 - s0 * s0 ) ) ], ( 0, toward, 0 ) )
        yb = y + toward * 1.2
        _fpoly_d( model, F, BLK, [ ( -hx - 1.2, yb, top - 10.0 ), ( hx + 1.2, yb, top - 10.0 ), ( hx + 1.2, yb, top - 7.5 ),
                                   ( -hx - 1.2, yb, top - 7.5 ) ], ( 0, toward, 0 ) )
    tys = np.linspace( hy0 - 0.6, hy1 + 0.6, 7 )
    txs = [ s * ( hx + 0.6 ) for s in ( -1.0, -0.5, 0.0, 0.5, 1.0 ) ]
    for y0, y1 in zip( tys, tys[1:] ):
        for x0, x1 in zip( txs, txs[1:] ):
            pts = [ ( x, y, coaming_top( y ) + crown * ( 1 - ( x / ( hx + 0.6 ) ) ** 2 ) )
                    for x, y in ( ( x0, y0 ), ( x1, y0 ), ( x1, y1 ), ( x0, y1 ) ) ]
            _fpoly_d( model, F, "sh_canvas", pts, ( 0, 0, 1 ) )
    for y in ( -60.0, 30.0, 120.0 ):
        top = coaming_top( y )
        bar = [ ( -hx - 1.5, y, top - 6.0 ) ] + [ ( s * ( hx + 1.3 ), y, top + crown * ( 1 - s * s ) + 0.8 )
                                                  for s in ( -1.0, -0.5, 0.0, 0.5, 1.0 ) ] + [ ( hx + 1.5, y, top - 6.0 ) ]
        tube( model, [ F.p( *p ) for p in _bend_path( bar, 2.0, 3 )[0] ], 0.9, BLK, 4 )

    # the mast and derrick, topped up over the hatch; the topping lift, the cargo runner and its hook; the stays
    ym, mast_top = 232.0, 382.0
    zb = _pf_deck_at( 0.0, ym )
    RP._frustum( model, F.p( 0.0, ym, zb - 1.0 ), F.p( 0.0, ym, mast_top ), 6.0, 3.8, "sh_pine", 10 )
    disc( model, BLK, F.p( 0.0, ym, mast_top + 1.2 ), F.z, 4.6, sides=10 )

    def mast_r( z ):
        return 6.0 - 2.2 * ( z - zb ) / ( mast_top - zb )

    rod( model, F.p( 0.0, ym, mast_top - 0.2 ), F.p( 0.0, ym, mast_top + 1.2 ), 4.6, BLK, 10 )
    for z, hgt in ( ( mast_top - 18.0, 5.0 ), ( 101.0, 6.0 ), ( 340.0, 3.0 ) ):
        _band( model, F.p( 0.0, ym, z ), F.z, mast_r( z ), hgt, BLK, 10, 0.6 )
    ang = math.radians( 28.0 )
    d = np.array( ( 0.0, -math.cos( ang ), math.sin( ang ) ) )
    heel = np.array( ( 0.0, ym - mast_r( 101.0 ) - 3.5, 101.0 ) )
    head = heel + d * 312.0
    RP._frustum( model, F.p( *heel ), F.p( *head ), 4.4, 3.0, "sh_pine", 8 )
    disc( model, BLK, F.p( *heel ), -_world( F, d ), 4.4, sides=8 )
    _band( model, F.p( *( head - d * 4.0 ) ), _world( F, d ), 3.1, 7.0, BLK, 8, 0.7 )
    disc( model, BLK, F.p( *head ), _world( F, d ), 3.0, sides=8 )
    F.box( model, -2.2, 2.2, heel[1] - 1.0, ym - mast_r( 101.0 ) + 0.5, 97.0, 105.0, BLK )        # the gooseneck
    down = np.array( ( 0.0, -math.sin( ang ), -math.cos( ang ) ) )
    rod( model, F.p( *( head + ( 0, 0, 2.5 ) ) ), F.p( 0.0, ym - mast_r( 360.0 ), 362.0 ), 0.5, BLK, 4 )
    block = head + down * 4.0
    hook_y, hook_z = block[1], 124.0
    rod( model, F.p( *block ), F.p( 0.0, hook_y, hook_z + 8.0 ), 0.4, BLK, 4 )
    F.box( model, -2.0, 2.0, hook_y - 2.4, hook_y + 2.4, hook_z, hook_z + 8.0, BLK )
    tube( model, [ F.p( 0.0, hook_y, hook_z ), F.p( 0.0, hook_y, hook_z - 6.0 ), F.p( 0.0, hook_y + 1.8, hook_z - 8.4 ),
                   F.p( 0.0, hook_y + 3.8, hook_z - 7.6 ), F.p( 0.0, hook_y + 4.3, hook_z - 5.2 ) ], 0.7, "sh_steel", 5 )
    lead = heel + down * 5.5 + d * 6.0
    rod( model, F.p( *( head + down * 5.5 - d * 6.0 ) ), F.p( *lead ), 0.4, BLK, 4 )
    zw = _pf_deck_at( 0.0, 262.0 )
    rod( model, F.p( *lead ), F.p( 0.0, 262.0, zw + 22.0 ), 0.4, BLK, 4 )
    rod( model, F.p( 0.0, ym + mast_r( 360.0 ), 360.0 ), F.p( 0.0, _pf_stem( 112.0 ) - 2.0, 114.0 ), 0.45, BLK, 4 )
    for side in ( 1.0, -1.0 ):
        for y in ( ym - 12.0, ym + 14.0 ):
            x = _pf_half( y, _pf_rail( y ) )
            rod( model, F.p( 0.0, ym, 338.0 ), F.p( side * ( x - 1.0 ), y, _pf_rail( y ) + 2.0 ), 0.4, BLK, 4 )

    # the steam winch forward of the mast, the windlass and its chains on the foredeck, the anchors, the bitts
    F.box( model, -19.0, 19.0, 252.0, 272.0, zw - 1.5, zw + 3.0, "sh_steel_green" )
    for side in ( 1.0, -1.0 ):
        x0, x1 = sorted( ( side * 13.0, side * 16.0 ) )
        F.box( model, x0, x1, 254.0, 270.0, zw + 3.0, zw + 25.0, "sh_steel_green" )
        rod( model, F.p( side * 16.0, 262.0, zw + 16.0 ), F.p( side * 26.0, 262.0, zw + 16.0 ), 5.0, "sh_steel", 10,
             caps=( False, True ) )
    rod( model, F.p( -13.0, 262.0, zw + 16.0 ), F.p( 13.0, 262.0, zw + 16.0 ), 6.5, "sh_steel", 12 )
    F.box( model, -11.0, 11.0, 270.0, 280.0, zw + 3.0, zw + 19.0, "sh_steel_green" )
    rod( model, F.p( -6.0, 275.0, zw + 19.0 ), F.p( -6.0, 275.0, zw + 25.0 ), 3.0, "sh_steel_green", 8,
         caps=( False, True ) )
    yw = 325.0
    zl = _pf_deck_at( 0.0, yw )
    F.box( model, -17.0, 17.0, yw - 7.0, yw + 7.0, zl - 1.5, zl + 4.0, "sh_steel_green" )
    for side in ( 1.0, -1.0 ):
        x0, x1 = sorted( ( side * 15.0, side * 17.5 ) )
        F.box( model, x0, x1, yw - 6.0, yw + 6.0, zl + 4.0, zl + 19.0, "sh_steel_green" )
        rod( model, F.p( side * 7.5, yw, zl + 12.0 ), F.p( side * 11.5, yw, zl + 12.0 ), 7.0, "sh_steel", 12,
             caps=( True, True ) )
        hawse = ( side * 15.0, 352.0 )
        zh = _pf_deck_at( *hawse )
        tube( model, [ F.p( side * 9.5, yw + 6.0, zl + 17.0 ), F.p( side * 12.0, yw + 14.0, zl + 9.0 ),
                       F.p( hawse[0], hawse[1] - 3.0, zh + 1.5 ) ], 1.3, "sh_rust", 5 )
        disc( model, BLK, F.p( hawse[0], hawse[1], zh + 0.3 ), F.z, 4.2, sides=8 )
        # the anchor drawn up in its hawse pipe on the bow
        za = 44.0
        p0 = _pf_on( 351.0, za, side, 2.2 )
        nrm = _pf_normal( 351.0, za, side )
        along = _unit( np.cross( nrm, ( 0.0, 0.0, 1.0 ) ) )
        upd = np.cross( along, nrm )
        _obox( model, F, p0 + upd * 6.0, upd, along, ( 22.0, 3.0, 3.0 ), BLK )
        _obox( model, F, p0 - upd * 6.0 + nrm * 0.8, along, upd, ( 15.0, 9.0, 3.2 ), BLK )
        _annulus( model, F.p( *_pf_on( 351.0, za + 16.0, side, 0.2 ) ), _world( F, nrm ), 3.0, 4.6, BLK )
    rod( model, F.p( -7.5, yw, zl + 12.0 ), F.p( 7.5, yw, zl + 12.0 ), 4.0, "sh_steel", 10 )
    for x, y in ( ( 46.0, 300.0 ), ( 88.0, -172.0 ), ( 40.0, -342.0 ) ):
        for side in ( 1.0, -1.0 ):
            _bitts( model, F, side * x, y, _pf_deck_at( x, y ) - 0.3 )

    # the engine casing, the funnel raked aft with its whistle, waste steam pipe and stays, the cowl vents
    cx, cy0, cy1 = 46.0, -212.0, -162.0
    zc0 = min( _pf_deck_at( cx, cy0 ), _pf_deck_at( cx, cy1 ) ) - 1.0
    zc1 = _pf_deck_at( 0.0, -187.0 ) + 30.0
    F.box( model, -cx, cx, cy0, cy1, zc0, zc1, { "default": "sh_paint_white", "top": "sh_steel", "bottom": None } )
    rake = math.radians( 5.0 )
    fd = np.array( ( 0.0, -math.sin( rake ), math.cos( rake ) ) )
    fb, fh = np.array( ( 0.0, -186.0, zc1 - 2.0 ) ), 176.0
    revolve( model, F.p( *fb ), _world( F, fd ), [ ( 14.0, 0.0 ), ( 14.0, fh - 3.0 ), ( 15.3, fh - 3.0 ), ( 15.3, fh ),
                                                   ( 13.3, fh ), ( 13.3, fh - 9.0 ) ], BLK, 16, crease=30.0 )
    disc( model, BLK, F.p( *( fb + fd * ( fh - 9.0 ) ) ), F.z, 13.4, sides=16 )
    _band( model, F.p( *( fb + fd * 0.62 * fh ) ), _world( F, fd ), 14.0, 2.5, BLK, 16, 0.6 )
    for t0, t1, off, r, paint in ( ( 2.0, 140.0, ( 0.0, 15.6, 0.0 ), 1.1, "sh_brass" ),
                                   ( 2.0, fh + 9.0, ( 0.0, -16.6, 0.0 ), 2.4, BLK ) ):
        rod( model, F.p( *( fb + fd * t0 + off ) ), F.p( *( fb + fd * t1 + off ) ), r, paint, 8 )
    whistle = fb + fd * 140.0 + ( 0.0, 15.6, 0.0 )
    rod( model, F.p( *whistle ), F.p( *( whistle + ( 0, 0, 9.0 ) ) ), 2.3, "sh_brass", 8, caps=( True, True ) )
    sphere( model, F.p( *( whistle + ( 0, 0, 9.8 ) ) ), 1.4, "sh_brass", 6, 3 )
    for sx, sy in ( ( 1, 1 ), ( -1, 1 ), ( 1, -1 ), ( -1, -1 ) ):
        a = fb + fd * 0.62 * fh + np.array( ( sx * 10.5, sy * 10.5, 0.0 ) )
        rod( model, F.p( *a ), F.p( sx * ( cx - 4.0 ), cy1 - 4.0 if sy > 0 else cy0 + 4.0, zc1 + 0.2 ), 0.35, BLK, 4 )
    for side in ( 1.0, -1.0 ):
        x = side * 30.0
        path, _ = _bend_path( [ ( x, -168.0, zc1 - 0.5 ), ( x, -168.0, zc1 + 30.0 ), ( x, -159.0, zc1 + 30.0 ) ], 7.0, 4 )
        tube( model, [ F.p( *p ) for p in path ], 5.0, "sh_paint_white", 10 )
        mouth = np.array( ( x, -159.0, zc1 + 30.0 ) )
        RP._frustum( model, F.p( *mouth ), F.p( *( mouth + ( 0.0, 7.0, 0.0 ) ) ), 5.0, 9.5, "sh_paint_white", 12,
                     inside="sh_paint_red" )
        disc( model, "sh_paint_red", F.p( *( mouth + ( 0.0, 0.3, 0.0 ) ) ), F.y, 5.0, sides=10 )

    # the wheelhouse: varnished, windows all round, a door each side, a white roof, side lights, a lifebuoy
    wx, wy0, wy1 = 40.0, -280.0, -222.0
    wz0 = min( _pf_deck_at( wx, wy0 ), _pf_deck_at( wx, wy1 ) ) - 1.0
    wz1 = _pf_deck_at( 0.0, -251.0 ) + 84.0
    zwin = wz1 - 26.0
    F.box( model, -wx, wx, wy0, wy1, wz0, wz1, { "default": "sh_pine", "bottom": None, "top": None } )
    F.box( model, -wx - 3.0, wx + 3.0, wy0 - 3.0, wy1 + 3.0, wz1, wz1 + 3.0, "sh_paint_white" )
    for x in ( -24.0, 0.0, 24.0 ):
        F.quad( model, "sh_window_dark", x, wy1 + 0.06, zwin, 17.0, 21.0, "front" )
    for x in ( -26.0, 26.0 ):
        F.quad( model, "sh_window_dark", x, wy0 - 0.06, zwin, 14.0, 18.0, "back" )
    for side in ( 1.0, -1.0 ):
        face = "right" if side > 0 else "left"
        F.quad( model, "sh_window_dark", side * ( wx + 0.06 ), -233.0, zwin, 16.0, 21.0, face )
        x0, x1 = sorted( ( side * wx, side * ( wx + 0.7 ) ) )
        F.box( model, x0, x1, -273.0, -249.0, wz0 + 2.0, wz1 - 7.0, "sh_pine", skip=( "bottom", ) )
        F.quad( model, "sh_window_dark", side * ( wx + 0.76 ), -261.0, zwin, 14.0, 17.0, face )
        rod( model, F.p( side * ( wx + 0.7 ), -253.0, zwin - 22.0 ), F.p( side * ( wx + 2.0 ), -253.0, zwin - 22.0 ),
             0.5, "sh_brass", 5, caps=( False, True ) )
        # the side lights on boards at the roof's forward corners: red to port (+x), green to starboard
        x0, x1 = sorted( ( side * ( wx + 1.5 ), side * ( wx + 3.0 ) ) )
        F.box( model, x0, x1, wy1 - 14.0, wy1 + 2.0, wz1 + 3.0, wz1 + 13.0, BLK )
        x0, x1 = sorted( ( side * ( wx + 3.0 ), side * ( wx + 7.0 ) ) )
        F.box( model, x0, x1, wy1 - 2.0, wy1 + 2.5, wz1 + 5.0, wz1 + 11.0,
               "sh_paint_red" if side > 0 else "sh_paint_door" )
    c = np.array( ( 0.0, wy0 - 3.1, wz1 - 33.0 ) )
    for q in range( 4 ):
        arc = [ F.p( *( c + ( 12.0 * math.cos( a ), 0.0, 12.0 * math.sin( a ) ) ) )
                for a in np.linspace( q * math.pi / 2, ( q + 1 ) * math.pi / 2, 4 ) ]
        tube( model, arc, 2.5, "sh_paint_red" if q % 2 == 0 else "sh_paint_white", 6 )
    # the skylight over the cabin aft and the stove's chimney
    zs = _pf_deck_at( 0.0, -305.0 )
    F.box( model, -13.0, 13.0, -316.0, -294.0, zs - 2.0, zs + 9.0, { "default": "sh_pine", "bottom": None, "top": None } )
    for side in ( 1.0, -1.0 ):
        _fpoly_d( model, F, "sh_window_dark", [ ( side * 13.0, -316.0, zs + 9.0 ), ( side * 13.0, -294.0, zs + 9.0 ),
                                                ( 0.0, -294.0, zs + 15.0 ), ( 0.0, -316.0, zs + 15.0 ) ],
                  ( side * 6.0, 0.0, 13.0 ) )
    for y, toward in ( ( -316.0, -1.0 ), ( -294.0, 1.0 ) ):
        _fpoly_d( model, F, "sh_pine", [ ( -13.0, y, zs + 9.0 ), ( 13.0, y, zs + 9.0 ), ( 0.0, y, zs + 15.0 ) ],
                  ( 0.0, toward, 0.0 ) )
    rod( model, F.p( 26.0, -300.0, zs - 1.0 ), F.p( 26.0, -300.0, zs + 30.0 ), 2.0, BLK, 8 )
    rod( model, F.p( 26.0, -300.0, zs + 31.5 ), F.p( 26.0, -300.0, zs + 32.5 ), 3.8, BLK, 8, caps=( True, True ) )

    # rope fenders down both sides, portholes forward and aft
    fender = [ ( 0.0, -12.0 ), ( 4.2, -10.5 ), ( 6.0, -6.5 ), ( 6.0, 6.5 ), ( 4.2, 10.5 ), ( 0.0, 12.0 ) ]
    for side in ( 1.0, -1.0 ):
        for y in ( 150.0, -40.0, -225.0 ):
            zf = 27.0
            c = _pf_on( y, zf, side, 6.3 )
            revolve( model, F.p( *c ), F.z, fender, "sh_rope", 8 )
            xr = _pf_half( y, _pf_rail( y ) )
            zr = _pf_rail( y ) + 2.6
            tube( model, [ F.p( *( c + ( 0, 0, 11.5 ) ) ), F.p( side * ( xr + 1.6 ), y, zr ), F.p( side * ( xr - 3.4 ), y, zr ),
                           F.p( side * ( xr - 3.4 ), y, zr - 7.0 ) ], 0.55, "sh_rope", 4 )
        for y in ( 292.0, 316.0, -296.0, -320.0 ):
            z = _pf_deck( y ) - ( 13.0 if y > 0 else 12.0 )
            nrm = _world( F, _pf_normal( y, z, side ) )
            p = F.p( *_pf_on( y, z, side, 0.25 ) )
            disc( model, "sh_window_dark", p, nrm, 3.6, sides=8 )
            _annulus( model, p, nrm, 3.6, 5.4, "sh_brass", 8 )

    # her name on both bows and across the counter
    for side in ( 1.0, -1.0 ):
        curve = [ _pf_on( y, _pf_deck( y ) + 15.0, side ) for y in np.arange( 230.0, 371.0, 2.0 ) ]
        if side > 0:
            curve.reverse()                                         # the port side reads from the bow aft
        _curve_label( model, F, "sh_lettering", "boat_mairi_ros", curve,
                      lambda p, s=side: _pf_normal( p[1], p[2], s ), 14.0 )
    zn = 62.0
    stern = [ _pf_on( y, zn, 1.0 ) for y in np.linspace( -330.0, _pf_stern( zn ) + 0.01, 40 ) ]
    curve = stern + [ p * ( -1.0, 1.0, 1.0 ) for p in reversed( stern ) ]
    _curve_label( model, F, "sh_lettering", "boat_mairi_ros", curve,
                  lambda p: _pf_normal( p[1], p[2], 1.0 if p[0] >= 0 else -1.0 ), 9.0, pieces=10 )

    # collision: the hull up to the deck and the bulwarks, as convex pieces; boxes for the rest
    groups = [ ( 0, 2 ), ( 2, 4 ), ( 4, 6 ), ( 6, 8 ), ( 8, 10 ), ( 10, 14 ), ( 14, 16 ), ( 16, 18 ), ( 18, 20 ),
               ( 20, 22 ), ( 22, 24 ) ]
    for i0, i1 in groups:
        pts = []
        for i in range( i0, i1 + 1 ):
            for row in rows[:-1]:
                x, y, z = row[i]
                pts += [ ( x, y, z ), ( -x, y, z ) ]
            x, y, z = deck[i]
            pts.append( ( 0.0, y, z + 4.0 * max( x - 2.5, 0.0 ) / 105.5 ) )
        model.hull( [ F.p( *p ) for p in pts ], METAL )
        for side in ( 1.0, -1.0 ):
            pts = []
            for i in range( i0, i1 + 1 ):
                for p in ( deck[i], rail[i] ):
                    lift = 2.0 if p is rail[i] else 0.0
                    pts += [ ( side * ( p[0] + 1.0 ), p[1], p[2] + lift ),
                             ( side * max( p[0] - 3.0, 0.0 ), p[1], p[2] + lift ) ]
            model.hull( [ F.p( *p ) for p in pts ], METAL )
    for y0, y1 in ( ( hy0 - 1.0, -30.0 ), ( -30.0, 90.0 ), ( 90.0, hy1 + 1.0 ) ):
        F.collide( model, -hx - 1.5, hx + 1.5, y0, y1, _pf_deck( y0 ),
                   max( coaming_top( y0 ), coaming_top( y1 ) ) + crown, METAL )
    F.collide( model, -cx, cx, cy0, cy1, zc0, zc1, METAL )
    F.collide( model, -15.5, 15.5, -216.0, -170.0, zc1, zc1 + fh, METAL )
    F.collide( model, -wx - 3.0, wx + 3.0, wy0 - 3.0, wy1 + 3.0, wz0, wz1 + 3.0, METAL )
    F.collide( model, -6.0, 6.0, ym - 6.0, ym + 6.0, zb, mast_top, METAL )
    F.collide( model, -19.0, 19.0, 252.0, 280.0, zw - 1.5, zw + 25.0, METAL )
    F.collide( model, -17.5, 17.5, yw - 7.0, yw + 7.0, zl - 1.5, zl + 19.0, METAL )
    F.collide( model, -13.0, 13.0, -316.0, -294.0, zs - 2.0, zs + 15.0, METAL )
    return z_water + _pf_deck_at( 0.0, 0.0 )


# ---------------------------------------------------------------------------------------------------------------------
# Creels

CREEL = ( 26.0, 20.0, 15.0 )            # a bow creel's length, width and height (660 x 510 x 380 mm)


def _creel( model, C ):
    """ One bow creel in its own frame C (the middle of its base at the origin, its length along y): a base frame of
    black rubber-sleeved bar with a runner down the middle, three bows across it, netting over the bows, the two ends
    and the floor, and an entrance ring ("eye") in each side with its netting funnel leading in. """
    L, W, H = CREEL
    hl, hw, r = L / 2 - 0.6, W / 2 - 0.6, 0.55
    for x0, y0, x1, y1 in ( ( -hw, -hl, hw, -hl ), ( -hw, hl, hw, hl ), ( -hw, -hl, -hw, hl ), ( hw, -hl, hw, hl ),
                            ( 0.0, -hl, 0.0, hl ) ):
        rod( model, C.p( x0, y0, r ), C.p( x1, y1, r ), r, "sh_rubber", 4 )
    steps, top = 6, H - 2 * r
    arc = [ ( hw * math.cos( math.pi * k / steps ), r + top * math.sin( math.pi * k / steps ) )
            for k in range( steps + 1 ) ]
    bows = ( -hl, 0.0, hl )
    for y in bows:
        tube( model, [ C.p( x, y, z ) for x, z in arc ], 0.45, "sh_rubber", 3 )
    # the netting, both sides of it (it's see-through)
    for ya, yb in zip( bows, bows[1:] ):
        for ( xa, za ), ( xb, zb ) in zip( arc, arc[1:] ):
            model.polygon( "sh_net", [ C.p( xa, ya, za ), C.p( xb, ya, zb ), C.p( xb, yb, zb ), C.p( xa, yb, za ) ],
                           both_sides=True )
    for y in ( -hl, hl ):
        model.polygon( "sh_net", [ C.p( x, y, z ) for x, z in arc ], both_sides=True )
    model.polygon( "sh_net", [ C.p( -hw, -hl, r ), C.p( hw, -hl, r ), C.p( hw, hl, r ), C.p( -hw, hl, r ) ],
                   both_sides=True )
    # the eyes, one each side in alternate bays, their funnels running in towards the middle
    for s in ( 1.0, -1.0 ):
        t = math.radians( 40.0 )
        p = np.array( ( s * hw * math.cos( t ), s * hl / 2, r + top * math.sin( t ) ) )
        nrm = _unit( ( s * math.cos( t ) / hw, 0.0, math.sin( t ) / top ) )
        c = C.p( *( p + nrm * 0.2 ) )
        _annulus( model, c, _world( C, nrm ), 2.4, 3.1, "sh_rubber", 6 )
        inner = p - nrm * 6.0 - np.array( ( 0.0, 0.0, 1.5 ) )
        RP._frustum( model, C.p( *p ), C.p( *inner ), 2.4, 1.1, "sh_net", 5, inside="sh_net" )


def creels( model, e, n, z0, count=6, axis="n", collide=True ):
    """ Bow creels (lobster pots) stacked loaf on loaf up to three high, their lengths along axis ("n" or "e") and the
    stacks end to end along it, each creel a little askew; ( e, n ) is the stacks' middle. Collision (with collide):
    one box round them, "plastic". Returns the top of the highest stack. """
    L, W, H = CREEL
    cols = max( 1, math.ceil( count / 3 ) )
    heights = [ count // cols + ( 1 if k < count % cols else 0 ) for k in range( cols ) ]
    F = frame_for( e, n, z0, "+n" if axis == "n" else "+e" )
    pitch, rise = L + 1.5, H - 0.4
    for k, high in enumerate( heights ):
        y = ( k - ( cols - 1 ) / 2 ) * pitch
        for level in range( high ):
            key = ( "creel", e, n, z0, k, level )
            yaw = math.radians( between( -5.0, 5.0, *key, "yaw" ) )
            C = RP.Frame( F.p( between( -1.2, 1.2, *key, "x" ), y + between( -1.0, 1.0, *key, "y" ), level * rise ),
                          math.cos( yaw ) * F.y + math.sin( yaw ) * F.x )
            _creel( model, C )
    top = max( heights ) * rise + 0.4
    if collide:
        F.collide( model, -W / 2 - 1.5, W / 2 + 1.5, -cols * pitch / 2, cols * pitch / 2, 0.0, top, "plastic" )
    return z0 + top


# ---------------------------------------------------------------------------------------------------------------------
# The creel boat

# A 7 m creel (lobster) boat's lines in its own frame: x across (+x the port side), y forward from amidships, z up from
# the waterline. 276 over the stem and the transom, 104 in beam (2.65 m), drawing 22 at the hull and 31 at the skeg. A
# fine bow on a raked stem with a rounded forefoot and flared topsides, a round bilge easing aft into a shallow vee,
# the bottom rising to a broad transom just in the water, a skeg running aft to guard the propeller and carry the
# rudder's heel; the sheer rises 14 to the stem and 4 to the transom over 30 amidships. The working deck is 6 over the
# water aft (freeing ports drain it), the cuddy is under the foredeck and the wheelhouse over the cuddy's after end.
CB_ROWS = ( -22.0, -21.0, -18.0, -13.0, -7.0, -6.0, -2.0, 1.0, 4.0, "s24", "s17", "sheer" )
CB_DECK = 6.0                   # the working deck over the water
CB_CUDDY = 62.0                 # the cuddy's after bulkhead: the wheelhouse front stands on it
CB_FORE = 6.0                   # the foredeck under the sheer (at its edge)
CB_LETTERS = 12.6               # the number's atlas entry: its figures 25 cm tall, the least on a 5-12 m boat


def _cb_sheer( y ):
    a = ( y + 20.0 ) / ( 158.0 if y >= -20.0 else 110.0 )
    return 30.0 + ( 14.0 if y >= -20.0 else 4.0 ) * a * a


def _cb_stem( z ):
    """ The stem's y at height z: raked 12 over the sheer's height, the forefoot rounded into the keel. """
    if z >= 0.0:
        return 126.0 + 12.0 * min( z, 44.0 ) / 44.0
    return 92.0 + 34.0 * math.sqrt( max( 0.0, 1.0 - ( z / 22.0 ) ** 2 ) )


def _cb_transom( z ):
    """ The transom's y at height z: its foot at -6 under the water, raked 8 aft at the sheer. """
    return -130.0 - 8.0 * ( z + 6.0 ) / 40.0


def _cb_bottom( y ):
    """ The keel line: level under the forebody, rising aft to the transom's foot. """
    if y >= -40.0:
        return -22.0
    return -22.0 + 16.0 * ( ( -40.0 - y ) / 90.0 ) ** 2


def _cb_section( z, bottom=-22.0, breadth=52.0, top=30.0 ):
    """ A section's half-breadth at height z: a vee (about 20 degrees of deadrise amidships) turning up round the bilge
    to upright topsides at top, flaring a little over 30. """
    u = min( max( ( z - bottom ) / ( top - bottom ), 0.0 ), 1.0 )
    return breadth * ( 1.0 - ( 1.0 - u ) ** 3 ) + max( 0.0, z - 30.0 ) * 0.07


def _cb_half( y, z ):
    """ The hull's half-breadth at ( y, z ): the midship section; aft its floor rises, its bilge turns lower down and
    it narrows a little, to a broad transom (84 across at the deck) over a shallow vee; forward it fines to the stem
    (fuller higher up, so the bow flares). """
    if y < -40.0:
        a = ( ( -40.0 - y ) / 90.0 ) ** 2
        return _cb_section( z, -22.0 + 16.0 * a, 52.0 * ( 1.0 - 0.16 * a ), 30.0 - 18.0 * a )
    xm = _cb_section( z )
    if y > 20.0:
        f = ( y - 20.0 ) / ( _cb_stem( z ) - 20.0 )
        if f >= 1.0:
            return 0.0
        return xm * ( 1.0 - f ** ( 1.2 + 1.4 * ( max( z + 22.0, 0.0 ) / 66.0 ) ** 1.5 ) )
    return xm


def _cb_normal( y, z, side=1.0 ):
    """ The hull's outward normal at ( y, z ) on the side side (+1 or -1), local. """
    h = 0.3
    dy = ( _cb_half( y + h, z ) - _cb_half( y - h, z ) ) / ( 2 * h )
    dz = ( _cb_half( y, z + h ) - _cb_half( y, z - h ) ) / ( 2 * h )
    nrm = np.array( ( side, -dy, -dz ) )
    return nrm / np.linalg.norm( nrm )


def _cb_on( y, z, side, out=0.0 ):
    """ The point on the hull's side side at ( y, z ), out along its normal. """
    return np.array( ( side * _cb_half( y, z ), y, z ) ) + _cb_normal( y, z, side ) * out


def _cb_level( row ):
    """ A row's height along the hull: a number, "sheer", or "s<d>" (d under the sheer). """
    if row == "sheer":
        return _cb_sheer
    if isinstance( row, str ):
        d = float( row[1:] )
        return lambda y: _cb_sheer( y ) - d
    return lambda y: row


def _cb_row( row ):
    """ One of the hull's rows round the +x side, aft to the stem: 23 points, ten round the run (from the transom, or
    from where the rising bottom meets a low row), three along the middle and ten round the bow. """
    height = _cb_level( row )
    ya, yf = -134.0, 134.0
    for _ in range( 30 ):
        ya, yf = _cb_transom( height( ya ) ), _cb_stem( height( yf ) )
    if not isinstance( row, str ) and row < -6.0:
        ya = -40.0 - 90.0 * math.sqrt( ( row + 22.0 ) / 16.0 )
    ys = [ -40.0 - ( -40.0 - ya ) * math.sin( math.pi / 2 * k / 10 ) for k in range( 10, 0, -1 ) ]
    ys += [ -40.0, -10.0, 20.0 ]
    ys += [ 20.0 + ( yf - 20.0 ) * math.sin( math.pi / 2 * k / 10 ) for k in range( 1, 11 ) ]
    return [ ( 0.0 if k == len( ys ) - 1 else _cb_half( y, height( y ) ), y, height( y ) ) for k, y in enumerate( ys ) ]


def _cb_paints( paint ):
    """ The hull's paint up to each row: antifouling to 1 over the water (red, or black under red topsides), a boot-top
    to 4, the topsides, and a band under the sheer that carries the number (blue on a white hull, so the white figures
    show). """
    white = paint == "sh_hull_white"
    boot, band = ( "sh_hull_blue", "sh_hull_blue" ) if white else ( "sh_hull_white", paint )
    antifouling = _cb_antifouling( paint )

    def of( top ):
        if top == "sheer":
            return band
        if isinstance( top, str ):
            return paint
        return antifouling if top <= 1.0 else boot if top <= 4.0 else paint
    return of


def _cb_antifouling( paint ):
    return "sh_hull_black" if paint == "sh_hull_red" else "sh_hull_red"


def _cb_keel( y ):
    """ The skeg's underside at y (it ends at the forefoot, y 92). """
    return float( np.interp( y, [ -127.0, -100.0, -40.0, 40.0, 92.0 ], [ -31.2, -31.0, -30.3, -29.3, -20.0 ] ) )


def _cb_keel_line( y ):
    """ The hull's lowest point at y (on the centreline): the rising run aft, level, round the forefoot, up the stem. """
    if y < -40.0:
        return _cb_bottom( y )
    if y <= 92.0:
        return -22.0
    if y <= 126.0:
        return -22.0 * math.sqrt( max( 0.0, 1.0 - ( ( y - 92.0 ) / 34.0 ) ** 2 ) )
    return ( y - 126.0 ) * 44.0 / 12.0


def _cb_in( y, z ):
    """ The inside of the hull's 2.5 skin (the bulwarks' inner face) at ( y, z ). """
    return max( _cb_half( y, z ) - 2.5, 0.0 )


def _cb_fore( y ):
    """ The foredeck's height at its edge. """
    return _cb_sheer( y ) - CB_FORE


def _cb_camber( x, w ):
    """ The foredeck's crown over its edge at x, w being its half-breadth there: 2 at the middle of a 48 half-breadth. """
    if w <= 1e-6:
        return 0.0
    return 2.0 * ( 1.0 - ( x / w ) ** 2 ) * w / 48.0


def _cb_tip( level ):
    """ The y forward of which the inside at height level( y ) has closed to nothing. """
    lo, hi = 60.0, 140.0
    for _ in range( 40 ):
        mid = ( lo + hi ) / 2
        if _cb_in( mid, level( mid ) ) > 0.0:
            lo = mid
        else:
            hi = mid
    return lo


def _cb_cleat( model, F, x, y, z, along=( 0.0, 1.0, 0.0 ) ):
    """ A stainless horn cleat 8 long on a flat top at ( x, y, z ), its horns along along. """
    a = np.asarray( along, float )
    c = np.array( ( x, y, z ) )
    for s in ( -1.0, 1.0 ):
        rod( model, F.p( *( c + a * s * 1.6 ) ), F.p( *( c + a * s * 1.6 + ( 0, 0, 1.4 ) ) ), 0.55, "sh_stainless", 5 )
    rod( model, F.p( *( c - a * 4.0 + ( 0, 0, 1.6 ) ) ), F.p( *( c + a * 4.0 + ( 0, 0, 1.6 ) ) ), 0.6, "sh_stainless", 5,
         caps=( True, True ) )


def _cb_number( model, F, entry, side, h=CB_LETTERS, pieces=10 ):
    """ The port number (an sh_lettering entry) on one bow, h tall on the band under the sheer: centred along it, its
    pieces following the hull's flare up and down as well as its curve, reading from the bow aft on the port side. """
    def zc( y ):
        return _cb_sheer( y ) - 10.5

    ys = np.arange( 56.0, 121.0, 1.0 )
    mid = [ _cb_on( y, zc( y ), side ) for y in ys ]
    s = np.concatenate( ( [ 0.0 ], np.cumsum( [ np.linalg.norm( b - a ) for a, b in zip( mid, mid[1:] ) ] ) ) )
    width = h * aspect( "sh_lettering", entry )
    s0 = ( s[-1] - width ) / 2
    u0, v0, u1, v1 = _rect( "sh_lettering", entry )
    yk = [ float( np.interp( s0 + width * k / pieces, s, ys ) ) for k in range( pieces + 1 ) ]
    if side > 0:
        yk.reverse()
    for k in range( pieces ):
        ua, ub = u0 + ( u1 - u0 ) * k / pieces, u0 + ( u1 - u0 ) * ( k + 1 ) / pieces
        corners = [ ( yk[k], -h / 2 ), ( yk[k + 1], -h / 2 ), ( yk[k + 1], h / 2 ), ( yk[k], h / 2 ) ]
        _smooth_poly( model, F, "sh_lettering", [ _cb_on( y, zc( y ) + dz, side, 0.12 ) for y, dz in corners ],
                      [ _cb_normal( y, zc( y ) + dz, side ) for y, dz in corners ],
                      uv=[ ( ua, v0 ), ( ub, v0 ), ( ub, v1 ), ( ua, v1 ) ] )


def creel_boat( model, e, n, z0, facing, paint="sh_hull_blue", trailer=True, number=None, afloat=False ):
    """ A 7 m creel (lobster) boat, 276 over the stem and the transom and 104 in beam, its bow towards facing and
    ( e, n ) amidships. A carvel wooden hull painted paint over antifouling (red; black under a red hull) and a
    boot-top, with a band under the sheer that carries its port number on both bows ("CR 47" on a blue hull, "CR 112" on
    any other, or number: an sh_lettering entry or its text), a varnished gunwale, a black rubbing strake and a
    stainless stem band; a skeg with the propeller and rudder. Forward, the white wheelhouse over the cuddy, with its
    radar dome, mast and lights, aerials, deck lights, exhaust and lifebuoy; aft, the working deck: the pot hauler on
    the starboard side under its davit, the landing table, four creels, buoys and a dahn. trailer: on a braked twin-axle
    road trailer (z0 the road); else on keel blocks and shores (z0 the ground); afloat: in the water (z0 the waterline)
    with fenders out. Collision: "wood": the hull as convex pieces, the bulwarks as slabs, a box for the wheelhouse (on
    blocks, a box each); the trailer's frame, wheels and drawbar "metal" boxes. Returns the working deck's height. """
    zw = z0 if afloat else z0 + ( 56.0 if trailer else 46.0 )
    F = frame_for( e, n, zw, facing )
    _grain( model, "sh_deck", "sh_pine", "sh_rope", "sh_planks_grey" )
    WH, BLK, RED, SS = "sh_paint_white", "sh_paint_black", _cb_antifouling( paint ), "sh_stainless"
    of = _cb_paints( paint )
    rows = [ _cb_row( r ) for r in CB_ROWS ]
    cols = len( rows[0] )
    sheer = rows[-1]

    # the hull, both sides
    for side in ( 1.0, -1.0 ):
        for j in range( len( rows ) - 1 ):
            pj = of( CB_ROWS[j + 1] )
            for i in range( cols - 1 ):
                corners = [ rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i] ]
                _smooth_poly( model, F, pj, [ ( side * x, y, z ) for x, y, z in corners ],
                              [ _cb_normal( y, z, side ) for x, y, z in corners ] )
    # the transom, from its foot under the water to the sheer
    for j in range( CB_ROWS.index( -6.0 ), len( rows ) - 1 ):
        a, b = rows[j][0], rows[j + 1][0]
        _fpoly_d( model, F, of( CB_ROWS[j + 1] ), [ a, ( -a[0], a[1], a[2] ), ( -b[0], b[1], b[2] ), b ], ( 0, -1, 0.2 ) )
    # the keel and the skeg's deadwood, the shoe under the propeller, the propeller, the rudder, the stem band
    RP._side_prism( model, F, [ ( 92.0, -20.0 ), ( -40.0, -20.0 ), ( -40.0, -30.3 ), ( 40.0, -29.3 ) ], -2.0, 2.0,
                    lambda k: None if k < 2 else RED, RED )
    RP._side_prism( model, F, [ ( -40.0, -20.0 ), ( -100.0, -12.9 ), ( -100.0, -31.0 ), ( -40.0, -30.3 ) ], -2.0, 2.0,
                    lambda k: None if k in ( 0, 3 ) else RED, RED )
    F.box( model, -1.5, 1.5, -127.0, -100.0, -31.2, -29.2, RED )
    rod( model, F.p( 0.0, -100.0, -21.0 ), F.p( 0.0, -104.0, -21.0 ), 0.8, SS, 6 )
    rod( model, F.p( 0.0, -104.0, -21.0 ), F.p( 0.0, -108.5, -21.0 ), 1.6, "sh_brass", 8, caps=( True, True ) )
    hub = np.array( ( 0.0, -106.2, -21.0 ) )
    for k in range( 3 ):
        ang = 0.4 + 2 * math.pi * k / 3
        radial = np.array( ( math.cos( ang ), 0.0, math.sin( ang ) ) )
        tangent = np.array( ( -math.sin( ang ), 0.0, math.cos( ang ) ) )
        chord = math.cos( math.radians( 25.0 ) ) * tangent + math.sin( math.radians( 25.0 ) ) * np.array( ( 0, 1.0, 0 ) )
        blade = [ hub + radial * r + chord * c for r, c in ( ( 1.4, -2.0 ), ( 1.4, 2.0 ), ( 5.0, 2.4 ), ( 6.4, 0.8 ),
                                                              ( 6.1, -1.5 ) ) ]
        model.polygon( "sh_brass", [ F.p( *p ) for p in blade ], both_sides=True )
    RP._side_prism( model, F, [ ( -110.0, -28.5 ), ( -110.0, -12.2 ), ( -125.5, -7.3 ), ( -125.5, -28.5 ) ], -1.4, 1.4,
                    lambda k: None if k == 1 else RED, RED )
    tube( model, [ F.p( 0.0, _cb_stem( z ) + 0.7, z ) for z in np.linspace( -4.0, 44.0, 9 ) ], 1.0, SS, 4 )

    # inside: the bulwarks (white) round the working deck, from the transom's inner face forward to the cuddy
    ztop = _cb_sheer( -135.6 )
    for _ in range( 20 ):
        ztop = _cb_sheer( _cb_transom( ztop ) + 2.5 )

    def aft_inner( z ):
        y = _cb_transom( z ) + 2.5
        return ( _cb_in( y, z ), y, z )

    def levels( y ):
        return ( CB_DECK, ( CB_DECK + _cb_sheer( y ) ) / 2, _cb_sheer( y ) )

    aft = [ aft_inner( z ) for z in ( CB_DECK, ( CB_DECK + ztop ) / 2, ztop ) ]
    stations = [ aft ] + [ [ ( _cb_in( y, z ), y, z ) for z in levels( y ) ]
                           for y in ( -120.0, -105.0, -85.0, -60.0, -40.0, -10.0, 20.0, 40.0, CB_CUDDY ) ]
    for side in ( 1.0, -1.0 ):
        for sa, sb in zip( stations, stations[1:] ):
            for k in range( 2 ):
                corners = [ sa[k], sb[k], sb[k + 1], sa[k + 1] ]
                _smooth_poly( model, F, WH, [ ( side * x, y, z ) for x, y, z in corners ],
                              [ -_cb_normal( y, z, side ) for x, y, z in corners ] )
    _fpoly_d( model, F, WH, [ aft[0], aft[1], aft[2], ( -aft[2][0], aft[2][1], aft[2][2] ),
                              ( -aft[1][0], aft[1][1], aft[1][2] ), ( -aft[0][0], aft[0][1], aft[0][2] ) ], ( 0, 1, 0 ) )
    # the working deck, planked fore and aft
    for sa, sb in zip( stations, stations[1:] ):
        pts = [ ( -sa[0][0], sa[0][1], CB_DECK ), ( sa[0][0], sa[0][1], CB_DECK ), ( sb[0][0], sb[0][1], CB_DECK ),
                ( -sb[0][0], sb[0][1], CB_DECK ) ]
        _fpoly_d( model, F, "sh_deck", pts, ( 0, 0, 1 ), uv=[ ( p[0] / 128.0, p[1] / 128.0 ) for p in pts ] )
    # the foredeck over the cuddy, cambered, and the low bulwarks round it
    y_tip = _cb_tip( _cb_fore )
    y_tip2 = _cb_tip( _cb_sheer )
    fys = [ CB_CUDDY + ( y_tip - CB_CUDDY ) * math.sin( math.pi / 2 * k / 8 ) for k in range( 9 ) ]
    strips = []
    for y in fys:
        w = _cb_in( y, _cb_fore( y ) )
        strips.append( [ ( s * w, y, _cb_fore( y ) + _cb_camber( s * w, w ) ) for s in ( -1.0, -0.5, 0.0, 0.5, 1.0 ) ] )
    for sa, sb in zip( strips, strips[1:] ):
        for k in range( 4 ):
            pts = [ sa[k], sa[k + 1], sb[k + 1], sb[k] ]
            _fpoly_d( model, F, "sh_deck", pts, ( 0, 0, 1 ), uv=[ ( p[0] / 128.0, p[1] / 128.0 ) for p in pts ] )
    fwd = [ [ ( _cb_in( y, z ), y, z ) for z in ( _cb_fore( y ), _cb_sheer( y ) ) ]
            for y in fys + [ ( 2 * y_tip + y_tip2 ) / 3, ( y_tip + 2 * y_tip2 ) / 3, y_tip2 ] ]
    for side in ( 1.0, -1.0 ):
        for sa, sb in zip( fwd, fwd[1:] ):
            corners = [ sa[0], sb[0], sb[1], sa[1] ]
            _smooth_poly( model, F, WH, [ ( side * x, y, z ) for x, y, z in corners ],
                          [ -_cb_normal( y, z, side ) for x, y, z in corners ] )
        # the cuddy's after bulkhead beside the wheelhouse: the step up from the working deck to the foredeck
        w = _cb_in( CB_CUDDY, _cb_fore( CB_CUDDY ) )
        _fpoly_d( model, F, WH, [ ( side * 31.0, CB_CUDDY, CB_DECK ), ( side * _cb_in( CB_CUDDY, CB_DECK ), CB_CUDDY, CB_DECK ),
                                  ( side * w, CB_CUDDY, _cb_fore( CB_CUDDY ) ),
                                  ( side * 31.0, CB_CUDDY, _cb_fore( CB_CUDDY ) + _cb_camber( 31.0, w ) ) ], ( 0, -1, 0 ) )

    # the varnished gunwale capping the sheer and the transom, the rubbing strake, the freeing ports
    for side in ( 1.0, -1.0 ):
        for a, b in zip( sheer, sheer[1:] ):
            ot = [ ( side * ( p[0] + 0.5 ), p[1], p[2] + 1.5 ) for p in ( a, b ) ]
            it = [ ( side * max( p[0] - 3.0, 0.0 ), p[1], p[2] + 1.5 ) for p in ( a, b ) ]
            ob = [ ( q[0], q[1], q[2] - 2.0 ) for q in ot ]
            ib = [ ( q[0], q[1], q[2] - 2.0 ) for q in it ]
            n_out = _cb_normal( ( a[1] + b[1] ) / 2, ( a[2] + b[2] ) / 2, side )
            _fpoly_d( model, F, "sh_pine", [ ot[0], ot[1], it[1], it[0] ], ( 0, 0, 1 ),
                      uv=[ ( q[0] / 128.0, q[1] / 128.0 ) for q in ( ot[0], ot[1], it[1], it[0] ) ] )
            _fpoly_d( model, F, "sh_pine", [ ob[0], ob[1], ot[1], ot[0] ], tuple( n_out ),
                      uv=[ ( q[2] / 128.0, q[1] / 128.0 ) for q in ( ob[0], ob[1], ot[1], ot[0] ) ] )
            _fpoly_d( model, F, "sh_pine", [ ib[0], ib[1], it[1], it[0] ], tuple( -n_out ),
                      uv=[ ( q[2] / 128.0, q[1] / 128.0 ) for q in ( ib[0], ib[1], it[1], it[0] ) ] )
    xt, yt, zt = sheer[0]
    F.box( model, -xt - 0.5, xt + 0.5, yt - 0.5, yt + 3.0, zt - 0.5, zt + 1.5, "sh_pine" )
    zc = zt - 2.5
    yc = _cb_transom( zc )
    xc = _cb_half( yc, zc )

    def strake_side( side ):
        return [ _cb_on( p[1], _cb_sheer( p[1] ) - 2.5, side, 1.4 ) for p in sheer[1:-1] ]

    def corner( a, b, c ):
        return _bend_path( [ a, b, c ], 3.0, 3 )[0][1:-1]

    stem = np.array( ( 0.0, _cb_stem( _cb_sheer( 138.0 ) - 2.5 ) + 1.4, _cb_sheer( 138.0 ) - 2.5 ) )
    port, stbd = strake_side( 1.0 ), strake_side( -1.0 )
    pc, sc = np.array( ( xc + 1.4, yc - 1.4, zc ) ), np.array( ( -xc - 1.4, yc - 1.4, zc ) )
    loop = [ stem ] + port[::-1] + corner( port[0], pc, sc ) + corner( pc, sc, stbd[0] ) + stbd + [ stem ]
    tube( model, [ F.p( *p ) for p in loop ], 1.8, "sh_rubber", 4 )
    for side in ( 1.0, -1.0 ):
        for y in ( -110.0, -75.0, -40.0, -5.0 ):
            corners = [ ( y - 4.0, 6.5 ), ( y + 4.0, 6.5 ), ( y + 4.0, 9.5 ), ( y - 4.0, 9.5 ) ]
            _smooth_poly( model, F, BLK, [ _cb_on( yy, zz, side, 0.1 ) for yy, zz in corners ],
                          [ _cb_normal( yy, zz, side ) for yy, zz in corners ] )

    # the wheelhouse: its front raked forward (against the glare) on the cuddy's after end, a door aft
    wx, wy0, wy1, wz1 = 31.0, 10.0, CB_CUDDY, 82.0
    zfw = _cb_fore( wy1 )

    def front_y( z ):
        return wy1 + 4.0 * ( z - zfw ) / ( wz1 - zfw )

    fn = _unit( ( 0.0, wz1 - zfw, -4.0 ) )
    for side in ( 1.0, -1.0 ):
        x = side * wx
        _fpoly_d( model, F, WH, [ ( x, wy0, CB_DECK ), ( x, wy1, CB_DECK ), ( x, wy1, zfw ), ( x, wy0, zfw ) ], ( side, 0, 0 ) )
        _fpoly_d( model, F, WH, [ ( x, wy0, zfw ), ( x, wy1, zfw ), ( x, front_y( wz1 ), wz1 ), ( x, wy0, wz1 ) ],
                  ( side, 0, 0 ) )
        face = "right" if side > 0 else "left"
        for yc in ( 25.0, 47.0 ):
            F.quad( model, "sh_window_dark", side * ( wx + 0.06 ), yc, 61.0, 18.0, 22.0, face )
        # the side lights on boards under the roof's forward corners: red to port (+x), green to starboard
        x0, x1 = sorted( ( x, side * ( wx + 0.8 ) ) )
        F.box( model, x0, x1, 52.0, 61.0, 72.0, 80.0, BLK, skip=( "top", ) )
        x0, x1 = sorted( ( side * ( wx + 0.8 ), side * ( wx + 2.8 ) ) )
        F.box( model, x0, x1, 55.0, 60.0, 74.0, 78.0, "sh_paint_red" if side > 0 else "sh_paint_door" )
    _fpoly_d( model, F, WH, [ ( -wx, wy1, zfw ), ( wx, wy1, zfw ), ( wx, front_y( wz1 ), wz1 ), ( -wx, front_y( wz1 ), wz1 ) ],
              tuple( fn ) )
    for xc in ( -19.0, 0.0, 19.0 ):
        pts = [ np.array( ( xc + dx, front_y( z ), z ) ) + fn * 0.06 for dx, z in ( ( -8.5, 50.0 ), ( 8.5, 50.0 ),
                                                                                  ( 8.5, 74.0 ), ( -8.5, 74.0 ) ) ]
        _fpoly_d( model, F, "sh_window_dark", pts, tuple( fn ) )
    _fpoly_d( model, F, WH, [ ( -wx, wy0, CB_DECK ), ( wx, wy0, CB_DECK ), ( wx, wy0, wz1 ), ( -wx, wy0, wz1 ) ], ( 0, -1, 0 ) )
    F.box( model, -wx - 2.0, wx + 2.0, wy0 - 2.0, front_y( wz1 ) + 3.0, wz1, wz1 + 2.5, WH )
    F.quad( model, "sh_window_dark", 13.0, wy0 - 0.06, 60.0, 18.0, 20.0, "back" )
    F.box( model, -22.0, -4.0, wy0 - 0.6, wy0, 6.5, 66.0, WH, skip=( "front", ) )             # the door
    F.quad( model, "sh_window_dark", -13.0, wy0 - 0.66, 52.0, 11.0, 16.0, "back" )
    rod( model, F.p( -6.5, wy0 - 0.6, 36.0 ), F.p( -6.5, wy0 - 2.0, 36.0 ), 0.5, SS, 5, caps=( False, True ) )
    rod( model, F.p( -6.5, wy0 - 2.0, 36.0 ), F.p( -10.5, wy0 - 2.0, 36.0 ), 0.45, SS, 5, caps=( False, True ) )
    rz = wz1 + 2.5
    # on the roof: the mast with its masthead light, the radar dome, the aerials, a GPS mushroom, the deck lights
    rod( model, F.p( 0.0, 20.0, rz ), F.p( 0.0, 20.0, rz + 42.0 ), 1.5, SS, 8 )
    rod( model, F.p( 0.0, 20.0, rz + 42.0 ), F.p( 0.0, 20.0, rz + 46.0 ), 1.8, WH, 8 )
    rod( model, F.p( 0.0, 20.0, rz + 46.0 ), F.p( 0.0, 20.0, rz + 47.0 ), 2.0, BLK, 8, caps=( True, True ) )
    rod( model, F.p( 0.0, 20.0, rz + 30.0 ), F.p( 0.0, 21.8, rz + 30.0 ), 1.2, BLK, 6, caps=( False, True ) )
    rod( model, F.p( 0.0, 42.0, rz ), F.p( 0.0, 42.0, rz + 3.5 ), 3.0, WH, 10 )
    revolve( model, F.p( 0.0, 42.0, rz + 3.5 ), F.z, [ ( 0.0, 0.0 ), ( 9.2, 0.0 ), ( 9.2, 4.8 ), ( 8.0, 6.6 ),
                                                       ( 5.5, 7.7 ), ( 0.0, 8.0 ) ], WH, 16 )
    for x, y, h in ( ( 28.0, 13.0, 45.0 ), ( -28.0, 13.0, 25.0 ) ):
        rod( model, F.p( x, y, rz ), F.p( x, y, rz + 3.0 ), 0.9, BLK, 6 )
        rod( model, F.p( x, y, rz + 3.0 ), F.p( x, y, rz + h ), 0.35, WH, 4 )
    rod( model, F.p( -18.0, 32.0, rz ), F.p( -18.0, 32.0, rz + 3.0 ), 0.6, BLK, 5 )
    revolve( model, F.p( -18.0, 32.0, rz + 3.0 ), F.z, [ ( 0.0, 0.0 ), ( 2.6, 0.0 ), ( 2.6, 1.2 ), ( 1.6, 2.5 ),
                                                         ( 0.0, 2.8 ) ], WH, 8 )
    for x in ( -16.0, 16.0 ):
        F.box( model, x - 3.0, x + 3.0, wy0 - 1.0, wy0 + 2.0, rz, rz + 4.0, "sh_steel" )
        F.quad( model, "sh_glass", x, wy0 - 1.06, rz + 2.0, 5.0, 3.0, "back" )
    # the dry exhaust up the wheelhouse's after corner, and a lifebuoy on its back
    rod( model, F.p( 27.0, 5.5, CB_DECK ), F.p( 27.0, 5.5, 108.0 ), 2.2, BLK, 8, caps=( False, True ) )
    for z in ( 40.0, 76.0 ):
        F.box( model, 26.2, 27.8, 5.5, wy0, z - 0.8, z + 0.8, BLK )
    # (a 24" ring: orange, with four bands of reflective tape, on two hooks)
    c = np.array( ( 11.0, wy0 - 2.6, 34.0 ) )

    def ring_arc( a0, a1, count ):
        return [ F.p( *( c + ( 9.9 * math.cos( math.radians( a ) ), 0.0, 9.9 * math.sin( math.radians( a ) ) ) ) )
                 for a in np.linspace( a0, a1, count ) ]

    for q in range( 4 ):
        tube( model, ring_arc( 50.0 + 90.0 * q, 130.0 + 90.0 * q, 5 ), 2.1, "sh_paint_orange", 6 )
        tube( model, ring_arc( 40.0 + 90.0 * q, 50.0 + 90.0 * q, 2 ), 2.16, WH, 6 )
    for x in ( c[0] - 5.0, c[0] + 5.0 ):
        F.box( model, x - 0.6, x + 0.6, wy0 - 4.0, wy0, c[2] + 5.1, c[2] + 6.3, SS )

    # the pot hauler on the starboard side abaft the wheelhouse: a V-sheave on its hydraulic motor atop a pedestal,
    # under the davit; the rope comes up from the sea over the davit's block, round the sheave's vee and off its
    # bottom into a heap on the deck
    hx, hz, rr = -40.0, 40.0, 6.0                   # the sheave's centre, and the rope's radius round it in the vee
    rod( model, F.p( hx, -6.0, CB_DECK ), F.p( hx, -6.0, CB_DECK + 0.8 ), 5.0, "sh_steel", 10, caps=( False, True ) )
    rod( model, F.p( hx, -6.0, CB_DECK + 0.8 ), F.p( hx, -6.0, hz - 5.0 ), 2.6, "sh_steel", 8 )
    F.box( model, hx - 3.0, hx + 3.0, -9.5, -2.5, hz - 5.0, hz - 4.0, "sh_steel" )
    rod( model, F.p( hx, -2.5, hz ), F.p( hx, -10.0, hz ), 4.2, BLK, 10, caps=( False, True ) )
    for y0 in ( -2.0, 2.0 ):
        RP._frustum( model, F.p( hx, y0, hz ), F.p( hx, 0.0, hz ), 9.0, 5.5, "sh_steel", 14 )
        disc( model, "sh_steel", F.p( hx, y0, hz ), F.y * y0, 9.0, 14 )
    rod( model, F.p( hx, 2.0, hz ), F.p( hx, 3.0, hz ), 2.2, "sh_steel", 8, caps=( False, True ) )
    for hose in ( [ ( -38.6, -10.6, 38.0 ), ( -38.6, -11.4, 12.0 ), ( -35.0, -11.4, CB_DECK + 0.8 ) ],
                  [ ( -41.4, -10.6, 38.0 ), ( -41.4, -12.8, 12.0 ), ( -36.6, -12.8, CB_DECK + 0.8 ) ] ):
        tube( model, [ F.p( *p ) for p in _bend_path( hose, 3.0, 3 )[0] ], 0.6, BLK, 5 )
    F.box( model, -38.6, -32.6, -14.6, -9.6, CB_DECK, CB_DECK + 1.2, "sh_steel" )
    dav = _bend_path( [ ( -43.0, -14.0, CB_DECK ), ( -43.0, -14.0, 66.0 ), ( -62.0, 0.0, 76.0 ) ], 8.0, 5 )[0]
    tube( model, [ F.p( *p ) for p in dav ], 1.8, "sh_steel", 8, caps=( False, True ) )
    rod( model, F.p( -43.0, -14.0, CB_DECK ), F.p( -43.0, -14.0, CB_DECK + 0.8 ), 3.8, "sh_steel", 8,
         caps=( False, True ) )
    F.box( model, -49.4, -44.6, -15.0, -13.0, 26.0, 28.0, "sh_steel" )
    for y in ( -1.5, 1.0 ):
        F.box( model, -65.6, -58.4, y, y + 0.5, 66.0, 74.0, "sh_steel" )
    rod( model, F.p( -62.0, -1.0, 70.0 ), F.p( -62.0, 1.0, 70.0 ), 3.4, BLK, 10 )
    rod( model, F.p( -62.0, 0.0, 74.0 ), F.p( -62.0, 0.0, 75.6 ), 0.8, "sh_steel", 5 )
    px, pz = -59.2, 70.0
    t0 = math.atan2( pz - hz, px - hx ) - math.acos( rr / math.hypot( px - hx, pz - hz ) )
    rope = [ ( px, 0.0, pz ) ]
    rope += [ ( hx + rr * math.cos( a ), 0.0, hz + rr * math.sin( a ) )
              for a in np.linspace( t0, math.radians( -95.0 ), 9 ) ]
    rope += [ ( -41.0, 0.05, 33.0 ), ( -41.4, 0.3, 28.0 ), ( -41.0, 0.8, 16.0 ), ( -40.4, 1.4, 9.0 ),
              ( -40.0, 1.9, 7.0 ) ]
    for k in range( 28 ):
        a = math.radians( 200.0 ) - 2 * math.pi * k / 12
        rad = 5.5 - 3.0 * k / 27
        lift = 0.25 if k % 3 == 1 else 0.0
        rope.append( ( -34.5 + rad * math.cos( a ), 4.0 + rad * math.sin( a ), CB_DECK + 0.3 + lift ) )
    tube( model, [ F.p( *p ) for p in rope ], 0.3, "sh_rope", 4 )
    if afloat:
        tail = [ ( -64.8, 0.0, 70.0 ), ( -66.6, -1.4, 46.0 ), ( -68.8, -3.2, 22.0 ), ( -71.4, -5.0, -2.0 ) ]
    else:
        tail = [ ( -64.8, 0.0, 70.0 ), ( -65.2, 0.3, 64.0 ), ( -65.0, 0.9, 59.5 ) ]
    tube( model, [ F.p( *p ) for p in tail ], 0.3, "sh_rope", 4 )
    # the landing table the creels come aboard onto, aft of the davit, with one on it
    F.box( model, -47.0, -27.0, -48.0, -18.0, 26.0, 27.5, WH )
    F.box( model, -28.5, -27.0, -48.0, -18.0, 27.5, 29.5, WH )
    F.box( model, -47.0, -28.5, -48.0, -46.5, 27.5, 29.5, WH )
    for x in ( -42.5, -29.0 ):
        for y in ( -46.0, -20.0 ):
            rod( model, F.p( x, y, CB_DECK ), F.p( x, y, 26.0 ), 0.7, "sh_steel", 5 )
    axis = "n" if facing in ( "+n", "-n" ) else "e"
    creels( model, *F.p( -37.5, -32.5, 0.0 )[:2], zw + 27.5, count=1, axis=axis, collide=False )
    # four more creels to port, two marker buoys and a dahn (a flagged pole on its float) stowed by the transom
    creels( model, *F.p( 24.0, -82.0, 0.0 )[:2], zw + CB_DECK, count=4, axis=axis, collide=False )
    for x, y in ( ( -25.0, -115.0 ), ( -11.0, -110.0 ) ):
        sphere( model, F.p( x, y, CB_DECK + 6.5 ), 6.5, "sh_paint_orange", 10, 5 )
        rod( model, F.p( x, y, CB_DECK + 12.6 ), F.p( x, y, CB_DECK + 14.4 ), 0.9, BLK, 5, caps=( False, True ) )
    dx, dy = -28.0, -127.0
    rod( model, F.p( dx, dy, CB_DECK ), F.p( dx, dy, 78.0 ), 0.7, "sh_pine", 5, caps=( False, True ) )
    rod( model, F.p( dx, dy, CB_DECK ), F.p( dx, dy, CB_DECK + 3.6 ), 1.6, BLK, 6, caps=( False, True ) )
    rod( model, F.p( dx, dy, 18.0 ), F.p( dx, dy, 30.0 ), 3.2, "sh_paint_orange", 8, caps=( True, True ) )
    model.polygon( BLK, [ F.p( dx, dy + 0.6, 76.5 ), F.p( dx, dy + 13.0, 75.0 ), F.p( dx, dy + 13.0, 66.0 ),
                          F.p( dx, dy + 0.6, 66.5 ) ], both_sides=True )
    F.box( model, dx - 0.8, dx + 0.8, _cb_transom( 32.0 ) + 2.5, dy - 0.6, 31.4, 32.6, "sh_steel" )

    # on the bow: the stem-head roller, the samson post, and cleats along the gunwale
    zs = _cb_sheer( 138.0 ) + 1.5
    F.box( model, -2.4, 2.4, 133.0, 141.0, zs - 0.9, zs + 0.6, SS )
    for s in ( -1.0, 1.0 ):
        x0, x1 = sorted( ( s * 1.4, s * 2.3 ) )
        F.box( model, x0, x1, 134.0, 141.5, zs + 0.6, zs + 4.6, SS )
    rod( model, F.p( -1.4, 139.6, zs + 2.6 ), F.p( 1.4, 139.6, zs + 2.6 ), 1.2, "sh_rubber", 8 )
    zp = _cb_fore( 118.0 ) + _cb_camber( 0.0, _cb_in( 118.0, _cb_fore( 118.0 ) ) )
    F.box( model, -2.0, 2.0, 116.0, 120.0, zp - 0.5, zp + 13.0, "sh_pine" )
    rod( model, F.p( -3.6, 118.0, zp + 9.5 ), F.p( 3.6, 118.0, zp + 9.5 ), 0.5, SS, 5, caps=( True, True ) )
    for side in ( 1.0, -1.0 ):
        for y in ( -100.0, 40.0 ):
            zg = _cb_sheer( y )
            _cb_cleat( model, F, side * ( _cb_half( y, zg ) - 1.25 ), y, zg + 1.5 )

    # the port number on both bows
    entry = number or ( "CR 47" if paint == "sh_hull_blue" else "CR 112" )
    if not entry.startswith( "boat_" ):
        entry = "boat_" + entry.lower().replace( " ", "" )
    for side in ( 1.0, -1.0 ):
        _cb_number( model, F, entry, side )

    if afloat:
        # alongside: fenders over both sides, their lines made fast over the gunwale
        prof = [ ( 0.0, -11.0 ), ( 3.0, -10.2 ), ( 4.2, -8.0 ), ( 4.2, 8.0 ), ( 3.0, 10.2 ), ( 0.0, 11.0 ) ]
        for side in ( 1.0, -1.0 ):
            for y in ( -50.0, 30.0 ):
                xo = side * ( _cb_half( y, 20.0 ) + 4.5 )
                revolve( model, F.p( xo, y, 12.0 ), F.z, prof, "sh_paint_orange", 10 )
                zg = _cb_sheer( y )
                xg = side * _cb_half( y, zg )
                tube( model, [ F.p( xo, y, 23.0 ), F.p( xg + side * 1.0, y, zg + 0.6 ), F.p( xg, y, zg + 1.8 ),
                               F.p( xg - side * 2.6, y, zg + 1.8 ) ], 0.3, "sh_rope", 4 )
    elif trailer:
        _cb_trailer( model, e, n, z0, facing, F, zw - z0 )
    else:
        _cb_blocks( model, e, n, z0, facing, zw - z0 )
    _cb_collision( model, F )
    return zw + CB_DECK


def _cb_trailer( model, e, n, z0, facing, F, dz ):
    """ The creel boat's road trailer, the boat's waterline dz over the road: a galvanised braked twin-axle trailer with
    keel rollers on its spine, bunks to the bilges, a winch post with a bow stop, a braked coupling and its jockey wheel
    let down, mudguards and a lighting board. Collision: "metal" boxes (the frame, the wheels, the winch post) and a
    hull for the drawbar. """
    G = frame_for( e, n, z0, facing )
    ST, BLK = "sh_steel", "sh_paint_black"
    # the frame: two side members, the spine the keel rollers ride on, cross members, the A-frame to the coupling
    for s in ( -1.0, 1.0 ):
        x0, x1 = sorted( ( s * 22.5, s * 25.5 ) )
        G.box( model, x0, x1, -127.0, 100.0, 14.0, 19.0, ST )
        model.beam( G.p( s * 24.0, 100.0, 16.5 ), G.p( s * 3.0, 165.0, 16.5 ), ( 3.0, 5.0 ), ST )
    G.box( model, -2.5, 2.5, -127.0, 186.0, 14.0, 19.0, ST )
    for y in ( 90.0, 40.0, -10.0, -70.0, -120.0 ):
        G.box( model, -22.5, 22.5, y - 1.5, y + 1.5, 15.0, 18.0, ST )
    # the coupling: its overrun damper, the hood over the ball socket, the handbrake; the jockey wheel let down
    G.box( model, -3.2, 3.2, 182.0, 192.0, 14.5, 21.0, ST )
    sphere( model, G.p( 0.0, 193.0, 18.0 ), 3.6, ST, 10, 5 )
    model.beam( G.p( 2.6, 185.0, 21.0 ), G.p( 2.6, 177.0, 30.0 ), ( 1.2, 1.2 ), BLK )
    rod( model, G.p( 2.6, 177.0, 30.0 ), G.p( 2.6, 174.6, 32.7 ), 0.9, "sh_rubber", 6, caps=( False, True ) )
    G.box( model, 2.5, 6.4, 170.0, 174.0, 14.0, 19.5, ST )
    rod( model, G.p( 8.0, 172.0, 9.2 ), G.p( 8.0, 172.0, 30.0 ), 1.6, ST, 8, caps=( False, True ) )
    for x in ( 6.6, 9.0 ):
        G.box( model, x, x + 0.4, 169.5, 174.5, 3.0, 9.2, ST )
    G.box( model, 6.6, 9.4, 169.5, 174.5, 8.6, 9.2, ST )
    rod( model, G.p( 7.0, 172.0, 4.0 ), G.p( 9.0, 172.0, 4.0 ), 4.0, "sh_rubber", 10, caps=( True, True ) )
    model.beam( G.p( 8.0, 172.0, 30.6 ), G.p( 8.0, 167.0, 30.6 ), ( 1.0, 1.0 ), BLK )
    rod( model, G.p( 8.0, 167.0, 30.6 ), G.p( 8.0, 167.0, 33.6 ), 0.6, BLK, 6, caps=( False, True ) )
    # keel rollers on the spine under the skeg
    for y in ( 60.0, 20.0, -20.0, -60.0, -100.0, -116.0 ):
        zc = dz + _cb_keel( y ) - 2.5
        rod( model, G.p( -3.5, y, zc ), G.p( 3.5, y, zc ), 2.5, "sh_rubber", 8, caps=( True, True ) )
        for s in ( -1.0, 1.0 ):
            x0, x1 = sorted( ( s * 3.6, s * 4.6 ) )
            G.box( model, x0, x1, y - 2.0, y + 2.0, 19.0, zc + 1.0, ST )
    # carpeted bunks under the bilges on posts from the side members
    for s in ( -1.0, 1.0 ):
        hp = _cb_on( -15.0, -10.5, s )
        nrm = _cb_normal( -15.0, -10.5, s )
        RP._obox( model, G, tuple( hp + nrm * 1.0 + ( 0.0, 0.0, dz ) ), ( 0.0, 1.0, 0.0 ), ( nrm[2], 0.0, -nrm[0] ),
                  ( 60.0, 4.0, 2.0 ), "sh_planks_grey" )
        for y in ( -35.0, 5.0 ):
            top = _cb_on( y, -10.5, s, 2.0 ) + ( 0.0, 0.0, dz )
            RP._fbeam( model, G, ( s * 24.0, y, 19.0 ), tuple( top ), ( 2.5, 2.5 ), ST )
    # the winch post on the drawbar: two uprights with the bow stop on a bar between them, braced forward; the winch
    # between the uprights, its strap aft to the bow eye on the stem
    G.box( model, -4.5, 4.5, 133.0, 138.0, 19.0, 20.5, ST )
    for s in ( -1.0, 1.0 ):
        x0, x1 = sorted( ( s * 3.0, s * 4.5 ) )
        G.box( model, x0, x1, 134.0, 137.0, 20.5, 64.0, ST )
        model.beam( G.p( s * 3.75, 137.0, 56.0 ), G.p( s * 2.5, 160.0, 19.0 ), ( 1.5, 1.5 ), ST )
        rod( model, G.p( s * 2.8, 135.5, 50.0 ), G.p( s * 3.0, 135.5, 50.0 ), 3.4, ST, 10, caps=( True, True ) )
    G.box( model, -3.0, 3.0, 134.0, 137.0, 58.0, 62.0, ST )
    G.box( model, -2.5, 2.5, 129.5, 134.0, 57.0, 63.0, "sh_rubber" )
    rod( model, G.p( -4.5, 135.5, 50.0 ), G.p( 6.4, 135.5, 50.0 ), 0.8, ST, 6 )
    rod( model, G.p( -2.8, 135.5, 50.0 ), G.p( 2.8, 135.5, 50.0 ), 2.6, "sh_paint_blue", 10 )
    model.beam( G.p( 6.4, 135.5, 49.4 ), G.p( 6.4, 135.5, 57.0 ), ( 0.8, 1.6 ), ST )
    rod( model, G.p( 6.4, 135.5, 57.0 ), G.p( 8.6, 135.5, 57.0 ), 0.6, BLK, 6, caps=( False, True ) )
    model.beam( G.p( 0.0, 135.5, 52.6 ), G.p( 0.0, 128.4, dz - 1.6 ), ( 1.8, 0.15 ), "sh_paint_blue" )
    ce = np.array( ( 0.0, 126.4, -1.6 ) )
    tube( model, [ F.p( *( ce + ( 0.0, 1.8 * math.cos( a ), 1.3 * math.sin( a ) ) ) )
                   for a in np.linspace( -math.pi / 2, math.pi / 2, 6 ) ], 0.35, "sh_stainless", 5 )
    # the braked tandem axle: torsion beams under the side members, 185R14 wheels under one-piece mudguards
    for y in ( -8.0, -38.0 ):
        G.box( model, -30.0, 30.0, y - 1.5, y + 1.5, 11.2, 14.2, ST )
        for s in ( -1.0, 1.0 ):
            x0, x1 = sorted( ( s * 30.0, s * 34.3 ) )
            G.box( model, x0, x1, y - 1.0, y + 1.0, 11.7, 13.7, ST )
            rod( model, G.p( s * 34.3, y, 12.7 ), G.p( s * 41.6, y, 12.7 ), 12.7, "sh_rubber", 14, caps=( True, True ) )
            disc( model, ST, G.p( s * 41.65, y, 12.7 ), G.x * s, 7.5, 12 )
            rod( model, G.p( s * 41.6, y, 12.7 ), G.p( s * 42.4, y, 12.7 ), 2.6, ST, 8, caps=( False, True ) )
    for s in ( -1.0, 1.0 ):
        x0, x1 = sorted( ( s * 33.5, s * 43.0 ) )
        _arch( model, G, -8.0, 12.7, 15.2, x0, x1, ST, 15.0, 90.0, 5 )
        G.box( model, x0, x1, -38.0, -8.0, 27.75, 28.05, ST )
        _arch( model, G, -38.0, 12.7, 15.2, x0, x1, ST, 90.0, 165.0, 5 )
        xa, xb = sorted( ( s * 25.5, s * 34.3 ) )
        G.box( model, xa, xb, -24.0, -22.0, 17.0, 18.5, ST )
        xa, xb = sorted( ( s * 33.5, s * 34.3 ) )
        G.box( model, xa, xb, -24.0, -22.0, 18.5, 27.75, ST )
    # the lighting board on the side members' ends: stop and tail lamps, and a plate for the towing car's number
    G.box( model, -40.0, 40.0, -128.5, -127.0, 15.0, 23.0, BLK )
    for s in ( -1.0, 1.0 ):
        G.quad( model, "sh_paint_red", s * 35.5, -128.56, 19.0, 8.0, 5.0, "back" )
    G.quad( model, "sh_paint_yellow", 0.0, -128.56, 19.0, 20.5, 4.3, "back" )
    # collision
    G.collide( model, -25.5, 25.5, -128.5, 100.0, 0.0, dz - 31.5, "metal" )
    for s in ( -1.0, 1.0 ):
        x0, x1 = sorted( ( s * 33.5, s * 43.0 ) )
        G.collide( model, x0, x1, -50.7, 4.7, 0.0, 28.1, "metal" )
    model.hull( [ G.p( x, y, z ) for x, y in ( ( -25.5, 100.0 ), ( 25.5, 100.0 ), ( 4.0, 165.0 ), ( -4.0, 165.0 ) )
                  for z in ( 0.0, 21.0 ) ], "metal" )
    G.collide( model, -4.0, 10.0, 165.0, 196.6, 0.0, 24.0, "metal" )
    G.collide( model, -4.5, 4.5, 129.5, 138.0, 21.0, 64.0, "metal" )


def _cb_blocks( model, e, n, z0, facing, dz ):
    """ The creel boat laid up on the hard, its waterline dz over the ground: keel blocks of crossed baulks under the
    skeg and timber shores to the bilges. Collision: "wood": a box for each block, a hull for each shore. """
    G = frame_for( e, n, z0, facing )
    for y0 in ( -115.0, -60.0, 0.0, 50.0 ):
        h = dz + _cb_keel( y0 )
        layers = max( 1, math.ceil( h / 6.0 ) )
        t = h / layers
        for k in range( layers ):
            across = ( layers - 1 - k ) % 2 == 0                # the top layer lies across the keel
            for c in ( -4.5, 4.5 ):
                if across:
                    G.box( model, -10.0, 10.0, y0 + c - 2.75, y0 + c + 2.75, k * t, ( k + 1 ) * t, "sh_planks_grey" )
                else:
                    G.box( model, c - 2.75, c + 2.75, y0 - 10.0, y0 + 10.0, k * t, ( k + 1 ) * t, "sh_planks_grey" )
        G.collide( model, -10.0, 10.0, y0 - 10.0, y0 + 10.0, 0.0, h, "wood" )
    for y in ( -60.0, 10.0, 70.0 ):
        for s in ( -1.0, 1.0 ):
            top = G.p( *( _cb_on( y, 4.0, s, 1.8 ) + ( 0.0, 0.0, dz ) ) )
            foot = G.p( s * ( _cb_half( y, 4.0 ) + 28.0 ), y, 0.0 )
            model.beam( foot, top, ( 3.5, 3.5 ), "sh_planks_grey" )
            a = _unit( top - foot )
            side = _unit( np.cross( ( 0.0, 0.0, 1.0 ), a ) )
            third = np.cross( a, side )
            model.hull( [ p + side * i * 1.75 + third * j * 1.75 for p in ( foot, top ) for i in ( -1, 1 )
                          for j in ( -1, 1 ) ], "wood" )
            fx, fy = s * ( _cb_half( y, 4.0 ) + 28.0 ), y
            G.box( model, fx - 5.0, fx + 5.0, fy - 5.0, fy + 5.0, 0.0, 1.5, "sh_planks_grey" )


def _cb_collision( model, F ):
    """ The creel boat's own collision, "wood": the hull in convex pieces from the keel up to the working deck aft of
    the cuddy and to the foredeck over it, the bulwarks round both as slabs, the transom's, the skeg, the wheelhouse. """
    def section( y, top, count=5 ):
        pts = []
        for z in np.linspace( _cb_keel_line( y ), top, count ):
            x = _cb_half( y, z )
            pts += [ F.p( x, y, z ), F.p( -x, y, z ) ]
        return pts

    transom = []
    for z in np.linspace( -6.0, CB_DECK, 4 ):
        y = _cb_transom( z )
        x = _cb_half( y, z )
        transom += [ F.p( x, y, z ), F.p( -x, y, z ) ]
    aft = [ transom ] + [ section( y, CB_DECK ) for y in ( -120.0, -100.0, -80.0, -60.0, -40.0, -10.0, 20.0, 45.0,
                                                          CB_CUDDY ) ]
    fore = [ section( y, _cb_fore( y ) ) for y in ( CB_CUDDY, 80.0, 95.0, 108.0, 118.0 ) ]
    fore.append( [ F.p( 0.0, _cb_stem( z ), z ) for z in np.linspace( _cb_keel_line( 118.0 ), _cb_fore( 138.0 ), 5 ) ] )
    for pieces in ( aft, fore ):
        for a, b in zip( pieces, pieces[1:] ):
            model.hull( a + b, "wood" )

    # the bulwarks: slabs from the decks to the gunwale's top, between stations along each side; the transom's
    def wall( y, low, side ):
        hi = _cb_sheer( y ) + 1.5
        return [ F.p( side * ( _cb_half( y, min( z, _cb_sheer( y ) ) ) + 0.5 ), y, z ) for z in ( low, hi ) ] + \
               [ F.p( side * max( _cb_in( y, min( z, _cb_sheer( y ) ) ) - 0.5, 0.0 ), y, z ) for z in ( low, hi ) ]

    ztop = _cb_sheer( -135.6 )
    for _ in range( 20 ):
        ztop = _cb_sheer( _cb_transom( ztop ) )
    corner = []
    for side in ( 1.0, -1.0 ):
        for z in ( CB_DECK, ztop + 1.5 ):
            y = _cb_transom( min( z, ztop ) )
            x = _cb_half( y, min( z, ztop ) )
            corner.append( [ F.p( side * ( x + 0.5 ), y, z ), F.p( side * max( x - 3.0, 0.0 ), y + 2.5, z ) ] )
    model.hull( [ p for pair in corner for p in pair ], "wood" )
    for side in ( 1.0, -1.0 ):
        stern = [ p for z in ( CB_DECK, ztop + 1.5 ) for p in
                  ( F.p( side * ( _cb_half( _cb_transom( min( z, ztop ) ), min( z, ztop ) ) + 0.5 ),
                         _cb_transom( min( z, ztop ) ), z ),
                    F.p( side * max( _cb_half( _cb_transom( min( z, ztop ) ), min( z, ztop ) ) - 3.0, 0.0 ),
                         _cb_transom( min( z, ztop ) ) + 2.5, z ) ) ]
        walls = [ stern ] + [ wall( y, CB_DECK, side ) for y in ( -100.0, -60.0, -20.0, 20.0, CB_CUDDY ) ]
        for a, b in zip( walls, walls[1:] ):
            model.hull( a + b, "wood" )
        walls = [ wall( y, _cb_fore( y ), side ) for y in ( CB_CUDDY, 90.0, 115.0 ) ]
        walls.append( [ F.p( 0.0, _cb_stem( z ), z ) for z in ( _cb_fore( 138.0 ), _cb_sheer( 138.0 ) + 1.5 ) ] )
        for a, b in zip( walls, walls[1:] ):
            model.hull( a + b, "wood" )
    F.collide( model, -2.0, 2.0, -110.0, 92.0, -31.0, -20.0, "wood" )
    F.collide( model, -33.0, 33.0, 8.0, 69.0, CB_DECK, 84.5, "wood" )


# ---------------------------------------------------------------------------------------------------------------------
# The dinghy

# A 13 ft clinker dinghy's lines in its own frame: x across (+x the port side), y forward from amidships, z up from the
# rabbet amidships (the top of the keel). 157 over the stem and the transom, 59 in beam (1.5 m) and 21 deep amidships;
# the sheer rises 6 to the stem head and 2 to the transom. A near-upright stem on a rounded forefoot, a firm round bilge
# on a flattish floor, the run rising aft to a raked transom 36 across at the sheer, and a keel 1.5 deep deepening into
# a skeg aft. Seven strakes a side, each lapping 0.45 over the one below and gained flush into the stem, on
# steam-bent timbers.
RB_STRAKES = 7
RB_LAP = 0.45                   # a plank's lower edge stands this far out from the one below it
RB_SKIN = 0.4                   # the planks' thickness (10 mm larch)
RB_KEEL = 1.5                   # the keel's depth under the rabbet
RB_HEAD = 27.0                  # the stem head over the rabbet amidships
RB_FLOOR = 4.2                  # the bottom boards' top
RB_BAULK = 5.0                  # the baulks an upturned dinghy rests on
RB_ANTIFOULING = 3              # strakes painted with antifouling, from the garboard up
# normalised sections ( breadth, height ) from the rabbet to the sheer: amidships, at the transom and near the stem
_RB_MID = ( ( 0.0, 0.0 ), ( 0.28, 0.055 ), ( 0.52, 0.125 ), ( 0.70, 0.23 ), ( 0.83, 0.37 ), ( 0.92, 0.55 ),
            ( 0.97, 0.76 ), ( 1.0, 1.0 ) )
_RB_AFT = ( ( 0.0, 0.0 ), ( 0.30, 0.10 ), ( 0.52, 0.21 ), ( 0.70, 0.34 ), ( 0.83, 0.48 ), ( 0.92, 0.63 ),
            ( 0.97, 0.80 ), ( 1.0, 1.0 ) )
_RB_BOW = ( ( 0.0, 0.0 ), ( 0.22, 0.12 ), ( 0.42, 0.25 ), ( 0.60, 0.39 ), ( 0.75, 0.54 ), ( 0.87, 0.69 ),
            ( 0.95, 0.85 ), ( 1.0, 1.0 ) )
_RB_TABLES = {}


def _rb_sheer( y ):
    if y >= -5.0:
        return 21.0 + 6.0 * ( ( y + 5.0 ) / 83.5 ) ** 2
    return 21.0 + 2.0 * ( ( -5.0 - y ) / 71.0 ) ** 2


def _rb_keel( y ):
    """ The rabbet's height at y: level amidships, rising aft to the transom's foot, round the forefoot, up the stem. """
    if y < -10.0:
        return 6.0 * ( ( -10.0 - y ) / 66.0 ) ** 2
    if y <= 40.0:
        return 0.0
    if y < 76.0:
        t = ( y - 40.0 ) / 36.0
        return 14.0 * ( 1.0 - math.sqrt( max( 0.0, 1.0 - t * t ) ) )
    return 14.0 + ( y - 76.0 ) * 13.0 / 2.5


def _rb_stem( z ):
    """ The rabbet's y at height z on the forefoot and the stem. """
    if z <= 14.0:
        return 40.0 + 36.0 * math.sqrt( max( 0.0, 1.0 - ( 1.0 - z / 14.0 ) ** 2 ) )
    return 76.0 + ( z - 14.0 ) * 2.5 / 13.0


def _rb_transom( z ):
    """ The transom's after face at height z: its foot at -76, raked 2.5 aft at the sheer. """
    return -76.0 - 2.5 * ( z - 6.0 ) / 17.0


def _rb_beam( y ):
    """ The half-breadth at the sheer. """
    if y <= -8.0:
        return 29.5 - 11.5 * ( ( -8.0 - y ) / 68.0 ) ** 2
    return 29.5 * ( 1.0 - min( 1.0, ( y + 8.0 ) / 86.5 ) ** 2.2 )


def _rb_riser( y ):
    """ The top of the risers the thwarts sit on, following the sheer 9.4 under it. """
    return _rb_sheer( y ) - 9.4


def _rb_catmull( pts, per ):
    """ A Catmull-Rom curve through pts, per points a span. """
    p = [ np.asarray( q, float ) for q in pts ]
    p = [ 2 * p[0] - p[1] ] + p + [ 2 * p[-1] - p[-2] ]
    out = []
    for i in range( 1, len( p ) - 2 ):
        a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range( per ):
            t = k / per
            out.append( 0.5 * ( 2 * b + ( c - a ) * t + ( 2 * a - 5 * b + 4 * c - d ) * t * t
                                + ( 3 * b - a - 3 * c + d ) * t ** 3 ) )
    out.append( p[-2] )
    return out


def _rb_table( y ):
    """ Station y's section, port side, densely from the rabbet to the sheer: ( x, z, girth so far ). """
    y = min( y, 78.5 )
    key = round( y, 5 )
    table = _RB_TABLES.get( key )
    if table is None:
        w = min( max( ( -40.0 - y ) / 36.0, 0.0 ), 1.0 ) ** 1.5
        v = min( max( ( y - 15.0 ) / 55.0, 0.0 ), 1.0 ) ** 1.3
        sec = [ ( m[0] * ( 1 - w - v ) + a[0] * w + b[0] * v, m[1] * ( 1 - w - v ) + a[1] * w + b[1] * v )
                for m, a, b in zip( _RB_MID, _RB_AFT, _RB_BOW ) ]
        dense = _rb_catmull( sec, 6 )
        B, Kz, S = _rb_beam( y ), _rb_keel( y ), _rb_sheer( y )
        xs = np.array( [ B * q[0] for q in dense ] )
        zs = np.array( [ Kz + ( S - Kz ) * q[1] for q in dense ] )
        s = np.concatenate( ( [ 0.0 ], np.cumsum( np.hypot( np.diff( xs ), np.diff( zs ) ) ) ) )
        table = ( xs, zs, s )
        _RB_TABLES[key] = table
    return table


def _rb_point( y, g ):
    """ The point at girth fraction g (0 the rabbet, 1 the sheer) round station y's section, port side. """
    xs, zs, s = _rb_table( y )
    if s[-1] < 1e-6:
        return np.array( ( 0.0, y, float( zs[-1] ) ) )
    at = min( max( g, 0.0 ), 1.0 ) * s[-1]
    return np.array( ( float( np.interp( at, s, xs ) ), y, float( np.interp( at, s, zs ) ) ) )


def _rb_girth( y ):
    return float( _rb_table( y )[2][-1] )


def _rb_half( y, z ):
    """ The hull's half-breadth at ( y, z ) (the outside of the planking, laps aside): nothing under the rabbet, the
    sheer's over it. """
    xs, zs, s = _rb_table( y )
    zz = np.maximum.accumulate( zs )
    if z <= zz[0]:
        return 0.0
    return float( np.interp( z, zz, xs ) )


def _rb_z_at( y, x ):
    """ The bottom's height at half-breadth x on station y. """
    xs, zs, s = _rb_table( y )
    return float( np.interp( x, np.maximum.accumulate( xs ), zs ) )


def _rb_g_at( y, z ):
    """ The girth fraction where station y's section reaches height z. """
    xs, zs, s = _rb_table( y )
    if s[-1] < 1e-6:
        return 0.0
    return float( np.interp( z, np.maximum.accumulate( zs ), s ) ) / s[-1]


def _rb_normal( y, g ):
    """ The hull's outward normal at ( y, g ), port side. """
    h = 0.25
    a, b = _rb_point( y - h, g ), _rb_point( y + h, g )
    c, d = _rb_point( y, max( g - 0.01, 0.0 ) ), _rb_point( y, min( g + 0.01, 1.0 ) )
    nrm = np.cross( b - a, d - c )
    length = np.linalg.norm( nrm )
    return nrm / length if length > 1e-9 else np.array( ( 1.0, 0.0, 0.0 ) )


def _rb_x_in( y, z ):
    """ The inside of the planking at ( y, z ). """
    return max( _rb_half( y, z ) - RB_SKIN, 0.0 )


def _rb_lines_g( j, y ):
    """ Line j's girth fraction at y. The lines between the strakes are spaced evenly round each section; forward of
    the forefoot's start they come into the stem's rabbet one after another (the planks' hood ends), evenly up it. """
    if j >= RB_STRAKES:
        return 1.0
    lam = 0.0 if y < 40.0 else min( _rb_keel( y ) / RB_HEAD, 1.0 )
    if lam >= 1.0:
        return 0.0
    return min( max( ( j / RB_STRAKES - lam ) / ( 1.0 - lam ), 0.0 ), 1.0 )


def _rb_hood( j ):
    """ The y at which line j comes into the stem. """
    return _rb_stem( RB_HEAD * j / RB_STRAKES )


def _rb_aft( g ):
    """ Where girth fraction g meets the transom's after face. """
    y = -76.0
    for _ in range( 30 ):
        y = _rb_transom( _rb_point( y, g )[2] )
    return _rb_point( y, g )


def _rb_lines():
    """ The lines between the strakes, port side, each from the transom to the stem: line 0 the rabbet, line
    RB_STRAKES the sheer, each a list of ( point, girth fraction ). The stations are closer towards the bow, and each
    plank's hood end is one of them. """
    hoods = [ _rb_hood( j ) for j in range( 1, RB_STRAKES + 1 ) ]
    base = [ -72.0, -66.0, -58.0, -48.0, -36.0, -22.0, -8.0, 6.0, 20.0, 32.0, 42.0, 50.0, 57.0, 63.0, 68.0, 72.0 ]
    ys = sorted( [ y for y in base if min( abs( y - h ) for h in hoods ) > 1.2 ] + hoods )
    lines = []
    for j in range( RB_STRAKES + 1 ):
        g0 = _rb_lines_g( j, -76.0 )
        lines.append( [ ( _rb_aft( g0 ), g0 ) ] + [ ( _rb_point( y, _rb_lines_g( j, y ) ), _rb_lines_g( j, y ) )
                                                   for y in ys ] )
    return lines


def _rb_lap( j, y ):
    """ How far plank j's lower edge stands out over the plank below at y: the full lap, gained away over the last 10
    before the plank below runs into the stem. """
    if j < 1 or j >= RB_STRAKES:
        return 0.0
    return RB_LAP * min( max( ( _rb_hood( j ) - y ) / 10.0, 0.0 ), 1.0 )


class _Tilted:
    """ A frame that needn't be level (a boat heeled or upturned): origin o and unit axes x, y, z. Use it with
    _fpoly / _obox / F.p, never Frame.box. """

    def __init__( self, o, x, y, z ):
        self.o, self.x, self.y, self.z = ( np.asarray( v, float ) for v in ( o, x, y, z ) )

    def p( self, x, y, z ):
        return self.o + x * self.x + y * self.y + z * self.z


def _rb_paints( paint ):
    """ Each strake's paint, garboard up: antifouling (red; black under a red hull) on the lowest, the topsides, and
    the sheer strake in a contrasting colour. """
    sheer = "sh_hull_blue" if paint == "sh_hull_white" else "sh_hull_white"
    return [ _cb_antifouling( paint ) ] * RB_ANTIFOULING + [ paint ] * ( RB_STRAKES - 1 - RB_ANTIFOULING ) + [ sheer ]


def _rb_mirror( p, side ):
    return np.array( ( side * p[0], p[1], p[2] ) )


def _rb_planking( model, F, paint, lines ):
    """ The clinker planking, both sides: each strake's outside, its lower edge standing out over the strake below
    with a narrow land under it. """
    paints = _rb_paints( paint )
    count = len( lines[0] )
    lapped = [ [ pt + _rb_lap( j, pt[1] ) * _rb_normal( pt[1], g ) for pt, g in lines[j] ] for j in range( len( lines ) ) ]
    for k in range( RB_STRAKES ):
        lo, hi = lapped[k], [ pt for pt, g in lines[k + 1] ]
        mids = [ ( a + b ) / 2 for a, b in zip( lo, hi ) ]
        normals = []
        for i in range( count ):
            across = hi[i] - lo[i]
            nrm = np.cross( mids[min( i + 1, count - 1 )] - mids[max( i - 1, 0 )], across )
            if np.linalg.norm( across ) < 0.05 or np.linalg.norm( nrm ) < 1e-9:
                nrm = _rb_normal( lo[i][1], ( lines[k][i][1] + lines[k + 1][i][1] ) / 2 )
            normals.append( _unit( nrm ) )
        downs = []
        for i in range( count ):
            across = hi[i] - lo[i]
            downs.append( -_unit( across ) if np.linalg.norm( across ) > 1e-6 else -normals[i] )
        for side in ( 1.0, -1.0 ):
            for i in range( count - 1 ):
                pts = [ lo[i], lo[i + 1], hi[i + 1], hi[i] ]
                if np.linalg.norm( pts[0] - pts[3] ) > 1e-4 or np.linalg.norm( pts[1] - pts[2] ) > 1e-4:
                    _smooth_poly( model, F, paints[k], [ _rb_mirror( p, side ) for p in pts ],
                                  [ _rb_mirror( n, side ) for n in ( normals[i], normals[i + 1], normals[i + 1],
                                                                     normals[i] ) ] )
                if k < 1:
                    continue
                land = [ lines[k][i][0], lines[k][i + 1][0], lo[i + 1], lo[i] ]
                if np.linalg.norm( land[1] - land[2] ) > 1e-3 or np.linalg.norm( land[0] - land[3] ) > 1e-3:
                    _smooth_poly( model, F, paints[k], [ _rb_mirror( p, side ) for p in land ],
                                  [ _rb_mirror( n, side ) for n in ( downs[i], downs[i + 1], downs[i + 1], downs[i] ) ] )


def _rb_inside( model, F, lines, upturned ):
    """ The planks' inner faces, varnished (left out under the bottom boards). """
    count = len( lines[0] )
    inner = []
    for row in lines:
        out = []
        for pt, g in row:
            q = pt - RB_SKIN * _rb_normal( pt[1], g )
            out.append( ( np.array( ( max( q[0], 0.0 ), q[1], q[2] ) ), g * _rb_girth( pt[1] ),
                          -_rb_normal( pt[1], g ) ) )
        inner.append( out )
    for k in range( RB_STRAKES ):
        for i in range( count - 1 ):
            quad4 = [ inner[k][i], inner[k][i + 1], inner[k + 1][i + 1], inner[k + 1][i] ]
            if not upturned and max( q[0][2] for q in quad4 ) < RB_FLOOR - 0.2 and \
                    -44.0 <= quad4[0][0][1] and quad4[1][0][1] <= 36.0:
                continue
            pts = [ q[0] for q in quad4 ]
            if np.linalg.norm( pts[0] - pts[3] ) < 1e-4 and np.linalg.norm( pts[1] - pts[2] ) < 1e-4:
                continue
            uv = [ ( q[1] / 128.0, q[0][1] / 128.0 ) for q in quad4 ]
            for side in ( 1.0, -1.0 ):
                _smooth_poly( model, F, "sh_pine", [ _rb_mirror( p, side ) for p in pts ],
                              [ _rb_mirror( q[2], side ) for q in quad4 ], uv=uv )


def _rb_keelson( model, F, paint ):
    """ The keel, the skeg's deadwood aft and the stem, 1.6 thick, with a brass band along the keel and up the stem's
    face, and the hog's top inside. Returns the stem head's ( y, z ) at its face. """
    anti = _cb_antifouling( paint )
    profile = []                                    # ( inner (in the hull), outer, half-thickness )
    for y in ( -76.0, -66.0, -52.0, -36.0, -20.0, -4.0, 18.0, 40.0 ):
        profile.append( ( np.array( ( y, _rb_keel( y ) + 0.5 ) ), np.array( ( y, -RB_KEEL ) ), 0.8 ) )
    for k in range( 1, 7 ):
        th = math.pi / 2 * k / 6
        p = np.array( ( 40.0 + 36.0 * math.sin( th ), 14.0 - 14.0 * math.cos( th ) ) )
        nrm = _unit( ( math.sin( th ) / 36.0, -math.cos( th ) / 14.0 ) )
        profile.append( ( p - nrm * 0.5, p + nrm * RB_KEEL, 0.8 ) )
    top = _rb_sheer( 78.5 ) + 0.25
    nrm = _unit( ( 13.0, -2.5 ) )
    for z in ( 20.0, top ):
        p = np.array( ( _rb_stem( z ), z ) )
        d = RB_KEEL - 0.5 * min( max( ( z - 14.0 ) / 13.0, 0.0 ), 1.0 )
        i, o = p - nrm * 0.5, p + nrm * d
        if z == top:
            i, o = np.array( ( i[0], top ) ), np.array( ( o[0], top ) )
        profile.append( ( i, o, 0.8 - 0.15 * ( z - 14.0 ) / 13.0 ) )
    for ( ia, oa, wa ), ( ib, ob, wb ) in zip( profile, profile[1:] ):
        side_paint = anti if ( ia[1] + ob[1] ) / 2 < 6.0 else paint
        for s in ( 1.0, -1.0 ):
            _fpoly_d( model, F, side_paint, [ ( s * wa, ia[0], ia[1] ), ( s * wb, ib[0], ib[1] ),
                                              ( s * wb, ob[0], ob[1] ), ( s * wa, oa[0], oa[1] ) ], ( s, 0, 0 ) )
        edge = ob - oa
        _fpoly_d( model, F, "sh_brass", [ ( -wa, oa[0], oa[1] ), ( wa, oa[0], oa[1] ), ( wb, ob[0], ob[1] ),
                                          ( -wb, ob[0], ob[1] ) ], ( 0.0, edge[1], -edge[0] ) )
        edge = ib - ia
        _fpoly_d( model, F, "sh_pine", [ ( -wa, ia[0], ia[1] ), ( wa, ia[0], ia[1] ), ( wb, ib[0], ib[1] ),
                                         ( -wb, ib[0], ib[1] ) ], ( 0.0, -edge[1], edge[0] ) )
    i0, o0, w0 = profile[0]
    _fpoly_d( model, F, anti, [ ( -w0, o0[0], o0[1] ), ( w0, o0[0], o0[1] ), ( w0, i0[0], i0[1] ),
                                ( -w0, i0[0], i0[1] ) ], ( 0, -1, 0 ) )
    it, ot, wt = profile[-1]
    _fpoly_d( model, F, paint, [ ( -wt, it[0], top ), ( wt, it[0], top ), ( wt, ot[0], top ), ( -wt, ot[0], top ) ],
              ( 0, 0, 1 ) )
    return ot[0], top


def _rb_transom_board( model, F, lines ):
    """ The varnished transom, 1 thick, its after face covering the plank ends. Returns its top's ( y forward face,
    z, half-breadth inside ). """
    outer, inner = [], []
    for j, row in enumerate( lines ):
        pt, g = row[0]
        nrm = _rb_normal( pt[1], g )
        q = pt + nrm * ( RB_LAP if j >= 1 else 0.0 )
        r = pt - nrm * RB_SKIN
        outer += [ ( q[0], q[2] ), ( -q[0], q[2] ) ]
        inner += [ ( max( r[0], 0.0 ), r[2] ), ( -max( r[0], 0.0 ), r[2] ) ]
    sheer = lines[RB_STRAKES][0][0]
    top = sheer[2] + 0.25
    xo, xi = sheer[0] + RB_LAP + 0.9, sheer[0] - RB_SKIN - 0.9
    ring_o = _hull2d( [ p for p in outer if p[1] <= top ] + [ ( xo, top ), ( -xo, top ) ] )
    ring_i = _hull2d( [ p for p in inner if p[1] <= top ] + [ ( xi, top ), ( -xi, top ) ] )
    _fpoly_d( model, F, "sh_pine", [ ( x, _rb_transom( z ) - 0.02, z ) for x, z in ring_o ], ( 0, -1, -0.15 ),
              uv=[ ( z / 128.0, x / 128.0 ) for x, z in ring_o ] )
    _fpoly_d( model, F, "sh_pine", [ ( x, _rb_transom( z ) + 1.0, z ) for x, z in ring_i ], ( 0, 1, 0.15 ),
              uv=[ ( z / 128.0, x / 128.0 ) for x, z in ring_i ] )
    ya, yf = _rb_transom( top ) - 0.02, _rb_transom( top ) + 1.0
    _fpoly_d( model, F, "sh_pine", [ ( -xo, ya, top ), ( xo, ya, top ), ( xi, yf, top ), ( -xi, yf, top ) ],
              ( 0, 0, 1 ) )
    return yf, top, xi


def _rb_gunwale( model, F, lines ):
    """ The varnished gunwale both sides: the outwale against the sheer strake, the capping over it, the inwale
    inside; and the breasthook across the bow between them. """
    rows = [ pt for pt, g in lines[RB_STRAKES] ]
    keep = [ p for p in rows if not ( 75.8 < p[1] < 78.4 ) ]
    PINE = "sh_pine"
    ends = []
    for p in keep:
        nrm = _rb_normal( p[1], 1.0 )
        h = np.array( ( nrm[0], nrm[1], 0.0 ) )
        h = h / np.linalg.norm( h ) if np.linalg.norm( h ) > 1e-6 else np.array( ( 1.0, 0.0, 0.0 ) )
        o = p + h * ( RB_LAP + 0.9 )
        i = p - h * ( RB_SKIN + 0.9 )
        i[0] = max( i[0], 0.0 )
        ends.append( ( p, o, i, h ) )
    up, down = np.array( ( 0.0, 0.0, 0.25 ) ), np.array( ( 0.0, 0.0, -1.5 ) )
    for side in ( 1.0, -1.0 ):
        m = lambda q: _rb_mirror( q, side )
        for ( pa, oa, ia, ha ), ( pb, ob, ib, hb ) in zip( ends, ends[1:] ):
            hs = [ m( ha ), m( hb ) ]
            top = [ oa + up, ob + up, ib + up, ia + up ]
            _fpoly_d( model, F, PINE, [ m( q ) for q in top ], ( 0, 0, 1 ),
                      uv=[ ( q[0] / 128.0, q[1] / 128.0 ) for q in top ] )
            face = [ oa + down, ob + down, ob + up, oa + up ]
            _smooth_poly( model, F, PINE, [ m( q ) for q in face ], [ hs[0], hs[1], hs[1], hs[0] ],
                          uv=[ ( q[2] / 128.0, q[1] / 128.0 ) for q in face ] )
            under = [ pa + ha * RB_LAP + down, pb + hb * RB_LAP + down, ob + down, oa + down ]
            _fpoly_d( model, F, PINE, [ m( q ) for q in under ], ( 0, 0, -1 ),
                      uv=[ ( q[0] / 128.0, q[1] / 128.0 ) for q in under ] )
            if np.linalg.norm( ia - ib ) > 1e-3 and ( ia[0] > 1e-3 or ib[0] > 1e-3 ):
                inner = [ ia + down, ib + down, ib + up, ia + up ]
                _smooth_poly( model, F, PINE, [ m( q ) for q in inner ], [ -hs[0], -hs[1], -hs[1], -hs[0] ],
                              uv=[ ( q[2] / 128.0, q[1] / 128.0 ) for q in inner ] )
    yb = 64.0
    pb = _rb_point( yb, 1.0 )
    xb = max( pb[0] - RB_SKIN - 0.9, 0.0 )
    zb = pb[2] + 0.25
    pts = [ ( -xb, yb, zb ), ( xb, yb, zb ), ( 0.0, 77.0, _rb_sheer( 77.0 ) + 0.25 ) ]
    _fpoly_d( model, F, PINE, pts, ( 0, 0, 1 ), uv=[ ( p[0] / 128.0, p[1] / 128.0 ) for p in pts ] )
    _fpoly_d( model, F, PINE, [ ( -xb, yb, zb - 1.6 ), ( xb, yb, zb - 1.6 ), ( xb, yb, zb ), ( -xb, yb, zb ) ],
              ( 0, -1, 0 ) )


def _rb_fittings( model, F, transom_top, upturned ):
    """ The risers, the thwarts on them, the stern sheets, the quarter knees, and (right way up) the timbers and the
    bottom boards. """
    PINE = "sh_pine"
    ys = [ -70.0, -58.0, -48.0, -36.0, -22.0, -8.0, 6.0, 20.0, 32.0, 42.0, 50.0 ]
    for side in ( 1.0, -1.0 ):
        for ya, yb in zip( ys, ys[1:] ):
            ta, tb = _rb_riser( ya ), _rb_riser( yb )
            a0, a1 = _rb_x_in( ya, ta - 1.2 ) - 0.8, _rb_x_in( ya, ta ) - 0.8
            b0, b1 = _rb_x_in( yb, tb - 1.2 ) - 0.8, _rb_x_in( yb, tb ) - 0.8
            face = [ ( a0, ya, ta - 1.2 ), ( b0, yb, tb - 1.2 ), ( b1, yb, tb ), ( a1, ya, ta ) ]
            _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in face ], ( -side, 0, 0 ),
                      uv=[ ( p[2] / 128.0, p[1] / 128.0 ) for p in face ] )
            topf = [ ( a1, ya, ta ), ( b1, yb, tb ), ( b1 + 0.8, yb, tb ), ( a1 + 0.8, ya, ta ) ]
            _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in topf ], ( 0, 0, 1 ) )
    # the thwarts: amidships (the rowing thwart), forward, and the stern thwart
    for y, width in ( ( -4.0, 8.5 ), ( 46.0, 7.0 ), ( -50.0, 8.0 ) ):
        z = _rb_riser( y )
        half = min( _rb_x_in( y - width / 2, z ), _rb_x_in( y + width / 2, z ) ) - 0.1
        _obox( model, F, ( 0.0, y, z + 0.45 ), ( 1, 0, 0 ), ( 0, 1, 0 ), ( 2 * half, width, 0.9 ), PINE )
    # the stern sheets: a seat along each side from the stern thwart to the transom, on the risers
    st = [ -50.0, -58.0, -64.0, -70.0 ]
    for side in ( 1.0, -1.0 ):
        rim = [ ( _rb_x_in( y, _rb_riser( y ) ) - 0.1, y, _rb_riser( y ) + 0.9 ) for y in st ]
        for a, b in zip( rim, rim[1:] ):
            seat = [ a, b, ( b[0] - 7.0, b[1], b[2] ), ( a[0] - 7.0, a[1], a[2] ) ]
            _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in seat ], ( 0, 0, 1 ),
                      uv=[ ( p[0] / 128.0, p[1] / 128.0 ) for p in seat ] )
            edge = [ ( a[0] - 7.0, a[1], a[2] - 0.9 ), ( b[0] - 7.0, b[1], b[2] - 0.9 ), ( b[0] - 7.0, b[1], b[2] ),
                     ( a[0] - 7.0, a[1], a[2] ) ]
            _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in edge ], ( -side, 0, 0 ) )
    # the quarter knees in the transom's corners, flush with the capping
    yf, zt, xi = transom_top
    for side in ( 1.0, -1.0 ):
        yk = yf + 9.0
        zk = _rb_sheer( yk ) + 0.25
        a, b, c = ( xi, yf, zt ), ( _rb_x_in( yk, zk - 0.25 ) - 0.9, yk, zk ), ( xi - 8.0, yf, zt )
        _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in ( a, b, c ) ], ( 0, 0, 1 ) )
        _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in ( ( b[0], b[1], b[2] - 1.4 ),
                                                                     ( c[0], c[1], c[2] - 1.4 ), c, b ) ],
                  ( -side, 1, 0 ) )
    if upturned:
        return
    # the timbers: steam-bent ribs inside the planking, 1 wide and 0.6 proud, from the keel (or the bottom boards) up
    # to the inwale
    for y in ( -60.0, -45.0, -30.0, -15.0, 0.0, 15.0, 30.0, 42.0, 52.0 ):
        g0 = _rb_g_at( y, RB_FLOOR + 0.6 ) if -44.0 <= y <= 36.0 else 0.0
        gs = np.linspace( g0, _rb_g_at( y, _rb_sheer( y ) - 1.5 ), 4 )
        rows = []
        for dy in ( -0.5, 0.5 ):
            row = []
            for g in gs:
                nrm = _rb_normal( y + dy, g )
                skin = _rb_point( y + dy, g ) - nrm * RB_SKIN
                row.append( ( skin, skin - nrm * 0.6, nrm ) )
            rows.append( row )
        a, b = rows
        for side in ( 1.0, -1.0 ):
            for k in range( len( gs ) - 1 ):
                inner = [ a[k][1], b[k][1], b[k + 1][1], a[k + 1][1] ]
                _smooth_poly( model, F, PINE, [ _rb_mirror( p, side ) for p in inner ],
                              [ _rb_mirror( -q[2], side ) for q in ( a[k], b[k], b[k + 1], a[k + 1] ) ] )
                for r, toward in ( ( a, -1.0 ), ( b, 1.0 ) ):
                    face = [ r[k][0], r[k][1], r[k + 1][1], r[k + 1][0] ]
                    _fpoly_d( model, F, PINE, [ _rb_mirror( p, side ) for p in face ], ( 0, toward, 0 ) )
    # the bottom boards, fore and aft
    ys = [ -44.0, -36.0, -22.0, -8.0, 6.0, 20.0, 32.0, 36.0 ]
    ws = [ _rb_x_in( y, RB_FLOOR ) - 0.6 for y in ys ]
    for ( ya, wa ), ( yb, wb ) in zip( zip( ys, ws ), zip( ys[1:], ws[1:] ) ):
        pts = [ ( -wa, ya, RB_FLOOR ), ( wa, ya, RB_FLOOR ), ( wb, yb, RB_FLOOR ), ( -wb, yb, RB_FLOOR ) ]
        _fpoly_d( model, F, "sh_floorboards", pts, ( 0, 0, 1 ), uv=[ ( p[0] / 128.0, p[1] / 128.0 ) for p in pts ] )
    for y, w, toward in ( ( ys[0], ws[0], -1.0 ), ( ys[-1], ws[-1], 1.0 ) ):
        _fpoly_d( model, F, "sh_floorboards", [ ( -w, y, RB_FLOOR - 0.6 ), ( w, y, RB_FLOOR - 0.6 ),
                                                ( w, y, RB_FLOOR ), ( -w, y, RB_FLOOR ) ], ( 0, toward, 0 ) )


def _rb_rowlocks( model, F ):
    """ Brass crutches in their plates on the gunwale abreast the rowing thwart's after edge. Returns their horns' tops
    (local). """
    y = -19.0
    p = _rb_point( y, 1.0 )
    z = p[2] + 0.25
    tops = []
    for side in ( 1.0, -1.0 ):
        x = side * ( p[0] - 0.2 )
        _obox( model, F, ( x, y, z + 0.1 ), ( 1, 0, 0 ), ( 0, 1, 0 ), ( 1.6, 3.2, 0.2 ), "sh_brass" )
        path = [ ( x, y - 1.3, z + 3.2 ), ( x, y - 1.3, z + 2.0 ) ]
        path += [ ( x, y - 1.3 * math.cos( a ), z + 2.0 - 1.3 * math.sin( a ) )
                  for a in np.linspace( 0.3, math.pi - 0.3, 4 ) ]
        path += [ ( x, y + 1.3, z + 2.0 ), ( x, y + 1.3, z + 3.2 ) ]
        tube( model, [ F.p( *q ) for q in path ], 0.35, "sh_brass", 5, caps=( True, True ) )
        rod( model, F.p( x, y, z + 0.2 ), F.p( x, y, z + 0.75 ), 0.45, "sh_brass", 5 )
        tops.append( ( x, y, z + 3.55 ) )
    return tops


def _rb_oar( model, a, b, up, tip_paint ):
    """ A 90 in ash oar from its grip end a to its blade tip b (world), the blade flat across up: the grip, the loom,
    a leather sleeve and collar where it works in the crutch, the shaft and the blade, its tip painted. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    d = _unit( b - a )
    L = np.linalg.norm( b - a )
    at = lambda s: a + d * s * L / 90.0
    rod( model, at( 0.0 ), at( 5.5 ), 0.65, "sh_pine", 6, caps=( True, False ) )
    RP._frustum( model, at( 5.5 ), at( 7.0 ), 0.65, 1.0, "sh_pine", 6 )
    rod( model, at( 7.0 ), at( 27.0 ), 1.0, "sh_pine", 6 )
    rod( model, at( 27.0 ), at( 39.0 ), 1.1, "sh_rubber", 6, caps=( True, True ) )
    rod( model, at( 34.0 ), at( 35.2 ), 1.6, "sh_rubber", 8, caps=( True, True ) )
    RP._frustum( model, at( 39.0 ), at( 62.0 ), 0.95, 0.75, "sh_pine", 6 )
    upv = _unit( np.asarray( up, float ) - d * np.dot( up, d ) )
    across = np.cross( d, upv )

    def section( s, w, t ):
        c = at( s )
        return [ c - across * w / 2 - upv * t / 2, c + across * w / 2 - upv * t / 2,
                 c + across * w / 2 + upv * t / 2, c - across * w / 2 + upv * t / 2 ]

    secs = [ ( 62.0, 1.4, 1.2, "sh_pine" ), ( 70.0, 4.6, 0.7, "sh_pine" ), ( 84.0, 5.6, 0.5, tip_paint ),
             ( 90.0, 5.4, 0.45, tip_paint ) ]
    for ( sa, wa, ta, pa ), ( sb, wb, tb, pb ) in zip( secs, secs[1:] ):
        A, B = section( sa, wa, ta ), section( sb, wb, tb )
        for k in range( 4 ):
            k1 = ( k + 1 ) % 4
            outward( model, pa, [ A[k], A[k1], B[k1], B[k] ], ( A[k] + A[k1] ) / 2 - at( sa ) )
    outward( model, tip_paint, section( 90.0, 5.4, 0.45 ), d )


def _rb_chocks( model, G ):
    """ A chock under each bilge amidships, cut to the bottom. Collision: a hull each, "wood". """
    y = -12.0
    for side in ( 1.0, -1.0 ):
        prof = [ ( 9.0, 0.0 ), ( 16.0, 0.0 ) ] + [ ( x, _rb_z_at( y, x ) + RB_KEEL - 0.05 ) for x in ( 16.0, 12.5, 9.0 ) ]
        rows = [ [ ( side * x, yy, z ) for x, z in prof ] for yy in ( y - 3.0, y + 3.0 ) ]
        cx, cz = np.mean( [ p[0] for p in prof ] ), np.mean( [ p[1] for p in prof ] )
        for k in range( len( prof ) ):
            k1 = ( k + 1 ) % len( prof )
            face = [ rows[0][k], rows[0][k1], rows[1][k1], rows[1][k] ]
            mid = ( side * ( ( prof[k][0] + prof[k1][0] ) / 2 - cx ), 0.0, ( prof[k][1] + prof[k1][1] ) / 2 - cz )
            RP._fpoly( model, G, "sh_planks_grey", face, mid )
        for row, toward in ( ( rows[0], -1.0 ), ( rows[1], 1.0 ) ):
            RP._fpoly( model, G, "sh_planks_grey", row, ( 0, toward, 0 ) )
        model.hull( [ G.p( *p ) for row in rows for p in row ], WOOD )


def _rb_collision( model, F, upturned ):
    """ The dinghy's collision, "wood". Right way up it's open inside: the bottom up to the bottom boards, the sides as
    slabs to the gunwale's top, the bow and the stern sheets solid, the transom over them. Upturned, one hull. """
    def section( y, z0, z1, count=3, out=RB_LAP ):
        pts = []
        for z in np.linspace( z0, z1, count ):
            x = _rb_half( y, min( z, _rb_sheer( y ) ) ) + out
            pts += [ F.p( x, y, z ), F.p( -x, y, z ) ]
        return pts

    if upturned:
        pts = []
        for y in ( -70.0, -50.0, -25.0, 0.0, 25.0, 50.0, 64.0, 72.0 ):
            pts += section( y, _rb_keel( y ), _rb_sheer( y ) + 0.25, 4, RB_LAP + 0.9 )
            pts.append( F.p( 0.0, y, -RB_KEEL if y <= 40.0 else _rb_keel( y ) - RB_KEEL ) )
        for z in ( 6.0, 14.0, _rb_sheer( -78.0 ) + 0.25 ):
            y = _rb_transom( z )
            x = _rb_half( y, min( z, _rb_sheer( y ) ) ) + RB_LAP + 0.9
            pts += [ F.p( x, y, z ), F.p( -x, y, z ) ]
        pts += [ F.p( 0.0, _rb_stem( z ) + RB_KEEL, z ) for z in ( 14.0, 20.0, _rb_sheer( 78.5 ) + 0.25 ) ]
        pts.append( F.p( 0.0, -76.0, -RB_KEEL ) )
        model.hull( pts, WOOD )
        return
    bottom = []
    for y in ( -64.0, -45.0, -20.0, 10.0, 35.0, 52.0, 62.0 ):
        kz = _rb_keel( y )
        bottom += section( y, kz, max( RB_FLOOR, kz + 0.5 ) )
        bottom.append( F.p( 0.0, y, -RB_KEEL if y <= 40.0 else kz - RB_KEEL ) )
    model.hull( bottom, WOOD )
    for side in ( 1.0, -1.0 ):
        slabs = []
        for y in ( -74.0, -40.0, 0.0, 30.0, 52.0 ):
            lo, hi = max( RB_FLOOR, _rb_keel( y ) + 0.5 ), _rb_sheer( y ) + 0.25
            pts = []
            for z in ( lo, ( lo + hi ) / 2, hi ):
                x = _rb_half( y, min( z, _rb_sheer( y ) ) )
                pts += [ F.p( side * ( x + RB_LAP + ( 0.9 if z >= hi else 0.0 ) ), y, z ),
                         F.p( side * max( x - 1.6, 0.0 ), y, z ) ]
            slabs.append( pts )
        for a, b in zip( slabs, slabs[1:] ):
            model.hull( a + b, WOOD )
    bow = []
    for y in ( 52.0, 62.0, 70.0 ):
        bow += section( y, _rb_keel( y ), _rb_sheer( y ) + 0.25, 4 )
    bow += [ F.p( 0.0, _rb_stem( z ) + RB_KEEL, z ) for z in np.linspace( _rb_keel( 70.0 ), _rb_sheer( 78.5 ) + 0.25, 4 ) ]
    model.hull( bow, WOOD )
    stern = [ F.p( 0.0, -76.0, -RB_KEEL ) ]
    for z in ( 6.0, 9.0, 12.0 ):
        y = _rb_transom( z )
        x = _rb_half( y, z ) + RB_LAP
        stern += [ F.p( x, y, z ), F.p( -x, y, z ) ]
    for y in ( -64.0, -50.0 ):
        stern += section( y, _rb_keel( y ), _rb_riser( y ) + 0.9 )
        stern.append( F.p( 0.0, y, -RB_KEEL ) )
    model.hull( stern, WOOD )
    zb = _rb_sheer( -78.0 ) + 0.25
    slab = []
    for z in ( 12.0, zb ):
        y = _rb_transom( z )
        x = _rb_half( y, min( z, zb - 0.25 ) ) + RB_LAP
        slab += [ F.p( x, y, z ), F.p( -x, y, z ), F.p( x - 1.6, y + 1.6, z ), F.p( -x + 1.6, y + 1.6, z ) ]
    model.hull( slab, WOOD )


def rowing_boat( model, e, n, z0, facing, paint="sh_hull_white", upturned=False, heel=0 ):
    """ A 13 ft clinker dinghy (a tender or a pulling boat), 157 over the stem and the transom and 59 in beam, its bow
    towards facing and ( e, n ) amidships, on the ground at z0. Seven larch strakes a side, each lapping the one below,
    painted paint over antifouling (red; black under a red hull) with a contrasting sheer strake; a keel and skeg with
    a brass band, a varnished transom, gunwale, thwarts, stern sheets and timbers, bottom boards, brass crutches, two
    oars along the thwarts and its painter coiled on the ground ahead of it. Right way up it sits on its keel with a
    chock under each bilge; heel ( 1 or -1 ) lays it over on its port or starboard bilge instead, as a boat lies on a
    beach. upturned: keel up on two baulks across its gunwales, the oars on the ground beside it. Collision: "wood":
    open inside, the bottom, the bow and the stern sheets as convex pieces and the sides as slabs; upturned, one hull
    over it; the baulks and chocks. Returns the boat's highest point's z. """
    G = frame_for( e, n, z0, facing )
    _grain( model, "sh_pine", "sh_floorboards", "sh_rope", "sh_planks_grey" )
    lines = _rb_lines()
    if upturned:
        # keel up, pitched so the gunwale's tops at y +-38 sit level on the baulks
        ga, gb = _rb_point( 38.0, 1.0 ), _rb_point( -38.0, 1.0 )
        alpha = math.atan2( gb[2] - ga[2], 76.0 )
        F = _Tilted( G.o, -G.x, math.cos( alpha ) * G.y - math.sin( alpha ) * G.z,
                     -( math.sin( alpha ) * G.y + math.cos( alpha ) * G.z ) )
        F.o = F.o + np.array( ( 0.0, 0.0, z0 + RB_BAULK - F.p( 0.0, 38.0, ga[2] + 0.25 )[2] ) )
    elif heel:
        h = 1.0 if heel > 0 else -1.0
        # rolled about the keel's lower edge on that side until the bilge comes down onto the ground
        rho = math.pi / 2
        for row in lines:
            for pt, g in row:
                q = pt + _rb_normal( pt[1], g ) * RB_LAP
                if q[0] - 0.8 > 1.0:
                    rho = min( rho, math.atan2( q[2] + RB_KEEL, q[0] - 0.8 ) )
        c, s = math.cos( rho ), math.sin( rho ) * h
        F = _Tilted( G.o, c * G.x - s * G.z, G.y, s * G.x + c * G.z )
        F.o = F.o + ( G.p( h * 0.8, 0.0, 0.0 ) - F.p( h * 0.8, 0.0, -RB_KEEL ) )
    else:
        F = _Tilted( G.p( 0.0, 0.0, RB_KEEL ), G.x, G.y, G.z )
    sheer_paint = _rb_paints( paint )[-1]
    _rb_planking( model, F, paint, lines )
    _rb_inside( model, F, lines, upturned )
    stem = _rb_keelson( model, F, paint )
    transom_top = _rb_transom_board( model, F, lines )
    _rb_gunwale( model, F, lines )
    _rb_fittings( model, F, transom_top, upturned )
    if upturned:
        # the oars on the ground beside it, lying on their collars and blades
        for side, y0 in ( ( 1.0, -46.0 ), ( -1.0, -41.0 ) ):
            x = side * 41.0
            _rb_oar( model, G.p( x, y0, 2.45 ), G.p( x + side * 2.0, y0 + 90.0, 0.25 ), G.z, sheer_paint )
        for y in ( -38.0, 38.0 ):
            G.box( model, -34.0, 34.0, y - 3.0, y + 3.0, 0.0, RB_BAULK, "sh_planks_grey", WOOD )
        _rb_collision( model, F, True )
        return float( max( F.p( 0.0, y, -RB_KEEL )[2] for y in ( -76.0, 40.0 ) ) )
    tops = _rb_rowlocks( model, F )
    # the oars along the thwarts, blades forward; heeled, they've rolled down against the low side
    oars = ( ( 3.0, 0.0 ), ( 10.0, 3.0 ) ) if not heel else ( ( 18.3, 0.0 ), ( 12.4, 3.0 ) )
    for x, dy in oars:
        x = x * ( 1.0 if heel >= 0 else -1.0 )
        _rb_oar( model, F.p( x, -58.0 + dy, _rb_riser( -50.0 ) + 1.9 ),
                 F.p( x, 32.0 + dy, _rb_riser( -4.0 ) + 0.95 ), F.z, sheer_paint )
    # the painter from a ring bolt on the stem down to a coil on the ground ahead
    ring = np.array( ( 0.0, _rb_stem( 21.0 ) + 1.9, 21.0 ) )
    tube( model, [ F.p( *( ring + ( 0.0, 0.8 * math.cos( a ), 0.8 * math.sin( a ) ) ) )
                   for a in np.linspace( 0.0, 2 * math.pi, 9 ) ], 0.2, "sh_steel", 4 )
    start = F.p( *( ring + ( 0.0, 0.2, -0.8 ) ) )
    coil = G.p( 3.0 + 6.0 * heel, 94.0, 0.0 )
    path = [ start, ( start + coil ) / 2 + np.array( ( 0.0, 0.0, -0.3 * ( start[2] - z0 ) ) ),
             coil - G.y * 7.0 + np.array( ( 0.0, 0.0, 0.3 ) ) ]
    for k in range( 1, 16 ):
        a = -math.pi / 2 + 2 * math.pi * k / 8
        r = 7.0 - 3.0 * k / 15
        path.append( coil + G.x * r * math.cos( a ) + G.y * r * math.sin( a ) +
                     np.array( ( 0.0, 0.0, 0.3 + ( 0.45 if k > 8 else 0.0 ) ) ) )
    tube( model, path, 0.3, "sh_rope", 4 )
    if not heel:
        _rb_chocks( model, G )
    _rb_collision( model, F, False )
    return float( max( p[2] for p in [ F.p( 0.0, stem[0], stem[1] ) ] + [ F.p( *t ) for t in tops ] ) )


# ---------------------------------------------------------------------------------------------------------------------
# Pallets, sacks and peat


def _axis_frame( e, n, z0, axis ):
    """ A frame whose y runs along axis ("n" or "e"). """
    return frame_for( e, n, z0, "+n" if axis == "n" else "+e" )


def _rr_pieces( hw, hl, r ):
    """ A rounded rectangle's corner radius (clamped) and its eight pieces' lengths: the +x+y corner, the +y side, the
    -x+y corner, the -x side, ... counter-clockwise. """
    r = max( 0.0, min( r, hw, hl ) )
    return r, [ math.pi * r / 2, 2 * ( hw - r ), math.pi * r / 2, 2 * ( hl - r ) ] * 2


def _rr_point( hw, hl, r, piece, t ):
    """ The point ( x, y ) the way t along piece of a rounded rectangle, and its outward normal. The same ( piece, t )
    on two rectangles are corresponding points, so a band between two of them can be drawn quad by quad. """
    r, _ = _rr_pieces( hw, hl, r )
    if piece % 2 == 0:                  # a corner
        cx, cy = ( ( hw - r, hl - r ), ( -hw + r, hl - r ), ( -hw + r, -hl + r ), ( hw - r, -hl + r ) )[piece // 2]
        a = math.pi / 2 * ( piece // 2 + t )
        return ( cx + r * math.cos( a ), cy + r * math.sin( a ) ), ( math.cos( a ), math.sin( a ) )
    if piece == 1:
        return ( ( hw - r ) * ( 1 - 2 * t ), hl ), ( 0.0, 1.0 )
    if piece == 3:
        return ( -hw, ( hl - r ) * ( 1 - 2 * t ) ), ( -1.0, 0.0 )
    if piece == 5:
        return ( ( hw - r ) * ( 2 * t - 1 ), -hl ), ( 0.0, -1.0 )
    return ( hw, ( hl - r ) * ( 2 * t - 1 ) ), ( 1.0, 0.0 )


def _rr_at( outline, s ):
    """ ( piece, t ) of the point s round a rounded rectangle ( hw, hl, r ) from the start of its first piece. """
    _, pieces = _rr_pieces( *outline )
    s %= sum( pieces )
    acc = 0.0
    for k, p in enumerate( pieces ):
        if p > 1e-9 and s <= acc + p:
            return k, ( s - acc ) / p
        acc += p
    return 7, 1.0


def _rr_outline( hw, hl, r, steps=3 ):
    """ A rounded rectangle's outline ( x, y ), counter-clockwise, steps segments to a corner, no repeated points. """
    pts = []
    for piece in range( 0, 8, 2 ):
        for s in range( steps + 1 ):
            pts.append( _rr_point( hw, hl, r, piece, s / steps )[0] )
    pts = _dedupe( pts )
    if len( pts ) > 2 and np.linalg.norm( pts[0] - pts[-1] ) < 1e-3:
        pts.pop()
    return [ ( float( p[0] ), float( p[1] ) ) for p in pts ]


def _plan_ccw( points ):
    """ Plan points listed counter-clockwise from above (a frame can mirror them). """
    area = sum( p[0] * q[1] - q[0] * p[1] for p, q in zip( points, points[1:] + points[:1] ) )
    return points if area > 0 else points[::-1]


EPAL = RP.EPAL                          # 800 x 1200 x 144 mm


def _epal( model, F, x, y, z, paint="sh_planks_grey" ):
    """ One Euro pallet (EPAL) in F, its length along F's y, its middle at ( x, y ) and its underside at z: three
    bottom boards, nine blocks with the fork openings between them, three cross boards and the five deck boards. """
    W, L, H = EPAL[0] / 2, EPAL[1] / 2, EPAL[2]
    for x0, x1 in RP._EPAL_COLS:
        F.box( model, x + x0, x + x1, y - L, y + L, z, z + 0.87, paint, skip=( "bottom", ) )
        for r in RP._EPAL_ROWS:
            F.box( model, x + x0, x + x1, y + r - 2.85, y + r + 2.85, z + 0.87, z + 3.94, paint,
                   skip=( "top", "bottom" ) )
    for r in RP._EPAL_ROWS:
        F.box( model, x - W, x + W, y + r - 2.85, y + r + 2.85, z + 3.94, z + 4.8, paint )
    for x0, x1 in RP._EPAL_DECK:
        F.box( model, x + x0, x + x1, y - L, y + L, z + 4.8, z + H, paint )


def pallet( model, e, n, z0, axis="n" ):
    """ An empty Euro pallet (EPAL, 1200 x 800 x 144 mm) in weathered grey planks, its length along axis ("n" or
    "e"). Collision: one box, "wood". Returns its top. """
    F = _axis_frame( e, n, z0, axis )
    _grain( model, "sh_planks_grey" )
    _epal( model, F, 0.0, 0.0, 0.0 )
    F.collide( model, -EPAL[0] / 2, EPAL[0] / 2, -EPAL[1] / 2, EPAL[1] / 2, 0.0, EPAL[2], WOOD )
    return z0 + EPAL[2]


def pallet_stack( model, e, n, z0, count=6, axis="n" ):
    """ count empty Euro pallets stacked by hand, each a little off the one under it, their lengths along axis.
    Collision: one box, "wood". Returns the stack's top. """
    F = _axis_frame( e, n, z0, axis )
    _grain( model, "sh_planks_grey" )
    reach = 0.0
    for k in range( count ):
        key = ( "pallet", e, n, z0, k )
        x = between( -0.7, 0.7, *key, "x" ) if k else 0.0
        y = between( -0.9, 0.9, *key, "y" ) if k else 0.0
        reach = max( reach, abs( x ), abs( y ) )
        _epal( model, F, x, y, k * EPAL[2] )
    F.collide( model, -EPAL[0] / 2 - reach, EPAL[0] / 2 + reach, -EPAL[1] / 2 - reach, EPAL[1] / 2 + reach, 0.0,
               count * EPAL[2], WOOD )
    return z0 + count * EPAL[2]


SACK = ( 17.7, 25.6, 2.4, 3.9 )         # a filled 25 kg malt sack lying flat: width, length, under and over its seam


def _signed( w, m ):
    return math.copysign( abs( w ) ** m, w )


def _sack( model, C, a, b, under, over, sides=12 ):
    """ A filled hessian sack lying flat in its own frame C (its middle on the floor at the origin, its length along y,
    the sewn mouth towards +y): a rounded pillow, its seam all round under over the floor and its top domed over over
    it, pressed flat where it rests; its top falling towards the mouth, and the sewn mouth standing out as a flap with
    an ear at each corner. """
    e1, e2 = 0.75, 0.42                 # the superellipsoid's roundness up and down, and round in plan
    lats = ( -0.62, -0.25, 0.12, 0.45, 0.75, 1.0 )
    low = under / abs( _signed( math.sin( lats[0] * math.pi / 2 ), e1 ) )
    rings, norms = [], []
    for f in lats:
        phi = f * math.pi / 2
        cp, sp = math.cos( phi ), math.sin( phi )
        c = over if f >= 0 else low
        ring, nrm = [], []
        for i in range( sides ):
            th = 2 * math.pi * ( i + 0.5 ) / sides
            ct, st = math.cos( th ), math.sin( th )
            x = a * _signed( cp, e1 ) * _signed( ct, e2 )
            y = b * _signed( cp, e1 ) * _signed( st, e2 )
            h = c * _signed( sp, e1 )
            if y > 0 and h > 0:
                h *= 1.0 - 0.45 * ( y / b ) ** 3
            ring.append( ( x, y, under + h ) )
            nrm.append( _unit( ( _signed( cp, 2 - e1 ) * _signed( ct, 2 - e2 ) / a,
                                 _signed( cp, 2 - e1 ) * _signed( st, 2 - e2 ) / b, _signed( sp, 2 - e1 ) / c ) ) )
        rings.append( ring )
        norms.append( nrm )
    for j in range( len( lats ) - 1 ):
        for i in range( sides ):
            i1 = ( i + 1 ) % sides
            _smooth_poly( model, C, "sh_sack", [ rings[j][i], rings[j][i1], rings[j + 1][i1], rings[j + 1][i] ],
                          [ norms[j][i], norms[j][i1], norms[j + 1][i1], norms[j + 1][i] ] )
    z = under + 0.3
    flap = [ ( -0.72 * a, b - 0.8, z ), ( 0.72 * a, b - 0.8, z ), ( 0.97 * a, b + 0.4, z - 0.5 ),
             ( 0.66 * a, b + 1.5, z - 1.0 ), ( -0.66 * a, b + 1.5, z - 1.0 ), ( -0.97 * a, b + 0.4, z - 0.5 ) ]
    for up in ( 1.0, -1.0 ):
        _fpoly_d( model, C, "sh_sack", flap, ( 0.0, 0.0, up ) )


def sack_stack( model, e, n, z0, layers=4, axis="n" ):
    """ Filled hessian malt sacks (25 kg, about 450 x 650 x 160 mm) stacked on a Euro pallet, its length along axis:
    layers of four lying lengthwise in pairs, their mouths out, then three lying across, their mouths turned
    alternately, so the layers bind; each sack a little askew and its own size, settled into the ones under it, and the
    top layer sometimes a sack short. Collision: one box, "fabric". Returns the top. """
    F = _axis_frame( e, n, z0, axis )
    _grain( model, "sh_planks_grey" )
    _epal( model, F, 0.0, 0.0, 0.0 )
    width, length, under, over = SACK
    rise = under + over - 0.9
    top = EPAL[2]
    for k in range( layers ):
        z = EPAL[2] + k * rise
        if k % 2 == 0:
            spots = [ ( sx * 8.7, sy * 12.9, 0.0 if sy > 0 else math.pi ) for sy in ( 1, -1 ) for sx in ( -1, 1 ) ]
        else:
            spots = [ ( 0.0, y, math.pi / 2 if i % 2 == 0 else -math.pi / 2 )
                      for i, y in enumerate( ( -15.6, 0.0, 15.6 ) ) ]
        gone = -1
        if k == layers - 1 and layers > 1 and chance( 0.4, "sack short", e, n, z0, layers ):
            gone = int( unit( "sack gone", e, n, z0, layers ) * len( spots ) )
        for i, ( x, y, turn ) in enumerate( spots ):
            if i == gone:
                continue
            key = ( "sack", e, n, z0, k, i )
            t = turn + math.radians( between( -3.0, 3.0, *key, "yaw" ) )
            C = RP.Frame( F.p( x + between( -0.6, 0.6, *key, "x" ), y + between( -0.6, 0.6, *key, "y" ), z ),
                          math.cos( t ) * F.y + math.sin( t ) * F.x )
            o = over * between( 0.88, 1.08, *key, "over" )
            _sack( model, C, width / 2 * between( 0.97, 1.03, *key, "a" ),
                   length / 2 * between( 0.96, 1.03, *key, "b" ), under, o )
            top = max( top, z + under + o )
    F.collide( model, -18.0, 18.0, -27.0, 27.0, 0.0, top, "fabric" )
    return z0 + top


PEAT_COURSE = 3.0                       # a course of dried peats laid flat (each about 12 x 4 x 2.5 in)


def _peat_course( model, F, lo, hi, z0, z1, key, piece_len, lean, tread=0.0, lip=0.0 ):
    """ One course of peats round a stack, from height z0 to z1: its bottom edge on the rounded rectangle lo and its
    top edge on hi ( hw, hl, r ), cut into peats about piece_len long, each set out or in a little, its face leaning
    out by lean at the top. tread draws each peat's top back into the stack (a wall's step); lip stands a roof row's
    lower edge proud of the row under it, with a face under the edge. """
    _, pieces = _rr_pieces( *lo )
    total = sum( pieces )
    cuts = [ between( 0.0, total, *key, "start" ) ]
    while True:
        d = piece_len * between( 0.75, 1.25, *key, len( cuts ) )
        if cuts[-1] + d > cuts[0] + total - 0.55 * piece_len:
            break
        cuts.append( cuts[-1] + d )
    cuts.append( cuts[0] + total )
    for k, ( s0, s1 ) in enumerate( zip( cuts, cuts[1:] ) ):
        a, b = _rr_at( lo, s0 ), _rr_at( lo, s1 )
        out = between( -0.45, 0.45, *key, "out", k )
        ( pa, na ), ( pb, nb ) = _rr_point( *lo, *a ), _rr_point( *lo, *b )
        ( qa, ma ), ( qb, mb ) = _rr_point( *hi, *a ), _rr_point( *hi, *b )
        d0, d1 = out + lip, out + lean
        bottom = [ ( pa[0] + na[0] * d0, pa[1] + na[1] * d0, z0 ), ( pb[0] + nb[0] * d0, pb[1] + nb[1] * d0, z0 ) ]
        top = [ ( qb[0] + mb[0] * d1, qb[1] + mb[1] * d1, z1 ), ( qa[0] + ma[0] * d1, qa[1] + ma[1] * d1, z1 ) ]
        mid = _unit( ( na[0] + nb[0] + ma[0] + mb[0], na[1] + nb[1] + ma[1] + mb[1], 0.0 ) )
        run = ( math.hypot( pa[0] - qa[0], pa[1] - qa[1] ) + math.hypot( pb[0] - qb[0], pb[1] - qb[1] ) ) / 2
        _fpoly_d( model, F, "sh_peat", bottom + top, ( mid[0] * ( z1 - z0 ), mid[1] * ( z1 - z0 ), run + 0.05 ) )
        if tread:
            back = [ ( top[1][0] - ma[0] * tread, top[1][1] - ma[1] * tread, z1 + 0.5 ),
                     ( top[0][0] - mb[0] * tread, top[0][1] - mb[1] * tread, z1 + 0.5 ) ]
            _fpoly_d( model, F, "sh_peat", top + back, ( 0.0, 0.0, 1.0 ) )
        if lip:
            under = [ ( pb[0] + nb[0] * out, pb[1] + nb[1] * out, z0 - 0.8 ),
                      ( pa[0] + na[0] * out, pa[1] + na[1] * out, z0 - 0.8 ) ]
            _fpoly_d( model, F, "sh_peat", bottom + under, ( mid[0], mid[1], -0.7 ) )


def peat_stack( model, e, n, z0, length=120, width=80, height=60, axis="n" ):
    """ A built stack of dried peats (the kiln's fuel), its length along axis ("n" or "e"): walls of peats laid flat in
    courses round its rounded corners, each course stepped in on the one below and its peats tipped outwards to shed
    the rain, up to the eaves at three fifths of its height; above them a rounded, ridged top of peats laid
    overlapping like slates; and a few peats fallen at its foot. Collision: one hull, "dirt". Returns its top. """
    F = _axis_frame( e, n, z0, axis )
    key = ( "peat", e, n, z0, length, width, height )
    courses = max( 2, round( height * 0.6 / PEAT_COURSE ) )
    eaves = courses * PEAT_COURSE
    batter = 0.11 * PEAT_COURSE
    W, L, r0 = width / 2, length / 2, min( 12.0, width * 0.15 )
    base = ( W, L, r0 )

    def wall( k ):
        return ( W - k * batter, L - k * batter, max( 0.0, r0 - k * batter ) )

    for k in range( courses ):
        _peat_course( model, F, wall( k ), wall( k + 1 ), k * PEAT_COURSE, ( k + 1 ) * PEAT_COURSE,
                      key + ( "wall", k ), 12.0, 0.35, tread=2.5 )
    We, Le, re = wall( courses )
    rows = max( 2, round( ( height - eaves ) / 4.0 ) )

    def roof( k ):
        hw = We * max( 0.0, 1.0 - ( k / rows ) ** 1.6 )
        return ( hw, Le - ( We - hw ), min( hw, re + ( We - hw ) ) )

    def roof_z( k ):
        return eaves + ( height - eaves ) * k / rows

    for k in range( rows ):
        _peat_course( model, F, roof( k ), roof( k + 1 ), roof_z( k ), roof_z( k + 1 ), key + ( "roof", k ), 10.0, 0.0,
                      lip=0.6 )

    # the stack's heart, a little inside the courses, so the joints between the peats show peat, not daylight
    def ring( outline, z, inset ):
        hw, hl, r = ( max( 0.0, v - inset ) for v in outline )
        return [ F.p( *_rr_point( hw, hl, r, piece, t )[0], z ) for piece in ( 0, 2, 4, 6 ) for t in ( 0.0, 0.5, 1.0 ) ]

    core = [ ring( base, 0.0, 1.2 ), ring( wall( courses ), eaves, 1.2 ),
             ring( roof( rows // 2 ), roof_z( rows // 2 ) - 0.9, 1.0 ), ring( roof( rows ), height - 1.4, 0.0 ) ]
    heart = F.p( 0.0, 0.0, eaves * 0.5 )
    for lo, hi in zip( core, core[1:] ):
        for k in range( 12 ):
            pts = _dedupe( [ lo[k], lo[( k + 1 ) % 12], hi[( k + 1 ) % 12], hi[k] ] )
            if len( pts ) > 2 and np.linalg.norm( pts[0] - pts[-1] ) < 1e-3:
                pts.pop()
            if len( pts ) > 2:
                outward( model, "sh_peat", pts, np.mean( pts, axis=0 ) - heart )
    for k in range( 4 ):
        kk = key + ( "loose", k )
        ( x, y ), ( nx, ny ) = _rr_point( *base, int( unit( *kk, "piece" ) * 8 ) % 8, unit( *kk, "t" ) )
        out = between( 5.0, 16.0, *kk, "out" )
        yaw = between( 0.0, math.pi, *kk, "yaw" )
        tilt = between( -0.06, 0.06, *kk, "tilt" )
        _obox( model, F, ( x + nx * out, y + ny * out, 1.1 + abs( tilt ) * 5.5 ),
               ( math.cos( yaw ), math.sin( yaw ), tilt ), ( -math.sin( yaw ), math.cos( yaw ), 0.0 ),
               ( 11.0, 4.0, 2.5 ), "sh_peat" )
    hull = []
    for outline, z in ( ( base, 0.0 ), ( wall( courses ), eaves ), ( roof( rows // 2 ), roof_z( rows // 2 ) ),
                        ( roof( rows ), height ) ):
        hull += [ F.p( x, y, z ) for x, y in _rr_outline( *outline, steps=2 ) ]
    model.hull( hull, "dirt" )
    return z0 + height


# ---------------------------------------------------------------------------------------------------------------------
# The quay's ironwork

# ( r, z ): a cast-iron mushroom bollard, 24 tall, on its own round flange; and one post of a double bollard (bitts)
BOLLARD = ( ( 10.0, 0.0 ), ( 10.0, 1.1 ), ( 7.6, 1.5 ), ( 6.6, 2.6 ), ( 6.0, 6.0 ), ( 5.5, 11.0 ), ( 5.3, 15.0 ),
            ( 5.5, 16.8 ), ( 6.6, 18.3 ), ( 7.9, 19.4 ), ( 8.2, 20.4 ), ( 8.2, 21.3 ), ( 7.4, 22.6 ), ( 5.0, 23.6 ),
            ( 0.0, 24.0 ) )
BITT = ( ( 6.2, 1.4 ), ( 5.6, 5.0 ), ( 5.1, 11.0 ), ( 5.0, 14.5 ), ( 5.2, 16.2 ), ( 6.3, 17.6 ), ( 7.4, 18.6 ),
         ( 7.6, 19.6 ), ( 7.6, 20.4 ), ( 6.8, 21.6 ), ( 4.6, 22.5 ), ( 0.0, 22.9 ) )


def _nut( model, p, r=0.85, height=0.7, paint=IRON ):
    """ A hexagon nut standing on p. """
    model.cylinder( ( p[0], p[1] ), r, p[2], p[2] + height, { "side": paint, "top": paint }, sides=6 )


def bollard( model, e, n, z0, kind="single", axis="n" ):
    """ A cast-iron mooring bollard, painted black: "single", a mushroom bollard 24 tall (its head 16.4 across with a
    lip to keep a rope on, its waist 10.6) on a round flange 20 across held down by four bolts; or "double", a pair of
    posts 26 apart on one base plate held down by four bolts, the pair along axis ("n" or "e"). Collision: one box,
    "metal". Returns its top. """
    if kind == "double":
        F = _axis_frame( e, n, z0, axis )
        plate = _plan_ccw( [ tuple( F.p( x, y, 0.0 )[:2] ) for x, y in _rr_outline( 9.0, 22.0, 4.0, steps=2 ) ] )
        model.prism( plate, z0, z0 + 1.4, { "side": IRON, "top": IRON } )
        for s in ( -1, 1 ):
            revolve( model, F.p( 0.0, s * 13.0, 0.0 ), ( 0.0, 0.0, 1.0 ), BITT, IRON, sides=12 )
            for x in ( -7.3, 7.3 ):
                _nut( model, F.p( x, s * 13.0, 1.4 ) )
        F.collide( model, -9.0, 9.0, -22.0, 22.0, 0.0, BITT[-1][1], METAL )
        return z0 + BITT[-1][1]
    revolve( model, ( e, n, z0 ), ( 0.0, 0.0, 1.0 ), BOLLARD, IRON, sides=12 )
    for k in range( 4 ):
        a = math.radians( 45.0 + 90.0 * k )
        _nut( model, ( e + 8.7 * math.cos( a ), n + 8.7 * math.sin( a ), z0 + 1.1 ) )
    model.collision_box( ( e - 8.2, n - 8.2, z0 ), ( e + 8.2, n + 8.2, z0 + 24.0 ), METAL )
    return z0 + 24.0


# The crane in its own frame: x across, y along the jib, z up from the quay
CRANE_PILLAR = ( ( 13.0, 1.5 ), ( 12.4, 3.2 ), ( 10.2, 5.2 ), ( 9.5, 8.2 ), ( 9.5, 10.0 ), ( 9.0, 11.2 ), ( 8.4, 30.0 ),
                 ( 7.5, 70.0 ), ( 6.6, 110.0 ), ( 6.4, 116.5 ) )
CRANE_CAP = ( ( 6.4, 116.5 ), ( 7.4, 117.5 ), ( 7.4, 122.4 ), ( 6.2, 124.0 ), ( 3.0, 125.0 ), ( 1.2, 127.5 ),
              ( 0.0, 127.8 ) )
CRANE_COLLAR = ( ( 7.6, 53.0 ), ( 9.4, 54.0 ), ( 9.4, 63.0 ), ( 7.4, 64.0 ) )
CRANE_FOOT = ( 10.5, 59.5 )             # ( y, z ): the jib plates' pin on the collar
CRANE_HEAD = ( 158.0, 139.0 )           # ( y, z ): the head sheave's pin
CRANE_SHEAVE = 6.2
CRANE_DRUM = ( 15.0, 50.0 )             # ( y, z ): the chain drum's shaft
CRANE_WHEEL = 10.0                      # the spur wheel's pitch radius (the pinion's 2.4)
CRANE_HOOK = 76.0                       # the hook's eye over the quay


def _link_chain( model, top, bottom, paint="sh_rust", pitch=1.5, size=( 2.2, 1.25, 0.38 ) ):
    """ A hanging chain from top down to bottom: links pitch apart, each turned square to the last. """
    top, bottom = np.asarray( top, float ), np.asarray( bottom, float )
    axis = _unit( top - bottom )
    u, v = _ring_axes( axis )
    for k in range( max( 1, int( np.linalg.norm( top - bottom ) / pitch ) ) ):
        w = u if k % 2 == 0 else v
        model.oriented_box( top - axis * ( pitch * ( k + 0.5 ) ), ( axis, w, np.cross( axis, w ) ), size,
                            { "default": paint, "+x": None, "-x": None } )


def _crane_hook( model, eye, h, paint=IRON ):
    """ A forged crane hook hanging from eye (the chain's last link): the swivel, the shank, and the bowl curling round
    to its point, in the plane of h and up. Returns its lowest point. """
    eye, h, up = np.asarray( eye, float ), _unit( h ), np.array( ( 0.0, 0.0, 1.0 ) )
    rod( model, eye + up * 0.6, eye - up * 1.6, 0.9, paint, 8, caps=( True, True ) )
    rod( model, eye - up * 1.6, eye - up * 2.4, 1.3, paint, 8, caps=( True, True ) )
    zc, r = -7.2, 2.1
    pts, rs = [ eye - up * 2.4 ], [ 0.75 ]
    for a in range( 180, 441, 20 ):
        t = math.radians( a )
        pts.append( eye + h * ( r + r * math.cos( t ) ) + up * ( zc + r * math.sin( t ) ) )
        rs.append( 0.8 + 0.28 * math.sin( math.pi * ( a - 180 ) / 180 ) if a <= 360 else 0.8 - 0.45 * ( a - 360 ) / 80 )
    tube( model, pts, rs, paint, 6, caps=( False, True ) )
    return float( eye[2] + zc - r - 1.08 )


def harbour_crane( model, e, n, z0, facing ):
    """ A Victorian hand pillar crane on a quay (to lift about a ton): a tapering cast-iron pillar on a square base
    plate bolted to the quay and, turning on it, a pair of wrought-iron jib plates rising from a collar 5 ft up to a
    head 13 ft out and 11 ft 7 in up, tied back to the pillar's cap by two round bars. Under the jib, between cheek
    plates bolted to the jib plates: the chain drum with its spur wheel and pinion, a ratchet and pawl, and two crank
    handles at waist height. The chain runs from the drum up between the jib plates, over the head sheave and down to
    a hook at about head height. Painted black, the chain rusty. facing: the way the jib points. Collision: "metal"
    boxes round the pillar and round the gear. Returns the hook's eye. """
    F = frame_for( e, n, z0, facing )
    up = ( 0.0, 0.0, 1.0 )
    F.box( model, -15.0, 15.0, -15.0, 15.0, 0.0, 1.5, IRON, skip=( "bottom", ) )
    for x, y in ( ( -12.5, -12.5 ), ( 0.0, -12.5 ), ( 12.5, -12.5 ), ( 12.5, 0.0 ), ( 12.5, 12.5 ), ( 0.0, 12.5 ),
                  ( -12.5, 12.5 ), ( -12.5, 0.0 ) ):
        _nut( model, F.p( x, y, 1.5 ), 1.0, 0.9 )
    origin = F.p( 0.0, 0.0, 0.0 )
    revolve( model, origin, up, CRANE_PILLAR, IRON, sides=14 )
    # what turns: the collar with the jib's lug, and the cap with the ties' lug
    revolve( model, origin, up, CRANE_COLLAR, IRON, sides=14 )
    F.box( model, -3.0, 3.0, 6.5, 12.8, 55.0, 64.0, IRON )
    revolve( model, origin, up, CRANE_CAP, IRON, sides=14 )
    F.box( model, -3.4, 3.4, 1.5, 7.0, 118.6, 123.4, IRON )
    rod( model, F.p( -5.4, 4.5, 121.0 ), F.p( 5.4, 4.5, 121.0 ), 0.7, IRON, 6, caps=( True, True ) )
    # the jib plates, their distance pieces, the foot pin and the head sheave
    y0, zf = CRANE_FOOT
    y1, zh = CRANE_HEAD
    d = _unit( ( y1 - y0, zh - zf ) )
    perp = ( -d[1], d[0] )
    for x in ( -3.6, 3.6 ):
        model.beam( F.p( x, y0 - d[0] * 2.5, zf - d[1] * 2.5 ), F.p( x, y1 + d[0] * 4.5, zh + d[1] * 4.5 ),
                    ( 0.75, 6.5 ), IRON )
    for f in ( 0.3, 0.55, 0.8 ):
        y, z = y0 + ( y1 - y0 ) * f + perp[0] * 2.2, zf + ( zh - zf ) * f + perp[1] * 2.2
        rod( model, F.p( -3.3, y, z ), F.p( 3.3, y, z ), 0.8, IRON, 6 )
    rod( model, F.p( -4.6, y0, zf ), F.p( 4.6, y0, zf ), 1.0, IRON, 6, caps=( True, True ) )
    revolve( model, F.p( 0.0, y1, zh ), F.x, ( ( 0.0, -0.8 ), ( CRANE_SHEAVE, -0.8 ), ( CRANE_SHEAVE, -0.35 ),
                                               ( CRANE_SHEAVE - 0.8, 0.0 ), ( CRANE_SHEAVE, 0.35 ),
                                               ( CRANE_SHEAVE, 0.8 ), ( 0.0, 0.8 ) ), IRON, sides=12 )
    rod( model, F.p( -4.9, y1, zh ), F.p( 4.9, y1, zh ), 0.9, IRON, 6, caps=( True, True ) )
    # the ties, from the cap's lug to the outside of the jib plates near the head
    for x in ( -4.3, 4.3 ):
        rod( model, F.p( x, 4.5, 121.0 ), F.p( x, 150.0, 136.0 ), 0.85, IRON, 6, caps=( True, True ) )
    # the hoisting gear: two cheek plates bolted to the jib plates by three stays
    dy, dz = CRANE_DRUM
    edge = lambda y: zf + ( y - y0 ) * d[1] / d[0] - 3.25 / d[0] + 3.0
    for x in ( -10.6, 10.6 ):
        RP._side_prism( model, F, [ ( 5.0, 35.0 ), ( 9.0, 31.0 ), ( 20.0, 31.0 ), ( 24.0, 35.0 ), ( 24.0, edge( 24.0 ) ),
                                    ( 5.0, edge( 5.0 ) ) ],
                        x - 0.3, x + 0.3, lambda k: IRON, IRON )
    for y, z in ( ( 8.0, 56.5 ), ( 21.0, 63.5 ), ( 21.5, 34.0 ) ):
        rod( model, F.p( -11.3, y, z ), F.p( 11.3, y, z ), 0.6, IRON, 6, caps=( True, True ) )
    revolve( model, F.p( 0.0, dy, dz ), F.x, ( ( 0.0, -8.4 ), ( 5.2, -8.4 ), ( 5.2, -7.9 ), ( 4.0, -7.9 ), ( 4.0, 7.9 ),
                                               ( 5.2, 7.9 ), ( 5.2, 8.4 ), ( 0.0, 8.4 ) ), IRON, sides=12 )
    revolve( model, F.p( 0.0, dy, dz ), F.x, ( ( 4.0, -5.6 ), ( 4.75, -5.3 ), ( 4.75, 2.8 ), ( 4.0, 3.1 ) ), "sh_rust",
             sides=12 )
    rod( model, F.p( -13.2, dy, dz ), F.p( 12.4, dy, dz ), 0.9, IRON, 6, caps=( True, True ) )
    # the spur wheel (its rim and teeth, six spokes and the hub) outside the left cheek, and the pinion under it
    wx = -12.2
    rim = ( ( CRANE_WHEEL - 1.3, -0.65 ), ( CRANE_WHEEL, -0.65 ), ( CRANE_WHEEL, 0.65 ), ( CRANE_WHEEL - 1.3, 0.65 ),
            ( CRANE_WHEEL - 1.3, -0.65 ) )
    revolve( model, F.p( wx, dy, dz ), F.x, rim, IRON, sides=24 )
    revolve( model, F.p( wx, dy, dz ), F.x, ( ( 0.0, -1.0 ), ( 2.2, -1.0 ), ( 2.2, 1.0 ), ( 0.0, 1.0 ) ), IRON, sides=8 )
    for k in range( 6 ):
        c, s = math.cos( math.pi * k / 3 ), math.sin( math.pi * k / 3 )
        _obox( model, F, ( wx, dy + c * 5.4, dz + s * 5.4 ), ( 0.0, c, s ), ( 1.0, 0.0, 0.0 ), ( 6.6, 0.7, 1.1 ), IRON )
    for k in range( 30 ):
        a = 2 * math.pi * ( k + 0.5 ) / 30
        c, s = math.cos( a ), math.sin( a )
        _obox( model, F, ( wx, dy + c * ( CRANE_WHEEL + 0.4 ), dz + s * ( CRANE_WHEEL + 0.4 ) ), ( 0.0, c, s ),
               ( 0.0, -s, c ), ( 0.8, 0.85, 1.3 ), { "default": IRON, "-x": None } )
    cz = dz - CRANE_WHEEL - 2.4
    revolve( model, F.p( wx, dy, cz ), F.x, ( ( 0.0, -0.65 ), ( 2.4, -0.65 ), ( 2.4, 0.65 ), ( 0.0, 0.65 ) ), IRON,
             sides=10 )
    # the ratchet and its pawl outside the right cheek
    revolve( model, F.p( 11.6, dy, dz ), F.x, ( ( 0.0, -0.4 ), ( 3.6, -0.4 ), ( 3.6, 0.4 ), ( 0.0, 0.4 ) ), IRON,
             sides=12 )
    _obox( model, F, ( 11.6, dy - 2.6, dz + 4.4 ), ( 0.0, 0.8, -0.6 ), ( 1.0, 0.0, 0.0 ), ( 4.2, 0.6, 1.0 ), IRON )
    # the crank shaft and its two handles, opposite each other
    rod( model, F.p( -15.4, dy, cz ), F.p( 15.4, dy, cz ), 0.75, IRON, 6, caps=( True, True ) )
    for x, a in ( ( -14.9, 115.0 ), ( 14.9, 295.0 ) ):
        t = math.radians( a )
        end = ( dy + 9.0 * math.cos( t ), cz + 9.0 * math.sin( t ) )
        model.beam( F.p( x, dy, cz ), F.p( x, *end ), ( 0.7, 1.6 ), IRON )
        s = 1.0 if x > 0 else -1.0
        rod( model, F.p( x, *end ), F.p( x + s * 5.6, *end ), 0.95, IRON, 8, caps=( False, True ) )
    # the chain: from the drum up under the jib to the sheave, and hanging from it to the hook
    rs = CRANE_SHEAVE - 0.4
    to = _unit( ( y1 - dy, zh - dz - 4.75 ) )
    rod( model, F.p( 0.0, dy, dz + 4.75 ), F.p( 0.0, y1 - to[1] * rs, zh + to[0] * rs ), 0.42, "sh_rust", 4 )
    wrap = math.atan2( to[0], -to[1] )
    tube( model, [ F.p( 0.0, y1 + rs * math.cos( wrap * f ), zh + rs * math.sin( wrap * f ) )
                   for f in ( 1.0, 0.8, 0.6, 0.4, 0.2, 0.0 ) ], 0.42, "sh_rust", 4 )
    eye = F.p( 0.0, y1 + rs, CRANE_HOOK )
    _link_chain( model, F.p( 0.0, y1 + rs, zh ), eye )
    _crane_hook( model, eye, -F.y )
    model.collision_box( ( e - 9.6, n - 9.6, z0 ), ( e + 9.6, n + 9.6, z0 + 128.0 ), METAL )
    F.collide( model, -20.6, 20.6, 4.0, 26.0, 28.0, 61.0, METAL )
    return tuple( float( v ) for v in eye )


# ---------------------------------------------------------------------------------------------------------------------
# The yard's and the pier's clutter

# A 70 l fish box (moulded polyethylene, 800 x 500 x 290 mm): its half-width, half-length and height at the rim
FISHBOX = ( 9.85, 15.75, 11.4 )
FISHBOX_PITCH = FISHBOX[2] - 0.2        # stacked, a box's foot sits 0.2 down inside the rim of the one below


def _fb_rings( top ):
    """ A fish box's rings ( hw, hl, r, z ) from its foot up the tapered wall (the hand holds are in the band from the
    third to the fourth), out under the lip, up its edge, over the rim and down inside: to the floor in the top box,
    an inch down in the others (the box above hides the rest). """
    hw, hl, H = FISHBOX
    foot, low, lip = ( 8.6, 14.5, 1.3, 0.0 ), ( 8.9, 14.8, 1.6, 0.35 ), ( 9.4, 15.3, 2.0, H - 1.1 )
    inner, floor = ( 8.75, 14.65, 1.35, H ), ( 8.22, 14.12, 0.82, 0.8 )

    def at( a, b, z ):
        f = ( z - a[3] ) / ( b[3] - a[3] )
        return tuple( a[k] + ( b[k] - a[k] ) * f for k in range( 3 ) ) + ( z, )

    return [ foot, low, at( low, lip, H - 3.6 ), at( low, lip, H - 2.0 ), lip, ( hw, hl, 2.45, H - 1.1 ),
             ( hw, hl, 2.45, H ), inner, floor if top else at( floor, inner, H - 1.0 ) ]


def _fb_ring( ring ):
    """ A ring's twelve points ( x, y, z ), three to each rounded corner, and their outward normals ( x, y ). Points
    2-3 run along the +y end, 5-6 the -x side, 8-9 the -y end and 11-0 the +x side. """
    hw, hl, r, z = ring
    pts, nrm = [], []
    for c in range( 4 ):
        for s in range( 3 ):
            ( x, y ), ( nx, ny ) = _rr_point( hw, hl, r, 2 * c, s / 2 )
            pts.append( np.array( ( x, y, z ) ) )
            nrm.append( ( nx, ny ) )
    return pts, nrm


def _fb_normal( a, b, hn ):
    """ The normal of a band running from point a on one ring to point b on the next, where the rings' outward normal
    is hn: out and down where the wall leans out, up over the rim, in and up inside. """
    dz = b[2] - a[2]
    out = ( b[0] - a[0] ) * hn[0] + ( b[1] - a[1] ) * hn[1]
    return _unit( ( hn[0] * dz, hn[1] * dz, -out ) )


def _fb_hold( model, F, paint, a0, a1, b0, b1, hn, half=2.5, depth=0.65 ):
    """ The band across one end of a fish box from ring a (points a0, a1) up to ring b, with a hand hold cut in it,
    2 half wide: the wall either side of it, and the hold's sill, head, sides and dark back. """
    s = 1.0 if a0[0] > 0 else -1.0

    def at( p, q, x ):
        return p + ( q - p ) * ( ( x - p[0] ) / ( q[0] - p[0] ) )

    nrm = tuple( _fb_normal( a0, b0, hn ) )
    a_1, a_2 = at( a0, a1, s * half ), at( a0, a1, -s * half )
    b_1, b_2 = at( b0, b1, s * half ), at( b0, b1, -s * half )
    _fpoly_d( model, F, paint, [ a0, a_1, b_1, b0 ], nrm )
    _fpoly_d( model, F, paint, [ a_2, a1, b1, b_2 ], nrm )
    d = np.array( ( -hn[0], -hn[1], 0.0 ) ) * depth
    _fpoly_d( model, F, "sh_rubber", [ a_1 + d, a_2 + d, b_2 + d, b_1 + d ], ( hn[0], hn[1], 0.0 ) )
    _fpoly_d( model, F, paint, [ a_1, a_2, a_2 + d, a_1 + d ], ( 0.0, 0.0, 1.0 ) )
    _fpoly_d( model, F, paint, [ b_1, b_2, b_2 + d, b_1 + d ], ( 0.0, 0.0, -1.0 ) )
    _fpoly_d( model, F, paint, [ a_1, a_1 + d, b_1 + d, b_1 ], ( -s, 0.0, 0.0 ) )
    _fpoly_d( model, F, paint, [ a_2, a_2 + d, b_2 + d, b_2 ], ( s, 0.0, 0.0 ) )


def _fish_box( model, F, paint, top ):
    """ One fish box in F (x across it, y along it, z up from its foot); only the top box of a stack shows its floor. """
    rings = [ _fb_ring( r ) for r in _fb_rings( top ) ]
    hn = rings[0][1]
    for b in range( len( rings ) - 1 ):
        A, B = rings[b][0], rings[b + 1][0]
        for i in range( 12 ):
            j = ( i + 1 ) % 12
            if b == 2 and i in ( 2, 8 ):
                _fb_hold( model, F, paint, A[i], A[j], B[i], B[j], hn[i] )
                continue
            ni, nj = _fb_normal( A[i], B[i], hn[i] ), _fb_normal( A[j], B[j], hn[j] )
            _smooth_poly( model, F, paint, [ A[i], A[j], B[j], B[i] ], [ ni, nj, nj, ni ] )
    if top:
        _fpoly_d( model, F, paint, rings[-1][0], ( 0.0, 0.0, 1.0 ) )


def fish_boxes( model, e, n, z0, count=5, colour="blue", axis="n" ):
    """ count 70 l fish boxes stacked on the quay: moulded polyethylene, 800 x 500 x 290 mm, the walls tapered with ribs
    up them (the texture's), a lip round the top and a hand hold in each end. Each sits 0.2 down inside the rim of the
    one below and a little askew on it. colour: "blue", "orange" or "mixed" (box by box); their lengths along axis
    ("n" or "e"). Collision: one box, "plastic". Returns the stack's top. """
    if colour not in ( "blue", "orange", "mixed" ):
        raise ValueError( f"fish_boxes: colour must be blue, orange or mixed, not {colour!r}" )
    count = max( 1, int( count ) )
    key = ( "fish", e, n, z0, count, colour, axis )
    yaw0 = math.radians( between( -1.5, 1.5, *key, "yaw" ) ) - ( math.pi / 2 if axis == "e" else 0.0 )
    for k in range( count ):
        yaw, de, dn = yaw0, 0.0, 0.0
        if k:
            yaw += math.radians( between( -0.5, 0.5, *key, k, "yaw" ) )
            de, dn = between( -0.12, 0.12, *key, k, "e" ), between( -0.12, 0.12, *key, k, "n" )
        F = RP.Frame( ( e + de, n + dn, z0 + k * FISHBOX_PITCH ), ( -math.sin( yaw ), math.cos( yaw ) ) )
        c = colour if colour != "mixed" else pick( ( "blue", "orange" ), *key, k, "colour" )
        _fish_box( model, F, f"sh_fishbox_{c}", k == count - 1 )
    top = ( count - 1 ) * FISHBOX_PITCH + FISHBOX[2]
    F = RP.Frame( ( e, n, z0 ), ( -math.sin( yaw0 ), math.cos( yaw0 ) ) )
    _obox( model, F, ( 0.0, 0.0, top / 2 ), ( 1.0, 0.0, 0.0 ), ( 0.0, 1.0, 0.0 ), ( 20.5, 32.3, top ), None, "plastic" )
    return z0 + top


def _rope( model, points, d, sides=6, caps=( True, True ), paint="sh_rope" ):
    """ A laid rope d across along a polyline (round its corners first), shaded smooth, with sh_rope's strands wound
    round it at the picture's own lay: a quarter of the picture's width goes once round the rope (three strands) and its
    height is 4 pi d of rope, so the strands lie at the texture's 37 degrees whatever the rope's size. The ends are
    whipped flat. """
    pts = _dedupe( points )
    if len( pts ) < 2:
        return
    count = len( pts )
    tans = []
    for i in range( count ):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == count - 1:
            t = pts[-1] - pts[-2]
        else:
            t = _unit( pts[i] - pts[i - 1] ) + _unit( pts[i + 1] - pts[i] )
        tans.append( _unit( t ) )
    u = _ring_axes( tans[0] )[0]
    rings, dirs, along = [], [], [ 0.0 ]
    for i in range( count ):
        u = u - tans[i] * np.dot( u, tans[i] )
        if np.linalg.norm( u ) < 1e-6:
            u = _ring_axes( tans[i] )[0]
        u = _unit( u )
        w = np.cross( tans[i], u )
        ds = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * w for k in range( sides ) ]
        dirs.append( ds )
        rings.append( [ pts[i] + d / 2 * v for v in ds ] )
        if i:
            along.append( along[-1] + float( np.linalg.norm( pts[i] - pts[i - 1] ) ) )
    lay = 4 * math.pi * d
    for i in range( count - 1 ):
        v0, v1 = along[i] / lay, along[i + 1] / lay
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            u0, u1 = 0.25 * k / sides, 0.25 * ( k + 1 ) / sides
            nrm = [ dirs[i][k], dirs[i][k1], dirs[i + 1][k1], dirs[i + 1][k] ]
            outward( model, paint, [ rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k] ], sum( nrm ),
                     uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ], normals=nrm )
    if caps[0]:
        outward( model, paint, rings[0], -tans[0] )
    if caps[1]:
        outward( model, paint, rings[-1], tans[-1] )
    _grain( model, paint )


def _cubic( p0, p1, p2, p3, steps ):
    """ A cubic Bezier's points, p0 left out. """
    p0, p1, p2, p3 = ( np.asarray( p, float ) for p in ( p0, p1, p2, p3 ) )
    out = []
    for s in range( 1, steps + 1 ):
        t = s / steps
        out.append( ( 1 - t ) ** 3 * p0 + 3 * ( 1 - t ) ** 2 * t * p1 + 3 * ( 1 - t ) * t * t * p2 + t ** 3 * p3 )
    return out


def _settle( plan, d, skip ):
    """ Heights for a rope laid down along plan ( x, y ) in order: each point lies on whatever was laid before it (but
    the last skip points) within d of it, else on the ground (d / 2), and the rope's stiffness bridges the dips. """
    P = np.asarray( plan, float )
    z = np.full( len( P ), d / 2 )

    def support( i ):
        lim = i - skip
        if lim < 2:
            return d / 2
        a, b = P[:lim - 1], P[1:lim]
        ab = b - a
        t = np.clip( np.einsum( "ij,ij->i", P[i] - a, ab ) / np.maximum( np.einsum( "ij,ij->i", ab, ab ), 1e-9 ), 0, 1 )
        h = np.linalg.norm( P[i] - ( a + ab * t[:, None] ), axis=1 )
        ok = h < d
        if not ok.any():
            return d / 2
        zz = z[:lim - 1] + ( z[1:lim] - z[:lim - 1] ) * t
        return max( d / 2, float( np.max( zz[ok] + np.sqrt( d * d - h[ok] ** 2 ) ) ) )

    for i in range( len( P ) ):
        z[i] = support( i )
    for _ in range( 6 ):
        s = z.copy()
        s[1:-1] = 0.25 * z[:-2] + 0.5 * z[1:-1] + 0.25 * z[2:]
        z = np.maximum( z, s )
    for i in range( len( P ) ):
        z[i] = max( z[i], support( i ) )
    return z


def rope_coil( model, e, n, z0, r=14 ):
    """ A mooring rope (inch manila) coiled down on the quay as a sailor drops it: five to seven loosely oval loops of
    different sizes, each a little off the one before, lying on the ground or across the loops under it in a low heap,
    and the end led off the top and down to trail along the ground. r: the heap's outer radius. No collision. Returns
    the heap's top. """
    d = 1.0
    key = ( "coil", e, n, z0, r )
    loops = int( min( 7, max( 5, round( 3 + r / 5 ) ) ) )
    steps = int( min( 16, max( 12, round( r ) ) ) )
    shape = []
    for k in range( loops ):
        R = between( 0.5 * r, r - d / 2, *key, k, "r" )
        a, off = between( 0.0, 2 * math.pi, *key, k, "off" ), between( 0.0, 0.2 * r, *key, k, "offr" )
        oval = between( 0.75, 1.0, *key, k, "oval" )
        R = min( R, ( r - d / 2 - off ) / 1.0 )
        shape.append( ( np.array( ( e + off * math.cos( a ), n + off * math.sin( a ) ) ), R, oval,
                        between( 0.0, math.pi, *key, k, "turn" ) ) )

    def at( k, ang ):
        C, R, oval, turn = shape[k]
        x, y = R * math.cos( ang - turn ), R * oval * math.sin( ang - turn )
        return C + np.array( ( x * math.cos( turn ) - y * math.sin( turn ), x * math.sin( turn ) + y * math.cos( turn ) ) )

    th = between( 0.0, 2 * math.pi, *key, "start" )
    plan, angle = [], []
    for k in range( loops ):
        last = k == loops - 1
        sweep = 2 * math.pi * between( 0.94, 1.06, *key, k, "sweep" )
        for s in range( steps + ( 1 if last else 0 ) ):
            f = s / steps
            a = th + sweep * f
            w = 0.0 if last else _smooth( ( f - 0.7 ) / 0.3 )
            plan.append( at( k, a ) * ( 1 - w ) + at( k + 1, a ) * w if w else at( k, a ) )
            angle.append( a )
        th += sweep
    z = _settle( plan, d, int( 0.8 * steps ) )
    path = [ np.array( ( p[0], p[1], z0 + zz ) ) for p, zz in zip( plan, z ) ]
    # the end: off the top of the heap the way the last loop runs, down to the ground and along it
    end = path[-1]
    T = _unit( np.append( plan[-1] - plan[-2], 0.0 ) )
    side = np.array( ( -T[1], T[0], 0.0 ) ) * ( 1.0 if chance( 0.5, *key, "side" ) else -1.0 )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    G = end + T * 12.0
    G[2] = z0 + d / 2
    path += _cubic( end, end + T * 4.0 + up * 1.0, G - T * 5.0, G, 7 )
    path += _cubic( G, G + T * 7.0, G + T * 14.0 + side * 3.0, G + T * 20.0 + side * 4.0, 5 )
    _rope( model, path, d, 5 )
    return float( z0 + z.max() + d / 2 )


def buoy( model, e, n, z0, colour="orange" ):
    """ A round inflatable PVC buoy (a mooring float, also hung over the side as a fender) 17 across and 21 long to the
    top of its moulded rope eye, lying on its side on the ground with its axis 55-80 degrees off upright and sunk a
    little under its weight, with a short lanyard through the eye trailing on the ground. colour: "orange", "red",
    "yellow", "blue", "white" or "black" (the sh_paint_ paints). Collision: one small box, "plastic". Returns its
    top. """
    if colour not in ( "orange", "red", "yellow", "blue", "white", "black" ):
        raise ValueError( f"buoy: no sh_paint_{colour}" )
    key = ( "buoy", e, n, z0, colour )
    tilt = math.radians( between( 55.0, 80.0, *key, "tilt" ) )
    yaw = between( 0.0, 2 * math.pi, *key, "yaw" )
    axis = np.array( ( math.sin( tilt ) * math.cos( yaw ), math.sin( tilt ) * math.sin( yaw ), math.cos( tilt ) ) )
    c = np.array( ( e, n, z0 + 8.25 ) )
    prof = [ ( 0.0, -8.5 ) ] + [ ( 8.5 * math.cos( math.radians( a ) ), 8.5 * math.sin( math.radians( a ) ) )
                                for a in ( -67.5, -45.0, -22.5, 0.0, 22.5, 45.0, 62.0 ) ] \
        + [ ( 2.7, 8.2 ), ( 2.2, 9.0 ), ( 1.8, 9.6 ), ( 0.0, 9.8 ) ]
    paint = f"sh_paint_{colour}"
    revolve( model, c, axis, prof, paint, sides=12, crease=50.0 )
    u = _ring_axes( axis )[0]
    v = np.cross( axis, u )
    if v[2] < 0:
        v = -v
    eye = c + axis * 10.4
    _loop( model, eye, axis, v, 1.4, 1.6, 0.85, paint, steps=10, sides=6 )
    # the lanyard: knotted through the eye (its tail end on one side), down to the ground on the other and along it
    out = _unit( ( axis[0], axis[1], 0.0 ) )
    w = u * ( 1.0 if chance( 0.5, *key, "side" ) else -1.0 )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    G = np.array( ( eye[0], eye[1], z0 + 0.3 ) ) + w * 8.0 + out * 3.0
    path = [ eye - w * 2.4 - up * 1.4, eye - w * 1.3 - up * 0.3, eye ]
    path += _cubic( eye, eye + w * 3.0, G - w * 3.0 + up * 2.0, G, 7 )
    path += _cubic( G, G + w * 6.0, G + w * 12.0 + out * 4.0, G + w * 18.0 + out * 3.0, 5 )
    _rope( model, path, 0.6, 4 )
    model.collision_box( ( e - 6.5, n - 6.5, z0 ), ( e + 6.5, n + 6.5, z0 + 15.0 ), "plastic" )
    return z0 + 16.75


# A 200 l (44 gallon) steel drum standing on end ( r, z ): the rolled chime at its foot, the two rolling hoops, the top
# chime and the lid, sunk half an inch inside it
DRUM = ( ( 11.2, 0.0 ), ( 11.5, 0.3 ), ( 11.5, 0.95 ), ( 11.2, 1.25 ),
         ( 11.2, 10.95 ), ( 11.6, 11.4 ), ( 11.6, 11.8 ), ( 11.2, 12.25 ),
         ( 11.2, 22.35 ), ( 11.6, 22.8 ), ( 11.6, 23.2 ), ( 11.2, 23.65 ),
         ( 11.2, 33.4 ), ( 11.5, 33.7 ), ( 11.5, 34.65 ), ( 11.1, 34.65 ), ( 11.0, 34.15 ), ( 0.0, 34.15 ) )


def drum( model, e, n, z0, paint="sh_paint_blue" ):
    """ A 200 l (44 gallon) steel drum standing on end, 23.2 across its hoops and 34.65 tall: a rolled chime top and
    bottom (the bottom one rusted on some), two rolling hoops, and the lid's two screw bungs, 2 in and 3/4 in. Collision:
    one box, "metal". Returns its top. """
    key = ( "drum", e, n, z0, paint )
    rusty = chance( 0.5, *key, "rust" )
    revolve( model, ( e, n, z0 ), ( 0.0, 0.0, 1.0 ), DRUM, lambda k: "sh_rust" if rusty and k < 3 else paint,
             sides=16, turn=between( 0.0, math.pi / 8, *key, "turn" ) )
    a = between( 0.0, 2 * math.pi, *key, "bungs" )
    for r, s in ( ( 1.45, 1.0 ), ( 0.85, -1.0 ) ):
        revolve( model, ( e + s * 8.3 * math.cos( a ), n + s * 8.3 * math.sin( a ), z0 + 34.15 ), ( 0.0, 0.0, 1.0 ),
                 ( ( r, 0.0 ), ( r, 0.35 ), ( r - 0.25, 0.45 ), ( 0.0, 0.45 ) ), "sh_steel", 8 )
    model.collision_box( ( e - 11.6, n - 11.6, z0 ), ( e + 11.6, n + 11.6, z0 + 34.65 ), METAL )
    return z0 + 34.65


# A square Victorian street lantern ( half-width, z ): its base, the four panes (band 3, sh_lamp_warm: lit) widening
# upwards between the corner posts, the cornice, the hipped roof and the vent's cap. 26 tall, 17 across the cornice.
LANTERN = ( ( 0.0, 0.0 ), ( 3.0, 0.0 ), ( 5.25, 2.4 ), ( 5.0, 2.6 ), ( 7.5, 17.4 ), ( 8.25, 17.4 ), ( 8.25, 19.0 ),
            ( 8.6, 19.0 ), ( 4.0, 22.5 ), ( 1.4, 24.6 ), ( 1.4, 26.0 ), ( 0.0, 26.0 ) )
LANTERN_GLASS = 3
LANTERN_HANG_TOP = 30.05        # a hanging lantern's ring's top over its base


def _square_bands( model, F, base, prof, paint, s=1.0 ):
    """ A square thing's surface from a profile ( half-width, z ) about the upright through base (local), its sides
    along F's axes, s times the profile's size: paint( k ) for the band from point k to k + 1 (None leaves it out). """
    bx, by, bz = base
    for k, ( ( w0, h0 ), ( w1, h1 ) ) in enumerate( zip( prof, prof[1:] ) ):
        p = paint( k ) if callable( paint ) else paint
        if p is None:
            continue
        w0, w1, h0, h1 = w0 * s, w1 * s, h0 * s, h1 * s
        for hx, hy in ( ( 0.0, 1.0 ), ( -1.0, 0.0 ), ( 0.0, -1.0 ), ( 1.0, 0.0 ) ):
            tx, ty = -hy, hx
            pts = [ ( bx + ( hx - tx ) * w0, by + ( hy - ty ) * w0, bz + h0 ),
                    ( bx + ( hx + tx ) * w0, by + ( hy + ty ) * w0, bz + h0 ),
                    ( bx + ( hx + tx ) * w1, by + ( hy + ty ) * w1, bz + h1 ),
                    ( bx + ( hx - tx ) * w1, by + ( hy - ty ) * w1, bz + h1 ) ]
            _fpoly_d( model, F, p, pts, ( hx * ( h1 - h0 ), hy * ( h1 - h0 ), -( w1 - w0 ) ) )


def _lantern( model, F, base, s=1.0, hang=False ):
    """ A square cast-iron street lantern with its glass lit, standing on base (local) at s times full size: the
    profile's bands, the four corner posts, a ball finial and over it a spike or, to hang it, a ring. Returns the
    lamp's place (world) and the lantern's top (local z). """
    bx, by, bz = base
    _square_bands( model, F, base, LANTERN, lambda k: "sh_lamp_warm" if k == LANTERN_GLASS else IRON, s )
    for sx in ( -1.0, 1.0 ):
        for sy in ( -1.0, 1.0 ):
            a = np.array( ( bx + sx * 5.0 * s, by + sy * 5.0 * s, bz + 2.6 * s ) )
            b = np.array( ( bx + sx * 7.5 * s, by + sy * 7.5 * s, bz + 17.4 * s ) )
            _obox( model, F, tuple( ( a + b ) / 2 ), tuple( b - a ), ( 1.0, 0.0, 0.0 ),
                   ( float( np.linalg.norm( b - a ) ), 0.7 * s, 0.7 * s ), IRON )
    sphere( model, F.p( bx, by, bz + 26.9 * s ), 0.9 * s, IRON, sides=8, rings=4 )
    if hang:
        _loop( model, F.p( bx, by, bz + 28.7 * s ), F.y, np.array( ( 0.0, 0.0, 1.0 ) ), 1.1 * s, 1.1 * s, 0.25 * s,
               IRON, steps=8, sides=4 )
        top = bz + LANTERN_HANG_TOP * s
    else:
        revolve( model, F.p( bx, by, bz + 27.6 * s ), ( 0.0, 0.0, 1.0 ), ( ( 0.45 * s, 0.0 ), ( 0.0, 1.4 * s ) ), IRON,
                 sides=6 )
        top = bz + 29.0 * s
    return F.p( bx, by, bz + 10.0 * s ), top


def _lamp_column( H ):
    """ The lamp column's profile ( r, z ) up to the lantern's spigot at H: the moulded base, the shaft, the collars
    round the ladder bar and the capital. """
    return [ ( 9.0, 0.0 ), ( 9.0, 1.2 ), ( 8.2, 1.8 ), ( 7.6, 2.6 ), ( 7.8, 3.6 ), ( 7.0, 4.6 ), ( 7.0, 18.2 ),
             ( 7.6, 18.9 ), ( 7.6, 19.9 ), ( 6.5, 20.6 ), ( 5.6, 22.6 ), ( 4.7, 25.8 ), ( 4.2, 28.6 ), ( 4.0, 30.2 ),
             ( 4.5, 30.8 ), ( 4.5, 32.0 ), ( 3.7, 32.6 ), ( 2.8, H - 19.0 ), ( 3.4, H - 18.3 ), ( 3.4, H - 16.7 ),
             ( 2.6, H - 16.0 ), ( 2.6, H - 12.6 ), ( 3.1, H - 12.0 ), ( 3.1, H - 10.0 ), ( 2.6, H - 9.4 ),
             ( 2.9, H - 7.2 ), ( 3.7, H - 5.4 ), ( 4.7, H - 4.2 ), ( 4.7, H - 3.2 ), ( 1.9, H - 2.6 ), ( 1.9, H ) ]


def lamp_post( model, e, n, z0, height=150, axis="e" ):
    """ A Victorian cast-iron lamp column, painted black, with its square lantern: a moulded base 18 across and 20 tall
    with a door in its side (facing along axis, "e" or "n"), a shaft tapering from 7.4 to 5.6 across, the
    lamplighter's ladder bar (24 across, along axis) under the capital, and the lantern on the spigot, its glass lit.
    height: the column's top, where the lantern stands (150, 12 ft 6 in; the lantern adds 29). Collision: one small
    "metal" box 10 across round the column, from the ground to its top: a player's box meets it before their boots reach
    the base, and shots meet it within an inch or two of the shaft. Returns the lamp's place (the lead puts a light
    there). """
    F = _axis_frame( e, n, z0, axis )
    H = float( height )
    revolve( model, ( e, n, z0 ), ( 0.0, 0.0, 1.0 ), _lamp_column( H ), IRON, sides=12, turn=math.pi / 12 )
    rod( model, F.p( 0.0, -12.0, H - 11.0 ), F.p( 0.0, 12.0, H - 11.0 ), 0.55, IRON, 6 )
    for s in ( -1.0, 1.0 ):
        sphere( model, F.p( 0.0, s * 12.0, H - 11.0 ), 1.0, IRON, sides=8, rings=4 )
    _obox( model, F, ( 0.0, 6.7, 11.4 ), ( 1.0, 0.0, 0.0 ), ( 0.0, 1.0, 0.0 ), ( 5.0, 0.85, 11.0 ), IRON )
    light, _ = _lantern( model, F, ( 0.0, 0.0, H ) )
    F.collide( model, -5.0, 5.0, -5.0, 5.0, 0.0, H, METAL )
    return tuple( float( v ) for v in light )


def wall_lantern( model, e, n, z, facing ):
    """ A small square street lantern (16 tall) hanging from a wrought-iron wall bracket: the wall plate, the arm
    reaching 13.5 out and curling down into a scroll, a curved brace under it, and the ring the lantern hangs from.
    ( e, n, z ): where the arm meets the wall face; facing: the way out from the wall. No collision. Returns the lamp's
    place (14.2 under the arm). """
    F = frame_for( e, n, z, facing )
    _obox( model, F, ( 0.0, 0.25, -2.0 ), ( 1.0, 0.0, 0.0 ), ( 0.0, 1.0, 0.0 ), ( 3.6, 0.5, 12.0 ), IRON )
    pts, rs = [ F.p( 0.0, 0.5, 0.0 ) ], [ 0.45 ]
    for k in range( 21 ):
        f = k / 20
        th, R = math.pi / 2 - 2.5 * math.pi * f, 1.2 - 0.75 * f
        pts.append( F.p( 0.0, 13.5 + R * math.cos( th ), -1.2 + R * math.sin( th ) ) )
        rs.append( 0.45 - 0.15 * f )
    tube( model, pts, rs, IRON, 6, caps=( False, True ) )
    tube( model, [ F.p( 0.0, 8.0 - 7.5 * math.cos( p ), -7.0 + 6.6 * math.sin( p ) )
                   for p in np.linspace( 0.0, math.pi / 2, 9 ) ], 0.35, IRON, 5 )
    _loop( model, F.p( 0.0, 12.5, 0.0 ), F.x, np.array( ( 0.0, 0.0, 1.0 ) ), 0.75, 0.75, 0.2, IRON, steps=8, sides=4 )
    rod( model, F.p( 0.0, 12.5, -0.75 ), F.p( 0.0, 12.5, -2.0 ), 0.18, IRON, 4 )
    light, _ = _lantern( model, F, ( 0.0, 12.5, -1.8 - LANTERN_HANG_TOP * 0.62 ), 0.62, hang=True )
    return tuple( float( v ) for v in light )


def bench( model, e, n, z0, facing ):
    """ A seaside bench 60 long: five seat slats and three back slats of weathered hardwood on two cast-iron ends 52
    apart (each a front and a back leg with a stretcher, the seat rail, the back support, and an arm on a scrolled
    support ending in a knuckle), and a tie rod between the ends. Seat 17.5 high and 17 deep, the back's top 32 up.
    facing: the way someone sitting on it looks. Collision: "wood" boxes round the seat and round the back. Returns
    the seat's height. """
    F = frame_for( e, n, z0, facing )
    _grain( model, "sh_planks_grey" )
    for x in ( -26.0, 26.0 ):
        def bar( y0, h0, y1, h1, size=( 0.9, 1.7 ) ):
            a, b = np.array( ( x, y0, h0 ) ), np.array( ( x, y1, h1 ) )
            _obox( model, F, tuple( ( a + b ) / 2 ), tuple( b - a ), ( 1.0, 0.0, 0.0 ),
                   ( float( np.linalg.norm( b - a ) ), *size ), IRON )

        bar( 9.5, -0.3, 8.6, 16.6 )                         # the front leg
        bar( -12.5, -0.3, -7.6, 16.6 )                      # the back leg
        bar( 10.3, 16.2, -8.4, 15.3 )                       # the seat rail
        bar( -7.4, 15.0, -12.75, 32.5 )                     # the back support
        bar( -10.7, 24.6, 9.5, 25.0, ( 2.0, 1.1 ) )         # the arm
        bar( 9.22, 5.0, -11.0, 5.0, ( 0.9, 1.3 ) )          # the stretcher
        sphere( model, F.p( x, 9.6, 25.0 ), 1.0, IRON, sides=8, rings=4 )
        tube( model, [ F.p( x, 9.0 + 0.3 * t + 1.4 * math.sin( 2 * math.pi * t ), 16.6 + 7.8 * t )
                       for t in np.linspace( 0.0, 1.0, 11 ) ], 0.55, IRON, 5 )
        for y in ( 9.4, -12.4 ):
            F.box( model, x - 0.9, x + 0.9, y - 1.4, y + 1.4, 0.0, 0.5, IRON, skip=( "bottom", ) )
    for y in ( 7.3, 3.95, 0.6, -2.75, -6.1 ):
        _obox( model, F, ( 0.0, y, 16.2 + ( y - 9.8 ) * 0.05 + 1.4 ), ( 1.0, 0.0, 0.0 ), ( 0.0, 1.0, 0.05 ),
               ( 60.0, 2.75, 1.1 ), "sh_planks_grey" )
    along, front = np.array( ( -0.2916, 0.9565 ) ), np.array( ( 0.9565, 0.2916 ) )
    foot = np.array( ( -7.6, 15.6 ) )
    for s in ( 6.35, 10.65, 14.95 ):
        y, h = foot + along * s + front * 1.35
        _obox( model, F, ( 0.0, y, h ), ( 1.0, 0.0, 0.0 ), ( 0.0, along[0], along[1] ), ( 60.0, 3.5, 1.0 ),
               "sh_planks_grey" )
    rod( model, F.p( -26.0, -0.9, 5.0 ), F.p( 26.0, -0.9, 5.0 ), 0.4, IRON, 5 )
    F.collide( model, -30.0, 30.0, -12.5, 9.8, 0.0, 17.5, WOOD )
    y, h = foot + along * 10.65 + front * 0.5
    _obox( model, F, ( 0.0, y, h ), ( 1.0, 0.0, 0.0 ), ( 0.0, along[0], along[1] ), ( 60.0, 13.0, 2.2 ), None, WOOD )
    return z0 + 17.5


# A granite trough's half-width, half-length and height (an old horse trough, 610 x 1220 x 510 mm)
TROUGH = ( 12.0, 24.0, 20.0 )
_GRANITE = {}


def _granite_blocks():
    """ The whole blocks of the sh_granite picture ( column, row, length, height ) in pixels of its 1024 (from the
    left and the top), from stillhouse_materials' own layout of its courses; [] while that isn't there. """
    if "blocks" not in _GRANITE:
        blocks = []
        try:
            import stillhouse_materials as SM
            block, u, v, length, rowh = SM._ashlar_layout( 1024 )[:5]
            ids, first = np.unique( block.ravel(), return_index=True )
            for f in first:
                y, x = divmod( int( f ), 1024 )
                x0 = ( x + 0.5 - float( u.flat[f] ) ) % 1024
                y0 = y + 0.5 - float( v.flat[f] )
                L, h = float( length.flat[f] ), float( rowh.flat[f] )
                if x0 + L <= 1024.0 + 1e-6 and y0 >= -1e-6 and y0 + h <= 1024.0 + 1e-6:
                    blocks.append( ( x0, y0, L, h ) )
        except Exception:
            blocks = []
        _GRANITE["blocks"] = blocks
    return _GRANITE["blocks"]


def _granite_face( model, F, pts, towards, up, origin, at, k ):
    """ A face of the trough in sh_granite, given one block of the picture: at ( column, row ) of the picture is at
    origin (local), the picture's rows run down against up (local) and its columns to the right of it seen from in
    front, k px to the inch. Without the picture's layout (k None), map_kit maps it. """
    if k is None:
        _fpoly_d( model, F, "sh_granite", pts, towards )
        return
    N, U = _unit( _world( F, towards ) ), _unit( _world( F, up ) )
    U = _unit( U - N * np.dot( U, N ) )
    right = np.cross( U, N )
    O = F.p( *origin )
    world = [ F.p( *p ) for p in pts ]
    uv = [ ( ( at[0] + np.dot( P - O, right ) * k ) / 1024.0, 1.0 - ( at[1] - np.dot( P - O, U ) * k ) / 1024.0 )
           for P in world ]
    outward( model, "sh_granite", world, N, uv=uv )


def trough( model, e, n, z0, axis="n" ):
    """ A granite trough (an old horse trough, now planted), 48 x 24 x 20, cut from one block: its sides battered in a
    little, a chamfer round the top, a rim 2.6 wide, and earth and grass 2.5 under the rim. Its faces take one dressed
    block of the sh_granite picture (its tooled margin and picked face) at the texture's own scale. Its length along
    axis ("n" or "e"). Collision: one box, "default" (stone). Returns its top. """
    F = _axis_frame( e, n, z0, axis )
    hw, hl, H = TROUGH
    blocks = _granite_blocks()
    k, bx, by, L, bh = None, 0.0, 0.0, 0.0, 0.0
    if blocks:
        inset = 2.37                                    # px: inside the cement joint round the block
        scored = sorted( ( ( min( 6.4, ( b[2] - 2 * inset ) / ( 2 * hl ), ( b[3] - 2 * inset ) / 19.2 ), b )
                           for b in blocks ), key=lambda t: -t[0] )
        k, ( bx, by, L, bh ) = pick( scored[:6], "trough", e, n, z0 )
    mid = bx + L / 2
    top_row, low_row = by + 2.37, by + bh - 2.37
    bw, bl = hw - 0.6, hl - 0.6                         # the batter's top at 19.2
    cw, cl = hw - 1.4, hl - 1.4                         # the chamfer's top at 20
    ow, ol = hw - 4.0, hl - 4.0                         # the opening
    for s in ( -1.0, 1.0 ):
        # the long sides and the ends, battered in by 0.6
        _granite_face( model, F, [ ( s * hw, -hl, 0.0 ), ( s * hw, hl, 0.0 ), ( s * bw, bl, 19.2 ), ( s * bw, -bl, 19.2 ) ],
                       ( s * 19.2, 0.0, 0.6 ), ( -s * 0.6, 0.0, 19.2 ), ( s * hw, 0.0, 0.0 ), ( mid, low_row ), k )
        end_mid = bx + 2.37 + hw * k if ( k and s > 0 ) else ( bx + L - 2.37 - hw * k if k else 0.0 )
        _granite_face( model, F, [ ( -hw, s * hl, 0.0 ), ( hw, s * hl, 0.0 ), ( bw, s * bl, 19.2 ), ( -bw, s * bl, 19.2 ) ],
                       ( 0.0, s * 19.2, 0.6 ), ( 0.0, -s * 0.6, 19.2 ), ( 0.0, s * hl, 0.0 ), ( end_mid, low_row ), k )
        # the chamfers
        _granite_face( model, F, [ ( s * bw, -bl, 19.2 ), ( s * bw, bl, 19.2 ), ( s * cw, cl, H ), ( s * cw, -cl, H ) ],
                       ( s, 0.0, 1.0 ), ( -s, 0.0, 1.0 ), ( s * cw, 0.0, H ), ( mid, top_row ), k )
        _granite_face( model, F, [ ( -bw, s * bl, 19.2 ), ( bw, s * bl, 19.2 ), ( cw, s * cl, H ), ( -cw, s * cl, H ) ],
                       ( 0.0, s, 1.0 ), ( 0.0, -s, 1.0 ), ( 0.0, s * cl, H ), ( mid, top_row ), k )
        # the rim
        _granite_face( model, F, [ ( s * cw, -cl, H ), ( s * cw, cl, H ), ( s * ow, ol, H ), ( s * ow, -ol, H ) ],
                       ( 0.0, 0.0, 1.0 ), ( s, 0.0, 0.0 ), ( s * cw, 0.0, H ), ( mid, top_row ), k )
        _granite_face( model, F, [ ( -cw, s * cl, H ), ( cw, s * cl, H ), ( ow, s * ol, H ), ( -ow, s * ol, H ) ],
                       ( 0.0, 0.0, 1.0 ), ( 0.0, s, 0.0 ), ( 0.0, s * cl, H ), ( mid, top_row ), k )
        # the inside, down to the earth
        _granite_face( model, F, [ ( s * ow, -ol, H ), ( s * ow, ol, H ), ( s * ow, ol, H - 2.5 ), ( s * ow, -ol, H - 2.5 ) ],
                       ( -s, 0.0, 0.0 ), ( 0.0, 0.0, 1.0 ), ( s * ow, 0.0, H ), ( mid, top_row ), k )
        _granite_face( model, F, [ ( -ow, s * ol, H ), ( ow, s * ol, H ), ( ow, s * ol, H - 2.5 ), ( -ow, s * ol, H - 2.5 ) ],
                       ( 0.0, -s, 0.0 ), ( 0.0, 0.0, 1.0 ), ( 0.0, s * ol, H ), ( mid, top_row ), k )
    _fpoly_d( model, F, "sh_grass", [ ( -ow, -ol, H - 2.5 ), ( ow, -ol, H - 2.5 ), ( ow, ol, H - 2.5 ), ( -ow, ol, H - 2.5 ) ],
              ( 0.0, 0.0, 1.0 ) )
    F.collide( model, -hw, hw, -hl, hl, 0.0, H, "default" )
    return z0 + H


# A sack truck's wheel ( r, along its axle ): the tyre, and the steel centre's two halves
BARROW_TYRE = ( ( 3.2, -1.65 ), ( 4.4, -1.65 ), ( 4.95, -1.25 ), ( 5.1, -0.5 ), ( 5.1, 0.5 ), ( 4.95, 1.25 ),
                ( 4.4, 1.65 ), ( 3.2, 1.65 ) )
BARROW_HUB = ( ( ( 0.0, -1.9 ), ( 1.3, -1.9 ), ( 1.3, -1.1 ), ( 3.2, -1.1 ), ( 3.2, -1.65 ) ),
               ( ( 3.2, 1.65 ), ( 3.2, 1.1 ), ( 1.3, 1.1 ), ( 1.3, 1.9 ), ( 0.0, 1.9 ) ) )


def barrow( model, e, n, z0, facing ):
    """ A sack truck (a porter's barrow) parked upright on its toe plate and wheels: a red tubular steel frame 15 wide
    and 48 tall, leaning back to its handles (rubber grips), three cross tubes, the steel toe plate with its gussets
    and lip, and two 10 in wheels with rubber tyres on an axle behind. facing: the way the toe plate points.
    Collision: one box, "metal". Returns its top. """
    F = frame_for( e, n, z0, facing )
    red = "sh_paint_red"
    for x in ( -7.5, 7.5 ):
        path, _ = _bend_path( [ F.p( x, 0.0, 0.5 ), F.p( x, -6.2, 44.0 ), F.p( x, -9.6, 48.2 ) ], 3.0, 4 )
        tube( model, path, 0.6, red, 6, caps=( True, True ) )
        grip = _unit( ( -3.4, 4.2 ) )
        rod( model, F.p( x, -9.6 - grip[0] * 3.9, 48.2 - grip[1] * 3.9 ),
             F.p( x, -9.6 + grip[0] * 0.25, 48.2 + grip[1] * 0.25 ), 0.75, "sh_rubber", 6, caps=( True, True ) )
        RP._side_prism( model, F, [ ( 0.3, 0.3 ), ( 3.6, 0.3 ), ( -0.2, 4.2 ) ], x - 0.15, x + 0.15,
                        lambda k: "sh_steel", "sh_steel" )
        model.beam( F.p( x, -0.75, 9.5 ), F.p( x, -4.5, 5.1 ), ( 0.3, 2.2 ), red )
    for h in ( 12.0, 24.0, 36.0 ):
        y = -6.2 * ( h - 0.5 ) / 43.5
        rod( model, F.p( -7.5, y, h ), F.p( 7.5, y, h ), 0.45, red, 6 )
    F.box( model, -7.75, 7.75, 0.0, 8.0, 0.0, 0.3, "sh_steel", skip=( "bottom", ) )
    F.box( model, -7.75, 7.75, 7.7, 8.0, 0.3, 1.1, "sh_steel" )
    rod( model, F.p( -13.5, -4.5, 5.1 ), F.p( 13.5, -4.5, 5.1 ), 0.5, "sh_steel", 6, caps=( True, True ) )
    for x in ( -11.8, 11.8 ):
        c = F.p( x, -4.5, 5.1 )
        revolve( model, c, F.x, BARROW_TYRE, "sh_rubber", sides=12 )
        for hub in BARROW_HUB:
            revolve( model, c, F.x, hub, "sh_steel", sides=12 )
    F.collide( model, -13.5, 13.5, -10.0, 8.0, 0.0, 48.8, METAL )
    return z0 + 48.8


def ladder( model, e, n, z0, z1, facing, paint="sh_steel", grabs=True ):
    """ A steel ladder fixed to a wall (a quay's face) from z0 up to its top z1: two flat stringers 7 out from the
    wall, round rungs a foot apart, stays to plates bolted to the wall every 6 ft, and, with grabs, the stringers carried
    on 30 over the top as hand hoops bent back over the edge and down to the ground behind it. ( e, n ): the wall face
    at the ladder's middle; facing: the way out from the wall. No collision. Returns its top (the hoops'). """
    F = frame_for( e, n, z0, facing )
    h = z1 - z0
    top = h - 6.0 if grabs else h
    for x in ( -8.5, 8.5 ):
        F.box( model, x - 0.25, x + 0.25, 5.75, 8.25, 0.0, top, paint, skip=( "bottom", ) )
    z = h - 3.0
    while z >= 6.0:
        rod( model, F.p( -8.5, 7.0, z ), F.p( 8.5, 7.0, z ), 0.5, paint, 6 )
        z -= 12.0
    z = 36.0
    while z <= h - 12.0:
        for x in ( -8.5, 8.5 ):
            F.box( model, x - 0.25, x + 0.25, 0.4, 5.75, z - 1.0, z + 1.0, paint )
            F.box( model, x - 1.5, x + 1.5, 0.0, 0.4, z - 2.0, z + 2.0, paint )
        z += 72.0
    if not grabs:
        return z1
    for x in ( -8.5, 8.5 ):
        path, _ = _bend_path( [ F.p( x, 7.0, h - 6.0 ), F.p( x, 7.0, h + 30.0 ), F.p( x, -5.0, h + 30.0 ),
                                F.p( x, -5.0, h ) ], 6.0, 5 )
        tube( model, path, 0.75, paint, 8, caps=( False, True ) )
    return z1 + 30.75


# ---------------------------------------------------------------------------------------------------------------------
# Preview: every prop on a sketch of the distillery's ground at the design doc's levels (the ground, the sea, the
# condensers' stands and the harled wall are only for the pictures)

SHOWCASE_SEA_Z = -195.0
SHOWCASE_BED = -330.0                       # the flat bed east of the pier
SHOWCASE_BEACH = ( ( -2600.0, -330.0 ), ( -2100.0, -300.0 ), ( -1760.0, -190.0 ), ( -1480.0, -150.0 ),
                   ( -1350.0, -150.0 ) )   # ( n, z ) west of the pier
SHOWCASE_SOUTH = -3400.0                    # the sketch's ground and sea reach this far out
SHOWCASE_STAND = 90.0                       # the condensers' stands: their tails 18 up must fall to the safe's inlets
SHOWCASE_TOP = ( -1650.0, 1450.0, -2650.0, 1050.0 )


def _slab( model, paint, e0, e1, n0, n1, z, under=None, depth=0.0 ):
    """ A level floor at z (the preview's ground), with its edge faces down to z - depth. """
    model.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ] )
    if depth > 0:
        model.box( ( e0, n0, z - depth ), ( e1, n1, z ), { "default": under or paint, "+z": None, "-z": None } )


def _beach_z( n ):
    ns, zs = zip( *SHOWCASE_BEACH )
    return float( np.interp( n, ns, zs ) )


def _beach_paint( n ):
    return "sh_shingle" if n >= -1480 else "sh_sand" if n >= -1700 else "sh_sand_wet" if n >= -1820 else "sh_seabed"


def _slope( model, e0, e1, rows ):
    """ The beach from e0 to e1: a strip of quads through rows (n, ascending), each painted by its middle. """
    for a, b in zip( rows, rows[1:] ):
        model.polygon( _beach_paint( ( a + b ) / 2 ), [ ( e0, a, _beach_z( a ) ), ( e1, a, _beach_z( a ) ),
                                                        ( e1, b, _beach_z( b ) ), ( e0, b, _beach_z( b ) ) ] )


def _stand( model, e, n, top, half=26.0 ):
    """ A steel stand for a condenser: four legs and a chequer-plate deck at top. Collision: one box, "metal". """
    for se in ( -1, 1 ):
        for sn in ( -1, 1 ):
            x, y = e + se * ( half - 3.0 ), n + sn * ( half - 3.0 )
            model.box( ( x - 2.0, y - 2.0, 0.0 ), ( x + 2.0, y + 2.0, top - 6.0 ),
                       { "default": "sh_steel_green", "+z": None, "-z": None } )
    model.box( ( e - half, n - half, top - 6.0 ), ( e + half, n + half, top - 1.0 ),
               { "default": "sh_steel_green", "+z": None } )
    model.box( ( e - half, n - half, top - 1.0 ), ( e + half, n + half, top ),
               { "default": "sh_steel_green", "+z": "sh_chequer", "-z": None } )
    model.collision_box( ( e - half, n - half, 0.0 ), ( e + half, n + half, top ), METAL )


def _lyne_link( model, end, inlet ):
    """ A lyne arm carried on at its fall from its end flange to over a condenser's vapour inlet, then down into it. """
    end, inlet = np.asarray( end, float ), np.asarray( inlet, float )
    z = end[2] - np.linalg.norm( inlet[:2] - end[:2] ) * LYNE_FALL
    pipe( model, [ end, ( inlet[0], inlet[1], z ), inlet ], LYNE_R, "sh_copper", flanges=False )


def showcase():
    """ [ ( name, model ) ]: every prop on a sketch of the distillery at the design doc's levels. North of the yard
    (z 0, n -900..300): the tun room (the mash tun, two washbacks and a pipe run), the still house (the wash and spirit
    stills, their condensers on stands with the tails falling to the spirit safe) and the warehouse (three dunnage
    stows, loose casks in the aisles). In the yard: the tanker, two cars and the van, stacks of goods,
    peat, a cask pyramid and a rank, a lamp post and a harled wall with its bench, lantern, trough and barrow. The shore
    walk (z -50): the creel boats ashore, creels, fish boxes, a rope and buoys. The beach: two dinghies. The pier
    (e -150..150 out to n -1950): bollards, the crane, a lamp, the ladder and gear. Afloat (z -195): the puffer across
    the pier head and a creel boat alongside. """
    out = []

    def prop( name ):
        m = K.Model()
        out.append( ( name, m ) )
        return m

    # the ground
    g = prop( "ground (preview)" )
    _slab( g, "sh_floorboards", -1250.0, -520.0, 300.0, 1000.0, 0.0 )
    _slab( g, "sh_floor_tiles", -520.0, 520.0, 300.0, 1000.0, 0.0 )
    _slab( g, "sh_dunnage", 520.0, 1300.0, 300.0, 1000.0, 0.0 )
    for e0, e1 in ( ( -1600.0, -1250.0 ), ( 1300.0, 1400.0 ) ):
        _slab( g, "sh_setts", e0, e1, 300.0, 1000.0, 0.0 )
    _slab( g, "sh_setts", -1600.0, 1400.0, -900.0, 300.0, 0.0, "sh_granite", 50.0 )
    _slab( g, "sh_setts", -1600.0, 1400.0, -1350.0, -900.0, -50.0, "sh_granite", -50.0 - SHOWCASE_BED )
    _slope( g, -1600.0, -150.0, [ SHOWCASE_SOUTH, -2600.0, -2350.0, -2100.0, -1950.0, -1820.0, -1760.0, -1700.0,
                                  -1600.0, -1480.0, -1350.0 ] )
    _slab( g, "sh_seabed", -150.0, 1400.0, SHOWCASE_SOUTH, -1350.0, SHOWCASE_BED )
    rows = [ -2600.0, -2350.0, -2100.0, -1950.0 ]     # (further out the beach is down at the bed)
    for a, b in zip( rows, rows[1:] ):                  # the beach's edge over the flat bed, beyond the pier head
        pts = _dedupe( [ ( -150.0, a, SHOWCASE_BED ), ( -150.0, b, SHOWCASE_BED ), ( -150.0, b, _beach_z( b ) ),
                         ( -150.0, a, _beach_z( a ) ) ] )
        g.polygon( "sh_seabed", pts, normal=( 1.0, 0.0, 0.0 ) )
    g.box( ( -150.0, -1950.0, SHOWCASE_BED ), ( 150.0, -1350.0, -170.0 ),
           { "default": "sh_granite_weed", "+z": None, "-z": None, "+n": None } )
    g.box( ( -150.0, -1950.0, -170.0 ), ( 150.0, -1350.0, -50.0 ),
           { "default": "sh_granite", "+z": "sh_setts", "-z": None, "+n": None } )
    g.box( ( -800.0, -700.0, 0.0 ), ( -300.0, -680.0, 220.0 ), { "default": "sh_harl", "-z": None } )
    sea = prop( "sea (preview)" )
    for e0 in range( -1600, 1400, 500 ):
        for n0 in range( int( SHOWCASE_SOUTH ), -1350, 500 ):
            e1, n1 = min( e0 + 500, 1400 ), min( n0 + 500, -1350 )
            sea.polygon( "sh_sea", [ ( e0, n0, SHOWCASE_SEA_Z ), ( e1, n0, SHOWCASE_SEA_Z ),
                                     ( e1, n1, SHOWCASE_SEA_Z ), ( e0, n1, SHOWCASE_SEA_Z ) ] )

    # the tun room
    mash_tun( prop( "mash_tun" ), -880.0, 790.0, 0.0 )
    for e in ( -1080.0, -740.0 ):
        washback( prop( "washback" ), e, 450.0, 0.0 )
    pipe( prop( "pipe" ), [ ( -1220.0, 980.0, 0.0 ), ( -1220.0, 980.0, 150.0 ), ( -560.0, 980.0, 150.0 ),
                            ( -560.0, 600.0, 150.0 ), ( -560.0, 600.0, 0.0 ) ] )

    # the still house: the stills' lyne arms run north to their condensers, whose tails fall to the safe
    wash_end = pot_still( prop( "pot_still" ), -300.0, 560.0, 0.0, "wash", ( 0.0, 1.0 ), 120 )
    spirit_end = pot_still( prop( "pot_still" ), -20.0, 560.0, 0.0, "spirit", ( 0.0, 1.0 ), 100 )
    stands = prop( "condenser stand (preview)" )
    _stand( stands, -300.0, 770.0, SHOWCASE_STAND )
    _stand( stands, -20.0, 720.0, SHOWCASE_STAND )
    wash_in, wash_tail = condenser( prop( "condenser" ), -300.0, 770.0, SHOWCASE_STAND, 120, 16 )
    spirit_in, spirit_tail = condenser( prop( "condenser" ), -20.0, 720.0, SHOWCASE_STAND, 95, 14 )
    spirit_safe( prop( "spirit_safe" ), 200.0, 420.0, 0.0, "-n" )
    m = prop( "pipe" )
    _lyne_link( m, wash_end, wash_in )
    _lyne_link( m, spirit_end, spirit_in )
    for tail, e in ( ( wash_tail, 206.0 ), ( spirit_tail, 194.0 ) ):     # the safe's inlets, at x +-6 on its lid
        pipe( m, [ tail, ( e, tail[1], tail[2] - 1.5 ), ( e, 424.0, 103.0 ), ( e, 424.0, 98.0 ) ], 1.5, "sh_copper",
              flanges=False )

    # the warehouse: stows, and loose casks in the aisles
    cask_stow( prop( "cask_stow" ), 560.0, 1260.0, 930.0, 0.0, 3, 1, "hogshead", 1 )
    cask_stow( prop( "cask_stow" ), 560.0, 1260.0, 690.0, 0.0, 3, 2, "barrel", 2 )
    cask_stow( prop( "cask_stow" ), 560.0, 1100.0, 400.0, 0.0, 2, 1, "butt", 3 )
    cask( prop( "cask" ), 640.0, 850.0, 0.0, "e", "hogshead", 3 )
    cask( prop( "cask" ), 760.0, 850.0, 0.0, "n", "barrel", 5, standing=True )
    cask( prop( "cask" ), 880.0, 850.0, 0.0, "n", "butt", dark=True )
    cask( prop( "cask" ), 1000.0, 850.0, 0.0, "n", "hogshead", "plain", standing=True )
    cask( prop( "cask" ), 1180.0, 540.0, 0.0, "n", "barrel", 7 )

    # the yard
    tanker( prop( "tanker" ), -800.0, -80.0, 0.0, "+e" )
    van( prop( "van" ), -350.0, -80.0, "+n", "sh_paint_white" )
    car( prop( "car" ), -230.0, -80.0, "+n", "sh_paint_blue" )
    car( prop( "car" ), -110.0, -80.0, "-n", "sh_paint_red", kind="estate" )
    sack_stack( prop( "sack_stack" ), 470.0, -250.0, 0.0, 4, "n" )
    sack_stack( prop( "sack_stack" ), 470.0, -130.0, 0.0, 3, "e" )
    pallet_stack( prop( "pallet_stack" ), 600.0, -250.0, 0.0, 6 )
    pallet( prop( "pallet" ), 600.0, -120.0, 0.0, "e" )
    for ( e, n ), paint in zip( ( ( 720.0, -300.0 ), ( 746.0, -300.0 ), ( 733.0, -277.0 ), ( 690.0, -290.0 ) ),
                                ( "sh_paint_blue", "sh_paint_red", "sh_paint_yellow", "sh_rust" ) ):
        drum( prop( "drum" ), e, n, 0.0, paint )
    peat_stack( prop( "peat_stack" ), -1300.0, 100.0, 0.0 )
    cask_pyramid( prop( "cask_pyramid" ), 900.0, 100.0, 0.0, "n", 3, seed=4 )
    cask_rank( prop( "cask_rank" ), 1000.0, 1350.0, 150.0, 0.0, seed=5 )
    lamp_post( prop( "lamp_post" ), 150.0, -700.0, 0.0, 150 )
    bench( prop( "bench" ), -640.0, -716.0, 0.0, "-n" )
    wall_lantern( prop( "wall_lantern" ), -450.0, -700.0, 160.0, "-n" )
    trough( prop( "trough" ), -380.0, -730.0, 0.0, "e" )
    barrow( prop( "barrow" ), -560.0, -714.0, 0.0, "-n" )

    # the shore walk
    creel_boat( prop( "creel_boat (trailer)" ), -650.0, -1100.0, -50.0, "+e" )
    creel_boat( prop( "creel_boat (blocks)" ), -1150.0, -1100.0, -50.0, "-e", "sh_hull_red", trailer=False )
    rowing_boat( prop( "rowing_boat (upturned)" ), -1150.0, -1270.0, -50.0, "+e", upturned=True )
    creels( prop( "creels" ), -320.0, -1000.0, -50.0, 6, "e" )
    creels( prop( "creels" ), -320.0, -1120.0, -50.0, 2, "n" )
    fish_boxes( prop( "fish_boxes" ), -200.0, -1000.0, -50.0, 5, "blue" )
    fish_boxes( prop( "fish_boxes" ), -170.0, -1060.0, -50.0, 3, "orange", "e" )
    fish_boxes( prop( "fish_boxes" ), -230.0, -1080.0, -50.0, 4, "mixed" )
    rope_coil( prop( "rope_coil" ), -420.0, -1260.0, -50.0, 14 )
    for ( e, n ), colour in zip( ( ( -380.0, -1230.0 ), ( -360.0, -1270.0 ), ( -400.0, -1300.0 ) ),
                                 ( "orange", "red", "yellow" ) ):
        buoy( prop( "buoy" ), e, n, -50.0, colour )

    # the beach
    rowing_boat( prop( "rowing_boat" ), -700.0, -1415.0, -150.0, "+e" )
    rowing_boat( prop( "rowing_boat (heeled)" ), -1000.0, -1420.0, -150.0, "-e", heel=1 )

    # the pier
    for e, n, kind in ( ( 128.0, -1520.0, "double" ), ( -128.0, -1640.0, "double" ), ( 128.0, -1760.0, "single" ),
                        ( 128.0, -1930.0, "single" ), ( -130.0, -1930.0, "single" ) ):
        bollard( prop( "bollard" ), e, n, -50.0, kind, "n" )
    harbour_crane( prop( "harbour_crane" ), 100.0, -1430.0, -50.0, "+e" )
    lamp_post( prop( "lamp_post" ), -120.0, -1820.0, -50.0, 150, "n" )
    rope_coil( prop( "rope_coil" ), -60.0, -1880.0, -50.0, 16 )
    rope_coil( prop( "rope_coil" ), 60.0, -1870.0, -50.0, 11 )
    buoy( prop( "buoy" ), -90.0, -1900.0, -50.0, "white" )
    buoy( prop( "buoy" ), 90.0, -1905.0, -50.0, "blue" )
    fish_boxes( prop( "fish_boxes" ), 60.0, -1700.0, -50.0, 4, "mixed", "e" )
    creels( prop( "creels" ), -70.0, -1700.0, -50.0, 4, "n" )
    ladder( prop( "ladder" ), 150.0, -1850.0, -300.0, -50.0, "+e" )

    # afloat
    puffer( prop( "puffer" ), 0.0, -2072.0, SHOWCASE_SEA_Z, "+e" )
    creel_boat( prop( "creel_boat (afloat)" ), 218.0, -1600.0, SHOWCASE_SEA_Z, "-n", "sh_hull_white", trailer=False,
                afloat=True )
    return out


SHOWCASE_VIEWS = [   # ( name, eye, target, horizontal field of view ), plan inches
    ( "overview", ( -1900.0, -2900.0, 1700.0 ), ( -100.0, -300.0, 0.0 ), 70 ),
    ( "still_house", ( -60.0, 200.0, 90.0 ), ( -100.0, 650.0, 170.0 ), 90 ),
    ( "stills_side", ( -620.0, 420.0, 150.0 ), ( -100.0, 640.0, 160.0 ), 85 ),
    ( "safe", ( 200.0, 330.0, 75.0 ), ( 200.0, 430.0, 72.0 ), 70 ),
    ( "tun_room", ( -560.0, 320.0, 130.0 ), ( -900.0, 650.0, 40.0 ), 85 ),
    ( "warehouse", ( 540.0, 790.0, 64.0 ), ( 1100.0, 810.0, 40.0 ), 85 ),
    ( "warehouse_b", ( 1250.0, 540.0, 120.0 ), ( 800.0, 760.0, 40.0 ), 80 ),
    ( "yard", ( 300.0, -850.0, 120.0 ), ( -300.0, -250.0, 40.0 ), 85 ),
    ( "tanker", ( -480.0, 120.0, 100.0 ), ( -800.0, -80.0, 60.0 ), 80 ),
    ( "wall", ( -300.0, -880.0, 80.0 ), ( -470.0, -700.0, 60.0 ), 85 ),
    ( "goods", ( 800.0, -450.0, 110.0 ), ( 450.0, -150.0, 30.0 ), 80 ),
    ( "cask_yard", ( 1150.0, -200.0, 90.0 ), ( 850.0, 120.0, 40.0 ), 75 ),
    ( "shore", ( -250.0, -1300.0, 20.0 ), ( -850.0, -1080.0, 0.0 ), 80 ),
    ( "pier", ( 0.0, -1380.0, 20.0 ), ( 0.0, -1800.0, -40.0 ), 85 ),
    ( "puffer", ( 600.0, -1700.0, -50.0 ), ( 0.0, -2072.0, -150.0 ), 70 ),
    ( "puffer_deck", ( -60.0, -1920.0, 30.0 ), ( 80.0, -2072.0, -40.0 ), 85 ),
    ( "harbour", ( 900.0, -2900.0, -80.0 ), ( 0.0, -1800.0, -120.0 ), 70 ),
    ( "moored", ( 520.0, -1430.0, -110.0 ), ( 200.0, -1620.0, -175.0 ), 70 ),
    ( "creel_deck", ( 330.0, -1500.0, 40.0 ), ( 215.0, -1600.0, -170.0 ), 75 ),
    ( "beach", ( -500.0, -1700.0, -120.0 ), ( -850.0, -1450.0, -140.0 ), 75 ),
    ( "ladder", ( 400.0, -1880.0, -100.0 ), ( 150.0, -1880.0, -150.0 ), 70 ),
]


def preview( out_dir, views=None ):
    """ Renders the showcase into out_dir (its perspective views and a top view) and prints each prop's triangles and
    collision. """
    import stillhouse_preview as V

    items = showcase()
    tally = {}
    for name, m in items:
        t = tally.setdefault( name, [ 0, 0, 0, 0 ] )
        t[0] += 1
        t[1] += m.triangle_count()
        t[2] += len( m.boxes )
        t[3] += len( m.hulls )
    print( f"{'prop':34s} {'count':>5s} {'triangles':>10s} {'each':>7s} {'boxes':>6s} {'hulls':>6s}" )
    for name, ( count, tris, boxes, hulls ) in tally.items():
        print( f"{name:34s} {count:5d} {tris:10d} {tris // count:7d} {boxes:6d} {hulls:6d}" )
    total = sum( m.triangle_count() for _, m in items )
    print( f"{'total':34s} {len( items ):5d} {total:10d}" )
    models = [ m for _, m in items ]
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    opaque, glass, sea = V.triangles( models ), V.triangles( models, glass=True ), V.triangles( models, sea=True )
    V.top_down( opaque, glass, SHOWCASE_TOP, 4.0, sea=sea ).save( out / "top.png" )
    print( f"wrote {out / 'top.png'}" )
    for name, eye, target, fov in SHOWCASE_VIEWS:
        if views and name not in views:
            continue
        V.perspective( opaque, glass, eye, target, fov=fov, sea=sea ).save( out / f"{name}.png" )
        print( f"wrote {out / name}.png" )


def main( argv=None ):
    parser = argparse.ArgumentParser( description="Stillhouse's props: renders a showcase of them (writes no assets)." )
    parser.add_argument( "--preview", metavar="DIR", required=True, help="where to write the renders" )
    parser.add_argument( "views", nargs="*", help="only these views (" + ", ".join(
        v[0] for v in SHOWCASE_VIEWS ) + "); the top view is always written" )
    args = parser.parse_args( argv )
    preview( args.preview, args.views )


if __name__ == "__main__":
    main()
