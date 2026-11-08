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

eh.OUT = eh.ROOT / "output/model-trial-20261106/reefhall_filter_stairs"
eh.SNIPPETS = eh.OUT / "snippets"

import math
import math
STEPS, L1 = 26, 208.0
FLIGHTS = {   # name: ( lo e, hi e, lo n, hi n, climb axis 0=e 1=n, rails on ( lower, higher ) across )
    "A": ( 300.0, 586.0, 1110.0, 1250.0, 0, ( True, True ) ),
    "B": ( -1150.0, -1030.0, 1384.0, 1670.0, 1, ( False, True ) ),
}


def world( e, n, z ):
    return ( n, -e, z )


def ray( a, b ):
    return [ *world( *a ), *world( *b ) ]


def flight_rays( name, e0, e1, n0, n1, axis, rails ):
    out = []
    a0, a1, o0, o1 = ( e0, e1, n0, n1 ) if axis == 0 else ( n0, n1, e0, e1 )
    P = lambda a, o, z: ( a, o, z ) if axis == 0 else ( o, a, z )      # noqa: E731
    run = ( a1 - a0 ) / STEPS
    om = ( o0 + o1 ) / 2
    for k in range( STEPS ):
        a = a0 + ( k + 0.5 ) * run
        for o in ( o0 + 4.0, o0 + 12.0, om - 20.0, om, om + 20.0, o1 - 12.0, o1 - 4.0 ):
            out.append( ( f"{name} tread {k:02d} o={o:g}", ray( P( a, o, 400.0 ), P( a, o, -20.0 ) ) ) )
    for side, ( keep, line ) in enumerate( zip( rails, ( o0 + 2.0, o1 - 2.0 ) ) ):
        for t in ( 0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95 ):
            a = a0 + t * ( a1 - a0 )
            out.append( ( f"{name} rail {side} top t={t}", ray( P( a, line, 400.0 ), P( a, line, -20.0 ) ) ) )
    for t in ( 0.15, 0.4, 0.65, 0.9 ):
        a = a0 + t * ( a1 - a0 )
        z = t * L1 + 30.0
        out.append( ( f"{name} across from low t={t}", ray( P( a, o0 - 45.0, z ), P( a, om, z ) ) ) )
        out.append( ( f"{name} across from high t={t}", ray( P( a, o1 + 45.0, z ), P( a, om, z ) ) ) )
    for o in ( o0 + 30.0, om, o1 - 30.0 ):
        out.append( ( f"{name} foot o={o:g}", ray( P( a0 - 60.0, o, 4.0 ), P( a0 + 10.0, o, 4.0 ) ) ) )
        out.append( ( f"{name} head o={o:g}", ray( P( a1 + 60.0, o, 100.0 ), P( a1 - 10.0, o, 100.0 ) ) ) )
    return out


def grid_rays():
    out = []
    for e in range( -1200, 1001, 100 ):                    # the filter hall's floor and catwalks
        for n in range( 1050, 1751, 100 ):
            out.append( ( f"filter grid {e},{n}", ray( ( float( e ), float( n ), 500.0 ), ( float( e ), float( n ), -20.0 ) ) ) )
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
