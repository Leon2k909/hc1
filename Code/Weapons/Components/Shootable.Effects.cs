using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Shootable
{
	/// <summary>Chance of a visible flash, tuned per weapon rather than on every shot.</summary>
	[Property, Group( "Effects" ), Range( 0f, 1f )] public float MuzzleFlashChance { get; set; } = 0.25f;
	[Property, Group( "Effects" )] public float MuzzleFlashScale { get; set; } = 0.65f;
	[Property, Group( "Effects" )] public GameObject MuzzleSmokePrefab { get; set; }
	[Property, Group( "Effects" )] public float MuzzleSmokeScale { get; set; } = 1f;
	[Property, Group( "Suppressed Effects" )] public bool HasBuiltInSuppressor { get; set; }
	[Property, Group( "Suppressed Effects" ), Range( 0f, 1f )] public float SuppressedMuzzleFlashChance { get; set; } = 0.02f;
	[Property, Group( "Suppressed Effects" )] public float SuppressedMuzzleFlashScale { get; set; } = 0.5f;

	private readonly DischargeEffectState _dischargeEffects = new();

	private void PlayDischargeEffects( bool suppressed )
	{
		var attachments = GunsmithAttachmentEffects.For( Equipment );
		var flashChance = suppressed ? SuppressedMuzzleFlashChance
			: (MuzzleFlashChance * attachments.FlashChance).Clamp( 0f, 1f );
		var flashScale = suppressed ? SuppressedMuzzleFlashScale : MuzzleFlashScale;
		var effects = _dischargeEffects.Shoot( flashChance, flashScale,
			MuzzleSmokePrefab.IsValid() ? MuzzleSmokeScale : 0f, suppressed );

		// Roll once on the firing owner and broadcast the result to every viewer.
		DoShootEffects( suppressed, effects.Flash, effects.FlashScale, effects.SmokeScale, attachments.SoundVolume );
	}

	/// <summary>Residual smoke on a fresh reload, only after recent live firing.</summary>
	public void PlayReloadSmoke()
	{
		if ( IsProxy || !MuzzleSmokePrefab.IsValid() )
			return;

		var scale = _dischargeEffects.ReloadSmoke( MuzzleSmokeScale );
		if ( scale <= 0f )
			return;

		DoReloadSmoke( scale, AmmoComponent.IsValid() && !AmmoComponent.HasAmmo );
	}

	[Rpc.Broadcast]
	private void DoReloadSmoke( float scale, bool chamberOpen )
	{
		if ( Application.IsDedicatedServer || !Equipment.IsValid() || !Equipment.IsDeployed )
			return;

		var effector = Effector;
		if ( !effector.IsValid() || !effector.ModelRenderer.IsValid() )
			return;

		// A wisp at the barrel; a smaller puff at the open action when reloading empty.
		CreateDischargeParticle( MuzzleSmokePrefab, effector.DischargeMuzzle, scale, "Residual barrel smoke" );
		if ( chamberOpen )
			CreateDischargeParticle( MuzzleSmokePrefab, effector.EjectionPort, scale * 0.55f, "Chamber smoke" );
	}

	private void CreateDischargeParticle( GameObject prefab, GameObject attachment, float scale, string name )
	{
		if ( !prefab.IsValid() || !attachment.IsValid() || scale <= 0f )
			return;

		var particle = prefab.Clone( new CloneConfig
		{
			Parent = attachment,
			Transform = new Transform().WithScale( scale ),
			StartEnabled = true,
			Name = $"{name}: {Equipment.GameObject}"
		} );
		particle.NetworkMode = NetworkMode.Never;
	}
}
