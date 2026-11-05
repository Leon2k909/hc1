using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

public record CosmeticArt( string Id, string Name, string Image );

/// <summary>Only these shipped images may be placed as multiplayer sprays.</summary>
public static class CosmeticCatalog
{
	public static IReadOnlyList<CosmeticArt> Sprays { get; } = Array.AsReadOnly( new[]
	{
		new CosmeticArt( "precision", "Precision", "ui/medals/precision.png" ),
		new CosmeticArt( "fieldcraft", "Fieldcraft", "ui/medals/training.png" ),
		new CosmeticArt( "streak", "Streak", "ui/medals/streak.png" ),
		new CosmeticArt( "vanguard", "Vanguard", "ui/prestige/prestige_1_readable.png" ),
		new CosmeticArt( "sentinel", "Sentinel", "ui/prestige/prestige_2_readable.png" ),
		new CosmeticArt( "veteran", "Veteran", "ui/prestige/prestige_3_readable.png" )
	} );

	public static IReadOnlyList<CosmeticArt> LoadingScreens { get; } = Array.AsReadOnly( new[]
	{
		new CosmeticArt( "default", "Game default", "" ),
		new CosmeticArt( "orion", "Orion", "ui/maps/orion.png" ),
		new CosmeticArt( "riverside", "Riverside", "ui/maps/riverside.png" ),
		new CosmeticArt( "belltower", "Belltower", "ui/maps/belltower.png" ),
		new CosmeticArt( "collider", "Collider", "ui/maps/collider.png" ),
		new CosmeticArt( "railhead", "Railhead", "ui/maps/railhead.png" ),
		new CosmeticArt( "reefhall", "Reef Hall", "ui/maps/reefhall.png" ),
		new CosmeticArt( "forestbase", "Forest Base", "ui/maps/forestbase.png" ),
		new CosmeticArt( "spillway", "Spillway", "ui/maps/spillway.png" )
	} );

	public static CosmeticArt FindSpray( string id ) => Sprays.FirstOrDefault( item => item.Id == id );
	public static CosmeticArt FindLoadingScreen( string id ) => LoadingScreens.FirstOrDefault( item => item.Id == id );

	/// <summary>A personal loading image is never sent to other players or used as a spray.</summary>
	public static bool TryImageUrl( string text, out string url )
	{
		url = null;
		if ( string.IsNullOrWhiteSpace( text ) || text.Length > 2048
			|| !Uri.TryCreate( text.Trim(), UriKind.Absolute, out var uri ) || uri.Scheme != Uri.UriSchemeHttps
			|| !string.IsNullOrEmpty( uri.UserInfo ) || !string.IsNullOrEmpty( uri.Fragment ) ) return false;
		var path = uri.AbsolutePath;
		if ( !new[] { ".png", ".jpg", ".jpeg", ".webp" }.Any( ext => path.EndsWith( ext, StringComparison.OrdinalIgnoreCase ) ) ) return false;
		url = uri.AbsoluteUri;
		return true;
	}
}
