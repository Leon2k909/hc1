var results = new System.Collections.Generic.List<object>();
foreach (var name in new[] { "lt_brick", "lt_brick_soot" })
{
    var asset = Editor.AssetSystem.FindByPath($"materials/lowtide/{name}.vmat");
    if (asset == null) throw new Exception($"Missing {name}");
    var source = System.IO.File.ReadAllText(asset.AbsolutePath);
    if (!source.Contains("TextureFacadeWear"))
    {
        var end = source.LastIndexOf('}');
        if (end < 0) throw new Exception("Missing material closing brace");
        source = source.Insert(end, "    TextureFacadeWear \"materials/lowtide/masonry/facade_wear.png\"\n    g_flFacadeWear \"1\"\n");
        System.IO.File.WriteAllText(asset.AbsolutePath, source);
    }
    results.Add(new { name, success = asset.Compile(false) });
    await Task.Yield();
}
foreach (var path in new[] { "lt_brick_glazed", "lt_brick_slime", "finish/lt_quay_stone",
    "masonry/lt_arch_clay", "masonry/lt_granite_trim", "roofs/lt_slate" })
{
    var asset = Editor.AssetSystem.FindByPath($"materials/lowtide/{path}.vmat");
    if (asset == null) throw new Exception($"Missing {path}");
    results.Add(new { name = path, success = asset.Compile(false) });
    await Task.Yield();
}
return results;
