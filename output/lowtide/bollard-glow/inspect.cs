var root = Editor.SceneEditorSession.Active?.Scene;
var project = @"C:\sbox-projects\hc1\forked-shooter-main\assets";
string[] paths = {
    "materials/lowtide/lt_bollard_diffuser.vmat",
    "models/maps/lowtide/lowtide_dress_east.obj",
    "models/maps/lowtide/lowtide_dress_east.mtl",
    "models/maps/lowtide/lowtide_dress_east.vmdl",
    "models/maps/lowtide/lowtide_dress_west.obj",
    "scenes/maps/Lowtide/lowtide.scene"
};
var files = paths.Select(p => {
    var file = System.IO.Path.Combine(project, p.Replace('/', System.IO.Path.DirectorySeparatorChar));
    var exists = System.IO.File.Exists(file);
    var size = exists ? new System.IO.FileInfo(file).Length : 0L;
    var last = exists ? System.IO.File.GetLastWriteTime(file).ToString("u") : "";
    var text = exists && (p.EndsWith(".vmdl") || p.EndsWith(".mtl") || p.EndsWith(".scene")) ? System.IO.File.ReadAllText(file) : "";
    return new {Path=p, Exists=exists, Bytes=size, Modified=last,
        HasBand = text.Contains("lt_bollard_diffuser"), HasLights=text.Contains("Bollard diffuser")};
});
return new {Scene=root?.Name, InScene=root?.GetAllObjects(true).Count(), Files=files.ToArray()};
