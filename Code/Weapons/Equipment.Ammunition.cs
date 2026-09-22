using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Equipment
{
	[Sync] public bool UsesTracerRounds { get; private set; }
	[Sync] public int AttachmentMagazineCapacity { get; private set; }
	[Sync] public float AttachmentReloadMultiplier { get; private set; } = 1f;

	internal void RefreshAmmunitionLoadout()
	{
		// Cookies belong to this client. Never apply them to another player's weapon or a bot.
		if ( IsProxy || !Owner.IsValid() || !Owner.IsLocallyControlled ) return;
		UsesTracerRounds = GunsmithLoadoutManager.UsesTracerRounds( Resource );
		var oldCapacity = AttachmentMagazineCapacity;
		var hasMagazine = GunsmithLoadoutManager.TryGetAttachment( Resource, GunsmithPartType.Magazine, out var magazine ) && magazine.IsValid();
		AttachmentMagazineCapacity = hasMagazine ? Math.Max( 0, magazine.MagazineCapacity ) : 0;
		AttachmentReloadMultiplier = hasMagazine ? magazine.ReloadTimeMultiplier.Clamp( 0.5f, 2f ) : 1f;
		// Changing capacity never manufactures ammunition. A smaller magazine discards excess rounds.
		if ( oldCapacity != AttachmentMagazineCapacity )
		{
			var ammo = GetComponentInChildren<WeaponAmmo>( true );
			if ( ammo.IsValid() ) ammo.Ammo = Math.Min( ammo.Ammo, ammo.GetMaxAmmoWithChamber() );
		}
	}
}
