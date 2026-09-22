using Facepunch;
using Facepunch.Gunsmith;

namespace SWB.Base;

public partial class Weapon
{
	[Property, Sync] public EquipmentResource GunsmithResource { get; set; }

	internal void RefreshAmmunitionLoadout( ShootInfo shootInfo )
	{
		if ( IsProxy || !Owner.IsValid() || Owner.IsBot || !GunsmithResource.IsValid() || !shootInfo.IsValid() ) return;
		shootInfo.UsesTracerRounds = GunsmithLoadoutManager.UsesTracerRounds( GunsmithResource );
	}
}
