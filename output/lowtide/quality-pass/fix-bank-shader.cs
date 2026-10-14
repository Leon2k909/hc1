var project = Project.Current.GetRootPath();
var relative = "shaders/hc1_lowtide_stone.shader";
var path = System.IO.Path.Combine(project, "Assets", relative);
System.IO.File.Copy(System.IO.Path.Combine(project, "output/lowtide/quality-pass/banks-stage/hc1_lowtide_stone.shader"), path, true);
var result = await Editor.EditorUtility.CompileShader(relative, new Sandbox.Engine.Shaders.ShaderCompileOptions(), cancellationToken);
return new { result.Success, result.Skipped, Programs = result.Programs.Select(p => new { p.Name, p.Success, p.Output }) };
