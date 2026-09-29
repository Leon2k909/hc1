namespace Facepunch;

/// <summary>
/// The barrel's temperature from firing, from the real gun's numbers. Each shot heats the barrel by
/// <see cref="HeatPerShot"/>, and it cools toward the air (Newton's law of cooling, <see cref="CoolingTime"/>).
/// Only a hot barrel matters: past <see cref="DispersionStart"/> the heat opens the gun's groups, growing to
/// <see cref="HotDispersion"/> at <see cref="HotTemperature"/>. A cold or warm barrel shoots exactly where it's aimed.
/// A closed-bolt gun left with a round chambered in a barrel past <see cref="CookOffTemperature"/> fires it by itself.
/// </summary>
[Title( "Barrel Heat" ), Group( "Weapon Components" )]
public sealed class BarrelHeat : EquipmentComponent
{
	/// <summary>
	/// Barrel temperature rise per shot, in °C: the heat one round leaves in the barrel over the barrel's heat capacity
	/// (its mass times steel's specific heat).
	/// </summary>
	[Property] public float HeatPerShot { get; set; }

	/// <summary>Seconds for the barrel's temperature above the air to fall by a factor of e.</summary>
	[Property] public float CoolingTime { get; set; } = 600f;

	/// <summary>Barrel temperature above the air, °C, where its groups start to open.</summary>
	[Property] public float DispersionStart { get; set; }

	/// <summary>Barrel temperature above the air, °C, where the groups are <see cref="HotDispersion"/> wider.</summary>
	[Property] public float HotTemperature { get; set; }

	/// <summary>
	/// Extra dispersion at <see cref="HotTemperature"/>, in milliradians: the standard deviation of a shot's angle on
	/// each axis. It grows in a straight line from <see cref="DispersionStart"/> and stops growing past this.
	/// </summary>
	[Property] public float HotDispersion { get; set; }

	/// <summary>
	/// Barrel temperature above the air, °C, where a round sitting in the chamber cooks off: it fires within
	/// <see cref="CookOffTime"/> of the last shot. 0 for guns that fire from an open bolt, which keep the chamber empty.
	/// </summary>
	[Property] public float CookOffTemperature { get; set; }

	/// <summary>The longest a chambered round sits in a barrel that hot before it cooks off, in seconds.</summary>
	[Property] public float CookOffTime { get; set; } = 10f;

	/// <summary>The barrel's temperature above the air just after the last shot, and the time since.</summary>
	[Sync] public float ShotTemperature { get; set; }
	[Sync] public TimeSince TimeSinceShot { get; set; }

	/// <summary>The barrel's temperature above the air, °C.</summary>
	public float Temperature => CoolingTime > 0f ? ShotTemperature * MathF.Exp( -TimeSinceShot / CoolingTime ) : 0f;

	/// <summary>The extra dispersion at the barrel's temperature, in radians (standard deviation per axis).</summary>
	public float Dispersion
	{
		get
		{
			if ( HotTemperature <= DispersionStart ) return 0f;
			var hot = ((Temperature - DispersionStart) / (HotTemperature - DispersionStart)).Clamp( 0f, 1f );
			return hot * HotDispersion * 0.001f;
		}
	}

	/// <summary>When the round now in the chamber would cook off, in seconds after the last shot.</summary>
	private float _cookOffAfter;

	internal void Shoot()
	{
		ShotTemperature = Temperature + HeatPerShot;
		TimeSinceShot = 0;
		_cookOffAfter = Game.Random.Float( 1f, CookOffTime );
	}

	protected override void OnFixedUpdate()
	{
		if ( IsProxy || CookOffTemperature <= 0f || !Equipment.IsValid() || !Equipment.IsDeployed ) return;
		if ( TimeSinceShot < _cookOffAfter || Temperature < CookOffTemperature ) return;
		if ( Equipment.Tags.Has( "reloading" ) ) return;

		var shootable = Equipment.GetComponentInChildren<Shootable>();
		if ( !shootable.IsValid() || !shootable.AmmoComponent.IsValid() || !shootable.AmmoComponent.HasAmmo ) return;

		// The action cycles as usual and chambers the next round, which can cook off in turn.
		shootable.Shoot();
	}

	/// <summary>A random offset for a shot's direction from the barrel's heat: normally distributed on each axis.</summary>
	internal Vector3 Deviation( Rotation aim )
	{
		var sigma = Dispersion;
		if ( sigma <= 0f ) return Vector3.Zero;

		// Box-Muller: a normal deviate on each axis.
		var radius = MathF.Sqrt( -2f * MathF.Log( 1f - Game.Random.Float( 0f, 0.9999f ) ) ) * sigma;
		var angle = Game.Random.Float( 0f, MathF.PI * 2f );
		return aim.Right * (radius * MathF.Cos( angle )) + aim.Up * (radius * MathF.Sin( angle ));
	}
}
