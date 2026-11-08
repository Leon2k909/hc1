var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var rays = new System.Collections.Generic.List<object>();
var lines = new System.Collections.Generic.List<object>();
int newColliders = 0, totalColliders = 0;
using ( s.Scene.Push() )
{
    foreach ( var c in s.Scene.GetAllComponents<Collider>() )
    {
        totalColliders++;
        for ( var q = c.GameObject; q != null; q = q.Parent ) if ( q.Name == "Perimeter Wall" ) { newColliders++; break; }
    }

    // 1. collision rays from inside the yard toward each wall at two heights (plan (e,n) -> engine (x = n, y = -e))
    float[] lat = { -640f, -300f, 0f, 420f };
    float[] zs = { 30f, 100f, 140f };
    var walls = new[] { ("N", 0, 1f), ("S", 0, -1f), ("E", 1, -1f), ("W", 1, 1f) };
    foreach ( var w in walls )
    foreach ( var l in lat )
    foreach ( var z in zs )
    {
        Vector3 origin, dir;
        if ( w.Item2 == 0 ) { origin = new Vector3( w.Item3 * 770f, l, z ); dir = new Vector3( w.Item3, 0, 0 ); }
        else { origin = new Vector3( l, w.Item3 * 770f, z ); dir = new Vector3( 0, w.Item3, 0 ); }
        var tr = s.Scene.Trace.Ray( origin, origin + dir * 120f ).Run();
        rays.Add( new { Wall = w.Item1, Lat = l, Z = z, Origin = origin.ToString(), Hit = tr.Hit, Started = tr.StartedSolid, Dist = tr.Distance, Pos = tr.HitPosition.ToString(), Obj = tr.GameObject?.Name } );
    }

    // 2. clear sight lines to the north wall (eye height 64) at several distances, for the LOD review
    float[] distsM = { 12f, 17.4f, 20f, 30f, 40f, 50f };
    foreach ( var dm in distsM )
    {
        float dIn = dm * 39.37f;
        var ok = new System.Collections.Generic.List<string>();
        for ( int ang = -40; ang <= 40; ang += 10 )
        for ( int yt = -700; yt <= 700; yt += 50 )
        {
            float a = ang * 3.14159265f / 180f;
            var dirv = new Vector3( MathF.Cos( a ), MathF.Sin( a ), 0 );
            var target = new Vector3( 832f, yt, 64f );
            var cam = target - dirv * dIn;
            if ( MathF.Abs( cam.x ) > 790f || MathF.Abs( cam.y ) > 780f ) continue;
            var tr = s.Scene.Trace.Ray( cam, target ).Run();
            if ( tr.StartedSolid ) continue;
            if ( tr.Hit && tr.HitPosition.x >= 826f && tr.Distance >= dIn - 12f ) ok.Add( ang + "/" + yt );
        }
        lines.Add( new { DistM = dm, Clear = ok.Count, Samples = string.Join( " ", ok.Take( 40 ) ) } );
    }
}
return new { newColliders, totalColliders, rays, lines };
