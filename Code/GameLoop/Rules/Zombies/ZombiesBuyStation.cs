using Sandbox;

namespace Facepunch;

public enum ZombiesBuyKind
{
	Perk,
	WallWeapon,
	WeaponCrate,
	AmmoBox,
	Workbench,
}

/// <summary>
/// Something a player can spend points on by pressing Use: a perk machine, a wall-buy weapon
/// (buying it again refills ammo at half price), the weapon crate, an ammo box, or the workbench, whose menu
/// (<see cref="Facepunch.UI.ZombiesWorkbenchPanel"/>) changes attachments and sells armour, ammo and grenades
/// (ZombiesWorkbench.cs).
/// </summary>
public sealed partial class ZombiesBuyStation : Component, IUse, IMarkerObject
{
	public const int WeaponCrateCost = 950;
	public const int AmmoBoxCost = 1000;
	public const float UseRange = 100f;

	[Property, Sync( SyncFlags.FromHost )] public ZombiesBuyKind Kind { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public ZombiesPerk Perk { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public string WeaponName { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public int Cost { get; set; }

	public static int PerkCost( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.IronTonic => 2500,
		ZombiesPerk.BoltSoda => 3000,
		ZombiesPerk.HotShot => 2000,
		ZombiesPerk.SecondWind => 1500,
		ZombiesPerk.FleetFoot => 2000,
		_ => 2000
	};

	public static string PerkName( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.IronTonic => "Iron Tonic",
		ZombiesPerk.BoltSoda => "Bolt Soda",
		ZombiesPerk.HotShot => "Hot Shot",
		ZombiesPerk.SecondWind => "Second Wind",
		ZombiesPerk.FleetFoot => "Fleet Foot",
		_ => perk.ToString()
	};

	public static string PerkDescription( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.IronTonic => "More health",
		ZombiesPerk.BoltSoda => "Faster reloads",
		ZombiesPerk.HotShot => "Faster fire rate, double damage",
		ZombiesPerk.SecondWind => "Faster revives, solo self-revive",
		ZombiesPerk.FleetFoot => "Move faster",
		_ => ""
	};

	public static Color PerkColor( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.IronTonic => new Color( 0.85f, 0.15f, 0.15f ),
		ZombiesPerk.BoltSoda => new Color( 0.2f, 0.85f, 0.3f ),
		ZombiesPerk.HotShot => new Color( 0.95f, 0.65f, 0.1f ),
		ZombiesPerk.SecondWind => new Color( 0.3f, 0.6f, 1f ),
		ZombiesPerk.FleetFoot => new Color( 1f, 0.55f, 0.15f ),
		_ => Color.White
	};

	/// <summary>
	/// The perk's artwork name: Perks/&lt;art&gt;_poster.vmat and _sign.vmat on the dispenser, ui/zombies/perks/&lt;art&gt;.png
	/// on the HUD (all made by Assets/Perks/build_perk_art.py).
	/// </summary>
	public static string PerkArt( ZombiesPerk perk ) => perk.ToString().ToLowerInvariant();

	public EquipmentResource Weapon => string.IsNullOrEmpty( WeaponName ) ? null
		: ResourceLibrary.GetAll<EquipmentResource>().FirstOrDefault( x =>
			x.ResourceName.Equals( WeaponName, StringComparison.OrdinalIgnoreCase ) );

	public string Title => Kind switch
	{
		ZombiesBuyKind.Perk => PerkName( Perk ),
		ZombiesBuyKind.WallWeapon => Weapon?.Name ?? WeaponName,
		ZombiesBuyKind.WeaponCrate => "Weapon Crate",
		ZombiesBuyKind.AmmoBox => "Ammo Box",
		ZombiesBuyKind.Workbench => "Workbench",
		_ => ""
	};

	/// <summary>
	/// <see cref="Title"/> as it's shown: the station's own name in the player's language. Guns and perks keep their names.
	/// </summary>
	private string ShownTitle => Kind is ZombiesBuyKind.WeaponCrate or ZombiesBuyKind.AmmoBox or ZombiesBuyKind.Workbench ? Tr( Title ) : Title;

	/// <summary>What pressing Use would cost this player right now, and what it does (in the player's language, for the prompt).</summary>
	public (int cost, string action) GetOffer( PlayerPawn player )
	{
		switch ( Kind )
		{
			case ZombiesBuyKind.WallWeapon:
				if ( OwnsWeapon( player ) ) return (Cost / 2, Tr( "Buy ammo for {0}", Title ));
				return (Cost, Tr( "Buy {0}", Title ));
			case ZombiesBuyKind.Perk:
				return (Cost, Tr( "Buy {0} — {1}", Title, Tr( PerkDescription( Perk ) ) ));
			case ZombiesBuyKind.AmmoBox:
				return (Cost, Tr( "Refill all ammo" ));
			case ZombiesBuyKind.Workbench:
				return (0, Tr( "Open the Workbench" ));
			default:
				return (Cost, Tr( "Open the Weapon Crate" ));
		}
	}

	public bool HasAmmoToRefill( PlayerPawn player ) => player is not null && player.Inventory.Equipment.Any( equipment =>
		equipment.IsValid() && equipment.GetComponentInChildren<WeaponAmmo>() is { } ammo &&
		(ammo.Ammo < ammo.GetEffectiveMaxAmmo() || ammo.ReserveAmmo < ammo.GetMaxReserve()) );

	private bool OwnsWeapon( PlayerPawn player )
	{
		var res = Weapon;
		return res is not null && player.Inventory.Equipment.Any( x => x.IsValid() && x.Resource == res );
	}

	UseResult IUse.CanUse( PlayerPawn player )
	{
		if ( player is null || player.WorldPosition.Distance( WorldPosition ) > UseRange ) return false;

		var state = ZombiesPlayerState.For( player );
		if ( state?.IsDowned == true ) return false;

		// The workbench's menu opens on the player's own machine (ZombiesWorkbenchPanel); its purchases are Buy RPCs.
		if ( Kind == ZombiesBuyKind.Workbench ) return true;

		if ( Kind == ZombiesBuyKind.Perk && state is not null && state.HasPerk( Perk ) )
			return "You already have this perk";
		if ( Kind == ZombiesBuyKind.AmmoBox && !HasAmmoToRefill( player ) )
			return "Ammo already full";

		var (cost, _) = GetOffer( player );
		var eco = player.GetComponent<ZombiesPlayerEconomy>();
		if ( eco is null || eco.Points < cost )
			return $"Not enough points ({cost} needed)";

		return true;
	}

	void IUse.OnUse( PlayerPawn player )
	{
		if ( !Networking.IsHost || Kind == ZombiesBuyKind.Workbench ) return;
		if ( player is null || player.WorldPosition.Distance( WorldPosition ) > UseRange ) return;

		var eco = player.GetComponent<ZombiesPlayerEconomy>();
		var state = ZombiesPlayerState.For( player );
		if ( eco is null || state?.IsDowned == true || player.HealthComponent.State != LifeState.Alive ) return;

		var (cost, _) = GetOffer( player );

		switch ( Kind )
		{
			case ZombiesBuyKind.Perk:
				if ( state is null || state.HasPerk( Perk ) ) return;
				if ( !eco.TrySpendPoints( cost ) ) return;
				state.GivePerk( Perk );
				break;

			case ZombiesBuyKind.WallWeapon:
				var res = Weapon;
				if ( res is null ) return;
				var owned = OwnsWeapon( player );
				if ( !eco.TrySpendPoints( cost ) ) return;
				if ( !owned ) player.Inventory.Give( res, true );
				player.Inventory.RefillAmmo();
				break;

			case ZombiesBuyKind.WeaponCrate:
				var pool = ZombiesRoundSystem.GetWeaponCratePool().ToList();
				if ( pool.Count == 0 ) return;
				if ( !eco.TrySpendPoints( cost ) ) return;
				var pick = pool[Game.Random.Int( 0, pool.Count - 1 )];
				player.Inventory.Give( pick, true );
				player.Inventory.RefillAmmo();
				using ( Rpc.FilterInclude( player.Network.Owner ) )
				{
					GameMode.Instance?.ShowToast( $"Weapon Crate: {pick.Name}", Facepunch.UI.ToastType.Generic, 3 );
				}
				break;

			case ZombiesBuyKind.AmmoBox:
				if ( !HasAmmoToRefill( player ) || !eco.TrySpendPoints( cost ) ) return;
				player.Inventory.RefillAmmo();
				break;
		}

		Sound.Play( "sounds/ui/buy.sound", WorldPosition );
	}

	// ── Marker: floating label over the station ─────────────────────────────────
	// Perk dispensers are taller, and their name sign would sit behind the label.
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * (Kind == ZombiesBuyKind.Perk ? 112f : 90f);
	string IMarkerObject.DisplayText => Kind == ZombiesBuyKind.Workbench ? ShownTitle : $"{ShownTitle} · {Cost}";
	// Hidden (tiny range) while the opening cinematic covers the screen.
	float IMarkerObject.MarkerMaxDistance => ZombiesRoundSystem.Current?.IntroPlaying == true ? 0.01f : UseRange;
	bool IMarkerObject.ShowChevron => false;
	string IMarkerObject.InputHint => "Use";
}
