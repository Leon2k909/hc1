using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Equipment
{
	[Sync] public bool UsesTracerRounds { get; private set; }
	[Sync] public int AttachmentMagazineCapacity { get; private set; }
	[Sync] public float AttachmentReloadMultiplier { get; private set; } = 1f;

	/// <summary>
	/// The fitted magazine when it reloads with its own animations (<see cref="GunsmithPart.ReloadAnimation"/>), else
	/// null. Only the owner has it; the viewmodel and <see cref="Reloadable"/> are the owner's.
	/// </summary>
	public GunsmithPart ReloadMagazine { get; private set; }

	internal void RefreshAmmunitionLoadout()
	{
		// Cookies belong to this client. Never apply them to another player's weapon or a bot.
		if ( IsProxy || !Owner.IsValid() || !Owner.IsLocallyControlled ) return;
		UsesTracerRounds = ApplySavedAttachments && GunsmithLoadoutManager.UsesTracerRounds( Resource );
		var oldCapacity = AttachmentMagazineCapacity;
		GunsmithPart magazine = null;
		var hasMagazine = ApplySavedAttachments && GunsmithLoadoutManager.TryGetAttachment( Resource, GunsmithPartType.Magazine, out magazine ) && magazine.IsValid();
		AttachmentMagazineCapacity = hasMagazine ? Math.Max( 0, magazine.MagazineCapacity ) : 0;
		AttachmentReloadMultiplier = hasMagazine ? magazine.ReloadTimeMultiplier.Clamp( 0.5f, 2f ) : 1f;
		ReloadMagazine = hasMagazine && magazine.ReloadAnimation > 0 ? magazine : null;
		// Changing capacity never manufactures ammunition. A smaller magazine discards excess rounds.
		if ( oldCapacity != AttachmentMagazineCapacity )
		{
			var ammo = GetComponentInChildren<WeaponAmmo>( true );
			if ( ammo.IsValid() ) ammo.Ammo = Math.Min( ammo.Ammo, ammo.GetMaxAmmoWithChamber() );
		}
	}
}
