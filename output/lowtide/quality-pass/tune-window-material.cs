var asset = Editor.AssetSystem.FindByPath("materials/lowtide/windows/lt_window_interior.vmat");
if (asset == null) throw new Exception("Window material is missing");
var source = System.IO.File.ReadAllText(asset.AbsolutePath);
source = source.Replace("g_flInteriorBrightness \"0.32\"", "g_flInteriorBrightness \"0.16\"");
System.IO.File.WriteAllText(asset.AbsolutePath, source);
return new { success = asset.Compile(false) };
