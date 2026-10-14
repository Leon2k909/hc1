var asset = Editor.AssetSystem.FindByPath("materials/lowtide/lt_water.vmat");
if (asset == null) throw new Exception("Water material missing");
var text = System.IO.File.ReadAllText(asset.AbsolutePath)
    .Replace("g_flRippleTile \"138\"", "g_flRippleTile \"48\"")
    .Replace("g_flRippleStrength \"1.15\"", "g_flRippleStrength \"0.8\"")
    .Replace("g_flWaterRoughness \"0.065\"", "g_flWaterRoughness \"0.10\"");
System.IO.File.WriteAllText(asset.AbsolutePath, text);
return new { success = asset.Compile(false) };
