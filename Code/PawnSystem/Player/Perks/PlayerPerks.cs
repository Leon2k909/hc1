using Sandbox;
using Facepunch.Gunsmith;

namespace Facepunch;

/// <summary>
/// A component attached to the player that holds their currently equipped perks and provides utility methods.
/// </summary>
public partial class PlayerPerks : Component
{
	[RequireComponent]
	public PlayerPawn Player { get; set; }

	public PerkResource Perk1 { get; private set; }
	public PerkResource Perk2 { get; private set; }
	public PerkResource Perk3 { get; private set; }

	protected override void OnStart()
	{
		if ( !Player.Client.IsValid() || !Player.Client.IsLocalPlayer )
			return;

		LoadFromCookies();
	}

	public void LoadFromCookies()
	{
		Perk1 = GetPerkResource( GunsmithLoadoutManager.GetPerk( 1 ) );
		Perk2 = GetPerkResource( GunsmithLoadoutManager.GetPerk( 2 ) );
		Perk3 = GetPerkResource( GunsmithLoadoutManager.GetPerk( 3 ) );
	}

	private PerkResource GetPerkResource( string resourceName )
	{
		if ( string.IsNullOrEmpty( resourceName ) ) return null;

		foreach ( var perk in PerkResource.All )
		{
			if ( perk.ResourcePath.Equals( resourceName, System.StringComparison.OrdinalIgnoreCase ) ||
			     perk.ResourceName.Equals( resourceName, System.StringComparison.OrdinalIgnoreCase ) ||
			     perk.Name.Equals( resourceName, System.StringComparison.OrdinalIgnoreCase ) )
			{
				return perk;
			}
		}
		return null;
	}

	/// <summary>
	/// Returns true if the player has a perk with this exact name equipped.
	/// </summary>
	public bool HasPerk( string perkName )
	{
		if ( Perk1 != null && Perk1.Name.Equals( perkName, System.StringComparison.OrdinalIgnoreCase ) ) return true;
		if ( Perk2 != null && Perk2.Name.Equals( perkName, System.StringComparison.OrdinalIgnoreCase ) ) return true;
		if ( Perk3 != null && Perk3.Name.Equals( perkName, System.StringComparison.OrdinalIgnoreCase ) ) return true;

		return false;
	}
}
