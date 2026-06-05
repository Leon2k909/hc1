using Sandbox;
using System.Collections.Generic;

namespace Facepunch;

/// <summary>
/// A category of perk (e.g. Perk 1, Perk 2, Perk 3).
/// </summary>
public enum PerkCategory
{
	Perk1 = 1,
	Perk2 = 2,
	Perk3 = 3
}

/// <summary>
/// A resource definition for a player Perk.
/// </summary>
[GameResource( "HC1/Perk", "perk", "A player perk that provides modifiers", IconBgColor = "#E0B358", Icon = "star" )]
public partial class PerkResource : GameResource
{
	public static HashSet<PerkResource> All { get; set; } = new();

	[Category( "Base" )]
	public string Name { get; set; } = "My Perk";
	
	[Category( "Base" )]
	public string Description { get; set; } = "";

	[Category( "Base" )]
	public PerkCategory Category { get; set; }

	/// <summary>
	/// The icon to show in the UI for this perk.
	/// </summary>
	[Category( "Base" ), ImageAssetPath]
	public string Icon { get; set; }

	protected override void PostLoad()
	{
		if ( All.Contains( this ) )
			return;

		All.Add( this );
	}
}
