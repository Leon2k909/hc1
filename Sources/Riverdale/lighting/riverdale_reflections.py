"""
Riverdale's reflection cubes from the editor's camera faces: capture-reflections.cs.txt writes six 8-bit faces per
probe (ACES at a fixed exposure); this takes the tonemap back, calibrates on open sky and writes each probe's linear
panorama as an EXR with a sky.shader vmat, which the sky asset compiler turns into a cube (import-reflections.cs.txt).
That route never runs the runtime GGX filter that faulted envmap_filtering_cs on this workstation. Cerro Blanco's method
(Tools/cerroblanco_reflections.py), with a probe list, per-probe exposure and the sky's tint from config.json.

    python Sources/Riverdale/lighting/riverdale_reflections.py [key ...] [--captures DIR] [--stage DIR] [--manifest PATH]
    python Sources/Riverdale/lighting/riverdale_reflections.py --selftest

- Calibration: the calibration probe's upward face (config.json "calibration": the west yard's, open sky) against the
  sky's own EXR times the SkyBox2D tint the capture recorded, over the face's middle (about 37 degrees round the zenith),
  channel by channel; their median is the scale every probe gets. It refuses if the channels disagree by over 12%.
- Each face is undone with belltower_sky's exact inverse of the engine's ACES at the probe's capture exposure.
- Writes output/riverdale/lighting/stage/materials/riverdale/reflections/<revision>/reflection_<key>.exr and .vmat,
  a panorama.png per probe beside its faces (display only), and output/riverdale/lighting/reflection-manifest.json with
  every staged file's hash.
- --selftest makes faces from the sky EXR itself, as the engine would show them, converts them and checks the panorama
  comes back as the sky: the face directions, the projection and the tonemap's inverse, end to end.
"""
import argparse
import ast
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
CONFIG = HERE / "config.json"
RUNS = ROOT / "output/riverdale/lighting"
SKY_EXR = ROOT / "Assets/materials/riverdale/sky/riverdale_sky.exr"
PANORAMA = ( 1024, 2048 )


def sky_functions():
    """ The verified EXR reader and writer and the exact inverse of the engine's ACES, from Tools/belltower_sky.py,
    without importing its sky generation. """
    source = ast.parse( ( ROOT / "Tools/belltower_sky.py" ).read_text( encoding="utf-8" ) )
    names = { "read_exr", "write_exr", "undisplay", "display", "srgb_linear", "aces" }
    constants = { "ACES_IN", "ACES_OUT", "DESIGN_EXPOSURE" }
    selected = [ node for node in source.body
                 if isinstance( node, ast.FunctionDef ) and node.name in names
                 or isinstance( node, ast.Assign ) and any( isinstance( t, ast.Name ) and t.id in constants for t in node.targets ) ]
    namespace = { "np": np, "struct": struct, "zlib": zlib, "Path": Path }
    exec( compile( ast.Module( body=selected, type_ignores=[] ), "verified_sky_io", "exec" ), namespace )
    return namespace


SKY = sky_functions()


def vector( text ):
    return np.array( [ float( v.strip() ) for v in text.split( "," ) ], np.float32 )


def validate( metadata, size ):
    if "ACES" not in metadata.get( "Encoding", "" ) or metadata.get( "CaptureSize" ) != f"{size},{size}":
        raise ValueError( "Reflection faces require the fixed-size ACES camera capture" )
    if metadata.get( "ScreenSpaceOcclusion" ) is not False or metadata.get( "DisplayEffects" ) is not False:
        raise ValueError( "Recapture with display effects disabled: they introduce seams" )
    faces = metadata.get( "Faces", [] )
    if len( faces ) != 6 or sorted( f.get( "Face" ) for f in faces ) != list( range( 6 ) ):
        raise ValueError( "Exactly six uniquely numbered reflection faces are required" )
    for face in metadata["Faces"]:
        number = face["Face"]
        if abs( face["FieldOfView"] - 90 ) >= 0.01 or face["CaptureSize"] != f"{size},{size}":
            raise ValueError( f"Face {number}: recapture with a square 90-degree projection" )
        if face.get( "File" ) != f"face-{number}.png":
            raise ValueError( f"Face {number}: unexpected file name" )
        if not np.allclose( vector( face["Position"] ), vector( metadata["Position"] ), atol=0.5 ):
            raise ValueError( f"Face {number}: the camera moved between faces" )
        basis = np.array( [ vector( face[k] ) for k in ( "Forward", "Right", "Up" ) ] )
        if basis.shape != ( 3, 3 ) or not np.isfinite( basis ).all() or not np.allclose( basis @ basis.T, np.eye( 3 ), atol=0.005 ):
            raise ValueError( f"Face {number}: camera directions are not orthonormal" )


def validate_capture( metadata, config, probe ):
    """Do not generate reusable assets from an earlier scene/revision or probe."""
    if metadata.get( "Revision" ) != config["revision"] or metadata.get( "Key" ) != probe["key"] or metadata.get( "Name" ) != probe["name"]:
        raise ValueError( f"{probe['key']}: captured faces belong to a different revision or probe" )
    if not np.allclose( vector( metadata["Position"] ), vector( probe["capture_world"] ), atol=0.5 ):
        raise ValueError( f"{probe['key']}: capture point differs from the lighting plan" )
    if abs( float( metadata["Exposure"] ) - probe["exposure"] ) > 0.001:
        raise ValueError( f"{probe['key']}: captured at an obsolete exposure; recapture this probe" )
    validate( metadata, config["reflection_capture_size"] )


def face_image( directory, face, exposure, scale ):
    encoded = np.asarray( Image.open( directory / face["File"] ).convert( "RGB" ), np.float32 )
    linear = SKY["undisplay"]( encoded, exposure=exposure ) * scale
    return linear, { "face": face["Face"], "clipped_fraction": float( ( encoded.max( axis=-1 ) >= 254 ).mean() ),
                     "black_fraction": float( ( encoded.max( axis=-1 ) <= 1 ).mean() ) }


def directions_for( face, size ):
    u = ( np.arange( size ) + 0.5 ) / ( size / 2 ) - 1
    v = 1 - ( np.arange( size ) + 0.5 ) / ( size / 2 )
    d = vector( face["Forward"] ) + u[None, :, None] * vector( face["Right"] ) + v[:, None, None] * vector( face["Up"] )
    return d / np.linalg.norm( d, axis=-1, keepdims=True )


def sky_lookup( sky, d ):
    """ The sky panorama's texel in direction d (world), as sky.shader maps it (Cerro Blanco's verified mapping). """
    x = np.mod( -np.arctan2( d[..., 1], d[..., 0] ) / ( 2 * np.pi ), 1 ) * sky.shape[1]
    y = ( 0.5 - np.arcsin( np.clip( d[..., 2], -1, 1 ) ) / np.pi ) * sky.shape[0]
    return sky[np.clip( y.astype( int ), 0, sky.shape[0] - 1 ), x.astype( int ) % sky.shape[1]]


def calibration( config, captures, sky ):
    probe = next( r for r in config["reflections"] if r["calibration"] )
    directory = captures / probe["key"]
    metadata = json.loads( ( directory / "faces.json" ).read_text( encoding="utf-8" ) )
    size = config["reflection_capture_size"]
    validate_capture( metadata, config, probe )
    face = next( f for f in metadata["Faces"] if f["Face"] == 4 )
    observed, _ = face_image( directory, face, metadata["Exposure"], 1.0 )
    tint = vector( metadata.get( "SkyTint", "1,1,1" ) )
    expected = sky_lookup( sky, directions_for( face, size ) ) * tint
    middle = np.s_[size // 8:-size // 8, size // 8:-size // 8]
    channels = np.median( ( expected / np.maximum( observed, 1e-6 ) )[middle].reshape( -1, 3 ), axis=0 )
    scale = float( np.median( channels ) )
    spread = float( np.max( np.abs( channels / scale - 1 ) ) )
    if spread > 0.12 or not 0.05 < scale < 8:
        raise ValueError( f"The sky calibration disagrees across channels: {channels}" )
    report = { "probe": probe["key"], "radiance_scale": scale, "channel_scales": channels.tolist(), "max_channel_deviation": spread,
               "sky_tint": tint.tolist() }
    ( directory.parent / "calibration.json" ).write_text( json.dumps( report, indent=2 ), encoding="utf-8" )
    return scale, report


def panorama( config, probe, captures, stage, scale ):
    revision = config["revision"]
    size = config["reflection_capture_size"]
    directory = captures / probe["key"]
    metadata = json.loads( ( directory / "faces.json" ).read_text( encoding="utf-8" ) )
    validate_capture( metadata, config, probe )
    h, w = PANORAMA
    lat = ( 0.5 - ( np.arange( h, dtype=np.float32 ) + 0.5 ) / h ) * np.pi
    lon = -( np.arange( w, dtype=np.float32 ) + 0.5 ) / w * 2 * np.pi
    directions = np.stack( np.broadcast_arrays( np.cos( lat[:, None] ) * np.cos( lon ), np.cos( lat[:, None] ) * np.sin( lon ),
                                                np.sin( lat[:, None] ) ), axis=-1 )
    best = np.full( ( h, w ), -1, np.float32 )
    result = np.zeros( ( h, w, 3 ), np.float32 )
    diagnostics = []
    for face in sorted( metadata["Faces"], key=lambda f: f["Face"] ):
        image, check = face_image( directory, face, metadata["Exposure"], scale )
        diagnostics.append( check )
        forward, right, up = ( vector( face[k] ) for k in ( "Forward", "Right", "Up" ) )
        denominator = directions @ forward
        selected = denominator > best
        safe = np.maximum( denominator, 1e-5 )
        u = np.clip( ( ( directions @ right ) / safe + 1 ) * size / 2 - 0.5, 0, size - 1 )
        v = np.clip( ( 1 - ( directions @ up ) / safe ) * size / 2 - 0.5, 0, size - 1 )
        x, y = u.astype( np.int32 ), v.astype( np.int32 )
        x1, y1 = np.minimum( x + 1, size - 1 ), np.minimum( y + 1, size - 1 )
        a, b = ( u - x )[..., None], ( v - y )[..., None]
        colour = ( image[y, x] * ( 1 - a ) + image[y, x1] * a ) * ( 1 - b ) + ( image[y1, x] * ( 1 - a ) + image[y1, x1] * a ) * b
        result[selected], best[selected] = colour[selected], denominator[selected]
    if not np.isfinite( result ).all() or best.min() <= 0.5:
        raise ValueError( f"{probe['key']}: invalid radiance or incomplete cubemap coverage" )
    relative = Path( "materials/riverdale/reflections" ) / revision
    out = stage / relative
    out.mkdir( parents=True, exist_ok=True )
    SKY["write_exr"]( out / f"reflection_{probe['key']}.exr", result )
    # Display only; the asset keeps the camera's linear values.
    shown = result / ( 1 + result )
    shown = np.where( shown <= 0.0031308, shown * 12.92, 1.055 * shown ** ( 1 / 2.4 ) - 0.055 )
    Image.fromarray( np.clip( shown * 255, 0, 255 ).astype( np.uint8 ) ).save( directory / "panorama.png" )
    path = ( relative / f"reflection_{probe['key']}.exr" ).as_posix()
    ( out / f"reflection_{probe['key']}.vmat" ).write_text(
        '"Layer0"\n{\n shader "shaders/sky.shader"\n F_TEXTURE_FORMAT2 "6"\n'
        ' g_flBrightnessExposureBias "0"\n g_flRenderOnlyExposureBias "0"\n'
        f' SkyTexture "{path}"\n}}\n', encoding="utf-8" )
    report = { "key": probe["key"], "name": probe["name"], "exposure": metadata["Exposure"], "radiance_max": float( result.max() ),
               "radiance_median": float( np.median( result ) ), "size": [ w, h ], "faces": diagnostics }
    ( directory / "conversion.json" ).write_text( json.dumps( report, indent=2 ), encoding="utf-8" )
    return report, result


def convert( config, keys, captures, stage, manifest_path ):
    available = { r["key"] for r in config["reflections"] }
    if keys and ( unknown := set( keys ) - available ):
        raise ValueError( f"Unknown reflection probe(s): {', '.join( sorted( unknown ) )}" )
    sky = SKY["read_exr"]( SKY_EXR )
    if not np.isfinite( sky ).all():
        raise ValueError( f"Invalid sky radiance: {SKY_EXR}" )
    scale, calibrated = calibration( config, captures, sky )
    probes = [ r for r in config["reflections"] if not keys or r["key"] in keys ]
    reports = [ panorama( config, p, captures, stage, scale )[0] for p in probes ]
    relative = Path( "materials/riverdale/reflections" ) / config["revision"]
    # A selective conversion must never manifest older files left in the staging
    # directory: import-reflections requires a complete, current 12-probe set.
    produced = [ stage / relative / f"reflection_{r['key']}.{ext}"
                 for r in probes for ext in ( "exr", "vmat" ) ]
    files = [ { "path": p.relative_to( stage ).as_posix(), "sha256": hashlib.sha256( p.read_bytes() ).hexdigest() }
              for p in sorted( produced ) ]
    manifest = { "revision": config["revision"], "capture_encoding": "ACES inverse with sky calibration", "radiance_scale": scale,
                 "calibration": calibrated, "captures": reports, "files": files }
    manifest_path.parent.mkdir( parents=True, exist_ok=True )
    manifest_path.write_text( json.dumps( manifest, indent=2 ), encoding="utf-8" )
    return manifest


# ---------------------------------------------------------------------------------------------------------------------

def rotation_vectors( pitch, yaw ):
    """ Rotation.From( pitch, yaw, 0 )'s Forward, Right and Up in s&box's world (x forward, y left, z up). """
    p, y = np.radians( pitch ), np.radians( yaw )
    forward = np.array( ( np.cos( p ) * np.cos( y ), np.cos( p ) * np.sin( y ), -np.sin( p ) ) )
    right = np.array( ( np.sin( y ), -np.cos( y ), 0.0 ) )
    up = np.cross( right, forward )
    return forward, right, up


def selftest( config ):
    """ Faces made from the sky EXR as the engine would show them (tinted, ACES at the probe's exposure, 8 bits) for
    every planned probe, converted back. The panorama should be the tinted sky again. """
    out = ROOT / "output/riverdale/aaa/lighting/reflection-selftest"
    captures, stage = out / "captures", out / "stage"
    sky = SKY["read_exr"]( SKY_EXR )
    tint = np.array( ( 1.0, 1.0, 1.0 ), np.float32 )
    size = config["reflection_capture_size"]
    rotations = [ ( 0, 0 ), ( 0, 90 ), ( 0, 180 ), ( 0, -90 ), ( -90, 0 ), ( 90, 0 ) ]
    for probe in config["reflections"]:
        directory = captures / probe["key"]
        directory.mkdir( parents=True, exist_ok=True )
        faces = []
        for index, ( pitch, yaw ) in enumerate( rotations ):
            forward, right, up = rotation_vectors( pitch, yaw )
            face = { "File": f"face-{index}.png", "Face": index, "FieldOfView": 90, "Position": probe["capture_world"],
                     "CaptureSize": f"{size},{size}", "Forward": ",".join( map( str, forward ) ), "Right": ",".join( map( str, right ) ),
                     "Up": ",".join( map( str, up ) ) }
            radiance = sky_lookup( sky, directions_for( face, size ) ) * tint
            Image.fromarray( SKY["display"]( radiance, exposure=probe["exposure"] ) ).save( directory / face["File"] )
            faces.append( face )
        ( directory / "faces.json" ).write_text( json.dumps( {
            "Key": probe["key"], "Name": probe["name"], "Revision": config["revision"], "Position": probe["capture_world"],
            "Exposure": probe["exposure"], "Encoding": "sRGB; ACES tonemapper; selftest", "ScreenSpaceOcclusion": False,
            "DisplayEffects": False, "SkyTint": ",".join( map( str, tint ) ), "CaptureSize": f"{size},{size}", "Faces": faces } ),
            encoding="utf-8" )
    manifest = convert( config, None, captures, stage, out / "reflection-manifest.json" )
    # Compare where the sky isn't clipped by 8 bits, away from the sun.
    h, w = PANORAMA
    result = SKY["read_exr"]( stage / "materials/riverdale/reflections" / config["revision"] / "reflection_west_yard.exr" )
    lat = ( 0.5 - ( np.arange( h ) + 0.5 ) / h ) * np.pi
    lon = -( np.arange( w ) + 0.5 ) / w * 2 * np.pi
    d = np.stack( np.broadcast_arrays( np.cos( lat[:, None] ) * np.cos( lon ), np.cos( lat[:, None] ) * np.sin( lon ), np.sin( lat[:, None] ) ), -1 )
    truth = sky_lookup( sky, d ) * tint
    shown = SKY["display"]( truth, exposure=next( r for r in config["reflections"] if r["key"] == "west_yard" )["exposure"] )
    ok = shown.max( axis=-1 ) < 250
    error = np.abs( result - truth )[ok] / np.maximum( truth[ok], 1e-3 )
    report = { "radiance_scale": manifest["radiance_scale"], "compared_share": float( ok.mean() ),
               "median_relative_error": float( np.median( error ) ), "p95_relative_error": float( np.percentile( error, 95 ) ),
               "files": len( manifest["files"] ), "probes": len( manifest["captures"] ) }
    ( out / "selftest.json" ).write_text( json.dumps( report, indent=2 ), encoding="utf-8" )
    side = np.concatenate( ( np.asarray( Image.open( captures / "west_yard" / "panorama.png" ).resize( ( 1024, 512 ) ) ),
                             np.asarray( Image.fromarray( shown ).resize( ( 1024, 512 ) ) ) ), axis=0 )
    Image.fromarray( side ).save( out / "selftest.png" )
    print( json.dumps( report, indent=2 ) )
    passed = abs( manifest["radiance_scale"] - 1 ) < 0.03 and report["median_relative_error"] < 0.03 and report["p95_relative_error"] < 0.1
    print( "selftest passed" if passed else "selftest FAILED" )
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "keys", nargs="*", help="only these probes (all by default)" )
    parser.add_argument( "--captures", help="faces folder (default output/riverdale/lighting/reflections/<revision>)" )
    parser.add_argument( "--stage", default=str( RUNS / "stage" ) )
    parser.add_argument( "--manifest", default=str( RUNS / "reflection-manifest.json" ) )
    parser.add_argument( "--selftest", action="store_true" )
    args = parser.parse_args()
    config = json.loads( CONFIG.read_text( encoding="utf-8" ) )
    if args.selftest:
        return selftest( config )
    captures = Path( args.captures ) if args.captures else RUNS / "reflections" / config["revision"]
    manifest = convert( config, set( args.keys ), captures, Path( args.stage ), Path( args.manifest ) )
    print( json.dumps( { "radiance_scale": manifest["radiance_scale"], "probes": [ c["key"] for c in manifest["captures"] ],
                         "files": len( manifest["files"] ) }, indent=2 ) )
    return 0


if __name__ == "__main__":
    sys.exit( main() )
