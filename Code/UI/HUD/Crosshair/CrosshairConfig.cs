namespace Facepunch;

public class CrosshairConfig
{
	public string Style { get; set; } = "hc1";
	public bool Enabled { get; set; } = true;
	public bool HideOnAds { get; set; } = true;

	public string Color { get; set; } = "#3cff7a";
	public float Alpha { get; set; } = 1f;
	public int Thickness { get; set; } = 2;
	public int Size { get; set; } = 10;
	public int Gap { get; set; } = 6;
	public bool Dot { get; set; } = true;
	public bool TStyle { get; set; } = false;
	public bool Outline { get; set; } = true;
	public int OutlineThickness { get; set; } = 2;
	public float OutlineAlpha { get; set; } = 0.8f;

	public string HitStyle { get; set; } = "x";
	public string HitColor { get; set; } = "#ff4444";
	public float HitAlpha { get; set; } = 1f;
	public int HitThickness { get; set; } = 3;
	public int HitSize { get; set; } = 14;
	public int HitDuration { get; set; } = 420;
	public bool HitOutline { get; set; } = true;
	public int HitOutlineThickness { get; set; } = 2;
	public float HitOutlineAlpha { get; set; } = 0.8f;

	private const string FilePath = "crosshair_config.json";

	public static CrosshairConfig Load()
	{
		try
		{
			return FileSystem.Data.ReadJson<CrosshairConfig>( FilePath, new CrosshairConfig() ) ?? new CrosshairConfig();
		}
		catch
		{
			return new CrosshairConfig();
		}
	}

	public void Save()
	{
		FileSystem.Data.WriteJson( FilePath, this );
	}
}