using System;
using System.Linq;
using System.Text.Json;

namespace Facepunch;

/// <summary>
/// The crosshair a player shares on the scoreboard. Contains both renderers' settings;
/// copying it leaves the recipient's hit markers and other game settings alone.
/// </summary>
public sealed class SharedCrosshair
{
	public const int MaxJsonLength = 4096;
	public int Version { get; set; }
	public string Style { get; set; } = "hc1";
	public bool Enabled { get; set; } = true;
	public bool HideOnAds { get; set; } = true;
	public string Color { get; set; } = "#3cff7a";
	public float Alpha { get; set; } = 1f;
	public int Thickness { get; set; } = 2;
	public int Size { get; set; } = 10;
	public int Gap { get; set; } = 6;
	public bool Dot { get; set; } = true;
	public bool TStyle { get; set; }
	public bool Outline { get; set; } = true;
	public int OutlineThickness { get; set; } = 2;
	public float OutlineAlpha { get; set; } = .8f;
	public bool NativeDot { get; set; } = true;
	public bool NativeDynamic { get; set; } = true;
	public float NativeLength { get; set; } = 10f;
	public float NativeWidth { get; set; } = 2f;
	public float NativeGap { get; set; } = 15f;
	public string NativeColor { get; set; } = "#ffffff";
	public float NativeAlpha { get; set; } = 1f;

	public string ToJson() => JsonSerializer.Serialize( this );

	/// <summary> Copies the aiming reticle while preserving every hit marker setting on the target. </summary>
	public void CopyTo( CrosshairConfig target )
	{
		target.Style = Style;
		target.Enabled = Enabled;
		target.HideOnAds = HideOnAds;
		target.Color = Color;
		target.Alpha = Alpha;
		target.Thickness = Thickness;
		target.Size = Size;
		target.Gap = Gap;
		target.Dot = Dot;
		target.TStyle = TStyle;
		target.Outline = Outline;
		target.OutlineThickness = OutlineThickness;
		target.OutlineAlpha = OutlineAlpha;
	}

	/// <summary> Untrusted network data never supplies CSS, unknown styles or unbounded dimensions. </summary>
	public static bool TryRead( string json, out SharedCrosshair result )
	{
		result = null;
		if ( string.IsNullOrWhiteSpace( json ) || json.Length > MaxJsonLength )
			return false;

		SharedCrosshair value;
		try { value = JsonSerializer.Deserialize<SharedCrosshair>( json ); }
		catch ( JsonException ) { return false; }

		if ( value is null || value.Version != 1
			|| value.Style is not ("hc1" or "classic" or "modern" or "custom" or "none")
			|| !TryColor( value.Color, out var color ) || !TryColor( value.NativeColor, out var nativeColor )
			|| !float.IsFinite( value.Alpha ) || !float.IsFinite( value.OutlineAlpha ) || !float.IsFinite( value.NativeAlpha )
			|| !float.IsFinite( value.NativeLength ) || !float.IsFinite( value.NativeWidth ) || !float.IsFinite( value.NativeGap ) )
			return false;

		value.Color = color;
		value.NativeColor = nativeColor;
		value.Alpha = Math.Clamp( value.Alpha, 0f, 1f );
		value.OutlineAlpha = Math.Clamp( value.OutlineAlpha, 0f, 1f );
		value.NativeAlpha = Math.Clamp( value.NativeAlpha, 0f, 1f );
		value.Thickness = Math.Clamp( value.Thickness, 1, 12 );
		value.Size = Math.Clamp( value.Size, 1, 64 );
		value.Gap = Math.Clamp( value.Gap, 0, 64 );
		value.OutlineThickness = Math.Clamp( value.OutlineThickness, 0, 8 );
		value.NativeLength = Math.Clamp( value.NativeLength, 2f, 50f );
		value.NativeWidth = Math.Clamp( value.NativeWidth, 1f, 10f );
		value.NativeGap = Math.Clamp( value.NativeGap, -5f, 50f );
		result = value;
		return true;
	}

	private static bool TryColor( string text, out string color )
	{
		color = null;
		if ( text is null || text.Length is not (4 or 7 or 9) || text[0] != '#'
			|| !text.Skip( 1 ).All( c => c is >= '0' and <= '9' or >= 'a' and <= 'f' or >= 'A' and <= 'F' ) )
			return false;

		// SDK Color.Hex includes RGBA. Opacity is carried separately, and HUD CSS uses RGB.
		color = text.Length == 4 ? $"#{text[1]}{text[1]}{text[2]}{text[2]}{text[3]}{text[3]}" : text[..7];
		color = color.ToLowerInvariant();
		return true;
	}
}
