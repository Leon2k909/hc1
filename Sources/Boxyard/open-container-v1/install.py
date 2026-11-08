"""Add (or --remove) the "Open Container Detail" scene object in Boxyard. Takes the editor lock; Reef Hall goes back in front."""
import sys
from pathlib import Path

ROOT = Path(r"C:\sbox-projects\hc1\forked-shooter-main")
sys.path.insert(0, str(ROOT / "Sources/ReefHall/lobby-rail-v1"))
import editor as eh  # noqa: E402

eh.SCENE_NAME = "boxyard"
eh.SCENE_PATH = "scenes/maps/Boxyard/boxyard.scene"
MODEL = "models/props/boxyard/open_container_v1/open_container.vmdl"

ADD = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "boxyard" );
if ( session == null ) throw new Exception( "Boxyard is not open" );
if ( Game.IsPlaying ) throw new Exception( "play session running" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true };
var scene = session.Scene;
var all = scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var old = all.Where( g => g.Name == "Open Container Detail" ).ToArray();
@BODY@
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
return new { Retry = false, Removed = old.Length, Saved = !session.HasUnsavedChanges };
'''
CREATE = r'''if ( old.Length > 0 ) throw new Exception( "already added" );
var model = Model.Load( "@MODEL@" );
if ( model.IsError ) throw new Exception( "model did not load" );
var item = Editor.Mcp.SceneTools.CreateGameObject( name: "Open Container Detail", position: "0,0,0", angles: "0,0,0" );
Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );'''
REMOVE = r'''foreach ( var g in old ) g.Destroy();'''

if __name__ == "__main__":
    body = REMOVE if "--remove" in sys.argv else CREATE.replace("@MODEL@", MODEL)
    code = ADD.replace("@BODY@", body)
    with eh.borrowed(scene="boxyard", wait=1500):
        for _ in range(3):
            r = eh.run(code)
            print(r)
            if "Retry = true" not in str(r) and '"Retry":true' not in str(r).replace(" ", ""):
                break
