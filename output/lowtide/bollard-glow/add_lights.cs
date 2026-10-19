var scene = Editor.SceneEditorSession.Active.Scene;
var added = 0;
foreach (var side in new[] { 1, -1 })
{
    foreach (var e in new[] {1050,1210,1370,1530,1690,1850,2010,2170})
    {
        var name = $"Bollard diffuser {(side == 1 ? "east" : "west")} {e}";
        if (scene.GetAllObjects(true).Any(x => x.Name == name)) continue;
        var obj = scene.CreateObject();
        obj.Name = name;
        obj.WorldPosition = new Vector3(1193, -side * e, 38);
        var light = obj.Components.Create<PointLight>();
        light.LightColor = new Color(1.2f, 1.25f, 1.35f);
        light.Radius = 70;
        light.Shadows = false;
        added++;
    }
}
return new {Added=added};
