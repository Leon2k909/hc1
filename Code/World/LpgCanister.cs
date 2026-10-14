using Sandbox.Events;

namespace Facepunch;

/// <summary>A strapped forklift LPG cylinder. The host simulates it; static scene ids identify its RPCs.</summary>
[Title( "LPG Canister" ), Category( "Environment" ), Icon( "propane_tank" )]
public sealed partial class LpgCanister : Component, Component.IDamageable, Component.INetworkListener,
	IGameEventHandler<BetweenRoundCleanupEvent>, IDescription
{
	[Property] public Model IntactModel { get; set; }
	[Property] public Model RupturedModel { get; set; }
	[Property] public SoundEvent LeakSound { get; set; }
	[Property] public SoundEvent FireSound { get; set; }
	[Property] public SoundEvent RuptureSound { get; set; }
	[Property] public float BlastRadius { get; set; } = 240f;
	[Property] public float BlastDamage { get; set; } = 120f;

	public LpgCanisterPhase Phase => _state.Phase;
	public float Fuel => _state.Fuel;
	public float Heat => _state.Heat;
	public int Holes => _state.Holes;
	public Vector3 LeakPosition => WorldTransform.PointToWorld( _localLeak );
	public Vector3 LeakDirection => WorldTransform.NormalToWorld( _localDirection ).Normal;
	string IDescription.DisplayName => "LPG cylinder";
	string IDescription.Icon => "ui/weapons/grenades/he_grenade_01.png";

	readonly LpgCanisterState _state = new();
	Vector3 _localLeak = new( 0f, 17.8f, 0f );
	Vector3 _localDirection = new( 0f, 1f, 0f );
	Component _attacker;
	TimeSince _sinceSimulation, _sinceSent;
	readonly List<SurfaceFire.FireTarget> _targets = new();

	protected override void OnStart()
	{
		ApplyModel();
		if ( !Networking.IsHost ) RequestState( GameObject.Id );
	}

	protected override void OnUpdate()
	{
		if ( Networking.IsHost && _state.HasFuel && _sinceSimulation >= 0.1f )
		{
			var dt = MathF.Min( _sinceSimulation, 0.5f );
			_sinceSimulation = 0;
			var before = Phase;
			var heat = ExternalHeat( out var ignition );
			_state.Step( dt, heat / 80f, ignition );
			if ( Phase == LpgCanisterPhase.Burning ) BurnNearby( dt );
			if ( Phase != before || (_state.IsReleasing && _sinceSent >= 0.5f) ) Publish( Phase != before );
			if ( Phase == LpgCanisterPhase.Ruptured && before != Phase ) Rupture();
		}
		if ( !Application.IsDedicatedServer ) UpdateVisuals( Time.Delta );
	}

	/// <summary>Keep the game's fire/explosion/melee flags, which the generic engine adapter does not carry.</summary>
	public void TakeDamage( DamageInfo info )
	{
		if ( !Networking.IsHost || !_state.HasFuel || info.Damage <= 0f ) return;
		if ( info.Flags.HasFlag( DamageFlags.Melee ) || info.Flags.HasFlag( DamageFlags.FallDamage ) ) return;
		if ( info.Flags.HasFlag( DamageFlags.Burn ) )
		{
			_attacker = info.Attacker.IsValid() ? info.Attacker : _attacker;
			_state.Ignite();
			Publish( true );
			return;
		}

		PunctureAt( info.Position, info.Force, info.Attacker, info.WasExplosion ? 2 : 1 );
		if ( info.WasExplosion ) { _state.Ignite(); Publish( true ); }
	}

	public void OnDamage( in Sandbox.DamageInfo info )
	{
		if ( !Networking.IsHost || info.Damage <= 0f || !_state.HasFuel ) return;
		if ( info.Tags.Has( "melee" ) ) return;
		var attacker = info.Attacker.IsValid() ? info.Attacker.GetComponent<Component>() : null;
		if ( info.Tags.Has( "burn" ) || info.Tags.Has( "fire" ) )
		{
			_attacker = attacker.IsValid() ? attacker : _attacker;
			_state.Ignite();
			Publish( true );
			return;
		}
		PunctureAt( info.Position, info.Position - info.Origin, attacker );
	}

	void PunctureAt( Vector3 position, Vector3 direction, Component attacker, int holes = 1 )
	{
		var first = !_state.IsReleasing;
		_state.Puncture( holes );
		if ( first )
		{
			// Clamp to the bottle: a blast reports its origin rather than a surface impact.
			var local = WorldTransform.PointToLocal( position );
			var radial = new Vector3( local.x, 0f, local.z );
			if ( local.y > 17f && radial.Length < 2f )
			{
				_localLeak = new Vector3( 0f, 18f, 0f );
				_localDirection = new Vector3( 0f, 1f, 0f );
			}
			else
			{
				local.y = Math.Clamp( local.y, -17f, 17f );
				var end = MathF.Abs( local.y );
				var radius = end <= 13.5f ? 6.3f : end <= 15.2f ? 6.3f - (end - 13.5f) * 0.4f / 1.7f
					: end <= 16.4f ? 5.9f - (end - 15.2f) : 4.7f - (end - 16.4f) * 4f;
				if ( radial.Length > radius ) { radial = radial.Normal * radius; local.x = radial.x; local.z = radial.z; }
				if ( radial.Length < 0.1f ) radial = WorldTransform.NormalToLocal( -direction ).WithY( 0f );
				if ( radial.Length < 0.1f ) radial = Vector3.Backward;
				var slope = end <= 13.5f ? 0f : end <= 15.2f ? 0.4f / 1.7f : end <= 16.4f ? 1f : 4f;
				_localDirection = end >= 16.99f ? new Vector3( 0f, MathF.Sign( local.y ), 0f )
					: (radial.Normal + new Vector3( 0f, MathF.Sign( local.y ) * slope, 0f )).Normal;
				_localLeak = local + _localDirection * 0.2f;
			}
		}
		_attacker = attacker.IsValid() ? attacker : _attacker;
		Publish( true );
	}

	float ExternalHeat( out bool ignition )
	{
		var flux = SurfaceFire.HeatAt( Scene, WorldPosition, out var from );
		if ( flux > 0f && !Visible( WorldPosition, from ) ) flux = 0f;
		ignition = false;
		foreach ( var node in MolotovFireNode.All )
		{
			if ( !node.IsValid() || node.Scene != Scene ) continue;
			var fire = node.WorldPosition + Vector3.Up * 16f;
			var distance = WorldPosition.Distance( fire );
			if ( distance > 180f || !Visible( WorldPosition, fire ) ) continue;
			flux += 60f / MathF.Max( 1f, distance * distance / 1600f );
			if ( LeakPosition.Distance( fire ) < 90f ) ignition = true;
		}
		foreach ( var grenade in Scene.GetAllComponents<ThermiteGrenade>() )
		{
			if ( !grenade.IsBurning || LeakPosition.Distance( grenade.WorldPosition ) > 64f ) continue;
			if ( !Visible( LeakPosition, grenade.WorldPosition ) ) continue;
			ignition = true;
			if ( grenade.Player.IsValid() ) _attacker = grenade.Player;
		}
		// An existing burning surface touching the jet also ignites the released gas.
		var jetHeat = SurfaceFire.HeatAt( Scene, LeakPosition + LeakDirection * 28f, out from );
		if ( jetHeat >= 20f && Visible( LeakPosition, from ) ) ignition = true;
		return flux;
	}

	bool Visible( Vector3 from, Vector3 to )
	{
		var tr = Scene.Trace.Ray( from, to ).IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "player", "enemy", "ragdoll", "playerclip", BreakableGlass.Tag ).Run();
		return !tr.Hit || tr.Distance >= from.Distance( to ) - 8f;
	}

	void BurnNearby( float dt )
	{
		var start = LeakPosition;
		var end = start + LeakDirection * (75f * _state.Pressure);
		SurfaceFire.FindBodies( Scene, new BBox( start - Vector3.One * 140f, start + Vector3.One * 140f ), _targets );
		foreach ( var target in _targets )
		{
			var body = target.Feet + Vector3.Up * target.Height * 0.55f;
			var jet = end - start;
			var closest = start + jet * Math.Clamp( Vector3.Dot( body - start, jet ) / MathF.Max( jet.LengthSquared, 1f ), 0f, 1f );
			var distance = body.Distance( closest );
			if ( distance > 100f || !Visible( closest, body ) ) continue;
			var flux = distance < 18f ? SurfaceFire.InFlameFlux : 24f / MathF.Max( 1f, distance * distance / 400f );
			if ( flux <= SurfaceFire.HarmlessFlux ) continue;
			var damage = MathF.Pow( flux, 4f / 3f ) * dt / SurfaceFire.LethalDose * 100f;
			var health = target.Body.GameObject.GetComponent<HealthComponent>();
			if ( health.IsValid() ) health.TakeDamage( new DamageInfo( _attacker, damage, this, closest, Flags: DamageFlags.Burn ) );
			else if ( target.Body is ZombieAI zombie ) zombie.OnDamage( new Sandbox.DamageInfo( damage, _attacker?.GameObject, GameObject )
				{ Position = body, Origin = closest, Tags = new TagSet( new[] { "burn" } ) } );
		}
	}

	void Rupture()
	{
		// The bottle's pressure failure, with distance falloff and solid cover, once on the host.
		Explosion.AtPoint( WorldPosition, BlastRadius, BlastDamage, _attacker, this,
			new Curve( new Curve.Frame( 0f, 1f ), new Curve.Frame( 1f, 0f ) ) );
	}

	void ApplyModel()
	{
		var renderer = GetComponent<ModelRenderer>();
		if ( renderer.IsValid() ) renderer.Model = Phase == LpgCanisterPhase.Ruptured ? RupturedModel : IntactModel;
		foreach ( var collider in GetComponents<Collider>( true ) ) collider.Enabled = Phase != LpgCanisterPhase.Ruptured;
	}

	void Publish( bool eventEffects = false )
	{
		_sinceSent = 0;
		ApplyModel();
		if ( eventEffects && _visualPhase != LpgCanisterPhase.Ruptured && Phase == LpgCanisterPhase.Ruptured ) PlayRupture();
		_visualPhase = Phase;
		ReceiveState( GameObject.Id, Phase, Fuel, Heat, Holes, _localLeak, _localDirection, eventEffects );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	static void ReceiveState( Guid id, LpgCanisterPhase phase, float fuel, float heat, int holes, Vector3 leak, Vector3 direction, bool eventEffects )
	{
		var canister = Find( id );
		if ( !canister.IsValid() ) return;
		var old = canister._visualPhase;
		canister._state.Restore( phase, fuel, heat, holes );
		canister._localLeak = leak;
		canister._localDirection = direction;
		canister.ApplyModel();
		if ( eventEffects && old != LpgCanisterPhase.Ruptured && phase == LpgCanisterPhase.Ruptured ) canister.PlayRupture();
		canister._visualPhase = phase;
	}

	static LpgCanister Find( Guid id ) => Game.ActiveScene?.Directory.FindByGuid( id )?.GetComponent<LpgCanister>();

	[Rpc.Host]
	static void RequestState( Guid id )
	{
		var canister = Find( id );
		if ( canister.IsValid() ) canister.Publish();
	}

	void Component.INetworkListener.OnActive( Connection connection )
	{
		if ( !Networking.IsHost ) return;
		using ( Rpc.FilterInclude( connection ) ) Publish();
	}

	void IGameEventHandler<BetweenRoundCleanupEvent>.OnGameEvent( BetweenRoundCleanupEvent ev )
	{
		_state.Reset();
		_attacker = null;
		_localLeak = new Vector3( 0f, 17.8f, 0f );
		_localDirection = new Vector3( 0f, 1f, 0f );
		DestroyVisuals();
		ApplyModel();
		if ( Networking.IsHost ) Publish();
	}

	protected override void OnDisabled() => DestroyVisuals();
	protected override void OnDestroy() => DestroyVisuals();
}
