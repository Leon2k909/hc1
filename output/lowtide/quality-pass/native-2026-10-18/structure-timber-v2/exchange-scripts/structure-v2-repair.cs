var root=Project.Current.GetRootPath();
var relative="materials/lowtide/structure/";
var files=new[]{"lt_beam_timber_v2.vmat","lt_cast_iron_v2.vmat"};
foreach(var name in files)
{
    var file=System.IO.Path.Combine(root,"Assets",relative,name);
    var current=System.IO.File.ReadAllText(file);
    var fixedText=System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2/stage",relative,name));
    if(current.Replace("    TextureAmbientOcclusion \"materials/default/default_white.tga\"\n","")!=fixedText)throw new Exception("Unexpected material change");
    System.IO.File.WriteAllText(file,fixedText);
}
return new{Repaired=files,Note="Use the shader's default white occlusion input"};
