"""Install the timber watch deck: add it to the Riverside scene and take the old deck's triangles out of the Pad mesh.

Needs prepare_install.py to have run. The Pad's collision, the scene's other objects and the build scripts are not
touched. Riverside is brought to the front only for the few seconds this takes (the editor is shared); revert.py undoes it.
"""
from pathlib import Path
import json, sys, time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parent))
import editor as E  # noqa: E402

OUT = E.ROOT / 'output/riverside/watch-deck-v1'

CODE = r'''var session = Editor.SceneEditorSession.Active;
if ( session == null || session.Scene.Name != "riverside" ) throw new Exception( "Riverside is not the active document: " + session?.Scene.Name );
if ( session.HasUnsavedChanges || Game.IsPlaying ) throw new Exception( "Riverside must be a clean, editing document" );
if ( session.Scene.GetAllObjects( false ).Any( g => g.Name == "Watch Deck" ) ) throw new Exception( "Watch Deck is already installed" );
var model = Model.Load( "models/props/riverside/watch_deck_v1/deck.vmdl" );
if ( model.IsError || !model.MeshInfo.Meshes.Select( m => m.Triangles ).SequenceEqual( new[] { @TRIS@ } ) ) throw new Exception( "The watch deck model is not the built one" );
var project = Sandbox.Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( project, "output/riverside/watch-deck-v1" );
var plan = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( folder, "install-plan.json" ) ) );
string Hash( string p ) => Convert.ToHexString( System.Security.Cryptography.SHA256.HashData( System.IO.File.ReadAllBytes( p ) ) ).ToLowerInvariant();
var relative = plan["source"].GetValue<string>();
if ( relative.Contains( ".." ) || !relative.StartsWith( "Assets/models/maps/riverside/" ) ) throw new Exception( "Unexpected mesh target" );
var target = System.IO.Path.Combine( project, relative );
var staged = System.IO.Path.Combine( project, plan["staged"].GetValue<string>() );
if ( Hash( target ) != plan["source_before"].GetValue<string>() || Hash( staged ) != plan["source_after"].GetValue<string>() ) throw new Exception( "The Pad mesh changed since it was staged" );
if ( Hash( System.IO.Path.Combine( project, "Assets/scenes/maps/Riverside/riverside.scene" ) ) != plan["scene_before"].GetValue<string>() ) throw new Exception( "The Riverside scene file changed since it was staged" );
var group = Editor.Mcp.SceneTools.CreateGameObject( name: "Watch Deck" );
var item = Editor.Mcp.SceneTools.CreateGameObject( name: "Timber Watch Deck", parent: group.Id.ToString(), position: "-445,-60,96", angles: "0,0,0" );
Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
Editor.Mcp.SceneTools.SaveScene();
System.IO.File.WriteAllText( System.IO.Path.Combine( folder, "native-objects.json" ), System.Text.Json.JsonSerializer.Serialize( new { Group = group.Id, Object = item.Id } ) );
System.IO.File.WriteAllBytes( target, System.IO.File.ReadAllBytes( staged ) );
Editor.AssetSystem.RegisterFile( target );
return new { Group = group.Id, Object = item.Id, SceneSaved = true, RemovedOldTriangles = plan["removed_triangles"].GetValue<int>(), MatchesStaged = Hash( target ) == plan["source_after"].GetValue<string>() };
'''

POLL = r'''var pad = Model.Load( "models/maps/riverside/riverside_pad.vmdl" );
return new { pad.IsError, Tris = pad.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
'''


def main():
    plan = json.loads((OUT / 'install-plan.json').read_text())
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert (OUT / 'install-before/riverside_pad.obj').exists(), 'Run prepare_install.py first'
    code = CODE.replace('@TRIS@', ', '.join(str(t) for t in manifest['triangles']))
    with E.borrowed('riverside'):
        result = E.script(code, 'install-watch-deck.cs')
    (OUT / 'native-install.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    # The editor recompiles the Pad's ModelDoc by itself once it sees the OBJ change; wait for the new triangle count.
    want = 33152 - plan['removed_triangles']
    for _ in range(40):
        r = E.script(POLL, 'poll-pad.cs')
        print(r, flush=True)
        if not r['IsError'] and r['Tris'] == [want]:
            break
        time.sleep(3)
    else:
        raise SystemExit('The Pad has not recompiled to %d triangles yet; look at the editor before going on' % want)


if __name__ == '__main__':
    main()
