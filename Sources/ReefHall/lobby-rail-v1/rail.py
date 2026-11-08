"""The lobby balcony's glass railing as standalone models (Sources/ReefHall/lobby-rail-v1, 2026-11-06).

The old railing (Tools/reefhall_map.py railing(), 504 triangles for the north run and its south mirror) was square gunmetal
posts every 60 in, one 8-sided steel tube and flat glass quads. The new one is a frameless-glass balustrade:

  * a stainless base shoe 3.4 in wide with a chamfered top and a dark gasket slot the glass stands in;
  * 12 mm (0.5 in) toughened glass panels with edge faces, 57.6 in wide, one per bay;
  * round stainless posts every 60 in with a base collar, a flared top and a cup under the handrail;
  * two stainless glass clamps per post and side, each with a fixing screw;
  * a round 2 in stainless handrail in 120 in lengths with a splice ring at each joint, flat-capped at the run's ends.

Everything is built in sections of two bays (120 in) so a section's level of detail follows its own distance: a 21 m run drawn
as one model would switch as a whole, from its middle. Two models: `lobby_rail_section` (posts at its start and middle) and
`lobby_rail_section_end` (the same, plus the run's last post). The south run is the north run's mirror image across n = 0 and
the section is symmetric across its own length, so the same models serve both: only the position differs.

Existing Reef Hall materials only (rh_steel, rh_glass, rh_black): no new textures, no new materials.

Run:  python rail.py [--no-write]       writes Assets/models/props/reefhall/lobby_rail_v1/ (OBJ per LOD and the vmdl files)
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
import map_kit as K          # noqa: E402
import riverdale_parts as P  # noqa: E402
import reefhall_map as R     # noqa: E402

HERE = Path( __file__ ).resolve().parent
MODEL_DIR = ROOT / "Assets/models/props/reefhall/lobby_rail_v1"
MODEL_RES = "models/props/reefhall/lobby_rail_v1"

BAY = 60.0
HALF = BAY                      # a section is two bays long: y from -60 to 60 about its centre
RAIL_Z = 42.0                   # the old handrail's centre line
RAIL_R = 1.0                    # 2 in tube (the old one was 3.2 in)
GLASS_T = 0.5
GLASS_GAP = 1.2                 # from the post's centre to the glass edge
GLASS_Z0, GLASS_Z1 = 2.6, 38.0  # the glass stands in the shoe's slot (floor at 2.6) and ends under the rail
SHOE_Z = 3.3
LOD_THRESHOLDS = { 0: 0.0, 1: 20.0, 2: 60.0 }   # about 19 in per unit: 380 in (9.7 m) and 1140 in (29 m) from a section's centre
LODS = {
    0: dict( post_sides=10, rail_sides=12, clamps=True, screws=True, ring=True, shoe="full" ),
    1: dict( post_sides=6, rail_sides=8, clamps=True, screws=False, ring=True, shoe="full" ),
    2: dict( post_sides=6, rail_sides=6, clamps=False, screws=False, ring=False, shoe="simple" ),
}

STEEL, GLASS, BLACK = "rh_steel", "rh_glass", "rh_black"
UP = np.array( ( 0.0, 0.0, 1.0 ) )


def v3( x, y, z ):
    return np.array( ( x, y, z ), float )


def turn_to_plan( model ):
    """ A quarter turn about the vertical axis, ( x, y, z ) -> ( -y, x, z ): the drawing's y (along the run, west) becomes
    plan -e and its x (across) becomes plan n, so after map_kit.to_world ( n, -e, z ) the model's world x is across the run
    and its world y is along it. A rotation (determinant +1): winding and normals stay outward. """
    def turn( v ):
        return np.array( ( -v[1], v[0], v[2] ), float )
    for paint, items in list( model.polygons.items() ):
        model.polygons[paint] = [ ( [ turn( p ) for p in points ], turn( normal ) ) for points, normal in items ]
    model.polygon_normals = { key: [ turn( n ) for n in normals ] for key, normals in model.polygon_normals.items() }


class Section:
    def __init__( self, lod, end_post=False ):
        self.lod, self.cfg, self.end_post = lod, LODS[lod], end_post
        self.m = K.Model()

    def card( self, paint, pts, towards ):
        P.card( self.m, paint, pts, np.asarray( towards, float ) )

    # ----- the base shoe ------------------------------------------------------------------------------------------
    def shoe( self ):
        if self.cfg["shoe"] == "full":
            prof = [ ( -1.7, 0.0 ), ( -1.7, 2.7 ), ( -1.35, SHOE_Z ), ( -0.38, SHOE_Z ), ( -0.38, GLASS_Z0 ),
                     ( 0.38, GLASS_Z0 ), ( 0.38, SHOE_Z ), ( 1.35, SHOE_Z ), ( 1.7, 2.7 ), ( 1.7, 0.0 ) ]
            kinds = [ ( STEEL, ( -1, 0 ) ), ( STEEL, ( -0.7, 0.7 ) ), ( STEEL, ( 0, 1 ) ), ( BLACK, ( 1, 0 ) ), ( BLACK, ( 0, 1 ) ),
                      ( BLACK, ( -1, 0 ) ), ( STEEL, ( 0, 1 ) ), ( STEEL, ( 0.7, 0.7 ) ), ( STEEL, ( 1, 0 ) ) ]
        else:
            prof = [ ( -1.7, 0.0 ), ( -1.7, SHOE_Z ), ( 1.7, SHOE_Z ), ( 1.7, 0.0 ) ]
            kinds = [ ( STEEL, ( -1, 0 ) ), ( STEEL, ( 0, 1 ) ), ( STEEL, ( 1, 0 ) ) ]
        y0, y1 = -HALF, HALF
        for ( a, b ), ( paint, n ) in zip( zip( prof[:-1], prof[1:] ), kinds ):
            self.card( paint, [ v3( a[0], y0, a[1] ), v3( a[0], y1, a[1] ), v3( b[0], y1, b[1] ), v3( b[0], y0, b[1] ) ],
                       v3( n[0], 0.0, n[1] ) )
        # the ends: three convex pieces round the slot (the neighbouring section hides them; the run's own ends show them)
        if self.cfg["shoe"] == "full":
            blocks = [ [ prof[0], prof[1], prof[2], prof[3], ( -0.38, 0.0 ) ], [ ( -0.38, 0.0 ), prof[4], prof[5], ( 0.38, 0.0 ) ],
                       [ ( 0.38, 0.0 ), prof[6], prof[7], prof[8], prof[9] ] ]
        else:
            blocks = [ prof ]
        for y, s in ( ( y0, -1.0 ), ( y1, 1.0 ) ):
            for blk in blocks:
                pts = [ v3( x, y, z ) for x, z in blk ]
                self.card( STEEL, pts, v3( 0.0, s, 0.0 ) )

    # ----- the glass ----------------------------------------------------------------------------------------------
    def glass( self ):
        t = GLASS_T / 2
        z0, z1 = GLASS_Z0, GLASS_Z1
        for lo in ( -HALF, 0.0 ):
            a, b = lo + GLASS_GAP, lo + BAY - GLASS_GAP
            for s in ( 1.0, -1.0 ):
                self.card( GLASS, [ v3( s * t, a, z0 ), v3( s * t, b, z0 ), v3( s * t, b, z1 ), v3( s * t, a, z1 ) ] if s > 0 else
                           [ v3( s * t, b, z0 ), v3( s * t, a, z0 ), v3( s * t, a, z1 ), v3( s * t, b, z1 ) ], v3( s, 0.0, 0.0 ) )
            self.card( GLASS, [ v3( -t, a, z1 ), v3( t, a, z1 ), v3( t, b, z1 ), v3( -t, b, z1 ) ], UP )
            for y, s in ( ( a, -1.0 ), ( b, 1.0 ) ):
                self.card( GLASS, [ v3( -t, y, z0 ), v3( t, y, z0 ), v3( t, y, z1 ), v3( -t, y, z1 ) ], v3( 0.0, s, 0.0 ) )

    # ----- posts, clamps ------------------------------------------------------------------------------------------
    def posts( self ):
        ys = [ -HALF, 0.0 ] + ( [ HALF ] if self.end_post else [] )
        sides = self.cfg["post_sides"]
        prof = [ ( 1.5, SHOE_Z ), ( 1.5, 3.8 ), ( 0.95, 4.1 ), ( 0.9, 4.3 ), ( 0.9, 39.7 ), ( 1.2, 40.1 ), ( 1.2, 41.2 ) ]
        if self.lod == 2:
            prof = [ ( 0.9, SHOE_Z ), ( 0.9, 40.6 ), ( 1.2, 41.0 ), ( 1.2, 41.2 ) ]
        for y in ys:
            P.lathe( self.m, ( 0.0, y ), prof, STEEL, sides=sides, cap=STEEL )
        if not self.cfg["clamps"]:
            return
        for y in ys:
            lo, hi = -2.0, 2.0              # a clamp plate spans both glass edges at a joint
            if self.end_post and y >= HALF - 0.1:
                lo, hi = -2.0, 0.9          # the run's last post: its panel is on one side only
            for s in ( 1.0, -1.0 ):
                for z0 in ( 11.0, 29.0 ):
                    x0, x1 = s * ( GLASS_T / 2 ), s * ( GLASS_T / 2 + 0.3 )
                    ya, yb, za, zb = y + lo, y + hi, z0, z0 + 3.6
                    self.card( STEEL, [ v3( x1, ya, za ), v3( x1, yb, za ), v3( x1, yb, zb ), v3( x1, ya, zb ) ] if s > 0 else
                               [ v3( x1, yb, za ), v3( x1, ya, za ), v3( x1, ya, zb ), v3( x1, yb, zb ) ], v3( s, 0.0, 0.0 ) )
                    self.card( STEEL, [ v3( x0, ya, zb ), v3( x1, ya, zb ), v3( x1, yb, zb ), v3( x0, yb, zb ) ], UP )
                    self.card( STEEL, [ v3( x0, ya, za ), v3( x1, ya, za ), v3( x1, yb, za ), v3( x0, yb, za ) ], -UP )
                    for yy, ss in ( ( ya, -1.0 ), ( yb, 1.0 ) ):
                        self.card( STEEL, [ v3( x0, yy, za ), v3( x1, yy, za ), v3( x1, yy, zb ), v3( x0, yy, zb ) ], v3( 0.0, ss, 0.0 ) )
                    if self.cfg["screws"]:
                        yy = ( ya + yb ) / 2      # one cap-head screw on each plate, in the plate's middle
                        P.lathe_axis( self.m, ( x1, yy, z0 + 1.8 ), ( s, 0.0, 0.0 ),
                                      [ ( 0.34, 0.0 ), ( 0.34, 0.12 ) ], STEEL, sides=6, cap=STEEL )

    # ----- the handrail -------------------------------------------------------------------------------------------
    def rail( self ):
        sides = self.cfg["rail_sides"]
        P.lathe_axis( self.m, ( 0.0, -HALF, RAIL_Z ), ( 0.0, 1.0, 0.0 ), [ ( RAIL_R, 0.0 ), ( RAIL_R, 2 * HALF ) ], STEEL, sides=sides )
        # flat caps on both ends: they show only at the run's ends (everywhere else the neighbouring section hides them)
        for y, s in ( ( -HALF, -1.0 ), ( HALF, 1.0 ) ):
            ring = [ v3( RAIL_R * math.cos( 2 * math.pi * k / sides ), y, RAIL_Z + RAIL_R * math.sin( 2 * math.pi * k / sides ) ) for k in range( sides ) ]
            self.card( STEEL, ring if s > 0 else ring[::-1], v3( 0.0, s, 0.0 ) )
        if self.cfg["ring"]:
            # the splice ring at the section's start
            P.lathe_axis( self.m, ( 0.0, -HALF, RAIL_Z ), ( 0.0, 1.0, 0.0 ),
                          [ ( RAIL_R, -0.5 ), ( RAIL_R + 0.16, -0.34 ), ( RAIL_R + 0.16, 0.34 ), ( RAIL_R, 0.5 ) ], STEEL, sides=sides )

    def build( self, turn=True ):
        """ The section is drawn with x across the rail and y along it (+y towards the west end of the run). turn=True
        then turns the finished model a quarter turn into the generator's plan coordinates ( e, n, z ), where the north
        run lies along e: map_kit.write_obj turns plan into world as ( n, -e, z ), which puts the section's x across the
        run on world x and its y along the run on world y (the first install skipped this and the sections stood across
        the balcony). turn=False keeps the drawing frame, for preview.py. """
        self.shoe()
        self.glass()
        self.posts()
        self.rail()
        m = self.m
        if turn:
            turn_to_plan( m )
        R.configure( m )
        return m


# ---------------------------------------------------------------------------------------------------------------------

def weld_obj( path ):
    """ K.write_obj gives every polygon its own vertex records; the lobby's OBJ (the BEFORE) shares them. Merge identical
    position, UV and normal records so the two count the same way. """
    lines = Path( path ).read_text().split( "\n" )
    tables = { "v": {}, "vt": {}, "vn": {} }
    keep = { "v": [], "vt": [], "vn": [] }
    remap = { "v": {}, "vt": {}, "vn": {} }
    counts = { "v": 0, "vt": 0, "vn": 0 }
    heads, body = [], []
    for line in lines:
        tag = line.split( " ", 1 )[0]
        if tag in tables:
            counts[tag] += 1
            if line not in tables[tag]:
                tables[tag][line] = len( tables[tag] ) + 1
                keep[tag].append( line )
            remap[tag][counts[tag]] = tables[tag][line]
        elif tag == "f":
            body.append( ( "f", line ) )
        elif tag == "usemtl":
            body.append( ( "m", line ) )
        elif line and tag in ( "#", "mtllib", "o" ):
            heads.append( line )
    out = list( heads ) + keep["v"] + keep["vt"] + keep["vn"]
    for kind, line in body:
        if kind == "m":
            out.append( line )
            continue
        toks = []
        for tok in line.split()[1:]:
            a, b, c = ( int( x ) for x in tok.split( "/" ) )
            toks.append( f"{remap['v'][a]}/{remap['vt'][b]}/{remap['vn'][c]}" )
        out.append( "f " + " ".join( toks ) )
    Path( path ).write_bytes( ( "\n".join( out ) + "\n" ).encode() )


def write_vmdl( path, files, paints, model ):
    """ A model with one render mesh per LOD, and no physics (the lobby's own collision boxes stay). """
    remaps = ",\n".join( f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{model.material_overrides[p]}" }}' for p in sorted( paints ) )
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{MODEL_RES}/{f}" import_translation = [ 0.0, 0.0, 0.0 ] '
        'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] } }'
        for i, f in enumerate( files ) )
    groups = ",\n".join( f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {LOD_THRESHOLDS[i]:.1f} meshes = [ "lod{i}" ] }}'
                         for i in range( len( files ) ) )
    text = ( "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
             "// Generated by Sources/ReefHall/lobby-rail-v1/rail.py\n"
             "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
             "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n"
             "\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n"
             + remaps + "\n\t\t\t\t\t\t]\n\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n"
             "\t\t\t\t]\n\t\t\t},\n"
             "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\n\t\t\t\t]\n\t\t\t},\n"
             "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + groups + "\n\t\t\t\t]\n\t\t\t},\n"
             "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n" )
    K.write_text( path, text )


def tri_count( model ):
    return sum( len( p ) - 2 for polys in model.polygons.values() for p, _ in polys )


def build_all( write=True ):
    stats = {}
    for name, end in ( ( "lobby_rail_section", False ), ( "lobby_rail_section_end", True ) ):
        files, paints, first = [], set(), None
        stats[name] = {}
        for lod in ( 0, 1, 2 ):
            model = Section( lod, end ).build()
            first = first or model
            paints |= set( model.polygons )
            obj = f"{name}_lod{lod}"
            if write:
                MODEL_DIR.mkdir( parents=True, exist_ok=True )
                tris = K.write_obj( MODEL_DIR / f"{obj}.obj", model, obj )
                weld_obj( MODEL_DIR / f"{obj}.obj" )
            else:
                tris = tri_count( model )
            files.append( f"{obj}.obj" )
            stats[name][lod] = tris
        if write:
            write_vmdl( MODEL_DIR / f"{name}.vmdl", files, paints, first )
    return stats


if __name__ == "__main__":
    print( build_all( write="--no-write" not in sys.argv ) )
