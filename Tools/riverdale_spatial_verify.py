"""Verify a staged, render-only Riverdale forest split and prepare its safe scene replacement.

    python Tools/riverdale_spatial_verify.py --stage output/riverdale/aaa/spatial-stage

The saved scene and all existing Riverdale models are left alone. We confirm the source tree
OBJ files are byte-identical to those used for the saved lighting bake and that the collection
of all sectors contains every textured/shaded triangle exactly once. The staged scene then
inherits the live scene's other objects verbatim, including every light, clip, spawn, indirect
volume and captured reflection probe; only the render-only tree nodes are substituted.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import map_kit as K

ROOT = K.ROOT
TREE_BASES = ( "riverdale_backdrop_trees", "riverdale_backdrop_trees_near" )
SCENE_REL = Path( "scenes/maps/Riverdale/riverdale.scene" )
MASK = ( 1 << 128 ) - 1


def signature( obj ):
    """Order-independent checksum of every triangle's material, positions, UVs and normals."""
    v, vt, vn = [], [], []
    result = defaultdict( lambda: { "faces": 0, "sum": 0, "xor": 0 } )
    paint = None
    with obj.open( "rb" ) as stream:
        for line in stream:
            line = line.rstrip( b"\r\n" )
            if line.startswith( b"v " ):
                v.append( line[2:] )
            elif line.startswith( b"vt " ):
                vt.append( line[3:] )
            elif line.startswith( b"vn " ):
                vn.append( line[3:] )
            elif line.startswith( b"usemtl " ):
                paint = line[7:].decode( "ascii" )
            elif line.startswith( b"f " ):
                if paint is None:
                    raise ValueError( f"{obj}: unpainted face" )
                corners = []
                for token in line[2:].split():
                    a, b, c = ( int( n ) - 1 for n in token.split( b"/" ) )
                    corners.extend( ( v[a], vt[b], vn[c] ) )
                blob = paint.encode() + b"\x00" + b"\x00".join( corners )
                digest = int.from_bytes( hashlib.blake2b( blob, digest_size=16 ).digest(), "big" )
                row = result[paint]
                row["faces"] += 1
                row["sum"] = ( row["sum"] + digest ) & MASK
                row["xor"] ^= digest
    return result


def merge( rows ):
    merged = defaultdict( lambda: { "faces": 0, "sum": 0, "xor": 0 } )
    for source in rows:
        for paint, row in source.items():
            dest = merged[paint]
            dest["faces"] += row["faces"]
            dest["sum"] = ( dest["sum"] + row["sum"] ) & MASK
            dest["xor"] ^= row["xor"]
    return dict( merged )


def sha( path ):
    with path.open( "rb" ) as stream:
        return hashlib.file_digest( stream, "sha256" ).hexdigest()


def find( scene, name ):
    return next( o for o in scene["GameObjects"] if o.get( "Name" ) == name )


def main():
    parser = argparse.ArgumentParser( description=__doc__ )
    parser.add_argument( "--stage", required=True, type=Path )
    args = parser.parse_args()
    stage = args.stage.resolve()
    assets = ROOT / "Assets"
    orig_dir = assets / "models/maps/riverdale"
    staged_orig_dir = stage / "models/maps/riverdale"
    sector_dir = stage / "models/maps/riverdale_sectors"
    if not sector_dir.is_dir():
        raise FileNotFoundError( f"No staged forest sectors in {sector_dir}" )
    counts = {}
    for base in TREE_BASES:
        original = orig_dir / f"{base}.obj"
        staged = staged_orig_dir / original.name
        if sha( original ) != sha( staged ):
            raise ValueError( f"Original {base}.obj differs from the baked-lighting source; cannot reuse its bake" )
        sectors = sorted( sector_dir.glob( f"{base}_sector_??.obj" ) )
        if len( sectors ) != 8:
            raise ValueError( f"{base}: expected 8 sectors, found {len( sectors )}" )
        for sector in sectors:
            if not sector.with_suffix( ".vmdl" ).is_file() or not sector.with_suffix( ".mtl" ).is_file():
                raise FileNotFoundError( f"Incomplete source model: {sector}" )
        expected = dict( signature( original ) )
        observed = merge( signature( sector ) for sector in sectors )
        if observed != expected:
            raise ValueError( f"{base}: a triangle, UV, normal or paint differs between original and sectors" )
        counts[base] = { "triangles": sum( p["faces"] for p in expected.values() ),
                         "sectors": { s.stem: sum( r["faces"] for r in signature( s ).values() ) for s in sectors } }
        print( f"{base}: {counts[base]['triangles']:,} exact triangles in {len(sectors)} sectors" )
    # Merge from the saved scene, so no editor-authored settings, GUIDs, player clips or baked data are overwritten.
    scene = json.loads( ( assets / SCENE_REL ).read_text( encoding="utf-8" ) )
    proposed = json.loads( ( stage / SCENE_REL ).read_text( encoding="utf-8" ) )
    old_world = find( scene, "Riverdale" )
    new_world = find( proposed, "Riverdale" )
    segments = [ o for o in new_world["Children"] if "_sector_" in o.get( "Name", "" ).lower() ]
    # Names are human-facing; the model resource is the authoritative key.
    segments = [ o for o in new_world["Children"] if any(
        f"{name}_sector_" in json.dumps( o.get( "Components", [] ) ) for name in TREE_BASES ) ]
    if len( segments ) != 16:
        raise ValueError( f"Staged scene has {len(segments)} sector models, expected 16" )
    original_labels = { "Backdrop Trees", "Backdrop Trees Near" }
    if sum( o.get( "Name" ) in original_labels for o in old_world["Children"] ) != 2:
        raise ValueError( "The saved scene's original two tree renderers are missing or duplicated" )
    old_world["Children"] = [ o for o in old_world["Children"] if o.get( "Name" ) not in original_labels ] + segments
    all_ids = [ o["__guid"] for o in old_world["Children"] ]
    if len( all_ids ) != len( set( all_ids ) ):
        raise ValueError( "The new world contains duplicate object identifiers" )
    from_dir = "models/maps/riverdale_sectors/"
    for obj in segments:
        model = next( ( c.get( "Model" ) for c in obj["Components"] if c.get( "__type" ) == "Sandbox.ModelRenderer" ), None )
        path = model.get( "Path" ) if isinstance( model, dict ) else model
        if not isinstance( path, str ) or not path.startswith( from_dir ):
            raise ValueError( f"Unexpected spatial asset reference: {path}" )
        if any( c.get( "__type" ) == "Sandbox.ModelCollider" for c in obj["Components"] ):
            raise ValueError( "Spatial trees may not have collision" )
    output = stage / SCENE_REL
    K.write_text( output, json.dumps( scene, indent=2 ), newline=None )
    report = { "equivalence": "all painted triangles, UVs and normals matched exactly", "source_models_unchanged": True,
               "sectors": 16, "counts": counts, "scene_merged_from": str( assets / SCENE_REL ),
               "preserves_other_scene_objects": True }
    ( stage / "spatial-validation.json" ).write_text( json.dumps( report, indent=2 ) + "\n", encoding="utf-8" )
    print( f"Prepared scene with {len(old_world['Children'])} world models; saved everything else from the active project" )


if __name__ == "__main__":
    main()
