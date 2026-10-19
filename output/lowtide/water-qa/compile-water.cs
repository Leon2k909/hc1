var result = await Editor.EditorUtility.CompileShader(
    "shaders/hc1_lowtide_water.shader",
    new Sandbox.Engine.Shaders.ShaderCompileOptions(), cancellationToken );
return new { result.Success, result.Skipped,
    Programs = result.Programs.Select( p => new { p.Name, p.Success, p.Output } ).ToArray() };
