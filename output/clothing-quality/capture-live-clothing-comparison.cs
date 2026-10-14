var vm=Game.ActiveScene.GetAllComponents<Facepunch.ViewModel>().FirstOrDefault(v=>v.Enabled && v.Arms.IsValid());
var camera=Game.ActiveScene.Camera;
if(vm is null || !camera.IsValid()) return "No active viewmodel camera";
var overrides=new System.Collections.Generic.List<(SkinnedModelRenderer Renderer,int Slot,Material Original,Material Detailed)>();
foreach(var r in vm.GameObject.GetComponentsInChildren<SkinnedModelRenderer>())
    for(int i=0;i<r.Model.Materials.Length;i++)
    {
        var detailed=r.Materials.GetOverride(i);
        if(detailed?.Name.StartsWith("hc1-first-person-")==true) overrides.Add((r,i,r.Model.Materials[i],detailed));
    }
var output=@"D:\Documents\s&box projects\hc1\forked-shooter-main\output\clothing-quality";
try
{
    foreach(var item in overrides) item.Renderer.Materials.SetOverride(item.Slot,item.Original);
    using(var bitmap=new Bitmap(1920,1080))
    {
        camera.RenderToBitmap(bitmap,false);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,"live-before.png"),bitmap.ToPng());
    }
    foreach(var item in overrides) item.Renderer.Materials.SetOverride(item.Slot,item.Detailed);
    using(var bitmap=new Bitmap(1920,1080))
    {
        camera.RenderToBitmap(bitmap,false);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,"live-after.png"),bitmap.ToPng());
    }
    return new { Materials=overrides.Count, Before=System.IO.Path.Combine(output,"live-before.png"),After=System.IO.Path.Combine(output,"live-after.png") };
}
finally
{
    foreach(var item in overrides)
        if(item.Renderer.IsValid()) item.Renderer.Materials.SetOverride(item.Slot,item.Detailed);
}
