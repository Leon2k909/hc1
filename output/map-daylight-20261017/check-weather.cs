var session = Editor.SceneEditorSession.Active;
if ( Game.IsPlaying || session?.Scene is null || session.HasUnsavedChanges )
    throw new Exception( "Expected the idle saved editor scene." );
var scene = session.Scene;
var wasDirty = session.HasUnsavedChanges;
var skies = scene.GetAllComponents<SkyBox2D>().Select( x => new { Component = x, x.Tint, x.SkyMaterial } ).ToArray();
var suns = scene.GetAllComponents<DirectionalLight>().Select( x => new { Component = x, x.LightColor, x.SkyColor } ).ToArray();
var fogs = scene.GetAllComponents<GradientFog>().Select( x => new { Component = x, x.Color, x.Height, x.StartDistance, x.EndDistance, x.FalloffExponent } ).ToArray();
var probes = scene.GetAllComponents<EnvmapProbe>().Select( x => new { Component = x, x.TintColor } ).ToArray();
if ( skies.Length != 1 || suns.Length != 1 || fogs.Length != 1 )
    throw new Exception( "Expected the outdoor map's sky, sun and fog." );
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public;
var rain = AppDomain.CurrentDomain.GetAssemblies().Select( x => x.GetType( "Facepunch.RainView", false ) ).LastOrDefault( x => x is not null );
var type = rain?.GetNestedType( "RainLook", System.Reflection.BindingFlags.NonPublic ) ?? throw new Exception( "RainLook missing." );
var look = Activator.CreateInstance( type, true );
var apply = type.GetMethod( "Apply", flags ) ?? throw new Exception( "RainLook.Apply missing." );
var restore = type.GetMethod( "Restore", flags ) ?? throw new Exception( "RainLook.Restore missing." );
bool Restored() => skies.All( x => x.Component.Tint == x.Tint && x.Component.SkyMaterial == x.SkyMaterial )
    && suns.All( x => x.Component.LightColor == x.LightColor && x.Component.SkyColor == x.SkyColor )
    && fogs.All( x => x.Component.Color == x.Color && x.Component.Height == x.Height && x.Component.StartDistance == x.StartDistance
        && x.Component.EndDistance == x.EndDistance && x.Component.FalloffExponent == x.FalloffExponent )
    && probes.All( x => x.Component.TintColor == x.TintColor );
try
{
    apply.Invoke( look, new object[] { scene, 1f, 20f, 0f, 0.8f } );
    var stormChanged = !Restored();
    restore.Invoke( look, null );
    var stormRestored = Restored();
    apply.Invoke( look, new object[] { scene, 0f, 0f, 0f, 0.6f } );
    var fairWeatherChanged = !Restored();
    restore.Invoke( look, null );
    var fairWeatherRestored = Restored();
    if ( !stormChanged || !stormRestored || !fairWeatherChanged || !fairWeatherRestored )
        throw new Exception( "Weather transition did not change and restore the authored profile." );
    return new { map = scene.Source.ResourcePath, stormChanged, stormRestored, fairWeatherChanged, fairWeatherRestored,
        skies = skies.Length, suns = suns.Length, fogs = fogs.Length, probes = probes.Length, wasDirty };
}
finally
{
    try { restore.Invoke( look, null ); }
    finally
    {
        foreach ( var x in skies ) { x.Component.Tint = x.Tint; x.Component.SkyMaterial = x.SkyMaterial; }
        foreach ( var x in suns ) { x.Component.LightColor = x.LightColor; x.Component.SkyColor = x.SkyColor; }
        foreach ( var x in fogs ) { x.Component.Color = x.Color; x.Component.Height = x.Height; x.Component.StartDistance = x.StartDistance;
            x.Component.EndDistance = x.EndDistance; x.Component.FalloffExponent = x.FalloffExponent; }
        foreach ( var x in probes ) x.Component.TintColor = x.TintColor;
    }
    if ( session.HasUnsavedChanges != wasDirty )
        throw new Exception( "Weather check changed the editor dirty state." );
}
