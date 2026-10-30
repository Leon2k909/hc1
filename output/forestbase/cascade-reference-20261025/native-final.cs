var scene=Editor.SceneEditorSession.Active.Scene;
var folder="C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/cascade-reference-20261025";
var shots=new System.Collections.Generic.List<object>();
GameObject temporary=null;
CameraComponent camera=null;
try
{
    using(scene.Push())
    {
        temporary=scene.CreateObject(true);
        temporary.Name="__water_reference_inspection";
        camera=temporary.AddComponent<CameraComponent>();
    }
    foreach(var view in new[]{
        ("front",new Vector3(1450,-430,350),new Vector3(3300,-430,450),68f,1600,1100),
        ("basin",new Vector3(2000,-430,620),new Vector3(3300,-430,400),82f,1600,1100),
        ("river",new Vector3(-1800,140,0),new Vector3(-2450,0,-280),70f,1280,800),
        ("front-motion",new Vector3(1450,-430,350),new Vector3(3300,-430,450),68f,1600,1100)})
    {
        cancellationToken.ThrowIfCancellationRequested();
        using(scene.Push())
        {
            camera.WorldPosition=view.Item2;
            camera.WorldRotation=Rotation.LookAt(view.Item3-view.Item2,Vector3.Up);
            camera.FieldOfView=view.Item4;
            using var bitmap=new Bitmap(view.Item5,view.Item6);
            for(var warmup=0;warmup<8;warmup++)
            {
                scene.EditorTick(.033f,.033f);
                camera.RenderToBitmap(bitmap,false);
            }
            var file=System.IO.Path.Combine(folder,"final-"+view.Item1+".png");
            System.IO.File.WriteAllBytes(file,bitmap.ToPng());
            shots.Add(new{Name=view.Item1,Path=file,Position=view.Item2.ToString(),Target=view.Item3.ToString(),Fov=view.Item4});
        }
        await Task.Delay(450,cancellationToken);
    }
    var materials=new[]{"waterfall_current","waterfall_0","waterfall_1","waterfall_2","waterfall_3","waterfall_impact","waterfall_spray","plunge_basin"}
        .Select(name=>{var path="materials/forestbase/"+name+".vmat";var m=Material.Load(path);return new{Path=path,MaterialError=m.IsError,ShaderError=m.Shader.IsError};}).ToArray();
    var result=new{Scene=scene.Name,Models=scene.GetAllComponents<ModelRenderer>().Count(),ModelErrors=scene.GetAllComponents<ModelRenderer>().Count(x=>x.Model==null||x.Model.IsError),Materials=materials,Shots=shots};
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-final.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    return result;
}
finally { temporary?.Destroy(); }
