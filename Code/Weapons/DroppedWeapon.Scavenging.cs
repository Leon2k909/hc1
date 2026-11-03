namespace Facepunch;

public partial class DroppedEquipment
{
	/// <summary>The compatible weapon in hand, if it has reserve space.</summary>
	public WeaponAmmo FindScavengeTarget( PlayerPawn player ) => FindScavengeTargets( player ).FirstOrDefault();

	private IEnumerable<WeaponAmmo> FindScavengeTargets( PlayerPawn player )
	{
		if ( !player.IsValid() || Resource is null || RoundsLeft <= 0 ) yield break;

		var candidates = player.Inventory.Equipment
			.Where( x => x == player.CurrentEquipment )
			.Where( x => x.IsValid() && x.Resource is not null )
			.Where( x => x.Resource == Resource
				|| (x.Resource.Category == Resource.Category && x.Resource.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary) );

		foreach ( var equipment in candidates )
		{
			var ammo = equipment.GetComponentInChildren<WeaponAmmo>( true );
			if ( ammo.IsValid() && ammo.ReserveAmmo < ammo.GetMaxReserve() ) yield return ammo;
		}
	}

	/// <summary>Refill the held weapon's reserve, leaving the dropped gun available for Use.</summary>
	private bool TryScavenge( PlayerPawn player )
	{
		var source = GetComponent<WeaponAmmo>();
		if ( !source.IsValid() ) return false;

		var scavenged = false;
		foreach ( var target in FindScavengeTargets( player ) )
		{
			var room = target.GetMaxReserve() - target.ReserveAmmo;
			// Keep the last loaded round so the physical gun can still be picked up and fired.
			var taken = Math.Min( room, source.ReserveAmmo + Math.Max( 0, source.Ammo - 1 ) );
			if ( taken <= 0 ) break;

			var fromReserve = Math.Min( taken, source.ReserveAmmo );
			source.ReserveAmmo -= fromReserve;
			source.Ammo -= taken - fromReserve;
			target.ReceiveReserve( taken );
			scavenged = true;
		}

		return scavenged;
	}
}
