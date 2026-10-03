"""
Reef Hall's aquarium animals, built from numbers with no samples or downloads: two big animals and thirteen reef fish,
each its real size and colours. For each it writes, into Assets/models/maps/reefhall/fauna/:

  - <name>.obj: the mesh, smooth-shaded, every part a closed solid wound outwards;
  - <name>_color.png: its colours, painted with numpy;
  - <name>.vmat: on shaders/hc1_fish.shader, with the swimming wave's settings for that animal;
  - <name>.vmdl: render only, no collision (they're behind glass; Code/Maps/TankFauna.cs swims them).

It also writes fauna_species.json beside them: each animal's reach (how far its body can come from its middle, at any
heading, pitch and bank, swimming), which Tools/reefhall_map.py hands to TankFauna with how each one behaves (SPECIES).

Model space is the animal's own: +X forward (the nose), +Y to its left, +Z up, the middle of its body near the origin.
The OBJ writes ( x, y, z ) as ( y, z, x ), as Tools/map_kit.py does, since ModelDoc reads an OBJ as Y-up. Its UVs are
OBJ's (v up), as the grass atlas's are.

Sizes are real ones in inches (the game's unit), adults as aquariums keep them:
  - grey reef shark (Carcharhinus amblyrhynchos): 1.8 m, 72;
  - reef manta (Mobula alfredi): 3.5 m across the wings, 140;
  - yellow tang (Zebrasoma flavescens): 20 cm, 8;
  - blue tang (Paracanthurus hepatus): 18 cm, 7;
  - blue-green chromis (Chromis viridis): 12 cm, 5;
  - copperband butterflyfish (Chelmon rostratus): 15 cm, 6, a third of it the snout's;
  - regal angelfish (Pygoplites diacanthus): 20 cm, 8;
  - Moorish idol (Zanclus cornutus): 18 cm, 7, and its dorsal filament as long again;
  - ocellaris clownfish (Amphiprion ocellaris): 9 cm, 3.5;
  - Banggai cardinalfish (Pterapogon kauderni): 7.5 cm, 3;
  - red lionfish (Pterois volitans): 33 cm, 13;
  - white-spotted puffer (Arothron hispidus): 30 cm, 12;
  - mandarinfish (Synchiropus splendidus): 6 cm, 2.4;
  - yellow-and-blueback fusilier (Caesio teres): 23 cm, 9;
  - Indo-Pacific sergeant (Abudefduf vaigiensis): 15 cm, 6.
The freshwater angelfish (Pterophyllum) is left out: every tank here is a reef.

Bodies are lofted along X through super-elliptic sections. Fins are thin lens-shaped solids (thickest in the middle,
meeting in a sharp edge all round) whose roots sit inside the body. The texture is laid out in four parts:
  - the body: U 0 to 0.47 nose to tail, V round its girth (belly, one side, the back, the other side, belly);
  - the pectoral fins: U 0.5 to 0.58 root to tip, V across the fin. hc1_fish.shader flutters what's in this strip;
  - the pelvic fins: U 0.585 to 0.62, the same way;
  - the dorsal, anal and tail fins: U 0.63 to 1 and V 0 to 1, a side view of them (nose at U 0.63, the top at V 1).
The colours are painted from where each texel is on the fish (each triangle is drawn into the texture with its points'
positions), so a band runs on from the body into the fins as it does on the fish. The manta keeps a layout of its own.

    python Tools/reefhall_fauna.py                 writes everything
    python Tools/reefhall_fauna.py --only a,b      only those animals
    python Tools/reefhall_fauna.py --preview <dir> also renders each animal with Blender (if it's installed)
"""

import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path( __file__ ).resolve().parent.parent
OUT = ROOT / "Assets" / "models" / "maps" / "reefhall" / "fauna"
RESOURCE = "models/maps/reefhall/fauna"
TEXTURE = 1024

ROLES = { "body": 1, "median": 2, "pectoral": 3, "pelvic": 4, "custom": 5 }
PECTORAL_U = ( 0.5, 0.58 )
PELVIC_U = ( 0.585, 0.62 )
MEDIAN_U = ( 0.63, 0.998 )
BODY_U = ( 0.004, 0.47 )


# ---------------------------------------------------------------------------------------------------------------------
# Meshes

class Mesh:
    """ Triangles in parts. Each part is a closed solid (or near enough: a fin's root, buried in the body, is open), so
    its winding can be checked by its volume. Normals are smoothed within a part's sheet over vertices at the same
    place, so seams don't show as creases, while a fin's two faces stay apart at its edge. Each vertex has a role (body,
    a median fin, a pectoral or pelvic fin) and three numbers for painting: the body's s, up and side, or a fin's span
    and chord. UVs are worked out once the fish is whole (`finish`). """

    def __init__( self ):
        self.positions = []
        self.attrs = []
        self.roles = []
        self.uvs = []
        self.normals = []
        self.triangles = []

    def add_part( self, sheets, role ):
        """ sheets: [ ( positions (n, 3), attrs (n, 3) or uvs for "custom", triangles (m, 3) ) ]. """
        part_tris = []
        offset = len( self.positions )
        starts = []
        for positions, attrs, triangles in sheets:
            starts.append( offset )
            for p, a in zip( positions, attrs ):
                self.positions.append( np.asarray( p, float ) )
                self.attrs.append( tuple( a ) + ( 0.0, ) * ( 3 - len( a ) ) )
                self.roles.append( role )
                self.uvs.append( tuple( a[:2] ) if role == "custom" else None )
            for t in triangles:
                part_tris.append( [ offset + int( k ) for k in t ] )
            offset += len( positions )
        starts.append( offset )

        # Drop the slivers where a grid collapses to a point (a nose, a fin's tip)
        pos = np.array( self.positions )
        kept = []
        for a, b, c in part_tris:
            if np.linalg.norm( np.cross( pos[b] - pos[a], pos[c] - pos[a] ) ) > 1e-8:
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
                groups.setdefault( tuple( np.round( pos[k], 4 ) ), [] ).append( k - starts[0] )
            for members in groups.values():
                normals[ members ] = normals[ members ].sum( axis=0 )
        for n in normals:
            length = np.linalg.norm( n )
            self.normals.append( n / length if length > 1e-12 else np.array( ( 0.0, 0.0, 1.0 ) ) )
        self.triangles.extend( part_tris )

    def finish( self ):
        """ The UVs: the body by its s and girth, the paired fins by span and chord, the median fins by a side view. """
        pos = np.array( self.positions )
        median = [ k for k, r in enumerate( self.roles ) if r == "median" ]
        if median:
            mp = pos[ median ]
            self.x_front, self.x_back = mp[:, 0].max(), mp[:, 0].min()
            self.z_low, self.z_high = mp[:, 2].min(), mp[:, 2].max()
        for k, ( role, ( a, b, c ) ) in enumerate( zip( self.roles, self.attrs ) ):
            if role == "body":
                self.uvs[k] = ( lerp( *BODY_U, a ), 0.002 + 0.996 * c_girth( b, c, a ) )
            elif role == "median":
                x, z = pos[k, 0], pos[k, 2]
                u = lerp( *MEDIAN_U, ( self.x_front - x ) / max( self.x_front - self.x_back, 1e-6 ) )
                v = 0.004 + 0.992 * ( z - self.z_low ) / max( self.z_high - self.z_low, 1e-6 )
                self.uvs[k] = ( u, v )
            elif role == "pectoral":
                self.uvs[k] = ( lerp( *PECTORAL_U, a ), 0.01 + 0.98 * b )
            elif role == "pelvic":
                self.uvs[k] = ( lerp( *PELVIC_U, a ), 0.01 + 0.98 * b )

    def volume_sign_check( self ):
        """ Every triangle's normal should agree with its vertices' smoothed normals (it's wound outwards). Points where
        a grid collapses (a nose, a fin's tip) are left out: their normal is the mean of all round them. """
        pos = np.array( self.positions )
        nrm = np.array( self.normals )
        shared = {}
        for p in pos:
            key = tuple( np.round( p, 4 ) )
            shared[key] = shared.get( key, 0 ) + 1
        bad = 0
        for a, b, c in self.triangles:
            if any( shared[ tuple( np.round( pos[k], 4 ) ) ] > 2 for k in ( a, b, c ) ):
                continue
            face = np.cross( pos[b] - pos[a], pos[c] - pos[a] )
            if np.dot( face, nrm[a] + nrm[b] + nrm[c] ) < 0:
                bad += 1
        return bad


def c_girth( up, side, s ):
    """ The body's V: where round its girth a point is, from up (the cosine of its angle from the back) and which side
    (its third number carries the sign). """
    theta = math.atan2( side, up )             # 0 at the back, pi at the belly, the sign the side
    return ( theta + math.pi ) / ( 2 * math.pi )


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

class Profile:
    """ A lofted body's outline, to hang fins on: its top and bottom z, half width and middle at any x. """

    def __init__( self, x_nose, x_tail, half_width, half_up, half_down, centre ):
        self.x_nose, self.x_tail = x_nose, x_tail
        self.hw, self.hu, self.hd, self.c = half_width, half_up, half_down, centre

    def s( self, x ):
        return float( np.clip( ( self.x_nose - x ) / ( self.x_nose - self.x_tail ), 0.0, 1.0 ) )

    def top( self, x, inset=0.18 ):
        s = self.s( x )
        return self.c( s ) + self.hu( s ) * ( 1 - inset )

    def bottom( self, x, inset=0.18 ):
        s = self.s( x )
        return self.c( s ) - self.hd( s ) * ( 1 - inset )

    def width( self, x ):
        return self.hw( self.s( x ) )

    def centre( self, x ):
        return self.c( self.s( x ) )


def body( mesh, x_nose, x_tail, half_width, half_up, half_down, stations=30, ring=22, power=0.85, centre=lambda s: 0.0 ):
    """ A body lofted from the nose (s 0) to the tail (s 1). half_* are functions of s; they go to 0 at both ends.
    Stations are closer together at both ends, where the outline turns fastest. """
    positions, attrs = [], []
    for k in range( stations ):
        s = 0.5 - 0.5 * math.cos( math.pi * k / ( stations - 1 ) )
        x = lerp( x_nose, x_tail, s )
        for j in range( ring + 1 ):
            theta = -math.pi + 2 * math.pi * j / ring
            sn, cs = math.sin( theta ), math.cos( theta )
            y = half_width( s ) * math.copysign( abs( sn ) ** power, sn )
            h = half_up( s ) if cs >= 0 else half_down( s )
            z = centre( s ) + h * math.copysign( abs( cs ) ** power, cs )
            positions.append( ( x, y, z ) )
            # The seam (j 0 and ring) is at the belly; the sign of side tells the two halves apart for the UV.
            side = -1e-6 if j == 0 else ( 1e-6 if j == ring else sn )
            attrs.append( ( s, cs, side ) )
    mesh.add_part( [ ( positions, attrs, grid_triangles( stations, ring + 1 ) ) ], "body" )
    return Profile( x_nose, x_tail, half_width, half_up, half_down, centre )


def bezier( p0, p1, p2, t ):
    return ( 1 - t ) ** 2 * p0 + 2 * ( 1 - t ) * t * p1 + t * t * p2


def fin( mesh, root_le, root_te, tip, le_bend=None, te_bend=None, thickness=1.0, chord_steps=7, span_steps=8,
         role="median" ):
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
        positions, attrs = [], []
        for a in range( chord_steps ):
            i = a / ( chord_steps - 1 )
            for b in range( span_steps ):
                j = b / ( span_steps - 1 )
                le = bezier( root_le, le_bend, tip, j )
                te = bezier( root_te, te_bend, tip, j )
                p = lerp( le, te, i )
                t = thickness * ( 1 - 0.5 * j ) * ( 1 - j ) ** 0.3 * ( 4 * i * ( 1 - i ) ) ** 0.6
                positions.append( p + side * normal * t * 0.5 )
                attrs.append( ( j, i, 0.0 ) )
        sheets.append( ( positions, attrs, grid_triangles( chord_steps, span_steps ) ) )
    mesh.add_part( sheets, role )


def median_fin( mesh, root, edge, thickness, chord_steps=10, span_steps=6, role="median" ):
    """ A fin on the body's middle plane (a dorsal, an anal fin, a tail): root(i) and edge(i) give ( x, z ) for i from 0
    to 1 along it (front to back, or bottom to top for a tail), the root inside the body and the edge its outline. """
    # Finer than asked, so outlines stay round
    chord_steps, span_steps = max( chord_steps, int( chord_steps * 1.5 ) ), span_steps + 2
    sheets = []
    for side in ( 1.0, -1.0 ):
        positions, attrs = [], []
        for a in range( chord_steps ):
            i = a / ( chord_steps - 1 )
            r = np.asarray( root( i ), float )
            e = np.asarray( edge( i ), float )
            for b in range( span_steps ):
                j = b / ( span_steps - 1 )
                p = lerp( r, e, j )
                t = thickness * ( 1 - j ) ** 0.55 * ( 4 * i * ( 1 - i ) ) ** 0.45
                positions.append( ( p[0], side * t * 0.5, p[1] ) )
                attrs.append( ( j, i, 0.0 ) )
        sheets.append( ( positions, attrs, grid_triangles( chord_steps, span_steps ) ) )
    mesh.add_part( sheets, role )


def mirror_y( p ):
    return None if p is None else ( p[0], -p[1], p[2] )


def paired_fin( mesh, root_le, root_te, tip, le_bend=None, te_bend=None, role="pectoral", **kw ):
    fin( mesh, root_le, root_te, tip, le_bend, te_bend, role=role, **kw )
    fin( mesh, mirror_y( root_le ), mirror_y( root_te ), mirror_y( tip ), mirror_y( le_bend ), mirror_y( te_bend ),
         role=role, **kw )


def flank_y( b, x, z, inset=0.82, power=0.85 ):
    """ How far out the body's flank is at ( x, z ), times `inset`, so a fin's root there sits inside the body. """
    s = b.s( x )
    c = b.c( s )
    h = b.hu( s ) if z >= c else b.hd( s )
    rel = min( abs( z - c ) / max( h, 1e-6 ), 0.98 )
    cs = rel ** ( 1 / power )
    return b.hw( s ) * math.sqrt( max( 1 - cs * cs, 0.0 ) ) ** power * inset


def side_fins( mesh, b, x, z, root, length, out=35.0, down=20.0, breadth=0.42, thickness=None, role="pectoral",
               rake=0.25 ):
    """ A pair of paired fins (pectoral or pelvic) on the flanks of body `b`: a root `root` tall at ( x, z ), leaning
    back by `rake`, and a rounded fan `length` long, swept back and `out` degrees away from the body and `down` degrees
    down, `breadth` of its length across at its widest. """
    y = flank_y( b, x, z )
    o, d = math.radians( out ), math.radians( down )
    direction = np.array( ( -math.cos( o ) * math.cos( d ), math.sin( o ) * math.cos( d ), -math.sin( d ) ) )
    root_le = np.array( ( x + rake * root * 0.5, y, z + root * 0.5 ) )
    root_te = np.array( ( x - rake * root * 0.5, y, z - root * 0.5 ) )
    across = root_le - root_te
    across /= np.linalg.norm( across )
    across = across - direction * np.dot( across, direction )
    across /= np.linalg.norm( across )
    mid = ( root_le + root_te ) / 2
    tip = mid + direction * length
    le_bend = mid + direction * length * 0.62 + across * length * breadth
    te_bend = mid + direction * length * 0.62 - across * length * breadth
    thickness = thickness if thickness is not None else max( 0.03, 0.08 * length )
    paired_fin( mesh, tuple( root_le ), tuple( root_te ), tuple( tip ), tuple( le_bend ), tuple( te_bend ), role=role,
                thickness=thickness, chord_steps=7, span_steps=8 )


def envelope( s, widest=0.32, peduncle=0.2, nose_power=0.55, end=0.94 ):
    """ A fusiform outline: rounded nose, widest at `widest`, tapering to the tail's stalk, closing at s 1. """
    if s <= widest:
        return math.sin( 0.5 * math.pi * s / widest ) ** nose_power
    if s <= end:
        t = ( s - widest ) / ( end - widest )
        return lerp( 1.0, peduncle, 0.5 - 0.5 * math.cos( math.pi * t ) )
    t = ( s - end ) / ( 1 - end )
    return peduncle * math.cos( 0.5 * math.pi * t ) ** 0.7


def snouted( s, snout, radius, full, **kw ):
    """ A body with a snout: a thin tube `radius` / `full` of the body's size along the first `snout` of the length,
    rounded at its tip, running into an envelope that starts a little way back along it (a smooth maximum of the two,
    so the forehead rises out of the snout). """
    tube = ( radius / full ) * math.sin( 0.5 * math.pi * min( s / ( snout * 0.15 ), 1.0 ) ) ** 0.5 \
        * ( 1 - smoothstep( snout, snout * 1.6, s ) )
    start = snout * 0.6
    head = envelope( ( s - start ) / ( 1 - start ), **kw ) if s > start else 0.0
    return ( tube ** 4 + head ** 4 ) ** 0.25


def rounded_edge( root, height, front=0.2, back=0.25, power=0.6 ):
    """ A soft-rayed fin's outline: up from its front, `height(i)` over the root, rounding over at its back. """
    def edge( i ):
        x, z = root( i )
        h = height( i ) * smoothstep( 0.0, front, i ) ** power * ( 1 - smoothstep( 1 - back, 1.0, i ) ** 2.2 ) ** 0.5
        return ( x - 0.15 * h * i, z + h )
    return edge


def fan_tail( x_root, z_low, z_high, outline, steps=17, thickness=0.12, mesh=None ):
    """ A tail: its root a vertical line at x_root, its outline(i) from the lower lobe's tip (i 0) round to the upper
    one's (i 1). """
    median_fin( mesh, lambda i: ( x_root, lerp( z_low, z_high, i ) ), outline, thickness, chord_steps=steps, span_steps=6 )


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
          stations=32, ring=22 )
    # First dorsal: tall, its trailing edge swept and a little concave
    fin( m, ( 10.0, 0, 4.4 ), ( -2.0, 0, 3.6 ), ( -4.5, 0, 15.5 ), ( 6.5, 0, 12.5 ), ( -1.8, 0, 8.0 ), thickness=1.3 )
    fin( m, ( -13.5, 0, 2.2 ), ( -18.5, 0, 1.9 ), ( -20.0, 0, 5.2 ), ( -16.5, 0, 4.6 ), ( -18.4, 0, 3.2 ), thickness=0.6 )
    # Pectorals: long and sickle-shaped, out and down
    paired_fin( m, ( 17.5, 3.6, -2.6 ), ( 10.5, 3.4, -3.0 ), ( 1.0, 21.5, -9.0 ), ( 13.0, 13.5, -5.4 ), ( 8.5, 9.0, -5.0 ),
                thickness=1.1 )
    paired_fin( m, ( -8.0, 1.8, -3.2 ), ( -12.0, 1.2, -2.8 ), ( -14.5, 5.0, -6.0 ), ( -10.0, 4.0, -5.2 ), None,
                thickness=0.55, role="pelvic" )
    fin( m, ( -15.0, 0, -2.2 ), ( -19.0, 0, -1.6 ), ( -20.5, 0, -5.0 ), ( -16.8, 0, -4.4 ), ( -19.2, 0, -2.8 ), thickness=0.55 )
    # The tail: the upper lobe long and raised, the lower one shorter (heterocercal)
    fin( m, ( -20.5, 0, 1.4 ), ( -26.0, 0, 0.6 ), ( -37.0, 0, 13.0 ), ( -28.0, 0, 6.8 ), ( -28.5, 0, 3.6 ), thickness=1.0,
         span_steps=10 )
    fin( m, ( -22.0, 0, -0.2 ), ( -26.0, 0, 0.6 ), ( -31.5, 0, -8.5 ), ( -25.5, 0, -5.4 ), ( -28.5, 0, -2.8 ), thickness=0.8 )
    return m


def yellow_tang():
    """ Yellow tang, 8 long: a tall, flat disc of a body with a long dorsal and anal fin, and a short snout. """
    m = Mesh()
    b = body( m, 4.0, -2.9,
              half_width=lambda s: 0.6 * envelope( s, 0.38, 0.35, 0.7 ),
              half_up=lambda s: 2.55 * envelope( s, 0.45, 0.24, 0.9 ) * ( 0.55 + 0.45 * smoothstep( 0.0, 0.3, s ) ),
              half_down=lambda s: 2.4 * envelope( s, 0.42, 0.24, 0.9 ) * ( 0.6 + 0.4 * smoothstep( 0.0, 0.3, s ) ),
              centre=lambda s: -0.35 * ( 1 - smoothstep( 0.0, 0.25, s ) ), stations=24, ring=18 )
    dorsal = lambda i: ( lerp( 2.2, -2.6, i ), b.top( lerp( 2.2, -2.6, i ), 0.12 ) )
    median_fin( m, dorsal, rounded_edge( dorsal, lambda i: lerp( 0.9, 1.25, smoothstep( 0, 0.7, i ) ), 0.12, 0.3 ), 0.22 )
    anal = lambda i: ( lerp( 0.9, -2.6, i ), b.bottom( lerp( 0.9, -2.6, i ), 0.12 ) )
    anal_edge = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: lerp( 0.9, 1.15, smoothstep( 0, 0.7, i ) ), 0.12, 0.3 )
    median_fin( m, anal, lambda i: ( anal_edge( i )[0], -anal_edge( i )[1] ), 0.22 )
    fan_tail( -2.65, -0.42, 0.42, lambda i: ( -3.95 + 0.25 * math.sin( math.pi * i ) ** 2 + 0.12 * abs( math.cos( math.pi * i ) ),
                                              lerp( -1.5, 1.5, i ) ), mesh=m, thickness=0.16 )
    side_fins( m, b, 0.85, -0.45, 0.4, 1.25 )
    side_fins( m, b, 1.15, -1.65, 0.25, 0.8, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def blue_tang():
    """ Blue tang, 7 long: an oval, flat body, a long low dorsal and anal fin and a straight-edged tail. """
    m = Mesh()
    b = body( m, 3.1, -2.3,
              half_width=lambda s: 0.45 * envelope( s, 0.38, 0.32, 0.7 ),
              half_up=lambda s: 1.62 * envelope( s, 0.42, 0.24, 0.85 ),
              half_down=lambda s: 1.5 * envelope( s, 0.42, 0.24, 0.85 ),
              centre=lambda s: -0.12 * ( 1 - smoothstep( 0.0, 0.3, s ) ), stations=26, ring=18 )
    dorsal = lambda i: ( lerp( 1.7, -2.0, i ), b.top( lerp( 1.7, -2.0, i ), 0.12 ) )
    median_fin( m, dorsal, rounded_edge( dorsal, lambda i: lerp( 0.5, 0.78, smoothstep( 0, 0.6, i ) ), 0.08, 0.25 ), 0.16 )
    anal = lambda i: ( lerp( 0.5, -2.0, i ), b.bottom( lerp( 0.5, -2.0, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: lerp( 0.5, 0.7, smoothstep( 0, 0.6, i ) ), 0.08, 0.25 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.16 )
    # A straight-edged tail with its corners drawn out a little
    fan_tail( -2.05, -0.36, 0.36, lambda i: ( -3.45 - 0.42 * abs( 2 * i - 1 ) ** 3, lerp( -1.32, 1.32, i ) ), mesh=m )
    side_fins( m, b, 1.05, -0.45, 0.35, 1.1 )
    side_fins( m, b, 1.0, -1.2, 0.2, 0.75, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def chromis():
    """ Blue-green chromis, 5 long: a small, deep-ish body and a deeply forked tail. """
    m = Mesh()
    b = body( m, 2.5, -1.7,
              half_width=lambda s: 0.42 * envelope( s, 0.35, 0.3 ),
              half_up=lambda s: 0.9 * envelope( s, 0.4, 0.3, 0.7 ),
              half_down=lambda s: 0.8 * envelope( s, 0.38, 0.3, 0.7 ), stations=18, ring=14 )
    dorsal = lambda i: ( lerp( 1.2, -1.4, i ), b.top( lerp( 1.2, -1.4, i ), 0.12 ) )
    median_fin( m, dorsal, rounded_edge( dorsal, lambda i: lerp( 0.42, 0.55, i ), 0.1, 0.22 ), 0.08, chord_steps=8, span_steps=5 )
    anal = lambda i: ( lerp( -0.3, -1.4, i ), b.bottom( lerp( -0.3, -1.4, i ), 0.12 ) )
    median_fin( m, anal, lambda i: ( anal( i )[0] - 0.2 * i, anal( i )[1] - 0.5 * smoothstep( 0, 0.25, i ) * ( 1 - smoothstep( 0.75, 1, i ) ** 2 ) ** 0.5 ),
                0.08, chord_steps=6, span_steps=5 )
    # Deeply forked
    fan_tail( -1.5, -0.28, 0.28, lambda i: ( -2.6 + 0.75 * math.sin( math.pi * i ) ** 1.3, lerp( -0.95, 0.95, i ) ), mesh=m,
              thickness=0.07 )
    side_fins( m, b, 0.75, -0.2, 0.25, 0.75 )
    side_fins( m, b, 0.65, -0.68, 0.15, 0.45, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def copperband():
    """ Copperband butterflyfish, 6 long: a tall, very flat disc, a long thin snout for picking in crevices, and its
    soft dorsal and anal fins rounded out behind. """
    m = Mesh()
    snout = 0.22
    b = body( m, 3.05, -1.75,
              half_width=lambda s: 0.36 * snouted( s, snout, 0.12, 0.36, widest=0.42, peduncle=0.35, nose_power=0.8 ),
              half_up=lambda s: 1.6 * snouted( s, snout, 0.13, 1.6, widest=0.5, peduncle=0.22, nose_power=0.9 ),
              half_down=lambda s: 1.5 * snouted( s, snout, 0.11, 1.5, widest=0.48, peduncle=0.22, nose_power=0.9 ),
              centre=lambda s: 0.12 * ( 1 - smoothstep( 0.1, 0.4, s ) ) - 0.05, stations=34, ring=18 )
    dorsal = lambda i: ( lerp( 1.35, -1.55, i ), b.top( lerp( 1.35, -1.55, i ), 0.12 ) )
    median_fin( m, dorsal, rounded_edge( dorsal, lambda i: lerp( 0.45, 1.25, smoothstep( 0.1, 0.75, i ) ), 0.08, 0.22, 0.5 ), 0.14,
                chord_steps=12 )
    anal = lambda i: ( lerp( 0.35, -1.55, i ), b.bottom( lerp( 0.35, -1.55, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: lerp( 0.45, 1.0, smoothstep( 0.1, 0.75, i ) ), 0.08, 0.22, 0.5 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.14 )
    fan_tail( -1.55, -0.32, 0.32, lambda i: ( -2.6 + 0.05 * math.sin( math.pi * i ), lerp( -0.92, 0.92, i ) ), mesh=m,
              thickness=0.08 )
    side_fins( m, b, 0.8, -0.45, 0.3, 0.8 )
    side_fins( m, b, 0.7, -1.3, 0.15, 0.75, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def regal_angel():
    """ Regal angelfish, 8 long: a deep oval, its dorsal and anal fins running back into rounded lobes over the tail. """
    m = Mesh()
    b = body( m, 3.0, -2.45,
              half_width=lambda s: 0.62 * envelope( s, 0.42, 0.3, 0.75 ),
              half_up=lambda s: 2.0 * envelope( s, 0.46, 0.22, 0.85 ),
              half_down=lambda s: 1.85 * envelope( s, 0.46, 0.22, 0.85 ),
              centre=lambda s: -0.2 * ( 1 - smoothstep( 0.0, 0.3, s ) ), stations=26, ring=18 )
    dorsal = lambda i: ( lerp( 1.6, -2.2, i ), b.top( lerp( 1.6, -2.2, i ), 0.12 ) )
    d_edge = rounded_edge( dorsal, lambda i: lerp( 0.4, 1.3, smoothstep( 0.2, 0.85, i ) ), 0.06, 0.3, 0.5 )
    median_fin( m, dorsal, lambda i: ( d_edge( i )[0] - 0.55 * smoothstep( 0.6, 1.0, i ), d_edge( i )[1] ), 0.2, chord_steps=12 )
    anal = lambda i: ( lerp( 0.3, -2.2, i ), b.bottom( lerp( 0.3, -2.2, i ), 0.12 ) )
    a_up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: lerp( 0.5, 1.25, smoothstep( 0.2, 0.85, i ) ), 0.06, 0.3, 0.5 )
    median_fin( m, anal, lambda i: ( a_up( i )[0] - 0.5 * smoothstep( 0.6, 1.0, i ), -a_up( i )[1] ), 0.2, chord_steps=12 )
    fan_tail( -2.25, -0.45, 0.45, lambda i: ( -3.75 + 0.18 * abs( 2 * i - 1 ) ** 2, lerp( -1.15, 1.15, i ) ), mesh=m, thickness=0.14 )
    side_fins( m, b, 0.95, -0.55, 0.4, 1.15 )
    side_fins( m, b, 0.85, -1.75, 0.25, 1.0, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def moorish_idol():
    """ Moorish idol, 7 long: a tall flat disc on a short snout, its dorsal fin drawn out into a long white filament
    that trails back over the tail, and a tall swept anal fin. """
    m = Mesh()
    snout = 0.18
    b = body( m, 2.85, -1.45,
              half_width=lambda s: 0.32 * snouted( s, snout, 0.12, 0.32, widest=0.4, peduncle=0.35, nose_power=0.8 ),
              half_up=lambda s: 1.9 * snouted( s, snout, 0.14, 1.9, widest=0.4, peduncle=0.2, nose_power=0.9 ),
              half_down=lambda s: 1.95 * snouted( s, snout, 0.12, 1.95, widest=0.45, peduncle=0.2, nose_power=0.9 ),
              centre=lambda s: -0.25 * ( 1 - smoothstep( 0.1, 0.45, s ) ), stations=34, ring=18 )
    # The dorsal and anal fins are sickles swept back from the nape and the belly. The dorsal's leading rays go on into
    # the filament, which trails back past the tail.
    nape, rear = b.top( 1.4, 0.12 ), b.top( -1.25, 0.12 )
    fin( m, ( 1.4, 0, nape ), ( -1.25, 0, rear ), ( -0.9, 0, 4.05 ), ( 1.5, 0, 3.7 ), ( -1.0, 0, 2.0 ), thickness=0.12,
         chord_steps=10, span_steps=10 )
    fin( m, ( -0.7, 0, 3.98 ), ( -1.0, 0, 3.86 ), ( -4.6, 0, 2.2 ), ( -2.6, 0, 4.1 ), ( -2.7, 0, 3.6 ), thickness=0.07,
         chord_steps=4, span_steps=16 )
    belly, tail = b.bottom( 0.3, 0.12 ), b.bottom( -1.25, 0.12 )
    fin( m, ( 0.3, 0, belly ), ( -1.25, 0, tail ), ( -1.1, 0, -3.6 ), ( 0.2, 0, -3.3 ), ( -1.15, 0, -2.0 ), thickness=0.12,
         chord_steps=10, span_steps=10 )
    fan_tail( -1.3, -0.3, 0.3, lambda i: ( -2.5 + 0.1 * math.sin( math.pi * i ) - 0.12 * abs( 2 * i - 1 ) ** 3, lerp( -0.8, 0.8, i ) ),
              mesh=m, thickness=0.08 )
    side_fins( m, b, 0.65, -0.55, 0.3, 0.85 )
    side_fins( m, b, 0.65, -1.65, 0.15, 0.8, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def clownfish():
    """ Ocellaris clownfish, 3.5 long: a stout oval, rounded fins, the dorsal notched between its spiny and soft parts. """
    m = Mesh()
    b = body( m, 1.45, -1.1,
              half_width=lambda s: 0.37 * envelope( s, 0.38, 0.38, 0.65 ),
              half_up=lambda s: 0.64 * envelope( s, 0.42, 0.34, 0.75 ),
              half_down=lambda s: 0.58 * envelope( s, 0.4, 0.34, 0.75 ),
              centre=lambda s: -0.04, stations=20, ring=16 )
    dorsal = lambda i: ( lerp( 0.75, -0.95, i ), b.top( lerp( 0.75, -0.95, i ), 0.12 ) )
    def d_height( i ):
        notch = 1 - 0.55 * math.exp( -( ( i - 0.47 ) / 0.07 ) ** 2 )
        return lerp( 0.3, 0.42, smoothstep( 0.4, 0.75, i ) ) * notch
    median_fin( m, dorsal, rounded_edge( dorsal, d_height, 0.1, 0.25, 0.5 ), 0.08, chord_steps=14, span_steps=5 )
    anal = lambda i: ( lerp( -0.15, -0.95, i ), b.bottom( lerp( -0.15, -0.95, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: 0.42, 0.25, 0.35, 0.5 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.08, chord_steps=7, span_steps=5 )
    # A rounded fan of a tail
    fan_tail( -0.98, -0.22, 0.22, lambda i: ( -1.0 - 0.72 * math.sin( math.pi * lerp( 0.08, 0.92, i ) ) ** 0.6,
                                               0.62 * math.sin( math.pi * ( i - 0.5 ) ) * 1.05 ), mesh=m, thickness=0.07 )
    side_fins( m, b, 0.5, -0.2, 0.28, 0.75, breadth=0.5 )
    side_fins( m, b, 0.42, -0.52, 0.15, 0.42, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def banggai():
    """ Banggai cardinalfish, 3 long: a deep body and a big eye, a tall pointed first dorsal, the second dorsal and anal
    fins swept back into long rays, and a deeply forked tail with drawn-out lobes. """
    m = Mesh()
    b = body( m, 1.12, -0.88,
              half_width=lambda s: 0.27 * envelope( s, 0.35, 0.35, 0.7 ),
              half_up=lambda s: 0.62 * envelope( s, 0.42, 0.3, 0.8 ),
              half_down=lambda s: 0.6 * envelope( s, 0.42, 0.3, 0.8 ), stations=18, ring=14 )
    first = lambda i: ( lerp( 0.42, 0.0, i ), b.top( lerp( 0.42, 0.0, i ), 0.12 ) )
    median_fin( m, first, lambda i: ( lerp( 0.32, 0.0, i ) - 0.15 * math.sin( math.pi * i ), first( i )[1] + 1.15 * math.sin( math.pi * lerp( 0.5, 1.0, i ) ) ** 0.8 * ( 1 - i ** 4 ) ),
                0.05, chord_steps=6, span_steps=6 )
    second = lambda i: ( lerp( -0.15, -0.68, i ), b.top( lerp( -0.15, -0.68, i ), 0.12 ) )
    median_fin( m, second, lambda i: ( lerp( -1.2, -0.68, i ) - 0.1 * math.sin( math.pi * i ), second( i )[1] + lerp( 0.95, 0.0, i ** 0.8 ) ),
                0.05, chord_steps=7, span_steps=6 )
    anal = lambda i: ( lerp( -0.12, -0.68, i ), b.bottom( lerp( -0.12, -0.68, i ), 0.12 ) )
    median_fin( m, anal, lambda i: ( lerp( -1.12, -0.68, i ) - 0.1 * math.sin( math.pi * i ), anal( i )[1] - lerp( 0.9, 0.0, i ** 0.8 ) ),
                0.05, chord_steps=7, span_steps=6 )
    fan_tail( -0.78, -0.2, 0.2, lambda i: ( -1.95 + 0.95 * math.sin( math.pi * i ) ** 1.1, lerp( -0.95, 0.95, i ) ), mesh=m,
              thickness=0.05 )
    side_fins( m, b, 0.38, -0.18, 0.2, 0.55 )
    # Long pelvic fins, held down and a little forward
    side_fins( m, b, 0.4, -0.47, 0.12, 0.95, out=12, down=80, breadth=0.18, role="pelvic" )
    return m


def lionfish():
    """ Red lionfish, 13 long: a big head with tentacles over the eyes, a crest of long venomous spines, the soft
    dorsal, anal and tail fins rounded, and huge fan pectorals of separate rays, held out like wings. """
    m = Mesh()
    b = body( m, 5.0, -3.7,
              half_width=lambda s: 1.15 * envelope( s, 0.3, 0.3, 0.6 ),
              half_up=lambda s: 1.65 * envelope( s, 0.28, 0.3, 0.7 ) * ( 0.85 + 0.15 * smoothstep( 0.0, 0.2, s ) ),
              half_down=lambda s: 1.5 * envelope( s, 0.32, 0.3, 0.7 ),
              centre=lambda s: -0.25 * ( 1 - smoothstep( 0.0, 0.35, s ) ), stations=30, ring=20 )
    # Thirteen spines, each raked back, tallest in front; a low membrane between them
    heights = [ 3.4, 4.6, 5.1, 5.0, 4.6, 4.2, 3.8, 3.3, 2.9, 2.5, 2.1, 1.7, 1.3 ]
    xs = np.linspace( 3.2, -1.1, len( heights ) )
    for k, ( x0, h ) in enumerate( zip( xs, heights ) ):
        root_z = b.top( x0, 0.15 )
        rake = 0.55 + 0.06 * k
        median_fin( m, lambda i, x0=x0, root_z=root_z: ( x0 + 0.1 - 0.2 * i, root_z ),
                    lambda i, x0=x0, root_z=root_z, h=h, rake=rake: ( x0 - rake * h / 4.0 - 0.02 * ( i - 0.5 ), root_z + h ),
                    0.1, chord_steps=3, span_steps=7 )
    spine = lambda i: ( lerp( 3.35, -1.2, i ), b.top( lerp( 3.35, -1.2, i ), 0.12 ) )
    def membrane( i ):
        x, z = spine( i )
        h = float( np.interp( x, xs[::-1], np.asarray( heights[::-1] ) ) ) * 0.42
        rise = smoothstep( 0.0, 0.05, i ) * ( 1 - smoothstep( 0.93, 1.0, i ) )
        return ( x - 0.25 * rise, z + h * rise )
    median_fin( m, spine, membrane, 0.06, chord_steps=26, span_steps=4 )
    soft = lambda i: ( lerp( -1.2, -3.3, i ), b.top( lerp( -1.2, -3.3, i ), 0.12 ) )
    median_fin( m, soft, rounded_edge( soft, lambda i: 1.7, 0.1, 0.45, 0.5 ), 0.12 )
    anal = lambda i: ( lerp( -1.3, -3.2, i ), b.bottom( lerp( -1.3, -3.2, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: 1.6, 0.15, 0.45, 0.5 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.12 )
    fan_tail( -3.45, -0.5, 0.5, lambda i: ( -3.55 - 2.75 * math.sin( math.pi * lerp( 0.06, 0.94, i ) ) ** 0.55,
                                             1.75 * math.sin( math.pi * ( i - 0.5 ) ) ), mesh=m, thickness=0.12 )
    # The pectoral fans: eleven rays from the root behind the gill cover, from down-and-out round to back-and-out, a
    # membrane over their inner half
    root = np.array( ( 1.9, 0.95, -0.75 ) )
    down_out = np.array( ( 0.15, 0.62, -0.77 ) ); down_out /= np.linalg.norm( down_out )
    back_out = np.array( ( -0.93, 0.36, -0.05 ) ); back_out /= np.linalg.norm( back_out )
    normal = np.cross( down_out, back_out ); normal /= np.linalg.norm( normal )
    rays = []
    for k in range( 11 ):
        t = k / 10
        a = math.acos( float( np.clip( np.dot( down_out, back_out ), -1, 1 ) ) ) * t
        d = down_out * math.cos( a ) + np.cross( normal, down_out ) * math.sin( a )
        length = 5.6 * ( 0.72 + 0.28 * math.sin( math.pi * lerp( 0.1, 0.9, t ) ) )
        across = np.cross( normal, d ); across /= np.linalg.norm( across )
        tip = root + d * length + np.array( ( 0, 0, -0.25 ) ) * math.sin( math.pi * t )
        paired_fin( m, root + across * 0.11, root - across * 0.11, tip, root + d * length * 0.5 + across * 0.07,
                    root + d * length * 0.5 - across * 0.07, thickness=0.07, chord_steps=3, span_steps=9 )
        rays.append( ( d, length ) )
    d0, l0 = rays[0]
    d1, l1 = rays[-1]
    dm, lm = rays[5]
    paired_fin( m, root + d0 * 0.25, root + d1 * 0.25, root + dm * lm * 0.62, root + d0 * l0 * 0.6, root + d1 * l1 * 0.6,
                thickness=0.04, chord_steps=9, span_steps=6 )
    side_fins( m, b, 1.55, -1.3, 0.3, 2.3, out=15, down=60, breadth=0.25, role="pelvic" )
    # Tentacles over the eyes
    for side in ( 1, -1 ):
        fin( m, ( 3.75, 0.42 * side, 0.9 ), ( 3.55, 0.42 * side, 0.85 ), ( 3.35, 0.62 * side, 2.1 ), None, None, thickness=0.08,
             chord_steps=3, span_steps=5, role="median" )
    return m


def puffer():
    """ White-spotted puffer, 12 long: a blunt, round-headed body tapering to a stout stalk, small rounded dorsal and
    anal fins set far back, small pectorals and a rounded tail. It sculls along with them. """
    m = Mesh()
    b = body( m, 5.6, -4.1,
              half_width=lambda s: 2.45 * envelope( s, 0.36, 0.3, 0.35 ),
              half_up=lambda s: 2.25 * envelope( s, 0.38, 0.3, 0.4 ),
              half_down=lambda s: 2.55 * envelope( s, 0.36, 0.28, 0.42 ),
              centre=lambda s: -0.15, power=0.8, stations=30, ring=22 )
    dorsal = lambda i: ( lerp( -2.25, -3.35, i ), b.top( lerp( -2.25, -3.35, i ), 0.15 ) )
    median_fin( m, dorsal, rounded_edge( dorsal, lambda i: 1.45, 0.2, 0.5, 0.5 ), 0.16, chord_steps=8 )
    anal = lambda i: ( lerp( -2.2, -3.3, i ), b.bottom( lerp( -2.2, -3.3, i ), 0.15 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: 1.35, 0.2, 0.5, 0.5 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.16, chord_steps=8 )
    fan_tail( -3.85, -0.6, 0.6, lambda i: ( -4.0 - 2.25 * math.sin( math.pi * lerp( 0.06, 0.94, i ) ) ** 0.6,
                                             1.55 * math.sin( math.pi * ( i - 0.5 ) ) ), mesh=m, thickness=0.16 )
    paired_fin( m, ( 1.9, 2.0, 0.1 ), ( 1.35, 1.95, -0.4 ), ( 0.45, 3.05, -0.1 ), ( 1.4, 2.95, 0.35 ), ( 0.6, 2.6, -0.5 ),
                thickness=0.12, chord_steps=6, span_steps=6 )
    return m


def mandarin():
    """ Mandarinfish, 2.4 long: a dragonet, broad-headed and flat-bellied, with big round pectorals, splayed pelvic
    fins it props itself on, a tall first dorsal and a rounded tail. """
    m = Mesh()
    b = body( m, 1.02, -0.86,
              half_width=lambda s: 0.36 * envelope( s, 0.25, 0.35, 0.5 ),
              half_up=lambda s: 0.36 * envelope( s, 0.3, 0.32, 0.6 ),
              half_down=lambda s: 0.26 * envelope( s, 0.28, 0.32, 0.6 ),
              centre=lambda s: 0.0, stations=18, ring=16 )
    first = lambda i: ( lerp( 0.15, -0.1, i ), b.top( lerp( 0.15, -0.1, i ), 0.12 ) )
    median_fin( m, first, lambda i: ( first( i )[0] - 0.12 * math.sin( math.pi * i ), first( i )[1] + 0.42 * math.sin( math.pi * lerp( 0.35, 1.0, i ) ) ** 0.7 ),
                0.03, chord_steps=5, span_steps=5 )
    second = lambda i: ( lerp( -0.18, -0.86, i ), b.top( lerp( -0.18, -0.86, i ), 0.12 ) )
    median_fin( m, second, rounded_edge( second, lambda i: 0.3, 0.1, 0.3, 0.5 ), 0.03, chord_steps=8, span_steps=4 )
    anal = lambda i: ( lerp( -0.2, -0.86, i ), b.bottom( lerp( -0.2, -0.86, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: 0.24, 0.1, 0.3, 0.5 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.03, chord_steps=8, span_steps=4 )
    fan_tail( -0.78, -0.12, 0.12, lambda i: ( -0.8 - 0.62 * math.sin( math.pi * lerp( 0.06, 0.94, i ) ) ** 0.6,
                                               0.4 * math.sin( math.pi * ( i - 0.5 ) ) ), mesh=m, thickness=0.04 )
    paired_fin( m, ( 0.38, 0.3, 0.0 ), ( 0.18, 0.3, -0.12 ), ( -0.15, 0.78, 0.0 ), ( 0.3, 0.72, 0.18 ), ( -0.15, 0.58, -0.15 ),
                thickness=0.035, chord_steps=6, span_steps=6 )
    paired_fin( m, ( 0.55, 0.15, -0.18 ), ( 0.35, 0.15, -0.2 ), ( 0.42, 0.62, -0.3 ), ( 0.62, 0.45, -0.22 ), None,
                thickness=0.03, role="pelvic", chord_steps=5, span_steps=5 )
    return m


def fusilier():
    """ Yellow-and-blueback fusilier, 9 long: a slim, pointed, fast schooling fish with a deeply forked tail. """
    m = Mesh()
    b = body( m, 3.8, -3.0,
              half_width=lambda s: 0.62 * envelope( s, 0.38, 0.22, 0.6 ),
              half_up=lambda s: 1.12 * envelope( s, 0.4, 0.24, 0.7 ),
              half_down=lambda s: 1.0 * envelope( s, 0.38, 0.24, 0.7 ),
              centre=lambda s: -0.08 * ( 1 - smoothstep( 0, 0.3, s ) ), stations=26, ring=18 )
    dorsal = lambda i: ( lerp( 1.6, -2.3, i ), b.top( lerp( 1.6, -2.3, i ), 0.12 ) )
    median_fin( m, dorsal, rounded_edge( dorsal, lambda i: lerp( 0.55, 0.35, i ), 0.1, 0.2, 0.6 ), 0.1, chord_steps=10 )
    anal = lambda i: ( lerp( -0.6, -2.3, i ), b.bottom( lerp( -0.6, -2.3, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: lerp( 0.5, 0.3, i ), 0.1, 0.2, 0.6 )
    median_fin( m, anal, lambda i: ( up( i )[0], -up( i )[1] ), 0.1 )
    fan_tail( -2.75, -0.3, 0.3, lambda i: ( -5.1 + 1.4 * math.sin( math.pi * i ) ** 1.4, 1.65 * ( 2 * i - 1 ) ), mesh=m, thickness=0.1 )
    side_fins( m, b, 1.55, -0.35, 0.3, 1.2, breadth=0.25 )
    side_fins( m, b, 1.15, -0.88, 0.2, 0.6, out=15, down=65, breadth=0.3, role="pelvic" )
    return m


def sergeant_major():
    """ Indo-Pacific sergeant, 6 long: a deep damselfish with a long dorsal fin and a forked tail. """
    m = Mesh()
    b = body( m, 2.55, -1.95,
              half_width=lambda s: 0.52 * envelope( s, 0.38, 0.3, 0.7 ),
              half_up=lambda s: 1.42 * envelope( s, 0.42, 0.26, 0.8 ),
              half_down=lambda s: 1.3 * envelope( s, 0.42, 0.26, 0.8 ),
              centre=lambda s: -0.1 * ( 1 - smoothstep( 0, 0.3, s ) ), stations=24, ring=18 )
    dorsal = lambda i: ( lerp( 1.35, -1.75, i ), b.top( lerp( 1.35, -1.75, i ), 0.12 ) )
    d_edge = rounded_edge( dorsal, lambda i: lerp( 0.45, 0.85, smoothstep( 0.5, 0.85, i ) ), 0.08, 0.25, 0.5 )
    median_fin( m, dorsal, lambda i: ( d_edge( i )[0] - 0.3 * smoothstep( 0.7, 1.0, i ), d_edge( i )[1] ), 0.12, chord_steps=12 )
    anal = lambda i: ( lerp( -0.25, -1.75, i ), b.bottom( lerp( -0.25, -1.75, i ), 0.12 ) )
    up = rounded_edge( lambda i: ( anal( i )[0], -anal( i )[1] ), lambda i: lerp( 0.6, 0.85, smoothstep( 0.3, 0.8, i ) ), 0.12, 0.25, 0.5 )
    median_fin( m, anal, lambda i: ( up( i )[0] - 0.3 * smoothstep( 0.7, 1.0, i ), -up( i )[1] ), 0.12 )
    fan_tail( -1.75, -0.32, 0.32, lambda i: ( -3.2 + 0.6 * math.sin( math.pi * i ) ** 1.5, 1.08 * ( 2 * i - 1 ) ), mesh=m, thickness=0.09 )
    side_fins( m, b, 0.9, -0.42, 0.35, 1.05 )
    side_fins( m, b, 0.82, -1.2, 0.2, 0.75, out=15, down=65, breadth=0.3, role="pelvic" )
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


def custom_fin( mesh, root_le, root_te, tip, le_bend, te_bend, thickness, uv, chord_steps=7, span_steps=8 ):
    """ fin(), with the manta's own UVs. """
    root_le, root_te, tip = ( np.asarray( p, float ) for p in ( root_le, root_te, tip ) )
    le_bend = np.asarray( le_bend if le_bend is not None else ( root_le + tip ) / 2, float )
    te_bend = np.asarray( te_bend if te_bend is not None else ( root_te + tip ) / 2, float )
    normal = np.cross( tip - ( root_le + root_te ) / 2, root_te - root_le )
    normal /= np.linalg.norm( normal )
    sheets = []
    for side in ( 1.0, -1.0 ):
        positions, uvs = [], []
        for a in range( chord_steps ):
            i = a / ( chord_steps - 1 )
            for b in range( span_steps ):
                j = b / ( span_steps - 1 )
                p = lerp( bezier( root_le, le_bend, tip, j ), bezier( root_te, te_bend, tip, j ), i )
                t = thickness * ( 1 - 0.5 * j ) * ( 1 - j ) ** 0.3 * ( 4 * i * ( 1 - i ) ) ** 0.6
                positions.append( p + side * normal * t * 0.5 )
                uvs.append( uv( p, side ) )
        sheets.append( ( positions, uvs, grid_triangles( chord_steps, span_steps ) ) )
    mesh.add_part( sheets, "custom" )


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
    m.add_part( sheets, "custom" )

    top_uv = lambda p, side: manta_uv( p[0], p[1], side > 0 )
    for s in ( 1, -1 ):
        custom_fin( m, ( 22.5, 13.5 * s, 0.6 ), ( 21.0, 8.5 * s, 0.4 ), ( 31.5, 11.5 * s, -2.2 ), ( 28.5, 14.0 * s, -0.6 ),
                    ( 28.0, 9.5 * s, -1.0 ), 1.6, top_uv )
    custom_fin( m, ( -18.0, 0, 3.5 ), ( -23.5, 0, 2.6 ), ( -26.0, 0, 7.0 ), ( -21.5, 0, 6.8 ), None, 0.9, top_uv )
    positions, uvs = [], []
    stations, ring = 14, 8
    for k in range( stations ):
        s = k / ( stations - 1 )
        x = lerp( -20.0, MANTA_BACK, s )
        r = 1.4 * ( 1 - s ) ** 0.8 * smoothstep( 0.0, 0.02, s )
        for j in range( ring + 1 ):
            th = 2 * math.pi * j / ring
            positions.append( ( x, r * math.sin( th ), 0.5 - 1.5 * s * s + r * math.cos( th ) ) )
            uvs.append( manta_uv( x, 0.0, True ) )
    m.add_part( [ ( positions, uvs, grid_triangles( stations, ring + 1 ) ) ], "custom" )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Painting: each triangle drawn into the texture with its points' positions and numbers, then a painter per animal

def rasterise( mesh ):
    """ Fields over the texture: role (0 where nothing is), the position x y z and the three numbers, each texel the
    one its triangle has there. Gaps are filled from their neighbours, so seams don't show. """
    H = W = TEXTURE
    role = np.zeros( ( H, W ), np.int8 )
    fields = np.zeros( ( 6, H, W ), np.float32 )
    pos = np.array( mesh.positions )
    att = np.array( mesh.attrs )
    data = np.concatenate( [ pos, att ], axis=1 )
    uv = np.array( [ u if u is not None else ( 0, 0 ) for u in mesh.uvs ] )
    px = uv[:, 0] * W - 0.5
    py = ( 1 - uv[:, 1] ) * H - 0.5
    roles = np.array( [ ROLES[r] for r in mesh.roles ] )
    for a, b, c in mesh.triangles:
        if roles[a] == ROLES["custom"]:
            continue
        xs, ys = px[[ a, b, c ]], py[[ a, b, c ]]
        x0, x1 = int( max( 0, math.floor( xs.min() ) ) ), int( min( W - 1, math.ceil( xs.max() ) ) )
        y0, y1 = int( max( 0, math.floor( ys.min() ) ) ), int( min( H - 1, math.ceil( ys.max() ) ) )
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid( np.arange( x0, x1 + 1 ), np.arange( y0, y1 + 1 ) )
        d = ( ys[1] - ys[2] ) * ( xs[0] - xs[2] ) + ( xs[2] - xs[1] ) * ( ys[0] - ys[2] )
        if abs( d ) < 1e-9:
            continue
        w0 = ( ( ys[1] - ys[2] ) * ( gx - xs[2] ) + ( xs[2] - xs[1] ) * ( gy - ys[2] ) ) / d
        w1 = ( ( ys[2] - ys[0] ) * ( gx - xs[2] ) + ( xs[0] - xs[2] ) * ( gy - ys[2] ) ) / d
        w2 = 1 - w0 - w1
        inside = ( w0 >= -0.02 ) & ( w1 >= -0.02 ) & ( w2 >= -0.02 )
        if not inside.any():
            continue
        values = w0[..., None] * data[a] + w1[..., None] * data[b] + w2[..., None] * data[c]
        yy, xx = gy[inside], gx[inside]
        fields[:, yy, xx] = values[inside].T
        role[yy, xx] = roles[a]
    # Fill the gaps round each island from its neighbours
    for _ in range( 10 ):
        empty = role == 0
        if not empty.any():
            break
        for dy, dx in ( ( 0, 1 ), ( 0, -1 ), ( 1, 0 ), ( -1, 0 ) ):
            src_role = np.roll( role, ( dy, dx ), axis=( 0, 1 ) )
            take = empty & ( src_role != 0 )
            role[take] = src_role[take]
            fields[:, take] = np.roll( fields, ( dy, dx ), axis=( 1, 2 ) )[:, take]
            empty = role == 0
    return role, fields


class Canvas:
    """ What a painter works with: masks for the body and each kind of fin, the position (x, y, z), and the body's s,
    up (-1 belly to 1 back) and side (0 at the top and bottom, 1 at the flank), or a fin's span (0 root to 1 edge) and
    chord. """

    def __init__( self, mesh ):
        self.role, f = rasterise( mesh )
        self.x, self.y, self.z = f[0], f[1], f[2]
        self.a, self.b, self.c = f[3], f[4], f[5]
        self.is_body = self.role == ROLES["body"]
        self.is_median = self.role == ROLES["median"]
        self.is_pectoral = self.role == ROLES["pectoral"]
        self.is_pelvic = self.role == ROLES["pelvic"]
        self.is_fin = ~self.is_body
        self.s, self.up, self.side = self.a, self.b, np.abs( self.c )
        self.span, self.chord = self.a, self.b
        self.shape = self.x.shape
        rng = np.random.default_rng( 11 )
        self.colour = np.zeros( self.shape + ( 3, ), np.float32 )

    def fill( self, colour, mask=None ):
        colour = np.broadcast_to( np.asarray( colour, np.float32 ), self.shape + ( 3, ) )
        if mask is None:
            self.colour[...] = colour
        else:
            m = np.asarray( mask, np.float32 )[..., None]
            self.colour = self.colour + ( colour - self.colour ) * m

    def noise( self, scale, seed, a=None, b=None ):
        """ Smooth noise over two of the fields (x and z unless given), 0..1. """
        a = self.x if a is None else a
        b = self.z if b is None else b
        out = np.zeros( self.shape, np.float32 )
        amp, total = 1.0, 0.0
        for octave in range( 3 ):
            k = scale * 2 ** octave
            ph = np.random.default_rng( seed + octave ).uniform( 0, 6.28, 6 )
            out += amp * ( np.sin( a * k + ph[0] + np.sin( b * k * 0.7 + ph[1] ) ) * np.sin( b * k * 1.3 + ph[2] + np.sin( a * k * 0.6 + ph[3] ) ) )
            total += amp
            amp *= 0.5
        return 0.5 + 0.5 * out / total

    def scales( self, size, strength=0.05 ):
        """ The faint lattice of scales over the body: brighter at each scale's edge. """
        k = 2 * math.pi / size
        lattice = np.abs( np.sin( ( self.x + self.z * 0.55 ) * k ) * np.sin( ( self.x - self.z * 0.55 ) * k ) )
        shade = 1 + strength * ( lattice - 0.5 ) * self.is_body
        self.colour *= shade[..., None]

    def eye( self, x, z, r, iris, ring=None, pupil=( 0.02, 0.02, 0.025 ) ):
        """ An eye on both flanks: a dark pupil, its iris, a thin ring round it, a glint. """
        d = np.hypot( self.x - x, self.z - z ) / r
        on = self.is_body & ( self.side > 0.35 )
        self.fill( ring if ring is not None else np.asarray( iris ) * 0.6, on * smoothstep( 1.06, 0.98, d ) * 0.85 )
        self.fill( iris, on * smoothstep( 0.98, 0.9, d ) )
        self.fill( pupil, on * smoothstep( 0.62, 0.55, d ) )
        glint = np.hypot( self.x - ( x + 0.25 * r ), self.z - ( z + 0.25 * r ) ) / r
        self.fill( ( 0.85, 0.88, 0.9 ), on * smoothstep( 0.16, 0.08, glint ) * 0.8 )

    def done( self, grain=0.04, seed=0 ):
        g = self.noise( 9.0, seed + 100 )
        self.colour *= ( 1 - grain + 2 * grain * g )[..., None]
        return np.clip( self.colour, 0, 1 )


def band( v, centre, half, soft=0.03 ):
    return smoothstep( half + soft, half - soft, np.abs( v - centre ) )


def outlined_band( c, v, centre, half, fill, edge, edge_width, mask=None ):
    """ A band of `fill` along v, edged on both sides by `edge`. """
    m = np.ones( c.shape ) if mask is None else mask
    c.fill( edge, m * band( v, centre, half + edge_width, 0.02 ) )
    c.fill( fill, m * band( v, centre, half, 0.02 ) )


def paint_shark( mesh ):
    c = Canvas( mesh )
    grain = c.noise( 0.25, 1 )
    back = np.array( ( 0.34, 0.37, 0.40 ) )
    belly = np.array( ( 0.86, 0.86, 0.84 ) )
    up = np.where( c.is_body, c.up, 1.0 )
    c.fill( belly )
    c.fill( back, smoothstep( -0.42, -0.12, up ) )
    c.colour *= ( 0.94 + 0.1 * grain )[..., None]
    # Gill slits: five short dark lines on each side, behind the eye
    for k in range( 5 ):
        line = band( c.x, 25.0 - 1.1 * k, 0.12, 0.08 ) * band( c.z, -0.6, 1.8, 0.4 ) * c.is_body * ( c.side > 0.6 )
        c.fill( ( 0.16, 0.17, 0.18 ), line * 0.85 )
    c.eye( 30.5, 1.6, 0.55, ( 0.12, 0.13, 0.1 ) )
    # Fins: the back's grey; black tips and a dark trailing edge (the reef shark's marks)
    fins = c.is_fin
    c.fill( back * 0.92 * ( 0.94 + 0.1 * grain )[..., None], fins )
    tip = smoothstep( 0.72, 0.93, c.span ) + 0.7 * smoothstep( 0.8, 0.97, c.chord ) * smoothstep( 0.3, 0.6, c.span )
    tail = ( c.x < -26 ) & c.is_median
    c.fill( ( 0.05, 0.05, 0.06 ), fins * np.clip( tip * ( c.z < 10 ) + tail * smoothstep( 9, 12, np.abs( c.z ) ), 0, 1 ) )
    return c.done( 0.02 )


def paint_tang( mesh ):
    c = Canvas( mesh )
    yellow = np.array( ( 0.98, 0.8, 0.07 ) )
    c.fill( yellow )
    c.fill( ( 1.0, 0.88, 0.32 ), c.is_body * smoothstep( -0.5, -0.9, c.up ) * 0.4 )
    c.fill( ( 0.95, 0.72, 0.05 ), c.is_body * smoothstep( 0.4, 0.95, c.up ) * 0.5 )
    # The scalpel at the tail's base: white, in a pale sheath
    spine = np.exp( -( ( c.x + 2.45 ) / 0.13 ) ** 2 - ( ( c.z + 0.05 ) / 0.13 ) ** 2 ) * c.is_body * ( c.side > 0.5 )
    c.fill( ( 0.97, 0.96, 0.9 ), np.clip( spine * 2.0, 0, 1 ) )
    c.eye( 2.65, 0.8, 0.3, ( 0.15, 0.12, 0.05 ), ring=( 0.75, 0.55, 0.05 ) )
    c.fill( yellow * 0.95, c.is_fin )
    c.fill( ( 0.93, 0.66, 0.04 ), c.is_fin * smoothstep( 0.7, 1.0, c.span ) * 0.5 )
    c.scales( 0.16, 0.05 )
    return c.done( 0.04, 3 )


def paint_blue_tang( mesh ):
    c = Canvas( mesh )
    blue = np.array( ( 0.06, 0.26, 0.82 ) )
    black = np.array( ( 0.02, 0.025, 0.05 ) )
    yellow = np.array( ( 1.0, 0.82, 0.08 ) )
    c.fill( blue )
    c.fill( ( 0.18, 0.42, 0.9 ), c.is_body * smoothstep( -0.2, -0.85, c.up ) * 0.6 )
    # The palette: a black band from the eye back along the upper flank to the tail, looping round a blue oval
    xn = ( 3.1 - c.x ) / 5.4
    zr = np.where( c.is_body, c.up, np.clip( c.z / 1.6, -1.5, 1.5 ) )
    path = 0.28 + 0.1 * np.sin( math.pi * np.clip( ( xn - 0.15 ) / 0.75, 0, 1 ) ) - 0.25 * smoothstep( 0.7, 0.95, xn )
    stripe = smoothstep( 0.17, 0.11, np.abs( zr - path ) ) * smoothstep( 0.08, 0.14, xn ) * smoothstep( 0.98, 0.9, xn )
    oval = ( ( xn - 0.48 ) / 0.22 ) ** 2 + ( ( zr - 0.66 ) / 0.26 ) ** 2
    loop = smoothstep( 1.55, 1.3, oval ) * smoothstep( 0.62, 0.8, oval )
    c.fill( black, c.is_body * np.clip( stripe + loop + smoothstep( 0.82, 0.92, zr ) * smoothstep( 0.2, 0.3, xn ) * smoothstep( 0.85, 0.75, xn ), 0, 1 ) )
    # The tail's stalk and tail: yellow, the tail edged black above and below
    c.fill( yellow, smoothstep( 0.84, 0.94, xn ) * ( 1 - stripe ) * np.where( c.is_body, smoothstep( 0.45, 0.2, np.abs( zr - 0.0 ) ), 1.0 ) )
    tail = c.is_median & ( c.x < -2.05 )
    c.fill( yellow, tail )
    c.fill( black, tail * smoothstep( 0.95, 1.15, np.abs( c.z ) ) )
    # Dorsal and anal fins: blue, a black margin
    fins = c.is_median & ( c.x >= -2.05 )
    c.fill( black, fins * smoothstep( 0.55, 0.85, c.span ) )
    c.fill( ( 0.95, 0.85, 0.35 ), c.is_pectoral * 0.85 )
    c.fill( black, c.is_pelvic * 0.6 )
    c.eye( 2.2, 0.35, 0.27, ( 0.1, 0.12, 0.25 ), ring=( 0.02, 0.03, 0.06 ) )
    c.scales( 0.15, 0.05 )
    return c.done( 0.04, 4 )


def paint_chromis( mesh ):
    c = Canvas( mesh )
    back = np.array( ( 0.12, 0.45, 0.55 ) )
    flank = np.array( ( 0.4, 0.82, 0.78 ) )
    belly = np.array( ( 0.8, 0.93, 0.88 ) )
    c.fill( flank )
    c.fill( back, c.is_body * smoothstep( 0.35, 0.85, c.up ) )
    c.fill( belly, c.is_body * smoothstep( -0.4, -0.85, c.up ) )
    # Iridescence: the flank shifts from green to blue along the body
    c.fill( ( 0.35, 0.7, 0.95 ), c.is_body * smoothstep( 0.4, 1.0, c.s ) * smoothstep( -0.3, 0.3, c.up ) * 0.5 )
    c.fill( flank * 0.85, c.is_fin )
    c.fill( ( 0.15, 0.35, 0.42 ), c.is_median * smoothstep( 0.7, 1.0, c.span ) * 0.6 )
    c.eye( 1.95, 0.25, 0.2, ( 0.1, 0.2, 0.2 ) )
    c.scales( 0.12, 0.06 )
    return c.done( 0.04, 5 )


def paint_copperband( mesh ):
    c = Canvas( mesh )
    white = np.array( ( 0.93, 0.93, 0.88 ) )
    copper = np.array( ( 0.95, 0.5, 0.1 ) )
    dark = np.array( ( 0.08, 0.07, 0.12 ) )
    c.fill( white )
    c.fill( ( 0.97, 0.9, 0.72 ), c.is_body * smoothstep( 0.3, 0.9, c.up ) * 0.4 )
    # The snout: yellow-orange above, pale below
    snout = c.is_body * smoothstep( 2.0, 2.25, c.x )
    c.fill( ( 0.97, 0.72, 0.25 ), snout * smoothstep( -0.3, 0.5, c.up ) )
    # Five bands, each copper edged in black: through the eye, at the gill, mid body, over the rear, round the stalk
    for centre, half, slant in ( ( 1.62, 0.13, 0.08 ), ( 0.88, 0.17, 0.05 ), ( 0.05, 0.22, 0.0 ), ( -0.82, 0.2, -0.08 ) ):
        v = c.x + slant * c.z
        outlined_band( c, v, centre, half, copper, dark, 0.045 )
        c.fill( ( 0.82, 0.86, 0.95 ), band( v, centre, half + 0.075, 0.015 ) * ( 1 - band( v, centre, half + 0.045, 0.015 ) ) * 0.6 )
    stalk = c.x + 0.0 * c.z
    c.fill( dark, band( stalk, -1.48, 0.07, 0.02 ) * c.is_body )
    c.fill( copper, band( stalk, -1.48, 0.035, 0.015 ) * c.is_body )
    # The false eye on the soft dorsal: black ringed in white
    d = np.hypot( c.x + 0.95, c.z - 2.05 )
    c.fill( white, c.is_median * smoothstep( 0.24, 0.2, d ) )
    c.fill( dark, c.is_median * smoothstep( 0.18, 0.14, d ) )
    # Tail: clear and pale, a black bar near its base and a thin dark edge
    tail = c.is_median & ( c.x < -1.6 )
    c.fill( ( 0.85, 0.85, 0.75 ), tail )
    c.fill( dark, tail * band( c.x, -1.85, 0.06, 0.02 ) )
    c.fill( ( 0.95, 0.65, 0.2 ), c.is_median * ( c.x >= -1.6 ) * smoothstep( 0.8, 0.95, c.span ) * 0.7 )
    c.fill( ( 0.9, 0.88, 0.8 ), c.is_pectoral )
    c.fill( copper, c.is_pelvic )
    c.eye( 1.62, 0.3, 0.13, ( 0.12, 0.08, 0.05 ), ring=dark )
    c.scales( 0.11, 0.05 )
    return c.done( 0.03, 6 )


def paint_regal( mesh ):
    c = Canvas( mesh )
    orange = np.array( ( 0.98, 0.6, 0.1 ) )
    white = np.array( ( 0.93, 0.95, 1.0 ) )
    navy = np.array( ( 0.05, 0.1, 0.38 ) )
    c.fill( orange )
    c.fill( ( 1.0, 0.8, 0.2 ), smoothstep( -1.2, -2.6, c.x ) )
    # The face: blue-grey ahead of the first bar
    c.fill( ( 0.42, 0.48, 0.62 ), c.is_body * smoothstep( 2.0, 2.4, c.x ) * 0.8 )
    # Bars: white edged in navy, slanting back from the top
    for k, centre in enumerate( np.linspace( 2.05, -1.65, 9 ) ):
        v = c.x + 0.22 * c.z
        mask = np.where( c.is_body | c.is_median, 1.0, 0.0 ) * ( c.x > -2.25 )
        outlined_band( c, v, centre, 0.085, white, navy, 0.05, mask )
    # The rear dorsal: dark blue with pale blue streaks; the anal fin striped blue
    rear_dorsal = c.is_median * ( c.z > 1.5 ) * smoothstep( -0.2, -0.8, c.x )
    c.fill( navy, rear_dorsal )
    streak = np.abs( np.sin( ( c.z * 1.0 - c.x * 0.6 ) * 9.0 ) ) < 0.18
    c.fill( ( 0.45, 0.65, 0.95 ), rear_dorsal * streak )
    anal = c.is_median * ( c.z < -1.6 )
    c.fill( ( 0.98, 0.72, 0.15 ), anal )
    c.fill( ( 0.15, 0.35, 0.85 ), anal * ( np.abs( np.sin( ( c.z + 0.4 * c.x ) * 8.0 ) ) < 0.22 ) )
    tail = c.is_median & ( c.x < -2.25 )
    c.fill( ( 1.0, 0.82, 0.18 ), tail )
    c.fill( ( 1.0, 0.75, 0.2 ), c.is_pectoral )
    c.fill( ( 1.0, 0.7, 0.15 ), c.is_pelvic )
    c.fill( ( 0.3, 0.55, 0.95 ), c.is_pelvic * band( c.chord, 0.2, 0.08 ) )
    c.eye( 2.15, 0.75, 0.28, ( 0.15, 0.1, 0.08 ), ring=navy )
    c.scales( 0.14, 0.06 )
    return c.done( 0.04, 7 )


def paint_idol( mesh ):
    c = Canvas( mesh )
    white = np.array( ( 0.95, 0.95, 0.9 ) )
    black = np.array( ( 0.03, 0.03, 0.035 ) )
    yellow = np.array( ( 0.98, 0.84, 0.22 ) )
    c.fill( white )
    # Yellow over the rear body and the dorsal's base
    c.fill( yellow, smoothstep( 0.0, -0.4, c.x ) * smoothstep( -1.6, -1.2, c.x ) * ( c.is_body | ( c.is_median & ( np.abs( c.z ) < 2.4 ) ) ) )
    c.fill( yellow, c.is_body * smoothstep( 0.3, 0.9, c.up ) * smoothstep( 1.2, 0.6, c.x ) * 0.7 )
    # Two broad black bands: the first from the nape down through the eye to the belly, the second over the rear
    first = c.x + 0.12 * c.z
    c.fill( black, band( first, 1.2, 0.36, 0.03 ) * ( c.is_body | c.is_median ) * ( c.z < 3.3 ) )
    second = c.x + 0.25 * c.z
    c.fill( black, band( second, -0.6, 0.4, 0.03 ) * ( c.is_body | c.is_median ) * ( c.z < 3.0 ) )
    c.fill( white, band( second, -0.6 + 0.47, 0.04, 0.015 ) * ( c.is_body | c.is_median ) * ( c.z < 2.8 ) * 0.9 )
    # The snout: an orange saddle and a black tip
    c.fill( ( 0.95, 0.55, 0.12 ), c.is_body * band( c.x, 2.4, 0.16 ) * smoothstep( 0.0, 0.6, c.up ) )
    c.fill( black, c.is_body * smoothstep( 2.68, 2.75, c.x ) )
    # The filament white; the tail black with a white edge
    tail = c.is_median & ( c.x < -1.35 ) & ( np.abs( c.z ) < 1.0 )
    c.fill( black, tail )
    c.fill( white, tail * smoothstep( 0.8, 0.95, c.span ) )
    c.fill( white, c.is_median * ( c.z > 2.6 ) )
    c.fill( ( 0.9, 0.9, 0.85 ), c.is_pectoral )
    c.fill( black, c.is_pelvic )
    c.eye( 1.25, 0.45, 0.16, ( 0.25, 0.22, 0.1 ), ring=black )
    c.scales( 0.12, 0.04 )
    return c.done( 0.03, 8 )


def paint_clownfish( mesh ):
    c = Canvas( mesh )
    orange = np.array( ( 1.0, 0.45, 0.06 ) )
    white = np.array( ( 0.98, 0.98, 0.96 ) )
    black = np.array( ( 0.03, 0.03, 0.03 ) )
    c.fill( orange )
    c.fill( ( 1.0, 0.58, 0.18 ), c.is_body * smoothstep( -0.3, -0.9, c.up ) * 0.5 )
    zr = np.where( c.is_body, c.up, 0.0 )
    # Three white bars edged in black: behind the eye, the middle one bulging forward, round the stalk
    for centre, half, bulge in ( ( 0.82, 0.1, -0.06 ), ( 0.05, 0.14, 0.2 ), ( -0.86, 0.075, 0.0 ) ):
        v = c.x - bulge * ( 1 - zr * zr )
        mask = ( c.is_body | c.is_median ).astype( float )
        outlined_band( c, v, centre, half, white, black, 0.035, mask )
    # Every fin edged black
    c.fill( black, c.is_fin * smoothstep( 0.8, 0.95, c.span ) )
    c.eye( 1.05, 0.2, 0.12, ( 0.9, 0.42, 0.06 ), ring=black )
    c.scales( 0.07, 0.05 )
    return c.done( 0.04, 9 )


def paint_banggai( mesh ):
    c = Canvas( mesh )
    silver = np.array( ( 0.8, 0.82, 0.8 ) )
    black = np.array( ( 0.03, 0.03, 0.035 ) )
    c.fill( silver )
    c.fill( ( 0.9, 0.9, 0.86 ), c.is_body * smoothstep( -0.2, -0.8, c.up ) )
    for centre, half in ( ( 0.82, 0.1 ), ( 0.22, 0.14 ), ( -0.52, 0.12 ) ):
        c.fill( black, band( c.x + 0.05 * c.z, centre, half, 0.025 ) * ( c.is_body | c.is_median ) )
    # The fins: black leading rays, the rest grey, the tail's lobes edged black
    c.fill( ( 0.62, 0.64, 0.62 ), c.is_median * ( c.x < -0.65 ) )
    c.fill( black, c.is_median * ( c.x < -0.78 ) * smoothstep( 0.62, 0.8, np.abs( c.z ) ) )
    c.fill( black, c.is_pelvic )
    # Pearly white dots over the rear body and fins
    dots = np.zeros( c.shape )
    rng = np.random.default_rng( 12 )
    for _ in range( 70 ):
        x, z, r = rng.uniform( -1.8, -0.05 ), rng.uniform( -1.6, 1.6 ), rng.uniform( 0.025, 0.045 )
        dots = np.maximum( dots, smoothstep( r, r * 0.6, np.hypot( c.x - x, c.z - z ) ) )
    c.fill( ( 0.98, 0.98, 0.96 ), dots * ( c.is_body | c.is_median ) * ( c.x < -0.62 ) )
    c.eye( 0.78, 0.18, 0.15, ( 0.85, 0.75, 0.3 ), ring=black )
    c.scales( 0.07, 0.05 )
    return c.done( 0.03, 10 )


def paint_lionfish( mesh ):
    c = Canvas( mesh )
    red = np.array( ( 0.55, 0.09, 0.07 ) )
    cream = np.array( ( 0.96, 0.88, 0.8 ) )
    c.fill( cream )
    # Zebra stripes, fanning out from the eye over the head and running down the body
    eye_x, eye_z = 3.85, 0.55
    angle = np.arctan2( c.z - eye_z, c.x - eye_x )
    radial = np.hypot( c.x - eye_x, c.z - eye_z )
    head = smoothstep( 2.6, 3.3, c.x )
    phase = np.where( head > 0.5, angle * 4.5 + radial * 0.8, ( c.x + 0.2 * c.z ) * 3.0 + np.sin( c.z * 1.4 ) * 0.4 )
    wave = np.sin( phase * 1.6 ) + 0.55 * np.sin( phase * 0.8 + 0.6 )
    stripes = smoothstep( 0.15, -0.25, wave )
    c.fill( red, c.is_body * stripes )
    c.fill( red * 0.9, c.is_body * smoothstep( 0.6, 1.0, c.up ) * 0.4 )
    # The spines banded red and white; the soft fins pale, rows of dark spots
    spines = c.is_median & ( c.z > 1.3 ) & ( c.x > -1.25 )
    c.fill( cream, spines )
    c.fill( red, spines * smoothstep( 0.1, -0.2, np.sin( c.z * 5.5 ) ) )
    soft = c.is_median & ~spines
    c.fill( ( 0.85, 0.82, 0.78 ), soft )
    spots = np.zeros( c.shape )
    rng = np.random.default_rng( 31 )
    for x, z in rng.uniform( ( -6.4, -3.0 ), ( -0.8, 3.0 ), ( 260, 2 ) ):
        spots = np.maximum( spots, smoothstep( 0.11, 0.06, np.hypot( c.x - x, c.z - z ) ) )
    c.fill( ( 0.18, 0.08, 0.06 ), soft * spots * 0.85 )
    # The pectoral fans: each ray banded red and white; the membrane pale with brownish bands along the fin
    rays = c.is_pectoral
    c.fill( cream, rays )
    c.fill( red, rays * smoothstep( 0.1, -0.2, np.sin( c.span * 26.0 ) ) )
    c.fill( ( 0.35, 0.12, 0.08 ), c.is_pelvic )
    c.fill( ( 0.95, 0.95, 0.95 ), c.is_pelvic * ( np.abs( np.sin( c.span * 30 ) ) > 0.85 ) )
    c.eye( eye_x, eye_z, 0.38, ( 0.55, 0.12, 0.06 ), ring=( 0.2, 0.05, 0.03 ) )
    c.scales( 0.25, 0.05 )
    return c.done( 0.05, 11 )


def paint_puffer( mesh ):
    c = Canvas( mesh )
    olive = np.array( ( 0.44, 0.41, 0.34 ) )
    belly = np.array( ( 0.94, 0.94, 0.9 ) )
    c.fill( olive )
    c.fill( belly, c.is_body * smoothstep( -0.15, -0.55, c.up ) )
    # Faint brown lines along the lower flank, into the white belly
    lines = smoothstep( 0.25, 0.0, np.abs( np.sin( c.z * 6.0 + c.x * 0.3 ) ) - 0.6 ) * smoothstep( 0.05, -0.3, c.up ) * smoothstep( -0.9, -0.5, c.up )
    c.fill( ( 0.5, 0.45, 0.38 ), c.is_body * lines * 0.5 )
    # White spots over the back, flanks and fins, smaller towards the snout
    rng = np.random.default_rng( 13 )
    spots = np.zeros( c.shape )
    pts = rng.uniform( ( -6.4, -2.6 ), ( 5.6, 2.6 ), ( 900, 2 ) )
    for x, z in pts:
        r = 0.1 + 0.06 * smoothstep( 4.0, -2.0, x )
        d = np.hypot( c.x - x, c.z - z )
        spots = np.maximum( spots, smoothstep( r, r * 0.55, d ) )
    dark = c.is_fin | ( c.is_body & ( c.up > -0.2 ) )
    c.fill( ( 0.95, 0.95, 0.92 ), spots * dark )
    # A dark ring round each pectoral's base, edged in yellow
    base = c.is_body * ( c.side > 0.6 )
    d = np.hypot( c.x - 1.4, c.z - 0.0 )
    c.fill( ( 0.12, 0.11, 0.09 ), base * smoothstep( 0.75, 0.45, d ) * 0.85 )
    c.fill( ( 0.35, 0.3, 0.25 ), c.is_pectoral )
    c.eye( 3.6, 1.05, 0.42, ( 0.4, 0.45, 0.2 ), ring=( 0.9, 0.85, 0.6 ) )
    return c.done( 0.05, 12 )


def paint_mandarin( mesh ):
    c = Canvas( mesh )
    blue = np.array( ( 0.05, 0.42, 0.78 ) )
    orange = np.array( ( 0.97, 0.38, 0.06 ) )
    navy = np.array( ( 0.03, 0.06, 0.32 ) )
    green = np.array( ( 0.12, 0.62, 0.55 ) )
    c.fill( blue )
    c.fill( green, c.noise( 3.5, 21 ) * 0.5 * c.is_body )
    # Wavy orange stripes outlined in navy, warped so no two are alike
    warp = c.noise( 4.0, 22 ) * 1.2 + np.sin( c.z * 9.0 + c.x * 3.0 ) * 0.25
    wave = np.sin( ( c.x * 1.0 + c.z * 0.55 + 0.35 * warp ) * 17.0 )
    c.fill( navy, smoothstep( 0.25, 0.4, wave ) )
    c.fill( orange, smoothstep( 0.45, 0.6, wave ) )
    # The head: orange with blue lines
    head = c.is_body * smoothstep( 0.45, 0.6, c.x )
    c.fill( orange, head )
    c.fill( ( 0.2, 0.55, 0.95 ), head * smoothstep( 0.55, 0.85, np.sin( ( c.z * 20 + c.x * 5 ) ) ) )
    # Fins: orange with blue margins, the tail red with blue lines
    c.fill( ( 0.95, 0.42, 0.08 ), c.is_pectoral | c.is_pelvic )
    c.fill( ( 0.15, 0.45, 0.9 ), ( c.is_pectoral | c.is_pelvic ) * smoothstep( 0.75, 0.95, c.span ) )
    tail = c.is_median & ( c.x < -0.8 )
    c.fill( ( 0.85, 0.2, 0.08 ), tail )
    c.fill( ( 0.15, 0.4, 0.9 ), tail * ( np.abs( np.sin( c.z * 18 ) ) > 0.8 ) )
    c.eye( 0.62, 0.22, 0.12, ( 0.9, 0.5, 0.1 ), ring=navy )
    return c.done( 0.03, 14 )


def paint_fusilier( mesh ):
    c = Canvas( mesh )
    blue = np.array( ( 0.1, 0.38, 0.88 ) )
    pale = np.array( ( 0.58, 0.78, 0.97 ) )
    belly = np.array( ( 0.9, 0.93, 0.97 ) )
    yellow = np.array( ( 1.0, 0.84, 0.1 ) )
    c.fill( blue )
    c.fill( pale, c.is_body * smoothstep( 0.1, -0.4, c.up ) )
    c.fill( belly, c.is_body * smoothstep( -0.5, -0.85, c.up ) )
    # Yellow over the back from mid-body to the tail, the tail all yellow
    xn = ( 3.8 - c.x ) / 6.8
    edge = 0.75 - 0.75 * smoothstep( 0.35, 0.95, xn )
    zr = np.where( c.is_body, c.up, np.sign( c.z ) )
    c.fill( yellow, smoothstep( edge - 0.05, edge + 0.05, zr ) * smoothstep( 0.3, 0.45, xn ) * ( c.is_body | c.is_median ) )
    c.fill( yellow, c.is_median * ( c.x < -2.8 ) )
    c.fill( ( 0.85, 0.9, 0.95 ), c.is_pectoral | c.is_pelvic )
    c.eye( 3.05, 0.25, 0.22, ( 0.2, 0.25, 0.3 ) )
    c.scales( 0.12, 0.06 )
    return c.done( 0.03, 15 )


def paint_sergeant( mesh ):
    c = Canvas( mesh )
    silver = np.array( ( 0.88, 0.9, 0.88 ) )
    yellow = np.array( ( 0.97, 0.88, 0.35 ) )
    black = np.array( ( 0.04, 0.045, 0.05 ) )
    c.fill( silver )
    c.fill( yellow, c.is_body * smoothstep( 0.1, 0.6, c.up ) )
    c.fill( ( 0.95, 0.95, 0.93 ), c.is_body * smoothstep( -0.4, -0.85, c.up ) )
    # Five black bars, fading out towards the belly
    zr = np.where( c.is_body, c.up, 1.0 )
    for centre in ( 1.35, 0.62, -0.12, -0.85, -1.52 ):
        c.fill( black, band( c.x + 0.08 * c.z, centre, 0.12, 0.03 ) * smoothstep( -0.75, -0.35, zr ) * ( c.is_body | ( c.is_median & ( c.z > 0 ) ) ) * 0.95 )
    c.fill( ( 0.78, 0.8, 0.78 ), c.is_fin & ~( c.is_median & ( c.z > 0 ) & ( c.x > -1.75 ) ) )
    c.fill( ( 0.35, 0.37, 0.38 ), c.is_median * ( c.x < -1.8 ) * smoothstep( 0.6, 1.0, np.abs( c.z ) ) * 0.7 )
    c.eye( 2.0, 0.45, 0.24, ( 0.35, 0.3, 0.15 ) )
    c.scales( 0.13, 0.06 )
    return c.done( 0.03, 16 )


def paint_manta( mesh ):
    t = ( np.arange( TEXTURE ) + 0.5 ) / TEXTURE
    u = t[None, :].repeat( TEXTURE, 0 )
    v = ( 1 - t )[:, None].repeat( TEXTURE, 1 )
    top = u < 0.5
    xn = np.where( top, u / 0.5, ( u - 0.5 ) / 0.5 )
    x = MANTA_FRONT - xn * ( MANTA_FRONT - MANTA_BACK )
    y = ( v - 0.5 ) * MANTA_SPAN
    ay = np.abs( y )
    yn = np.clip( ay / ( MANTA_SPAN / 2 ), 0, 1 )
    trailing = -0.42 * MANTA_CHORD + 0.32 * MANTA_CHORD * yn ** 0.7
    rng = np.random.default_rng( 5 )
    grain = 0.5 + 0.25 * np.sin( x * 0.9 + np.sin( y * 0.7 ) ) * np.sin( y * 1.1 + np.sin( x * 0.6 ) ) + 0.25 * rng.random( x.shape ) * 0.3

    dark = np.array( ( 0.045, 0.05, 0.058 ) )
    upper = np.broadcast_to( dark, u.shape + ( 3, ) ) * ( 0.85 + 0.3 * grain )[..., None]
    front = 15.0 - 0.18 * ( ay - 8.0 )
    rear = 9.0 - 0.55 * ( ay - 8.0 )
    patch = smoothstep( -1.5, 2.5, front - x ) * smoothstep( -1.5, 3.0, x - rear ) \
        * smoothstep( 6.0, 10.0, ay ) * ( 1 - smoothstep( 22.0, 34.0, ay ) )
    upper = upper + ( np.array( ( 0.72, 0.74, 0.74 ) ) - upper ) * np.clip( patch, 0, 1 )[..., None]

    lower = np.broadcast_to( np.array( ( 0.86, 0.87, 0.86 ) ), u.shape + ( 3, ) ) * ( 0.95 + 0.06 * grain )[..., None]
    margin = np.clip( smoothstep( 6.0, 0.0, x - trailing ) * smoothstep( 0.15, 0.4, yn ) + smoothstep( 0.8, 0.98, yn ), 0, 1 )
    mix = lambda a, b, m: a + ( np.asarray( b ) - a ) * np.asarray( m )[..., None]
    lower = mix( lower, ( 0.22, 0.23, 0.25 ), margin * 0.85 )
    lower = mix( lower, ( 0.08, 0.08, 0.09 ), smoothstep( 19.0, 22.0, x ) * ( 1 - smoothstep( 8.0, 10.0, ay ) ) )
    for k in range( 5 ):
        gx = 14.0 - 1.8 * k
        slit = np.exp( -( ( x - gx ) / 0.35 ) ** 2 ) * smoothstep( 7.5, 8.5, ay ) * ( 1 - smoothstep( 13.0, 14.5, ay ) )
        lower = mix( lower, ( 0.25, 0.25, 0.27 ), slit * 0.9 )
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


# ---------------------------------------------------------------------------------------------------------------------
# How each one swims and lives. TankFauna (Code/Maps/TankFauna.cs) reads these from the scene, where
# Tools/reefhall_map.py writes them with each group.
#
#   swim:  the shader's body wave: tail swing (a share of the length) and beats a second at cruising speed, the wave's
#          length in body lengths; fin: pectoral beats a second and how far they swing (a share of their length).
#   speed: cruising speed in inches a second, about 0.5-1.5 body lengths for reef fish, faster for the open-water
#          schoolers, slow for the hoverers (Videler, "Fish Swimming"; aquarium observation).
#   turn:  the fastest turn, degrees a second; response: seconds to settle into a turn (bigger animals are slower).
#   climb: the steepest climb (the sine of its pitch); bank: degrees it rolls into a full-rate turn.
#   low, high: its depth, as shares of the water's height over the sand; above: no higher than this over the sand (0:
#          no limit). rocks: the share of its destinations beside rock or coral; home: it keeps within this of a home
#          spot (0: the whole tank). pause: the chance it stops at a destination to hover, for pausemin-pausemax s.
#   group: solo, pair, shoal (a loose group) or school (a tight, aligned one); spread: room per fish, in lengths.
#   scale: the smallest and largest individual, a share of the model.

SPECIES = {
    "reef_shark": dict( build=reef_shark, paint=paint_shark, roughness=0.5,
                        swim=dict( swing=0.07, beat=0.8, wave=1.0, fin=0.0, fin_swing=0.0 ),
                        speed=42, turn=28, response=1.4, climb=0.25, bank=18, low=0.2, high=0.85, above=0, rocks=0.0,
                        home=0, pause=0.0, pausemin=0, pausemax=0, group="solo", spread=0, scale=( 0.92, 1.1 ) ),
    "manta_ray": dict( build=manta_ray, paint=paint_manta, roughness=0.5, ray=True,
                       swim=dict( swing=0.0, beat=0.32, wave=1.0, fin=0.0, fin_swing=0.0, flap=0.1 ),
                       speed=30, turn=20, response=1.8, climb=0.2, bank=24, low=0.35, high=0.9, above=0, rocks=0.0,
                       home=0, pause=0.0, pausemin=0, pausemax=0, group="solo", spread=0, scale=( 0.9, 1.08 ) ),
    "yellow_tang": dict( build=yellow_tang, paint=paint_tang, roughness=0.45,
                         swim=dict( swing=0.08, beat=2.6, wave=1.2, fin=2.2, fin_swing=0.3 ),
                         speed=7, turn=110, response=0.4, climb=0.4, bank=10, low=0.15, high=0.75, above=0, rocks=0.45,
                         home=0, pause=0.15, pausemin=1, pausemax=3, group="shoal", spread=1.6, scale=( 0.85, 1.1 ) ),
    "blue_tang": dict( build=blue_tang, paint=paint_blue_tang, roughness=0.42,
                       swim=dict( swing=0.08, beat=2.8, wave=1.2, fin=2.4, fin_swing=0.3 ),
                       speed=7, turn=120, response=0.35, climb=0.4, bank=10, low=0.2, high=0.8, above=0, rocks=0.35,
                       home=0, pause=0.15, pausemin=1, pausemax=3, group="shoal", spread=1.8, scale=( 0.85, 1.1 ) ),
    "chromis": dict( build=chromis, paint=paint_chromis, roughness=0.4,
                     swim=dict( swing=0.1, beat=3.6, wave=1.1, fin=4.0, fin_swing=0.35 ),
                     speed=5, turn=170, response=0.25, climb=0.45, bank=10, low=0.08, high=0.55, above=0, rocks=0.6,
                     home=0, pause=0.35, pausemin=1.5, pausemax=4, group="school", spread=1.1, scale=( 0.65, 0.85 ) ),
    "copperband": dict( build=copperband, paint=paint_copperband, roughness=0.42,
                        swim=dict( swing=0.06, beat=2.0, wave=1.3, fin=2.6, fin_swing=0.35 ),
                        speed=3, turn=70, response=0.5, climb=0.4, bank=8, low=0.05, high=0.55, above=0, rocks=0.85,
                        home=0, pause=0.55, pausemin=2, pausemax=6, group="solo", spread=2.5, scale=( 0.85, 1.05 ) ),
    "regal_angel": dict( build=regal_angel, paint=paint_regal, roughness=0.42,
                         swim=dict( swing=0.06, beat=1.8, wave=1.3, fin=2.0, fin_swing=0.3 ),
                         speed=4, turn=70, response=0.55, climb=0.35, bank=8, low=0.08, high=0.6, above=0, rocks=0.75,
                         home=0, pause=0.35, pausemin=2, pausemax=5, group="solo", spread=0, scale=( 0.85, 1.05 ) ),
    "moorish_idol": dict( build=moorish_idol, paint=paint_idol, roughness=0.42,
                          swim=dict( swing=0.06, beat=2.0, wave=1.3, fin=2.2, fin_swing=0.3 ),
                          speed=5, turn=80, response=0.5, climb=0.35, bank=8, low=0.2, high=0.75, above=0, rocks=0.3,
                          home=0, pause=0.15, pausemin=1, pausemax=3, group="pair", spread=2.2, scale=( 0.85, 1.05 ) ),
    "clownfish": dict( build=clownfish, paint=paint_clownfish, roughness=0.4,
                       swim=dict( swing=0.1, beat=3.2, wave=1.1, fin=3.6, fin_swing=0.4 ),
                       speed=3.5, turn=200, response=0.2, climb=0.45, bank=6, low=0.05, high=0.45, above=40, rocks=0.9,
                       home=20, pause=0.5, pausemin=0.8, pausemax=2.5, group="pair", spread=1.8, scale=( 0.8, 1.05 ) ),
    "banggai": dict( build=banggai, paint=paint_banggai, roughness=0.4,
                     swim=dict( swing=0.06, beat=1.6, wave=1.2, fin=2.8, fin_swing=0.35 ),
                     speed=1.4, turn=60, response=0.6, climb=0.3, bank=4, low=0.08, high=0.5, above=48, rocks=0.85,
                     home=28, pause=0.75, pausemin=3, pausemax=9, group="shoal", spread=2.2, scale=( 0.85, 1.05 ) ),
    "lionfish": dict( build=lionfish, paint=paint_lionfish, roughness=0.5,
                      swim=dict( swing=0.05, beat=1.0, wave=1.3, fin=0.6, fin_swing=0.12 ),
                      speed=2.5, turn=35, response=1.0, climb=0.25, bank=6, low=0.05, high=0.55, above=0, rocks=0.75,
                      home=0, pause=0.7, pausemin=4, pausemax=12, group="solo", spread=0, scale=( 0.8, 1.0 ) ),
    "puffer": dict( build=puffer, paint=paint_puffer, roughness=0.5,
                    swim=dict( swing=0.05, beat=1.2, wave=1.4, fin=2.2, fin_swing=0.35 ),
                    speed=4, turn=45, response=0.8, climb=0.3, bank=6, low=0.1, high=0.75, above=0, rocks=0.4,
                    home=0, pause=0.35, pausemin=2, pausemax=6, group="solo", spread=0, scale=( 0.8, 1.0 ) ),
    "mandarin": dict( build=mandarin, paint=paint_mandarin, roughness=0.35,
                      swim=dict( swing=0.05, beat=1.4, wave=1.2, fin=4.5, fin_swing=0.45 ),
                      speed=1.0, turn=90, response=0.3, climb=0.25, bank=4, low=0.0, high=0.15, above=8, rocks=0.85,
                      home=24, pause=0.7, pausemin=1, pausemax=4, group="solo", spread=0, scale=( 0.85, 1.05 ) ),
    "fusilier": dict( build=fusilier, paint=paint_fusilier, roughness=0.38,
                      swim=dict( swing=0.09, beat=3.0, wave=1.0, fin=1.5, fin_swing=0.2 ),
                      speed=14, turn=70, response=0.5, climb=0.3, bank=12, low=0.35, high=0.9, above=0, rocks=0.0,
                      home=0, pause=0.0, pausemin=0, pausemax=0, group="school", spread=1.2, scale=( 0.85, 1.05 ) ),
    "sergeant_major": dict( build=sergeant_major, paint=paint_sergeant, roughness=0.4,
                            swim=dict( swing=0.08, beat=2.6, wave=1.1, fin=2.4, fin_swing=0.3 ),
                            speed=8, turn=90, response=0.4, climb=0.35, bank=10, low=0.3, high=0.85, above=0, rocks=0.1,
                            home=0, pause=0.05, pausemin=1, pausemax=2, group="school", spread=1.5, scale=( 0.85, 1.05 ) ),
}


def shader_params( name, mesh ):
    """ The material's swimming settings: the body's length and nose, the wave, the pectorals' reach. """
    spec = SPECIES[name]
    swim = spec["swim"]
    p = np.array( mesh.positions )
    nose, tail = p[:, 0].max(), p[:, 0].min()
    pect = [ k for k, r in enumerate( mesh.roles ) if r == "pectoral" ]
    fin_reach = float( np.max( np.linalg.norm( p[pect] - p[pect].mean( axis=0 ), axis=1 ) ) ) if pect else 0.0
    out = { "g_flBodyLength": nose - tail, "g_flNoseX": nose, "g_flSwingAmount": swim["swing"], "g_flBeatRate": swim["beat"],
            "g_flWaveLength": swim["wave"], "g_flFinReach": fin_reach, "g_flFinSwing": swim["fin_swing"],
            "g_flFinRate": swim["fin"] }
    if spec.get( "ray" ):
        out.update( { "g_flRay": 1.0, "g_flSpan": MANTA_SPAN, "g_flFlapAmount": swim["flap"], "g_flBodyLength": 48.0, "g_flNoseX": 24.0 } )
    return out


def deform( p, uv, params, phase, amount, fin_phase, fin_amount ):
    """ What hc1_fish.shader does to the points, for working out how far they reach. """
    p = p.copy()
    L = params["g_flBodyLength"]
    if params.get( "g_flRay", 0 ) > 0:
        span = params["g_flSpan"]
        out = np.clip( np.abs( p[:, 1] ) / ( 0.5 * span ), 0, 1 )
        chord = np.clip( ( params["g_flNoseX"] - p[:, 0] ) / L, 0, 1 )
        w = np.sin( phase - chord * 1.6 )
        p[:, 2] += params["g_flFlapAmount"] * amount * span * out ** 1.5 * w
        return p
    s01 = np.clip( ( params["g_flNoseX"] - p[:, 0] ) / L, 0, 1 )
    env = 0.18 + 0.82 * s01 * s01
    wave = np.sin( phase - s01 * 2 * math.pi / params["g_flWaveLength"] )
    swing = params["g_flSwingAmount"] * L * amount * env
    p[:, 1] += swing * wave
    p[:, 0] -= swing * 0.15 * np.abs( wave ) * s01
    pect = ( uv[:, 0] >= PECTORAL_U[0] ) & ( uv[:, 0] < PECTORAL_U[1] )
    if pect.any() and params["g_flFinReach"] > 0:
        span = np.clip( ( uv[:, 0] - PECTORAL_U[0] ) / ( PECTORAL_U[1] - PECTORAL_U[0] ), 0, 1 )
        flap = params["g_flFinSwing"] * fin_amount * span * params["g_flFinReach"]
        p[pect, 0] += ( flap * np.sin( fin_phase - span * 1.5 ) )[pect]
        p[pect, 1] += ( np.sign( p[:, 1] ) * flap * 0.4 * ( 0.5 + 0.5 * np.cos( fin_phase - span * 1.5 ) ) )[pect]
    return p


def reach( name, mesh, params ):
    """ How far the body reaches from its middle: sideways (at any heading, so the horizontal radius) and up and down,
    swinging as hard as TankFauna lets it, at its steepest climb and fullest bank. """
    spec = SPECIES[name]
    pos = np.array( mesh.positions )
    uv = np.array( [ u if u is not None else ( 0, 0 ) for u in mesh.uvs ] )
    pitch = math.asin( spec["climb"] )
    bank = math.radians( spec["bank"] )
    horizontal, vertical = 0.0, 0.0
    for phase in np.linspace( 0, 2 * math.pi, 16, endpoint=False ):
        for fin_phase in ( 0.0, math.pi / 2, math.pi, 1.5 * math.pi ):
            p = deform( pos, uv, params, phase, 1.35, fin_phase, 1.0 )
            for pt in ( -pitch, 0.0, pitch ):
                for rl in ( -bank, 0.0, bank ):
                    # Roll about X, then pitch about Y
                    cr, sr = math.cos( rl ), math.sin( rl )
                    y = p[:, 1] * cr - p[:, 2] * sr
                    z = p[:, 1] * sr + p[:, 2] * cr
                    cp, sp = math.cos( pt ), math.sin( pt )
                    x = p[:, 0] * cp - z * sp
                    z = p[:, 0] * sp + z * cp
                    horizontal = max( horizontal, float( np.max( np.hypot( x, y ) ) ) )
                    vertical = max( vertical, float( np.max( np.abs( z ) ) ) )
    return horizontal * 1.02 + 0.05, vertical * 1.02 + 0.05


PREVIEW_SCRIPT = r'''
import bpy, math, sys, mathutils
args = sys.argv[ sys.argv.index( "--" ) + 1: ]
obj_path, tex_path, out_path, size = args[0], args[1], args[2], float( args[3] )
bpy.ops.wm.read_factory_settings( use_empty=True )
bpy.ops.wm.obj_import( filepath=obj_path, forward_axis="NEGATIVE_Z", up_axis="Y" )
ob = bpy.context.selected_objects[0]
mat = bpy.data.materials.new( "m" ); mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = next( n for n in nodes if n.type == "BSDF_PRINCIPLED" )
tex = nodes.new( "ShaderNodeTexImage" ); tex.image = bpy.data.images.load( tex_path )
mat.node_tree.links.new( tex.outputs[0], bsdf.inputs[0] )
bsdf.inputs["Roughness"].default_value = 0.45
ob.data.materials.clear(); ob.data.materials.append( mat )
for p in ob.data.polygons: p.use_smooth = True
scene = bpy.context.scene
names = [ e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items ]
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in names else ( "BLENDER_EEVEE" if "BLENDER_EEVEE" in names else scene.render.engine )
world = bpy.data.worlds.new( "w" ); scene.world = world; world.use_nodes = True
bg = next( n for n in world.node_tree.nodes if n.type == "BACKGROUND" ); bg.inputs[0].default_value = ( 0.18, 0.34, 0.48, 1 ); bg.inputs[1].default_value = 0.9
sun = bpy.data.objects.new( "sun", bpy.data.lights.new( "sun", "SUN" ) ); scene.collection.objects.link( sun )
sun.rotation_euler = ( math.radians( 35 ), math.radians( 15 ), math.radians( 20 ) ); sun.data.energy = 3.5
cam = bpy.data.objects.new( "cam", bpy.data.cameras.new( "cam" ) ); scene.collection.objects.link( cam ); scene.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size
scene.render.resolution_x, scene.render.resolution_y = 1400, 900
centre = sum( ( mathutils.Vector( c ) for c in ob.bound_box ), mathutils.Vector() ) / 8
centre = ob.matrix_world @ centre
# Imported Y-up with forward -Z, the model's X (its nose) is Blender's -Y and its left (+Y) Blender's +X
views = [ ( ( 1, 0.0001, 0.06 ), "side" ), ( ( 0.0001, 0.0001, 1 ), "top" ), ( ( 0.55, 0.45, -0.45 ), "below" ), ( ( 0.75, -0.55, 0.3 ), "front" ) ]
for direction, label in views:
    d = mathutils.Vector( direction ).normalized()
    cam.location = centre + d * size * 3
    cam.rotation_euler = ( -d ).to_track_quat( "-Z", "Y" ).to_euler()
    scene.render.filepath = out_path.replace( ".png", f"_{label}.png" )
    bpy.ops.render.render( write_still=True )
'''


def preview( directory, names ):
    blender = pathlib.Path( r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" )
    if not blender.exists():
        print( "no Blender for the preview" )
        return
    directory = pathlib.Path( directory )
    directory.mkdir( parents=True, exist_ok=True )
    script = directory / "fauna_preview.py"
    script.write_text( PREVIEW_SCRIPT )
    for name in names:
        p = np.array( [ [ float( v ) for v in line.split()[1:4] ] for line in ( OUT / f"{name}.obj" ).read_text().splitlines() if line.startswith( "v " ) ] )
        extent = p.max( axis=0 ) - p.min( axis=0 )
        size = float( max( extent[2], extent[1] * 1400 / 900, extent[0] ) ) * 1.12
        subprocess.run( [ str( blender ), "-b", "--python", str( script ), "--", str( OUT / f"{name}.obj" ),
                          str( OUT / f"{name}_color.png" ), str( directory / f"{name}.png" ), str( size ) ],
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )
        print( "preview", name )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--only", help="comma-separated animals to write" )
    parser.add_argument( "--preview", help="render each animal with Blender into this folder" )
    args = parser.parse_args()
    OUT.mkdir( parents=True, exist_ok=True )
    names = args.only.split( "," ) if args.only else list( SPECIES )
    sizes_path = OUT / "fauna_species.json"
    sizes = json.loads( sizes_path.read_text() ) if sizes_path.exists() else {}
    for name in names:
        spec = SPECIES[name]
        mesh = spec["build"]()
        mesh.finish()
        bad = mesh.volume_sign_check()
        write_obj( OUT / f"{name}.obj", mesh, name )
        colour = np.clip( spec["paint"]( mesh ), 0, 1 )
        Image.fromarray( ( colour * 255 + 0.5 ).astype( np.uint8 ) ).save( OUT / f"{name}_color.png" )
        params = shader_params( name, mesh )
        write_vmat( OUT / f"{name}.vmat", name, params, spec["roughness"] )
        write_vmdl( OUT / f"{name}.vmdl", name )
        horizontal, vertical = reach( name, mesh, params )
        p = np.array( mesh.positions )
        sizes[name] = { "reach": round( horizontal, 3 ), "up": round( vertical, 3 ), "length": round( float( p[:, 0].max() - p[:, 0].min() ), 3 ),
                        "nose": round( float( p[:, 0].max() ), 3 ) }
        print( f"{name}: {len( mesh.triangles )} triangles, {bad} wound inwards, reach {horizontal:.2f} up {vertical:.2f}, "
               f"bounds {np.round( p.min( axis=0 ), 2 )} to {np.round( p.max( axis=0 ), 2 )}" )
        if bad:
            sys.exit( f"{name} has triangles wound the wrong way" )
    sizes_path.write_text( json.dumps( sizes, indent=1, sort_keys=True ) + "\n", newline="\n" )
    if args.preview:
        preview( args.preview, names )


if __name__ == "__main__":
    main()
