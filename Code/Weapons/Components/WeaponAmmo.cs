namespace Facepunch;

/// <summary>
/// An ammo container. It holds ammo for a weapon.
/// </summary>
[Title( "Ammo" ), Group( "Weapon Components" )]
public partial class WeaponAmmo : Component, IDroppedWeaponState<WeaponAmmo>
{
	/// <summary>
	/// How much ammo are we holding?
	/// </summary>
	[Property, Sync] public int Ammo { get; set; } = 0;

	[Property] public int MaxAmmo { get; set; } = 30;

	/// <summary>
	/// Do we have any ammo?
	/// </summary>
	[Property] public bool HasAmmo => Ammo > 0;

	/// <summary>
	/// Maximum ammo after applying the player's mag-size tuning (+10 = +40%).
	/// </summary>
	public int GetEffectiveMaxAmmo()
	{
		var equip = Components.Get<Equipment>( FindMode.InParent );
		if ( equip?.Resource is null ) return MaxAmmo;
		var tune = WeaponTuningManager.GetTuning( equip.Resource.ResourceName );
		return (int)(MaxAmmo * (1f + tune.MagSize * 0.04f));
	}

	/// <summary>
	/// Is this container full (accounting for tuned mag size)?
	/// </summary>
	public bool IsFull => Ammo == GetEffectiveMaxAmmo();
}
