using Sandbox;

namespace Facepunch;

public enum ZombiesBuyKind
{
	Perk,
	WallWeapon,
	MysteryBox,
}

/// <summary>
/// Something a player can spend points on by pressing Use: a perk machine, a wall-buy weapon
/// (buying it again refills ammo at half price), or the mystery box.
/// </summary>
public sealed class ZombiesBuyStation : Component, IUse, IMarkerObject
{
	public const int MysteryBoxCost = 950;
	public const float UseRange = 100f;

	[Property, Sync( SyncFlags.FromHost )] public ZombiesBuyKind Kind { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public ZombiesPerk Perk { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public string WeaponName { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public int Cost { get; set; }

	public static int PerkCost( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.Juggernog => 2500,
		ZombiesPerk.SpeedCola => 3000,
		ZombiesPerk.DoubleTap => 2000,
		ZombiesPerk.QuickRevive => 1500,
		ZombiesPerk.StaminUp => 2000,
		_ => 2000
	};

	public static string PerkName( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.Juggernog => "Juggernog",
		ZombiesPerk.SpeedCola => "Speed Cola",
		ZombiesPerk.DoubleTap => "Double Tap",
		ZombiesPerk.QuickRevive => "Quick Revive",
		ZombiesPerk.StaminUp => "Stamin-Up",
		_ => perk.ToString()
	};

	public static string PerkDescription( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.Juggernog => "More health",
		ZombiesPerk.SpeedCola => "Faster reloads",
		ZombiesPerk.DoubleTap => "Faster fire rate, double damage",
		ZombiesPerk.QuickRevive => "Faster revives, solo self-revive",
		ZombiesPerk.StaminUp => "Move faster",
		_ => ""
	};

	public static Color PerkColor( ZombiesPerk perk ) => perk switch
	{
		ZombiesPerk.Juggernog => new Color( 0.85f, 0.15f, 0.15f ),
		ZombiesPerk.SpeedCola => new Color( 0.2f, 0.85f, 0.3f ),
		ZombiesPerk.DoubleTap => new Color( 0.95f, 0.65f, 0.1f ),
		ZombiesPerk.QuickRevive => new Color( 0.3f, 0.6f, 1f ),
		ZombiesPerk.StaminUp => new Color( 1f, 0.9f, 0.2f ),
		_ => Color.White
	};

	public EquipmentResource Weapon => string.IsNullOrEmpty( WeaponName ) ? null
		: ResourceLibrary.GetAll<EquipmentResource>().FirstOrDefault( x =>
			x.ResourceName.Equals( WeaponName, StringComparison.OrdinalIgnoreCase ) );

	public string Title => Kind switch
	{
		ZombiesBuyKind.Perk => PerkName( Perk ),
		ZombiesBuyKind.WallWeapon => Weapon?.Name ?? WeaponName,
		ZombiesBuyKind.MysteryBox => "Mystery Box",
		_ => ""
	};

	/// <summary>What pressing Use would cost this player right now, and what it does.</summary>
	public (int cost, string action) GetOffer( PlayerPawn player )
	{
		switch ( Kind )
		{
			case ZombiesBuyKind.WallWeapon:
				if ( OwnsWeapon( player ) ) return (Cost / 2, $"Buy ammo for {Title}");
				return (Cost, $"Buy {Title}");
			case ZombiesBuyKind.Perk:
				return (Cost, $"Buy {Title} — {PerkDescription( Perk )}");
			default:
				return (Cost, "Open the Mystery Box");
		}
	}

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

		if ( Kind == ZombiesBuyKind.Perk && state is not null && state.HasPerk( Perk ) )
			return "You already have this perk";

		var (cost, _) = GetOffer( player );
		var eco = player.GetComponent<ZombiesPlayerEconomy>();
		if ( eco is null || eco.Points < cost )
			return $"Not enough points ({cost} needed)";

		return true;
	}

	void IUse.OnUse( PlayerPawn player )
	{
		if ( !Networking.IsHost ) return;
		if ( player is null || player.WorldPosition.Distance( WorldPosition ) > UseRange ) return;

		var eco = player.GetComponent<ZombiesPlayerEconomy>();
		var state = ZombiesPlayerState.For( player );
		if ( eco is null ) return;

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

			case ZombiesBuyKind.MysteryBox:
				var pool = ZombiesRoundSystem.GetMysteryBoxPool().ToList();
				if ( pool.Count == 0 ) return;
				if ( !eco.TrySpendPoints( cost ) ) return;
				var pick = pool[Game.Random.Int( 0, pool.Count - 1 )];
				player.Inventory.Give( pick, true );
				player.Inventory.RefillAmmo();
				using ( Rpc.FilterInclude( player.Network.Owner ) )
				{
					GameMode.Instance?.ShowToast( $"Mystery Box: {pick.Name}", Facepunch.UI.ToastType.Generic, 3 );
				}
				break;
		}

		Sound.Play( "sounds/ui/buy.sound", WorldPosition );
	}

	// ── Marker: floating label over the station ─────────────────────────────────
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 90f;
	string IMarkerObject.DisplayText => $"{Title} · {Cost}";
	// Hidden (tiny range) while the opening cinematic covers the screen.
	float IMarkerObject.MarkerMaxDistance => ZombiesRoundSystem.Current?.IntroPlaying == true ? 0.01f : UseRange;
	bool IMarkerObject.ShowChevron => false;
	string IMarkerObject.InputHint => "Use";
}
