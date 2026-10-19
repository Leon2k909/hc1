if(!Game.IsPlaying)throw new Exception("Play must be running before restoring the map");
if(Game.ActiveScene?.Source?.ResourcePath!="scenes/maps/orion/orion.scene")return new{Skipped=true,Reason="The active map already changed"};
var map=ResourceLibrary.Get<SceneFile>("scenes/maps/lowtide/lowtide.scene");
if(map==null)throw new Exception("Original runtime map is unavailable");
var options=new SceneLoadOptions();
options.SetScene(map);
Game.ChangeScene(options);
return new{Requested="scenes/maps/lowtide/lowtide.scene",PriorEditorTab="scenes/maps/orion/orion.scene"};
