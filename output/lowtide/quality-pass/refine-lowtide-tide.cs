var project=Project.Current.GetRootPath();
var source=System.IO.Path.Combine(project,"output/lowtide/quality-pass/weathering-stage/Assets/shaders/hc1_brick.shader");
var destination=System.IO.Path.Combine(project,"Assets/shaders/hc1_brick.shader");
System.IO.File.Copy(source,destination,true);
var result=await Editor.EditorUtility.CompileShader("shaders/hc1_brick.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
return new{shader=result.Success};
