using Facepunch;
using System.Text.Json;

var checks = 0;
void Check( bool valid, string why )
{
	checks++;
	if ( !valid ) throw new Exception( why );
}

foreach ( var style in new[] { "hc1", "classic", "modern", "custom", "none" } )
{
	var source = new SharedCrosshair
	{
		Version = 1, Style = style, Enabled = false, HideOnAds = false, Color = "#12A9Df",
		Alpha = .4f, Thickness = 6, Size = 20, Gap = 12, Dot = false, TStyle = true, Outline = false,
		OutlineThickness = 4, OutlineAlpha = .6f, NativeDot = false, NativeDynamic = false,
		NativeLength = 44.2f, NativeWidth = 7.4f, NativeGap = -3.2f, NativeColor = "#Ad34F9", NativeAlpha = .5f
	};
	Check( SharedCrosshair.TryRead( source.ToJson(), out var read ), $"{style}: shared config round trip" );
	Check( read.Style == style && !read.Enabled && !read.HideOnAds, $"{style}: style/toggles" );
	Check( read.Color == "#12a9df" && read.Alpha == .4f, $"{style}: custom color/alpha" );
	Check( read.Size == 20 && read.Thickness == 6 && read.Gap == 12, $"{style}: custom dimensions" );
	Check( !read.Dot && read.TStyle && !read.Outline && read.OutlineThickness == 4 && read.OutlineAlpha == .6f,
		$"{style}: dot, T style and outline" );
	Check( !read.NativeDot && !read.NativeDynamic && read.NativeLength == 44.2f && read.NativeWidth == 7.4f
		&& read.NativeGap == -3.2f && read.NativeColor == "#ad34f9" && read.NativeAlpha == .5f, $"{style}: HC1 native settings" );

	var target = new CrosshairConfig
	{
		HitStyle = "diamond", HitColor = "#111111", HitAlpha = .2f, HitThickness = 6, HitSize = 48,
		HitDuration = 900, HitOutline = false, HitOutlineThickness = 4, HitOutlineAlpha = .3f
	};
	var hitBefore = HitSettings( target );
	read.CopyTo( target );
	Check( HitSettings( target ) == hitBefore, $"{style}: copying a crosshair preserves all hit marker settings" );
	Check( target.Style == style && !target.Enabled && !target.HideOnAds && target.Color == read.Color
		&& target.Alpha == read.Alpha && target.Size == read.Size && target.Thickness == read.Thickness
		&& target.Gap == read.Gap && target.Dot == read.Dot && target.TStyle == read.TStyle
		&& target.Outline == read.Outline && target.OutlineThickness == read.OutlineThickness
		&& target.OutlineAlpha == read.OutlineAlpha, $"{style}: copied reticle matches sender" );
}

foreach ( var json in new[] { null, "", "  ", "null", "[]", "{}", "broken", "{\"Version\":2}",
	"{\"Version\":1,\"Style\":\"url(evil)\"}", "{\"Version\":1,\"Color\":\"red;opacity:0\"}",
	"{\"Version\":1,\"Color\":\"#gggggg\"}", "{\"Version\":1,\"NativeColor\":\"#ffff\"}",
	"{\"Version\":1,\"Alpha\":1e999}", "{\"Version\":1,\"NativeLength\":1e999}",
	"{\"Version\":1,\"NativeWidth\":1e999}", "{\"Version\":1,\"NativeGap\":1e999}",
	"{\"Version\":1,\"NativeAlpha\":1e999}", "{\"Version\":1,\"OutlineAlpha\":1e999}",
	"{\"Version\":1,\"Enabled\":\"wrong type\"}", new string( ' ', SharedCrosshair.MaxJsonLength + 1 ) } )
	Check( !SharedCrosshair.TryRead( json, out _ ), "Malformed, oversized or unsafe network payload rejected" );

var huge = new SharedCrosshair
{
	Version = 1, Thickness = int.MaxValue, Size = int.MaxValue, Gap = int.MaxValue, OutlineThickness = int.MaxValue,
	Alpha = 2f, OutlineAlpha = 3f, NativeAlpha = 4f, NativeLength = 10000, NativeWidth = 20000, NativeGap = 30000
};
Check( SharedCrosshair.TryRead( huge.ToJson(), out var bounded ), "Finite large values can be clamped" );
Check( bounded.Thickness == 12 && bounded.Size == 64 && bounded.Gap == 64 && bounded.OutlineThickness == 8,
	"Custom geometry stays bounded" );
Check( bounded.Alpha == 1 && bounded.OutlineAlpha == 1 && bounded.NativeAlpha == 1
	&& bounded.NativeLength == 50 && bounded.NativeWidth == 10 && bounded.NativeGap == 50, "Native and opacity upper bounds" );
huge.Thickness = huge.Size = huge.Gap = huge.OutlineThickness = int.MinValue;
huge.Alpha = huge.OutlineAlpha = huge.NativeAlpha = huge.NativeLength = huge.NativeWidth = huge.NativeGap = -100;
Check( SharedCrosshair.TryRead( huge.ToJson(), out bounded ), "Finite negative values can be clamped" );
Check( bounded.Thickness == 1 && bounded.Size == 1 && bounded.Gap == 0 && bounded.OutlineThickness == 0,
	"Custom geometry lower bounds" );
Check( bounded.Alpha == 0 && bounded.OutlineAlpha == 0 && bounded.NativeAlpha == 0
	&& bounded.NativeLength == 2 && bounded.NativeWidth == 1 && bounded.NativeGap == -5, "Native and opacity lower bounds" );

Check( SharedCrosshair.TryRead( "{\"Version\":1,\"Color\":\"#ABC\",\"NativeColor\":\"#123\"}", out var shortColors )
	&& shortColors.Color == "#aabbcc" && shortColors.NativeColor == "#112233", "Three-digit color expansion" );
var nativeColor = new Color( .1f, .5f, .9f, .35f );
Check( SharedCrosshair.TryRead( new SharedCrosshair { Version = 1, NativeColor = nativeColor.Hex, NativeAlpha = nativeColor.a }.ToJson(),
	out var native ) && native.NativeAlpha == .35f, "SDK Color.Hex and alpha agree with the sharing format" );
Check( !JsonSerializer.Serialize( new SharedCrosshair { Version = 1 } ).Contains( "HitStyle" ), "Hit markers never enter the shared payload" );

Console.WriteLine( $"PASS: {checks} crosshair sharing checks (actual game source and SDK colors, no live engine)" );

static string HitSettings( CrosshairConfig config ) => JsonSerializer.Serialize( new
{
	config.HitStyle, config.HitColor, config.HitAlpha, config.HitThickness, config.HitSize,
	config.HitDuration, config.HitOutline, config.HitOutlineThickness, config.HitOutlineAlpha
} );
