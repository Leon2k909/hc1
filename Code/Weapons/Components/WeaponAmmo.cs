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
	/// Spare rounds carried for this weapon (not counting what's loaded). Reloads draw from here.
	/// </summary>
	[Property, Sync] public int ReserveAmmo { get; set; } = 0;

	/// <summary>
	/// Spare magazines a soldier carries for this weapon. -1 picks a realistic basic load from the weapon category.
	/// </summary>
	[Property] public int SpareMagazines { get; set; } = -1;

	/// <summary>
	/// Spare magazines by weapon category, modelled on an infantry basic load
	/// (a rifleman carries 7 x 30: one in the gun, six on the vest).
	/// </summary>
	public static int DefaultSpareMagazines( WeaponCategory category ) => category switch
	{
		WeaponCategory.AssaultRifle => 6,
		WeaponCategory.SMG => 6,
		WeaponCategory.Marksman => 6,
		WeaponCategory.Sniper => 5,
		WeaponCategory.LMG => 3,
		WeaponCategory.Shotgun => 4,
		WeaponCategory.Pistol => 5,
		WeaponCategory.Launcher => 3,
		_ => 4
	};

	/// <summary>
	/// Most spare rounds this weapon can carry.
	/// </summary>
	public int GetMaxReserve()
	{
		var mags = SpareMagazines;
		if ( mags < 0 )
		{
			var equip = Components.Get<Equipment>( FindMode.InParent );
			mags = DefaultSpareMagazines( equip?.Resource?.Category ?? WeaponCategory.None );
		}
		return Math.Max( 0, mags * GetEffectiveMaxAmmo() );
	}

	/// <summary>
	/// Fill the magazine and the spare ammo.
	/// </summary>
	public void RefillAll()
	{
		Ammo = GetEffectiveMaxAmmo();
		ReserveAmmo = GetMaxReserve();
	}

	/// <summary>
	/// Host → owner: hand over scavenged rounds. The owner applies them, since it owns the synced value.
	/// </summary>
	[Rpc.Owner]
	public void ReceiveReserve( int rounds )
	{
		AddReserve( rounds );
	}

	/// <summary>
	/// Add spare rounds (e.g. scavenged). Returns how many were actually taken.
	/// </summary>
	public int AddReserve( int rounds )
	{
		var take = Math.Clamp( rounds, 0, Math.Max( 0, GetMaxReserve() - ReserveAmmo ) );
		ReserveAmmo += take;
		return take;
	}

	/// <summary>
	/// Do we have any ammo?
	/// </summary>
	[Property] public bool HasAmmo => Ammo > 0;

	/// <summary>
	/// Fitted magazine capacity, or the weapon's default capacity (with optional tuning while tuning is on).
	/// </summary>
	public int GetEffectiveMaxAmmo()
	{
		var equip = Components.Get<Equipment>( FindMode.InParent );
		if ( equip?.Resource is null ) return MaxAmmo;
		// A fitted magazine has a physical round count. Weapon tuning cannot
		// turn a marked 15/30/45/60-round magazine into another capacity.
		if ( equip.AttachmentMagazineCapacity > 0 ) return equip.AttachmentMagazineCapacity;
		return MaxAmmo;
		// Weapon tuning is off (see WeaponTuningManager). Put back with tuning:
		// var tune = WeaponTuningManager.GetTuning( equip.Resource.ResourceName );
		// return Math.Max( 1, (int)(MaxAmmo * (1f + tune.MagSize * 0.04f)) );
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
