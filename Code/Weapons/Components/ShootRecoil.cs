using Facepunch.Gunsmith;

namespace Facepunch;

[Title( "Recoil" ), Group( "Weapon Components" )]
public partial class ShootRecoil : EquipmentComponent
{
	[Property] public float ResetTime { get; set; } = 0.3f;

	// Recoil Patterns
	[Property, FeatureEnabled( "Recoil Pattern" )] public bool UseRecoilPattern { get; set; } = false;
	[Property, Category( "UseRecoilPattern" ), Feature( "Recoil Pattern" )] public Vector2 Scale { get; set; } = new Vector2( 2f, 5f );
	[Property, Category( "UseRecoilPattern" ), Feature( "Recoil Pattern" ) ] public RecoilPattern RecoilPattern { get; set; } = new();
	[Property, Group( "Standard Recoil" ), Feature( "Standard Recoil" )] public RangedFloat HorizontalSpread { get; set; } 
	[Property, Group( "Standard Recoil" ), Feature( "Standard Recoil" )] public RangedFloat VerticalSpread { get; set; }

	internal Angles Current { get; private set; }

	TimeSince TimeSinceLastShot;
	int currentFrame = 0;

	/// <summary>
	/// Recoil scale from tuning. +10 = -15% recoil, -10 = +15% recoil.
	/// </summary>
	private float GetRecoilScale()
	{
		var weaponId = Equipment?.Resource?.ResourceName ?? string.Empty;
		if ( string.IsNullOrEmpty( weaponId ) ) return 1f;
		var tune = WeaponTuningManager.GetTuning( weaponId );
		return 1f - tune.Recoil * 0.015f;
	}

	internal void Shoot()
	{
		if ( TimeSinceLastShot > ResetTime )
			currentFrame = 0;

		TimeSinceLastShot = 0;

		var timeDelta = Time.Delta;
		// Hardcore: a shot arm or hand can't hold the gun down as well.
		var recoilScale = GetRecoilScale() * (Player?.HealthComponent?.WoundRecoilScale ?? 1f);
		var attachments = GunsmithAttachmentEffects.For( Equipment );

		if ( UseRecoilPattern )
		{
			var point = RecoilPattern.GetPoint( ref currentFrame );

			var newAngles = new Angles( -point.y * Scale.y * recoilScale * attachments.VerticalRecoil,
				-point.x * Scale.x * recoilScale * attachments.HorizontalRecoil, 0 ) * timeDelta;
			Current = Current + newAngles;
			currentFrame++;
		}
		else
		{
			var newAngles = new Angles( -VerticalSpread.GetValue() * recoilScale * attachments.VerticalRecoil * timeDelta,
				HorizontalSpread.GetValue() * recoilScale * attachments.HorizontalRecoil * timeDelta, 0 );
			Current = Current + newAngles;
		}

	}

	internal void ClearRecoil()
	{
		Current = Angles.Zero;
		currentFrame = 0;
	}

	protected override void OnUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.IsLocallyControlled )
			return;

		Current = Current.LerpTo( Angles.Zero, Time.Delta * 10f );
	}
}
