namespace Facepunch;

/// <summary>Local cosmetic brass: one case per shot, with no gameplay collision or network objects.</summary>
public sealed class SpentCasing : Component
{
	public const int MaxActiveCasings = 96;
	[Property] public float Lifetime { get; set; } = 8f;
	[Property] public SoundEvent BounceSound { get; set; }
	public Vector3 Velocity { get; private set; }
	public bool HasSettled { get; private set; }

	private GameObject _ignore;
	private Vector3 _spin;
	private float _age;
	private int _bounces;
	private bool _launched;

	public void Launch( Rotation weaponRotation, Vector3 inheritedVelocity, GameObject ignore )
	{
		_ignore = ignore;
		_age = 0f;
		_launched = true;
		GameObject.NetworkMode = NetworkMode.Never;
		GameObject.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		GameObject.Tags.Add( "particles" );
		Velocity = inheritedVelocity + weaponRotation.Right * Game.Random.Float( 85f, 115f )
			+ weaponRotation.Up * Game.Random.Float( 55f, 80f )
			- weaponRotation.Forward * Game.Random.Float( 12f, 30f );
		_spin = new Vector3( Game.Random.Float( 480f, 850f ), Game.Random.Float( -600f, 600f ), Game.Random.Float( 600f, 1100f ) );

		// Bound the cost even with several automatic weapons firing together.
		var active = Scene.GetAllComponents<SpentCasing>().Where( c => c != this && c.IsValid() && c._launched ).OrderByDescending( c => c._age ).ToList();
		// The incoming prefab is still disabled, so reserve its place explicitly.
		foreach ( var old in active.Take( Math.Max( 0, active.Count + 1 - MaxActiveCasings ) ) ) old.Retire();
	}

	protected override void OnUpdate()
	{
		if ( !_launched ) return;
		Advance( Time.Delta );
	}

	private void Advance( float delta )
	{
		_age += delta;
		if ( _age >= Lifetime )
		{
			Retire();
			return;
		}

		if ( HasSettled ) return;
		// Short swept steps keep fast-moving cases from tunnelling through nearby walls.
		for ( var remaining = Math.Min( delta, 0.1f ); remaining > 0f; )
		{
			var step = Math.Min( remaining, 1f / 60f );
			remaining -= step;
			Velocity += Scene.PhysicsWorld.Gravity * step;
			var end = WorldPosition + Velocity * step;
			var trace = Scene.Trace.Sphere( 0.18f, WorldPosition, end )
				.WithoutTags( "player", "weapon", "particles", "trigger", "playerclip", "movement" );
			if ( _ignore.IsValid() ) trace = trace.IgnoreGameObjectHierarchy( _ignore );
			var hit = trace.Run();
			WorldPosition = hit.Hit ? hit.EndPosition + hit.Normal * 0.05f : end;
			WorldRotation *= Rotation.From( _spin.x * step, _spin.y * step, _spin.z * step );
			if ( !hit.Hit ) continue;

			if ( _bounces++ < 2 && Velocity.Length > 35f && BounceSound is not null )
			{
				var sound = Sound.Play( BounceSound, WorldPosition );
				if ( sound is not null ) sound.Volume = 0.18f;
			}
			Velocity = Vector3.Reflect( Velocity, hit.Normal ) * 0.32f;
			_spin *= 0.45f;
			if ( hit.Normal.z > 0.6f && Velocity.Length < 18f )
			{
				HasSettled = true;
				Velocity = 0;
				var alongSurface = WorldRotation.Forward - hit.Normal * WorldRotation.Forward.Dot( hit.Normal );
				if ( alongSurface.Length > 0.001f ) WorldRotation = Rotation.LookAt( alongSurface.Normal, hit.Normal );
				break;
			}
		}
	}

	private void Retire()
	{
		_launched = false;
		Enabled = false;
		GameObject.Destroy();
	}
}
