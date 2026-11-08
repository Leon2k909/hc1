"""Physics rays through Reef Hall's stairs, from the real editor scene, before / after / reverted.

The stairs' collision is the generator's own (step boxes and rail hulls in the reefhall_*_hulls_* models); the standalone stair
models carry no physics. So every ray below must hit exactly the same place before and after the install and after a revert.

    python rays.py before|after|reverted

Read-only: it addresses the 'reefhall' editor session by name (it does not bring it to the front, move the camera or change the
scene), so it needs no editor lock. Results go to rays_<label>.json next to this file; for after / reverted it compares with
rays_before.json and exits 1 if any ray differs.

Rays are written in plan coordinates (e, n, z) and sent in world coordinates (n, -e, z): the lobby's two flights (a tread-by-tread
sweep, the handrail hulls from above and from the side, the head's end wall, the foot), the control flight (the same, its open
side too) and a coarse grid of vertical rays over the rest of both rooms' floors.
"""
import json
import sys
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
sys.path.insert( 0, str( HERE.parent / "lobby-rail-v1" ) )
import editor as eh   # noqa: E402

eh.OUT = eh.ROOT / "output/model-trial-20261106/reefhall_office_partitions"
eh.SNIPPETS = eh.OUT / "snippets"

import math
import math
import math
Z0, Z1 = 208.0, 380.0
RUNS = {   # name: ( start e, start n, along e? , length, gap )
    "A": ( 1880.0, 720.0, True, 370.0, ( 120.0, 200.0 ) ),
    "B": ( 2250.0, 720.0, False, 180.0, ( 60.0, 130.0 ) ),
}


def world( e, n, z ):
    return ( n, -e, z )


def ray( a, b ):
    return [ *world( *a ), *world( *b ) ]


def all_rays():
    out = []
    for name, ( e0, n0, along_e, length, gap ) in RUNS.items():
        def P( u, w, z, e0=e0, n0=n0, along_e=along_e ):
            return ( e0 + u, n0 + w, z ) if along_e else ( e0 + w, n0 + u, z )
        for k in range( int( length // 15 ) + 1 ):                   # horizontal rays through the wall at three heights, every 15 in
            u = 5.0 + k * 15.0
            if u > length:
                break
            for z in ( 230.0, 300.0, 370.0 ):
                out.append( ( f"{name} across u={u:g} z={z:g}", ray( P( u, -40.0, z ), P( u, 40.0, z ) ) ) )
                out.append( ( f"{name} back u={u:g} z={z:g}", ray( P( u, 40.0, z ), P( u, -40.0, z ) ) ) )
        for u in ( 10.0, 60.0, 100.0, 118.0, 122.0, 160.0, 198.0, 202.0, 240.0, 330.0 ):     # down onto the head, rails and floor
            if u <= length:
                for w in ( -2.0, 0.0, 2.0 ):
                    out.append( ( f"{name} down u={u:g} w={w:g}", ray( P( u, w, 500.0 ), P( u, w, 190.0 ) ) ) )
        for u in ( 0.0, length ):                                    # along the wall from beyond its ends
            out.append( ( f"{name} along from {u:g}", ray( P( u - 60.0 if u == 0.0 else u + 60.0, 0.0, 300.0 ), P( length / 2, 0.0, 300.0 ) ) ) )
    for e in range( 1760, 2300, 40 ):                                # a grid over the office floor
        for n in range( 730, 900, 40 ):
            out.append( ( f"office grid {e},{n}", ray( ( float( e ), float( n ), 500.0 ), ( float( e ), float( n ), 190.0 ) ) ) )
    return out


CODE = '''
var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) return new string[] { "no reefhall session" };
var scene = session.Scene;
var rays = System.Text.Json.JsonSerializer.Deserialize<double[][]>( System.IO.File.ReadAllText( @"__RAYS__" ) );
var res = new System.Collections.Generic.List<string>();
foreach ( var r in rays )
{
    var a = new Vector3( (float) r[0], (float) r[1], (float) r[2] );
    var b = new Vector3( (float) r[3], (float) r[4], (float) r[5] );
    var tr = scene.Trace.Ray( a, b ).Run();
    res.Add( tr.Hit ? $"{tr.HitPosition.x:F2},{tr.HitPosition.y:F2},{tr.HitPosition.z:F2}|{tr.Normal.x:F2},{tr.Normal.y:F2},{tr.Normal.z:F2}" : "-" );
}
return res.ToArray();
'''


def main( label ):
    rays = all_rays()
    eh.SNIPPETS.mkdir( parents=True, exist_ok=True )
    data = eh.SNIPPETS / f"rays_{label}_input.json"
    data.write_text( json.dumps( [ r for _, r in rays ] ) )
    got = eh.script( CODE.replace( "__RAYS__", str( data ) ), f"rays_{label}.cs" )
    if not isinstance( got, list ) or len( got ) != len( rays ):
        raise SystemExit( f"unexpected answer from the editor: {str( got )[:400]}" )
    result = { name: hit for ( name, _ ), hit in zip( rays, got ) }
    hits = sum( 1 for h in got if h != "-" )
    print( f"{label}: {len( rays )} rays, {hits} hit something" )
    ( HERE / f"rays_{label}.json" ).write_text( json.dumps( result, indent=0 ) )
    if label == "before":
        return
    base = json.loads( ( HERE / "rays_before.json" ).read_text() )
    differ = [ ( k, base[k], result.get( k ) ) for k in base if base[k] != result.get( k ) ]
    if differ:
        print( f"{len( differ )} of {len( base )} rays differ from before, first few:" )
        for item in differ[:12]:
            print( "  ", item )
        sys.exit( 1 )
    print( f"IDENTICAL to before: all {len( base )} rays hit the same points with the same normals" )


if __name__ == "__main__":
    main( sys.argv[1] )
