var project = Project.Current.GetRootPath();
var root = System.IO.Path.Combine(project, "output/lowtide/quality-pass/piles-stage/Assets");
var results = new System.Collections.Generic.List<object>();
foreach (var name in new[] { "lt_pile_timber", "lt_pile_end" })
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative = $"materials/lowtide/piles/{name}.vmat";
    System.IO.File.Copy(System.IO.Path.Combine(root, relative), System.IO.Path.Combine(project, "Assets", relative), true);
    var success = Editor.AssetSystem.FindByPath(relative).Compile(false);
    results.Add(new { path = relative, success });
    if (!success) throw new Exception($"Pile material compile failed: {relative}");
    await Task.Yield();
}
return results;
