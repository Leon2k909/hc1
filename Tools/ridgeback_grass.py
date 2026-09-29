"""
Grass for Ridgeback's terrain: clumps of geometry blades (no alpha cards), with three LODs each, a colour atlas for the
blades and the materials that draw them with shaders/hc1grass.shader (a breeze of its own, and sinking into the
ground towards the edge of the scattered area). Two clutters scatter them over the meadow and dry grass ground:

- The grass (scenes/maps/Ridgeback/ridgeback_grass.clutter, the scene's "Grass"): thick, out to about 37 m (FADE).
- The far grass (ridgeback_grass_far.clutter, "Far Grass"): about a sixth as many clumps of wider blades, which rise
  out of the ground where the grass sinks and go on to about 127 m (FAR_FADE). Past that the ground itself is painted
  the grass's colour (ground_colour, which Tools/terrain_textures.py uses), so the field doesn't turn dark where the
  grass ends. That's how the big open-world shooters do it: dense grass close by, sparse cheap clumps further out, and
  ground that matches beyond.

    python Tools/ridgeback_grass.py [--preview <png>]

- Writes Assets/models/grass/: grass_blades.png (the atlas), grass.vmat and grass_far.vmat, and for each clump
  <name>.vmdl with <name>_lod0/1/2.obj. OBJs are written Y-up, as s&box's OBJ importer reads them (x, z, -y).
- Writes the clutters too: which clumps grow on which ground (ENTRIES, GROWS_ON), how thick (DENSITY) and how far out
  (TILE_SIZE, TILE_RADIUS, FADE), and the same for the far grass (FAR_*). Each runs from a ClutterComponent in
  Infinite mode, in tiles round the camera.
- A clump stands on its origin with its blades going up +Z: the shader bends a vertex by its height.
- Blade colours are columns in the atlas, root at the bottom, tip at the top; each clump draws from its own columns.
- Sizes are in inches (units): meadow grass up to about 70 cm, dry grass a little shorter, tufts ankle high.
- LODs keep the clump's outline with fewer, wider blades. The switch thresholds are the engine's screen-size metric
  (about distance / 19 at 1920 wide): lod1 from about 5 m, lod2 from about 13 m; the far clumps' from about 53 m and
  83 m.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/models/grass"
RESOURCE_DIR = "models/grass"
SEED = 4242

ATLAS = ( 512, 512 )
COLUMNS = 16
PAD = 3                              # px kept clear either side of a column, so mips don't bleed as much

# Blade colours, root / middle / tip. 0-9 green, 10-15 dry.
BLADE_COLOURS = [
    ( ( 38, 52, 22 ), ( 70, 98, 38 ), ( 112, 128, 58 ) ),
    ( ( 34, 50, 24 ), ( 62, 90, 40 ), ( 98, 122, 60 ) ),
    ( ( 40, 56, 22 ), ( 82, 106, 42 ), ( 132, 140, 70 ) ),
    ( ( 30, 44, 20 ), ( 56, 82, 34 ), ( 88, 112, 50 ) ),
    ( ( 44, 58, 26 ), ( 90, 112, 48 ), ( 140, 146, 82 ) ),
    ( ( 26, 40, 18 ), ( 50, 74, 32 ), ( 80, 102, 46 ) ),
    ( ( 34, 50, 30 ), ( 64, 90, 52 ), ( 100, 124, 76 ) ),
    ( ( 38, 54, 24 ), ( 76, 100, 42 ), ( 150, 138, 90 ) ),
    ( ( 44, 52, 24 ), ( 86, 98, 44 ), ( 126, 128, 66 ) ),
    ( ( 40, 60, 24 ), ( 84, 120, 44 ), ( 126, 150, 64 ) ),
    ( ( 60, 58, 34 ), ( 112, 102, 62 ), ( 156, 142, 98 ) ),
    ( ( 54, 54, 30 ), ( 100, 96, 54 ), ( 140, 130, 86 ) ),
    ( ( 58, 50, 30 ), ( 122, 106, 66 ), ( 166, 150, 106 ) ),
    ( ( 46, 54, 26 ), ( 88, 96, 48 ), ( 130, 126, 78 ) ),
    ( ( 64, 56, 36 ), ( 130, 114, 74 ), ( 174, 160, 116 ) ),
    ( ( 50, 46, 28 ), ( 96, 86, 54 ), ( 138, 124, 86 ) ),
]
GREEN = list( range( 0, 10 ) )
DRY = list( range( 10, 16 ) )

# name: blade count, root radius, lengths, widths, lean (deg), droop (deg), columns (with weights)
CLUMPS = {
    "grass_meadow_a": dict( blades=36, radius=7.0, lengths=( 16.0, 30.0 ), widths=( 0.7, 1.2 ), lean=( 4, 30 ),
                            droop=( 10, 55 ), columns=[ ( c, 1.0 ) for c in GREEN ] + [ ( 13, 0.6 ) ] ),
    "grass_meadow_b": dict( blades=30, radius=6.0, lengths=( 9.0, 19.0 ), widths=( 0.6, 1.0 ), lean=( 6, 38 ),
                            droop=( 8, 45 ), columns=[ ( c, 1.0 ) for c in GREEN ] ),
    "grass_dry_a": dict( blades=30, radius=6.5, lengths=( 10.0, 25.0 ), widths=( 0.6, 1.0 ), lean=( 8, 40 ),
                         droop=( 20, 75 ), columns=[ ( c, 1.0 ) for c in DRY ] + [ ( 8, 0.8 ), ( 7, 0.6 ) ] ),
    "grass_tuft": dict( blades=16, radius=3.0, lengths=( 5.0, 11.0 ), widths=( 0.5, 0.9 ), lean=( 10, 45 ),
                        droop=( 10, 40 ), columns=[ ( c, 1.0 ) for c in GREEN + DRY ] ),
}

# (keep every nth blade, width scale, segments, switch threshold)
LODS = [ ( 1, 1.0, 4, 0.0 ), ( 2, 1.7, 3, 10.0 ), ( 4, 2.8, 2, 25.0 ) ]

# The clutter: which clumps (with their weights) grow on which of the terrain's materials (Tools/terrain_textures.py).
# Dirt, gravel, rock and scree get none.
CLUTTER = ROOT / "Assets/scenes/maps/Ridgeback/ridgeback_grass.clutter"
ENTRIES = [ ( "grass_meadow_a", 3.0 ), ( "grass_meadow_b", 4.0 ), ( "grass_dry_a", 4.0 ), ( "grass_tuft", 2.0 ) ]
GROWS_ON = { "meadow": [ 0, 1, 3 ], "meadow_dry": [ 2, 3 ] }
DENSITY = 26.0                       # the scatterer's density: clumps per 10 square metres
TILE_SIZE, TILE_RADIUS = 512, 3      # tiles of grass round the camera's own tile
FADE = ( 1000.0, 1450.0 )            # the shader sinks clumps into the ground between these distances from the camera
GROUND_MATCH = 0.9                   # the grass ground is painted this share of the blades' colour (ground_colour)
FAR_TINT = ( GROUND_MATCH, ) * 3     # and the blades shade towards it on their way down (ground / blade colour)
assert FADE[1] < TILE_SIZE * TILE_RADIUS, "the grass would stop at the tiles' edge before it has sunk"

# The far grass: the same colours in wider blades (a blade under a pixel wide shimmers), in fewer, bigger clumps (each
# clump costs the CPU when its tile is scattered, each blade only the GPU), from where the grass sinks out to FAR_FADE.
# It rises over the grass's FADE, so the two cross over.
FAR_CLUMPS = {
    "grass_far_meadow": dict( blades=24, radius=13.0, lengths=( 14.0, 30.0 ), widths=( 1.8, 2.8 ), lean=( 4, 32 ),
                              droop=( 10, 50 ), columns=[ ( c, 1.0 ) for c in GREEN ] + [ ( 13, 0.6 ) ] ),
    "grass_far_short": dict( blades=20, radius=11.0, lengths=( 8.0, 18.0 ), widths=( 1.6, 2.4 ), lean=( 6, 40 ),
                             droop=( 8, 45 ), columns=[ ( c, 1.0 ) for c in GREEN + DRY ] ),
    "grass_far_dry": dict( blades=20, radius=12.0, lengths=( 10.0, 25.0 ), widths=( 1.6, 2.4 ), lean=( 8, 40 ),
                           droop=( 20, 75 ), columns=[ ( c, 1.0 ) for c in DRY ] + [ ( 8, 0.8 ), ( 7, 0.6 ) ] ),
}
FAR_LODS = [ ( 1, 1.0, 2, 0.0 ), ( 2, 1.4, 1, 110.0 ), ( 3, 1.8, 1, 170.0 ) ]
FAR_CLUTTER = ROOT / "Assets/scenes/maps/Ridgeback/ridgeback_grass_far.clutter"
FAR_ENTRIES = [ ( "grass_far_meadow", 3.0 ), ( "grass_far_short", 3.0 ), ( "grass_far_dry", 4.0 ) ]
FAR_GROWS_ON = { "meadow": [ 0, 1 ], "meadow_dry": [ 2, 1 ] }
FAR_DENSITY = 4.0                    # a clump every 1.6 m or so: seen from the side at these distances that closes up
FAR_TILE_SIZE, FAR_TILE_RADIUS = 1024, 5
FAR_FADE = ( 4000.0, 5000.0 )
assert FAR_FADE[1] < FAR_TILE_SIZE * FAR_TILE_RADIUS, "the far grass would stop at the tiles' edge before it has sunk"


# ---------------------------------------------------------------------------------------------------------------------
# The atlas

def write_atlas():
    w, h = ATLAS
    col_w = w // COLUMNS
    rng = np.random.default_rng( SEED )
    image = np.zeros( ( h, w, 3 ) )
    t = ( 1.0 - ( np.arange( h ) + 0.5 ) / h )[:, None]                  # 0 at the root (bottom), 1 at the tip (top)

    def smooth( a, b, x ):
        s = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
        return s * s * ( 3 - 2 * s )

    for c, ( root, mid, tip ) in enumerate( BLADE_COLOURS ):
        root, mid, tip = ( np.array( v, float ) for v in ( root, mid, tip ) )
        colour = root + ( mid - root ) * smooth( 0.0, 0.45, t )[..., None]
        colour = colour + ( tip - mid ) * smooth( 0.45, 1.0, t )[..., None]
        colour = np.broadcast_to( colour, ( h, col_w, 3 ) ).copy()

        # Across the blade: a lighter vein down the middle, darker edges; streaks along it
        x = ( np.arange( col_w ) + 0.5 ) / col_w
        across = 1.0 + 0.07 * np.exp( -( ( x - 0.5 ) / 0.09 ) ** 2 ) - 0.08 * np.clip( 1.0 - np.minimum( x, 1 - x ) / 0.2, 0, 1 )
        streaks = 1.0 + 0.05 * rng.standard_normal( col_w )
        along = 1.0 + 0.03 * np.convolve( rng.standard_normal( h + 40 ), np.ones( 40 ) / 40, "valid" )[:h]
        colour *= ( across * streaks )[None, :, None] * along[:, None, None]
        image[:, c * col_w:( c + 1 ) * col_w] = colour

    OUT_DIR.mkdir( parents=True, exist_ok=True )
    Image.fromarray( np.clip( np.rint( image ), 0, 255 ).astype( np.uint8 ) ).save( OUT_DIR / "grass_blades.png" )


def column_uv( column ):
    w = ATLAS[0]
    col_w = w // COLUMNS
    return ( column * col_w + PAD ) / w, ( ( column + 1 ) * col_w - PAD ) / w


def srgb_to_linear( c ):
    c = np.clip( np.asarray( c, float ) / 255.0, 0.0, 1.0 )
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def ground_colour( material ):
    """ The mean colour (linear, 0..1) Tools/terrain_textures.py paints a grass ground to, so that past where the clumps
    have sunk the field is still the grass's colour: the blades' upper parts (what a field shows, seen from the side)
    over the clumps growing on it, by their weights, times GROUND_MATCH. None for ground with no grass. """
    if material not in GROWS_ON:
        return None
    t = ( np.arange( 256 ) + 0.5 ) / 256                               # along the blade, root to tip
    u = np.clip( ( t - 0.25 ) / 0.65, 0.0, 1.0 )
    weight = ( 1.0 - 0.85 * t ** 1.4 ) * u * u * ( 3 - 2 * u )         # the blade's width, upper parts only

    def smooth( a, b, x ):
        v = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
        return v * v * ( 3 - 2 * v )

    total, weights = np.zeros( 3 ), 0.0
    for index in GROWS_ON[material]:
        name, entry_weight = ENTRIES[index]
        columns = CLUMPS[name]["columns"]
        column_total = sum( w for _, w in columns )
        for column, column_weight in columns:
            root, mid, tip = ( np.array( v, float ) for v in BLADE_COLOURS[column] )
            colour = root + ( mid - root ) * smooth( 0.0, 0.45, t )[:, None]     # as write_atlas draws it
            colour = colour + ( tip - mid ) * smooth( 0.45, 1.0, t )[:, None]
            mean = ( srgb_to_linear( colour ) * weight[:, None] ).sum( 0 ) / weight.sum()
            share = entry_weight * column_weight / column_total
            total += mean * share
            weights += share
    return total / weights * GROUND_MATCH


# ---------------------------------------------------------------------------------------------------------------------
# Clumps

def blade_params( rng, spec ):
    """ Each blade's root, length, width, lean, heading, droop, twist and colour column. """
    columns = [ c for c, _ in spec["columns"] ]
    weights = np.array( [ w for _, w in spec["columns"] ] )
    blades = []
    for _ in range( spec["blades"] ):
        r = spec["radius"] * math.sqrt( rng.uniform() )
        a = rng.uniform( 0, 2 * math.pi )
        root = ( r * math.cos( a ), r * math.sin( a ) )
        outward = a if r > 0.3 else rng.uniform( 0, 2 * math.pi )
        lo, hi = spec["lengths"]
        length = math.exp( rng.uniform( math.log( lo ), math.log( hi ) ) )
        blades.append( dict(
            root=root,
            length=length,
            width=rng.uniform( *spec["widths"] ),
            lean=math.radians( rng.uniform( *spec["lean"] ) ) * ( 0.5 + 0.5 * r / spec["radius"] ),
            heading=outward + rng.normal( 0, 0.6 ),
            droop=math.radians( rng.uniform( *spec["droop"] ) ) * length / hi,
            twist=rng.normal( 0, 0.5 ),
            column=columns[rng.choice( len( columns ), p=weights / weights.sum() )],
        ) )
    # Long blades first, so LODs that keep every nth blade keep the tall outline
    blades.sort( key=lambda b: -b["length"] )
    return blades


def blade_mesh( b, width_scale, segments ):
    """ Vertices (position, normal, uv) and triangles of one blade: a tapering strip bending over along its length. """
    heading = b["heading"]
    lean_dir = np.array( ( math.cos( heading ), math.sin( heading ), 0.0 ) )
    side0 = np.array( ( -math.sin( heading ), math.cos( heading ), 0.0 ) )
    u0, u1 = column_uv( b["column"] )
    p = np.array( ( b["root"][0], b["root"][1], 0.0 ) )
    ds = b["length"] / segments
    verts, tris = [], []
    for k in range( segments + 1 ):
        t = k / segments
        theta = b["lean"] + b["droop"] * t * t
        tangent = math.sin( theta ) * lean_dir + np.array( ( 0.0, 0.0, math.cos( theta ) ) )
        # Twist the blade's flat side round its length a little
        tw = b["twist"] * t
        side = side0 * math.cos( tw ) + np.cross( tangent, side0 ) * math.sin( tw )
        normal = np.cross( side, tangent )
        normal /= np.linalg.norm( normal )
        if normal[2] < 0:
            normal = -normal
        if k < segments:
            half = 0.5 * b["width"] * width_scale * ( 1.0 - 0.85 * t ** 1.4 )
            verts.append( ( p - side * half, normal, ( u0, t ) ) )
            verts.append( ( p + side * half, normal, ( u1, t ) ) )
        else:
            verts.append( ( p.copy(), normal, ( 0.5 * ( u0 + u1 ), 1.0 ) ) )
        if k < segments:
            # Step along the curve with the angle half a segment on, so the blade ends where it should
            tm = ( k + 0.5 ) / segments
            thm = b["lean"] + b["droop"] * tm * tm
            p = p + ( math.sin( thm ) * lean_dir + np.array( ( 0.0, 0.0, math.cos( thm ) ) ) ) * ds
    for k in range( segments - 1 ):
        a, bb, c, d = 2 * k, 2 * k + 1, 2 * k + 2, 2 * k + 3
        tris += [ ( a, bb, d ), ( a, d, c ) ]
    last = 2 * ( segments - 1 )
    tris.append( ( last, last + 1, 2 * segments ) )
    return verts, tris


def clump_mesh( blades, keep, width_scale, segments ):
    verts, tris = [], []
    for b in blades[::keep]:
        v, t = blade_mesh( b, width_scale, segments )
        base = len( verts )
        verts += v
        tris += [ ( a + base, bb + base, c + base ) for a, bb, c in t ]
    return verts, tris


def write_obj( path, verts, tris ):
    lines = [ "# Tools/ridgeback_grass.py (Y-up, as s&box reads OBJ)", "o grass" ]
    for p, n, uv in verts:
        lines.append( f"v {p[0]:.4f} {p[2]:.4f} {-p[1]:.4f}" )
    for p, n, uv in verts:
        lines.append( f"vt {uv[0]:.5f} {uv[1]:.5f}" )
    for p, n, uv in verts:
        lines.append( f"vn {n[0]:.4f} {n[2]:.4f} {-n[1]:.4f}" )
    for a, b, c in tris:
        lines.append( f"f {a + 1}/{a + 1}/{a + 1} {b + 1}/{b + 1}/{b + 1} {c + 1}/{c + 1}/{c + 1}" )
    path.write_text( "\n".join( lines ) + "\n", encoding="utf-8" )


def write_vmdl( name, lods=LODS, material="grass" ):
    meshes = ",\n".join(
        f'    {{ _class = "RenderMeshFile" name = "lod{k}" filename = "{RESOURCE_DIR}/{name}_lod{k}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }'
        for k in range( len( lods ) ) )
    groups = ",\n".join(
        f'    {{ _class = "LODGroup" switch_threshold = {threshold:.1f} meshes = [ "lod{k}" ] }}'
        for k, ( _, _, _, threshold ) in enumerate( lods ) )
    text = f'''<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
{{
 rootNode =
 {{
  _class = "RootNode"
  children =
  [
   {{ _class = "MaterialGroupList" children = [ {{ _class = "DefaultMaterialGroup" remaps = [ ] use_global_default = true global_default_material = "{RESOURCE_DIR}/{material}.vmat" }} ] }},
   {{ _class = "RenderMeshList" children = [
{meshes}
   ] }},
   {{ _class = "LODGroupList" children = [
{groups}
   ] }},
  ]
  model_archetype = ""
  primary_associated_entity = ""
  base_model_name = ""
 }}
}}
'''
    ( OUT_DIR / f"{name}.vmdl" ).write_text( text, encoding="utf-8" )


def vmat( fade, rise=( 0.0, 0.0 ) ):
    """ The material: fade is where the clumps sink into the ground, rise where they come up out of it (none if 0). """
    return f'''// Tools/ridgeback_grass.py
Layer0
{{
	shader "shaders/hc1grass.shader"

	F_RENDER_BACKFACES 1
	F_TRANSMISSIVE 1
	F_DO_NOT_CAST_SHADOWS 1

	g_bFogEnabled "1"

	g_flBladeHeight "26.000"
	g_flSwayAmount "1.200"
	g_flSwaySpeed "0.900"
	g_flGustAmount "3.000"
	g_flGustLength "1400.000"
	g_flGustSpeed "260.000"
	g_vWindHeading "[0.600 -0.800]"
	g_flFadeStart "{fade[0]:.3f}"
	g_flFadeEnd "{fade[1]:.3f}"
	g_flRiseStart "{rise[0]:.3f}"
	g_flRiseEnd "{rise[1]:.3f}"
	g_vFarTint "[{FAR_TINT[0]:.3f} {FAR_TINT[1]:.3f} {FAR_TINT[2]:.3f}]"

	g_flWrapAmount "0.500"
	g_flWrapStrength "0.300"
	g_flMinRoughness "0.600"
	g_flGrassNormalUp "0.600"
	g_flColourVariation "0.120"
	g_flTransmissionScale "0.600"

	TextureColor "{RESOURCE_DIR}/grass_blades.png"
	TextureTransmissiveColor "{RESOURCE_DIR}/grass_blades.png"
	TextureNormal "materials/default/default_normal.tga"
	TextureRoughness "[0.800000 0.800000 0.800000 0.000000]"
	TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"
	TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
'''


def write_clutter( path, entries, grows_on, density, tile_size, tile_radius, scale ):
    """ Scatters the clumps over the grass ground, in tiles round the camera (a ClutterComponent in Infinite mode). """
    doc = {
        "Entries": [ { "Prefab": None, "Model": f"{RESOURCE_DIR}/{name}.vmdl", "Weight": weight, "LocalScale": 1,
                       "CastShadows": False, "EnablePhysics": False } for name, weight in entries ],
        "TileSizeEnum": f"Size{tile_size}",
        "TileRadius": tile_radius,
        "Scatterer": {
            "Type": "TerrainMaterialScatterer",
            "Scale": scale,
            "Density": density,
            "HeightOffset": -2,                          # roots into the ground on slopes
            "AlignToNormal": False,                      # grass grows straight up, whatever the slope
            "RandomYaw": True,
            "Mappings": [ { "Material": f"materials/terrain/{material}.tmat", "EntryIndices": indices }
                          for material, indices in grows_on.items() ],
            "UseFallback": False,
        },
        "__references": [],
        "__version": 0,
    }
    path.write_text( json.dumps( doc, indent=2 ) + "\n", encoding="utf-8" )
    print( f"wrote {path.relative_to( ROOT )}" )


def preview( meshes, path ):
    """ The clumps from the side and a little above, each LOD in a row, flat shaded from the atlas colours. """
    atlas = np.asarray( Image.open( OUT_DIR / "grass_blades.png" ).convert( "RGB" ), float )
    cell = 260
    image = Image.new( "RGB", ( cell * len( meshes ), cell * len( LODS ) ), ( 150, 170, 190 ) )
    draw = ImageDraw.Draw( image )
    yaw, pitch = math.radians( 30 ), math.radians( 20 )
    light = np.array( ( 0.4, -0.3, 0.85 ) )
    light /= np.linalg.norm( light )
    for col, ( name, lods ) in enumerate( meshes.items() ):
        for row, ( verts, tris ) in enumerate( lods ):
            pos = np.array( [ v[0] for v in verts ] )
            cx, cy = col * cell + cell / 2, row * cell + cell * 0.82
            x = pos[:, 0] * math.cos( yaw ) - pos[:, 1] * math.sin( yaw )
            depth = pos[:, 0] * math.sin( yaw ) + pos[:, 1] * math.cos( yaw )
            y = pos[:, 2] * math.cos( pitch ) - depth * math.sin( pitch )
            scale = 5.5
            order = sorted( tris, key=lambda t: -np.mean( depth[list( t )] ) )
            for t in order:
                u = np.mean( [ verts[k][2][0] for k in t ] )
                v = np.mean( [ verts[k][2][1] for k in t ] )
                colour = atlas[min( int( ( 1 - v ) * ATLAS[1] ), ATLAS[1] - 1 ), min( int( u * ATLAS[0] ), ATLAS[0] - 1 )]
                n = verts[t[0]][1]
                shade = 0.55 + 0.45 * abs( float( np.dot( n, light ) ) )
                pts = [ ( cx + x[k] * scale, cy - y[k] * scale ) for k in t ]
                draw.polygon( pts, fill=tuple( int( c * shade ) for c in colour ) )
            draw.text( ( col * cell + 6, row * cell + 4 ), f"{name} lod{row} {len( tris )} tris", fill=( 0, 0, 0 ) )
    image.save( path )
    print( f"wrote preview {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", help="also draw the clumps and their LODs here" )
    args = parser.parse_args()

    write_atlas()
    ( OUT_DIR / "grass.vmat" ).write_text( vmat( FADE ), encoding="utf-8" )
    ( OUT_DIR / "grass_far.vmat" ).write_text( vmat( FAR_FADE, FADE ), encoding="utf-8" )
    meshes = {}
    # Each layer draws from its own random numbers, so changing the far clumps leaves the grass as it was
    layers = ( ( CLUMPS, LODS, "grass", SEED ), ( FAR_CLUMPS, FAR_LODS, "grass_far", SEED + 1 ) )
    for clumps, lod_specs, material, seed in layers:
        rng = np.random.default_rng( seed )
        for name, spec in clumps.items():
            blades = blade_params( rng, spec )
            lods = []
            for k, ( keep, width_scale, segments, _ ) in enumerate( lod_specs ):
                verts, tris = clump_mesh( blades, keep, width_scale, segments )
                write_obj( OUT_DIR / f"{name}_lod{k}.obj", verts, tris )
                lods.append( ( verts, tris ) )
            write_vmdl( name, lod_specs, material )
            heights = [ v[0][2] for v in lods[0][0] ]
            print( f"{name}: {len( blades )} blades, up to {max( heights ):.1f} units high, "
                   + ", ".join( f"lod{k} {len( t )} tris" for k, ( _, t ) in enumerate( lods ) ) )
            meshes[name] = lods
    write_clutter( CLUTTER, ENTRIES, GROWS_ON, DENSITY, TILE_SIZE, TILE_RADIUS, "0.7 1.25" )
    write_clutter( FAR_CLUTTER, FAR_ENTRIES, FAR_GROWS_ON, FAR_DENSITY, FAR_TILE_SIZE, FAR_TILE_RADIUS, "0.8 1.3" )
    for material in GROWS_ON:
        print( f"{material} ground colour (linear): {np.round( ground_colour( material ), 4 )}" )
    if args.preview:
        preview( meshes, args.preview )


if __name__ == "__main__":
    main()
