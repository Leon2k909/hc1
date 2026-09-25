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
}
