"""
Riverdale's baked lighting: the indirect light (DDGI volumes) and static reflections, planned here, baked and captured
in the editor by Sources/Riverdale/editor/*.cs.txt, and kept here so Tools/riverdale_map.py's next run writes them back
into the scene it rewrites.

    python Sources/Riverdale/lighting/riverdale_lighting.py config             # write config.json from the map's layout
    python Sources/Riverdale/lighting/riverdale_lighting.py check [--preview]  # grids, capture points, cube previews
    python Sources/Riverdale/lighting/riverdale_lighting.py preserve           # keep a finished bake and capture
    python Sources/Riverdale/lighting/riverdale_lighting.py status             # is the kept bake still current?

Plan coordinates as in Tools/riverdale_map.py: e east, n north, z up, inches. The scene's world is ( n, -e, z ).

The indirect light, three IndirectLightVolumes baked in this order, so each later one sees the earlier ones' light:
- yard: the whole play area out to 16 past its edges, from the ground (z 2; receivers are sampled 20 up their normal)
  to 578, over every roof but the hall's (440 at most). The engine caps a grid at 40 a side, so 35 x 38 x 6 probes
  about 125 apart. It covers the hall too; inside, the hall's smaller volume wins.
- hall: the reactor hall's inside, 16 into its walls, deck and roof, 19 x 17 x 9 probes about 125 apart. A short blend
  (24) keeps its own light right up to its walls instead of fading to the yard's coarse probes there.
- pool: the fuel pool, from its floor to 8 over the deck (so the liner above the water is covered too), 10 x 10 x 6.
  Without it the liner would get the open sky's light. It's the smallest, so it wins inside its box.
Biases 20 along the normal and 30 towards the eye, as Belltower's and Cerro Blanco's at the same spacing.

The reflections, twelve static (CustomTexture) probes, each a cube captured from camera faces at a point in its room's
open air (capture-reflections.cs.txt), box-projected over the room. The realtime probes they replace ran the engine's
envmap filtering at load, which faulted envmap_filtering_cs on this workstation. The single yard probe stood inside B1's
core, and the courts had none: the yard is split in two and the courts have their own. Higher priority wins where boxes
overlap (the control rooms and the pool inside the hall's box).

Tools/riverdale_map.py reads what preserve kept with indirect_light_object() and reflection_probes_object(); see
output/riverdale/aaa/lighting/proposal.json ("generator_integration"). planned_indirect_object() is the volumes as
planned, in the engine's schema, for a generator that writes them itself before the first bake.
"""
import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
TOOLS = ROOT / "Tools"
ASSETS = ROOT / "Assets"
CONFIG = HERE / "config.json"
INDIRECT_CACHE = HERE / "indirect.json"
REFLECTIONS_CACHE = HERE / "reflections.json"
MANIFEST = HERE / "manifest.json"
RUNS = ROOT / "output/riverdale/lighting"                # what the editor scripts write
AAA = ROOT / "output/riverdale/aaa/lighting"             # this pass's offline checks and previews
SCENE = ASSETS / "scenes/maps/Riverdale/riverdale.scene"
SCENE_NAMESPACE = "5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85"   # Tools/riverdale_map.py's SceneIds, so the ids match its own
REVISION = "daylight-v1"
ENGINE = "26.10.13"
TEXTURES = ( "IrradianceTexture", "DistanceTexture", "RelocationTexture" )


def _tools():
    if str( TOOLS ) not in sys.path:
        sys.path.insert( 0, str( TOOLS ) )


def to_world( p ):
    return ( float( p[1] ), -float( p[0] ), float( p[2] ) )


def world_box( box ):
    """ A plan box ( e0, e1, n0, n1, z0, z1 ) as world ( mins, maxs ). """
    e0, e1, n0, n1, z0, z1 = box
    return ( n0, -e1, z0 ), ( n1, -e0, z1 )


def fmt( v ):
    return ",".join( f"{float( c ) + 0.0:g}" for c in v )        # + 0.0: no "-0"


def rel( path ):
    """ A path as the repository names it, or whole if it's elsewhere. """
    path = Path( path ).resolve()
    return path.relative_to( ROOT ).as_posix() if path.is_relative_to( ROOT ) else path.as_posix()


def engine_counts( mins, maxs, density ):
    """ IndirectLightVolume.ComputeProbeCounts: ceil( size x density / 1024 ) + 1 a side, 4 to 40. """
    return tuple( min( 40, max( 4, math.ceil( ( b - a ) * density / 1024.0 ) + 1 ) ) for a, b in zip( mins, maxs ) )


# ---------------------------------------------------------------------------------------------------------------------
# The plan

def layout():
    """ The map's own numbers (imported here, never at the top: riverdale_map imports its modules at load). """
    _tools()
    import riverdale_hall as H
    import riverdale_map as M
    return H, M


def plan_volumes():
    H, M = layout()
    e0, e1, n0, n1 = M.PLAY
    return [
        { "key": "yard", "name": "Plant Yard Indirect Light", "box": ( e0 - 16, e1 + 16, n0 - 16, n1 + 16, 2.0, 578.0 ),
          "probe_density": 8, "normal_bias": 20.0, "view_bias": 30.0, "blend_distance": 120.0,
          "runtime_intensity": 1.6, "runtime_contrast": 1.0, "runtime_saturation": 1.0, "timeout_seconds": 1800 },
        { "key": "hall", "name": "Reactor Hall Indirect Light", "box": ( H.E0 - 16, H.E1 + 16, H.N0 - 16, H.N1 + 16, 2.0, H.TOP + 16 ),
          "probe_density": 8, "normal_bias": 20.0, "view_bias": 30.0, "blend_distance": 24.0,
          "runtime_intensity": 1.8, "runtime_contrast": 1.0, "runtime_saturation": 1.0, "timeout_seconds": 1200 },
        { "key": "pool", "name": "Fuel Pool Indirect Light",
          "box": ( H.POOL[0] - H.POOL_R - 8, H.POOL[0] + H.POOL_R + 8, H.POOL[1] - H.POOL_R - 8, H.POOL[1] + H.POOL_R + 8,
                   H.POOL_FLOOR - 8, 8.0 ),
          "probe_density": 8, "normal_bias": 20.0, "view_bias": 30.0, "blend_distance": 24.0,
          "runtime_intensity": 1.2, "runtime_contrast": 1.0, "runtime_saturation": 1.0, "timeout_seconds": 900 },
    ]


def plan_reflections():
    """ ( key, scene name, capture point, box, priority, exposure, fallback tint ); boxes are the old probes' where
    they had one. exposure: the fixed exposure faces are captured at (the converter divides it out); fallback: how
    dim the sky cube stands in until the capture (indoors it's a stand-in for a dark room). """
    H, M = layout()
    p0, p1, q0, q1 = M.PLAY
    a0, a1, b0, b1 = M.ANNEX
    c0, c1, cn0, cn1 = H.CONTROL
    core = M.CORE
    out = [
        ( "hall", "Probe Hall", ( -260, 560, 330 ), ( H.E0, H.E1, H.N0, H.N1, -40, H.TOP ), 1, 2.5, 0.15 ),
        ( "pool", "Probe Pool", ( -260, 900, -220 ),
          ( -H.POOL_R, H.POOL_R, H.POOL[1] - H.POOL_R, H.POOL[1] + H.POOL_R, H.POOL_FLOOR, 0 ), 2, 2.5, 0.1 ),
        ( "a1", "Probe A1", ( ( a0 + a1 ) / 2, ( b0 + b1 ) / 2, 150 ), ( a0 + 30, a1 - 30, b0 + 30, b1 - 30, 0, M.ANNEX_TOP - 20 ), 1, 2.5, 0.15 ),
        ( "a2", "Probe A2", ( -( a0 + a1 ) / 2, ( b0 + b1 ) / 2, 150 ), ( -a1 + 30, -a0 - 30, b0 + 30, b1 - 30, 0, M.ANNEX_TOP - 20 ), 1, 2.5, 0.15 ),
        ( "b1_room", "Probe B1 Room", ( 0, ( core[2] + core[3] ) / 2, 280 ),
          ( core[0] + 24, core[1] - 24, core[2] + 24, core[3] - 24, M.ROOM_Z, M.CORE_TOP - 20 ), 1, 2.5, 0.15 ),
        ( "west_control", "Probe West Control", ( ( c0 + c1 ) / 2, ( cn0 + cn1 ) / 2, 370 ), ( c0, c1, cn0, cn1, H.UPPER, H.CONTROL_TOP ), 2, 2.5, 0.15 ),
        ( "east_control", "Probe East Control", ( -( c0 + c1 ) / 2, ( cn0 + cn1 ) / 2, 370 ), ( -c1, -c0, cn0, cn1, H.UPPER, H.CONTROL_TOP ), 2, 2.5, 0.15 ),
        ( "west_yard", "Probe West Yard", ( -1250, -880, 170 ), ( p0, 0, q0, H.N0 - H.WT, -20, 900 ), 0, 1.5, 1.0 ),
        ( "east_yard", "Probe East Yard", ( 1250, -880, 170 ), ( 0, p1, q0, H.N0 - H.WT, -20, 900 ), 0, 1.5, 1.0 ),
        ( "west_court", "Probe West Court", ( -1370, 1100, 170 ), ( p0, H.E0 - H.WT, H.N0 - H.WT, H.N1 + H.WT, -20, 800 ), 0, 1.5, 1.0 ),
        ( "east_court", "Probe East Court", ( 1370, 1100, 170 ), ( H.E1 + H.WT, p1, H.N0 - H.WT, H.N1 + H.WT, -20, 800 ), 0, 1.5, 1.0 ),
        ( "north", "Probe North", ( -370, 2330, 170 ), ( p0, p1, H.N1 + H.WT, q1, -20, 700 ), 0, 1.5, 1.0 ),
    ]
    return [ { "key": k, "name": n, "capture": tuple( float( c ) for c in at ), "box": tuple( float( c ) for c in box ),
               "priority": pr, "exposure": ex, "fallback_tint": fb, "tint": 1.0, "feathering": 0.04 }
             for k, n, at, box, pr, ex, fb in out ]


CALIBRATION = "west_yard"       # its upward face is open sky (check proves it): the converter calibrates on it


def build_config():
    volumes = []
    for order, v in enumerate( plan_volumes() ):
        mins, maxs = world_box( v["box"] )
        counts = engine_counts( mins, maxs, v["probe_density"] )
        entry = { "key": v["key"], "name": v["name"], "order": order, "plan_box": list( v["box"] ),
                  "bounds_min": fmt( mins ), "bounds_max": fmt( maxs ), "expected_counts": fmt( counts ),
                  "probes": counts[0] * counts[1] * counts[2],
                  "spacing": fmt( tuple( round( ( b - a ) / ( c - 1 ), 1 ) for a, b, c in zip( mins, maxs, counts ) ) ) }
        entry.update( { k: v[k] for k in ( "probe_density", "normal_bias", "view_bias", "blend_distance", "runtime_intensity",
                                            "runtime_contrast", "runtime_saturation", "timeout_seconds" ) } )
        volumes.append( entry )
    reflections = []
    for r in plan_reflections():
        mins, maxs = world_box( r["box"] )
        reflections.append( { "key": r["key"], "name": r["name"], "capture_plan": list( r["capture"] ),
                              "capture_world": fmt( to_world( r["capture"] ) ), "plan_box": list( r["box"] ),
                              "bounds_min": fmt( mins ), "bounds_max": fmt( maxs ), "priority": r["priority"],
                              "exposure": r["exposure"], "fallback_tint": r["fallback_tint"], "tint": r["tint"],
                              "feathering": r["feathering"], "calibration": r["key"] == CALIBRATION } )
    return { "revision": REVISION, "engine": ENGINE, "scene": "scenes/maps/riverdale/riverdale.scene",
             "note": "Written by Sources/Riverdale/lighting/riverdale_lighting.py config; world = ( n, -e, z ).",
             "timeout_seconds": 900, "reflection_capture_size": 512, "volumes": volumes, "reflections": reflections }


def write_json( path, value ):
    """ Whole files only: written beside, then moved over. """
    pending = path.with_name( path.name + ".pending" )
    pending.write_text( json.dumps( value, indent=2 ) + "\n", encoding="utf-8" )
    pending.replace( path )


def load_config():
    return json.loads( CONFIG.read_text( encoding="utf-8" ) )


# ---------------------------------------------------------------------------------------------------------------------
# For Tools/riverdale_map.py

def indirect_light_object():
    """ The kept "Indirect Light" group (its baked volumes), or None before the first preserve. """
    if not _cache_matches_revision() or not INDIRECT_CACHE.is_file():
        return None
    return json.loads( INDIRECT_CACHE.read_text( encoding="utf-8" ) )


def reflection_probes_object( fallback_texture=None, ids=None ):
    """ The kept "Reflection Probes" group (each probe static on its captured cube). Before the first capture, with
    fallback_texture (a compiled sky cube's resource path, see sky_fallback_texture()) and the scene's ids, the planned
    probes static on that cube, dimmed indoors; else None (keep the old probes). """
    if _cache_matches_revision( reflections=True ) and REFLECTIONS_CACHE.is_file():
        return json.loads( REFLECTIONS_CACHE.read_text( encoding="utf-8" ) )
    if fallback_texture is None or ids is None:
        return None
    config = load_config()
    children = []
    for r in config["reflections"]:
        short = r["name"].removeprefix( "Probe " )
        key = f"probe/{short}"
        at = [ float( c ) for c in r["capture_world"].split( "," ) ]
        lo = [ float( c ) - a for c, a in zip( r["bounds_min"].split( "," ), at ) ]
        hi = [ float( c ) - a for c, a in zip( r["bounds_max"].split( "," ), at ) ]
        t = r["fallback_tint"]
        children.append( probe_json( ids, key, r["name"], at, lo, hi, r, fallback_texture, t ) )
    return group_json( ids( "probes" ), "Reflection Probes", children )


def _cache_matches_revision( reflections=False ):
    """Never inject textures from an older revision or an indirect-only preserve."""
    if not MANIFEST.is_file() or not CONFIG.is_file():
        return False
    manifest = json.loads( MANIFEST.read_text( encoding="utf-8" ) )
    return ( manifest.get( "revision" ) == REVISION == load_config().get( "revision" )
             and ( not reflections or manifest.get( "reflections" ) is True ) )


def planned_indirect_object( ids, baked=False ):
    """ The "Indirect Light" group as the plan has it, in the engine's own schema (IndirectLightVolume __version 2, as
    Belltower's kept indirect.json): unbaked (BakeVersion 0, no textures), or with baked=True the texture paths the bake
    writes. With it the generator could write the volumes itself before a bake, in place of prepare-lighting. """
    config = load_config()
    children = []
    for v in config["volumes"]:
        prefix = f"lighting/riverdale/{config['revision']}/{v['key']}_"
        children.append( {
            "__guid": ids( f"indirect/{v['key']}" ), "__version": 2, "Flags": 0, "Name": v["name"], "Position": "0,0,0",
            "Rotation": "0,0,0,1", "Scale": "1,1,1", "Tags": "", "Enabled": True, "NetworkMode": 2, "NetworkFlags": 0,
            "NetworkOrphaned": 0, "NetworkTransmit": True, "OwnerTransfer": 1,
            "Components": [ {
                "__type": "Sandbox.IndirectLightVolume", "__guid": ids( f"indirect/{v['key']}/volume" ), "__enabled": True, "Flags": 0,
                "__version": 2, "BakeVersion": 1 if baked else 0, "BlendDistance": v["blend_distance"],
                "Bounds": { "Mins": v["bounds_min"], "Maxs": v["bounds_max"] },
                "DistanceTexture": prefix + "distance.vtex" if baked else None, "InsideGeometry": "Relocate",
                "IrradianceTexture": prefix + "irradiance.vtex" if baked else None, "NormalBias": v["normal_bias"],
                "ProbeDensity": v["probe_density"], "RelocationTexture": prefix + "relocation.vtex" if baked else None,
                "RenderExcludeTags": "", "RuntimeContrast": v["runtime_contrast"], "RuntimeIntensity": v["runtime_intensity"],
                "RuntimeSaturation": v["runtime_saturation"], "RuntimeTint": "1,1,1,1", "ViewBias": v["view_bias"] } ],
            "Children": [] } )
    return group_json( ids( "indirect" ), "Indirect Light", children )


def probe_json( ids, key, name, at, lo, hi, r, texture, tint ):
    return {
        "__guid": ids( key ), "__version": 2, "Flags": 0, "Name": name, "Position": fmt( at ), "Rotation": "0,0,0,1",
        "Scale": "1,1,1", "Tags": "", "Enabled": True, "NetworkMode": 2, "NetworkFlags": 0, "NetworkOrphaned": 0,
        "NetworkTransmit": True, "OwnerTransfer": 1,
        "Components": [ {
            "__type": "Sandbox.EnvmapProbe", "__guid": ids( f"{key}/probe" ), "__enabled": True, "Flags": 0, "__version": 1,
            "BakedTexture": None, "Bounds": { "Mins": fmt( lo ), "Maxs": fmt( hi ) }, "DelayBetweenUpdates": 0.1,
            "Feathering": r["feathering"], "FrameInterval": 5, "MaxDistance": 512, "Mode": "CustomTexture", "MultiBounce": False,
            "Priority": r["priority"], "Projection": "Box", "RenderExcludeTags": "", "Resolution": "Small", "Texture": texture,
            "TintColor": f"{tint:g},{tint:g},{tint:g},1", "UpdateStrategy": "OnEnabled", "ZFar": 4096, "ZNear": 8 } ],
        "Children": [] }


def group_json( guid, name, children ):
    return { "__guid": guid, "__version": 2, "Flags": 0, "Name": name, "Position": "0,0,0", "Rotation": "0,0,0,1",
             "Scale": "1,1,1", "Tags": "", "Enabled": True, "NetworkMode": 2, "NetworkFlags": 0, "NetworkOrphaned": 0,
             "NetworkTransmit": True, "OwnerTransfer": 1, "Components": [], "Children": children }


def sky_fallback_texture( copy=False ):
    """ The sky's compiled cube (materials/riverdale/sky/riverdale_sky_exr_*.generated.vtex_c, newest) as
    lighting/riverdale/<revision>/sky_fallback_<hash>.vtex, named by its content so a running editor never keeps an older
    cube under the same name (Orion's lesson); prepare-lighting.cs.txt makes the same copy. copy=True writes the copy
    into Assets (the generator's run; never from this pass). Returns the resource path, or None with no compiled sky. """
    cubes = sorted( ( ASSETS / "materials/riverdale/sky" ).glob( "riverdale_sky_exr_*.generated.vtex_c" ), key=lambda p: p.stat().st_mtime )
    if not cubes:
        return None
    data = cubes[-1].read_bytes()
    path = f"lighting/riverdale/{REVISION}/sky_fallback_{hashlib.sha256( data ).hexdigest()[:8]}.vtex"
    target = ASSETS / ( path + "_c" )
    if copy and not target.exists():
        target.parent.mkdir( parents=True, exist_ok=True )
        pending = target.with_name( target.name + ".pending" )
        pending.write_bytes( data )
        pending.replace( target )
    return path


# ---------------------------------------------------------------------------------------------------------------------
# preserve and status

def texture_path( value, prefix ):
    """ The engine saves resources as { Id, Path }; the cache keeps the path, the portable part. """
    path = value.get( "Path" ) if isinstance( value, dict ) else value
    if not isinstance( path, str ) or not path.startswith( prefix ) or not path.endswith( ".vtex" ) or ".." in path:
        raise ValueError( f"unexpected lighting texture {path!r}" )
    if not ( ASSETS / ( path + "_c" ) ).is_file() or not ( ASSETS / ( path + "_c" ) ).stat().st_size:
        raise FileNotFoundError( ASSETS / ( path + "_c" ) )
    return path


def scene_ids():
    _tools()
    import map_kit as K
    return K.SceneIds( SCENE_NAMESPACE )


def source_hashes():
    """ What a bake depends on besides the scene's lights: the models, the materials (and their maps), the sky. """
    files = [ p for folder in ( "models/maps/riverdale", "materials/riverdale", "materials/riverdale/sky" )
              for p in sorted( ( ASSETS / folder ).glob( "*" ) )
              if p.is_file() and not p.name.endswith( "_c" ) and not p.name.endswith( ".meta" ) and ".riverdale-" not in p.name ]
    out = {}
    for p in files:
        with p.open( "rb" ) as stream:
            out[rel( p )] = hashlib.file_digest( stream, "sha256" ).hexdigest()
    return out


def verify_bake_inputs( attempt, current_sources ):
    """Compare a successful bake's exact source snapshot to what will be preserved.

    The editor adds bake textures and probe assignments to the scene as it runs, so
    its scene-file hash changes legitimately. Its model/material/sky source hashes
    must not: otherwise preserving would stamp an obsolete bake as current.
    """
    snapshot = attempt / "input-assets.json"
    if not snapshot.is_file():
        raise ValueError( f"{rel( attempt )}: missing the bake's input-assets.json" )
    original = json.loads( snapshot.read_text( encoding="utf-8" ) )
    scene = rel( SCENE )
    original.pop( scene, None )
    changed = sorted( key for key in set( original ) | set( current_sources )
                      if original.get( key ) != current_sources.get( key ) )
    if changed:
        shown = ", ".join( changed[:5] )
        raise ValueError( f"{rel( attempt )}: {len( changed )} source asset(s) changed since the bake: {shown}; "
                          "rebuild and bake a new revision" )


LIGHT_FIELDS = {
    "Sandbox.DirectionalLight": ( "LightColor", "SkyColor", "Shadows", "FogStrength" ),
    "Sandbox.PointLight": ( "LightColor", "Radius", "Attenuation", "Shadows" ),
    "Sandbox.SpotLight": ( "LightColor", "Radius", "Attenuation", "Shadows", "ConeInner", "ConeOuter" ),
    "Sandbox.SkyBox2D": ( "SkyMaterial", "Tint", "SkyIndirectLighting" ),
    "Sandbox.GradientFog": ( "Color", "StartDistance", "EndDistance", "FalloffExponent", "Height", "VerticalFalloffExponent" ),
    "Sandbox.VolumetricFogVolume": ( "Bounds", "Strength", "Color", "FalloffExponent" ),
}


def light_digest( scene ):
    """ A hash of what lights a bake, whoever wrote the scene: the sun, the sky, the fog and haze, and every light's
    place, colour, reach and shadows. The editor saves every field and its own number formats, the generator a few, so
    only these values count, as numbers rounded to 1/1000. """
    def value( v ):
        if isinstance( v, dict ):
            return { k: value( x ) for k, x in sorted( v.items() ) if not k.startswith( "__" ) }
        if isinstance( v, str ):
            try:
                return [ round( float( c ), 3 ) for c in v.split( "," ) ]
            except ValueError:
                return v.lower()
        if isinstance( v, ( int, float ) ) and not isinstance( v, bool ):
            return round( float( v ), 3 )
        return v
    rows = []

    def walk( objects, path ):
        for o in objects:
            if not o.get( "Enabled", True ):
                continue
            name = f"{path}/{o.get( 'Name' )}"
            for c in o.get( "Components", [] ):
                fields = LIGHT_FIELDS.get( c.get( "__type" ) )
                if fields and c.get( "__enabled", True ):
                    rows.append( ( name, c["__type"], value( o.get( "Position", "0,0,0" ) ), value( o.get( "Rotation", "0,0,0,1" ) ),
                                   { f: value( c.get( f ) ) for f in fields } ) )
            walk( o.get( "Children", [] ), name )
    walk( [ o for o in scene["GameObjects"] if o.get( "Name" ) in ( "Sun", "Sky", "Fog", "Lights", "Volumetric Fog" ) ], "" )
    return hashlib.sha256( json.dumps( sorted( rows, key=lambda r: ( r[0], r[1] ) ), sort_keys=True ).encode() ).hexdigest()


def latest_complete( key, revision, expected ):
    attempts = sorted( ( RUNS / revision ).glob( f"{key}-*" ) )
    for attempt in reversed( attempts ):
        status = attempt / "bake-status.txt"
        result = attempt / "bake-result.json"
        if not status.is_file() or not result.is_file():
            continue
        if status.read_text( encoding="utf-8" ).strip() != f"Complete {expected}":
            continue
        data = json.loads( result.read_text( encoding="utf-8" ) )
        if data.get( "Passes" ) == 2 and data.get( "SavedFinalIrradiance" ) is True and data.get( "Grid" ) == expected \
                and data.get( "Volume" ) == key and data.get( "InputAssetsUnchanged" ) is True:
            return attempt, data
    raise ValueError( f"{key}: no completed two-pass bake of {revision} in {RUNS / revision}" )


def preserve( args ):
    config = load_config()
    revision = config["revision"]
    ids = scene_ids()
    scene = json.loads( SCENE.read_text( encoding="utf-8" ) )
    top = { o.get( "Name" ): o for o in scene["GameObjects"] }
    prefix = f"lighting/riverdale/{revision}/"
    # The indirect light: every planned volume baked, its textures this revision's, read back from the saved scene.
    group = top.get( "Indirect Light" ) or {}
    by_name = { c.get( "Name" ): c for c in group.get( "Children", [] ) }
    bakes = {}
    children = []
    current_sources = source_hashes()
    for v in config["volumes"]:
        attempt, result = latest_complete( v["key"], revision, v["expected_counts"] )
        verify_bake_inputs( attempt, current_sources )
        obj = json.loads( json.dumps( by_name[v["name"]] ) )
        component = next( c for c in obj["Components"] if c["__type"] == "Sandbox.IndirectLightVolume" )
        if component.get( "BakeVersion" ) != 1:
            raise ValueError( f"{v['name']}: not baked in the saved scene" )
        for field in TEXTURES:
            component[field] = texture_path( component[field], prefix + v["key"] + "_" )
        if component["Bounds"] != { "Mins": v["bounds_min"], "Maxs": v["bounds_max"] } and \
                [ [ float( c ) for c in component["Bounds"][k].split( "," ) ] for k in ( "Mins", "Maxs" ) ] != \
                [ [ float( c ) for c in v[k].split( "," ) ] for k in ( "bounds_min", "bounds_max" ) ]:
            raise ValueError( f"{v['name']}: its bounds differ from the plan" )
        obj["__guid"] = ids( f"indirect/{v['key']}" )
        component["__guid"] = ids( f"indirect/{v['key']}/volume" )
        children.append( obj )
        bakes[v["key"]] = { "attempt": rel( attempt ), "result": result,
                            "light_digest": light_digest( json.loads( ( attempt / "visual-scene.json" ).read_text( encoding="utf-8" ) ) ) }
    digests = { b["light_digest"] for b in bakes.values() }
    if len( digests ) != 1:
        raise ValueError( "the volumes were baked under different lights: bake them again in one go" )
    if light_digest( scene ) != next( iter( digests ) ):
        raise ValueError( "the scene's sun, sky, fog, haze or lights changed since the bake; bake a new revision" )
    indirect = group_json( ids( "indirect" ), "Indirect Light", children )
    # The reflections, when every planned probe has its captured cube.
    probes = top.get( "Reflection Probes" ) or {}
    by_name = { c.get( "Name" ): c for c in probes.get( "Children", [] ) }
    reflections = None
    try:
        out = []
        for r in config["reflections"]:
            obj = json.loads( json.dumps( by_name[r["name"]] ) )
            component = next( c for c in obj["Components"] if c["__type"] == "Sandbox.EnvmapProbe" )
            if component.get( "Mode" ) != "CustomTexture":
                raise ValueError( f"{r['name']}: not static" )
            component["Texture"] = texture_path( component["Texture"], prefix + "reflection_" + r["key"] )
            short = r["name"].removeprefix( "Probe " )
            obj["__guid"] = ids( f"probe/{short}" )
            component["__guid"] = ids( f"probe/{short}/probe" )
            out.append( obj )
        reflections = group_json( ids( "probes" ), "Reflection Probes", out )
    except ( KeyError, ValueError, FileNotFoundError, StopIteration ) as error:
        if not args.indirect_only:
            raise ValueError( f"reflections aren't all captured and applied ({error}); pass --indirect-only to keep the bake alone" )
        print( f"reflections left out: {error}" )
    manifest = { "revision": revision, "engine": ENGINE, "preserved_at_utc": datetime.now( timezone.utc ).isoformat(),
                 "volumes": bakes, "light_digest": digests.pop(), "reflections": reflections is not None,
                 "source_sha256": current_sources,
                 "rebake": "Bake again (a new revision) after changing geometry, materials, the sky or any light." }
    write_json( INDIRECT_CACHE, indirect )
    if reflections is not None:
        write_json( REFLECTIONS_CACHE, reflections )
    elif REFLECTIONS_CACHE.is_file():
        # An indirect-only pass must never resurrect an old set of captured cubes
        # on the generator's next run.
        REFLECTIONS_CACHE.unlink()
    write_json( MANIFEST, manifest )
    print( f"kept {len( children )} volumes" + ( f" and {len( reflections['Children'] )} reflection probes" if reflections else "" )
           + f" of {revision}; Tools/riverdale_map.py writes them back on its next run" )


def status( args ):
    if not MANIFEST.is_file():
        print( "no bake kept yet" )
        return 1
    manifest = json.loads( MANIFEST.read_text( encoding="utf-8" ) )
    now = source_hashes()
    changed = sorted( k for k in set( now ) | set( manifest["source_sha256"] ) if now.get( k ) != manifest["source_sha256"].get( k ) )
    lights = light_digest( json.loads( SCENE.read_text( encoding="utf-8" ) ) ) != manifest["light_digest"]
    revision_changed = manifest["revision"] != REVISION
    plan_changed = build_config() != load_config()
    for path in changed[:40]:
        print( f"changed since the bake: {path}" )
    if lights:
        print( "the scene's sun, sky, fog, haze or lights changed since the bake" )
    if revision_changed or plan_changed:
        print( "the lighting revision or planned grid/probe layout changed since the bake" )
    stale = bool( changed or lights or revision_changed or plan_changed )
    print( "current" if not stale else f"stale: {len( changed )} source file(s) changed; bake a new revision" )
    return 0 if not stale else 2


# ---------------------------------------------------------------------------------------------------------------------
# check

def check( args ):
    import numpy as np
    from PIL import Image, ImageDraw
    config = load_config()
    fresh = build_config()
    report = { "config_current": fresh == config, "volumes": [], "reflections": [] }
    if fresh != config:
        print( "config.json differs from the layout: run config" )
    _tools()
    import riverdale_map as M
    import railhead_preview as PV
    models = M.build()
    M.preview_setup()
    solid = [ models[n] for n, _, collide, _ in M.scene_models() if collide and n in models ]
    import railhead_map as R
    aabbs = R.collision_aabbs( solid )
    lo = np.array( [ a[0] for a in aabbs ] )
    hi = np.array( [ a[1] for a in aabbs ] )
    opaque = PV.triangles( list( models.values() ) )
    glass = PV.triangles( list( models.values() ), glass=True )
    tris = np.concatenate( ( opaque[0], glass[0] ) )

    def nearest( p, reach=400.0 ):
        """ Distance from p to the nearest drawn triangle (plan inches), within reach. """
        p = np.asarray( p, float )
        near = ( tris.min( axis=1 ) < p + reach ).all( axis=1 ) & ( tris.max( axis=1 ) > p - reach ).all( axis=1 )
        t = tris[near]
        if not len( t ):
            return reach
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        # Ericson's closest point on a triangle, vectorised.
        ab, ac, ap = b - a, c - a, p - a
        d1, d2 = ( ab * ap ).sum( 1 ), ( ac * ap ).sum( 1 )
        bp = p - b
        d3, d4 = ( ab * bp ).sum( 1 ), ( ac * bp ).sum( 1 )
        cp = p - c
        d5, d6 = ( ab * cp ).sum( 1 ), ( ac * cp ).sum( 1 )
        vc = d1 * d4 - d3 * d2
        vb = d5 * d2 - d1 * d6
        va = d3 * d6 - d5 * d4
        denom = np.where( np.abs( va + vb + vc ) < 1e-12, 1e-12, va + vb + vc )
        v, w = vb / denom, vc / denom
        q = a + ab * v[:, None] + ac * w[:, None]
        cases = [
            ( ( d1 <= 0 ) & ( d2 <= 0 ), a ),
            ( ( d3 >= 0 ) & ( d4 <= d3 ), b ),
            ( ( d6 >= 0 ) & ( d5 <= d6 ), c ),
        ]
        e_ab = ( vc <= 0 ) & ( d1 >= 0 ) & ( d3 <= 0 )
        q = np.where( e_ab[:, None], a + ab * ( d1 / np.where( d1 - d3 == 0, 1e-12, d1 - d3 ) )[:, None], q )
        e_ac = ( vb <= 0 ) & ( d2 >= 0 ) & ( d6 <= 0 )
        q = np.where( e_ac[:, None], a + ac * ( d2 / np.where( d2 - d6 == 0, 1e-12, d2 - d6 ) )[:, None], q )
        e_bc = ( va <= 0 ) & ( ( d4 - d3 ) >= 0 ) & ( ( d5 - d6 ) >= 0 )
        q = np.where( e_bc[:, None], b + ( c - b ) * ( ( d4 - d3 ) / np.where( ( d4 - d3 ) + ( d5 - d6 ) == 0, 1e-12, ( d4 - d3 ) + ( d5 - d6 ) ) )[:, None], q )
        for mask, point in cases:
            q = np.where( mask[:, None], point, q )
        return float( np.sqrt( ( ( q - p ) ** 2 ).sum( 1 ) ).min() )

    def inside_collision( p ):
        p = np.asarray( p, float )
        return bool( ( ( lo <= p ) & ( hi >= p ) ).all( axis=1 ).any() )

    # The volumes' grids: how many probes start inside the collision (the bake relocates or switches those off).
    for v in config["volumes"]:
        nx, ny, nz = ( int( c ) for c in v["expected_counts"].split( "," ) )
        e0, e1, n0, n1, z0, z1 = v["plan_box"]
        es, ns, zs = np.linspace( e0, e1, ny ), np.linspace( n0, n1, nx ), np.linspace( z0, z1, nz )
        grid = np.stack( np.meshgrid( es, ns, zs, indexing="ij" ), -1 ).reshape( -1, 3 )
        buried = 0
        for chunk in np.array_split( grid, max( 1, len( grid ) // 400 ) ):
            inside = ( ( lo[None] <= chunk[:, None] ) & ( hi[None] >= chunk[:, None] ) ).all( axis=2 ).any( axis=1 )
            buried += int( inside.sum() )
        counts = engine_counts( *world_box( v["plan_box"] )[:2], v["probe_density"] )
        row = { "key": v["key"], "grid": v["expected_counts"], "engine_grid": fmt( counts ), "probes": nx * ny * nz,
                "inside_collision": buried, "inside_share": round( buried / ( nx * ny * nz ), 3 ), "spacing": v["spacing"] }
        report["volumes"].append( row )
        print( f"volume {v['key']}: {row['grid']} = {row['probes']} probes, {row['spacing']} apart; {buried} start inside the collision" )

    # The capture points: in open air, clear of everything drawn, inside their own box.
    preview = Path( args.preview ) if args.preview else None
    if preview:
        ( preview / "probes" ).mkdir( parents=True, exist_ok=True )
    faces = [ ( "+n", ( 0, 1, 0 ), ( 1, 0, 0 ), ( 0, 0, 1 ) ), ( "-e (west)", ( -1, 0, 0 ), ( 0, 1, 0 ), ( 0, 0, 1 ) ),
              ( "-n", ( 0, -1, 0 ), ( -1, 0, 0 ), ( 0, 0, 1 ) ), ( "+e (east)", ( 1, 0, 0 ), ( 0, -1, 0 ), ( 0, 0, 1 ) ),
              ( "up", ( 0, 0, 1 ), ( 1, 0, 0 ), ( 0, -1, 0 ) ), ( "down", ( 0, 0, -1 ), ( 1, 0, 0 ), ( 0, 1, 0 ) ) ]
    # Plan faces in the capture script's order: world +x (north), +y (west), -x (south), -y (east), up, down.

    def render_face( eye, forward, right, up, size ):
        eye, forward, right, up = ( np.asarray( x, float ) for x in ( eye, forward, right, up ) )
        focal = size / 2
        xs = ( np.arange( size ) + 0.5 - size / 2 ) / focal
        ys = ( size / 2 - np.arange( size ) - 0.5 ) / focal
        rays = forward + xs[None, :, None] * right + ys[:, None, None] * up
        elevation = rays[..., 2] / np.linalg.norm( rays, axis=2 )
        t = np.clip( elevation * 2.5, 0.0, 1.0 )[..., None]
        image = PV.SKY[0] * ( 1 - t ) + PV.SKY[1] * t
        depth = np.zeros( ( size, size ) )
        PV.rasterise( image, depth, *PV.project( opaque, eye, right, up, forward, focal, size, size ) )
        gimage, gdepth = np.zeros_like( image ), np.zeros_like( depth )
        PV.rasterise( gimage, gdepth, *PV.project( glass, eye, right, up, forward, focal, size, size, both_sides=True ) )
        over = gdepth > depth
        image[over] = image[over] * 0.72 + gimage[over] * 0.28
        return image, depth

    for r in config["reflections"]:
        p = r["capture_plan"]
        e0, e1, n0, n1, z0, z1 = r["plan_box"]
        inside_box = e0 <= p[0] <= e1 and n0 <= p[1] <= n1 and z0 <= p[2] <= z1
        clearance = nearest( p )
        row = { "key": r["key"], "capture_plan": p, "clearance": round( clearance, 1 ), "inside_box": inside_box,
                "inside_collision": inside_collision( p ) }
        if ( preview or r["calibration"] ) and ( not args.only or r["key"] in args.only.split( "," ) or r["calibration"] ):
            size = 160
            sheet = Image.new( "RGB", ( size * 6 + 50, size + 22 ), ( 20, 20, 22 ) )
            draw = ImageDraw.Draw( sheet )
            for k, ( label, forward, right, up ) in enumerate( faces ):
                image, depth = render_face( p, forward, right, up, size )
                sheet.paste( Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) ), ( k * ( size + 10 ), 20 ) )
                draw.text( ( k * ( size + 10 ) + 3, 4 ), label, fill=( 230, 230, 230 ) )
                if label == "up":
                    # The converter calibrates on the face's middle (64 px in on 512, ~37 degrees round the zenith).
                    m = size // 8
                    row["sky_share_up"] = round( float( ( depth[m:-m, m:-m] == 0 ).mean() ), 3 )
            if preview:
                sheet.save( preview / "probes" / f"{r['key']}.png" )
        print( f"probe {r['key']}: clearance {row['clearance']}, in its box {inside_box}, in collision {row['inside_collision']}"
               + ( f", open sky up {row['sky_share_up']}" if "sky_share_up" in row else "" ) )
        report["reflections"].append( row )

    if preview:
        plan_picture( preview / "plan.png", config, models, PV )
    problems = [ r["key"] for r in report["reflections"] if r["clearance"] < 40 or not r["inside_box"] or r["inside_collision"] ]
    calib = next( r for r in report["reflections"] if r["key"] == CALIBRATION )
    if calib.get( "sky_share_up", 0 ) < 0.98:
        problems.append( f"{CALIBRATION} (calibration needs open sky up)" )
    report["problems"] = problems
    out = Path( args.report )
    out.parent.mkdir( parents=True, exist_ok=True )
    write_json( out, report )
    print( f"{len( problems )} problem(s){': ' + ', '.join( problems ) if problems else ''}" )
    return 1 if problems else 0


def plan_picture( path, config, models, PV ):
    """ Straight down, roofs cut at 600: the volumes (cyan), the probe boxes (orange) and capture points. """
    from PIL import ImageDraw
    import numpy as np
    bounds = ( -2500.0, 2500.0, -1950.0, 2650.0 )
    scale = 5.0
    opaque, glass = PV.triangles( list( models.values() ) ), PV.triangles( list( models.values() ), glass=True )
    image = PV.top_down( opaque, glass, bounds, scale, cut=600 ).convert( "RGB" )
    draw = ImageDraw.Draw( image )

    def px( e, n ):
        return ( ( e - bounds[0] ) / scale, ( bounds[3] - n ) / scale )
    for v, colour in zip( config["volumes"], ( ( 80, 220, 255 ), ( 120, 255, 160 ), ( 255, 255, 120 ) ) ):
        e0, e1, n0, n1, _, _ = v["plan_box"]
        draw.rectangle( [ px( e0, n1 ), px( e1, n0 ) ], outline=colour, width=2 )
        draw.text( ( px( e0, n1 )[0] + 4, px( e0, n1 )[1] + 4 ), f"{v['key']} {v['expected_counts']}", fill=colour )
    for r in config["reflections"]:
        e0, e1, n0, n1, _, _ = r["plan_box"]
        draw.rectangle( [ px( e0, n1 ), px( e1, n0 ) ], outline=( 255, 150, 60 ), width=1 )
        x, y = px( *r["capture_plan"][:2] )
        draw.ellipse( [ x - 4, y - 4, x + 4, y + 4 ], fill=( 255, 90, 40 ) )
        draw.text( ( x + 6, y - 6 ), r["key"], fill=( 255, 210, 160 ) )
    image.save( path )
    print( f"wrote {path.relative_to( ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    sub = parser.add_subparsers( dest="command", required=True )
    sub.add_parser( "config", help="write config.json from the map's layout" )
    c = sub.add_parser( "check", help="probe grids, capture points and their views" )
    c.add_argument( "--preview", nargs="?", const=str( AAA / "preview" ), help="write cube sheets and a plan here" )
    c.add_argument( "--report", default=str( AAA / "check-report.json" ) )
    c.add_argument( "--only", help="render only these probes' faces (comma-separated keys; the calibration probe always)" )
    p = sub.add_parser( "preserve", help="keep the finished bake (and reflections) for regeneration" )
    p.add_argument( "--indirect-only", action="store_true", help="keep the indirect light even if reflections aren't done" )
    sub.add_parser( "status", help="is the kept bake still current?" )
    args = parser.parse_args()
    if args.command == "config":
        config = build_config()
        write_json( CONFIG, config )
        for v in config["volumes"]:
            print( f"{v['key']}: {v['bounds_min']} .. {v['bounds_max']}, grid {v['expected_counts']} ({v['probes']} probes, {v['spacing']} apart)" )
        print( f"{len( config['reflections'] )} reflection probes; wrote {CONFIG.relative_to( ROOT )}" )
        return 0
    if args.command == "check":
        return check( args )
    if args.command == "preserve":
        return preserve( args )
    return status( args )


if __name__ == "__main__":
    raise SystemExit( main() or 0 )
