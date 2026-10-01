using Facepunch.Gunsmith;
using Sandbox;

namespace Facepunch;

/// <summary> What the Zombies workbench sells (<see cref="ZombiesBuyStation.Buy"/>). </summary>
public enum ZombiesWorkbenchItem
{
	/// <summary> One armour plate, <see cref="ZombiesBuyStation.PlateArmor"/>. </summary>
	ArmorPlate,

	/// <summary> Every plate the vest is missing. </summary>
	ArmorFill,

	/// <summary> One gun's spare ammo, back up to its basic load. </summary>
	Ammo,

	/// <summary> Every gun's spare ammo. </summary>
	AmmoAll,

	/// <summary> An HE grenade, for an empty lethal slot. </summary>
	Grenade,
}

/// <summary>
/// The workbench (<see cref="ZombiesBuyKind.Workbench"/>), like CoD Zombies' crafting table. Use opens its menu,
/// <see cref="Facepunch.UI.ZombiesWorkbenchPanel"/>, on the player's own machine; the host's Use does nothing.
/// <para>Attachments are free. They're the player's own gunsmith build, kept in their cookies, so the menu saves and fits
/// them itself (<see cref="RefitAttachments"/>), from the parts their weapon levels have unlocked. Armour, ammo and
/// grenades cost points, paid on the host through <see cref="Buy"/>.</para>
/// </summary>
public sealed partial class ZombiesBuyStation
{
	/// <summary> One plate. Plates take damage point for point before health (ZombiesPlayerState.AbsorbWithArmor). </summary>
	public const int PlateArmor = 50;
	public const int MaxPlates = 3;
	public const int MaxArmor = PlateArmor * MaxPlates;

	/// <summary> Points per point of armour: 250 a plate, 750 for a full vest. A zombie's swipe (45) takes most of a plate. </summary>
	public const int ArmorPointCost = 5;

	/// <summary> A primary's full spare ammo, the same as its wall-buy's refill. A secondary's is half that. </summary>
	public const int PrimaryAmmoCost = 500;
	public const int SecondaryAmmoCost = 250;

	public const int GrenadeCost = 250;
	public const string GrenadeResourcePath = "weapons/throwable/he_grenade/he_grenade.equip";

	/// <summary> How far away the menu stays open: a step back from where Use reaches doesn't shut it. </summary>
	public const float WorkbenchRange = UseRange + 60f;

	public static EquipmentResource GrenadeResource => ResourceLibrary.GetAll<EquipmentResource>()
		.FirstOrDefault( x => x.ResourcePath.Equals( GrenadeResourcePath, StringComparison.OrdinalIgnoreCase ) );

	/// <summary> Whether <paramref name="player"/> can work at this bench: in reach, alive and not downed. </summary>
	public bool CanWorkAt( PlayerPawn player ) => Kind == ZombiesBuyKind.Workbench && player.IsValid()
		&& player.HealthComponent.IsValid() && player.HealthComponent.State == LifeState.Alive
		&& ZombiesPlayerState.For( player )?.IsDowned != true
		&& player.WorldPosition.Distance( WorldPosition ) <= WorkbenchRange;

	// ── Prices ──────────────────────────────────────────────────────────────────

	/// <summary> The armour a purchase adds: one plate, or everything up to a full vest (<paramref name="fill"/>). </summary>
	public static float ArmorToAdd( PlayerPawn player, bool fill )
	{
		var armor = player?.ArmorComponent;
		if ( !armor.IsValid() ) return 0f;

		var missing = Math.Max( 0f, MaxArmor - armor.Armor );
		var add = fill ? missing : Math.Min( PlateArmor, missing );
		return add < 1f ? 0f : add;
	}

	public static int ArmorCost( PlayerPawn player, bool fill ) => RoundPrice( ArmorToAdd( player, fill ) * ArmorPointCost );

	/// <summary> The player's guns the bench has ammo for: the primary and secondary, not the knife or grenades. </summary>
	public static IEnumerable<Equipment> AmmoWeapons( PlayerPawn player ) => player?.Inventory?.Equipment
		.Where( x => x.IsValid() && x.Resource is not null
			&& (x.Resource.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary)
			&& x.GetComponentInChildren<WeaponAmmo>() is not null )
		.OrderBy( x => x.Resource.Slot ) ?? Enumerable.Empty<Equipment>();

	/// <summary> The spare rounds <paramref name="weapon"/> is short of its basic load. </summary>
	public static int MissingReserve( Equipment weapon ) =>
		weapon.IsValid() && weapon.GetComponentInChildren<WeaponAmmo>() is { } ammo
			? Math.Max( 0, ammo.GetMaxReserve() - ammo.ReserveAmmo )
			: 0;

	/// <summary> What topping up <paramref name="weapon"/>'s spare ammo costs: its share of a full load's price. </summary>
	public static int AmmoCost( Equipment weapon )
	{
		var missing = MissingReserve( weapon );
		if ( missing <= 0 ) return 0;

		var max = Math.Max( 1, weapon.GetComponentInChildren<WeaponAmmo>().GetMaxReserve() );
		var full = weapon.Resource?.Slot == EquipmentSlot.Primary ? PrimaryAmmoCost : SecondaryAmmoCost;
		return RoundPrice( full * (float)missing / max );
	}

	public static int AmmoAllCost( PlayerPawn player ) => AmmoWeapons( player ).Sum( AmmoCost );

	/// <summary> Why <paramref name="player"/> can't take a grenade from the bench, or null if they can. </summary>
	public static string GrenadeBlocked( PlayerPawn player )
	{
		if ( GrenadeResource is null || player?.Inventory is null ) return "Out of stock";
		if ( player.Inventory.HasInSlot( EquipmentSlot.Lethal ) ) return "Lethal slot full";
		return null;
	}

	/// <summary> Prices go up in tens, like everything else in Zombies. </summary>
	private static int RoundPrice( float points ) => points <= 0f ? 0 : Math.Max( 10, (int)MathF.Ceiling( points / 10f ) * 10 );

	// ── Buying ──────────────────────────────────────────────────────────────────

	/// <summary>
	/// Client → host: buy <paramref name="item"/> here. <paramref name="weapon"/> is the gun for
	/// <see cref="ZombiesWorkbenchItem.Ammo"/>. The host checks the reach and the price again.
	/// </summary>
	[Rpc.Host]
	public void Buy( ZombiesWorkbenchItem item, Equipment weapon )
	{
		var caller = Rpc.Caller;
		var player = GameUtils.AllPlayers.FirstOrDefault( x => x.Network.Owner == caller )?.PlayerPawn;
		if ( !Networking.IsHost || !CanWorkAt( player ) ) return;

		var eco = player.GetComponent<ZombiesPlayerEconomy>();
		if ( eco is null ) return;

		switch ( item )
		{
			case ZombiesWorkbenchItem.ArmorPlate:
			case ZombiesWorkbenchItem.ArmorFill:
			{
				var fill = item == ZombiesWorkbenchItem.ArmorFill;
				var add = ArmorToAdd( player, fill );
				if ( add <= 0f || !eco.TrySpendPoints( ArmorCost( player, fill ) ) ) return;
				player.ArmorComponent.Armor = Math.Min( MaxArmor, player.ArmorComponent.Armor + add );
				break;
			}

			case ZombiesWorkbenchItem.Ammo:
			{
				if ( !AmmoWeapons( player ).Contains( weapon ) ) return;
				var missing = MissingReserve( weapon );
				if ( missing <= 0 || !eco.TrySpendPoints( AmmoCost( weapon ) ) ) return;
				// The owner holds the synced ammo count, so it adds the rounds itself.
				weapon.GetComponentInChildren<WeaponAmmo>().ReceiveReserve( missing );
				break;
			}

			case ZombiesWorkbenchItem.AmmoAll:
			{
				var weapons = AmmoWeapons( player ).Where( x => MissingReserve( x ) > 0 ).ToList();
				if ( weapons.Count == 0 || !eco.TrySpendPoints( weapons.Sum( AmmoCost ) ) ) return;
				foreach ( var gun in weapons )
					gun.GetComponentInChildren<WeaponAmmo>().ReceiveReserve( MissingReserve( gun ) );
				break;
			}

			case ZombiesWorkbenchItem.Grenade:
			{
				if ( GrenadeBlocked( player ) is not null || !eco.TrySpendPoints( GrenadeCost ) ) return;
				player.Inventory.Give( GrenadeResource, false );
				break;
			}

			default:
				return;
		}

		using ( Rpc.FilterInclude( caller ) )
		{
			Bought( item );
		}
	}

	/// <summary> Host → the buyer: it went through. </summary>
	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void Bought( ZombiesWorkbenchItem item )
	{
		Sound.Play( "sounds/ui/buy.sound" );
		Facepunch.UI.ZombiesWorkbenchPanel.NotifyBought( item );
	}

	// ── Attachments ─────────────────────────────────────────────────────────────

	/// <summary>
	/// Fits <paramref name="weapon"/>'s saved attachments again, on the owner's machine, after the menu changes one: the
	/// viewmodel, the world model in the hands or on the back, and the magazine's capacity and reload. Other players see
	/// the world model with their own saved build, as they always do.
	/// </summary>
	public static void RefitAttachments( Equipment weapon )
	{
		if ( !weapon.IsValid() || !weapon.Resource.IsValid() || !weapon.ApplySavedAttachments ) return;

		var resource = weapon.Resource;
		if ( weapon.ViewModel.IsValid() )
			GunsmithLoadoutManager.ApplyAttachments( resource, weapon.ViewModel.GameObject );
		if ( weapon.WorldModel.IsValid() )
			GunsmithLoadoutManager.ApplyAttachments( resource, weapon.WorldModel.GameObject );

		var mounts = weapon.Owner.IsValid() ? weapon.Owner.GetComponentInChildren<EquipmentMountPoints>() : null;
		var mount = mounts.IsValid() ? mounts.GetMount( weapon ) : null;
		if ( mount is not null && mount.Mounted.TryGetValue( weapon, out var mounted ) && mounted.IsValid() )
			GunsmithLoadoutManager.ApplyAttachments( resource, mounted );

		weapon.RefreshAmmunitionLoadout();
	}

	// ── The bench itself ────────────────────────────────────────────────────────

	/// <summary> The user's own workbench, modelled in Blender and baked by Tools/zombies_workbench.py. </summary>
	internal const string BenchModelPath = "models/zombies/workbench/workbench.vmdl";

	/// <summary>
	/// The user's workbench (<see cref="BenchModelPath"/>): facing +X like the other stations, its back at x -20, 72
	/// wide and 86 tall to the shop light over its top shelf. The wood shavings on the floor reach 13 past the station's
	/// box. If the model hasn't compiled, the stand-in (<see cref="CreateStandInBench"/>).
	/// </summary>
	internal static void CreateBenchModel( GameObject parent )
	{
		var model = Model.Load( BenchModelPath );
		if ( model is null || model.IsError )
		{
			Log.Warning( $"Zombies workbench: {BenchModelPath} didn't load, building the stand-in" );
			CreateStandInBench( parent );
			return;
		}

		var bench = new GameObject( parent, true, "Workbench" );
		bench.Components.Create<ModelRenderer>().Model = model;
	}

	/// <summary>
	/// A steel-legged workbench with a pegboard back: a rifle lying on the top with a sight and a suppressor beside it, a
	/// vise, a plate carrier's plates against the pegboard and an ammo can on the shelf. Built from dev boxes and the
	/// game's own weapon models, facing +X like the other stations, 40 deep, 72 wide and 72 tall.
	/// </summary>
	private static void CreateStandInBench( GameObject parent )
	{
		var wood = new Color( 0.42f, 0.29f, 0.17f );
		var darkWood = new Color( 0.26f, 0.18f, 0.11f );
		var steel = new Color( 0.16f, 0.17f, 0.18f );
		var board = new Color( 0.33f, 0.31f, 0.27f );
		var plate = new Color( 0.25f, 0.28f, 0.19f );

		const float top = 40f;

		AddBox( parent, "Top", new Vector3( 0, 0, top - 1.5f ), new Vector3( 34, 72, 3 ), wood );
		foreach ( var x in new[] { -14f, 14f } )
		{
			foreach ( var y in new[] { -33f, 33f } )
				AddBox( parent, "Leg", new Vector3( x, y, (top - 3f) * 0.5f ), new Vector3( 3, 3, top - 3f ), steel );
		}
		AddBox( parent, "Shelf", new Vector3( 0, 0, 10 ), new Vector3( 30, 68, 1.5f ), darkWood );
		AddBox( parent, "Pegboard", new Vector3( -16, 0, top + 16 ), new Vector3( 1.5f, 70, 32 ), board );
		AddBox( parent, "Pegboard rail", new Vector3( -15, 0, top + 31.5f ), new Vector3( 3, 72, 1.5f ), steel );

		// Two armour plates leaning on the pegboard, left of centre.
		AddBox( parent, "Armour plate", new Vector3( -13.5f, -26, top + 7 ), new Vector3( 1.2f, 10, 13 ), plate );
		AddBox( parent, "Armour plate", new Vector3( -12, -15, top + 7 ), new Vector3( 1.2f, 10, 13 ), plate );

		// Tools hanging on the pegboard.
		AddBox( parent, "Wrench", new Vector3( -14.8f, 6, top + 18 ), new Vector3( 0.6f, 1.2f, 11 ), steel );
		AddBox( parent, "Hammer handle", new Vector3( -14.8f, 12, top + 17 ), new Vector3( 0.8f, 1.4f, 12 ), darkWood );
		AddBox( parent, "Hammer head", new Vector3( -14.6f, 12, top + 23 ), new Vector3( 1.4f, 5, 1.8f ), steel );
		AddBox( parent, "Pliers", new Vector3( -14.8f, 18, top + 19 ), new Vector3( 0.6f, 2, 8 ), new Color( 0.55f, 0.12f, 0.1f ) );

		// A bench vise on the right-hand end.
		AddBox( parent, "Vise base", new Vector3( 8, 28, top + 1 ), new Vector3( 8, 6, 2 ), steel );
		AddBox( parent, "Vise jaw", new Vector3( 11, 28, top + 4 ), new Vector3( 2, 6, 4 ), steel );
		AddBox( parent, "Vise jaw", new Vector3( 6, 28, top + 4 ), new Vector3( 2, 6, 4 ), steel );
		AddBox( parent, "Vise screw", new Vector3( 14, 28, top + 3.5f ), new Vector3( 4, 0.8f, 0.8f ), steel );

		// A rifle lying on its side, barrel to the right, with a sight and a suppressor next to it.
		var rifle = ResourceLibrary.GetAll<EquipmentResource>()
			.FirstOrDefault( x => x.ResourcePath.Equals( "weapons/m4a1/m4a1.equip", StringComparison.OrdinalIgnoreCase ) )?.WorldModel
			?? ZombiesRoundSystem.GetWeaponCratePool().FirstOrDefault( x => x.Slot == EquipmentSlot.Primary )?.WorldModel;
		AddLyingModel( parent, "Rifle", rifle, new Vector3( 4, -4, top ), 34f );
		AddLyingModel( parent, "Sight", Model.Load( "attachments/m4a1/optics/reflex.vmdl" ), new Vector3( -5, 8, top ), 5f );
		AddLyingModel( parent, "Suppressor", Model.Load( "attachments/m4a1/rifle_suppressor/rifle_suppressor.vmdl" ), new Vector3( -4, -22, top ), 9f );

		// An ammo can on the shelf.
		var can = new GameObject( parent, true, "Ammo can" );
		can.LocalPosition = new Vector3( 2, -18, 10.75f + 8f );
		can.LocalScale = 0.8f;
		ZombiesPowerUp.CreateAmmoCase( can );
	}

	private static void AddBox( GameObject parent, string name, Vector3 center, Vector3 size, Color tint )
	{
		var part = new GameObject( parent, true, name );
		var renderer = part.Components.Create<ModelRenderer>();
		renderer.Model = Model.Load( "models/dev/box.vmdl" );
		renderer.Tint = tint;
		var bounds = renderer.Model.Bounds;
		part.LocalScale = new Vector3( size.x / bounds.Size.x, size.y / bounds.Size.y, size.z / bounds.Size.z );
		part.LocalPosition = center - bounds.Center * part.LocalScale;
	}

	/// <summary>
	/// Lays <paramref name="model"/> on its left side on the bench top at <paramref name="spot"/>, its length (its X)
	/// along the bench and scaled down to <paramref name="length"/> at most.
	/// </summary>
	private static void AddLyingModel( GameObject parent, string name, Model model, Vector3 spot, float length )
	{
		if ( model is null || model.IsError ) return;

		var bounds = model.Bounds;
		var scale = Math.Min( 1f, length / Math.Max( bounds.Size.x, 1f ) );
		var go = new GameObject( parent, true, name );
		// Rolled onto its side (its left, +Y, facing up), then turned so the muzzle points along the bench.
		go.LocalRotation = Rotation.FromYaw( 90f ) * Rotation.FromRoll( 90f );
		go.LocalScale = scale;
		var lift = bounds.Size.y * scale * 0.5f;
		go.LocalPosition = spot + Vector3.Up * lift - go.LocalRotation * bounds.Center * scale;
		go.Components.Create<ModelRenderer>().Model = model;
	}
}
