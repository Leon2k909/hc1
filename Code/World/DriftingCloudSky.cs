namespace Facepunch;

/// <summary>Drive cloud drift in both matches and editor previews, whose sky pass freezes g_flTime.</summary>
[Title( "Drifting Cloud Sky" ), Category( "Environment" )]
public sealed class DriftingCloudSky : Component, Component.ExecuteInEditor
{
    private SkyBox2D _sky;
    private Weather _weather;

    protected override void OnUpdate()
    {
        if ( !_sky.IsValid() ) _sky = GetComponent<SkyBox2D>();
        if ( !_sky.IsValid() ) return;
        if ( Game.IsPlaying && !_weather.IsValid() ) _weather = Scene.GetAllComponents<Weather>().FirstOrDefault();

        var material = _sky.SkyMaterial;
        if ( material is null || material.IsError || material.ShaderName != "shaders/hc1_coastal_sky.shader" ) return;

        // One scalar uniform: no particles, physics or sky/lighting rebuild. Every
        // view uses the same clock, including editor, scope and reflection cameras.
        // Keep the serialized SkyMaterial reference intact so saving a scene is safe.
        material.Set( "g_flSkyCloudTime", _weather.IsValid() ? (float)_weather.Elapsed : (float)RealTime.Now );
    }
}
