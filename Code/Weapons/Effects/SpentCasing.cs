namespace Facepunch;

/// <summary>Local cosmetic brass: one case per shot, with no gameplay collision or network objects.</summary>
public sealed class SpentCasing : Component
{
	public const int MaxActiveCasings = 96;

	/// <summary>
	/// Past this far from the camera (units), and out of its view, a case isn't flown: it's put straight down on the floor
	/// under it. Its tink is silent past 700 (its events' reach), and from that far it's a pixel or two.
	/// </summary>
	private const float FlightReach = 1000f;

	[Property] public float Lifetime { get; set; } = 8f;
	/// <summary> Played where there's no case sound of our own for the floor (<see cref="WorldSounds.CasingBounce"/>). </summary>
	[Property] public SoundEvent BounceSound { get; set; }
	/// <summary> A rifle's case or a pistol's, for its tink as it lands. </summary>
	[Property] public WorldSounds.Brass Brass { get; set; } = WorldSounds.Brass.Rifle;
	public Vector3 Velocity { get; private set; }
	public bool HasSettled { get; private set; }

	/// <summary> Every case launched and not yet retired, oldest first. </summary>
	private static readonly List<SpentCasing> Cases = new();

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

		// Bound the cost even with several automatic weapons firing together: the oldest in this scene go first.
		Cases.Remove( this );
		var inScene = 0;
		for ( var i = Cases.Count - 1; i >= 0; i-- )
		{
			if ( !Cases[i].IsValid() || !Cases[i]._launched ) Cases.RemoveAt( i );
			else if ( Cases[i].Scene == Scene ) inScene++;
		}

		// The incoming prefab is still disabled, so reserve its place explicitly.
		var excess = inScene + 1 - MaxActiveCasings;
		for ( var i = 0; i < Cases.Count && excess > 0; )
		{
			if ( Cases[i].Scene != Scene )
			{
				i++;
				continue;
			}

			// Retiring takes it off the list.
			Cases[i].Retire();
			excess--;
		}

		Cases.Add( this );
	}

	protected override void OnUpdate()
	{
		if ( !_launched ) return;
		Advance( Time.Delta );
	}

	protected override void OnDestroy()
	{
		Cases.Remove( this );
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
		if ( IsOutOfSight() )
		{
			Drop();
			return;
		}

		// Short swept steps keep fast-moving cases from tunnelling through nearby walls.
		for ( var remaining = Math.Min( delta, 0.1f ); remaining > 0f; )
		{
			var step = Math.Min( remaining, 1f / 60f );
			remaining -= step;
			Velocity += Scene.PhysicsWorld.Gravity * step;
			var end = WorldPosition + Velocity * step;
			var hit = Trace( WorldPosition, end ).Run();
			WorldPosition = hit.Hit ? hit.EndPosition + hit.Normal * 0.05f : end;
			WorldRotation *= Rotation.From( _spin.x * step, _spin.y * step, _spin.z * step );
			if ( !hit.Hit ) continue;

			PlayBounce( hit );
			Velocity = Vector3.Reflect( Velocity, hit.Normal ) * 0.32f;
			_spin *= 0.45f;
			if ( hit.Normal.z > 0.6f && Velocity.Length < 18f )
			{
				Settle( hit );
				break;
			}
		}
	}

	private SceneTrace Trace( Vector3 from, Vector3 to )
	{
		var trace = Scene.Trace.Sphere( 0.18f, from, to )
			.WithoutTags( "player", "weapon", "particles", "trigger", "playerclip", "movement" );
		if ( _ignore.IsValid() ) trace = trace.IgnoreGameObjectHierarchy( _ignore );
		return trace;
	}

	/// <summary>
	/// Too far from the camera to hear (<see cref="FlightReach"/>) and outside its view, with a margin for the corners of
	/// the picture and the view turning. Only the main camera counts.
	/// </summary>
	private bool IsOutOfSight()
	{
		var camera = Scene.Camera;
		if ( !camera.IsValid() ) return false;

		var toCase = WorldPosition - camera.WorldPosition;
		var distance = toCase.Length;
		if ( distance < FlightReach ) return false;

		var halfAngle = MathF.Min( camera.FieldOfView * 0.75f + 10f, 89f ).DegreeToRadian();
		return Vector3.Dot( camera.WorldRotation.Forward, toCase ) < distance * MathF.Cos( halfAngle );
	}

	/// <summary> Puts the case down on the floor under it, done flying, with no tink: nobody's near enough to hear it. </summary>
	private void Drop()
	{
		var hit = Trace( WorldPosition, WorldPosition + Vector3.Down * 512f ).Run();
		if ( !hit.Hit || hit.StartedSolid )
		{
			Retire();
			return;
		}

		WorldPosition = hit.EndPosition + hit.Normal * 0.05f;
		Settle( hit );
	}

	/// <summary> Lays the case on the surface it came to rest on. </summary>
	private void Settle( in SceneTraceResult hit )
	{
		HasSettled = true;
		Velocity = 0;
		var alongSurface = WorldRotation.Forward - hit.Normal * WorldRotation.Forward.Dot( hit.Normal );
		if ( alongSurface.Length > 0.001f ) WorldRotation = Rotation.LookAt( alongSurface.Normal, hit.Normal );
	}

	/// <summary>
	/// A case landing: our own tink for the floor, as loud as the speed into it gives, while it's still hard enough to
	/// hear. A case chatters on as it slows, so every bounce plays, not only the first.
	/// </summary>
	private void PlayBounce( in SceneTraceResult hit )
	{
		var speed = -Velocity.Dot( hit.Normal );
		var ours = WorldSounds.CasingBounce( WorldSounds.SurfaceAt( hit ), Brass );
		if ( ours is not null )
		{
			var volume = WorldSounds.CasingVolume( speed );
			if ( volume <= 0f ) return;

			var sound = Sound.Play( ours, WorldPosition );
			if ( sound.IsValid() ) sound.Volume *= volume;
			return;
		}

		if ( _bounces++ < 2 && Velocity.Length > 35f && BounceSound is not null )
		{
			var sound = Sound.Play( BounceSound, WorldPosition );
			if ( sound.IsValid() ) sound.Volume = 0.18f;
		}
	}

	private void Retire()
	{
		_launched = false;
		Cases.Remove( this );
		Enabled = false;
		GameObject.Destroy();
	}
}
