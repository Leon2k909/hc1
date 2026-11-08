"""Install the new utility poles: add nine model objects to the Riverside scene and take the old poles' triangles out of the
dressing mesh.

Needs prepare_install.py to have run. The dressing's collision, insulators, transformer cans, lamp arms and wires, the scene's
other objects and the build scripts are not touched. Riverside is brought to the front only for the few seconds this takes
(the editor is shared, and the shared lock output/editor-lock is held meanwhile); revert.py undoes it.
"""
from pathlib import Path
import json, sys, time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parent))
sys.path.insert(0, str(Path(__file__).absolute().parents[3] / 'Tools'))
import editor as E  # noqa: E402
import map_kit as K  # noqa: E402
import riverside_map as R  # noqa: E402
import riverside_parts as P  # noqa: E402

OUT = E.ROOT / 'output/riverside/utility-pole-v1'

CODE = r'''var session = Editor.SceneEditorSession.Active;
if ( session == null || session.Scene.Name != "riverside" ) throw new Exception( "Riverside is not the active document: " + session?.Scene.Name );
if ( session.HasUnsavedChanges || Game.IsPlaying ) throw new Exception( "Riverside must be a clean, editing document" );
if ( session.Scene.GetAllObjects( false ).Any( g => g.Name == "Utility Poles" ) ) throw new Exception( "Utility Poles is already installed" );
void Check( string path, int[] tris )
{
	var model = Model.Load( path );
	if ( model.IsError || !model.MeshInfo.Meshes.Select( m => m.Triangles ).SequenceEqual( tris ) ) throw new Exception( "Not the built model: " + path );
}
Check( "models/props/riverside/utility_pole_v1/pole_2arm.vmdl", new[] { @TRIS2@ } );
Check( "models/props/riverside/utility_pole_v1/pole_1arm.vmdl", new[] { @TRIS1@ } );
var project = Sandbox.Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( project, "output/riverside/utility-pole-v1" );
var plan = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( folder, "install-plan.json" ) ) );
string Hash( string p ) => Convert.ToHexString( System.Security.Cryptography.SHA256.HashData( System.IO.File.ReadAllBytes( p ) ) ).ToLowerInvariant();
var relative = plan["source"].GetValue<string>();
if ( relative.Contains( ".." ) || !relative.StartsWith( "Assets/models/maps/riverside/" ) ) throw new Exception( "Unexpected mesh target" );
var target = System.IO.Path.Combine( project, relative );
var staged = System.IO.Path.Combine( project, plan["staged"].GetValue<string>() );
if ( Hash( target ) != plan["source_before"].GetValue<string>() || Hash( staged ) != plan["source_after"].GetValue<string>() ) throw new Exception( "The dressing mesh changed since it was staged" );
var sceneHash = Hash( System.IO.Path.Combine( project, "Assets/scenes/maps/Riverside/riverside.scene" ) );
if ( sceneHash != plan["scene_before"].GetValue<string>() && ( plan["scene_reverted"] == null || sceneHash != plan["scene_reverted"].GetValue<string>() ) ) throw new Exception( "The Riverside scene file changed since it was staged (or since revert.py saved it)" );
var dressing = Model.Load( "models/maps/riverside/riverside_dressing.vmdl" );
if ( dressing.IsError ) throw new Exception( "The dressing model does not load" );
var dressingBefore = dressing.MeshInfo.Meshes.Sum( m => m.Triangles );
var poles = new[] {
@POLES@
};
var group = Editor.Mcp.SceneTools.CreateGameObject( name: "Utility Poles" );
var ids = new System.Collections.Generic.List<string>();
foreach ( var p in poles )
{
	var item = Editor.Mcp.SceneTools.CreateGameObject( name: p.Name, parent: group.Id.ToString(), position: p.Pos, angles: "0," + p.Yaw + ",0" );
	Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = p.Model, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
	ids.Add( item.Id.ToString() );
}
Editor.Mcp.SceneTools.SaveScene();
System.IO.File.WriteAllText( System.IO.Path.Combine( folder, "native-objects.json" ), System.Text.Json.JsonSerializer.Serialize( new { Group = group.Id, Objects = ids } ) );
System.IO.File.WriteAllBytes( target, System.IO.File.ReadAllBytes( staged ) );
Editor.AssetSystem.RegisterFile( target );
return new { Group = group.Id, Objects = ids.Count, SceneSaved = true, DressingTrianglesBefore = dressingBefore, RemovedOldTriangles = plan["removed_triangles"].GetValue<int>(), MatchesStaged = Hash( target ) == plan["source_after"].GetValue<string>() };
'''

POLL = r'''var m = Model.Load( "models/maps/riverside/riverside_dressing.vmdl" );
return new { m.IsError, Tris = m.MeshInfo == null ? -1 : m.MeshInfo.Meshes.Sum( x => x.Triangles ) };
'''


def pole_rows():
    """ one C# initialiser per pole, from the generator's own registry: base in engine units, yaw in engine degrees """
    P.reset()
    P.OLD_POLES_IN_DRESSING = False
    R.dressing(K.Model())
    rows = []
    for k, (owner, base, yaw, arms) in enumerate(P.UTILITY_POLES):
        import math
        heading = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
        pos = K.to_world(base)
        rows.append('\tnew { Name = "Utility Pole %d", Pos = "%s", Yaw = "%.4f", Model = "%s" },' % (
            k + 1, ','.join('%.4f' % q for q in pos), K.plan_yaw(heading), R.UTILITY_POLE_MODELS[arms]))
    assert len(rows) == 9, len(rows)
    return '\n'.join(rows)


def main():
    plan = json.loads((OUT / 'install-plan.json').read_text())
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert (OUT / 'install-before/riverside_dressing.obj').exists(), 'Run prepare_install.py first'
    code = (CODE.replace('@TRIS2@', ', '.join(str(t) for t in manifest['pole_2arm']['triangles']))
                .replace('@TRIS1@', ', '.join(str(t) for t in manifest['pole_1arm']['triangles']))
                .replace('@POLES@', pole_rows()))
    with E.borrowed('riverside'):
        result = E.script(code, 'install-utility-poles.cs')
    (OUT / 'native-install.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    # The editor recompiles the dressing's ModelDoc by itself once it sees the OBJ change; wait for the new triangle count.
    want = result['DressingTrianglesBefore'] - plan['removed_triangles']
    for _ in range(60):
        r = E.script(POLL, 'poll-dressing.cs')
        print(r, flush=True)
        if not r['IsError'] and r['Tris'] == want:
            break
        time.sleep(3)
    else:
        raise SystemExit('The dressing has not recompiled to %d triangles yet; look at the editor before going on' % want)


if __name__ == '__main__':
    main()
