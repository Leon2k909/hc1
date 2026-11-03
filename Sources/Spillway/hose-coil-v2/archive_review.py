"""Archive hose-specific comparison resources after installation validation, through the editor."""
import json
import sys
sys.dont_write_bytecode = True
from native import Editor

with Editor() as editor:
    result = editor.script('''var root = Sandbox.Project.Current.GetRootPath();
var source = System.IO.Path.Combine(root, "Assets/models/compare_old/spillway_hose_v2");
var archive = System.IO.Path.Combine(root, "output/asset-improvement-20261030/spillway-hose/retired/comparison_sources");
System.IO.Directory.CreateDirectory(archive);
var moved = new System.Collections.Generic.List<string>();
foreach (var name in new[] { "old_hose", "cargo_dark_rest" })
    foreach (var suffix in new[] { ".obj", ".obj.meta", ".mtl", ".vmdl", ".vmdl.meta", ".vmdl_c" })
    {
        var file = name + suffix;
        var path = System.IO.Path.Combine(source, file);
        if (!System.IO.File.Exists(path)) continue;
        System.IO.File.Copy(path, System.IO.Path.Combine(archive, file), false);
        System.IO.File.Delete(path);
        moved.Add(file);
    }
return new { Archived = moved, SharedHiddenMaterialKept = true };''', 'archive-hose-review.cs')
    print(json.dumps(result, indent=2))
