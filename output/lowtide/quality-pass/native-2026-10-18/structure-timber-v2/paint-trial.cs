var root=Project.Current.GetRootPath();
var oldPath="materials/lowtide/structure/lt_cast_iron_v2.vmat";
var newPath="materials/lowtide/structure/lt_cast_paint_trial.vmat";
var old=System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Assets",oldPath));
var text=old.Replace("materials/lowtide/drainage/cast_iron_","materials/lowtide/marine/paint_").Replace("[.85 .85 .85]","[1.15 1.15 1.15]").Replace("[2.666666667 2.666666667]","[1.354666667 1.354666667]");
if(old==text||System.IO.File.Exists(System.IO.Path.Combine(root,"Assets",newPath)))throw new Exception("Unexpected trial state");
System.IO.File.WriteAllText(System.IO.Path.Combine(root,"Assets",newPath),text);
var registered=Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(root,"Assets",newPath));
return new{Path=newPath,Registered=registered!=null};
