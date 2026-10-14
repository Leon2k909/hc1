var camera=Editor.Application.Editor.Camera;
var commands=new Sandbox.Rendering.CommandList("Capture command verification");
var path=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/camera-command-verification.png");
try
{
 commands.Clear(Color.Magenta,true,false,false);
 camera.AddCommandList(commands,Sandbox.Rendering.Stage.AfterPostProcess,10000);
 using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(320,180);
 System.IO.File.WriteAllBytes(path,bitmap.ToPng());
}
finally { camera.RemoveCommandList(commands); commands.Reset(); }
return new {path, cameraFields=camera.GetType().GetFields(System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).Select(x=>new{x.Name,Type=x.FieldType.FullName}).ToArray()};
