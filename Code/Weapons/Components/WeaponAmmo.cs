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
	/// Does this weapon hold a round in the chamber? If so a tactical reload leaves a full magazine
	/// plus that chambered round — the classic 30+1. Reloading from empty has nothing to keep, so it
	/// only gives you a full magazine.
	/// </summary>
	[Property] public bool HasChamber { get; set; } = true;

	/// <summary>
	/// Total rounds the weapon can hold, chambered round included.
	/// </summary>
	public int GetMaxAmmoWithChamber() => GetEffectiveMaxAmmo() + ( HasChamber ? 1 : 0 );

	/// <summary>
	/// 1 while a round is sat in the chamber, otherwise 0.
	/// </summary>
	public int ChamberedRounds => HasChamber && Ammo > 0 ? 1 : 0;

	/// <summary>
	/// Rounds in the magazine — everything except the chambered one.
	/// </summary>
	public int AmmoInMagazine => Ammo - ChamberedRounds;

	/// <summary>
	/// Is this container full (accounting for tuned mag size and the chambered round)?
	/// </summary>
	public bool IsFull => Ammo >= GetEffectiveMaxAmmo() + ChamberedRounds;
}
