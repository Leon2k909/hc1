"""
Riverdale's proposed light and look for the baked-lighting pass, as data: the sun, the flat ambient, the fog and haze,
the post-processing and the map's lights, each change with its old and new values and why. One list feeds both the
proposal for Tools/riverdale_map.py's owner and the offline renders that check it.

    python Sources/Riverdale/lighting/look_proposal.py --write             # output/riverdale/aaa/lighting/proposal.json
    python Sources/Riverdale/lighting/look_proposal.py --stage-scenes DIR  # current.scene and proposal.scene copies

The aim: a cinematic sunrise that stays readable. The low sun (16 degrees, 33 north of east) is the key; the open sky,
through the baked indirect light, the fill; the hall's lamps, the cyan pool and the control rooms are pockets of their
own colour. Today a flat ambient (the sun's SkyColor, 0.40-0.54, unoccluded) lights every surface alike, indoors and
out, as brightly as the sunlit ground gets from a 16-degree sun (cos 74 = 0.28 of its light), so sunlit and shaded
ground read the same and the hall reads like the yard.

Changes marked before_bake light the indirect-light bake (or might): put them in the scene before
Sources/Riverdale/editor/bake-lighting.cs.txt runs, or bake again. The others are shading-time only.
"""
import argparse
import copy
import json
import re
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "output/riverdale/aaa/lighting"
SCENE = ROOT / "Assets/scenes/maps/Riverdale/riverdale.scene"

DOWN = "0,0.7071068,0,0.7071068"          # Rotation.From( 90, 0, 0 ): a light's forward (+x) pointing straight down

# ( id, where, old, new, before_bake, why ). where: the file and symbol in Tools/ that writes it; the scene object.
SCENE_CHANGES = [
    ( "sun_colour", "Tools/riverdale_map.py SUN_COLOUR (Sun: DirectionalLight.LightColor); also Tools/riverdale_sky.py LIGHT",
      "1.55,1.02,0.58,1", "2.30,1.62,1.05,1", True,
      "The key light, half again as strong and a little less orange (normalised 1:0.70:0.46, about 3300 K, where it was "
      "1:0.66:0.37, about 2600 K). A 16-degree sun in clean air after rain is golden, not deep orange, and it has to "
      "out-shine the sky's fill: the ground it grazes gets cos 74 = 0.28 of it, so at 1.02 green it lit the ground less "
      "than the old flat ambient (0.44). The sky's clouds are lit with the same colour (riverdale_sky.LIGHT): change both "
      "and rebuild the sky." ),
    ( "sun_ambient", "Tools/riverdale_map.py write_scene Sun SkyColor (DirectionalLight.SkyColor)",
      "0.40,0.44,0.54,1", "0.10,0.12,0.16,1", True,
      "A flat ambient reaches every surface alike, unoccluded: inside the hall, under the pipe racks and in the north "
      "lane as much as in the open yard. With the indirect light baked, the sky's light arrives occluded and bounced "
      "through the probes, so this stays only as a floor that keeps the deepest corners off black (Belltower keeps "
      "0.14,0.18,0.24, Spillway 0). Set it before the bake, as Cerro Blanco did, whether or not the bake reads it." ),
    ( "fog_colour", "Tools/riverdale_map.py FOG_COLOUR and the GradientFog's alpha", "1.02,0.86,0.70,0.7", "0.96,0.84,0.72,0.72", False,
      "A slightly less saturated morning haze: the same warm hue, less orange on the domes and towers across from the sun." ),
    ( "fog_start", "Tools/riverdale_map.py write_scene GradientFog.StartDistance", 3000, 2400, False,
      "Aerial perspective a little sooner, so the domes (about 4,400 out), the cooling towers (10,000-14,000) and the "
      "mountains stand in separate layers of depth." ),
    ( "fog_end", "Tools/riverdale_map.py write_scene GradientFog.EndDistance", 90000, 75000, False,
      "With the earlier start, the far mountains still fade before the world's edge." ),
    ( "hall_haze", "Tools/riverdale_map.py HAZE Hall Haze (strength, colour)", "0.35 0.78,0.88,1,1", "0.24 0.80,0.88,0.97,1", True,
      "The hall's air at 0.35 veils its far wall at 55 m (readability across the hall's 2,200 in), and lit by sixteen "
      "lamps it flattens everything to grey. Thinner, the lamps' and the pool's light read as glow in the air instead. "
      "Its hue stays cool against the warm deck lamps." ),
    ( "yard_haze", "Tools/riverdale_map.py HAZE Yard Haze (strength, colour)", "0.06 1,0.86,0.7,1", "0.08 1,0.84,0.66,1", True,
      "A little more humidity after rain, so the low sun shows as shafts between the buildings; still light enough to "
      "see across the yard." ),
    ( "ao", "Tools/riverdale_map.py look_object AmbientOcclusion (Intensity, Radius)", "0.7 110", "0.8 48", False,
      "The baked light now gives the room-scale occlusion. Screen-space AO at a 110 radius smears view-dependent halos "
      "over big flat walls; at 48 it does contact shadow: wall feet, props on the deck, crates, rails (Belltower 60, "
      "Lowtide and Railhead 28)." ),
    ( "grading", "Tools/riverdale_map.py look_object ColorGrading (ColorTempK, BlendFactor)", "6200 0.4", "6400 0.25", False,
      "Let the lights carry the colour (warm sun, cool sky fill, cyan pool, warm lamps) rather than a warm cast over "
      "everything, which muddies the pool's cyan and the shadows' blue." ),
    ( "vignette", "Tools/riverdale_map.py look_object Vignette.Intensity", 0.26, 0.16, False,
      "A shooter needs its screen edges readable (Belltower 0.1)." ),
    ( "bloom", "Tools/riverdale_map.py look_object Bloom (Strength, Threshold)", "0.32 1.15", "0.22 1.4", False,
      "With the stronger sun, sunlit concrete reaches about 1 before the tonemap: a threshold of 1.15 would glow whole "
      "walls. At 1.4 the lamps, beacons, screens, the pool and the sun's glints bloom, not the buildings." ),
    ( "exposure_rate", "Tools/riverdale_map.py look_object Tonemapping.Rate", 1, 1.3, False,
      "A little quicker to adapt through the hall's doors (Belltower 1.5). The range (1.0 to 2.5) stays: the sky was "
      "balanced for it (Tools/riverdale_sky.py EXPOSURE, SHOWN)." ),
]

# The lights, by name (as the scene names them). spot: becomes a SpotLight pointing that way (see "spot_lights").
LIGHT_CHANGES = [
    ( "high_bays", r"^High bay ", "Tools/riverdale_hall.py lights() (HIGH_BAYS)",
      { "LightColor": "1.05,1.18,1.35,1", "Radius": 1100, "Shadows": False, "type": "PointLight" },
      { "LightColor": "1.25,1.28,1.30,1", "Radius": 1500, "type": "SpotLight", "Rotation": DOWN, "ConeInner": 30, "ConeOuter": 60,
        "Shadows": { "High bay -250.0 600.0": True, "High bay 250.0 600.0": True, "High bay -250.0 1350.0": True,
                     "High bay 250.0 1350.0": True } },
      "Real high-bay LEDs throw their light down. As 1100-radius point lights they lit the roof and the walls' tops as "
      "much as the deck, and reached the deck (870 below) at the end of their falloff, so the hall was evenly grey "
      "from floor to roof. Down-pointing spots with the reach to land on the deck light the floor and leave the roof "
      "dark, which is where a hall's depth comes from. About 5800 K instead of 7500 K: the pool is the hall's cool "
      "accent, not every lamp. The four over the pool's flanks cast shadows (the crane, the mast, the railings and "
      "the control rooms' columns throw them across the deck); a spotlight's shadow is one map, not a point light's "
      "six." ),
    ( "control_rooms", r"^Control room ", "Tools/riverdale_hall.py upper_side() Control room",
      { "LightColor": "1.6,1.8,2.1,1", "Radius": 520, "Shadows": True }, { "LightColor": "1.55,1.50,1.40,1" },
      "An occupied control room is lit at 4000-4500 K. At about 9000 K the rooms read as empty grey boxes; warm-white "
      "pockets up on either side frame the cyan pool, and the screens stay the room's cool light." ),
    ( "control_fills", r"^Control fill ", "Tools/riverdale_hall.py upper_side() Control fill",
      { "LightColor": "1.1,1.25,1.45,1", "Radius": 360, "Shadows": False }, { "LightColor": "1.00,0.96,0.90,1", "Radius": 380 },
      "The same white as the room's main light, reaching its corners." ),
    ( "interior_ceilings", r"^(A[12] lamp |B1 passage$|B1 room$|Spawn room )",
      "Tools/riverdale_parts.py ceiling_light( kind='cool' ) via COOL, for the annexes, B1 and the spawn rooms",
      { "LightColor": "0.72,0.82,0.95,1", "type": "PointLight" },
      { "LightColor": "0.95,0.95,0.92,1", "type": "SpotLight", "Rotation": DOWN, "ConeInner": 40, "ConeOuter": 75 },
      "Industrial rooms lit at about 4800 K rather than 8000 K, so they read as lit interiors with their own colour "
      "against the gold outside, not as blue-grey extensions of the shade. Pointing down, they stop lighting the roof "
      "slab and the floor above through it (point lights have no shadows here)." ),
    ( "masts", r"^(Yard|Spawn) mast ", "Tools/riverdale_map.py yard_side() / spawn_side() masts",
      { "LightColor": "1.00,0.80,0.55,1", "Radius": "900 (yard) / 700 (spawn)" },
      { "LightColor": "0.80,0.66,0.48,1", "Radius": "720 (yard) / 560 (spawn)" },
      "At sunrise the floods are still on but the sun out-shines them. At full strength over 900 in they lifted the "
      "yard's shade evenly, which flattened the long shadows; dimmer and shorter they stay a warm accent by their poles." ),
    ( "wall_packs", r"^(?!High bay |Control |Pool |.*beacon|(Yard|Spawn) mast |A[12] lamp |B1 passage$|B1 room$|Spawn room ).*",
      "Tools/riverdale_parts.py wall_light() (every wall pack: warm, cool, cyan)",
      { "type": "PointLight", "Shadows": False },
      { "type": "SpotLight", "aim": "the fixture's out, 60 degrees below level", "ConeInner": 35, "ConeOuter": 70 },
      "Unshadowed point lights shine through walls: a wall pack outside the hall's south wall lit the deck inside, and "
      "the deck lamps on the hall's inner walls lit the courts outside; the bake would keep those leaks. A wall pack is "
      "a downward, forward lamp: as a spotlight aimed out and down from its lens it lights its wall and the ground in "
      "front and nothing behind. Colours stay (WARM 1.00,0.74,0.46 is the sodium-like accent against the cool fill)." ),
    ( "pool", r"^Pool (lamp|glow) ", "Tools/riverdale_hall.py lights()", {}, {},
      "Unchanged: tuned with the user on 2026-10-15 (the pool was too bright)." ),
    ( "beacons", r"beacon", "Tools/riverdale_parts.py beacon()", {}, {}, "Unchanged: small red markers." ),
]

SPOT_TEMPLATE = {
    "__type": "Sandbox.SpotLight", "__enabled": True, "Flags": 0, "Attenuation": 1, "ConeInner": 30, "ConeOuter": 60,
    "Contribution": "Diffuse, Specular, Transmissive", "Cookie": None, "FogMode": "Enabled", "FogStrength": 1,
    "LightColor": "1,1,1,1", "Radius": 500, "ShadowBias": 0, "ShadowHardness": 0.25, "Shadows": False }


def scene_value( scene, name ):
    return next( o for o in scene["GameObjects"] if o.get( "Name" ) == name )


def component( obj, kind ):
    return next( c for c in obj["Components"] if c["__type"] == kind )


def apply( scene ):
    """ The scene with the proposal applied: what the generator would write once its owner has made the changes. Wall
    packs keep their point lights here (their aim is only known to riverdale_parts.wall_light); the offline renderer
    treats spot and point lights alike. """
    s = copy.deepcopy( scene )
    sun = component( scene_value( s, "Sun" ), "Sandbox.DirectionalLight" )
    sun["LightColor"], sun["SkyColor"] = "2.30,1.62,1.05,1", "0.10,0.12,0.16,1"
    fog = component( scene_value( s, "Fog" ), "Sandbox.GradientFog" )
    fog.update( Color="0.96,0.84,0.72,0.72", StartDistance=2400, EndDistance=75000 )
    look = scene_value( s, "Look" )
    component( look, "Sandbox.AmbientOcclusion" ).update( Intensity=0.8, Radius=48 )
    component( look, "Sandbox.ColorGrading" ).update( ColorTempK=6400, BlendFactor=0.25 )
    component( look, "Sandbox.Vignette" ).update( Intensity=0.16 )
    component( look, "Sandbox.Bloom" ).update( Strength=0.22, Threshold=1.4 )
    component( look, "Sandbox.Tonemapping" ).update( Rate=1.3 )
    for haze in scene_value( s, "Volumetric Fog" )["Children"]:
        volume = component( haze, "Sandbox.VolumetricFogVolume" )
        if haze["Name"] == "Hall Haze":
            volume.update( Strength=0.24, Color="0.80,0.88,0.97,1" )
        elif haze["Name"] == "Yard Haze":
            volume.update( Strength=0.08, Color="1,0.84,0.66,1" )
    for obj in scene_value( s, "Lights" )["Children"]:
        name = obj["Name"]
        light = obj["Components"][0]
        if re.match( r"^High bay ", name ):
            spot = dict( SPOT_TEMPLATE, __guid=light["__guid"], LightColor="1.25,1.28,1.30,1", Radius=1500, ConeInner=30, ConeOuter=60,
                         Shadows=name in ( "High bay -250.0 600.0", "High bay 250.0 600.0", "High bay -250.0 1350.0", "High bay 250.0 1350.0" ) )
            obj["Components"] = [ spot ]
            obj["Rotation"] = DOWN
        elif re.match( r"^Control room ", name ):
            light["LightColor"] = "1.55,1.50,1.40,1"
        elif re.match( r"^Control fill ", name ):
            light.update( LightColor="1.00,0.96,0.90,1", Radius=380 )
        elif re.match( r"^(A[12] lamp |B1 passage$|B1 room$|Spawn room )", name ):
            spot = dict( SPOT_TEMPLATE, __guid=light["__guid"], LightColor="0.95,0.95,0.92,1", Radius=light["Radius"], ConeInner=40, ConeOuter=75 )
            obj["Components"] = [ spot ]
            obj["Rotation"] = DOWN
        elif re.match( r"^(Yard|Spawn) mast ", name ):
            light.update( LightColor="0.80,0.66,0.48,1", Radius=round( light["Radius"] * 0.8 ) )
    return s


def lighting_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location( "riverdale_lighting", HERE / "riverdale_lighting.py" )
    module = importlib.util.module_from_spec( spec )
    spec.loader.exec_module( module )
    return module


def proposal( config ):
    RL = lighting_module()
    ids = RL.scene_ids()
    first = config["reflections"][0]
    at = [ float( c ) for c in first["capture_world"].split( "," ) ]
    lo = [ float( c ) - a for c, a in zip( first["bounds_min"].split( "," ), at ) ]
    hi = [ float( c ) - a for c, a in zip( first["bounds_max"].split( "," ), at ) ]
    probe_example = RL.probe_json( ids, "probe/" + first["name"].removeprefix( "Probe " ), first["name"], at, lo, hi, first,
                                   f"lighting/riverdale/{config['revision']}/reflection_{first['key']}.vtex", first["tint"] )
    volumes = []
    for v in config["volumes"]:
        volumes.append( {
            "__type": "Sandbox.IndirectLightVolume", "GameObject": v["name"], "key": v["key"], "bake_order": v["order"],
            "Bounds": { "Mins": v["bounds_min"], "Maxs": v["bounds_max"] }, "ProbeDensity": v["probe_density"],
            "expected_ProbeCounts": v["expected_counts"], "probes": v["probes"], "probe_spacing": v["spacing"],
            "InsideGeometry": "Relocate", "NormalBias": v["normal_bias"], "ViewBias": v["view_bias"], "BlendDistance": v["blend_distance"],
            "RuntimeIntensity": v["runtime_intensity"], "RuntimeContrast": v["runtime_contrast"], "RuntimeSaturation": v["runtime_saturation"],
            "RuntimeTint": "1,1,1,1", "RenderExcludeTags": "", "BakeVersion": "0 before the bake, 1 after",
            "IrradianceTexture": f"lighting/riverdale/{config['revision']}/{v['key']}_irradiance.vtex",
            "DistanceTexture": f"lighting/riverdale/{config['revision']}/{v['key']}_distance.vtex",
            "RelocationTexture": f"lighting/riverdale/{config['revision']}/{v['key']}_relocation.vtex" } )
    probes = [ { "GameObject": r["name"], "key": r["key"], "Position (world)": r["capture_world"], "capture (plan)": r["capture_plan"],
                 "world box": { "Mins": r["bounds_min"], "Maxs": r["bounds_max"] }, "Mode": "CustomTexture", "Projection": "Box",
                 "Priority": r["priority"], "Texture": f"lighting/riverdale/{config['revision']}/reflection_{r['key']}.vtex",
                 "TintColor": f"{r['tint']:g},{r['tint']:g},{r['tint']:g},1", "capture exposure": r["exposure"],
                 "fallback TintColor before capture": f"{r['fallback_tint']:g}", "calibration": r["calibration"] }
               for r in config["reflections"] ]
    return {
        "area": "lighting",
        "summary": "Bake indirect light (three DDGI volumes) and capture twelve static reflection cubes in the editor, after a "
                   "sunrise grade that makes the low sun the key light, the baked sky the fill, and the hall's lamps, control "
                   "rooms and cyan pool pockets of their own colour. Every value below has its old value and reason.",
        "how_to_read": "old/new are as Tools/ writes them today and should write them. before_bake: put it in the scene before "
                       "Sources/Riverdale/editor/bake-lighting.cs.txt runs (it lights the bake, or might); otherwise shading-time "
                       "only, safe to tune after. Plan coordinates e,n,z; world ( n, -e, z ).",
        "scene_changes": [ { "id": i, "where": w, "old": o, "new": n, "before_bake": b, "why": y } for i, w, o, n, b, y in SCENE_CHANGES ],
        "light_changes": [ { "id": i, "names": rx, "where": w, "old": o, "new": n, "before_bake": bool( n ), "why": y }
                           for i, rx, w, o, n, y in LIGHT_CHANGES ],
        "spot_lights": {
            "why": "The generator writes every LIGHTS entry as a PointLight (riverdale_map.write_scene). Two changes above need "
                   "SpotLights: the high bays and interior ceiling lights pointing down, the wall packs out and down.",
            "generator_change": [
                "riverdale_parts.LIGHTS entries gain an optional 6th element, a dict: { 'spot': ( dx, dy, dz ) plan direction, "
                "'inner': degrees, 'outer': degrees }.",
                "wall_light(): append { 'spot': tuple( out * 0.5 - UP * 0.866 ), 'inner': 35, 'outer': 70 } (60 degrees below level, "
                "out from the lens). ceiling_light(): { 'spot': ( 0, 0, -1 ), 'inner': 40, 'outer': 75 }. riverdale_hall.lights() high "
                "bays: { 'spot': ( 0, 0, -1 ), 'inner': 30, 'outer': 60 }, radius 1500.",
                "write_scene(): for an entry with 'spot', the GameObject's Rotation is K.angles_rotation( pitch, yaw ) with world "
                "d = K.to_world( spot ) normalised, pitch = degrees( asin( -d.z ) ), yaw = degrees( atan2( d.y, d.x ) ); its component "
                "is the SpotLight below (keys from Lowtide's saved warehouse spots, which the engine wrote)."
            ],
            "component": SPOT_TEMPLATE,
            "straight_down_rotation": DOWN,
            "shadow_budget": "6 shadowed lights after the change (the two control rooms' as now, four high bays); each spotlight "
                             "shadow is one map where a point light's is six."
        },
        "indirect_light": {
            "bake": "Sources/Riverdale/editor/bake-lighting.cs.txt, once per volume, in bake_order: the yard, the hall, the pool. "
                    "Each later bake sees the earlier volumes' light (the cubemapper captures with every other baked volume), "
                    "so the hall sees the yard's light through its doors and the pool the hall's.",
            "why_these_volumes": [
                "yard: the whole play area 16 past its edges, z 2 to 578 (every roof but the hall's; receivers are sampled 20 up "
                "their normal, so the ground at 0 is inside). The engine caps a side at 40 probes, so 35 x 38 x 6 = 7,980 about "
                "125 apart, Belltower's and Cerro Blanco's spacing. It covers the hall too; inside, the hall's smaller volume "
                "wins. Above 578 the hall's outer walls blend over 120 to the sky's light.",
                "hall: the reactor hall's inside, 16 into its walls, deck and roof, 19 x 17 x 9 = 2,907. A short blend (24) so "
                "its own light holds right up to its walls; a long one would fade to the yard's coarse probes inside it (and to "
                "the sky's light above 578).",
                "pool: the fuel pool from its floor to 8 over the deck, 10 x 10 x 6 = 600. Without it the liner under the water "
                "gets the open sky's light; with it, the pool lamps' bounce."
            ],
            "volumes": volumes,
            "scene_json": "The kept group is Sources/Riverdale/lighting/indirect.json (riverdale_lighting.py preserve writes it from "
                          "the saved scene, ids from riverdale_map's SceneIds: indirect, indirect/<key>, indirect/<key>/volume; "
                          "texture fields as plain resource paths). Its shape is Belltower's Sources/Belltower/lighting/indirect.json: "
                          "an 'Indirect Light' GameObject at the origin whose children each hold one IndirectLightVolume.",
            "runtime": "RuntimeIntensity (yard 1.6, hall 1.8, pool 1.2), RuntimeContrast and RuntimeSaturation are shading-time: "
                       "tune them in review without baking again (Belltower 2, Railhead 2.4, Cerro Blanco 1.4, Collider 1.6).",
            "scene_json_example": RL.planned_indirect_object( ids, baked=True ),
            "scene_json_note": "Exactly what the kept indirect.json holds after a bake (ids from riverdale_map's SceneIds). "
                               "riverdale_lighting.planned_indirect_object( ids ) gives the unbaked form (BakeVersion 0, textures "
                               "null), which the generator may write before the first bake instead of prepare-lighting adding it."
        },
        "reflections": {
            "plan": "Twelve static CustomTexture probes on cubes captured as ordinary camera faces "
                    "(Sources/Riverdale/editor/capture-reflections.cs.txt), turned into linear panoramas offline "
                    "(Sources/Riverdale/lighting/riverdale_reflections.py: the engine's ACES taken back exactly, calibrated on the west "
                    "yard's open sky against the sky's own EXR), compiled by the sky asset compiler (import-reflections.cs.txt) "
                    "and assigned (apply-reflections.cs.txt). Collider's and Cerro Blanco's accepted method.",
            "why_not_realtime": "Riverdale's nine probes were realtime (RenderDynamically): each runs the engine's envmap filtering "
                                "as the map loads, which faulted envmap_filtering_cs (VK_ERROR_DEVICE_LOST) twice in the last eight "
                                "GPU crashes. EnvmapProbe.Bake and the GPU Quality GGX filter fault the same shader, so nothing here "
                                "bakes a probe in the engine.",
            "why_not_only_the_sky_cube": "Orion uses the sky's own compiled cube as one static probe. That suits an open yard but "
                                         "puts a bright blue sky in the reactor hall's, the control rooms' and the annexes' "
                                         "floors and glass. The sky cube is only the stand-in until the captures exist (dimmed to "
                                         "0.1-0.15 indoors).",
            "changes_from_the_old_probes": [
                "The single yard probe stood at plan 0,-1000,200, inside B1's core (e -160..160, n -1040..-700, up to 440): its "
                "cube would have been the inside of a concrete box. The yard is split at e 0 into West and East Yard, captured "
                "at plan -1250/1250,-880,170.",
                "The courts and the spawn strips (e beyond 1040, n -240..2040) had no probe; West and East Court cover them.",
                "North moves to plan -370,2330,170, off the pipe rack's columns (it was 55 from one).",
                "Capture points were checked against every drawn triangle (40 clear at least) and rendered flat from each face: "
                "output/riverdale/aaa/lighting/preview/probes/<key>.png."
            ],
            "probes": probes,
            "scene_json": "The kept group is Sources/Riverdale/lighting/reflections.json (the 'Reflection Probes' GameObject; probe "
                          "ids as riverdale_map's probe_object: probe/<name without 'Probe '> and probe/<name>/probe).",
            "scene_json_example": probe_example
        },
        "generator_integration": {
            "summary": "Tools/riverdale_map.py rewrites the scene whole, so it has to write the kept lighting back. Its owner adds:",
            "code": [
                "import importlib.util",
                "def lighting():",
                "    spec = importlib.util.spec_from_file_location( 'riverdale_lighting', K.ROOT / 'Sources/Riverdale/lighting/riverdale_lighting.py' )",
                "    module = importlib.util.module_from_spec( spec )",
                "    spec.loader.exec_module( module )",
                "    return module",
                "",
                "# in write_scene(), in place of the Reflection Probes group:",
                "RL = lighting()",
                "probe_group = RL.reflection_probes_object( RL.sky_fallback_texture( copy=True ), ids ) \\",
                "    or K.game_object( ids, 'Reflection Probes', 'probes', children=[ probe_object( *p ) for p in probe_list ] )",
                "# and after the Volumetric Fog group:",
                "indirect = RL.indirect_light_object()",
                "objects += [ indirect ] if indirect else []"
            ],
            "notes": [
                "reflection_probes_object() returns the kept, captured probes once preserve has run; before that, with the sky's "
                "compiled cube, the planned probes static on it (dimmed indoors); without a compiled sky, None (the old probes).",
                "probe_object()'s RenderDynamically=True (realtime) should go either way: the fallback path makes every probe static.",
                "riverdale_lighting.py imports nothing from Tools at load; its config/check commands import riverdale_map inside "
                "functions only.",
                "After any change to geometry, materials, the sky or a light, `riverdale_lighting.py status` reports the kept bake "
                "stale: bake a new revision (daylight-v2: change REVISION, run `config`)."
            ]
        },
        "optional": [
            { "id": "wet_ground_probes",
              "what": "Orion's after-rain trick: thin static probes over the open yard's ground only (box z -20..3, priority 3) on the "
                      "west/east yard cubes at TintColor 1.6, so the wet ground and puddles mirror the yard more strongly than walls do.",
              "why_optional": "Only worth it once the surfaces owner's wet ground (low roughness, puddles) is in; on dry-looking "
                              "concrete it would read as a sheen." },
            { "id": "colour_adjustments",
              "what": "A ColorAdjustments component on Look with Saturation 1.05 (Contrast 1.0, Brightness 1.0).",
              "why_optional": "A touch more colour in the sunrise; keep Contrast at 1: it works in linear HDR and crushed Orion's shadows." },
            { "id": "sun_elevation",
              "what": "Raise the sun from 16 to about 22-24 degrees, same azimuth (riverdale_map SUN_PITCH and riverdale_sky, whose "
                      "owner rebuilds the sky), before the bake.",
              "measured": sunlit_ground(),
              "why_optional": "Measured against the map's collision (2,008 samples of open ground, 75 in apart): at 16 degrees the "
                              "hall (1,040 high) and the annexes put all but 8% of the open ground in shade, so the yard is lit almost "
                              "only by the sky and reads blue-grey wherever a player stands. At 24 degrees 20% is in sun, with "
                              "shadows still 2.2 times their buildings' height: still a low, golden sun, with sunlit ground to read "
                              "against. The sky and the reference picture's mood are the sky owner's call." }
        ],
        "verification": {
            "editor_scripts": "Sources/Riverdale/lighting/check-scripts.py: all five scripts compile as run_csharp's method bodies against "
                              "the installed engine, and all 29 internal members they reach by reflection are in Sandbox.Engine.dll "
                              "with the parameter counts used (output/riverdale/aaa/lighting/native-script-types/report.json). Not run "
                              "in the editor.",
            "plan": "riverdale_lighting.py check: 0 problems; every capture point at least 70 in from any drawn triangle, inside its box, "
                    "outside the collision; the calibration probe's upward face 98.8% open sky (check-report.json, preview/).",
            "reflection_converter": "riverdale_reflections.py --selftest: faces made from the sky EXR through the engine's ACES come back "
                                    "with scale 1.0002, median error 0.5%, 95th percentile 2.3% (reflection-selftest/).",
            "look": "Cycles renders of the current scene and the proposal applied to a copy (render/compare_e1.0.png, compare_e1.8.png; "
                    "Sources/Riverdale/lighting/render_look.py, which also keeps RenderType Off models from casting, as in a match, and "
                    "renders SpotLights as spots). Cycles bounces light, so these stand for the baked result, not today's flat ambient."
        }
    }


def sunlit_ground():
    path = OUT / "sunlit-ground.json"
    return json.loads( path.read_text( encoding="utf-8" ) ) if path.is_file() else None


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--write", action="store_true", help="write output/riverdale/aaa/lighting/proposal.json" )
    parser.add_argument( "--stage-scenes", metavar="DIR", help="write current.scene and proposal.scene copies here" )
    args = parser.parse_args()
    if args.write:
        config = json.loads( ( HERE / "config.json" ).read_text( encoding="utf-8" ) )
        OUT.mkdir( parents=True, exist_ok=True )
        ( OUT / "proposal.json" ).write_text( json.dumps( proposal( config ), indent=2 ) + "\n", encoding="utf-8" )
        print( f"wrote {( OUT / 'proposal.json' ).relative_to( ROOT )}" )
    if args.stage_scenes:
        out = Path( args.stage_scenes )
        out.mkdir( parents=True, exist_ok=True )
        scene = json.loads( SCENE.read_text( encoding="utf-8" ) )
        ( out / "current.scene" ).write_text( json.dumps( scene, indent=1 ), encoding="utf-8" )
        ( out / "proposal.scene" ).write_text( json.dumps( apply( scene ), indent=1 ), encoding="utf-8" )
        print( f"wrote {out / 'current.scene'} and {out / 'proposal.scene'}" )


if __name__ == "__main__":
    main()
