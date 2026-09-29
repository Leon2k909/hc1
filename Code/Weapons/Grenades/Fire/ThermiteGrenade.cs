namespace Facepunch;

/// <summary>
/// The AN-M14 TH3 incendiary grenade, as FM 3-23.30 describes it. Its M201A1 fuze burns for 1.2 to 2 seconds, then 750 g
/// of thermate burns for 40 seconds at about 2,200 C wherever the grenade has come to rest. It's no explosive and
/// throws no flame. What burns is what it lies on and what its molten iron spatters onto within a metre or so, and a
/// grass fire that starts from them runs on by itself (<see cref="SurfaceFire"/>, which also works out the heat).
/// <para>
/// The thrower's machine runs the fuze and the canister's physics (<see cref="BaseGrenade"/>) and syncs when it lit. The
/// host lights the ground under it and spatters it about, and every machine draws the burn
/// (<see cref="ThermiteBurnEffect"/>).
/// </para>
/// </summary>
[Title( "Incendiary Grenade" ), Icon( "local_fire_department" )]
public sealed class ThermiteGrenade : BaseGrenade, IDescription
{
	/// <summary> The M201A1 fuze's delay, in seconds. </summary>
	public const float MinFuze = 1.2f;
	public const float MaxFuze = 2f;

	/// <summary> TH3 burns for 40 seconds. </summary>
	public const float BurnTime = 40f;

	/// <summary> Seconds for the first fire mix to light the whole charge. </summary>
	private const float Kindle = 0.8f;

	/// <summary> The last of the charge dies down over this many seconds. </summary>
	private const float Fade = 3f;

	/// <summary>
	/// kW radiated at full burn. 750 g of TH3 gives about 3 MJ over its 40 s (75 kW), and about a third of that leaves the
	/// white-hot burning point as radiant heat.
	/// </summary>
	public const float FullRadiantPower = 24f;

	/// <summary> kW from the pool of molten iron as the charge burns out, and how fast it cools (s). </summary>
	private const float SlagPower = 3f;
	private const float SlagCooling = 20f;

	/// <summary> The burning canister and the pool round it, in units: anything this close is touching 2,000 C. </summary>
	public const float ContactRadius = 16f;

	/// <summary> The flame's height at full burn, in units. </summary>
	private const float FullFlameHeight = 24f;

	/// <summary> Drops of molten iron a second at full burn, and how far they fly (m): most land close, none past 1.5 m. </summary>
	private const float SpatterRate = 10f;
	private const float SpatterMean = 0.35f;
	private const float SpatterMax = 1.5f;

	/// <summary> A drop landing on someone's feet: a small, deep burn. </summary>
	private const float SpatterDamage = 1.5f;

	/// <summary> How often the ground under it is kept burning. </summary>
	private const float GroundInterval = 0.5f;

	/// <summary> The burnt-out canister lies there this long after the burn, then goes. </summary>
	private const float Linger = 50f;

	/// <summary> Seconds into the burn before the ground under it is marked, by when it has stopped rolling. </summary>
	private const float ScorchAfter = 2f;
	private const int MaxScorches = 3;

	/// <summary> The canister's top, where the flame and sparks come out: 5.5 units up its axis from its base. </summary>
	public static readonly Vector3 LocalTop = new( 0f, 0f, 5.5f );

	[Sync] public bool Ignited { get; private set; }
	[Sync] public TimeSince SinceIgnited { get; private set; }

	string IDescription.DisplayName => "Incendiary Grenade";
	string IDescription.Icon => "ui/weapons/grenades/fire_grenade_01.png";

	/// <summary> Is the charge burning now? </summary>
	public bool IsBurning => Ignited && SinceIgnited < BurnTime;

	/// <summary> 0 to 1: how hard it burns now. </summary>
	public float CurrentIntensity => Ignited ? Intensity( SinceIgnited ) : 0f;

	/// <summary> kW of radiant heat now: the burning point, then the pool of slag as it cools. </summary>
	public float RadiantPower
	{
		get
		{
			if ( !Ignited ) return 0f;
			float t = SinceIgnited;
			var slag = SlagPower * Math.Clamp( t / BurnTime, 0f, 1f );
			if ( t > BurnTime ) slag *= MathF.Exp( -(t - BurnTime) / SlagCooling );
			if ( slag < 0.2f ) slag = 0f;
			return FullRadiantPower * Intensity( t ) + slag;
		}
	}

	/// <summary> The flame's height now, in units. </summary>
	public float FlameHeight => FullFlameHeight * CurrentIntensity;

	/// <summary> Who threw it: the fire and heat it makes are theirs. </summary>
	public FireSource Source
	{
		get
		{
			if ( _source is null || _source.Pawn != Player ) _source = FireSource.From( Player );
			return _source;
		}
	}

	private FireSource _source;
	private TimeSince _sinceGround;
	private Vector3? _scorchedAt;
	private int _scorches;
	private float _spatterDebt;
	private readonly List<SurfaceFire.FireTarget> _nearby = new();
	private ThermiteBurnEffect _effect;
	private bool _spent;

	/// <summary> 0 to 1: how hard the charge burns <paramref name="t"/> seconds after it lit. </summary>
	public static float Intensity( float t )
	{
		if ( t <= 0f || t >= BurnTime ) return 0f;
		var rise = Math.Clamp( t / Kindle, 0f, 1f );
		var fall = Math.Clamp( (BurnTime - t) / Fade, 0f, 1f );
		return rise * rise * (3f - 2f * rise) * fall;
	}

	protected override void OnStart()
	{
		base.OnStart();

		// The fuze started when the lever flew off, as it was thrown.
		if ( !IsProxy ) Lifetime = Game.Random.Float( MinFuze, MaxFuze );
	}

	protected override bool CanExplode() => !Ignited;

	/// <summary> The fuze has burnt down: the first fire mix lights the charge. The grenade stays where it is, burning. </summary>
	protected override void Explode()
	{
		if ( IsProxy || Ignited ) return;
		Ignited = true;
		SinceIgnited = 0;
	}

	protected override void OnUpdate()
	{
		base.OnUpdate();

		// Burning thermite anywhere stops an instant defuse (AllowInstantDefuse).
		CanDealDamage = !Ignited || SinceIgnited < BurnTime;

		if ( Networking.IsHost && IsBurning )
			BurnOnHost();

		if ( !Application.IsDedicatedServer )
			UpdateLook();

		if ( !IsProxy && Ignited && SinceIgnited > BurnTime + Linger )
			GameObject.Destroy();
	}

	private void BurnOnHost()
	{
		var fire = SurfaceFire.Ensure( Scene );
		if ( !fire.IsValid() ) return;

		// Whatever it lies on burns for as long as it does, and a few seconds more.
		if ( _sinceGround >= GroundInterval )
		{
			_sinceGround = 0;
			if ( TryGround( out var ground ) )
			{
				fire.Ignite( ground, Source, 1f, BurnTime - SinceIgnited + 5f );

				// Once it has settled, the slag and scorch it leaves: again if it rolls on somewhere else.
				var moved = _scorchedAt is not Vector3 last || last.Distance( ground ) > 20f;
				if ( SinceIgnited > ScorchAfter && moved && _scorches < MaxScorches )
				{
					_scorchedAt = ground;
					_scorches++;
					fire.MarkThermiteScorch( ground );
				}
			}
		}

		_spatterDebt += SpatterRate * CurrentIntensity * Time.Delta;
		if ( _spatterDebt < 1f ) return;

		var reach = (SpatterMax + 1f) * FireFuels.Metre;
		SurfaceFire.FindBodies( Scene, BBox.FromPositionAndSize( WorldPosition, new Vector3( reach * 2f, reach * 2f, 200f ) ), _nearby );

		while ( _spatterDebt >= 1f )
		{
			_spatterDebt -= 1f;
			Spatter( fire );
		}
	}

	/// <summary> The ground right under the canister, if it's lying on something. </summary>
	private bool TryGround( out Vector3 ground )
	{
		var tr = Trace( WorldPosition + Vector3.Up * 6f, WorldPosition + Vector3.Down * 12f );
		ground = tr.HitPosition;
		return tr.Hit && !tr.StartedSolid;
	}

	/// <summary>
	/// A drop of molten iron: it flies off at random, most of them a hand's breadth or two, lands, and lights what's there
	/// with that fuel's chance (<see cref="FireFuels.Behaviour.SpatterIgnition"/>). A wall in the way catches it.
	/// </summary>
	private void Spatter( SurfaceFire fire )
	{
		var random = Game.Random;
		var metres = MathF.Min( -SpatterMean * MathF.Log( 1f - random.Float( 0f, 0.9999f ) ), SpatterMax );
		var angle = random.Float( 0f, MathF.PI * 2f );
		var from = WorldPosition + Vector3.Up * 4f;
		var to = from + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * (metres * FireFuels.Metre);

		var flight = Trace( from, to );
		if ( flight.Hit ) to = flight.EndPosition - flight.Direction * 2f;

		var fall = Trace( to + Vector3.Up * 4f, to + Vector3.Down * 80f );
		if ( !fall.Hit || fall.StartedSolid ) return;

		fire.Spatter( fall.HitPosition, Source );

		foreach ( var target in _nearby )
		{
			if ( !target.Body.IsValid() ) continue;
			if ( (target.Feet - fall.HitPosition).WithZ( 0 ).Length > 16f ) continue;
			if ( MathF.Abs( target.Feet.z - fall.HitPosition.z ) > 24f ) continue;
			SurfaceFire.BurnBody( target, SpatterDamage, Source, this, WorldPosition );
		}
	}

	private SceneTraceResult Trace( Vector3 from, Vector3 to ) => Scene.Trace.Ray( from, to )
		.IgnoreGameObjectHierarchy( GameObject )
		.IgnoreDynamic()
		.WithoutTags( "player", "trigger", "playerclip", "ragdoll", "corpse", "grenade", "particles", "movement", "clutter" )
		.Run();

	/// <summary> Every machine: the burn's light, sparks, smoke and sound, and a burnt-out canister after. </summary>
	private void UpdateLook()
	{
		if ( Ignited && !_effect.IsValid() )
		{
			var go = new GameObject( GameObject, true, "Thermite Burn" );
			go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			go.NetworkMode = NetworkMode.Never;
			_effect = go.AddComponent<ThermiteBurnEffect>();
			_effect.Grenade = this;
		}

		if ( Ignited && !_spent && SinceIgnited > BurnTime )
		{
			// The canister's paint has burnt off and the steel under it has scaled black.
			_spent = true;
			foreach ( var model in Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				model.Tint = new Color( 0.22f, 0.2f, 0.19f );
		}
	}
}
