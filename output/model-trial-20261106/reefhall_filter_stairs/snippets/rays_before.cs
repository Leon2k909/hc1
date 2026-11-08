
var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) return new string[] { "no reefhall session" };
var scene = session.Scene;
var rays = System.Text.Json.JsonSerializer.Deserialize<double[][]>( System.IO.File.ReadAllText( @"C:\sbox-projects\hc1\forked-shooter-main\output\model-trial-20261106\reefhall_filter_stairs\snippets\rays_before_input.json" ) );
var res = new System.Collections.Generic.List<string>();
foreach ( var r in rays )
{
    var a = new Vector3( (float) r[0], (float) r[1], (float) r[2] );
    var b = new Vector3( (float) r[3], (float) r[4], (float) r[5] );
    var tr = scene.Trace.Ray( a, b ).Run();
    res.Add( tr.Hit ? $"{tr.HitPosition.x:F2},{tr.HitPosition.y:F2},{tr.HitPosition.z:F2}|{tr.Normal.x:F2},{tr.Normal.y:F2},{tr.Normal.z:F2}" : "-" );
}
return res.ToArray();
