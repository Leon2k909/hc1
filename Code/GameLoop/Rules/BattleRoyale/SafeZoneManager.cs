namespace Facepunch;

/// <summary>
/// The battle royale's safe zone, a circle that closes in phases like Warzone's: it holds, then shrinks onto the next
/// circle (picked at random inside it, on ground bots can walk to), and so on down to nothing. Outside it you lose health
/// steadily, more each phase, bots too. The next circle is known from the start of each hold, so the HUD can show it.
/// Idle until <see cref="SetFirstCircle"/> and <see cref="StartClosing"/> (see <see cref="BattleRoyaleMatch"/>).
/// </summary>
[Title( "Safe Zone" ), Icon( "radio_button_checked" )]
public sealed class SafeZoneManager : Component
{
	public static SafeZoneManager Current { get; private set; }

	/// <summary> One phase: hold for <see cref="Hold"/> seconds, then close to <see cref="Radius"/> (a share of the first circle) over <see cref="Shrink"/>. </summary>
	public readonly record struct Phase( float Hold, float Shrink, float Radius, float DamagePerSecond );

	public const int PhaseCount = 6;

	/// <summary>
	/// About nine and a half minutes in all. Damage is per second outside the zone: early on there's time to run for it,
	/// the last circles kill in seconds. The last one closes to nothing, so the match always ends.
	/// </summary>
	public static Phase GetPhase( int index ) => index switch
	{
		0 => new( 90f, 60f, 0.55f, 2f ),
		1 => new( 60f, 50f, 0.32f, 4f ),
		2 => new( 50f, 40f, 0.18f, 6f ),
		3 => new( 40f, 35f, 0.09f, 10f ),
		4 => new( 30f, 30f, 0.04f, 15f ),
		_ => new( 20f, 45f, 0f, 25f ),
	};

	/// <summary> Scales every hold and shrink, for quicker test matches. </summary>
	[Property] public float TimeScale { get; set; } = 1f;

	/// <summary> The circle the zone started this hold or shrink from. </summary>
	[Sync( SyncFlags.FromHost )] public Vector3 FromCenter { get; private set; }
	[Sync( SyncFlags.FromHost )] public float FromRadius { get; private set; }
	/// <summary> The circle it closes to next. </summary>
	[Sync( SyncFlags.FromHost )] public Vector3 NextCenter { get; private set; }
	[Sync( SyncFlags.FromHost )] public float NextRadius { get; private set; }
	/// <summary> The first circle's radius, which the phases' radii are shares of. </summary>
	[Sync( SyncFlags.FromHost )] public float FirstRadius { get; private set; }
	/// <summary> 1-based, 0 before the zone starts closing. </summary>
	[Sync( SyncFlags.FromHost )] public int PhaseNumber { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsShrinking { get; private set; }
	/// <summary> Time.Now when this hold or shrink started and ends. After the last shrink both stay put. </summary>
	[Sync( SyncFlags.FromHost )] public float StageStartedAt { get; private set; }
	[Sync( SyncFlags.FromHost )] public float StageEndsAt { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsRunning { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool HasCircle { get; private set; }
	[Sync( SyncFlags.FromHost )] public float DamagePerSecond { get; private set; }
	/// <summary> The last circle has closed: all that's left is the damage. </summary>
	[Sync( SyncFlags.FromHost )] public bool IsFinal { get; private set; }

	/// <summary> How far through the shrink under way, 0 while holding. </summary>
	public float ShrinkFraction => IsShrinking && StageEndsAt > StageStartedAt
		? ((Time.Now - StageStartedAt) / (StageEndsAt - StageStartedAt)).Clamp( 0f, 1f )
		: 0f;

	/// <summary> Where the zone is now. Every machine works it out from the synced circles, so it moves smoothly. </summary>
	public Vector3 ZoneCenter => Vector3.Lerp( FromCenter, NextCenter, ShrinkFraction );
	public float CurrentRadius => MathX.Lerp( FromRadius, NextRadius, ShrinkFraction );

	/// <summary> Seconds left in this hold or shrink. </summary>
	public float StageTimeLeft => MathF.Max( 0f, StageEndsAt - Time.Now );

	/// <summary> How far outside the zone <paramref name="position"/> is, or 0 inside it. The zone is a cylinder. </summary>
	public float DistanceOutside( Vector3 position ) =>
		HasCircle ? MathF.Max( 0f, position.WithZ( 0f ).Distance( ZoneCenter.WithZ( 0f ) ) - CurrentRadius ) : 0f;

	/// <summary> How far outside the next circle <paramref name="position"/> is, or 0 inside it. </summary>
	public float DistanceOutsideNext( Vector3 position ) =>
		HasCircle ? MathF.Max( 0f, position.WithZ( 0f ).Distance( NextCenter.WithZ( 0f ) ) - NextRadius ) : 0f;

	private int _phase;
	private TimeSince _timeSinceDamage;

	protected override void OnEnabled()
	{
		Current = this;
	}

	protected override void OnDisabled()
	{
		if ( Current == this )
			Current = null;
	}

	/// <summary> Host: the zone before it starts closing. Nothing is hurt yet. </summary>
	public void SetFirstCircle( Vector3 center, float radius )
	{
		FromCenter = NextCenter = center;
		FromRadius = NextRadius = FirstRadius = radius;
		PhaseNumber = 0;
		IsShrinking = false;
		IsRunning = false;
		IsFinal = false;
		HasCircle = true;
		StageStartedAt = StageEndsAt = Time.Now;
	}

	/// <summary> Host: start the first hold. </summary>
	public void StartClosing()
	{
		if ( !HasCircle )
			return;

		IsRunning = true;
		_timeSinceDamage = 0f;
		DamagePerSecond = GetPhase( 0 ).DamagePerSecond;
		BeginHold( 0 );
	}

	/// <summary> Host: the zone stops closing and stops hurting (the match is over). </summary>
	public void Stop()
	{
		if ( IsShrinking )
		{
			FromCenter = ZoneCenter;
			FromRadius = CurrentRadius;
			NextCenter = FromCenter;
			NextRadius = FromRadius;
			IsShrinking = false;
		}

		IsRunning = false;
	}

	/// <summary> Host: skip the rest of this hold or shrink (<c>dev_zone_next</c>). </summary>
	public void SkipStage()
	{
		if ( IsRunning )
			StageEndsAt = Time.Now;
	}

	private void BeginHold( int phase )
	{
		_phase = phase;
		var next = GetPhase( phase );
		PhaseNumber = phase + 1;
		NextRadius = FirstRadius * next.Radius;
		NextCenter = PickNextCenter( FromCenter, FromRadius, NextRadius );
		IsShrinking = false;
		StageStartedAt = Time.Now;
		StageEndsAt = Time.Now + next.Hold * TimeScale;
	}

	private void BeginShrink()
	{
		var phase = GetPhase( _phase );
		IsShrinking = true;
		DamagePerSecond = phase.DamagePerSecond;
		StageStartedAt = Time.Now;
		StageEndsAt = Time.Now + phase.Shrink * TimeScale;
	}

	private void EndShrink()
	{
		FromCenter = NextCenter;
		FromRadius = NextRadius;
		IsShrinking = false;

		if ( _phase + 1 < PhaseCount )
		{
			BeginHold( _phase + 1 );
			return;
		}

		IsFinal = true;
		StageStartedAt = StageEndsAt = Time.Now;
	}

	/// <summary>
	/// Somewhere for the next circle to sit wholly inside this one, on ground bots can walk to: not out past the map's
	/// edge or up on Flatgrass's roof.
	/// </summary>
	private Vector3 PickNextCenter( Vector3 center, float radius, float nextRadius )
	{
		var room = MathF.Max( 0f, radius - nextRadius );
		var bots = LightweightBotManager.Instance;
		for ( var i = 0; i < 16; i++ )
		{
			var angle = Game.Random.Float( 0f, MathF.PI * 2f );
			var distance = room * MathF.Sqrt( Game.Random.Float() );
			var point = center + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * distance;
			if ( Scene.NavMesh.GetClosestPoint( point, 1000f ) is not { } ground )
				continue;
			if ( ground.WithZ( 0f ).Distance( center.WithZ( 0f ) ) > room )
				continue;
			if ( bots.IsValid() && !bots.IsWalkable( ground ) )
				continue;

			return ground;
		}

		return center;
	}

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost || !IsRunning )
			return;

		if ( Time.Now >= StageEndsAt && !IsFinal )
		{
			if ( IsShrinking )
				EndShrink();
			else
				BeginShrink();
		}

		// Once a second, like Warzone's gas: each tick is a hit, so this keeps it to one flinch a second.
		if ( _timeSinceDamage >= 1f )
		{
			_timeSinceDamage = 0f;
			HurtEveryoneOutside();
		}
	}

	private void HurtEveryoneOutside()
	{
		var damage = DamagePerSecond;
		if ( damage <= 0f )
			return;

		foreach ( var pawn in GameUtils.PlayerPawns.ToArray() )
		{
			if ( !pawn.HealthComponent.IsValid() || pawn.HealthComponent.State != LifeState.Alive )
				continue;
			if ( DistanceOutside( pawn.WorldPosition ) <= 0f )
				continue;

			pawn.HealthComponent.TakeDamage( new DamageInfo( null, damage, Position: pawn.WorldPosition + Vector3.Up * 40f,
				Flags: DamageFlags.Zone ) );
		}

		foreach ( var bot in GameUtils.LightweightBots.ToArray() )
		{
			if ( !bot.IsValid() || !bot.IsAlive || DistanceOutside( bot.WorldPosition ) <= 0f )
				continue;

			bot.HealthComponent.TakeDamage( new DamageInfo( null, damage, Position: bot.WorldPosition + Vector3.Up * 40f,
				Flags: DamageFlags.Zone ) );
		}
	}

	/// <summary> Host: skip to the end of the zone's current hold or shrink. </summary>
	[ConCmd( "dev_zone_next" )]
	public static void DevNextStage()
	{
		if ( Current is null )
		{
			Log.Warning( "dev_zone_next: no safe zone in this match" );
			return;
		}

		Current.SkipStage();
	}
}
