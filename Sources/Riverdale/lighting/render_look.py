"""
Riverdale rendered offline in Cycles from a scene file other than the map's own (a staged copy from
look_proposal.py --stage-scenes), with Tools/railhead_render.py doing the work, to compare the current light with the
proposed one before anything goes into the editor. Nothing is written to Assets.

    blender -b --factory-startup --python Sources/Riverdale/lighting/render_look.py -- --scene <file.scene> --out <dir>
        --exposure 1.4 --view name,e,n,z,te,tn,tz,fov [--view ...] [--size 960x540] [--samples 48] [--bloom 0.3]

What Cycles shows and a match doesn't (railhead_render's docstring has the rest): it bounces light, so it stands for the
baked indirect light, not for today's flat ambient; it has no SkyColor floor, SSAO, SSR or reflection probes; spot
lights render as point lights; the exposure is fixed where a match adapts. So it compares one light against another, as
the bake would show them, not a final frame.
"""
import sys
from pathlib import Path

ROOT = Path( __file__ ).resolve().parents[3]
sys.path.insert( 0, str( ROOT / "Tools" ) )

import json                       # noqa: E402
import railhead_render as RR      # noqa: E402  (Blender's own Python; Tools must be on the path first)

argv = sys.argv[sys.argv.index( "--" ) + 1:] if "--" in sys.argv else []
if "--scene" not in argv:
    raise SystemExit( "--scene <file> is required" )
k = argv.index( "--scene" )
RR.SCENE = Path( argv[k + 1] ).resolve()

# A ModelRenderer with RenderType "Off" casts no shadow in a match (Riverdale's far backdrop: the cooling towers, hills
# and forest). railhead_render lets every model cast, so at the sun's 16 degrees the towers and hills in the east
# shadowed the yard here as they never do in the game.
NO_SHADOW = set()


def collect( objects ):
    for o in objects:
        if o.get( "Enabled", True ) is False:
            continue
        for c in o.get( "Components", [] ):
            if c.get( "__type" ) == "Sandbox.ModelRenderer" and c.get( "RenderType" ) == "Off" and c.get( "Model" ):
                NO_SHADOW.add( c["Model"] )
        collect( o.get( "Children", [] ) )


collect( json.loads( RR.SCENE.read_text( encoding="utf-8" ) )["GameObjects"] )
_map_model = RR.map_model


def map_model( path ):
    objects = _map_model( path )
    if path in NO_SHADOW:
        for o in objects:
            o.visible_shadow = False
    return objects


RR.map_model = map_model
print( f"no shadows from: {sorted( NO_SHADOW )}" )

# SpotLights as Blender spots (railhead_render renders them as point lights): the same brightness rule as its points
# (the engine's colour a quarter of the radius out), masked to the cone, pointing along the light's +x.
SPOTS = []
_read_scene = RR.read_scene


def read_scene():
    import math
    from mathutils import Matrix
    found = _read_scene()

    def walk( go, parent ):
        if go.get( "Enabled", True ) is False:
            return
        world = parent @ RR.local_matrix( go )
        for c in go.get( "Components", [] ):
            if c.get( "__type" ) == "Sandbox.SpotLight" and c.get( "__enabled", True ) is not False:
                SPOTS.append( ( world, RR.floats( c["LightColor"] ), float( c.get( "Radius", 400 ) ),
                                float( c.get( "ConeInner", 15 ) ), float( c.get( "ConeOuter", 45 ) ) ) )
        for child in go.get( "Children", [] ):
            walk( child, world )
    for go in json.loads( RR.SCENE.read_text( encoding="utf-8" ) )["GameObjects"]:
        walk( go, Matrix.Identity( 4 ) )
    spot_places = { tuple( round( v, 3 ) for v in s[0].to_translation() ) for s in SPOTS }
    found["points"] = [ p for p in found["points"] if tuple( round( v, 3 ) for v in p[0].to_translation() ) not in spot_places ]
    print( f"{len( SPOTS )} spot lights, {len( found['points'] )} point lights" )
    return found


def add_spots():
    import bpy
    import math
    from mathutils import Vector
    for world, colour, radius, inner, outer in SPOTS:
        strength = max( max( colour[:3] ), 1e-3 )
        light = bpy.data.lights.new( "Spot", "SPOT" )
        light.color = tuple( c / strength for c in colour[:3] )
        d0 = radius / 4
        light.energy = 4 * math.pi * d0 * d0 * math.pi * strength
        light.shadow_soft_size = 4.0
        light.spot_size = math.radians( min( 2 * outer, 179 ) )
        light.spot_blend = max( 0.0, min( 1.0, 1 - inner / max( outer, 1e-3 ) ) )
        obj = bpy.data.objects.new( "Spot", light )
        obj.location = world.to_translation()
        forward = world.to_3x3() @ Vector( ( 1, 0, 0 ) )
        obj.rotation_euler = forward.to_track_quat( "-Z", "Y" ).to_euler()
        bpy.context.scene.collection.objects.link( obj )


_add_sky = RR.add_sky


def add_sky( material_path, haze ):
    add_spots()
    return _add_sky( material_path, haze )


RR.read_scene = read_scene
RR.add_sky = add_sky
rest = argv[:k] + argv[k + 2:]
if "--views" not in rest:
    rest = [ "--views", "" ] + rest
sys.argv = [ sys.argv[0], "--" ] + rest
print( f"rendering {RR.SCENE}" )
RR.main()
