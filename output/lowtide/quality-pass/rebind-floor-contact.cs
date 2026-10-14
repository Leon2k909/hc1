var root = Project.Current.GetRootPath();
var relative = "materials/lowtide/interior/lt_concrete.vmat";
var source = System.IO.Path.Combine(root, "output/lowtide/quality-pass/floor-contact-stage/Assets", relative);
var target = System.IO.Path.Combine(root, "Assets", relative);
System.IO.File.WriteAllText(target, "// Static floor contact input, compiled after shader schema update.\n"+System.IO.File.ReadAllText(source));
await Task.Delay(1500, cancellationToken);
var material = Editor.AssetSystem.FindByPath(relative).Compile(false);
return new { material };
