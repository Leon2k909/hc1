"""
Railhead's kiosk: its texture atlas, rw_kiosk, drawn in plain Python (no numpy, no PIL) from the project's own fonts.

    python Tools/railhead_kiosk_art.py [--out <dir>]

Writes Assets/materials/railhead/rw_kiosk_color.png, _trans.png (alpha test: the fascia's lettering and the pier's
icons are cut out; everything else is opaque), _rough.png, _illum.png (the backlit lettering and the card terminal's
screen glow) and rw_kiosk.vmat. railhead_props.kiosk() places the entries by RECTS (rect_uv), which come from the
packer alone, so they're known without drawing anything. railhead_map.py runs it when the pictures aren't there (the
session that made it couldn't upload them to the repository's LFS store).

The kiosk is a modern station kiosk (Zeitschriften, Getraenke, Snacks): white lettering in Dinish (a DIN 1451 face, as
German signs are set) on the anthracite fascia, line icons on the pier, a menu board, a framed travel poster, and the
goods: magazine covers, crisp packets, bottle labels, sweet bars and the card terminal's screen. Every name on them is a plain
German word; no real brand, title or logo.

It needs its own rasteriser because the sandbox this was made in had neither numpy nor PIL: Font reads a TrueType
font's glyf outlines (simple and composite glyphs, cmap formats 4 and 12, the kern table), and Canvas fills polygons
with nonzero winding, 4 sub-scanlines a row and exact coverage along each, over RGB, alpha and roughness planes.
"""
import argparse
import math
import struct
import zlib
from array import array
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
FONTS = ROOT / "Assets/fonts"
OUT_DIR = ROOT / "Assets/materials/railhead"
RESOURCE_DIR = "materials/railhead"
W, H = 2048, 2048
PAD = 8

# ( name, width, height ) in pixels, packed in rows by height (pack()).
ENTRIES = ( [ ( "kiosk_word", 720, 260 ), ( "kiosk_sub", 1500, 120 ), ( "icons", 200, 600 ), ( "menu", 440, 560 ),
              ( "poster", 440, 640 ), ( "pos_screen", 240, 160 ) ]
            + [ ( f"mag_{k}", 240, 330 ) for k in range( 8 ) ]
            + [ ( f"chips_{k}", 260, 340 ) for k in range( 5 ) ]
            + [ ( f"label_{k}", 360, 120 ) for k in range( 6 ) ]
            + [ ( f"candy_{k}", 320, 96 ) for k in range( 4 ) ] )
CUT_OUT = { "kiosk_word", "kiosk_sub", "icons" }       # alpha-tested lettering; the rest is opaque
GLOW = CUT_OUT | { "pos_screen" }                       # self-lit (_illum.png): the backlit lettering and the screen
ILLUM = 1.3


def pack():
    """ name: ( x0, y0, x1, y1 ) in pixels from the top left: rows of entries, tallest first. """
    order = sorted( ENTRIES, key=lambda e: ( -e[2], ENTRIES.index( e ) ) )
    rects, x, y, row_h = {}, PAD, PAD, 0
    for name, w, h in order:
        if x + w + PAD > W:
            x, y, row_h = PAD, y + row_h + PAD, 0
        rects[name] = ( x, y, x + w, y + h )
        x += w + PAD
        row_h = max( row_h, h )
    assert y + row_h <= H, "the kiosk's atlas doesn't fit"
    return rects


RECTS = pack()


def rect_uv( name ):
    """ ( u0, v0, u1, v1 ) of an entry, v up from the picture's bottom edge (railhead_materials.rect_uv's way). """
    x0, y0, x1, y1 = RECTS[name]
    return ( x0 / W, 1.0 - y1 / H, x1 / W, 1.0 - y0 / H )


def aspect( name ):
    x0, y0, x1, y1 = RECTS[name]
    return ( x1 - x0 ) / ( y1 - y0 )


# ---------------------------------------------------------------------------------------------------------------------
# TrueType

class Font:
    """ A TrueType font's outlines and advances (glyf fonts only). """

    def __init__( self, path ):
        d = self.d = Path( path ).read_bytes()
        count = struct.unpack_from( ">H", d, 4 )[0]
        self.t = {}
        for i in range( count ):
            tag, _, off, length = struct.unpack_from( ">4sIII", d, 12 + 16 * i )
            self.t[tag.decode( "latin-1" )] = ( off, length )
        head = self.t["head"][0]
        self.upem = struct.unpack_from( ">H", d, head + 18 )[0]
        long_loca = struct.unpack_from( ">h", d, head + 50 )[0] == 1
        glyphs = struct.unpack_from( ">H", d, self.t["maxp"][0] + 4 )[0]
        metrics = struct.unpack_from( ">H", d, self.t["hhea"][0] + 34 )[0]
        hmtx = self.t["hmtx"][0]
        self.adv = [ struct.unpack_from( ">H", d, hmtx + 4 * min( g, metrics - 1 ) )[0] for g in range( glyphs ) ]
        loca = self.t["loca"][0]
        if long_loca:
            self.loca = [ struct.unpack_from( ">I", d, loca + 4 * i )[0] for i in range( glyphs + 1 ) ]
        else:
            self.loca = [ 2 * struct.unpack_from( ">H", d, loca + 2 * i )[0] for i in range( glyphs + 1 ) ]
        self.cmap = self._cmap()
        self.kern = self._kern()
        self.cache = {}
        self.cap = max( y for c in self.contours( self.glyph( "H" ) ) for _, y, _ in c ) / self.upem

    def _cmap( self ):
        d, base = self.d, self.t["cmap"][0]
        subs = []
        for i in range( struct.unpack_from( ">H", d, base + 2 )[0] ):
            pid, eid, off = struct.unpack_from( ">HHI", d, base + 4 + 8 * i )
            subs.append( ( pid, eid, base + off ) )
        out = {}
        for _, _, off in subs:
            fmt = struct.unpack_from( ">H", d, off )[0]
            if fmt == 12:
                for k in range( struct.unpack_from( ">I", d, off + 12 )[0] ):
                    sc, ec, sg = struct.unpack_from( ">III", d, off + 16 + 12 * k )
                    for c in range( sc, ec + 1 ):
                        out.setdefault( c, sg + c - sc )
            elif fmt == 4:
                seg2 = struct.unpack_from( ">H", d, off + 6 )[0]
                ends = off + 14
                starts = ends + seg2 + 2
                deltas = starts + seg2
                ranges = deltas + seg2
                for s in range( seg2 // 2 ):
                    end = struct.unpack_from( ">H", d, ends + 2 * s )[0]
                    start = struct.unpack_from( ">H", d, starts + 2 * s )[0]
                    delta = struct.unpack_from( ">h", d, deltas + 2 * s )[0]
                    ro = struct.unpack_from( ">H", d, ranges + 2 * s )[0]
                    for c in range( start, min( end, 0xFFFE ) + 1 ):
                        if ro == 0:
                            g = ( c + delta ) & 0xFFFF
                        else:
                            g = struct.unpack_from( ">H", d, ranges + 2 * s + ro + 2 * ( c - start ) )[0]
                            g = ( g + delta ) & 0xFFFF if g else 0
                        if g:
                            out.setdefault( c, g )
        return out

    def _kern( self ):
        if "kern" not in self.t:
            return {}
        d, off = self.d, self.t["kern"][0]
        tables = struct.unpack_from( ">H", d, off + 2 )[0]
        p, out = off + 4, {}
        for _ in range( tables ):
            _, length, coverage = struct.unpack_from( ">HHH", d, p )
            if coverage >> 8 == 0:
                for k in range( struct.unpack_from( ">H", d, p + 6 )[0] ):
                    left, right, value = struct.unpack_from( ">HHh", d, p + 14 + 6 * k )
                    out[( left, right )] = value
            p += length
        return out

    def glyph( self, ch ):
        return self.cmap.get( ord( ch ), 0 )

    def contours( self, g ):
        """ The glyph's contours: lists of ( x, y, on-curve ) in font units, y up. """
        if g in self.cache:
            return self.cache[g]
        d, glyf = self.d, self.t["glyf"][0]
        a, b = self.loca[g], self.loca[g + 1]
        res = []
        if b > a:
            p = glyf + a
            nc = struct.unpack_from( ">h", d, p )[0]
            if nc >= 0:
                ends = [ struct.unpack_from( ">H", d, p + 10 + 2 * i )[0] for i in range( nc ) ]
                npts = ends[-1] + 1 if ends else 0
                q = p + 10 + 2 * nc
                q += 2 + struct.unpack_from( ">H", d, q )[0]
                flags = []
                while len( flags ) < npts:
                    f = d[q]
                    q += 1
                    flags.append( f )
                    if f & 8:
                        flags.extend( [ f ] * d[q] )
                        q += 1
                flags = flags[:npts]
                coords = []
                for short, same in ( ( 2, 16 ), ( 4, 32 ) ):
                    v, vals = 0, []
                    for f in flags:
                        if f & short:
                            v += d[q] if f & same else -d[q]
                            q += 1
                        elif not f & same:
                            v += struct.unpack_from( ">h", d, q )[0]
                            q += 2
                        vals.append( v )
                    coords.append( vals )
                xs, ys = coords
                start = 0
                for e in ends:
                    res.append( [ ( xs[i], ys[i], bool( flags[i] & 1 ) ) for i in range( start, e + 1 ) ] )
                    start = e + 1
            else:
                q = p + 10
                while True:
                    fl, gi = struct.unpack_from( ">HH", d, q )
                    q += 4
                    if fl & 1:
                        dx, dy = struct.unpack_from( ">hh", d, q )
                        q += 4
                    else:
                        dx, dy = struct.unpack_from( ">bb", d, q )
                        q += 2
                    m = ( 1.0, 0.0, 0.0, 1.0 )
                    if fl & 8:
                        s = struct.unpack_from( ">h", d, q )[0] / 16384
                        m = ( s, 0.0, 0.0, s )
                        q += 2
                    elif fl & 0x40:
                        sx, sy = ( v / 16384 for v in struct.unpack_from( ">hh", d, q ) )
                        m = ( sx, 0.0, 0.0, sy )
                        q += 4
                    elif fl & 0x80:
                        m = tuple( v / 16384 for v in struct.unpack_from( ">hhhh", d, q ) )
                        q += 8
                    if not fl & 2:
                        dx = dy = 0
                    for cont in self.contours( gi ):
                        res.append( [ ( m[0] * x + m[2] * y + dx, m[1] * x + m[3] * y + dy, on ) for x, y, on in cont ] )
                    if not fl & 0x20:
                        break
        self.cache[g] = res
        return res

    def layout( self, s, size, tracking=0.0 ):
        """ [ ( glyph, pen x ) ] and the advance, for a string at em size px. """
        scale, pen, prev, out = size / self.upem, 0.0, None, []
        for ch in s:
            g = self.glyph( ch )
            if prev is not None:
                pen += self.kern.get( ( prev, g ), 0 ) * scale
            out.append( ( g, pen ) )
            pen += self.adv[g] * scale + tracking * size
            prev = g
        return out, pen - ( tracking * size if s else 0.0 )

    def width( self, s, size, tracking=0.0 ):
        return self.layout( s, size, tracking )[1]

    def polys( self, s, size, x, baseline, tracking=0.0 ):
        """ The string's outlines as pixel polygons (y down), its left at x. """
        scale = size / self.upem
        out = []
        for g, pen in self.layout( s, size, tracking )[0]:
            for cont in self.contours( g ):
                out.append( [ ( x + pen + px * scale, baseline - py * scale ) for px, py in flatten( cont ) ] )
        return out


def flatten( cont, steps=6 ):
    """ A TrueType contour (quadratic B-spline) as a polygon. """
    pts = list( cont )
    if not pts:
        return []
    if not pts[0][2]:
        if pts[-1][2]:
            pts = [ pts[-1] ] + pts[:-1]
        else:
            pts = [ ( ( pts[0][0] + pts[-1][0] ) / 2, ( pts[0][1] + pts[-1][1] ) / 2, True ) ] + pts
    out = [ ( pts[0][0], pts[0][1] ) ]
    cur, ctrl = pts[0], None

    def curve( a, c, b ):
        for k in range( 1, steps + 1 ):
            t = k / steps
            out.append( ( ( 1 - t ) ** 2 * a[0] + 2 * t * ( 1 - t ) * c[0] + t * t * b[0],
                          ( 1 - t ) ** 2 * a[1] + 2 * t * ( 1 - t ) * c[1] + t * t * b[1] ) )

    for p in pts[1:] + [ pts[0] ]:
        if p[2]:
            if ctrl is None:
                out.append( ( p[0], p[1] ) )
            else:
                curve( cur, ctrl, p )
                ctrl = None
            cur = p
        elif ctrl is None:
            ctrl = p
        else:
            mid = ( ( ctrl[0] + p[0] ) / 2, ( ctrl[1] + p[1] ) / 2, True )
            curve( cur, ctrl, mid )
            cur, ctrl = mid, p
    if ctrl is not None:
        curve( cur, ctrl, pts[0] )
    return out[:-1] if len( out ) > 1 and out[-1] == out[0] else out


# ---------------------------------------------------------------------------------------------------------------------
# The canvas

def hash01( x, y, seed=0 ):
    n = ( int( x ) * 374761393 + int( y ) * 668265263 + seed * 2246822519 ) & 0xFFFFFFFF
    n = ( ( n ^ ( n >> 13 ) ) * 1274126177 ) & 0xFFFFFFFF
    return ( ( n ^ ( n >> 16 ) ) & 0xFFFF ) / 65535.0


def mix( a, b, t ):
    return tuple( x + ( y - x ) * t for x, y in zip( a, b ) )


def area( poly ):
    return sum( x0 * y1 - x1 * y0 for ( x0, y0 ), ( x1, y1 ) in zip( poly, poly[1:] + poly[:1] ) ) / 2


class Canvas:
    def __init__( self, w, h ):
        self.w, self.h = w, h
        self.r, self.g, self.b = ( array( "f", [ 0.0 ] ) * ( w * h ) for _ in range( 3 ) )
        self.a = array( "f", [ 0.0 ] ) * ( w * h )
        self.rough = array( "f", [ 0.5 ] ) * ( w * h )

    def fill( self, polys, paint, alpha=1.0, rough=None, clip=None, orient=False, cover=False, colour=True ):
        """ Polygons ( lists of ( x, y ) pixels, y down ) filled by nonzero winding. paint: an ( r, g, b ) in 0..255, or
        f( x, y ) giving one. cover: also set the alpha (trans) plane; colour=False leaves the colour alone. """
        edges, xs_all = [], []
        for poly in polys:
            if len( poly ) < 3:
                continue
            if orient and area( poly ) < 0:
                poly = poly[::-1]
            xs_all += [ p[0] for p in poly ]
            for ( x0, y0 ), ( x1, y1 ) in zip( poly, poly[1:] + poly[:1] ):
                if y0 == y1:
                    continue
                if y0 < y1:
                    edges.append( ( y0, y1, x0, ( x1 - x0 ) / ( y1 - y0 ), 1 ) )
                else:
                    edges.append( ( y1, y0, x1, ( x0 - x1 ) / ( y0 - y1 ), -1 ) )
        if not edges:
            return
        cx0, cy0, cx1, cy1 = clip or ( 0, 0, self.w, self.h )
        y_lo = max( cy0, int( math.floor( min( e[0] for e in edges ) ) ) )
        y_hi = min( cy1, int( math.ceil( max( e[1] for e in edges ) ) ) )
        x_lo = max( cx0, int( math.floor( min( xs_all ) ) ) )
        x_hi = min( cx1, int( math.ceil( max( xs_all ) ) ) + 1 )
        if y_hi <= y_lo or x_hi <= x_lo:
            return
        edges.sort()
        span = x_hi - x_lo
        const = None if callable( paint ) else tuple( c / 255.0 for c in paint )
        S = 4
        idx, active = 0, []
        while idx < len( edges ) and edges[idx][1] <= y_lo:
            idx += 1
        for py in range( y_lo, y_hi ):
            diff = [ 0.0 ] * ( span + 2 )
            frac = [ 0.0 ] * ( span + 1 )
            hit = False
            for s in range( S ):
                sy = py + ( s + 0.5 ) / S
                while idx < len( edges ) and edges[idx][0] <= sy:
                    active.append( edges[idx] )
                    idx += 1
                active = [ e for e in active if e[1] > sy ]
                crossings = sorted( ( e[2] + ( sy - e[0] ) * e[3], e[4] ) for e in active if e[0] <= sy )
                wind = 0
                for i in range( len( crossings ) - 1 ):
                    wind += crossings[i][1]
                    if wind == 0:
                        continue
                    a = min( max( crossings[i][0] - x_lo, 0.0 ), span )
                    b = min( max( crossings[i + 1][0] - x_lo, 0.0 ), span )
                    if b <= a:
                        continue
                    hit = True
                    ia, ib = int( a ), int( b )
                    w = 1.0 / S
                    if ia == ib:
                        frac[ia] += ( b - a ) * w
                        continue
                    frac[ia] += ( ia + 1 - a ) * w
                    diff[ia + 1] += w
                    diff[ib] -= w
                    if ib < span:
                        frac[ib] += ( b - ib ) * w
            if not hit:
                continue
            run, row = 0.0, py * self.w + x_lo
            for i in range( span ):
                run += diff[i]
                c = run + frac[i]
                if c <= 0.0005:
                    continue
                a = ( c if c < 1.0 else 1.0 ) * alpha
                k = row + i
                if colour:
                    pr, pg, pb = const if const else tuple( v / 255.0 for v in paint( x_lo + i + 0.5, py + 0.5 ) )
                    self.r[k] += ( pr - self.r[k] ) * a
                    self.g[k] += ( pg - self.g[k] ) * a
                    self.b[k] += ( pb - self.b[k] ) * a
                if rough is not None:
                    self.rough[k] += ( rough - self.rough[k] ) * a
                if cover:
                    self.a[k] += ( 1.0 - self.a[k] ) * a

    def save( self, out, name ):
        def png( path, channels, rows ):
            raw = bytearray()
            for row in rows:
                raw.append( 0 )
                raw += row
            colour_type = { 1: 0, 3: 2 }[channels]

            def chunk( tag, data ):
                c = struct.pack( ">I", len( data ) ) + tag + data
                return c + struct.pack( ">I", zlib.crc32( tag + data ) & 0xFFFFFFFF )

            path.write_bytes( b"\x89PNG\r\n\x1a\n" + chunk( b"IHDR", struct.pack( ">IIBBBBB", self.w, self.h, 8, colour_type, 0, 0, 0 ) )
                              + chunk( b"IDAT", zlib.compress( bytes( raw ), 6 ) ) + chunk( b"IEND", b"" ) )

        def to8( v ):
            return 255 if v >= 1.0 else ( 0 if v <= 0.0 else int( v * 255 + 0.5 ) )

        def srgb( v ):
            return to8( v )

        w = self.w
        rows = []
        for y in range( self.h ):
            row = bytearray( 3 * w )
            base = y * w
            for x in range( w ):
                k = base + x
                row[3 * x] = srgb( self.r[k] )
                row[3 * x + 1] = srgb( self.g[k] )
                row[3 * x + 2] = srgb( self.b[k] )
            rows.append( row )
        png( out / f"{name}_color.png", 3, rows )
        for plane, suffix in ( ( self.a, "trans" ), ( self.rough, "rough" ) ):
            rows = [ bytearray( to8( plane[y * w + x] ) for x in range( w ) ) for y in range( self.h ) ]
            png( out / f"{name}_{suffix}.png", 1, rows )
        rows = [ bytearray( w ) for _ in range( self.h ) ]
        for entry in GLOW:
            x0, y0, x1, y1 = RECTS[entry]
            for y in range( max( 0, y0 - 4 ), min( self.h, y1 + 4 ) ):
                rows[y][max( 0, x0 - 4 ):min( w, x1 + 4 )] = b"\xff" * ( min( w, x1 + 4 ) - max( 0, x0 - 4 ) )
        png( out / f"{name}_illum.png", 1, rows )


# ---------------------------------------------------------------------------------------------------------------------
# Shapes (pixel coordinates, y down)

def rect( x0, y0, x1, y1 ):
    return [ ( x0, y0 ), ( x1, y0 ), ( x1, y1 ), ( x0, y1 ) ]


def rounded( x0, y0, x1, y1, r, steps=8 ):
    r = min( r, ( x1 - x0 ) / 2, ( y1 - y0 ) / 2 )
    pts = []
    for cx, cy, a0 in ( ( x1 - r, y0 + r, -90 ), ( x1 - r, y1 - r, 0 ), ( x0 + r, y1 - r, 90 ), ( x0 + r, y0 + r, 180 ) ):
        for k in range( steps + 1 ):
            t = math.radians( a0 + 90 * k / steps )
            pts.append( ( cx + r * math.cos( t ), cy + r * math.sin( t ) ) )
    return pts


def ellipse( cx, cy, rx, ry, turn=0.0, steps=40 ):
    c, s = math.cos( turn ), math.sin( turn )
    out = []
    for k in range( steps ):
        t = 2 * math.pi * k / steps
        x, y = rx * math.cos( t ), ry * math.sin( t )
        out.append( ( cx + x * c - y * s, cy + x * s + y * c ) )
    return out


def circle( cx, cy, r, steps=40 ):
    return ellipse( cx, cy, r, r, 0.0, steps )


def stroke( points, width, closed=False, caps=True ):
    """ A polyline's outline as polygons (one quad a segment and a disc a joint): fill with orient=True. """
    pts = list( points ) + ( [ points[0] ] if closed else [] )
    out, hw = [], width / 2
    for ( x0, y0 ), ( x1, y1 ) in zip( pts, pts[1:] ):
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot( dx, dy ) or 1.0
        nx, ny = -dy / length * hw, dx / length * hw
        out.append( [ ( x0 + nx, y0 + ny ), ( x1 + nx, y1 + ny ), ( x1 - nx, y1 - ny ), ( x0 - nx, y0 - ny ) ] )
    joints = pts if caps or closed else pts[1:-1]
    out += [ circle( x, y, hw, 16 ) for x, y in joints ]
    return out


def bezier( p0, p1, p2, p3, steps=16 ):
    out = []
    for k in range( steps + 1 ):
        t = k / steps
        u = 1 - t
        out.append( ( u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                      u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1] ) )
    return out


def vgrad( y0, y1, c0, c1, grain=0.0, seed=0 ):
    """ A vertical gradient paint from c0 at y0 to c1 at y1, with a little print grain. """
    def paint( x, y ):
        t = min( max( ( y - y0 ) / ( y1 - y0 ), 0.0 ), 1.0 )
        c = mix( c0, c1, t )
        if grain:
            g = 1.0 + grain * ( hash01( x, y, seed ) - 0.5 )
            c = tuple( v * g for v in c )
        return c
    return paint


# ---------------------------------------------------------------------------------------------------------------------
# The art

WHITE = ( 240, 238, 232 )
INK = ( 30, 31, 33 )


class Art:
    def __init__( self, canvas ):
        self.c = canvas
        self.bold = Font( FONTS / "Dinish-Bold.ttf" )
        self.regular = Font( FONTS / "Dinish-Regular.ttf" )

    # Text helpers: size given as cap height in pixels.
    def text( self, s, cap, x, baseline, paint, font=None, tracking=0.0, align="left", alpha=1.0, rough=None,
              cover=False, clip=None ):
        font = font or self.regular
        size = cap / font.cap
        width = font.width( s, size, tracking )
        if align == "centre":
            x -= width / 2
        elif align == "right":
            x -= width
        self.c.fill( font.polys( s, size, x, baseline, tracking ), paint, alpha, rough, clip=clip, cover=cover )
        return width

    def fit_cap( self, s, font, cap, width, tracking=0.0 ):
        """ The cap height that's cap or less and fits s in width. """
        size = cap / font.cap
        w = font.width( s, size, tracking )
        return cap if w <= width else cap * width / w

    def entry( self, name ):
        x0, y0, x1, y1 = RECTS[name]
        return x0, y0, x1, y1, x1 - x0, y1 - y0

    def opaque( self, name, paint, rough ):
        """ An opaque entry's ground, run 3 px into the padding so the mips don't bleed. """
        x0, y0, x1, y1, w, h = self.entry( name )
        self.c.fill( [ rect( x0 - 3, y0 - 3, x1 + 3, y1 + 3 ) ], paint, rough=rough, cover=True )
        return x0, y0, x1, y1, w, h

    # --- Lettering (cut out of the alpha plane; white everywhere so the mips stay white)
    def lettering( self ):
        for name in CUT_OUT:
            x0, y0, x1, y1, w, h = self.entry( name )
            self.c.fill( [ rect( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ) ], WHITE, rough=0.45 )
        x0, y0, x1, y1, w, h = self.entry( "kiosk_word" )
        cap = self.fit_cap( "Kiosk", self.bold, h * 0.74, w * 0.96, 0.01 )
        size = cap / self.bold.cap
        width = self.bold.width( "Kiosk", size, 0.01 )
        self.c.fill( self.bold.polys( "Kiosk", size, x0 + ( w - width ) / 2, y0 + h / 2 + cap / 2, 0.01 ), WHITE,
                     cover=True )
        x0, y0, x1, y1, w, h = self.entry( "kiosk_sub" )
        s = "Zeitschriften · Getränke · Snacks"
        cap = self.fit_cap( s, self.regular, h * 0.62, w * 0.97, 0.02 )
        size = cap / self.regular.cap
        width = self.regular.width( s, size, 0.02 )
        polys = self.regular.polys( s, size, x0 + ( w - width ) / 2, y0 + h / 2 + cap / 2, 0.02 )
        self.c.fill( polys, WHITE, cover=True )
        # Emboldened a little (its outlines stroked), so the strokes outlast the mips' alpha test further off.
        self.c.fill( [ q for poly in polys for q in stroke( poly, 4.5, closed=True ) ], WHITE, cover=True, orient=True )
        self.icons()

    def icons( self ):
        """ The pier's line icons: a newspaper, a bottle and a crisp packet, each in a rounded square. """
        x0, y0, x1, y1, w, h = self.entry( "icons" )
        lw = w * 0.035
        for k in range( 3 ):
            ox, oy, s = x0, y0 + k * w, w / 200.0

            def P( x, y ):
                return ( ox + x * s, oy + y * s )

            sq = rounded( *P( 16, 16 ), *P( 184, 184 ), 26 * s )
            parts = stroke( sq, lw, closed=True )
            if k == 0:            # a folded newspaper
                page = [ P( 50, 46 ), P( 150, 46 ), P( 150, 154 ), P( 50, 154 ) ]
                parts += stroke( page, lw, closed=True )
                parts += stroke( [ P( 150, 70 ), P( 160, 70 ), P( 160, 154 ), P( 150, 154 ) ], lw )
                parts.append( rect( *P( 64, 60 ), *P( 136, 76 ) ) )
                parts.append( rect( *P( 64, 88 ), *P( 94, 118 ) ) )
                for y in ( 92, 104, 116 ):
                    parts += stroke( [ P( 104, y ), P( 136, y ) ], lw * 0.8 )
                for y, x_end in ( ( 130, 136 ), ( 142, 118 ) ):
                    parts += stroke( [ P( 64, y ), P( x_end, y ) ], lw * 0.8 )
            elif k == 1:          # a bottle
                outline = ( [ P( 92, 50 ), P( 92, 62 ) ] + bezier( P( 92, 62 ), P( 92, 76 ), P( 72, 80 ), P( 72, 98 ) )
                            + [ P( 72, 158 ) ] + bezier( P( 72, 158 ), P( 72, 166 ), P( 76, 168 ), P( 84, 168 ) )
                            + [ P( 116, 168 ) ] + bezier( P( 116, 168 ), P( 124, 168 ), P( 128, 166 ), P( 128, 158 ) )
                            + [ P( 128, 98 ) ] + bezier( P( 128, 98 ), P( 128, 80 ), P( 108, 76 ), P( 108, 62 ) )
                            + [ P( 108, 50 ) ] )
                parts += stroke( outline, lw, closed=True )
                parts.append( rounded( *P( 88, 32 ), *P( 112, 48 ), 3 * s ) )
                parts += stroke( [ P( 72, 108 ), P( 128, 108 ) ], lw * 0.8 )
                parts += stroke( [ P( 72, 142 ), P( 128, 142 ) ], lw * 0.8 )
            else:                 # a crisp packet: crimped top and bottom, a round window
                top = [ P( 56 + 8 * j, 44 + ( 6 if j % 2 else 0 ) ) for j in range( 12 ) ]
                bottom = [ P( 144 - 8 * j, 158 + ( 6 if j % 2 else 0 ) ) for j in range( 12 ) ]
                right = bezier( P( 144, 50 ), P( 154, 90 ), P( 154, 120 ), P( 144, 158 ) )
                left = bezier( P( 56, 158 ), P( 46, 120 ), P( 46, 90 ), P( 56, 50 ) )
                parts += stroke( top + right + bottom + left, lw, closed=True )
                parts += stroke( circle( *P( 100, 104 ), 24 * s, 32 ), lw * 0.8, closed=True )
                parts += stroke( [ P( 72, 70 ), P( 128, 70 ) ], lw * 0.8 )
            self.c.fill( parts, WHITE, cover=True, orient=True )

    # --- The menu board
    def menu( self ):
        x0, y0, x1, y1, w, h = self.opaque( "menu", vgrad( 0, 1, ( 34, 36, 39 ), ( 34, 36, 39 ), 0.06, 3 ), 0.8 )
        s = w / 440.0
        frame = rounded( x0 + 14 * s, y0 + 14 * s, x1 - 14 * s, y1 - 14 * s, 4 * s )
        self.c.fill( stroke( frame, 2.5 * s, closed=True ), ( 205, 205, 200 ), 0.8, orient=True )
        items = ( "Zeitschriften", "Getränke", "Snacks", "Süßigkeiten", "Kaffee to go" )
        cap = 26 * s
        y = y0 + 96 * s
        for item in items:
            self.text( item, cap, x0 + 56 * s, y, WHITE )
            self.c.fill( [ rect( x1 - 98 * s, y - cap * 0.42 - 1.5 * s, x1 - 62 * s, y - cap * 0.42 + 1.5 * s ) ], WHITE )
            y += 82 * s
        self.c.fill( [ rect( x0 + 56 * s, y - 30 * s, x0 + 84 * s, y - 27 * s ) ], WHITE )

    # --- The travel poster: a lake under mountains at dusk
    def poster( self ):
        x0, y0, x1, y1, w, h = self.opaque( "poster", vgrad( 0, 1, ( 0, 0, 0 ), ( 0, 0, 0 ) ), 0.35 )
        s = w / 440.0

        def P( x, y ):
            return ( x0 + x * s, y0 + y * s )

        clip = ( x0, y0, x1, y1 )
        horizon = 372
        self.c.fill( [ rect( x0, y0, x1, y0 + horizon * s ) ],
                     vgrad( y0, y0 + horizon * s, ( 20, 52, 64 ), ( 104, 150, 150 ), 0.03, 5 ), clip=clip )
        self.c.fill( [ circle( *P( 304, 150 ), 74 * s, 64 ) ], ( 220, 222, 200 ), 0.10, clip=clip )
        self.c.fill( [ circle( *P( 304, 150 ), 50 * s, 64 ) ], ( 238, 232, 206 ), clip=clip )
        layers = ( ( ( 92, 136, 142 ), 268, ( 0, 300, 70, 248, 130, 286, 196, 224, 262, 280, 318, 240, 380, 290, 440, 258 ) ),
                   ( ( 62, 106, 114 ), 312, ( 0, 318, 56, 278, 120, 330, 170, 290, 236, 336, 300, 300, 352, 330, 440, 296 ) ),
                   ( ( 40, 80, 88 ), 350, ( 0, 352, 90, 330, 150, 352, 240, 340, 330, 356, 440, 336 ) ) )
        for colour, _, ridge in layers:
            pts = [ P( ridge[i], ridge[i + 1] ) for i in range( 0, len( ridge ), 2 ) ]
            self.c.fill( [ pts + [ P( 440, horizon + 2 ), P( 0, horizon + 2 ) ] ], colour, clip=clip )
        # Pines down both shores.
        pines = [ ( 18, 372, 120 ), ( 52, 372, 150 ), ( 84, 376, 110 ), ( 116, 378, 86 ), ( 140, 380, 62 ),
                  ( 330, 380, 70 ), ( 362, 378, 96 ), ( 398, 374, 130 ), ( 428, 372, 104 ) ]
        trees = []
        for cx, base, ht in pines:
            for k in range( 4 ):
                t0 = base - ht * k / 4.2
                half = ht * 0.24 * ( 1 - k / 5.0 )
                trees.append( [ P( cx - half, t0 ), P( cx + half, t0 ), P( cx, t0 - ht * 0.42 ) ] )
            trees.append( rect( *P( cx - 2, base - 6 ), *P( cx + 2, base + 4 ) ) )
        self.c.fill( trees, ( 16, 40, 42 ), clip=clip, orient=True )
        # The lake, the moon's path across it and the shore.
        self.c.fill( [ rect( x0, y0 + horizon * s, x1, y1 ) ],
                     vgrad( y0 + horizon * s, y1, ( 70, 116, 120 ), ( 18, 44, 54 ), 0.03, 7 ), clip=clip )
        for k in range( 22 ):
            y = horizon + 8 + k * 9
            half = 34 - k * 1.1 + 10 * hash01( k, 3 )
            if half > 4:
                self.c.fill( [ rect( *P( 304 - half, y ), *P( 304 + half, y + 2.2 ) ) ], ( 226, 222, 196 ),
                             0.55 - k * 0.02, clip=clip )
        self.c.fill( [ rect( x0, y0 + ( horizon - 1 ) * s, x1, y0 + ( horizon + 3 ) * s ) ], ( 14, 34, 38 ), clip=clip )
        cap = 30 * s
        for k, word in enumerate( ( "Kleine", "Pause", "Große", "Momente" ) ):
            self.text( word, cap, x0 + 40 * s, y0 + ( 454 + k * 44 ) * s, ( 244, 240, 226 ), clip=clip )
        self.c.fill( [ rect( *P( 40, 618 ), *P( 70, 621 ) ) ], ( 244, 240, 226 ), clip=clip )

    # --- Magazine covers
    MAGS = ( ( "REISEN", ( 236, 120, 70 ), ( 120, 40, 90 ), "sunset" ), ( "NATUR", ( 120, 180, 120 ), ( 30, 80, 50 ), "forest" ),
             ( "AUTO", ( 30, 40, 70 ), ( 10, 14, 24 ), "car" ), ( "SPORT", ( 210, 40, 40 ), ( 140, 20, 24 ), "sport" ),
             ( "KOCHEN", ( 246, 236, 214 ), ( 230, 210, 180 ), "food" ), ( "GARTEN", ( 196, 222, 160 ), ( 120, 170, 90 ), "flowers" ),
             ( "TECHNIK", ( 20, 30, 34 ), ( 10, 60, 70 ), "tech" ), ( "STADT", ( 150, 200, 236 ), ( 70, 120, 190 ), "city" ) )

    def magazine( self, k ):
        title, top, bottom, kind = self.MAGS[k]
        name = f"mag_{k}"
        x0, y0, x1, y1, w, h = self.opaque( name, vgrad( 0, 1, ( 0, 0, 0 ), ( 0, 0, 0 ) ), 0.3 )
        clip = ( x0, y0, x1, y1 )
        s = w / 240.0

        def P( x, y ):
            return ( x0 + x * s, y0 + y * s )

        self.c.fill( [ rect( x0, y0, x1, y1 ) ], vgrad( y0, y1, top, bottom, 0.02, k ), clip=clip )
        light = sum( top ) > 500
        ink = INK if light else WHITE
        if kind == "sunset":
            self.c.fill( [ circle( *P( 150, 170 ), 46 * s ) ], ( 255, 214, 120 ), clip=clip )
            for colour, ridge in ( ( ( 150, 60, 90 ), ( 0, 230, 50, 180, 110, 220, 170, 160, 240, 210 ) ),
                                   ( ( 80, 26, 60 ), ( 0, 260, 70, 220, 140, 262, 200, 230, 240, 250 ) ) ):
                pts = [ P( ridge[i], ridge[i + 1] ) for i in range( 0, len( ridge ), 2 ) ]
                self.c.fill( [ pts + [ P( 240, 330 ), P( 0, 330 ) ] ], colour, clip=clip )
        elif kind == "forest":
            self.c.fill( [ [ P( 0, 230 ), P( 80, 190 ), P( 160, 220 ), P( 240, 180 ), P( 240, 330 ), P( 0, 330 ) ] ],
                         ( 70, 130, 80 ), clip=clip )
            trees = []
            for j, ( cx, base, ht ) in enumerate( ( ( 40, 300, 120 ), ( 90, 310, 150 ), ( 150, 300, 110 ), ( 200, 312, 140 ) ) ):
                for m in range( 4 ):
                    t0 = base - ht * m / 4.4
                    half = ht * 0.26 * ( 1 - m / 5 )
                    trees.append( [ P( cx - half, t0 ), P( cx + half, t0 ), P( cx, t0 - ht * 0.4 ) ] )
            self.c.fill( trees, ( 22, 60, 36 ), clip=clip, orient=True )
        elif kind == "car":
            body = rounded( *P( 30, 200 ), *P( 210, 246 ), 14 * s )
            roof = [ P( 70, 202 ), P( 96, 168 ), P( 160, 168 ), P( 186, 202 ) ]
            self.c.fill( [ body, roof ], ( 220, 60, 50 ), clip=clip, orient=True )
            self.c.fill( [ [ P( 80, 200 ), P( 100, 176 ), P( 126, 176 ), P( 126, 200 ) ],
                           [ P( 134, 200 ), P( 134, 176 ), P( 156, 176 ), P( 174, 200 ) ] ], ( 40, 60, 90 ), clip=clip,
                         orient=True )
            for cx in ( 74, 168 ):
                self.c.fill( [ circle( *P( cx, 248 ), 20 * s ) ], ( 18, 18, 20 ), clip=clip )
                self.c.fill( [ circle( *P( cx, 248 ), 9 * s ) ], ( 170, 170, 176 ), clip=clip )
            for j in range( 4 ):
                self.c.fill( [ rect( *P( 4, 206 + 10 * j ), *P( 26 - 4 * j, 208 + 10 * j ) ) ], ( 200, 210, 230 ), 0.7,
                             clip=clip )
        elif kind == "sport":
            for j in range( 5 ):
                self.c.fill( [ [ P( -40 + 60 * j, 330 ), P( 10 + 60 * j, 330 ), P( 120 + 60 * j, 90 ), P( 70 + 60 * j, 90 ) ] ],
                             ( 255, 255, 255 ), 0.12, clip=clip )
            self.c.fill( [ circle( *P( 128, 210 ), 56 * s, 60 ) ], ( 245, 245, 240 ), clip=clip )
            self.c.fill( stroke( circle( *P( 128, 210 ), 56 * s, 60 ), 2.4 * s, closed=True ), ( 30, 30, 30 ), clip=clip,
                         orient=True )
            pent = [ P( 128 + 20 * math.cos( math.radians( 90 + 72 * j ) ), 210 - 20 * math.sin( math.radians( 90 + 72 * j ) ) )
                     for j in range( 5 ) ]
            self.c.fill( [ pent ], ( 30, 30, 30 ), clip=clip, orient=True )
        elif kind == "food":
            self.c.fill( [ circle( *P( 120, 214 ), 74 * s, 64 ) ], ( 255, 255, 255 ), clip=clip )
            self.c.fill( [ circle( *P( 120, 214 ), 58 * s, 64 ) ], ( 236, 232, 222 ), clip=clip )
            for cx, cy, r, col in ( ( 100, 200, 16, ( 220, 60, 40 ) ), ( 134, 196, 14, ( 120, 170, 60 ) ),
                                    ( 118, 226, 18, ( 240, 180, 60 ) ), ( 146, 228, 12, ( 200, 60, 40 ) ),
                                    ( 92, 232, 11, ( 90, 150, 50 ) ) ):
                self.c.fill( [ circle( *P( cx, cy ), r * s ) ], col, clip=clip )
            self.c.fill( [ rect( *P( 214, 150 ), *P( 220, 280 ) ) ], ( 180, 180, 186 ), clip=clip )
        elif kind == "flowers":
            for cx, cy, col in ( ( 60, 220, ( 230, 80, 120 ) ), ( 130, 190, ( 250, 200, 60 ) ), ( 190, 236, ( 200, 90, 200 ) ),
                                 ( 100, 270, ( 250, 140, 60 ) ) ):
                self.c.fill( [ rect( *P( cx - 2, cy ), *P( cx + 2, 330 ) ) ], ( 60, 110, 50 ), clip=clip )
                petals = [ ellipse( *P( cx + 14 * math.cos( t ), cy + 14 * math.sin( t ) ), 12 * s, 7 * s, t )
                           for t in ( 2 * math.pi * j / 6 for j in range( 6 ) ) ]
                self.c.fill( petals, col, clip=clip, orient=True )
                self.c.fill( [ circle( *P( cx, cy ), 7 * s ) ], ( 250, 230, 120 ), clip=clip )
        elif kind == "tech":
            lines = []
            for j in range( 7 ):
                y = 120 + 30 * j
                lines += stroke( [ P( 0, y ), P( 60 + 20 * ( j % 3 ), y ), P( 80 + 20 * ( j % 3 ), y + 20 ), P( 240, y + 20 ) ],
                                 2 * s, caps=False )
            self.c.fill( lines, ( 60, 200, 210 ), 0.5, clip=clip, orient=True )
            self.c.fill( [ rounded( *P( 84, 130 ), *P( 156, 280 ), 12 * s ) ], ( 12, 14, 16 ), clip=clip )
            self.c.fill( [ rounded( *P( 90, 140 ), *P( 150, 270 ), 6 * s ) ], vgrad( y0 + 140 * s, y0 + 270 * s,
                                                                                     ( 60, 190, 220 ), ( 40, 70, 180 ) ),
                         clip=clip )
        elif kind == "city":
            towers = []
            for j, ( a, b, ht ) in enumerate( ( ( 0, 34, 120 ), ( 30, 70, 170 ), ( 66, 96, 100 ), ( 92, 130, 200 ), ( 126, 160, 140 ),
                                                ( 156, 196, 180 ), ( 192, 240, 110 ) ) ):
                towers.append( rect( *P( a, 330 - ht ), *P( b, 330 ) ) )
            self.c.fill( towers, ( 40, 70, 120 ), clip=clip, orient=True )
            for j in range( 60 ):
                xw = 4 + 230 * hash01( j, 1, k )
                yw = 330 - 180 * hash01( j, 2, k )
                self.c.fill( [ rect( *P( xw, yw ), *P( xw + 4, yw + 5 ) ) ], ( 250, 220, 140 ), 0.8, clip=clip )
        # The masthead, a rule and the cover lines.
        cap = self.fit_cap( title, self.bold, 40 * s, 210 * s, 0.04 )
        self.text( title, cap, x0 + 15 * s, y0 + 20 * s + cap, ink, self.bold, 0.04, clip=clip )
        self.c.fill( [ rect( *P( 15, 72 ), *P( 225, 74 ) ) ], ink, clip=clip )
        lines = { "REISEN": ( "Die schönsten", "Ziele im Herbst" ), "NATUR": ( "Wald & Wild", "Spezial" ),
                  "AUTO": ( "Neu im Test", "Kombis" ), "SPORT": ( "Saisonstart", "Alle Teams" ),
                  "KOCHEN": ( "Schnelle Küche", "50 Rezepte" ), "GARTEN": ( "Herbstblumen", "pflanzen" ),
                  "TECHNIK": ( "Smartphones", "im Vergleich" ), "STADT": ( "Wochenende", "in der Stadt" ) }[title]
        band = ( 255, 255, 255 ) if not light else INK
        for j, line in enumerate( lines ):
            self.text( line, 13 * s, x0 + 15 * s, y0 + ( 96 + 18 * j ) * s, band, self.bold if j == 0 else self.regular,
                       clip=clip )
        self.c.fill( [ circle( *P( 204, 118 ), 22 * s ) ], ( 250, 210, 40 ), clip=clip )
        self.text( "NEU", 11 * s, x0 + 204 * s, y0 + 123 * s, INK, self.bold, align="centre", clip=clip )
        self.c.fill( [ rect( *P( 186, 296 ), *P( 228, 322 ) ) ], ( 250, 250, 248 ), clip=clip )
        bars = []
        for j in range( 16 ):
            if hash01( j, k, 9 ) > 0.4:
                bars.append( rect( *P( 189 + 2.2 * j, 299 ), *P( 190.2 + 2.2 * j, 316 ) ) )
        self.c.fill( bars, ( 20, 20, 20 ), clip=clip )

    # --- Crisp packets
    CHIPS = ( ( "Paprika", ( 206, 44, 32 ), ( 252, 196, 40 ) ), ( "Salz", ( 32, 84, 176 ), ( 250, 250, 250 ) ),
              ( "Kräuter", ( 40, 128, 64 ), ( 240, 236, 150 ) ), ( "Chili", ( 54, 26, 24 ), ( 240, 90, 30 ) ),
              ( "Brezeln", ( 150, 88, 40 ), ( 250, 224, 170 ) ) )

    def chips( self, k ):
        flavour, body, accent = self.CHIPS[k]
        name = f"chips_{k}"
        x0, y0, x1, y1, w, h = self.opaque( name, body, 0.22 )
        clip = ( x0, y0, x1, y1 )
        s = w / 260.0

        def P( x, y ):
            return ( x0 + x * s, y0 + y * s )

        def foil( x, y ):           # the packet's sheen: a highlight a quarter across, darker towards the right
            u = ( x - x0 ) / w
            t = 1.0 + 0.35 * math.exp( -( ( u - 0.26 ) / 0.08 ) ** 2 ) - 0.22 * max( 0.0, u - 0.6 ) / 0.4
            return tuple( min( 255.0, c * t ) for c in body )

        self.c.fill( [ rect( x0, y0, x1, y1 ) ], foil, clip=clip )
        dark = tuple( c * 0.62 for c in body )
        for ya, yb in ( ( 0, 30 ), ( 310, 340 ) ):
            self.c.fill( [ rect( *P( 0, ya ), *P( 260, yb ) ) ], dark, clip=clip )
            self.c.fill( [ rect( *P( 6 * j, ya ), *P( 6 * j + 2.5, yb ) ) for j in range( 44 ) ], ( 0, 0, 0 ), 0.18, clip=clip )
        cap = self.fit_cap( "Chips" if k < 4 else "Brezeln", self.bold, 54 * s, 230 * s )
        word = "Chips" if k < 4 else "Snack"
        self.text( word, cap, x0 + 132 * s, y0 + 112 * s, ( 0, 0, 0 ), self.bold, align="centre", alpha=0.35, clip=clip )
        self.text( word, cap, x0 + 129 * s, y0 + 109 * s, ( 255, 255, 255 ), self.bold, align="centre", clip=clip )
        self.c.fill( [ rounded( *P( 40, 128 ), *P( 220, 166 ), 19 * s ) ], accent, clip=clip )
        cap = self.fit_cap( flavour, self.bold, 22 * s, 160 * s )
        self.text( flavour, cap, x0 + 130 * s, y0 + ( 147 + 11 ) * s, body if sum( accent ) > 450 else ( 255, 255, 255 ),
                   self.bold, align="centre", clip=clip )
        if k < 4:
            for j, ( cx, cy, rx, ry, t ) in enumerate( ( ( 84, 240, 40, 30, 0.3 ), ( 140, 252, 44, 32, -0.4 ), ( 190, 236, 36, 28, 0.6 ),
                                                         ( 112, 276, 38, 26, -0.2 ), ( 166, 284, 40, 27, 0.2 ) ) ):
                c0, c1 = ( 252, 214, 120 ), ( 214, 150, 50 )
                cyp = y0 + cy * s

                def crisp( x, y, cyp=cyp, ry=ry, c0=c0, c1=c1 ):
                    return mix( c0, c1, min( 1.0, max( 0.0, ( y - cyp + ry * s ) / ( 2 * ry * s ) ) ) )

                self.c.fill( [ ellipse( *P( cx + 3, cy + 4 ), rx * s, ry * s, t ) ], ( 0, 0, 0 ), 0.25, clip=clip )
                self.c.fill( [ ellipse( *P( cx, cy ), rx * s, ry * s, t ) ], crisp, clip=clip )
                self.c.fill( stroke( [ P( cx - rx * 0.4, cy - 4 ), P( cx + rx * 0.3, cy - 8 ) ], 3 * s ), ( 255, 240, 190 ),
                             0.6, clip=clip, orient=True )
            garnish = { 0: ( ( 220, 40, 30 ), "dots" ), 1: ( ( 255, 255, 255 ), "dots" ), 2: ( ( 70, 150, 60 ), "leaves" ),
                        3: ( ( 230, 40, 20 ), "chili" ) }[k]
            if garnish[1] == "dots":
                self.c.fill( [ circle( *P( 70 + 130 * hash01( j, k ), 220 + 80 * hash01( j, k, 4 ) ), 3 * s, 10 )
                               for j in range( 26 ) ], garnish[0], clip=clip )
            elif garnish[1] == "leaves":
                self.c.fill( [ ellipse( *P( 60 + 150 * hash01( j, k ), 214 + 90 * hash01( j, k, 4 ) ), 12 * s, 5 * s,
                                        6.28 * hash01( j, 7 ) ) for j in range( 9 ) ], garnish[0], clip=clip, orient=True )
            else:
                pod = bezier( P( 200, 196 ), P( 236, 210 ), P( 238, 250 ), P( 214, 286 ) )
                self.c.fill( stroke( pod, 16 * s ), garnish[0], clip=clip, orient=True )
                self.c.fill( stroke( [ P( 196, 196 ), P( 186, 186 ) ], 6 * s ), ( 60, 130, 50 ), clip=clip, orient=True )
        else:
            for cx, cy in ( ( 92, 246 ), ( 172, 262 ) ):
                loop = ( bezier( P( cx - 46, cy + 30 ), P( cx - 70, cy - 20 ), P( cx - 10, cy - 50 ), P( cx, cy - 6 ) )
                         + bezier( P( cx, cy - 6 ), P( cx + 10, cy - 50 ), P( cx + 70, cy - 20 ), P( cx + 46, cy + 30 ) )[1:] )
                cross = [ P( cx - 30, cy + 34 ), P( cx + 12, cy - 2 ) ], [ P( cx + 30, cy + 34 ), P( cx - 12, cy - 2 ) ]
                for path in ( loop, *cross ):
                    self.c.fill( stroke( path, 15 * s ), ( 160, 84, 30 ), clip=clip, orient=True )
                for j in range( 9 ):
                    px, py = loop[j * 3 % len( loop )]
                    self.c.fill( [ rect( px - 2 * s, py - 1 * s, px + 2 * s, py + 1.5 * s ) ], ( 250, 250, 250 ), clip=clip )

    # --- Bottle labels
    LABELS = ( ( "Wasser", ( 40, 120, 200 ), ( 255, 255, 255 ) ), ( "Apfel", ( 60, 150, 60 ), ( 255, 255, 255 ) ),
               ( "Orange", ( 240, 130, 20 ), ( 255, 255, 255 ) ), ( "Cola", ( 196, 24, 30 ), ( 255, 255, 255 ) ),
               ( "Zitrone", ( 246, 214, 40 ), ( 40, 70, 30 ) ), ( "Eistee", ( 180, 100, 40 ), ( 255, 244, 220 ) ) )

    def label( self, k ):
        word, colour, ink = self.LABELS[k]
        name = f"label_{k}"
        x0, y0, x1, y1, w, h = self.opaque( name, colour, 0.3 )
        clip = ( x0, y0, x1, y1 )
        s = w / 360.0
        self.c.fill( [ rect( x0, y0, x1, y0 + 10 * s ) ], ink, 0.85, clip=clip )
        self.c.fill( [ rect( x0, y1 - 10 * s, x1, y1 ) ], ink, 0.85, clip=clip )
        wave = [ ( x0 + x * s, y0 + ( 84 + 10 * math.sin( x / 30.0 ) ) * s ) for x in range( 0, 361, 6 ) ]
        self.c.fill( [ wave + [ ( x1, y1 - 10 * s ), ( x0, y1 - 10 * s ) ] ], ( 255, 255, 255 ), 0.22, clip=clip )
        # The label wraps once round the bottle, so the name keeps to the third that faces the shelf's front.
        cap = self.fit_cap( word, self.bold, 34 * s, 108 * s )
        self.text( word, cap, x0 + w / 2, y0 + 56 * s + cap / 2, ink, self.bold, align="centre", clip=clip )
        for y in ( 56 - cap / s / 2 - 12, 56 + cap / s / 2 + 9 ):
            self.c.fill( [ rect( x0 + w / 2 - 54 * s, y0 + y * s, x0 + w / 2 + 54 * s, y0 + ( y + 2.5 ) * s ) ], ink, 0.85,
                         clip=clip )
        for cx in ( w / 2 - 110 * s, w / 2 + 110 * s ):
            self.c.fill( [ circle( x0 + cx, y0 + 58 * s, 9 * s ) ], ink, 0.9, clip=clip )

    # --- Sweet bars
    CANDY = ( ( "Schoko", ( 90, 46, 26 ), ( 240, 200, 110 ) ), ( "Nuss", ( 30, 70, 150 ), ( 255, 255, 255 ) ),
              ( "Karamell", ( 220, 120, 30 ), ( 255, 250, 235 ) ), ( "Minze", ( 30, 140, 110 ), ( 255, 255, 255 ) ) )

    def candy( self, k ):
        word, colour, ink = self.CANDY[k]
        name = f"candy_{k}"
        x0, y0, x1, y1, w, h = self.opaque( name, colour, 0.25 )
        clip = ( x0, y0, x1, y1 )
        s = w / 320.0
        self.c.fill( [ rect( x0, y0 + h * 0.42, x1, y0 + h * 0.58 ) ], ( 255, 255, 255 ), 0.12, clip=clip )
        for xa in ( x0, x1 - 22 * s ):
            self.c.fill( [ rect( xa, y0, xa + 22 * s, y1 ) ], tuple( c * 0.7 for c in colour ), clip=clip )
            self.c.fill( [ rect( xa + 4 * j * s, y0, xa + ( 4 * j + 1.6 ) * s, y1 ) for j in range( 6 ) ], ( 0, 0, 0 ), 0.2,
                         clip=clip )
        cap = self.fit_cap( word, self.bold, 34 * s, 230 * s )
        self.text( word, cap, x0 + w / 2, y0 + h / 2 + cap / 2, ink, self.bold, align="centre", clip=clip )

    # --- The till's screen
    def pos_screen( self ):
        x0, y0, x1, y1, w, h = self.opaque( "pos_screen", ( 22, 28, 40 ), 0.12 )
        s = w / 240.0
        self.c.fill( [ rect( x0, y0, x1, y0 + 26 * s ) ], ( 40, 60, 100 ) )
        cols = ( ( 70, 130, 90 ), ( 90, 110, 160 ), ( 170, 120, 60 ), ( 120, 80, 140 ), ( 80, 140, 150 ), ( 160, 70, 70 ) )
        for j in range( 6 ):
            cx, cy = j % 3, j // 3
            self.c.fill( [ rounded( x0 + ( 10 + 58 * cx ) * s, y0 + ( 38 + 46 * cy ) * s, x0 + ( 62 + 58 * cx ) * s,
                                    y0 + ( 78 + 46 * cy ) * s, 5 * s ) ], cols[j] )
        self.c.fill( [ rect( x0 + 186 * s, y0 + 38 * s, x1 - 10 * s, y1 - 12 * s ) ], ( 236, 236, 230 ) )
        for j in range( 6 ):
            self.c.fill( [ rect( x0 + 192 * s, y0 + ( 46 + 14 * j ) * s, x1 - 16 * s, y0 + ( 49 + 14 * j ) * s ) ], ( 90, 90, 96 ) )

    def draw( self ):
        self.lettering()
        self.menu()
        self.poster()
        for k in range( len( self.MAGS ) ):
            self.magazine( k )
        for k in range( len( self.CHIPS ) ):
            self.chips( k )
        for k in range( len( self.LABELS ) ):
            self.label( k )
        for k in range( len( self.CANDY ) ):
            self.candy( k )
        self.pos_screen()


def vmat():
    return "\n".join( [
        "// Tools/railhead_kiosk_art.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"',
        '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{RESOURCE_DIR}/rw_kiosk_trans.png"',
        '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"', '    F_SELF_ILLUM "1"',
        f'    TextureSelfIllumMask "{RESOURCE_DIR}/rw_kiosk_illum.png"', f'    g_flSelfIllumBrightness "{ILLUM:.2f}"',
        '    g_flSelfIllumAlbedoFactor "1.0"', '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"',
        '    g_flRoughnessScaleFactor "1"',
        '    g_flMetalness "0.00"', f'    TextureColor "{RESOURCE_DIR}/rw_kiosk_color.png"',
        '    TextureNormal "materials/default/default_normal.tga"', f'    TextureRoughness "{RESOURCE_DIR}/rw_kiosk_rough.png"',
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"', '    g_vColorTint "[1.0 1.0 1.0 1.0]"',
        '    g_flModelTintAmount "1.0"', "}" ] ) + "\n"


PICTURES = ( "color", "trans", "rough", "illum" )


def missing( out=OUT_DIR ):
    """ Whether any of the atlas's pictures isn't there (railhead_map draws them then). """
    return any( not ( Path( out ) / f"rw_kiosk_{k}.png" ).exists() for k in PICTURES )


def write( out=OUT_DIR ):
    out = Path( out )
    out.mkdir( parents=True, exist_ok=True )
    canvas = Canvas( W, H )
    Art( canvas ).draw()
    canvas.save( out, "rw_kiosk" )
    ( out / "rw_kiosk.vmat" ).write_text( vmat(), encoding="utf-8", newline="\n" )
    print( f"wrote {out / 'rw_kiosk'}_color/trans/rough/illum.png and rw_kiosk.vmat: {len( RECTS )} entries" )


def main():
    ap = argparse.ArgumentParser( description=__doc__.split( "\n\n" )[0] )
    ap.add_argument( "--out", type=Path, default=OUT_DIR )
    write( ap.parse_args().out )


if __name__ == "__main__":
    main()
