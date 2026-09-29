using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A window pane that breaks when a bullet goes through it, a blast reaches it or something thrown hits it, like the
/// Town House's on Ridgeback (Tools/ridgeback_buildings.py). Breaking leaves one of <see cref="BrokenModels"/> (the
/// jagged edge left in the sash), turns the collider off, plays <see cref="BreakSound"/> and throws the pane's shards
/// (<see cref="ShardEffect"/>), mostly falling where it stood and some flung on the way the break came.
/// </summary>
/// <remarks>
/// Glass is see-through: sight checks, blasts and the bots' shots leave anything tagged <see cref="Tag"/> out, and a
/// round through a pane isn't a wallbang. Map objects aren't network objects (NetworkMode.Snapshot), so as for the
/// doors (<see cref="TerrorTown.MapMover"/>) a break goes out through a static RPC keyed by the GameObject's id. Whoever
/// breaks it sends it (the shooter, the host for bots and blasts, a grenade's owner), so a pane breaks when the shot
/// lands rather than a round trip later, and every machine shatters it once. The host tells a player who joins later
/// which panes are broken, and the between-round cleanup puts them back.
/// </remarks>
public sealed class BreakableGlass : Component, Component.IDamageable, Component.INetworkListener,
	IGameEventHandler<BetweenRoundCleanupEvent>
{
	public const string Tag = "glass";

	/// <summary> Slower than this (units a second, ~3 m/s), something thrown bounces off the glass. </summary>
	public const float BreakSpeed = 120f;

	[Property] public SoundEvent BreakSound { get; set; }

	/// <summary> A ParticleEffect prefab with no emitter: the shards are emitted over the pane by hand. </summary>
	[Property] public GameObject ShardEffect { get; set; }

	/// <summary>
	/// The whole pane. Given here rather than read off the renderer at the start, since a player who joins after it
	/// broke gets the renderer's broken model in the scene snapshot.
	/// </summary>
	[Property] public Model IntactModel { get; set; }

	/// <summary> What's left in the sash, picked by the pane's id so every machine shows the same one. </summary>
	[Property] public List<Model> BrokenModels { get; set; }

	/// <summary> The glass's width and height, along the pane's own Y and Z. </summary>
	[Property] public Vector2 PaneSize { get; set; } = new( 16f, 16f );

	/// <summary> Shards thrown per square foot of glass. </summary>
	[Property] public float ShardDensity { get; set; } = 22f;

	public bool IsBroken { get; private set; }

	bool _shattered;

	/// <summary> Break it here and on every machine, the shards flying on away from <paramref name="from"/>. </summary>
	public void Break( Vector3 from )
	{
		if ( IsBroken ) return;

		SetBroken( true );
		BroadcastBreak( GameObject.Id, from );
	}

	[Rpc.Broadcast]
	static void BroadcastBreak( Guid objectId, Vector3 from )
	{
		var glass = Find( objectId );
		if ( !glass.IsValid() || glass._shattered ) return;

		glass._shattered = true;
		glass.SetBroken( true );
		glass.Shatter( from );
	}

	/// <summary> A pane that was broken before this machine joined: no sound or shards. </summary>
	[Rpc.Broadcast( NetFlags.HostOnly )]
	static void BroadcastBroken( Guid objectId )
	{
		var glass = Find( objectId );
		if ( !glass.IsValid() || glass._shattered ) return;

		glass._shattered = true;
		glass.SetBroken( true );
	}

	static BreakableGlass Find( Guid objectId ) =>
		Game.ActiveScene?.Directory.FindByGuid( objectId )?.GetComponent<BreakableGlass>();

	void SetBroken( bool broken )
	{
		IsBroken = broken;

		var renderer = GetComponent<ModelRenderer>( true );
		if ( renderer.IsValid() )
		{
			var model = broken ? BrokenModel() : IntactModel;
			if ( model is not null ) renderer.Model = model;
			renderer.Enabled = model is not null;
		}

		foreach ( var collider in GetComponents<Collider>( true ) )
			collider.Enabled = !broken;
	}

	Model BrokenModel()
	{
		if ( BrokenModels is not { Count: > 0 } ) return null;
		return BrokenModels[(int)((uint)GameObject.Id.GetHashCode() % (uint)BrokenModels.Count)];
	}

	void Shatter( Vector3 from )
	{
		if ( BreakSound is not null )
			Sound.Play( BreakSound, WorldPosition );

		if ( Application.IsDedicatedServer || !ShardEffect.IsValid() )
			return;

		var effect = ShardEffect.Clone( new Transform( WorldPosition, WorldRotation ) );
		var particles = effect.GetComponentInChildren<ParticleEffect>();
		if ( !particles.IsValid() ) return;

		// On the far side from the break: a shot's way through, away from a blast.
		var normal = WorldRotation.Forward;
		var away = Vector3.Dot( WorldPosition - from, normal ) >= 0f ? normal : -normal;
		var area = PaneSize.x * PaneSize.y / 144f;
		var count = Math.Clamp( (int)MathF.Ceiling( area * ShardDensity ), 4, particles.MaxParticles );
		for ( var i = 0; i < count; i++ )
		{
			var local = new Vector3( 0f, Game.Random.Float( -0.5f, 0.5f ) * PaneSize.x, Game.Random.Float( -0.5f, 0.5f ) * PaneSize.y );
			var particle = particles.Emit( WorldTransform.PointToWorld( local ), i / (float)count );

			// Most of a pane drops out of the sash; the pieces round the break are flung.
			var speed = Game.Random.Float() < 0.3f ? Game.Random.Float( 90f, 260f ) : Game.Random.Float( 4f, 45f );
			particle.Velocity = away * speed + Vector3.Random * 18f;
		}
	}

	public void OnDamage( in Sandbox.DamageInfo info )
	{
		if ( IsBroken || !Networking.IsHost ) return;

		var from = info.Attacker.IsValid() ? info.Attacker.WorldPosition + Vector3.Up * 64f : info.Position - WorldRotation.Forward;
		Break( from );
	}

	void Component.INetworkListener.OnActive( Connection channel )
	{
		if ( !IsBroken || !Networking.IsHost ) return;

		using ( Rpc.FilterInclude( channel ) )
			BroadcastBroken( GameObject.Id );
	}

	void IGameEventHandler<BetweenRoundCleanupEvent>.OnGameEvent( BetweenRoundCleanupEvent eventArgs ) => Restore();

	void Restore()
	{
		_shattered = false;
		SetBroken( false );
	}

	/// <summary>
	/// Break every pane on a shot's line from <paramref name="start"/> to where it stopped, for shots that leave glass
	/// out of their trace (the bots').
	/// </summary>
	public static void BreakAlong( Scene scene, Vector3 start, Vector3 end )
	{
		foreach ( var hit in scene.Trace.Ray( start, end ).WithTag( Tag ).RunAll() )
		{
			if ( hit.GameObject?.GetComponent<BreakableGlass>() is { IsBroken: false } glass )
				glass.Break( start );
		}
	}

	/// <summary>
	/// Break the panes among a blast's <paramref name="objects"/> that it reaches: those with no wall between them and
	/// <paramref name="point"/>. <paramref name="trace"/> is the blast's own, which leaves glass out. Host only.
	/// </summary>
	public static void BreakInBlast( IEnumerable<GameObject> objects, Vector3 point, SceneTrace trace )
	{
		foreach ( var obj in objects )
		{
			if ( !obj.IsValid() || obj.GetComponent<BreakableGlass>() is not { IsBroken: false } glass )
				continue;

			if ( trace.Ray( point, glass.WorldPosition ).Run().Hit )
				continue;

			glass.Break( point );
		}
	}

	/// <summary>
	/// Break the pane something thrown is about to hit, so it goes on through: if the first thing on its way over the
	/// next few steps is glass and it's going fast enough. Called by whoever simulates it. Thrown things pass the
	/// window's player clip (the collision rules' grenade/playerclip pair), so the trace does too.
	/// </summary>
	public static void BreakAhead( GameObject thrown, Vector3 position, Vector3 velocity, float radius = 2f )
	{
		if ( velocity.Length < BreakSpeed ) return;

		var tr = thrown.Scene.Trace.Sphere( radius, position, position + velocity * Time.Delta * 3f )
			.IgnoreGameObjectHierarchy( thrown )
			.WithoutTags( "trigger", "player", "ragdoll", "movement", "playerclip" )
			.Run();

		if ( tr.Hit && tr.GameObject?.GetComponent<BreakableGlass>() is { IsBroken: false } glass )
			glass.Break( position );
	}
}
