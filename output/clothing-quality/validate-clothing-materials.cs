var original = Material.Load("models/citizen_clothes/gloves/fingerless_gloves/textures/fingerless_gloves.vmat").GetTexture("g_tColor");
var packed = Texture.Load("materials/operators/first_person/fp_fingerless_gloves_albedo.png");
using var source = original.GetBitmap(0);
using var mask = source.Resize(packed.Width,packed.Height,true);
using var packedBitmap = packed.GetBitmap(0);
var expected=mask.GetPixels32(); var actual=packedBitmap.GetPixels32();
int alphaMismatch=0;
for(int i=0;i<expected.Length;i++) if(expected[i].a!=actual[i].a) alphaMismatch++;
var vm = Game.ActiveScene.GetAllComponents<Facepunch.ViewModel>().FirstOrDefault(v=>v.Enabled && v.Arms.IsValid());
var rows = new System.Collections.Generic.List<object>();
if(vm is not null)
    foreach(var r in vm.GameObject.GetComponentsInChildren<SkinnedModelRenderer>())
        for(int i=0;i<r.Model.Materials.Length;i++)
        {
            var baseMaterial=r.Model.Materials[i]; var material=r.Materials.GetOverride(i);
            if(material?.Name.StartsWith("hc1-first-person-")!=true) continue;
            rows.Add(new { Model=r.Model.Name, Material=material.Name, Width=material.GetTexture("g_tColor")?.Width,
                NormalPreserved=material.GetTexture("g_tNormal")==baseMaterial.GetTexture("g_tNormal"),
                AoPreserved=material.GetTexture("g_tAmbientOcclusion")==baseMaterial.GetTexture("g_tAmbientOcclusion"),
                AlphaTestPreserved=material.GetFeature("F_ALPHA_TEST")==baseMaterial.GetFeature("F_ALPHA_TEST") });
        }
var report=new { AlphaMismatchPixels=alphaMismatch, AlphaTestedPixels=expected.Length, LiveMaterials=rows };
System.IO.File.WriteAllText(@"D:\Documents\s&box projects\hc1\forked-shooter-main\output\clothing-quality\validation.json",Json.Serialize(report));
var camera=Game.ActiveScene.Camera;
if(camera.IsValid())
{
    using var image=new Bitmap(1920,1080);
    camera.RenderToBitmap(image,false);
    System.IO.File.WriteAllBytes(@"D:\Documents\s&box projects\hc1\forked-shooter-main\output\clothing-quality\live-after.png",image.ToPng());
}
return report;
