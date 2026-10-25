"""Belltower: stage the square's oak out of the map (the user, 2026-10-25: is it "out of place? remove if so").

The tree at plan (-560, 450), and its east mirror at (560, 450), stood in the square's north corners, 90 from the
west (east) house's shopfront and 100 from the north house's. Its crown is ~336 across, so it went ~6 ft into both
fronts, over their shop doors and windows.

Each tree is two things, both removed here from copies of the installed files:
- the "Oak tree" GameObject (Facepunch's medium oak) under the scene's "Trees and planting";
- its trunk's collision: one 7-sided hull (radius 12, 0 to 204.6 high) in belltower_west/east_hulls_wood.obj. Its 14
  vertices go, with its faces, and the later faces' indices are shifted down to match.
Nothing else in either file changes. Writes stage/ and a manifest of hashes; import-square-tree-removal.cs.txt
(Sources/Belltower/editor) publishes them."""
import hashlib, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCENE = ROOT / "Assets/scenes/maps/Belltower/belltower.scene"
MODELS = ROOT / "Assets/models/maps/belltower"
STAGE = HERE / "stage"

# Plan (e, n): world ( n, -e ), the OBJ's axes ( world y, z, world x ).
TREES = { "west": ( -560.0, 450.0 ), "east": ( 560.0, 450.0 ) }
GUIDS = { "west": "a2cf0f21-f175-5b6c-94ad-94300a71ecf6", "east": "9a1251cb-0d48-56aa-b411-e2c809353afc" }
TRUNK_R, TRUNK_TOP, SIDES = 12.0, 330 * 0.62, 7

sha = lambda data: hashlib.sha256( data ).hexdigest()


def stage_scene():
    raw = SCENE.read_bytes()
    scene = json.loads( raw.decode( "utf-8" ) )
    dump = lambda s: json.dumps( s, indent=2 ).replace( "\n", "\r\n" ).encode( "utf-8" )
    assert dump( scene ) == raw, "the scene no longer round-trips through json.dumps; stage it another way"
    foliage = next( o for o in scene["GameObjects"] if o.get( "Name" ) == "Trees and planting" )
    removed = []
    for side, guid in GUIDS.items():
        e, n = TREES[side]
        match = [ o for o in foliage["Children"] if o["__guid"] == guid ]
        assert len( match ) == 1, ( side, "tree not found" )
        tree = match[0]
        x, y, z = map( float, tree["Position"].split( "," ) )
        model = tree["Components"][0]["Model"]["Path"]
        assert tree["Name"] == "Oak tree" and ( x, y, z ) == ( n, -e, 0.0 ), tree
        assert model == "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl", model
        foliage["Children"].remove( tree )
        removed.append( { "side": side, "guid": guid, "position": tree["Position"], "scale": tree["Scale"] } )
    assert guid not in json.dumps( scene )
    return raw, dump( scene ), removed


def stage_hulls( side ):
    path = MODELS / f"belltower_{side}_hulls_wood.obj"
    raw = path.read_bytes()
    lines = raw.split( b"\n" )
    vertex_lines = [ k for k, line in enumerate( lines ) if line.startswith( b"v " ) ]
    vertices = [ tuple( map( float, lines[k].split()[1:4] ) ) for k in vertex_lines ]
    e, n = TREES[side]
    # The trunk's 14 vertices as map_kit wrote them: the bottom ring, then the top. The west's ring is the plan points
    # ( e + r cos a, n + r sin a ); the east half is the west mirrored, e to -e, in the same order.
    flip = 1.0 if side == "west" else -1.0
    want = []
    for z in ( 0.0, TRUNK_TOP ):
        for k in range( SIDES ):
            a = 2 * math.pi * k / SIDES
            pe = flip * ( -abs( e ) + TRUNK_R * math.cos( a ) )
            want.append( ( -pe, z, n + TRUNK_R * math.sin( a ) ) )
    starts = [ i for i in range( len( vertices ) - 2 * SIDES + 1 )
               if all( max( abs( a - b ) for a, b in zip( vertices[i + j], want[j] ) ) < 0.01 for j in range( 2 * SIDES ) ) ]
    assert len( starts ) == 1, ( side, "trunk hull", starts )
    first = starts[0] + 1                       # OBJ indices are 1-based
    last = first + 2 * SIDES - 1
    skip = set( vertex_lines[starts[0]:starts[0] + 2 * SIDES] )
    out, dropped_faces = [], 0
    for k, line in enumerate( lines ):
        if k in skip:
            continue
        if line.startswith( b"f " ):
            ids = [ int( t ) for t in line.split()[1:] ]
            inside = [ first <= i <= last for i in ids ]
            if all( inside ):
                dropped_faces += 1
                continue
            assert not any( inside ), ( side, "a face shares the trunk's vertices", line )
            line = b"f " + b" ".join( str( i - 2 * SIDES if i > last else i ).encode() for i in ids )
        out.append( line )
    assert dropped_faces >= SIDES + 2 * ( SIDES - 2 ), ( side, dropped_faces )
    return path.name, raw, b"\n".join( out ), { "vertices": [ first, last ], "faces": dropped_faces }


def main():
    STAGE.mkdir( exist_ok=True )
    manifest = { "files": {}, "removed": {} }
    before, after, removed = stage_scene()
    ( STAGE / "belltower.scene" ).write_bytes( after )
    manifest["files"]["scenes/maps/Belltower/belltower.scene"] = { "before": sha( before ), "after": sha( after ) }
    manifest["removed"]["scene"] = removed
    for side in TREES:
        name, before, after, info = stage_hulls( side )
        ( STAGE / name ).write_bytes( after )
        manifest["files"][f"models/maps/belltower/{name}"] = { "before": sha( before ), "after": sha( after ) }
        manifest["removed"][name] = info
    ( STAGE / "manifest.json" ).write_text( json.dumps( manifest, indent=2 ), encoding="utf-8" )
    print( json.dumps( manifest, indent=2 ) )


if __name__ == "__main__":
    main()
