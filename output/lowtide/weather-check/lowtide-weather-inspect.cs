var scene = Game.ActiveScene;
return new
{
    Scene = scene?.Name,
    Game.IsPlaying,
    Networking.IsHost,
    Weather = scene.GetAllComponents<Facepunch.Weather>().Select(w => new
    {
        w.Id, w.Active, w.IsProxy, w.Kind, w.Seed, Elapsed = (float)w.Elapsed, w.ForcedRate, w.RainRate,
        Rolled = typeof(Facepunch.Weather).GetField("_rolled", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)?.GetValue(w)
    }).ToArray(),
    Rain = scene.GetAllComponents<Facepunch.RainView>().Select(r => new { r.Id, r.Active, Weather = r.Weather?.Id }).ToArray(),
    Sky = scene.GetAllComponents<SkyBox2D>().Select(s => new { s.Id, s.Active, Material = s.SkyMaterial?.ResourcePath, Shader = s.SkyMaterial?.ShaderName, s.Tint }).ToArray(),
    Sun = scene.GetAllComponents<DirectionalLight>().Select(s => new { s.Id, s.LightColor, s.SkyColor }).ToArray(),
    Maps = scene.GetAllComponents<MapInstance>().Select(m => new { m.Active, m.IsLoaded }).ToArray(),
    Modes = scene.GetAllComponents<Facepunch.GameMode>().Select(m => new { m.Active, m.Ident }).ToArray(),
    Camera = scene.Camera?.WorldPosition
};
