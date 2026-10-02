"""
Reef Hall's aquarium animals: a grey reef shark, a reef manta, a yellow tang and a blue-green chromis, built from
numbers, with no samples or downloads. For each it writes, into Assets/models/maps/reefhall/fauna/:

  - <name>.obj: the mesh, smooth-shaded, every part a closed solid wound outwards;
  - <name>_color.png: its colours, painted with numpy;
  - <name>.vmat: on shaders/hc1_fish.shader, with the swimming wave's settings for that animal;
  - <name>.vmdl: render only, no collision (they're behind glass; Code/Maps/TankFauna.cs swims them).

Model space is the animal's own: +X forward (the nose), +Y to its left, +Z up, the middle of its body at the origin.
The OBJ writes ( x, y, z ) as ( y, z, x ), as Tools/map_kit.py does, since ModelDoc reads an OBJ as Y-up.

Sizes are real ones in inches (the game's unit):
  - grey reef shark (Carcharhinus amblyrhynchos): 1.8 m nose to tail, 72;
  - reef manta (Mobula alfredi): 3.5 m across the wings, 140;
  - yellow tang (Zebrasoma flavescens): 20 cm, 8;
  - blue-green chromis (Chromis viridis): 12 cm, 5.

Bodies are lofted along X through super-elliptic sections; fins are thin lens-shaped solids (thickest at mid-chord,
meeting in a sharp edge all round) whose roots sit inside the body. The textures are unwrapped so they read the same
whichever way up the importer takes an OBJ's V: a fish's body runs along U (0 to 0.6, nose to tail) and round its girth
along V (belly, one side, the back, the other side, belly), and its fins have U 0.6 to 1 from root to tip. The manta's
top is U 0 to 0.5 and its underside 0.5 to 1, nose to tail, with V across the span.

    python Tools/reefhall_fauna.py                 writes everything
    python Tools/reefhall_fauna.py --preview <dir> also renders each animal with Blender (if it's installed)
"""

import argparse
import math
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path( __file__ ).resolve().parent.parent
OUT = ROOT / "Assets" / "models" / "maps" / "reefhall" / "fauna"
RESOURCE = "models/maps/reefhall/fauna"
TEXTURE = 512


# ---------------------------------------------------------------------------------------------------------------------
# Meshes

class Mesh:
    """ Triangles in parts. Each part is a closed solid (or near enough: a fin's root, buried in the body, is open), so
    its winding can be checked by its volume. Normals are smoothed within a part's group over vertices at the same
    place, so seams in the UVs don't show as creases, while a fin's two faces stay apart at its edge. """

    def __init__( self ):
        self.positions = []
        self.uvs = []
        self.normals = []
        self.triangles = []

    def add_part( self, sheets ):
        """ sheets: [ ( positions (n, 3), uvs (n, 2), triangles (m, 3) ) ], each its own smoothing group. """
        part_tris = []
        offset = len( self.positions )
        starts = []
        for positions, uvs, triangles in sheets:
            starts.append( offset )
            for p, uv in zip( positions, uvs ):
                self.positions.append( np.asarray( p, float ) )
                self.uvs.append( uv )
            for t in triangles:
                part_tris.append( [ offset + int( k ) for k in t ] )
            offset += len( positions )
        starts.append( offset )

        # Drop the slivers where a grid collapses to a point (a nose, a fin's tip)
        pos = np.array( self.positions )
        kept = []
        for a, b, c in part_tris:
            if np.linalg.norm( np.cross( pos[b] - pos[a], pos[c] - pos[a] ) ) > 1e-7:
                kept.append( [ a, b, c ] )
        part_tris = kept

        # Outwards: a closed solid wound outwards has a positive volume
        centre = pos[ starts[0]:starts[-1] ].mean( axis=0 )
        volume = sum( np.dot( pos[a] - centre, np.cross( pos[b] - centre, pos[c] - centre ) ) for a, b, c in part_tris )
        if volume < 0:
            part_tris = [ [ a, c, b ] for a, b, c in part_tris ]

        # Smooth normals per sheet, merged over vertices at the same place
        normals = np.zeros( ( offset - starts[0], 3 ) )
        for a, b, c in part_tris:
            n = np.cross( pos[b] - pos[a], pos[c] - pos[a] )
            for k in ( a, b, c ):
                normals[ k - starts[0] ] += n
        for s0, s1 in zip( starts, starts[1:] ):
            groups = {}
            for k in range( s0, s1 ):
                groups.setdefault( tuple( np.round( pos[k], 3 ) ), [] ).append( k - starts[0] )
            for members in groups.values():
                total = normals[ members ].sum( axis=0 )
                normals[ members ] = total
        for n in normals:
            length = np.linalg.norm( n )
            self.normals.append( n / length if length > 1e-9 else np.array( ( 0.0, 0.0, 1.0 ) ) )
        self.triangles.extend( part_tris )

    def volume_sign_check( self ):
        """ Every triangle's normal should agree with its vertices' smoothed normals (it's wound outwards). Points where
        a grid collapses (a nose, a fin's tip) are left out: their normal is the mean of all round them. """
        pos = np.array( self.positions )
        nrm = np.array( self.normals )
        shared = {}
        for p in pos:
            key = tuple( np.round( p, 3 ) )
            shared[key] = shared.get( key, 0 ) + 1
        bad = 0
        for a, b, c in self.triangles:
            if any( shared[ tuple( np.round( pos[k], 3 ) ) ] > 2 for k in ( a, b, c ) ):
                continue
            face = np.cross( pos[b] - pos[a], pos[c] - pos[a] )
            if np.dot( face, nrm[a] + nrm[b] + nrm[c] ) < 0:
                bad += 1
        return bad


def grid_triangles( ni, nj, closed_j=False ):
    tris = []
    jn = nj if closed_j else nj - 1
    for i in range( ni - 1 ):
        for j in range( jn ):
            j1 = ( j + 1 ) % nj
            a, b, c, d = i * nj + j, ( i + 1 ) * nj + j, ( i + 1 ) * nj + j1, i * nj + j1
            tris += [ [ a, b, c ], [ a, c, d ] ]
    return tris


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def lerp( a, b, t ):
    return a + ( b - a ) * t


# ---------------------------------------------------------------------------------------------------------------------
# Bodies and fins

def body( mesh, x_nose, x_tail, half_width, half_up, half_down, stations=28, ring=20, power=0.85, centre=lambda s: 0.0,
          uv=None ):
    """ A body lofted from the nose (s 0) to the tail (s 1). half_* are functions of s; they go to 0 at both ends. """
    s_values = [ ( k / ( stations - 1 ) ) for k in range( stations ) ]
    positions, uvs = [], []
    for s in s_values:
        x = lerp( x_nose, x_tail, s )
        for j in range( ring + 1 ):
            theta = -math.pi + 2 * math.pi * j / ring
            sn, cs = math.sin( theta ), math.cos( theta )
            y = half_width( s ) * math.copysign( abs( sn ) ** power, sn )
            h = half_up( s ) if cs >= 0 else half_down( s )
            z = centre( s ) + h * math.copysign( abs( cs ) ** power, cs )
            positions.append( ( x, y, z ) )
            uvs.append( uv( s, theta ) if uv else ( 0.6 * s, j / ring ) )
    mesh.add_part( [ ( positions, uvs, grid_triangles( stations, ring + 1 ) ) ] )


def bezier( p0, p1, p2, t ):
    return ( 1 - t ) ** 2 * p0 + 2 * ( 1 - t ) * t * p1 + t * t * p2


def fin( mesh, root_le, root_te, tip, le_bend=None, te_bend=None, thickness=1.0, chord_steps=7, span_steps=8, uv=None ):
    """ A fin from its root (leading and trailing points, inside the body) out to its tip, its leading and trailing
    edges curved through le_bend / te_bend. A lens in section: thickness at mid-chord, a sharp edge all round. """
    root_le, root_te, tip = ( np.asarray( p, float ) for p in ( root_le, root_te, tip ) )
    le_bend = np.asarray( le_bend if le_bend is not None else ( root_le + tip ) / 2, float )
    te_bend = np.asarray( te_bend if te_bend is not None else ( root_te + tip ) / 2, float )
    span_dir = tip - ( root_le + root_te ) / 2
    chord_dir = root_te - root_le
    normal = np.cross( span_dir, chord_dir )
    normal /= np.linalg.norm( normal )

    sheets = []
    for side in ( 1.0, -1.0 ):
        positions, uvs = [], []
        for a in range( chord_steps ):
            i = a / ( chord_steps - 1 )
            for b in range( span_steps ):
                j = b / ( span_steps - 1 )
                le = bezier( root_le, le_bend, tip, j )
                te = bezier( root_te, te_bend, tip, j )
                p = lerp( le, te, i )
                t = thickness * ( 1 - 0.5 * j ) * ( 1 - j ) ** 0.3 * ( 4 * i * ( 1 - i ) ) ** 0.6
                positions.append( p + side * normal * t * 0.5 )
                uvs.append( uv( p, i, j, side ) if uv else ( 0.6 + 0.4 * j, i ) )
        sheets.append( ( positions, uvs, grid_triangles( chord_steps, span_steps ) ) )
    mesh.add_part( sheets )


def mirror_y( p ):
    return ( p[0], -p[1], p[2] )


def paired_fin( mesh, root_le, root_te, tip, le_bend=None, te_bend=None, **kw ):
    fin( mesh, root_le, root_te, tip, le_bend, te_bend, **kw )
    fin( mesh, mirror_y( root_le ), mirror_y( root_te ), mirror_y( tip ),
         mirror_y( le_bend ) if le_bend else None, mirror_y( te_bend ) if te_bend else None, **kw )


def envelope( s, widest=0.32, peduncle=0.2, nose_power=0.55, end=0.94 ):
    """ A fusiform outline: rounded nose, widest at `widest`, tapering to the tail's stalk, closing at s 1. """
    if s <= widest:
        return math.sin( 0.5 * math.pi * s / widest ) ** nose_power
    if s <= end:
        t = ( s - widest ) / ( end - widest )
        return lerp( 1.0, peduncle, 0.5 - 0.5 * math.cos( math.pi * t ) )
    t = ( s - end ) / ( 1 - end )
    return peduncle * math.cos( 0.5 * math.pi * t ) ** 0.7


# ---------------------------------------------------------------------------------------------------------------------
# The animals

def reef_shark():
    """ Grey reef shark, 72 long: nose at +36, the caudal fin's upper lobe ending at -37. """
    m = Mesh()
    flat_head = lambda s: 0.72 + 0.28 * smoothstep( 0.0, 0.22, s )
    body( m, 36.0, -26.0,
          half_width=lambda s: 5.3 * envelope( s, 0.34, 0.22 ),
          half_up=lambda s: 6.0 * envelope( s, 0.36, 0.26 ) * flat_head( s ),
          half_down=lambda s: 5.0 * envelope( s, 0.3, 0.22 ) * flat_head( s ),
          centre=lambda s: -0.4 * math.sin( math.pi * s ) + 1.0 * smoothstep( 0.8, 1.0, s ),
          stations=30, ring=22 )
    # First dorsal: tall, its trailing edge swept and a little concave
    fin( m, ( 10.0, 0, 4.4 ), ( -2.0, 0, 3.6 ), ( -4.5, 0, 15.5 ), ( 6.5, 0, 12.5 ), ( -1.8, 0, 8.0 ), thickness=1.3 )
    fin( m, ( -13.5, 0, 2.2 ), ( -18.5, 0, 1.9 ), ( -20.0, 0, 5.2 ), ( -16.5, 0, 4.6 ), ( -18.4, 0, 3.2 ), thickness=0.6 )
    # Pectorals: long and sickle-shaped, out and down
    paired_fin( m, ( 17.5, 3.6, -2.6 ), ( 10.5, 3.4, -3.0 ), ( 1.0, 21.5, -9.0 ), ( 13.0, 13.5, -5.4 ), ( 8.5, 9.0, -5.0 ),
                thickness=1.1 )
    paired_fin( m, ( -8.0, 1.8, -3.2 ), ( -12.0, 1.2, -2.8 ), ( -14.5, 5.0, -6.0 ), ( -10.0, 4.0, -5.2 ), None,
                thickness=0.55 )
    fin( m, ( -15.0, 0, -2.2 ), ( -19.0, 0, -1.6 ), ( -20.5, 0, -5.0 ), ( -16.8, 0, -4.4 ), ( -19.2, 0, -2.8 ), thickness=0.55 )
    # The tail: the upper lobe long and raised, the lower one shorter (heterocercal)
    fin( m, ( -20.5, 0, 1.4 ), ( -26.0, 0, 0.6 ), ( -37.0, 0, 13.0 ), ( -28.0, 0, 6.8 ), ( -28.5, 0, 3.6 ), thickness=1.0,
         span_steps=10 )
    fin( m, ( -22.0, 0, -0.2 ), ( -26.0, 0, 0.6 ), ( -31.5, 0, -8.5 ), ( -25.5, 0, -5.4 ), ( -28.5, 0, -2.8 ), thickness=0.8 )
    return m


def yellow_tang():
    """ Yellow tang, 8 long: a tall, flat disc of a body with a long dorsal and anal fin, and a short snout. """
    m = Mesh()
    body( m, 4.0, -2.9,
          half_width=lambda s: 0.6 * envelope( s, 0.38, 0.35, 0.7 ),
          half_up=lambda s: 2.55 * envelope( s, 0.45, 0.24, 0.9 ) * ( 0.55 + 0.45 * smoothstep( 0.0, 0.3, s ) ),
          half_down=lambda s: 2.4 * envelope( s, 0.42, 0.24, 0.9 ) * ( 0.6 + 0.4 * smoothstep( 0.0, 0.3, s ) ),
          centre=lambda s: -0.35 * ( 1 - smoothstep( 0.0, 0.25, s ) ),
          stations=18, ring=16 )
    fin( m, ( 2.0, 0, 1.9 ), ( -2.5, 0, 0.6 ), ( -2.3, 0, 2.5 ), ( 0.4, 0, 3.5 ), ( -2.9, 0, 1.5 ), thickness=0.22,
         chord_steps=8, span_steps=6 )
    fin( m, ( 1.0, 0, -1.9 ), ( -2.5, 0, -0.6 ), ( -2.3, 0, -2.3 ), ( -0.2, 0, -3.2 ), ( -2.9, 0, -1.4 ), thickness=0.22,
         chord_steps=8, span_steps=6 )
    fin( m, ( -2.4, 0, 0.45 ), ( -2.95, 0, 0.0 ), ( -4.1, 0, 1.55 ), ( -3.2, 0, 1.3 ), ( -3.6, 0, 0.7 ), thickness=0.18 )
    fin( m, ( -2.4, 0, -0.45 ), ( -2.95, 0, 0.0 ), ( -4.1, 0, -1.55 ), ( -3.2, 0, -1.3 ), ( -3.6, 0, -0.7 ), thickness=0.18 )
    paired_fin( m, ( 1.0, 0.4, -0.3 ), ( 0.55, 0.4, -0.55 ), ( -0.35, 0.95, -0.85 ), ( 0.4, 0.8, -0.5 ), None,
                thickness=0.12 )
    return m


def chromis():
    """ Blue-green chromis, 5 long: a small, deep-ish body and a deeply forked tail. """
    m = Mesh()
    body( m, 2.5, -1.7,
          half_width=lambda s: 0.42 * envelope( s, 0.35, 0.3 ),
          half_up=lambda s: 0.9 * envelope( s, 0.4, 0.3, 0.7 ),
          half_down=lambda s: 0.8 * envelope( s, 0.38, 0.3, 0.7 ),
          stations=14, ring=12 )
    fin( m, ( 1.1, 0, 0.65 ), ( -1.35, 0, 0.35 ), ( -1.15, 0, 1.08 ), ( 0.2, 0, 1.12 ), ( -1.45, 0, 0.7 ), thickness=0.1,
         chord_steps=6, span_steps=5 )
    fin( m, ( -0.3, 0, -0.6 ), ( -1.35, 0, -0.35 ), ( -1.2, 0, -1.05 ), ( -0.6, 0, -1.05 ), None, thickness=0.1,
         chord_steps=5, span_steps=5 )
    fin( m, ( -1.4, 0, 0.3 ), ( -1.75, 0, 0.0 ), ( -2.55, 0, 0.95 ), ( -1.9, 0, 0.75 ), ( -2.2, 0, 0.45 ), thickness=0.08,
         chord_steps=5, span_steps=5 )
    fin( m, ( -1.4, 0, -0.3 ), ( -1.75, 0, 0.0 ), ( -2.55, 0, -0.95 ), ( -1.9, 0, -0.75 ), ( -2.2, 0, -0.45 ), thickness=0.08,
         chord_steps=5, span_steps=5 )
    paired_fin( m, ( 0.9, 0.33, -0.15 ), ( 0.55, 0.33, -0.3 ), ( -0.05, 0.9, -0.45 ), None, None, thickness=0.06,
                chord_steps=5, span_steps=5 )
    return m


# The manta's planform, in its own terms: span 140, the disc 58 long, the head's front at +24
MANTA_SPAN = 140.0
MANTA_CHORD = 58.0
MANTA_FRONT, MANTA_BACK = 32.0, -62.0           # the horns' tips and the tail's end, for its texture


def manta_edges( yn ):
    """ Leading and trailing edge x at a share of the half-span (0 middle, 1 wingtip). """
    c = MANTA_CHORD
    leading = 0.42 * c - 0.52 * c * yn ** 1.6
    trailing = -0.42 * c + 0.32 * c * yn ** 0.7
    return leading, trailing


def manta_uv( x, y, top ):
    u = np.clip( ( MANTA_FRONT - x ) / ( MANTA_FRONT - MANTA_BACK ), 0.0, 1.0 ) * 0.5
    return ( float( u + ( 0.0 if top else 0.5 ) ), float( np.clip( y / MANTA_SPAN + 0.5, 0.0, 1.0 ) ) )


def manta_ray():
    """ Reef manta, 140 across: a lens-section disc with swept, pointed wings, two cephalic fins forward of the
    mouth, a small dorsal fin and a thin tail. """
    m = Mesh()
    c, half = MANTA_CHORD, MANTA_SPAN / 2
    rows, chords = 37, 15
    sheets = []
    for top in ( True, False ):
        positions, uvs = [], []
        for a in range( rows ):
            # Rows closer together towards the tips, where the outline turns fastest
            yn = math.sin( math.pi * ( a / ( rows - 1 ) - 0.5 ) )
            y = yn * half
            leading, trailing = manta_edges( abs( yn ) )
            thick = 0.11 * c * math.exp( -( abs( yn ) / 0.2 ) ** 2 ) + 0.03 * c * ( 1 - abs( yn ) )
            camber = -3.0 * yn * yn
            for b in range( chords ):
                i = b / ( chords - 1 )
                x = lerp( leading, trailing, i )
                section = ( 4 * i ** 0.8 * ( 1 - i ** 0.8 ) ) ** 0.55
                z = camber + ( 0.55 if top else -0.45 ) * thick * section
                positions.append( ( x, y, z ) )
                uvs.append( manta_uv( x, y, top ) )
        sheets.append( ( positions, uvs, grid_triangles( rows, chords ) ) )
    m.add_part( sheets )

    top_uv = lambda p, i, j, side: manta_uv( p[0], p[1], side > 0 )
    # Cephalic fins, unrolled, reaching forward either side of the mouth
    paired_fin( m, ( 22.5, 13.5, 0.6 ), ( 21.0, 8.5, 0.4 ), ( 31.5, 11.5, -2.2 ), ( 28.5, 14.0, -0.6 ), ( 28.0, 9.5, -1.0 ),
                thickness=1.6, uv=top_uv )
    fin( m, ( -18.0, 0, 3.5 ), ( -23.5, 0, 2.6 ), ( -26.0, 0, 7.0 ), ( -21.5, 0, 6.8 ), None, thickness=0.9, uv=top_uv )
    tail_uv = lambda s, theta: manta_uv( lerp( -20.0, MANTA_BACK, s ), 0.0, True )
    body( m, -20.0, MANTA_BACK,
          half_width=lambda s: 1.5 * ( 1 - s ) ** 0.8 * smoothstep( 0.0, 0.02, s ) + 0.0,
          half_up=lambda s: 1.3 * ( 1 - s ) ** 0.8 * smoothstep( 0.0, 0.02, s ),
          half_down=lambda s: 1.3 * ( 1 - s ) ** 0.8 * smoothstep( 0.0, 0.02, s ),
          centre=lambda s: 0.5 - 1.5 * s * s, stations=14, ring=8, uv=tail_uv )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Textures

def noise( size, scale, seed ):
    """ Smooth value noise, 0..1. """
    rng = np.random.default_rng( seed )
    cells = rng.random( ( scale + 1, scale + 1 ) )
    t = np.linspace( 0, scale, size, endpoint=False )
    i = t.astype( int )
    f = t - i
    f = f * f * ( 3 - 2 * f )
    a = cells[ i[:, None], i[None, :] ]
    b = cells[ i[:, None], i[None, :] + 1 ]
    c = cells[ i[:, None] + 1, i[None, :] ]
    d = cells[ i[:, None] + 1, i[None, :] + 1 ]
    fy, fx = f[:, None], f[None, :]
    return lerp( lerp( a, b, fx ), lerp( c, d, fx ), fy )


def uv_grid():
    """ u (across) and v (down the picture, 0 at the top) for each texel's centre. The fish textures are laid out so
    v's direction doesn't matter. """
    t = ( np.arange( TEXTURE ) + 0.5 ) / TEXTURE
    return t[None, :].repeat( TEXTURE, 0 ), t[:, None].repeat( TEXTURE, 1 )


def mix( a, b, t ):
    return a + ( np.asarray( b, float ) - a ) * t[..., None]


def fish_parts( u, v ):
    s = np.clip( u / 0.6, 0, 1 )
    theta = v * 2 * np.pi - np.pi
    return s, np.cos( theta ), np.abs( np.sin( theta ) ), u >= 0.6, np.clip( ( u - 0.6 ) / 0.4, 0, 1 ), v


def paint_shark():
    u, v = uv_grid()
    s, up, side, is_fin, span, chord = fish_parts( u, v )
    grain = noise( TEXTURE, 24, 1 ) * 0.6 + noise( TEXTURE, 64, 2 ) * 0.4
    back = np.array( ( 0.34, 0.37, 0.40 ) )
    belly = np.array( ( 0.86, 0.86, 0.84 ) )
    colour = mix( np.broadcast_to( belly, u.shape + ( 3, ) ).copy(), back, smoothstep( -0.42, -0.12, up ) )
    colour *= ( 0.92 + 0.12 * grain )[..., None]
    # Gill slits: five short dark lines on each side, behind the eye
    for k in range( 5 ):
        line = np.exp( -( ( s - ( 0.175 + 0.017 * k ) ) / 0.0035 ) ** 2 )
        line *= smoothstep( -0.35, -0.2, up ) * ( 1 - smoothstep( 0.18, 0.32, up ) ) * smoothstep( 0.55, 0.75, side )
        colour = mix( colour, ( 0.16, 0.17, 0.18 ), line * 0.85 )
    eye = np.exp( -( ( s - 0.085 ) / 0.008 ) ** 2 - ( ( up - 0.18 ) / 0.1 ) ** 2 ) * smoothstep( 0.5, 0.7, side )
    colour = mix( colour, ( 0.03, 0.03, 0.03 ), np.clip( eye * 1.6, 0, 1 ) )
    mouth = np.exp( -( ( s - 0.1 ) / 0.004 ) ** 2 ) * smoothstep( -0.8, -0.95, up )
    colour = mix( colour, ( 0.55, 0.53, 0.52 ), mouth * 0.6 )

    # Fins: the back's grey, a little darker; black tips and a dark trailing edge (the reef shark's marks)
    fin_colour = np.broadcast_to( back * 0.92, u.shape + ( 3, ) ) * ( 0.94 + 0.1 * grain )[..., None]
    fin_colour = mix( fin_colour, ( 0.05, 0.05, 0.06 ), np.clip( smoothstep( 0.72, 0.93, span )
                                                              + 0.7 * smoothstep( 0.8, 0.97, chord ) * smoothstep( 0.3, 0.6, span ), 0, 1 ) )
    return np.where( is_fin[..., None], fin_colour, colour )


def paint_tang():
    u, v = uv_grid()
    s, up, side, is_fin, span, chord = fish_parts( u, v )
    grain = noise( TEXTURE, 30, 3 )
    yellow = np.array( ( 0.97, 0.78, 0.06 ) )
    colour = np.broadcast_to( yellow, u.shape + ( 3, ) ) * ( 0.93 + 0.1 * grain )[..., None]
    colour = mix( colour, ( 1.0, 0.86, 0.3 ), smoothstep( -0.5, -0.9, up ) * 0.5 )
    eye = np.exp( -( ( s - 0.16 ) / 0.018 ) ** 2 - ( ( up - 0.3 ) / 0.12 ) ** 2 ) * smoothstep( 0.5, 0.7, side )
    colour = mix( colour, ( 0.04, 0.04, 0.04 ), np.clip( eye * 1.5, 0, 1 ) )
    spine = np.exp( -( ( s - 0.9 ) / 0.02 ) ** 2 - ( up / 0.15 ) ** 2 ) * smoothstep( 0.6, 0.8, side )
    colour = mix( colour, ( 0.97, 0.96, 0.9 ), np.clip( spine * 1.4, 0, 1 ) )
    fin_colour = np.broadcast_to( yellow * 0.97, u.shape + ( 3, ) ) * ( 0.95 + 0.08 * grain )[..., None]
    fin_colour = mix( fin_colour, ( 0.92, 0.62, 0.05 ), smoothstep( 0.75, 1.0, span ) * 0.6 )
    return np.where( is_fin[..., None], fin_colour, colour )


def paint_chromis():
    u, v = uv_grid()
    s, up, side, is_fin, span, chord = fish_parts( u, v )
    grain = noise( TEXTURE, 30, 4 )
    back = np.array( ( 0.12, 0.42, 0.50 ) )
    flank = np.array( ( 0.36, 0.78, 0.76 ) )
    belly = np.array( ( 0.78, 0.92, 0.88 ) )
    colour = mix( np.broadcast_to( flank, u.shape + ( 3, ) ).copy(), back, smoothstep( 0.35, 0.85, up ) )
    colour = mix( colour, belly, smoothstep( -0.4, -0.85, up ) )
    colour *= ( 0.93 + 0.1 * grain )[..., None]
    eye = np.exp( -( ( s - 0.13 ) / 0.02 ) ** 2 - ( ( up - 0.25 ) / 0.15 ) ** 2 ) * smoothstep( 0.5, 0.7, side )
    colour = mix( colour, ( 0.04, 0.05, 0.05 ), np.clip( eye * 1.5, 0, 1 ) )
    fin_colour = np.broadcast_to( flank * 0.85, u.shape + ( 3, ) ).copy()
    fin_colour = mix( fin_colour, ( 0.1, 0.3, 0.38 ), smoothstep( 0.75, 1.0, span ) * 0.7 )
    return np.where( is_fin[..., None], fin_colour, colour )


def paint_manta():
    u, v = uv_grid()
    top = u < 0.5
    xn = np.where( top, u / 0.5, ( u - 0.5 ) / 0.5 )
    x = MANTA_FRONT - xn * ( MANTA_FRONT - MANTA_BACK )
    y = ( v - 0.5 ) * MANTA_SPAN
    ay = np.abs( y )
    yn = np.clip( ay / ( MANTA_SPAN / 2 ), 0, 1 )
    trailing = -0.42 * MANTA_CHORD + 0.32 * MANTA_CHORD * yn ** 0.7
    grain = noise( TEXTURE, 28, 5 ) * 0.6 + noise( TEXTURE, 90, 6 ) * 0.4

    # Top: near black, with the reef manta's pale shoulder patches behind the head, split by a dark midline
    dark = np.array( ( 0.045, 0.05, 0.058 ) )
    upper = np.broadcast_to( dark, u.shape + ( 3, ) ) * ( 0.85 + 0.3 * grain )[..., None]
    # Each patch a soft triangle: its front edge along the back of the head, sweeping back and out to a point
    front = 15.0 - 0.18 * ( ay - 8.0 )
    rear = 9.0 - 0.55 * ( ay - 8.0 )
    patch = smoothstep( -1.5, 2.5, front - x ) * smoothstep( -1.5, 3.0, x - rear ) \
        * smoothstep( 6.0, 10.0, ay ) * ( 1 - smoothstep( 22.0, 34.0, ay ) )
    patch *= 0.7 + 0.3 * noise( TEXTURE, 12, 7 )
    upper = mix( upper, ( 0.72, 0.74, 0.74 ), np.clip( patch, 0, 1 ) )

    # Underside: white, dark along the wings' trailing edges and tips, the mouth, gill slits and a few spots
    lower = np.broadcast_to( np.array( ( 0.86, 0.87, 0.86 ) ), u.shape + ( 3, ) ) * ( 0.95 + 0.06 * grain )[..., None]
    margin = np.clip( smoothstep( 6.0, 0.0, x - trailing ) * smoothstep( 0.15, 0.4, yn ) + smoothstep( 0.8, 0.98, yn ), 0, 1 )
    lower = mix( lower, ( 0.22, 0.23, 0.25 ), margin * 0.85 )
    mouth = smoothstep( 19.0, 22.0, x ) * ( 1 - smoothstep( 8.0, 10.0, ay ) )
    lower = mix( lower, ( 0.08, 0.08, 0.09 ), mouth )
    for k in range( 5 ):
        gx = 14.0 - 1.8 * k
        slit = np.exp( -( ( x - gx ) / 0.35 ) ** 2 ) * smoothstep( 7.5, 8.5, ay ) * ( 1 - smoothstep( 13.0, 14.5, ay ) )
        lower = mix( lower, ( 0.25, 0.25, 0.27 ), slit * 0.9 )
    rng = np.random.default_rng( 8 )
    for _ in range( 14 ):
        sx, sy, r = rng.uniform( -14, 4 ), rng.uniform( -16, 16 ), rng.uniform( 0.6, 1.6 )
        spot = np.exp( -( ( x - sx ) ** 2 + ( y - sy ) ** 2 ) / ( r * r ) )
        lower = mix( lower, ( 0.12, 0.12, 0.14 ), np.clip( spot * 1.5, 0, 1 ) )
    return np.where( top[..., None], upper, lower )


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def obj_vector( p ):
    return f"{p[1]:.4f} {p[2]:.4f} {p[0]:.4f}"


def write_obj( path, mesh, material ):
    lines = [ "# Tools/reefhall_fauna.py", f"mtllib {path.stem}.mtl", f"o {path.stem}" ]
    lines += [ f"v {obj_vector( p )}" for p in mesh.positions ]
    lines += [ f"vt {u:.5f} {v:.5f}" for u, v in mesh.uvs ]
    lines += [ f"vn {obj_vector( n )}" for n in mesh.normals ]
    lines.append( f"usemtl {material}" )
    lines += [ "f " + " ".join( f"{k + 1}/{k + 1}/{k + 1}" for k in t ) for t in mesh.triangles ]
    path.write_text( "\n".join( lines ) + "\n", newline="\n" )
    path.with_suffix( ".mtl" ).write_text( f"newmtl {material}\nKd 1 1 1\nd 1\n", newline="\n" )


def write_vmat( path, name, swim, roughness ):
    params = "\n".join( f'\t{key} "{value:.3f}"' for key, value in swim.items() )
    path.write_text( f"""// Tools/reefhall_fauna.py
Layer0
{{
	shader "shaders/hc1_fish.shader"

	F_DO_NOT_CAST_SHADOWS 1
	g_bFogEnabled "1"

{params}
	g_flMinRoughness "{roughness:.3f}"

	TextureColor "{RESOURCE}/{name}_color.png"
	TextureNormal "materials/default/default_normal.tga"
	TextureRoughness "[{roughness:.3f} {roughness:.3f} {roughness:.3f} 0.000]"
	TextureMetalness "[0.000 0.000 0.000 0.000]"
	TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
""", newline="\n" )


def write_vmdl( path, name ):
    path.write_text( f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "{name}.vmat" to = "{RESOURCE}/{name}.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
					{{
						_class = "RenderMeshFile"
						name = "{name}"
						filename = "{RESOURCE}/{name}.obj"
						import_translation = [ 0.0, 0.0, 0.0 ]
						import_rotation = [ 0.0, 0.0, 0.0 ]
						import_scale = 1.0
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						parent_bone = ""
						import_filter = {{ exclude_by_default = false exception_list = [ ] }}
					}},
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""", newline="\n" )


# name: ( mesh, painter, the shader's swimming settings, roughness )
# Tail beats: a cruising reef shark ~0.8 a second, small reef fish 3-4; a manta's wingbeat takes ~3 s.
ANIMALS = {
    "reef_shark": ( reef_shark, paint_shark,
                    { "g_flBodyLength": 73.0, "g_flSwingAmount": 0.07, "g_flBeatRate": 0.8, "g_flWaveLength": 1.0,
                      "g_flRay": 0.0, "g_flSpan": 44.0, "g_flFlapAmount": 0.0 }, 0.5 ),
    "manta_ray": ( manta_ray, paint_manta,
                   { "g_flBodyLength": 48.0, "g_flSwingAmount": 0.0, "g_flBeatRate": 0.32, "g_flWaveLength": 1.0,
                     "g_flRay": 1.0, "g_flSpan": MANTA_SPAN, "g_flFlapAmount": 0.1 }, 0.5 ),
    "yellow_tang": ( yellow_tang, paint_tang,
                     { "g_flBodyLength": 8.1, "g_flSwingAmount": 0.09, "g_flBeatRate": 3.0, "g_flWaveLength": 1.2,
                       "g_flRay": 0.0, "g_flSpan": 3.0, "g_flFlapAmount": 0.0 }, 0.45 ),
    "chromis": ( chromis, paint_chromis,
                 { "g_flBodyLength": 5.05, "g_flSwingAmount": 0.1, "g_flBeatRate": 4.0, "g_flWaveLength": 1.1,
                   "g_flRay": 0.0, "g_flSpan": 2.0, "g_flFlapAmount": 0.0 }, 0.4 ),
}


PREVIEW_SCRIPT = r'''
import bpy, math, sys
args = sys.argv[ sys.argv.index( "--" ) + 1: ]
obj_path, tex_path, out_path, size = args[0], args[1], args[2], float( args[3] )
bpy.ops.wm.read_factory_settings( use_empty=True )
bpy.ops.wm.obj_import( filepath=obj_path )
ob = bpy.context.selected_objects[0]
mat = bpy.data.materials.new( "m" ); mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = next( n for n in nodes if n.type == "BSDF_PRINCIPLED" )
tex = nodes.new( "ShaderNodeTexImage" ); tex.image = bpy.data.images.load( tex_path )
mat.node_tree.links.new( tex.outputs[0], bsdf.inputs[0] )
bsdf.inputs["Roughness"].default_value = 0.5
ob.data.materials.clear(); ob.data.materials.append( mat )
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [ e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items ] else scene.render.engine
world = bpy.data.worlds.new( "w" ); scene.world = world; world.use_nodes = True
bg = next( n for n in world.node_tree.nodes if n.type == "BACKGROUND" ); bg.inputs[0].default_value = ( 0.25, 0.45, 0.6, 1 ); bg.inputs[1].default_value = 0.8
sun = bpy.data.objects.new( "sun", bpy.data.lights.new( "sun", "SUN" ) ); scene.collection.objects.link( sun )
sun.rotation_euler = ( math.radians( 40 ), math.radians( 10 ), math.radians( 30 ) ); sun.data.energy = 3
cam = bpy.data.objects.new( "cam", bpy.data.cameras.new( "cam" ) ); scene.collection.objects.link( cam ); scene.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
views = [ ( ( 1, 0, 0.3 ), "side" ), ( ( 0, 0.0001, 1 ), "top" ), ( ( 0.6, -0.8, -0.5 ), "below" ) ]
for direction, label in views:
    import mathutils
    d = mathutils.Vector( direction ).normalized()
    # The OBJ was written ( y, z, x ); imported Y-forward Z-up, model X ends up on Blender's... read it from the bounds
    cam.location = d * size * 3
    cam.rotation_euler = ( -d ).to_track_quat( "-Z", "Y" ).to_euler()
    scene.render.filepath = out_path.replace( ".png", f"_{label}.png" )
    bpy.ops.render.render( write_still=True )
'''


def preview( directory ):
    blender = pathlib.Path( r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" )
    if not blender.exists():
        print( "no Blender for the preview" )
        return
    directory = pathlib.Path( directory )
    directory.mkdir( parents=True, exist_ok=True )
    script = directory / "fauna_preview.py"
    script.write_text( PREVIEW_SCRIPT )
    sizes = { "reef_shark": 90, "manta_ray": 170, "yellow_tang": 11, "chromis": 7 }
    for name in ANIMALS:
        subprocess.run( [ str( blender ), "-b", "--python", str( script ), "--", str( OUT / f"{name}.obj" ),
                          str( OUT / f"{name}_color.png" ), str( directory / f"{name}.png" ), str( sizes[name] ) ],
                        check=True, stdout=subprocess.DEVNULL )
        print( "preview", name )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", help="render each animal with Blender into this folder" )
    args = parser.parse_args()
    OUT.mkdir( parents=True, exist_ok=True )
    for name, ( build, paint, swim, roughness ) in ANIMALS.items():
        mesh = build()
        bad = mesh.volume_sign_check()
        write_obj( OUT / f"{name}.obj", mesh, name )
        colour = np.clip( paint(), 0, 1 )
        Image.fromarray( ( colour ** ( 1 / 1.0 ) * 255 + 0.5 ).astype( np.uint8 ) ).save( OUT / f"{name}_color.png" )
        write_vmat( OUT / f"{name}.vmat", name, swim, roughness )
        write_vmdl( OUT / f"{name}.vmdl", name )
        p = np.array( mesh.positions )
        print( f"{name}: {len( mesh.triangles )} triangles, {bad} wound inwards, "
               f"bounds {np.round( p.min( axis=0 ), 1 )} to {np.round( p.max( axis=0 ), 1 )}" )
        if bad:
            sys.exit( f"{name} has triangles wound the wrong way" )
    if args.preview:
        preview( args.preview )


if __name__ == "__main__":
    main()
