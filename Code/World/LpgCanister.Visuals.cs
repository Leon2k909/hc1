namespace Facepunch;

public sealed partial class LpgCanister
{
	LpgCanisterPhase _visualPhase;
	ParticleEffect _vapour, _flame, _smoke, _fireball;
	PointLight _light;
	SoundHandle _loop;
	LpgCanisterPhase _soundPhase;
	float _emission;
	TimeSince _sinceBurst = 100f;
	TimeSince _sinceLastEmission;
	readonly List<GameObject> _fragments = new();

	void EnsureVisuals()
	{
		if ( _vapour.IsValid() ) return;
		_vapour = FireParticles.Create<LpgJetParticles>( GameObject, "LPG cold vapour", FireParticles.Smoke, 180, false, sorted: true, feather: 2f );
		_flame = FireParticles.Create<LpgJetParticles>( GameObject, "LPG jet fire", FireParticles.Flame, 180, true, feather: 2f );
		_smoke = FireParticles.Create<FireSmokeParticles>( GameObject, "LPG fire smoke", FireParticles.Smoke, 60, false, lit: true, sorted: true );
		_fireball = FireParticles.Create<FireballParticles>( GameObject, "LPG rupture", "textures/particles/flame/explosion/explosion_01.vtex", 24, false );
		var holder = new GameObject( GameObject, true, "LPG fire light" );
		holder.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		holder.NetworkMode = NetworkMode.Never;
		_light = holder.AddComponent<PointLight>();
		_light.Radius = 220f;
		_light.Shadows = true;
		_light.Enabled = false;
	}

	void UpdateVisuals( float delta )
	{
		if ( !_state.IsReleasing && !_vapour.IsValid() ) return;
		if ( !_state.IsReleasing && _sinceLastEmission > 12f && _sinceBurst > 12f ) { DestroyVisuals(); return; }
		EnsureVisuals();
		if ( _soundPhase != Phase )
		{
			_loop?.Stop( 0.15f );
			_loop = null;
			var sound = Phase == LpgCanisterPhase.Burning ? FireSound : Phase == LpgCanisterPhase.Leaking ? LeakSound : null;
			if ( sound is not null ) _loop = Sound.Play( sound, LeakPosition );
			_soundPhase = Phase;
		}
		if ( _loop is not null )
		{
			_loop.Position = LeakPosition;
			_loop.Volume = _state.Pressure * MathF.Min( 1.5f, 0.65f + Holes * 0.15f );
		}

		var burning = Phase == LpgCanisterPhase.Burning;
		_light.Enabled = burning || _sinceBurst < 0.6f;
		if ( _light.Enabled )
		{
			_light.WorldPosition = burning ? LeakPosition + LeakDirection * 24f : WorldPosition;
			var glow = burning ? _state.Pressure * (0.85f + MathF.Sin( Time.Now * 29f ) * 0.15f) : 5f * MathF.Exp( -_sinceBurst * 8f );
			_light.LightColor = new Color( 1f, 0.35f, 0.09f ) * glow;
		}
		if ( !_state.IsReleasing ) return;
		_sinceLastEmission = 0;

		_emission += delta * (burning ? 70f : 28f) * MathF.Min( Holes, 3 ) * _state.Pressure;
		var count = Math.Min( (int)_emission, 24 );
		_emission -= count;
		var effect = burning ? _flame : _vapour;
		for ( var i = 0; i < count && !effect.IsFull; i++ )
		{
			var p = effect.Emit( LeakPosition, Game.Random.Float() );
			p.StartScale = burning ? 0.6f : 1.5f;
			p.StartAngles = new Angles( burning ? 1f : 0f, Game.Random.Float( 0.8f, 1.2f ), 0f );
			p.Velocity = LeakDirection * (burning ? 130f : 65f) * _state.Pressure + Vector3.Random * 5f;
			p.Color = burning ? new Color( 0.5f, 0.65f, 1.8f ) : new Color( 0.8f, 0.85f, 0.9f );
			p.Size = burning ? 6f : 3f;
			p.Alpha = 0f;
			p.SequenceTime = new Vector3( 0f, 0f, Game.Random.Float() );
			p.Angles = new Angles( 0f, 0f, Game.Random.Float( 0f, 360f ) );
		}
		// A clean gas flame makes little soot; only a faint wisp rises off the hot fittings.
		if ( burning && Game.Random.Float() < delta * 5f )
			FireSmokeParticles.Emit( _smoke, LeakPosition + LeakDirection * 40f, 5f, 22f, 30f, 2f, new Color( 0.35f, 0.35f, 0.35f, 0.2f ) );
	}

	void PlayRupture()
	{
		if ( Application.IsDedicatedServer ) return;
		EnsureVisuals();
		_sinceBurst = 0;
		_loop?.Stop();
		_loop = null;
		if ( RuptureSound is not null ) Sound.Play( RuptureSound, WorldPosition );
		var scale = 0.6f + Fuel * 0.4f;
		for ( var i = 0; i < 12; i++ )
			FireballParticles.Emit( _fireball, WorldPosition + Vector3.Random * 18f, Game.Random.Float( 90f, 160f ) * scale,
				1.8f, i * 0.018f, 1.5f, 45f );
		for ( var i = 0; i < 15; i++ )
			FireSmokeParticles.Emit( _smoke, WorldPosition + Vector3.Random * 12f, 12f, 70f, 50f, 5f, new Color( 0.3f, 0.3f, 0.3f, 0.5f ) );
		var cap = Model.Load( "models/props/lowtide/lpg_canister_cap.vmdl" );
		if ( cap is not null && !cap.IsError )
		{
			foreach ( var sign in new[] { -1f, 1f } )
			{
				var fragment = new GameObject( GameObject, true, "LPG end cap" );
				fragment.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
				fragment.NetworkMode = NetworkMode.Never;
				fragment.Tags.Add( "particles" );
				var axis = WorldTransform.NormalToWorld( new Vector3( 0f, sign, 0f ) );
				fragment.WorldPosition = WorldPosition + axis * 17f;
				fragment.WorldRotation = WorldRotation;
				fragment.AddComponent<ModelRenderer>().Model = cap;
				fragment.AddComponent<LpgCanisterFragment>().Launch( axis * Game.Random.Float( 180f, 350f ) + Vector3.Up * 150f, GameObject );
				_fragments.Add( fragment );
			}
		}
	}

	void DestroyVisuals()
	{
		_loop?.Stop();
		_loop = null;
		foreach ( var effect in new[] { _vapour, _flame, _smoke, _fireball } ) if ( effect.IsValid() ) effect.GameObject.Destroy();
		if ( _light.IsValid() ) _light.GameObject.Destroy();
		foreach ( var fragment in _fragments )
		{
			if ( !fragment.IsValid() ) continue;
			fragment.Enabled = false;
			fragment.Destroy();
		}
		_fragments.Clear();
		_vapour = _flame = _smoke = _fireball = null;
		_light = null;
		_emission = 0f;
		_soundPhase = _visualPhase = LpgCanisterPhase.Intact;
		_sinceBurst = 100f;
	}
}

/// <summary>Local metal fragments sweep against solid scenery, bounce and settle; they do not add networked physics.</summary>
[Hide]
public sealed class LpgCanisterFragment : Component
{
	Vector3 _velocity, _spin;
	GameObject _ignore;
	float _age;
	bool _settled;

	public void Launch( Vector3 velocity, GameObject ignore )
	{
		_velocity = velocity;
		_ignore = ignore;
		_spin = Vector3.Random * 600f;
	}

	protected override void OnUpdate()
	{
		_age += Time.Delta;
		if ( _age > 12f ) { GameObject.Destroy(); return; }
		if ( _settled ) return;
		for ( var remaining = MathF.Min( Time.Delta, 0.1f ); remaining > 0f; )
		{
			var dt = MathF.Min( remaining, 1f / 120f );
			remaining -= dt;
			_velocity += Scene.PhysicsWorld.Gravity * dt;
			var end = WorldPosition + _velocity * dt;
			var hit = Scene.Trace.Sphere( 2f, WorldPosition, end ).IgnoreGameObjectHierarchy( _ignore )
				.WithoutTags( "player", "enemy", "weapon", "particles", "trigger", "playerclip" ).Run();
			WorldPosition = hit.Hit ? hit.EndPosition + hit.Normal * 2f : end;
			WorldRotation *= Rotation.From( _spin.x * dt, _spin.y * dt, _spin.z * dt );
			if ( !hit.Hit ) continue;
			_velocity = Vector3.Reflect( _velocity, hit.Normal ) * 0.3f;
			_spin *= 0.4f;
			if ( hit.Normal.z > 0.6f && _velocity.Length < 25f ) _settled = true;
		}
	}
}

/// <summary>Short pressure jets; cold condensation drops and thins, hot gas lifts and turns orange.</summary>
[Hide]
public sealed class LpgJetParticles : ParticleController
{
	float _dt;
	protected override void OnBeforeStep( float delta ) => _dt = delta;
	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var t = p.Age / MathF.Max( p.StartScale, 0.05f );
		if ( t >= 1f ) { p.Alpha = 0f; p.Age = 1e6f; return; }
		var burning = p.StartAngles.pitch > 0f;
		p.Size = (burning ? 6f + 23f * t : 3f + 18f * t) * p.StartAngles.yaw;
		p.Alpha = MathF.Min( t * 8f, 1f ) * (1f - t) * (burning ? 0.85f : 0.22f);
		p.SequenceTime.y = p.Age * (burning ? 30f : 8f) / 64f;
		if ( burning ) p.Color = Color.Lerp( new Color( 0.35f, 0.6f, 2f ), new Color( 1.6f, 0.5f, 0.08f ), MathF.Min( t * 2.5f, 1f ) );
		p.Velocity += (Vector3.Up * (burning ? 65f : -18f) - p.Velocity * (burning ? 0.4f : 1.5f)) * _dt;
	}
}
