var live = Game.ActiveScene;
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
try
{
    Facepunch.Weather weather;
    Facepunch.WorldWind wind;
    SkyBox2D sky;
    DirectionalLight sun;
    using (scene.Push())
    {
        sky = new GameObject(scene, true, "QA sky").Components.Create<SkyBox2D>();
        sky.SkyMaterial = Material.Load("materials/lowtide/sky/lowtide_sky.vmat");
        sun = new GameObject(scene, true, "QA sun").Components.Create<DirectionalLight>();
        sun.LightColor = new Color(1.45f, 1.26f, 1.02f, 1f);
        sun.SkyColor = new Color(.42f, .48f, .58f, 1f);
        var fog = new GameObject(scene, true, "QA fog").Components.Create<GradientFog>();
        fog.StartDistance = 2200; fog.EndDistance = 34000;
        wind = new GameObject(scene, true, "QA wind").Components.Create<Facepunch.WorldWind>();
        weather = new GameObject(scene, true, "QA weather").Components.Create<Facepunch.Weather>();
        var camera = new GameObject(scene, true, "QA camera").Components.Create<CameraComponent>();
        camera.WorldPosition = new Vector3(0, 0, 64);
        var ground = new GameObject(scene, true, "QA ground").Components.Create<BoxCollider>();
        ground.Scale = new Vector3(4000, 4000, 10);
        ground.WorldPosition = new Vector3(0, 0, -5);
        scene.EditorTick(.016f, .016f);
    }
    var initialMaterial = sky.SkyMaterial;
    var initialLight = sun.LightColor;
    var calm = wind.Velocity;
    var update = typeof(Facepunch.Weather).GetMethod("OnUpdate", flags);
    var viewUpdate = typeof(Facepunch.RainView).GetMethod("OnUpdate", flags);
    var elapsed = typeof(Facepunch.Weather).GetProperty("Elapsed");
    using (scene.Push())
    {
        weather.Set(Facepunch.WeatherKind.Clear, -1);
        update.Invoke(weather, null);
        var view = scene.GetAllComponents<Facepunch.RainView>().Single();
        scene.EditorTick(.032f, .016f);
        viewUpdate.Invoke(view, null);
        if (scene.GetAllComponents<ParticleEffect>().Any()) throw new Exception("Clear weather allocated rain effects");
        if (sky.SkyMaterial == initialMaterial) throw new Exception("Sky material was not isolated");
        weather.Seed = 1234;
        elapsed.SetValue(weather, (TimeSince)300f);
        viewUpdate.Invoke(view, null);
        var first = sun.LightColor;
        elapsed.SetValue(weather, (TimeSince)700f);
        viewUpdate.Invoke(view, null);
        if (sun.LightColor == first) throw new Exception("Fair-weather daylight did not change");
        if (sun.LightColor.r < initialLight.r * .88f) throw new Exception("Fair-weather change was too strong");
        weather.Set(Facepunch.WeatherKind.Steady, 5f);
        update.Invoke(weather, null);
        typeof(Facepunch.RainView).GetField("_k", flags).SetValue(view, 1f);
        viewUpdate.Invoke(view, null);
        if (scene.GetAllComponents<ParticleEffect>().Count() != 3) throw new Exception("Rain effects did not start");
        if (wind.Velocity == calm) throw new Exception("Rain wind did not start");
        weather.Set(Facepunch.WeatherKind.Clear, -1);
        typeof(Facepunch.RainView).GetField("_k", flags).SetValue(view, 0f);
        viewUpdate.Invoke(view, null);
        scene.EditorTick(.048f, .016f);
        if (scene.GetAllComponents<ParticleEffect>().Any()) throw new Exception("Rain effects survived clearing");
        if (wind.Velocity != calm) throw new Exception("Calm wind was not restored");
        if (scene.GetAllComponents<Facepunch.RainView>().Count() != 1) throw new Exception("Weather view was lost");
        view.Enabled = false;
        // Game callbacks are driven explicitly in this isolated editor scene.
        typeof(Facepunch.RainView).GetMethod("OnDisabled", flags).Invoke(view, null);
        if (sky.SkyMaterial != initialMaterial || sun.LightColor != initialLight) throw new Exception("Authored atmosphere was not restored");
    }
    return new {Passed = true, ClearEffects = 0, RainEffects = 3, ClearedEffects = 0, PrivateSky = true, DaylightChanged = true, WindRestored = true, AuthoredAtmosphereRestored = true, RuntimeUnchanged = live == Game.ActiveScene};
}
finally {scene.Destroy();}
