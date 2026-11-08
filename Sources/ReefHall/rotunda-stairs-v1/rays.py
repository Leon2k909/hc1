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

eh.OUT = eh.ROOT / "output/model-trial-20261106/reefhall_rotunda_stairs"
eh.SNIPPETS = eh.OUT / "snippets"

import math
STEPS, L1 = 26, 208.0
FLIGHTS = { "NE": ( 82.0, 47.5 ), "NW": ( 98.0, 132.5 ) }     # ( foot, head ) angles, degrees
R0, R1 = 480.0, 600.0


def world( e, n, z ):
    return ( n, -e, z )


def ray( a, b ):
    return [ *world( *a ), *world( *b ) ]


def pol( a, r, z ):
    t = math.radians( a )
    return ( r * math.cos( t ), r * math.sin( t ), z )


def flight_rays( name, foot, head ):
    out = []
    da = ( head - foot ) / STEPS
    for k in range( STEPS ):                               # a vertical ray down every tread at six radii
        a = foot + ( k + 0.5 ) * da
        for r in ( R0 + 6, R0 + 25, 510.0, 540.0, 570.0, R1 - 6 ):
            out.append( ( f"{name} tread {k:02d} r={r:g}", ray( pol( a, r, 400.0 ), pol( a, r, -20.0 ) ) ) )
    for side, r in enumerate( ( R0 + 2.0, R1 - 2.0 ) ):    # down onto the rail hulls' tops
        for t in ( 0.05, 0.15, 0.3, 0.45, 0.6, 0.75, 0.85, 0.95 ):
            a = foot + t * ( head - foot )
            out.append( ( f"{name} rail {side} top t={t}", ray( pol( a, r, 400.0 ), pol( a, r, -20.0 ) ) ) )
    for t in ( 0.1, 0.25, 0.4, 0.55, 0.7, 0.85 ):          # radially across the flight at rail height, from each side
        a = foot + t * ( head - foot )
        z = t * L1 + 30.0
        out.append( ( f"{name} across from inside t={t}", ray( pol( a, R0 - 45.0, z ), pol( a, 540.0, z ) ) ) )
        out.append( ( f"{name} across from outside t={t}", ray( pol( a, R1 + 45.0, z ), pol( a, 540.0, z ) ) ) )
    d = 1.0 if head > foot else -1.0                       # along the arc: the head's end wall from beyond it, the foot from beyond it
    for r in ( 500.0, 540.0, 580.0 ):
        for z in ( 60.0, 150.0, 200.0 ):
            out.append( ( f"{name} head wall r={r:g} z={z:g}", ray( pol( head - d * 14.0, r, z ), pol( head + d * 3.0, r, z ) ) ) )
        out.append( ( f"{name} foot r={r:g}", ray( pol( foot - d * 14.0, r, 4.0 ), pol( foot + d * 3.0, r, 4.0 ) ) ) )
    return out


def grid_rays():
    out = []
    for e in range( -900, 901, 100 ):                      # the Rotunda's floor and balcony
        for n in range( -900, 901, 100 ):
            out.append( ( f"rotunda grid {e},{n}", ray( ( float( e ), float( n ), 500.0 ), ( float( e ), float( n ), -20.0 ) ) ) )
    return out


def all_rays():
    rays = []
    for name, ( foot, head ) in FLIGHTS.items():
        rays += flight_rays( name, foot, head )
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
