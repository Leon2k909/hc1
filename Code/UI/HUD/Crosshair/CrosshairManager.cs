namespace Facepunch;

public static class CrosshairManager
{
	private static CrosshairConfig config;

	public static CrosshairConfig Config
	{
		get
		{
			config ??= CrosshairConfig.Load();
			return config;
		}
	}

	public static float HitFlash { get; private set; }
	public static bool SuppressNativeCrosshair => !Config.Enabled || Config.Style != "hc1";

	public static void Tick()
	{
		if ( HitFlash <= 0 ) return;
		HitFlash = Math.Max( 0, HitFlash - Time.Delta * 1000f );
	}

	public static void TriggerHit()
	{
		HitFlash = Config.HitDuration;
	}

	public static void SaveConfig()
	{
		Config.Save();
	}

	public static void ResetConfig()
	{
		config = new CrosshairConfig();
		SaveConfig();
	}

	public static string ShareSettings()
	{
		var c = Config;
		var native = GameSettingsSystem.Current;
		return new SharedCrosshair
		{
			Version = 1, Style = c.Style, Enabled = c.Enabled, HideOnAds = c.HideOnAds,
			Color = c.Color, Alpha = c.Alpha, Thickness = c.Thickness, Size = c.Size, Gap = c.Gap,
			Dot = c.Dot, TStyle = c.TStyle, Outline = c.Outline, OutlineThickness = c.OutlineThickness,
			OutlineAlpha = c.OutlineAlpha, NativeDot = native.ShowCrosshairDot, NativeDynamic = native.DynamicCrosshair,
			NativeLength = native.CrosshairLength, NativeWidth = native.CrosshairWidth, NativeGap = native.CrosshairDistance,
			NativeColor = native.CrosshairColor.Hex, NativeAlpha = native.CrosshairColor.a
		}.ToJson();
	}

	/// <summary> Applies only crosshair settings, including HC1's native renderer, and persists both files. </summary>
	public static bool TryCopySettings( string json )
	{
		if ( !SharedCrosshair.TryRead( json, out var shared ) )
			return false;

		shared.CopyTo( Config );

		var native = GameSettingsSystem.Current;
		native.ShowCrosshairDot = shared.NativeDot;
		native.DynamicCrosshair = shared.NativeDynamic;
		native.CrosshairLength = shared.NativeLength;
		native.CrosshairWidth = shared.NativeWidth;
		native.CrosshairDistance = shared.NativeGap;
		if ( Color.TryParse( shared.NativeColor, out var color ) )
			native.CrosshairColor = color.WithAlpha( shared.NativeAlpha );
		SaveConfig();
		GameSettingsSystem.Save();
		return true;
	}
}
