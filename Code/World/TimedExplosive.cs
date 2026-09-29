
using Facepunch;
using Sandbox.Events;
using DamageInfo = Facepunch.DamageInfo;

public sealed class TimedExplosive : Component, IUse, IMinimapIcon, IDescription
{
	[Property, Category( "Config" )]
	public float Duration { get; set; } = 45f;

	/// <summary>
	/// How long the defuse will take without a defuse kit.
	/// </summary>
	[Property, Category( "Config" )]
	public float BaseDefuseTime { get; set; } = 10f;

	/// <summary>
	/// How long the defuse will take with a defuse kit.
	/// </summary>
	[Property, Category( "Config" )]
	public float FastDefuseTime { get; set; } = 5f;

	/// <summary>
	/// How long the defuse will take, based on if the defuser has a defuse kit.
	/// </summary>
	public float DefuseTime => DefusingPlayer?.Inventory.HasDefuseKit ?? false
		? FastDefuseTime
		: BaseDefuseTime;

	public float Progress => Math.Clamp( TimeSinceDefuseStart / DefuseTime, 0f, 1f );

	[Sync( SyncFlags.FromHost )] public TimeSince TimeSinceDefuseStart { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSincePlanted { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsDefused { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool HasDetonated { get; private set; }
	public float SecondsRemaining => Math.Max( 0f, Duration - TimeSincePlanted );

	// IDescription
	string IDescription.DisplayName => "C4";
	string IDescription.Icon => "/ui/items/field_device.svg";

	public TimeSince TimeSinceLastBeep { get; private set; }

	[Property, Category( "Effects" )]
	public SoundEvent BeepSound { get; set; }

	[Property, Category( "Effects" )]
	public SoundEvent DefuseStartSound { get; set; }

	[Property, Category( "Effects" )]
	public SoundEvent DefuseEndSound { get; set; }

	[Property, Category( "Effects" )]
	public Curve BeepFrequency { get; set; } = new Curve( new Curve.Frame( 0f, 1f ), new Curve.Frame( 1f, 0.25f ) );

	[Property, Category( "Effects" )]
	public GameObject ExplosionPrefab { get; set; }

	[Property, Category( "Effects" )]
	public GameObject BeepEffectPrefab { get; set; }

	[Property, Category( "Effects" )]
	public LineRenderer Wires { get; set; }

	/// <summary>
	/// Bomb site this bomb was planted at.
	/// </summary>
	private BombSite BombSite { get; set; }
	public void InitializeSite( BombSite site ) => BombSite = site;

	[RequireComponent] public Spottable Spottable { get; private set; }

	[Sync( SyncFlags.FromHost )] public PlayerPawn DefusingPlayer { get; private set; }

	string IMinimapIcon.IconPath => "ui/minimaps/icon-map_bomb.png";

	Vector3 IMinimapElement.WorldPosition => WorldPosition;

	protected override void OnStart()
	{
		if ( Networking.IsHost ) TimeSincePlanted = 0f;
		TimeSinceLastBeep = 0f;
		
		BombSite ??= Zone.GetAt( WorldPosition )
			.Select( x => x.GetComponent<BombSite>() )
			.FirstOrDefault( x => x is not null );

		if ( !BombSite.IsValid() )
			Log.Warning( $"Bomb site is null!" );
		
		base.OnStart();
	}

	protected override void OnUpdate()
	{
		base.OnUpdate();
		if ( Wires.IsValid() && Wires.Points.Count > 1 )
			Wires.Points[1] = !IsDefused && !HasDetonated && DefusingPlayer.IsValid() ? DefusingPlayer.CameraGameObject : null;

		if ( IsDefused || HasDetonated )
		{
			return;
		}

		BeepEffects();

		if ( !Networking.IsHost ) return;

		// Completion is only possible while the defender is still alive, holding use and in reach.
		if ( DefusingPlayer is not null )
		{
			if ( !CanContinueDefusing() )
			{
				CancelDefusing();
			}
			else if ( TimeSinceDefuseStart >= DefuseTime && TimeSincePlanted - TimeSinceDefuseStart + DefuseTime <= Duration )
			{
				FinishDefusing();
				return;
			}
		}

		if ( TimeSincePlanted >= Duration )
		{
			Explode();
		}
	}

	private void Explode()
	{
		if ( HasDetonated || IsDefused ) return;
		HasDetonated = true;
		CancelDefusing();
		if ( ExplosionPrefab.IsValid() )
		{
			var explosion = ExplosionPrefab.Clone( WorldPosition, Rotation.FromYaw( Random.Shared.NextSingle() * 360f ) );
			explosion.NetworkSpawn();
		}

		Scene.Dispatch( new BombDetonatedEvent( GameObject, BombSite ) );

		if ( BombSite is not null )
		{
			// Bomb site determines damage, so safe radius can be tuned by the mapper

			foreach ( var health in Scene.GetAllComponents<HealthComponent>() )
			{
				var diff = health.WorldPosition - WorldPosition;
				var damage = BombSite.GetExplosionDamage( diff.Length );

				if ( damage <= 0f )
				{
					continue;
				}

				health.TakeDamage( new DamageInfo( null, damage, this,
					WorldPosition, diff.Normal * damage * 100f,
					HitboxTags.UpperBody, DamageFlags.Explosion ) );
			}
		}

		GameObject.Destroy();
	}

	private void BeepEffects()
	{
		var t = Math.Clamp( TimeSincePlanted / Duration, 0f, 1f );

		if ( TimeSinceLastBeep > BeepFrequency.Evaluate( t ) )
		{
			TimeSinceLastBeep = 0f;

			if ( BeepSound is not null )
			{
				Sound.Play( BeepSound, WorldPosition );
			}

			if ( BeepEffectPrefab.IsValid() )
			{
				BeepEffectPrefab.Clone( WorldPosition + Vector3.Up * 4f );
			}
		}
	}

	public void StartDefusing( PlayerPawn player )
	{
		if ( !Networking.IsHost || !CanUse( player ).CanUse ) return;

		DefusingPlayer = player;
		TimeSinceDefuseStart = 0f;
		PlayDefuseSound( false );
		RadioSounds.Play( player.Team, "Hidden", "Defusing the bomb" );
		player.IsFrozen = true;
		Scene.Dispatch( new BombDefuseStartEvent( player, GameObject, BombSite ) );
	}

	public void FinishDefusing()
	{
		if ( !Networking.IsHost || IsDefused || HasDetonated || !DefusingPlayer.IsValid() ) return;
		var player = DefusingPlayer;
		IsDefused = true;
		CancelDefusing();
		PlayDefuseSound( true );
		Scene.Dispatch( new BombDefusedEvent( player, GameObject, BombSite ) );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void PlayDefuseSound( bool finished )
	{
		var sound = finished ? DefuseEndSound : DefuseStartSound;
		if ( sound is not null ) Sound.Play( sound, WorldPosition );
	}

	public void CancelDefusing()
	{
		if ( !Networking.IsHost ) return;
		if ( DefusingPlayer.IsValid() )
		{
			DefusingPlayer.IsFrozen = GameMode.Instance?.Get<FreezePlayers>() is { Active: true };
		}

		if ( Wires.IsValid() && Wires.Points.Count > 1 ) Wires.Points[1] = null;
		DefusingPlayer = null;
	}

	public UseResult CanUse( PlayerPawn player )
	{
		return !IsDefused && !HasDetonated && !DefusingPlayer.IsValid() && IsDefenderInReach( player );
	}

	private bool IsDefenderInReach( PlayerPawn player ) => player.IsValid()
		&& player.Team == Team.CounterTerrorist && player.HealthComponent.State == LifeState.Alive
		&& player.WorldPosition.Distance( WorldPosition ) <= player.UseDistance;

	private bool CanContinueDefusing() => IsDefenderInReach( DefusingPlayer ) && DefusingPlayer.IsUsing;

	protected override void OnDisabled() { if ( Networking.IsHost ) CancelDefusing(); }
	protected override void OnDestroy() { if ( Networking.IsHost ) CancelDefusing(); }

	public void OnUse( PlayerPawn player )
	{
		if ( !Networking.IsHost || !CanUse( player ).CanUse ) return;
		StartDefusing( player );
	}

	bool IMinimapElement.IsVisible( Pawn viewer )
	{
		if ( Spottable.IsSpotted )
			return true;

		return viewer.Team == Team.Terrorist;
	}
}
