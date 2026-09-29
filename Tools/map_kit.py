"""
A kit for building a map by script out of boxes and polygons, the way Tools/ridgeback_buildings.py builds Ridgeback's
houses: world-scale UVs (a brick is a brick's size on every wall), Tools/building_textures.py's materials, and collision
made of the same boxes (PhysicsShapeBox) plus convex hulls, so what you see is what stops players, bots and bullets.
Tools/belltower_map.py builds Belltower with it.

Plan coordinates: e east, n north, z up, in inches (s&box units). s&box's world has +x north and +y west (as on the
radar), so plan ( e, n, z ) is world ( n, -e, z ). ModelDoc reads an OBJ as Y-up, so world ( x, y, z ) is written to the
OBJ as ( y, z, x ).

- Faces are named in plan directions: '+e', '-e', '+n', '-n', '+z', '-z'.
- A polygon is counter-clockwise seen from the side it faces, and is drawn as a fan from its first point, so that point
  must see the whole polygon.
- Model.mirrored() turns a model over east to west (e to -e), for the half of a symmetric map that mirrors the other.
"""
import json
import math
import uuid
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np

import building_textures as BT

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"

FACES = ( "+e", "-e", "+n", "-n", "+z", "-z" )
AXIS = { "e": 0, "n": 1, "z": 2 }


def normalise( v ):
    v = np.asarray( v, float )
    return v / np.linalg.norm( v )


def to_world( p ):
    """ Plan ( e, n, z ) to s&box world ( x north, y west, z ). """
    return np.array( ( p[1], -p[0], p[2] ), float )


def mirror_point( p ):
    return np.array( ( -p[0], p[1], p[2] ), float )


def mirror_face( face ):
    return { "+e": "-e", "-e": "+e" }.get( face, face )


# ---------------------------------------------------------------------------------------------------------------------
# Rotations (s&box's Rotation.From( pitch, yaw, roll ), as in Tools/ridgeback_buildings.py)

def rotation_matrix( pitch, yaw, roll ):
    """ The matrix of s&box's Rotation.From( pitch, yaw, roll ) (columns: the turned x, y and z axes). """
    sp, cp = math.sin( math.radians( pitch ) / 2 ), math.cos( math.radians( pitch ) / 2 )
    sy, cy = math.sin( math.radians( yaw ) / 2 ), math.cos( math.radians( yaw ) / 2 )
    sr, cr = math.sin( math.radians( roll ) / 2 ), math.cos( math.radians( roll ) / 2 )
    x, y, z, w = ( sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy,
                   cr * cp * cy + sr * sp * sy )
    return np.array( [
        [ 1 - 2 * ( y * y + z * z ), 2 * ( x * y - z * w ), 2 * ( x * z + y * w ) ],
        [ 2 * ( x * y + z * w ), 1 - 2 * ( x * x + z * z ), 2 * ( y * z - x * w ) ],
        [ 2 * ( x * z - y * w ), 2 * ( y * z + x * w ), 1 - 2 * ( x * x + y * y ) ],
    ] )


def angles_of( axes ):
    """ Pitch, yaw and roll (degrees) that turn the world's axes onto these (world vectors), checked. """
    m = np.column_stack( axes )
    pitch = math.degrees( math.asin( max( -1.0, min( 1.0, -m[2, 0] ) ) ) )
    yaw = math.degrees( math.atan2( m[1, 0], m[0, 0] ) )
    roll = math.degrees( math.atan2( m[2, 1], m[2, 2] ) )
    assert np.allclose( rotation_matrix( pitch, yaw, roll ), m, atol=1e-5 ), ( m, pitch, yaw, roll )
    return ( pitch, yaw, roll )


# ---------------------------------------------------------------------------------------------------------------------
# Model

class Model:
    """ Polygons by paint, and the collision: boxes ( centre, axes, size, surface ) and hulls ( points, surface ), all
    in plan coordinates. """

    def __init__( self ):
        self.polygons = defaultdict( list )      # paint -> [ ( points, normal ) ]
        self.boxes = []
        self.hulls = []
        self.props = []                         # optional scene instances: path, position, yaw, scale
        self.material_overrides = {}
        self.tile_overrides = {}
        self.polygon_uvs = {}                   # (paint, face index) -> explicitly authored UVs
        self.polygon_normals = {}               # (paint, face index) -> a normal per point, for round things
        self.grain_paints = set()

    # Drawing -------------------------------------------------------------------------------------------------------

    def polygon( self, paint, points, normal=None, both_sides=False, uv=None, normals=None ):
        """ normals: one per point (shading a curved surface smoothly across its facets), else the face's own. """
        points = [ np.asarray( p, float ) for p in points ]
        if normal is None:
            normal = np.zeros( 3 )
            for k in range( 1, len( points ) - 1 ):
                normal += np.cross( points[k] - points[0], points[k + 1] - points[0] )
        if np.linalg.norm( normal ) < 1e-9:
            return
        if uv is not None:
            self.polygon_uvs[(paint, len(self.polygons[paint]))] = list(uv)
        if normals is not None:
            self.polygon_normals[(paint, len(self.polygons[paint]))] = [ normalise( n ) for n in normals ]
        self.polygons[paint].append( ( points, normalise( normal ) ) )
        if both_sides:
            if uv is not None:
                self.polygon_uvs[(paint, len(self.polygons[paint]))] = list(uv[:1]) + list(uv[:0:-1])
            self.polygons[paint].append( ( points[:1] + points[:0:-1], -normalise( normal ) ) )

    def box( self, lo, hi, paints, surface=None, skip=() ):
        """ An axis-aligned box. paints is one paint or { face: paint } (with 'default'); a face painted None or listed
        in skip isn't drawn. surface adds the box to the collision. """
        lo, hi = np.minimum( lo, hi ).astype( float ), np.maximum( lo, hi ).astype( float )
        if np.any( hi - lo < 1e-6 ):
            return
        e0, n0, z0 = lo
        e1, n1, z1 = hi
        faces = {
            "+e": [ ( e1, n0, z0 ), ( e1, n1, z0 ), ( e1, n1, z1 ), ( e1, n0, z1 ) ],
            "-e": [ ( e0, n1, z0 ), ( e0, n0, z0 ), ( e0, n0, z1 ), ( e0, n1, z1 ) ],
            "+n": [ ( e1, n1, z0 ), ( e0, n1, z0 ), ( e0, n1, z1 ), ( e1, n1, z1 ) ],
            "-n": [ ( e0, n0, z0 ), ( e1, n0, z0 ), ( e1, n0, z1 ), ( e0, n0, z1 ) ],
            "+z": [ ( e0, n0, z1 ), ( e1, n0, z1 ), ( e1, n1, z1 ), ( e0, n1, z1 ) ],
            "-z": [ ( e0, n1, z0 ), ( e1, n1, z0 ), ( e1, n0, z0 ), ( e0, n0, z0 ) ],
        }
        for face, points in faces.items():
            paint = paints.get( face, paints.get( "default" ) ) if isinstance( paints, dict ) else paints
            if paint is None or face in skip:
                continue
            self.polygon( paint, points )
        if surface:
            self.boxes.append( ( ( lo + hi ) / 2, ( ( 1, 0, 0 ), ( 0, 1, 0 ), ( 0, 0, 1 ) ), hi - lo, surface ) )

    def oriented_box( self, centre, axes, size, paints, surface=None ):
        """ A box turned by axes (its own x, y and z as plan vectors: orthonormal, right-handed), size along each. Faces
        are named along its own axes: '+x', '-x', '+y', '-y', '+z', '-z'. """
        centre = np.asarray( centre, float )
        ax = [ normalise( a ) for a in axes ]
        h = np.asarray( size, float ) / 2

        def corner( sx, sy, sz ):
            return centre + ax[0] * sx * h[0] + ax[1] * sy * h[1] + ax[2] * sz * h[2]

        faces = {
            "+x": [ corner( 1, -1, -1 ), corner( 1, 1, -1 ), corner( 1, 1, 1 ), corner( 1, -1, 1 ) ],
            "-x": [ corner( -1, 1, -1 ), corner( -1, -1, -1 ), corner( -1, -1, 1 ), corner( -1, 1, 1 ) ],
            "+y": [ corner( 1, 1, -1 ), corner( -1, 1, -1 ), corner( -1, 1, 1 ), corner( 1, 1, 1 ) ],
            "-y": [ corner( -1, -1, -1 ), corner( 1, -1, -1 ), corner( 1, -1, 1 ), corner( -1, -1, 1 ) ],
            "+z": [ corner( -1, -1, 1 ), corner( 1, -1, 1 ), corner( 1, 1, 1 ), corner( -1, 1, 1 ) ],
            "-z": [ corner( -1, 1, -1 ), corner( 1, 1, -1 ), corner( 1, -1, -1 ), corner( -1, -1, -1 ) ],
        }
        for face, points in faces.items():
            paint = paints.get( face, paints.get( "default" ) ) if isinstance( paints, dict ) else paints
            if paint is not None:
                self.polygon( paint, points )
        if surface:
            self.boxes.append( ( centre, tuple( tuple( a ) for a in ax ), np.asarray( size, float ), surface ) )

    def beam( self, p0, p1, size, paint, surface=None, up=( 0, 0, 1 ) ):
        """ A box from p0 to p1, size ( across it, and the third way ): the second axis is level where it can be. """
        p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
        x_axis = normalise( p1 - p0 )
        up = np.asarray( up, float )
        side = np.cross( up, x_axis )
        if np.linalg.norm( side ) < 1e-6:
            side = np.cross( ( 1.0, 0.0, 0.0 ), x_axis )
        y_axis = normalise( side )
        z_axis = np.cross( x_axis, y_axis )
        self.oriented_box( ( p0 + p1 ) / 2, ( x_axis, y_axis, z_axis ), ( np.linalg.norm( p1 - p0 ), *size ), paint,
                           surface )

    def prism( self, outline, z0, z1, paints, surface=None, collide="hull" ):
        """ An upright prism over outline (plan ( e, n ) points, counter-clockwise from above, convex for a hull):
        paints is one paint or { 'side', 'top', 'bottom' }. collide 'hull' adds it as one hull, 'box' as its bounding
        box, None not at all (surface is still needed for either). """
        def paint_of( key ):
            return paints.get( key, paints.get( "default" ) ) if isinstance( paints, dict ) else paints

        pts = [ np.asarray( p, float ) for p in outline ]
        n = len( pts )
        side = paint_of( "side" )
        if side:
            for k in range( n ):
                a, b = pts[k], pts[( k + 1 ) % n]
                self.polygon( side, [ ( *a, z0 ), ( *b, z0 ), ( *b, z1 ), ( *a, z1 ) ] )
        top, bottom = paint_of( "top" ), paint_of( "bottom" )
        if top:
            self.polygon( top, [ ( *p, z1 ) for p in pts ] )
        if bottom:
            self.polygon( bottom, [ ( *p, z0 ) for p in reversed( pts ) ] )
        if surface and collide == "hull":
            self.hulls.append( ( [ ( *p, z ) for z in ( z0, z1 ) for p in pts ], surface ) )
        elif surface and collide == "box":
            e = [ p[0] for p in pts ]
            nn = [ p[1] for p in pts ]
            lo, hi = np.array( ( min( e ), min( nn ), z0 ) ), np.array( ( max( e ), max( nn ), z1 ) )
            self.boxes.append( ( ( lo + hi ) / 2, ( ( 1, 0, 0 ), ( 0, 1, 0 ), ( 0, 0, 1 ) ), hi - lo, surface ) )

    def cylinder( self, centre, radius, z0, z1, paints, sides=12, surface=None, collide="hull", turn=0.0 ):
        c = np.asarray( centre, float )
        outline = [ c + radius * np.array( ( math.cos( turn + 2 * math.pi * k / sides ),
                                               math.sin( turn + 2 * math.pi * k / sides ) ) ) for k in range( sides ) ]
        self.prism( outline, z0, z1, paints, surface, collide )

    def hull( self, points, surface ):
        """ Collision only: the convex hull of these plan points. """
        self.hulls.append( ( [ tuple( map( float, p ) ) for p in points ], surface ) )

    def collision_box( self, lo, hi, surface ):
        """ Collision only: an axis-aligned box. """
        lo, hi = np.minimum( lo, hi ).astype( float ), np.maximum( lo, hi ).astype( float )
        self.boxes.append( ( ( lo + hi ) / 2, ( ( 1, 0, 0 ), ( 0, 1, 0 ), ( 0, 0, 1 ) ), hi - lo, surface ) )

    # Whole models --------------------------------------------------------------------------------------------------

    def extend( self, other ):
        for paint, items in other.polygons.items():
            offset = len(self.polygons[paint])
            for i in range(len(items)):
                if (paint, i) in other.polygon_uvs:
                    self.polygon_uvs[(paint, offset+i)] = other.polygon_uvs[(paint, i)]
                if (paint, i) in other.polygon_normals:
                    self.polygon_normals[(paint, offset+i)] = other.polygon_normals[(paint, i)]
            self.polygons[paint].extend( items )
        self.boxes.extend( other.boxes )
        self.hulls.extend( other.hulls )
        self.props.extend( other.props )
        self.material_overrides.update( other.material_overrides )
        self.tile_overrides.update( other.tile_overrides )
        self.grain_paints.update( other.grain_paints )
        return self

    def mirrored( self, paint_map=None ):
        """ Turned over east to west: e to -e, with every polygon's order reversed so it still faces out. paint_map
        repaints ( { old: new } ), so a mirrored half can look different. """
        paint_map = paint_map or {}
        out = Model()
        out.material_overrides = dict( self.material_overrides )
        out.tile_overrides = dict( self.tile_overrides )
        out.grain_paints = set( self.grain_paints )
        flip = np.array( ( -1.0, 1.0, 1.0 ) )
        for paint, items in self.polygons.items():
            target = paint_map.get( paint, paint )
            for index, (points, normal) in enumerate(items):
                mirrored = [ p * flip for p in points ]
                uv = self.polygon_uvs.get((paint, index))
                if uv is not None:
                    out.polygon_uvs[(target, len(out.polygons[target]))] = uv[:1] + uv[:0:-1]
                normals = self.polygon_normals.get((paint, index))
                if normals is not None:
                    normals = [ n * flip for n in normals ]
                    out.polygon_normals[(target, len(out.polygons[target]))] = normals[:1] + normals[:0:-1]
                out.polygons[target].append( ( mirrored[:1] + mirrored[:0:-1], normal * flip ) )
        for centre, axes, size, surface in self.boxes:
            a0, a1, a2 = ( np.asarray( a, float ) * flip for a in axes )
            out.boxes.append( ( np.asarray( centre, float ) * flip, ( tuple( a0 ), tuple( -a1 ), tuple( a2 ) ), size, surface ) )
        for points, surface in self.hulls:
            out.hulls.append( ( [ tuple( np.asarray( p, float ) * flip ) for p in points ], surface ) )
        for prop in self.props:
            out.props.append( { **prop, "position": tuple( np.asarray( prop["position"] ) * flip ),
                                "yaw": -prop["yaw"] } )
        return out

    def bounds( self ):
        pts = [ p for items in self.polygons.values() for points, _ in items for p in points ]
        if not pts:
            return None
        pts = np.array( pts )
        return pts.min( axis=0 ), pts.max( axis=0 )

    def triangle_count( self ):
        return sum( len( points ) - 2 for items in self.polygons.values() for points, _ in items )


# ---------------------------------------------------------------------------------------------------------------------
# Shapes

def arc( centre_r, spring_z, radius, steps, start=180.0, end=0.0 ):
    """ Points ( r, z ) round a semicircle over an opening, from angle start to end (degrees; 180 is its left foot). """
    return [ ( centre_r + radius * math.cos( math.radians( start + ( end - start ) * k / steps ) ),
               spring_z + radius * math.sin( math.radians( start + ( end - start ) * k / steps ) ) )
             for k in range( steps + 1 ) ]


class Opening:
    """ A hole in a wall: r0..r1 along it, z0..z1 (an arch's z1 is its crown). kind is 'door', 'window', 'arch'
    (open, round-headed), 'glass' (a window with a pane in it), 'glass_arch', 'shut' (a door with a closed leaf in it)
    or 'shop' (a shopfront closed with a rolling shutter). """

    def __init__( self, r0, r1, z0, z1, kind ):
        self.r0, self.r1, self.z0, self.z1, self.kind = r0, r1, z0, z1, kind

    @property
    def arched( self ):
        return self.kind in ( "arch", "glass_arch" )

    @property
    def radius( self ):
        return ( self.r1 - self.r0 ) / 2

    @property
    def spring( self ):
        """ Where an arch's curve starts. """
        return self.z1 - self.radius if self.arched else self.z1

    @property
    def rect_top( self ):
        """ The top of the part the strips leave open. An arch is cut up to its crown, and its own faces fill the
        spandrels back in (Wall._arch_head). """
        return self.z1


class Wall:
    """ A straight wall. axis 'e' runs along e (its thickness across n), 'n' along n. run ( r0, r1 ) along it, across
    ( d0, d1 ) the other way, z ( z0, z1 ). outward is the plan direction its outside faces ('+n', ...), or None for an
    inside wall. """

    def __init__( self, axis, run, across, z, outward=None ):
        self.axis, self.run, self.across, self.z, self.outward = axis, tuple( run ), tuple( across ), tuple( z ), outward
        self.openings = []

    def add( self, centre, width, z0, z1, kind="window" ):
        opening = Opening( centre - width / 2, centre + width / 2, z0, z1, kind )
        self.openings.append( opening )
        return opening

    def lo_hi( self, r0, r1, d0, d1, z0, z1 ):
        if self.axis == "e":
            return ( r0, min( d0, d1 ), z0 ), ( r1, max( d0, d1 ), z1 )
        return ( min( d0, d1 ), r0, z0 ), ( max( d0, d1 ), r1, z1 )

    def point( self, r, d, z ):
        return np.array( ( r, d, z ) if self.axis == "e" else ( d, r, z ), float )

    def faces( self ):
        """ Plan face names: the wall's two ends, then its two sides ( low d, high d ). """
        along = ( "-e", "+e" ) if self.axis == "e" else ( "-n", "+n" )
        across = ( "-n", "+n" ) if self.axis == "e" else ( "-e", "+e" )
        return along, across

    def outer( self ):
        """ The outside face's d and which way out is along d (+1 / -1). """
        d0, d1 = self.across
        return ( d0, -1.0 ) if self.outward.startswith( "-" ) else ( d1, 1.0 )

    def build( self, model, outside, inside, reveal, end=None, surface="default", sill_paint=None ):
        """ The wall in vertical strips between its openings' edges, each strip solid wherever no opening crosses it.
        Openings' sides, heads and sills are painted reveal (sill_paint for a door's sill outside), the wall's ends end
        (None where they're hidden in another wall). Arches get their curved heads here too. """
        ( r_lo, r_hi ), ( z_lo, z_hi ) = self.run, self.z
        along, across = self.faces()
        if self.outward:
            out_face = self.outward
            in_face = across[1] if out_face == across[0] else across[0]
        else:
            out_face, in_face = across
            outside = inside
        cuts = [ ( o.r0, o.r1, o.z0, o.rect_top, o ) for o in self.openings ]
        edges = sorted( { r_lo, r_hi } | { r for c in cuts for r in c[:2] } )
        strips = list( zip( edges, edges[1:] ) )

        def holes( s0, s1 ):
            return sorted( ( z0, z1, o ) for r0, r1, z0, z1, o in cuts if r0 <= s0 + 1e-6 and r1 >= s1 - 1e-6 )

        def open_beside( r, z0, z1, before ):
            for s0, s1 in strips:
                if ( abs( s1 - r ) < 1e-6 ) if before else ( abs( s0 - r ) < 1e-6 ):
                    return any( h0 < z1 and h1 > z0 for h0, h1, _ in holes( s0, s1 ) )
            return False

        for s0, s1 in strips:
            bottom = z_lo
            for h0, h1, o in holes( s0, s1 ) + [ ( z_hi, z_hi, None ) ]:
                if h0 > bottom + 1e-6:
                    top = h0
                    above = o is not None and top < z_hi
                    sill = ( sill_paint or reveal ) if o is not None and o.kind in ( "door", "arch" ) and self.outward else reveal
                    below_is_arch = any( oo.arched and abs( oo.rect_top - bottom ) < 1e-6 and oo.r0 <= s0 + 1e-6
                                         and oo.r1 >= s1 - 1e-6 for oo in self.openings )
                    paints = { out_face: outside, in_face: inside,
                               "+z": sill if above else None,
                               "-z": ( None if below_is_arch else reveal ) if bottom > z_lo else None,
                               along[0]: end if abs( s0 - r_lo ) < 1e-6 else ( reveal if open_beside( s0, bottom, top, True ) else None ),
                               along[1]: end if abs( s1 - r_hi ) < 1e-6 else ( reveal if open_beside( s1, bottom, top, False ) else None ) }
                    model.box( *self.lo_hi( s0, s1, *self.across, bottom, top ), paints, surface )
                if h1 > bottom:
                    bottom = h1
        for o in self.openings:
            if o.arched:
                self._arch_head( model, o, outside, inside, reveal, out_face, surface )

    def _arch_head( self, model, o, outside, inside, reveal, out_face, surface, steps=12 ):
        """ The curved head of an arch: the spandrels either side on both faces, filling the wall down from the
        rectangle's top to the curve, and the soffit under the curve. """
        rc, zs, rad, top = ( o.r0 + o.r1 ) / 2, o.spring, o.radius, o.rect_top
        d0, d1 = self.across
        out_d = d0 if out_face in ( "-n", "-e" ) else d1
        in_d = d1 if out_d == d0 else d0
        curve = arc( rc, zs, rad, steps )                       # left foot, over the crown, to the right foot
        half = steps // 2
        for d, paint in ( ( out_d, outside ), ( in_d, inside ) ):
            # The polygon is wound for the side it faces.
            facing = np.array( ( 0.0, 1.0 if d == max( d0, d1 ) else -1.0, 0.0 ) ) if self.axis == "e" else \
                np.array( ( 1.0 if d == max( d0, d1 ) else -1.0, 0.0, 0.0 ) )
            for k, piece in enumerate( ( curve[:half + 1], curve[half:] ) ):
                # Fanned from the spandrel's top corner, which sees the whole curve.
                corner = ( o.r0, top ) if k == 0 else ( o.r1, top )
                pts = [ corner ] + [ ( r, min( z, top ) ) for r, z in piece ]
                pts3 = [ self.point( r, d, z ) for r, z in pts ]
                normal = np.zeros( 3 )
                for i in range( 1, len( pts3 ) - 1 ):
                    normal += np.cross( pts3[i] - pts3[0], pts3[i + 1] - pts3[0] )
                if np.linalg.norm( normal ) < 1e-9:
                    continue
                if np.dot( normal, facing ) < 0:
                    pts3 = pts3[:1] + pts3[:0:-1]
                model.polygon( paint, pts3 )
        # Soffit: quads under the curve, facing down into the opening.
        for ( ra, za ), ( rb, zb ) in zip( curve, curve[1:] ):
            za, zb = min( za, top ), min( zb, top )
            quad = [ self.point( ra, d0, za ), self.point( rb, d0, zb ), self.point( rb, d1, zb ), self.point( ra, d1, za ) ]
            mid_r, mid_z = ( ra + rb ) / 2, ( za + zb ) / 2
            towards = self.point( rc, 0, zs ) - self.point( mid_r, 0, mid_z )
            towards[AXIS["n"] if self.axis == "e" else AXIS["e"]] = 0.0
            normal = np.cross( quad[1] - quad[0], quad[2] - quad[0] )
            if np.dot( normal, towards ) < 0:
                quad = quad[:1] + quad[:0:-1]
            model.polygon( reveal, quad )
        # The spandrels' collision: a box in each top corner, wholly outside the curve (at 0.3 of the radius in from
        # the side the curve is 0.714 of the radius up).
        if surface:
            for r0, r1 in ( ( o.r0, o.r0 + 0.3 * rad ), ( o.r1 - 0.3 * rad, o.r1 ) ):
                model.collision_box( *self.lo_hi( r0, r1, d0, d1, zs + 0.72 * rad, top ), surface )


# ---------------------------------------------------------------------------------------------------------------------
# UVs, and writing a model

def face_uv( point, normal, paint, offset=( 0.0, 0.0 ), tile=None ):
    """ World-scale UVs (v up the picture), as seen from in front of the face: up is uphill along the face (north on a
    floor), right is to your right looking at it. Both in world space. """
    n = normalise( normal )
    if abs( n[2] ) > 0.999:
        up = np.array( ( 1.0, 0.0, 0.0 ) )
    else:
        up = normalise( np.array( ( 0.0, 0.0, 1.0 ) ) - n[2] * n )
    right = np.cross( -n, up )
    scale = tile if tile is not None else BT.tile_units( paint )
    return ( float( np.dot( point, right ) / scale + offset[0] ), float( np.dot( point, up ) / scale + offset[1] ) )


def obj_vector( p ):
    """ World ( x, y, z ) to the OBJ's axes ( y, z, x ). """
    return f"{p[1]:.3f} {p[2]:.3f} {p[0]:.3f}"


def uv_offset( name ):
    """ A steady per-model shift of the textures, so two buildings in the same paint don't show the same stones. """
    h = zlib.crc32( name.encode() )
    return ( ( h & 0xFFFF ) / 65535.0 * 7.0, ( ( h >> 16 ) & 0xFFFF ) / 65535.0 * 7.0 )


def write_obj( path, model, name ):
    offset = uv_offset( name )
    lines = [ "# Tools/map_kit.py", f"mtllib {path.stem}.mtl", f"o {path.stem}" ]
    vertices, uvs, normals, faces = [], [], [], []
    for paint in sorted( model.polygons ):
        faces.append( f"usemtl {paint}" )
        decal = paint in BT.DECALS
        for index, (points, normal) in enumerate(model.polygons[paint]):
            base = len( vertices )
            wn = to_world( normal )
            smooth = model.polygon_normals.get( ( paint, index ) )
            first_normal = len( normals ) + 1
            if smooth is None:
                normals.append( f"vn {obj_vector( wn )}" )
            else:
                normals.extend( f"vn {obj_vector( to_world( n ) )}" for n in smooth )
            world = [ to_world( p ) for p in points ]
            coords = [ face_uv( wp, wn, paint, offset, model.tile_overrides.get( paint ) ) for wp in world ]
            if paint in model.grain_paints:
                # Boards, rails and spokes need grain along their length, regardless of their world orientation.
                edges = [world[(i+1)%len(world)]-p for i,p in enumerate(world)]
                along = normalise(max(edges, key=lambda e: np.linalg.norm(e)))
                across = np.cross(wn, along)
                tile = model.tile_overrides.get(paint, BT.tile_units(paint))
                coords = [(float(np.dot(wp,across)/tile+offset[0]), float(np.dot(wp,along)/tile+offset[1])) for wp in world]
            coords = model.polygon_uvs.get((paint,index), coords)
            if decal:
                # Once across the polygon, whatever its size.
                us, vs = [ u for u, _ in coords ], [ v for _, v in coords ]
                coords = [ ( ( u - min( us ) ) / ( max( us ) - min( us ) ), ( v - min( vs ) ) / ( max( vs ) - min( vs ) ) )
                           for u, v in coords ]
            for wp, ( u, v ) in zip( world, coords ):
                vertices.append( f"v {obj_vector( wp )}" )
                uvs.append( f"vt {u:.5f} {v:.5f}" )
            for k in range( 1, len( points ) - 1 ):
                a, b, c = base + 1, base + k + 1, base + k + 2
                if smooth is None:
                    na = nb = nc = first_normal
                else:
                    na, nb, nc = first_normal, first_normal + k, first_normal + k + 1
                faces.append( f"f {a}/{a}/{na} {b}/{b}/{nb} {c}/{c}/{nc}" )
    write_text( path, "\n".join( lines + vertices + uvs + normals + faces ) + "\n" )
    write_text( path.with_suffix( ".mtl" ), "".join( f"newmtl {paint}\nKd 1 1 1\nd 1\n" for paint in sorted( model.polygons ) ) )
    return sum( 1 for f in faces if f.startswith( "f " ) )


def convex_faces( points ):
    """ The faces of the convex hull of points (world), each wound outwards, as index lists. """
    from scipy.spatial import ConvexHull
    pts = np.asarray( points, float )
    hull = ConvexHull( pts )
    centre = pts[hull.vertices].mean( axis=0 )
    faces = []
    for simplex in hull.simplices:
        a, b, c = pts[simplex]
        if np.dot( np.cross( b - a, c - a ), ( a + b + c ) / 3 - centre ) < 0:
            simplex = simplex[::-1]
        faces.append( list( simplex ) )
    return faces


def write_hulls_obj( path, hulls ):
    """ Every hull as its own element (no shared vertices), for ModelDoc's HullPerElement. """
    lines = [ "# Tools/map_kit.py: collision hulls", f"o {path.stem}" ]
    faces = []
    count = 0
    for points in hulls:
        world = [ to_world( p ) for p in points ]
        for w in world:
            lines.append( f"v {obj_vector( w )}" )
        for face in convex_faces( world ):
            faces.append( "f " + " ".join( str( count + i + 1 ) for i in face ) )
        count += len( world )
    write_text( path, "\n".join( lines + faces ) + "\n" )


def vec3( v ):
    return "[ " + ", ".join( f"{c:.4f}" for c in v ) + " ]"


def write_vmdl( path, resource_dir, name, model ):
    """ <name>.vmdl, after its hulls' OBJs. Returns the paths of the hull OBJs it wrote. """
    remaps = ",\n".join( f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{model.material_overrides.get( paint, BT.material_path( paint ) )}" }}'
                         for paint in sorted( model.polygons ) )
    shapes = []
    for centre, axes, size, surface in model.boxes:
        world_axes = [ to_world( a ) for a in axes ]
        shapes.append( "\t\t\t\t\t{\n"
                       '\t\t\t\t\t\t_class = "PhysicsShapeBox"\n'
                       '\t\t\t\t\t\tparent_bone = ""\n'
                       f'\t\t\t\t\t\tsurface_prop = "{surface}"\n'
                       '\t\t\t\t\t\tcollision_tags = "solid"\n'
                       f"\t\t\t\t\t\torigin = {vec3( to_world( centre ) )}\n"
                       f"\t\t\t\t\t\tangles = {vec3( angles_of( world_axes ) )}\n"
                       f"\t\t\t\t\t\tdimensions = {vec3( size )}\n"
                       "\t\t\t\t\t}," )
    by_surface = defaultdict( list )
    for points, surface in model.hulls:
        by_surface[surface].append( points )
    hull_files = set()
    for surface, hulls in sorted( by_surface.items() ):
        hull_name = f"{name}_hulls_{surface.replace( '.', '_' )}"
        hull_files.add( path.parent / f"{hull_name}.obj" )
        write_hulls_obj( path.parent / f"{hull_name}.obj", hulls )
        shapes.append( "\t\t\t\t\t{\n"
                       '\t\t\t\t\t\t_class = "PhysicsHullFile"\n'
                       f'\t\t\t\t\t\tname = "{hull_name}"\n'
                       '\t\t\t\t\t\tparent_bone = ""\n'
                       f'\t\t\t\t\t\tsurface_prop = "{surface}"\n'
                       '\t\t\t\t\t\tcollision_tags = "solid"\n'
                       "\t\t\t\t\t\trecenter_on_parent_bone = false\n"
                       "\t\t\t\t\t\toffset_origin = [ 0.0, 0.0, 0.0 ]\n"
                       "\t\t\t\t\t\toffset_angles = [ 0.0, 0.0, 0.0 ]\n"
                       '\t\t\t\t\t\talign_origin_x_type = "None"\n'
                       '\t\t\t\t\t\talign_origin_y_type = "None"\n'
                       '\t\t\t\t\t\talign_origin_z_type = "None"\n'
                       f'\t\t\t\t\t\tfilename = "{resource_dir}/{hull_name}.obj"\n'
                       "\t\t\t\t\t\timport_scale = 1.0\n"
                       "\t\t\t\t\t\tfaceMergeAngle = 10.0\n"
                       "\t\t\t\t\t\tmaxHullVertices = 0\n"
                       '\t\t\t\t\t\timport_mode = "HullPerElement"\n'
                       '\t\t\t\t\t\toptimization_algorithm = "QEM"\n'
                       "\t\t\t\t\t\timport_filter = { exclude_by_default = false exception_list = [ ] }\n"
                       "\t\t\t\t\t}," )
    physics = ""
    if shapes:
        physics = ( "\t\t\t{\n"
                    '\t\t\t\t_class = "PhysicsShapeList"\n'
                    "\t\t\t\tchildren =\n"
                    "\t\t\t\t[\n"
                    + "\n".join( shapes ) + "\n"
                    "\t\t\t\t]\n"
                    "\t\t\t},\n" )
    text = ( "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
             "{\n"
             "\trootNode =\n"
             "\t{\n"
             '\t\t_class = "RootNode"\n'
             "\t\tchildren =\n"
             "\t\t[\n"
             "\t\t\t{\n"
             '\t\t\t\t_class = "MaterialGroupList"\n'
             "\t\t\t\tchildren =\n"
             "\t\t\t\t[\n"
             "\t\t\t\t\t{\n"
             '\t\t\t\t\t\t_class = "DefaultMaterialGroup"\n'
             "\t\t\t\t\t\tremaps =\n"
             "\t\t\t\t\t\t[\n"
             + remaps + "\n"
             "\t\t\t\t\t\t]\n"
             "\t\t\t\t\t\tuse_global_default = false\n"
             '\t\t\t\t\t\tglobal_default_material = ""\n'
             "\t\t\t\t\t},\n"
             "\t\t\t\t]\n"
             "\t\t\t},\n"
             "\t\t\t{\n"
             '\t\t\t\t_class = "RenderMeshList"\n'
             "\t\t\t\tchildren =\n"
             "\t\t\t\t[\n"
             "\t\t\t\t\t{\n"
             '\t\t\t\t\t\t_class = "RenderMeshFile"\n'
             f'\t\t\t\t\t\tname = "{name}"\n'
             f'\t\t\t\t\t\tfilename = "{resource_dir}/{name}.obj"\n'
             "\t\t\t\t\t\timport_translation = [ 0.0, 0.0, 0.0 ]\n"
             "\t\t\t\t\t\timport_rotation = [ 0.0, 0.0, 0.0 ]\n"
             "\t\t\t\t\t\timport_scale = 1.0\n"
             '\t\t\t\t\t\talign_origin_x_type = "None"\n'
             '\t\t\t\t\t\talign_origin_y_type = "None"\n'
             '\t\t\t\t\t\talign_origin_z_type = "None"\n'
             '\t\t\t\t\t\tparent_bone = ""\n'
             "\t\t\t\t\t\timport_filter = { exclude_by_default = false exception_list = [ ] }\n"
             "\t\t\t\t\t},\n"
             "\t\t\t\t]\n"
             "\t\t\t},\n"
             + physics +
             "\t\t]\n"
             '\t\tmodel_archetype = ""\n'
             '\t\tprimary_associated_entity = ""\n'
             '\t\tanim_graph_name = ""\n'
             '\t\tbase_model_name = ""\n'
             "\t}\n"
             "}\n" )
    write_text( path, text )
    return hull_files


def write_text( path, text, newline="\n" ):
    """ Writes a file through a temporary one beside it, renamed over it once complete, so the editor, which compiles a
    changed file straight away, never reads it half-written. """
    temp = path.with_name( f"{path.name}.writing" )
    temp.write_text( text, encoding="utf-8", newline=newline )
    temp.replace( path )


def write_model( out_dir, resource_dir, name, model ):
    """ <name>.obj/.mtl, its hulls' OBJs and <name>.vmdl, then deletes the hull OBJs the model no longer uses. They
    aren't deleted first: the editor compiled the old vmdl the moment they went, and failed to find them. Returns the
    triangle count. """
    out_dir.mkdir( parents=True, exist_ok=True )
    old_hulls = set( out_dir.glob( f"{name}_hulls_*.obj" ) )
    triangles = write_obj( out_dir / f"{name}.obj", model, name )
    written = write_vmdl( out_dir / f"{name}.vmdl", resource_dir, name, model )
    for stale in old_hulls - written:
        stale.unlink()
        stale.with_name( f"{stale.name}.meta" ).unlink( missing_ok=True )
    return triangles


# ---------------------------------------------------------------------------------------------------------------------
# Scene JSON (as Tools/ridgeback_map.py writes it)

class SceneIds:
    """ Steady GUIDs from keys, so a re-run writes the same ids. """

    def __init__( self, namespace ):
        self.namespace = uuid.UUID( namespace )

    def __call__( self, key ):
        return str( uuid.uuid5( self.namespace, key ) )


def vec( v ):
    return ",".join( f"{c:g}" for c in v )


def yaw_rotation( degrees ):
    half = math.radians( degrees ) / 2
    return f"0,0,{math.sin( half ):.7f},{math.cos( half ):.7f}"


def angles_rotation( pitch, yaw, roll=0.0 ):
    """ Rotation.From( pitch, yaw, roll ) as x,y,z,w. """
    sp, cp = math.sin( math.radians( pitch ) / 2 ), math.cos( math.radians( pitch ) / 2 )
    sy, cy = math.sin( math.radians( yaw ) / 2 ), math.cos( math.radians( yaw ) / 2 )
    sr, cr = math.sin( math.radians( roll ) / 2 ), math.cos( math.radians( roll ) / 2 )
    return ",".join( f"{v:.7f}" for v in ( sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
                                            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy ) )


def plan_yaw( heading ):
    """ The world yaw (degrees) that faces plan heading ( de, dn ). World yaw 0 is +x (north), 90 is +y (west). """
    return math.degrees( math.atan2( -heading[0], heading[1] ) )


def component( ids, type_name, key, **props ):
    return { "__type": type_name, "__guid": ids( key ), "__enabled": True, "Flags": 0, **props }


def game_object( ids, name, key, position=( 0, 0, 0 ), rotation="0,0,0,1", components=(), children=(), tags="",
                 scale="1,1,1" ):
    return {
        "__guid": ids( key ), "__version": 2, "Flags": 0, "Name": name, "Position": vec( position ),
        "Rotation": rotation, "Scale": scale, "Tags": tags, "Enabled": True, "NetworkMode": 2, "NetworkFlags": 0,
        "NetworkOrphaned": 0, "NetworkTransmit": True, "OwnerTransfer": 1, "Components": list( components ),
        "Children": list( children ),
    }


def prefab_instance( ids, path, key=None, overrides=() ):
    """ A prefab dropped into the scene, with an instance id for everything in it (as the editor writes).
    overrides: ( property, value ) pairs on the prefab's root. """
    prefab = json.loads( ( ASSETS / path ).read_text( encoding="utf-8-sig" ) )
    found = set()

    def collect( node ):
        if isinstance( node, dict ):
            if "__guid" in node:
                found.add( node["__guid"] )
            if isinstance( node.get( "__PrefabIdToInstanceId" ), dict ):
                found.update( node["__PrefabIdToInstanceId"].values() )
            for k, value in node.items():
                if k != "__PrefabIdToInstanceId":
                    collect( value )
        elif isinstance( node, list ):
            for value in node:
                collect( value )

    collect( prefab["RootObject"] )
    root = prefab["RootObject"]["__guid"]
    resource = json.loads( ( ASSETS / f"{path}.meta" ).read_text( encoding="utf-8" ) )["guid"]
    key = key or f"prefab/{path}"
    instance = ids( key )
    mapping = { pid: instance if pid == root else ids( f"{key}/{pid}" ) for pid in sorted( found ) }
    target = { "Type": "GameObject", "IdValue": root }
    return {
        "__guid": instance, "__version": 2, "__Prefab": { "Id": resource, "Path": path },
        "__PrefabInstancePatch": { "AddedObjects": [], "RemovedObjects": [],
                                   "PropertyOverrides": [ { "Target": target, "Property": p, "Value": v } for p, v in overrides ],
                                   "MovedObjects": [] },
        "__PrefabIdToInstanceId": mapping,
    }
