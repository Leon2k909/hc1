namespace Facepunch;

/// <summary>
/// Continuous flames attached to the charred fuel, rather than short-lived cards which rise away from it.
/// Only the photographed flame and a small, smooth change in its height animate; its foot never moves.
/// </summary>
[Hide]
public sealed class BarrelFlameParticles : ParticleController
{
	// Points on the four logs in burn-drum-v2/drum.py, in the drum model's local coordinates.
	private static readonly Vector3[] FuelPoints =
	[
		new( -4.2f, -3.4f, 28.7f ), new( -0.9f, -0.2f, 30.7f ), new( 1.8f, 2.6f, 33.1f ),
		new( 4.4f, -2.0f, 28.0f ), new( -2.0f, 1.5f, 31.3f ),
		new( -0.6f, 2.4f, 28.5f ), new( 5.2f, 4.1f, 27.7f )
	];

	public Vector3 OpeningOrigin { get; private set; }
	public float OpeningRadius { get; private set; }
	public float OpeningHeight { get; private set; }
	public bool AttachedToFuel { get; private set; }
	private ModelRenderer _fuel;
	private bool _searchedFuel;
	private float _time;
	private float _height;
	private float _burn;

	public void UpdateFuel( Vector3 origin, float radius, float rimHeight, float height, float burn )
	{
		OpeningOrigin = origin;
		OpeningRadius = radius;
		OpeningHeight = rimHeight;
		_height = height;
		_burn = burn;
		if ( !_searchedFuel )
		{
			_searchedFuel = true;
			_fuel = Scene.GetAllComponents<ModelRenderer>()
				.Where( m => m.Model?.ResourcePath?.Contains( "burn_drum_v2/", StringComparison.OrdinalIgnoreCase ) == true
					&& (m.WorldPosition - origin).WithZ( 0f ).Length < 4f && MathF.Abs( origin.z - m.WorldPosition.z - 26.91f ) < 4f )
				.FirstOrDefault();
		}
		AttachedToFuel = _fuel.IsValid();

		// One persistent tongue per fuel site. No random births, relocation, roll, wind drift or detached cards.
		if ( ParticleEffect.ParticleCount != 0 ) return;
		for ( var i = 0; i < FuelPoints.Length; i++ )
		{
			var p = ParticleEffect.Emit( origin, i * 0.137f );
			p.StartScale = i;
			p.StartAngles = new Angles( 0f, i * 0.897f + Random.Shared.Float( 0f, 6f ), 0f );
			p.Alpha = 0f;
		}
	}

	protected override void OnBeforeStep( float delta ) => _time += delta;

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var index = Math.Clamp( (int)p.StartScale, 0, FuelPoints.Length - 1 );
		var local = FuelPoints[index];
		var root = _fuel.IsValid() ? _fuel.WorldTransform.PointToWorld( local )
			: OpeningOrigin + (local - Vector3.Up * 26.91f) * (OpeningRadius / 9.5f);
		var phase = p.StartAngles.yaw;
		// Slow changes in fuel output; the flipbook supplies the fast, upward-moving detail.
		var envelope = 0.89f + 0.08f * MathF.Sin( _time * 1.3f + phase )
			+ 0.03f * MathF.Sin( _time * 2.7f + phase * 1.7f );
		var height = _height * (index == 1 ? 0.88f : index == 2 ? 0.7f : 0.57f) * envelope * (0.92f + 0.08f * _burn);
		var availableWidth = MathF.Max( 1f, (OpeningRadius - (root - OpeningOrigin).WithZ( 0f ).Length - 0.5f) * 2f );
		// Keep the photographed flame's proportions. Edge sites make smaller flames instead of stretched threads.
		height = MathF.Min( height, availableWidth * FireParticles.FlameAspect );
		var width = height / FireParticles.FlameAspect;
		p.StartPosition = root;
		p.Size = new Vector3( width, height, 1f );
		p.Position = root + Vector3.Up * height * 0.5f;
		p.Velocity = Vector3.Zero;
		p.Angles = Angles.Zero;
		p.Color = new Color( 0.68f, 0.55f, 0.36f, 1f );
		p.Alpha = Math.Clamp( _time * 2f, 0f, 1f ) * (0.74f + 0.08f * envelope);
		// The sprite renderer takes a normalized cycle. The 64-frame sheet plays at 20 frames/s,
		// so one full flame cycle lasts 3.2 seconds. Keep the phase normalized for long editor sessions.
		p.SequenceTime = new Vector3( 0f, (_time * (20f / 64f) + phase / MathF.Tau) % 1f, 0f );
		// The renderer's 600-second lifetime is a safety limit for transient fire particles. These are fuel sites.
		p.Age = 0f;
	}
}

