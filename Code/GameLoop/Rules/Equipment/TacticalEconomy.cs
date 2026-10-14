namespace Facepunch;

public enum TacticalGear
{
	Armor,
	ArmorAndHelmet,
	DefuseKit
}

/// <summary>Host-authoritative buying for Tactical Defuse. Classes do not supply free equipment.</summary>
public sealed class TacticalEconomy : Component
{
	public const int ArmorPrice = 650;
	public const int HelmetPrice = 350;
	public const int DefuseKitPrice = 400;

	public static TacticalEconomy Current => GameMode.Instance?.Get<TacticalEconomy>();

	public static bool CanBuy( PlayerPawn player )
	{
		if ( !Current.IsValid() || !player.IsValid() || !player.Client.IsValid()
			|| player.HealthComponent?.State != LifeState.Alive
			|| player.Team is not (Team.Terrorist or Team.CounterTerrorist) )
			return false;

		// Read the active rule, so a late RPC cannot buy after the phase ends.
		return GameMode.Instance.Get<EnableBuyMenu>()?.BuyMenuMode == BuyMenuMode.EnabledEverywhere;
	}

	public static bool IsAvailable( EquipmentResource resource, Team team ) =>
		resource.IsValid() && EquipmentResource.All.Contains( resource )
		&& resource.IsPurchasable && !resource.IsWip && resource.Price > 0
		&& resource.IsPurchasableForTeam( team )
		&& resource.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary or EquipmentSlot.Utility
			or EquipmentSlot.Tactical or EquipmentSlot.Lethal
		&& resource.MainPrefab.IsValid() && resource.MainPrefab.GetComponentInChildren<Equipment>( true ).IsValid();

	public static IEnumerable<EquipmentResource> Catalog( Team team ) => EquipmentResource.All
		.Where( x => IsAvailable( x, team ) ).OrderBy( x => x.Price ).ThenBy( x => x.Name );

	/// <summary>Null means the gear is already owned or this team/mode cannot buy it.</summary>
	public static int? GearPrice( PlayerPawn player, TacticalGear gear )
	{
		if ( !Current.IsValid() || !player.IsValid() || !player.ArmorComponent.IsValid() ) return null;
		var armor = player.ArmorComponent;
		return gear switch
		{
			TacticalGear.Armor when armor.ArmorEnabled && armor.Armor < armor.MaxArmor => ArmorPrice,
			TacticalGear.ArmorAndHelmet when armor.HelmetsEnabled && (!armor.HasHelmet || armor.Armor < armor.MaxArmor)
				=> (armor.Armor < armor.MaxArmor ? ArmorPrice : 0) + (armor.HasHelmet ? 0 : HelmetPrice),
			TacticalGear.DefuseKit when player.Team == Team.CounterTerrorist && !player.Inventory.HasDefuseKit => DefuseKitPrice,
			_ => null
		};
	}

	public bool TryBuyEquipment( PlayerPawn player, EquipmentResource resource )
	{
		if ( !Networking.IsHost || !CanBuy( player ) || !IsAvailable( resource, player.Team )
			|| player.Client.Balance < resource.Price || player.Inventory.Has( resource ) ) return false;

		// Give handles replacing the slot and dropping the old weapon. Charge only after a successful grant.
		var equipment = player.Inventory.Give( resource, true, applySavedAttachments: false );
		if ( !equipment.IsValid() ) return false;
		player.Client.Balance -= resource.Price;
		return true;
	}

	public bool TryBuyGear( PlayerPawn player, TacticalGear gear )
	{
		if ( !Networking.IsHost || !CanBuy( player ) || GearPrice( player, gear ) is not { } price
			|| player.Client.Balance < price ) return false;

		switch ( gear )
		{
			case TacticalGear.Armor:
				player.ArmorComponent.Armor = player.ArmorComponent.MaxArmor;
				break;
			case TacticalGear.ArmorAndHelmet:
				player.ArmorComponent.Armor = player.ArmorComponent.MaxArmor;
				player.ArmorComponent.HasHelmet = true;
				break;
			case TacticalGear.DefuseKit:
				player.Inventory.HasDefuseKit = true;
				break;
			default:
				return false;
		}
		player.Client.Balance -= price;
		return true;
	}
}
