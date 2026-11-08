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

eh.OUT = eh.ROOT / "output/model-trial-20261106/reefhall_stairs"
eh.SNIPPETS = eh.OUT / "snippets"

STEPS, L1 = 26, 208.0
FLIGHTS = {   # name: ( foot e, head e, n lo, n hi, rails on ( lower n, higher n ) )
    "lobby_N": ( -2440.0, -2720.0, 420.0, 600.0, ( True, True ) ),
    "lobby_S": ( -2440.0, -2720.0, -600.0, -420.0, ( True, True ) ),
    "control": ( 2666.0, 2380.0, 770.0, 900.0, ( True, False ) ),
}


def world( e, n, z ):
    return ( n, -e, z )


def ray( a, b ):
    return [ *world( *a ), *world( *b ) ]


def flight_rays( name, foot, head, n0, n1, rails ):
    out = []
    run = ( head - foot ) / STEPS                          # negative: the flights climb towards -e
    L = abs( head - foot )
    nm = ( n0 + n1 ) / 2
    for k in range( STEPS ):                               # a vertical ray down every tread, on both sides and the middle
        e = foot + ( k + 0.5 ) * run
        for n in ( n0 + 13.0, nm - 25.0, nm, nm + 25.0, n1 - 13.0 ):
            out.append( ( f"{name} tread {k:02d} n={n:g}", ray( ( e, n, 400.0 ), ( e, n, -20.0 ) ) ) )
    for side, ( keep, line ) in enumerate( zip( rails, ( n0 + 2.0, n1 - 2.0 ) ) ):
        for t in ( 0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95 ):          # down onto the handrail hulls' sloped tops (or the bare kerb)
            e = foot + t * ( head - foot )
            out.append( ( f"{name} rail {side} {'hull' if keep else 'bare'} top t={t}", ray( ( e, line, 400.0 ), ( e, line, -20.0 ) ) ) )
    for t in ( 0.15, 0.4, 0.65, 0.9 ):                     # sideways across the flight at rail height, from each outside
        e = foot + t * ( head - foot )
        z = t * L1 + 30.0
        out.append( ( f"{name} across from low-n t={t}", ray( ( e, n0 - 45.0, z ), ( e, nm, z ) ) ) )
        out.append( ( f"{name} across from high-n t={t}", ray( ( e, n1 + 45.0, z ), ( e, nm, z ) ) ) )
    d = 1.0 if foot > head else -1.0                       # from the head towards the foot, along e
    for n in ( n0 + 30.0, nm, n1 - 30.0 ):                 # the head's end wall seen from beyond the head, the foot from beyond the foot
        out.append( ( f"{name} head wall n={n:g}", ray( ( head - d * 90.0, n, 100.0 ), ( head + d * 10.0, n, 100.0 ) ) ) )
        out.append( ( f"{name} foot n={n:g}", ray( ( foot + d * 120.0, n, 4.0 ), ( foot - d * 10.0, n, 4.0 ) ) ) )
    return out


def grid_rays():
    out = []
    for e in range( -2900, -1899, 100 ):                   # the lobby and its balconies
        for n in range( -900, 901, 150 ):
            out.append( ( f"lobby grid {e},{n}", ray( ( float( e ), float( n ), 500.0 ), ( float( e ), float( n ), -20.0 ) ) ) )
    for e in range( 2300, 2901, 100 ):                     # the control room round its flight
        for n in range( 400, 1001, 100 ):
            out.append( ( f"control grid {e},{n}", ray( ( float( e ), float( n ), 500.0 ), ( float( e ), float( n ), -20.0 ) ) ) )
    return out


def all_rays():
    rays = []
    for name, spec in FLIGHTS.items():
        rays += flight_rays( name, *spec )
    return rays + grid_rays()


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
