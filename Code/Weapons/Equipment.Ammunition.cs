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

	/// <summary>
	/// The fitted fire control group's selector positions (<see cref="GunsmithPart.FireModes"/>), else null for the
	/// weapon's own. Only the owner has it: the owner switches fire modes and fires (<see cref="Shootable.FireModes"/>).
	/// </summary>
	public IReadOnlyList<FireMode> TriggerFireModes { get; private set; }

	/// <summary>
	/// The fitted parts' weight against the factory gun's: <see cref="ViewModel.AimTime"/>'s multiplier, and what it adds
	/// to <see cref="WeightSlowdown"/> (<see cref="GunsmithAttachmentEffects.ApplyMass"/>). Only the owner has them: the
	/// viewmodel and the movement are the owner's.
	/// </summary>
	public float AttachmentAimTimeScale { get; private set; } = 1f;
	public float AttachmentWeightSlowdown { get; private set; }

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
		var triggerModes = ApplySavedAttachments && GunsmithLoadoutManager.TryGetAttachment( Resource, GunsmithPartType.Trigger, out var trigger )
			&& trigger.IsValid() && trigger.FireModes is { Count: > 0 } ? trigger.FireModes : null;
		if ( !ReferenceEquals( triggerModes, TriggerFireModes ) )
		{
			TriggerFireModes = triggerModes;
			GetComponentInChildren<Shootable>( true )?.KeepFireModeFitted();
		}
		var effects = GunsmithAttachmentEffects.For( this );
		AttachmentAimTimeScale = effects.AimTime;
		AttachmentWeightSlowdown = effects.WeightSlowdown;
		// Changing capacity never manufactures ammunition. A smaller magazine discards excess rounds.
		if ( oldCapacity != AttachmentMagazineCapacity )
		{
			var ammo = GetComponentInChildren<WeaponAmmo>( true );
			if ( ammo.IsValid() ) ammo.Ammo = Math.Min( ammo.Ammo, ammo.GetMaxAmmoWithChamber() );
		}
	}
}
