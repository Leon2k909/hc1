using Sandbox;
using System.Linq;

namespace Facepunch;

public enum ZombieSpeed
{
	Walk,
	Jog,
	Sprint,
}

public sealed class ZombieAI : Component, Component.IDamageable
{
	public const string ZombieModel = "zombie_project/models/zombie_male.vmdl";
	public const string DriverModel = "models/citizen_human/citizen_human_male.vmdl";

	/// <summary>The visible zombie mesh (bone-merged onto the hidden animated driver).</summary>
	private SkinnedModelRenderer Body => Components.GetAll<SkinnedModelRenderer>( FindMode.InDescendants ).FirstOrDefault( r => r != Renderer ) ?? Renderer;

	[Property] public float AttackRange { get; set; } = 64f;
	[Property] public float AttackDamage { get; set; } = 45f;
	[Property] public float AttackCooldown { get; set; } = 1.2f;
	[Property] public float MaxHealth { get; set; } = 100f;
	[Property] public float CorpseLifetime { get; set; } = 90f;

	/// <summary>Set by the round system before spawning. Synced so every client animates at the right pace.</summary>
	[Property, Sync( SyncFlags.FromHost )] public ZombieSpeed Speed { get; set; } = ZombieSpeed.Walk;
	[Sync( SyncFlags.FromHost )] private bool ReachesWhileClose { get; set; }

	public float Health { get; private set; }

	[RequireComponent] private NavMeshAgent Agent { get; set; }
	[RequireComponent] private SkinnedModelRenderer Renderer { get; set; }

	private enum AnimState { Idle, Move, Attack, Dead }

	/// <summary>Host decides, everyone plays it — the renderer itself isn't networked.</summary>
	[Sync( SyncFlags.FromHost )] private AnimState Anim { get; set; } = AnimState.Idle;
	[Sync( SyncFlags.FromHost )] private bool IsDead { get; set; }

	private const string MoveSeq = "walk";
	private const string IdleSeq = "idle";
	private const string AttackSeq = "attack";

	// Attack: the swing winds up, then lands only if the target is still in reach.
	private const float AttackWindup = 0.45f;
	private const float AttackAnimHold = 0.8f;

	private TimeSince _lastAttack = 10f;
	private TimeSince _timeSinceAttackStart = 10f;
	private bool _swingPending;

	private PlayerPawn _target;
	private TimeSince _timeSinceRetarget = 10f;
	private TimeSince _timeSinceStuck;
	private TimeSince _timeSinceProgress;
	private Vector3 _stuckAnchor;
	private float _bestDistance = float.MaxValue;
	private Rigidbody _rb;

	public float MoveSpeed => Speed switch
	{
		ZombieSpeed.Sprint => 215f,
		ZombieSpeed.Jog => 135f,
		_ => 70f
	};

	/// <summary>Walk cycle playback rate, so faster zombies' legs keep up with their feet.</summary>
	private float AnimRate => Anim == AnimState.Move ? MoveSpeed / 80f : 1f;

	protected override void OnStart()
	{
		Health = MaxHealth;
		if ( Networking.IsHost ) ReachesWhileClose = Game.Random.Int( 0, 99 ) < 35;


		if ( Agent.IsValid() )
		{
			Agent.MaxSpeed = MoveSpeed;
			Agent.Acceleration = MoveSpeed * 6f;
			Agent.UpdateRotation = false;
			// Only the host simulates movement; clients get the networked transform.
			Agent.Enabled = Networking.IsHost;
		}

		_rb = Components.GetOrCreate<Rigidbody>();
		_rb.MotionEnabled = false;
	}

	protected override void OnUpdate()
	{
		UpdateAnimation();

		if ( IsDead || !Networking.IsHost ) return;

		if ( Agent.IsValid() ) Agent.MaxSpeed = MoveSpeed;

		// Leaping/falling: let physics run until we land.
		if ( _rb.IsValid() && _rb.MotionEnabled )
		{
			WorldRotation = Rotation.FromYaw( WorldRotation.Yaw() );
			_rb.AngularVelocity = Vector3.Zero;

			var tr = Scene.Trace.Ray( WorldPosition, WorldPosition + Vector3.Down * 60f )
				.IgnoreGameObjectHierarchy( GameObject )
				.Run();

			// Landed — or the leap went nowhere; either way hand control back to the navmesh
			// so a zombie can never end up frozen with its agent switched off.
			var landed = tr.Hit && _rb.Velocity.z > -10f && _timeSinceStuck > 0.5f;
			if ( landed || _timeSinceStuck > 2f )
			{
				_rb.MotionEnabled = false;
				if ( Agent.IsValid() ) Agent.Enabled = true;
			}
			return;
		}

		// Not leaping, so the agent should be driving. Recover if something switched it off.
		if ( Agent.IsValid() && !Agent.Enabled )
			Agent.Enabled = true;

		if ( _timeSinceRetarget > 0.5f || !IsValidTarget( _target ) )
		{
			_timeSinceRetarget = 0;
			_target = FindTarget();
		}

		if ( _swingPending && _timeSinceAttackStart > AttackWindup )
			LandSwing();

		if ( !IsValidTarget( _target ) )
		{
			if ( Agent.IsValid() && Agent.Enabled ) Agent.Stop();
			SetAnim( AnimState.Idle );
			return;
		}

		var toTarget = (_target.WorldPosition - WorldPosition).WithZ( 0 );
		if ( toTarget.LengthSquared > 0.1f )
			WorldRotation = Rotation.Lerp( WorldRotation, Rotation.LookAt( toTarget.Normal, Vector3.Up ), Time.Delta * 10f );

		var dist = WorldPosition.Distance( _target.WorldPosition );
		var attacking = _timeSinceAttackStart < AttackAnimHold;

		if ( Agent.IsValid() && Agent.Enabled )
		{
			if ( attacking && dist < AttackRange )
				Agent.Stop();
			else
				Agent.MoveTo( _target.WorldPosition + GetSeparationOffset() );
		}

		if ( dist <= AttackRange && _lastAttack > AttackCooldown && !_swingPending )
			StartSwing();

		if ( !attacking )
			SetAnim( Agent.IsValid() && Agent.Velocity.Length > 10f ? AnimState.Move : AnimState.Idle );

		UpdateStuck( dist );
	}

	private void UpdateStuck( float dist )
	{
		// Leap only if we're genuinely wedged: barely moved for 2s while still far from the target.
		var moved = WorldPosition.WithZ( 0 ).Distance( _stuckAnchor.WithZ( 0 ) );
		if ( moved > 24f ) { _stuckAnchor = WorldPosition; _timeSinceStuck = 0; }

		if ( Agent.IsValid() && Agent.Enabled && dist > AttackRange * 1.5f )
		{
			if ( _timeSinceStuck > 2f )
			{
				Agent.Enabled = false;
				_rb.MotionEnabled = true;
				var dir = (_target.WorldPosition - WorldPosition).WithZ( 0 ).Normal;
				_rb.Velocity = dir * 150f + Vector3.Up * 150f;
				_timeSinceStuck = 0;
				_stuckAnchor = WorldPosition;
			}
		}
		else
		{
			_timeSinceStuck = 0;
		}

		// Lost, or unable to reach anyone for a long time: go back in the queue and respawn closer.
		if ( dist < _bestDistance - 50f )
		{
			_bestDistance = dist;
			_timeSinceProgress = 0;
		}

		if ( _timeSinceProgress > 15f && dist > 1200f )
		{
			IsDead = true;
			ZombiesRoundSystem.Current?.OnZombieRecycled();
			GameObject.Destroy();
		}
	}

	private static bool IsValidTarget( PlayerPawn p ) =>
		p.IsValid() && p.HealthComponent.State == LifeState.Alive && ZombiesPlayerState.For( p )?.IsDowned != true;

	private PlayerPawn FindTarget()
	{
		return Scene.GetAllComponents<PlayerPawn>()
			.Where( IsValidTarget )
			.OrderBy( p => WorldPosition.DistanceSquared( p.WorldPosition ) )
			.FirstOrDefault();
	}

	private void StartSwing()
	{
		_lastAttack = 0;
		_timeSinceAttackStart = 0;
		_swingPending = true;
		SetAnim( AnimState.Attack );
		PlaySound( "zombie.attack" );
	}

	private void LandSwing()
	{
		_swingPending = false;
		if ( !IsValidTarget( _target ) ) return;

		// A bit of extra reach so the swing isn't dodged by standing still at the edge.
		if ( WorldPosition.Distance( _target.WorldPosition ) > AttackRange + 24f ) return;

		_target.HealthComponent.TakeDamage( new Facepunch.DamageInfo( this, AttackDamage, this, _target.WorldPosition + Vector3.Up * 40f ) );
	}

	// ── Animation (runs on every client) ────────────────────────────────────────
	private void SetAnim( AnimState state )
	{
		if ( Anim != state ) Anim = state;
	}

	private string _playingSeq;

	private Vector3 _lastPos;
	private Vector3 _smoothVel;

	private void UpdateAnimation()
	{
		if ( !Renderer.IsValid() ) return;
		if ( Renderer.UseAnimGraph ) { UpdateAnimGraph(); return; }
		if ( Anim == AnimState.Dead ) return;

		var (seq, loop) = Anim switch
		{
			AnimState.Move => (MoveSeq, true),
			AnimState.Attack => (AttackSeq, false),
			_ => (IdleSeq, true)
		};

		if ( _playingSeq != seq )
		{
			_playingSeq = seq;
			Renderer.Sequence.Name = seq;
			Renderer.Sequence.Looping = loop;
			Renderer.Sequence.Time = 0;
		}

		Renderer.Sequence.Time += Time.Delta * AnimRate;
	}

	/// <summary>Citizen anim graph: velocity from position deltas so proxies animate too.</summary>
	private void UpdateAnimGraph()
	{
		if ( Anim == AnimState.Dead ) return;

		var vel = Time.Delta > 0f ? (WorldPosition - _lastPos) / Time.Delta : Vector3.Zero;
		_lastPos = WorldPosition;
		if ( vel.Length > 600f ) vel = Vector3.Zero; // teleports / spawn
		_smoothVel = _smoothVel.LerpTo( vel.WithZ( 0 ), Time.Delta * 10f );

		var local = WorldRotation.Inverse * _smoothVel;
		Renderer.Set( "move_x", local.x );
		Renderer.Set( "move_y", local.y );
		Renderer.Set( "move_z", 0f );
		Renderer.Set( "move_speed", _smoothVel.Length );
		Renderer.Set( "move_groundspeed", _smoothVel.Length );
		Renderer.Set( "wish_x", local.x );
		Renderer.Set( "wish_y", local.y );
		Renderer.Set( "wish_speed", _smoothVel.Length );
		Renderer.Set( "move_style", Speed == ZombieSpeed.Walk ? 1 : 2 );
		Renderer.Set( "b_grounded", true );
		// Keep the unarmed pose while moving, then use the punch upper-body pose
		// only for the attack window so the arms visibly join the lunge.
		var closeToTarget = IsValidTarget( _target )
			&& WorldPosition.DistanceSquared( _target.WorldPosition ) <= 200f * 200f;
		Renderer.Set( "holdtype", Anim == AnimState.Attack ? 5 : ReachesWhileClose && closeToTarget ? 6 : 0 );
		Renderer.Set( "aim_body_weight", 1f );

		if ( Anim == AnimState.Attack && _playingSeq != "attack" )
		{
			_playingSeq = "attack";
			Renderer.Set( "b_attack", true );
		}
		else if ( Anim != AnimState.Attack )
		{
			_playingSeq = null;
		}
	}

	// How far apart zombies try to stay, and how strongly they push.
	private const float SeparationRadius = 50f;
	private const float SeparationStrength = 40f;

	/// <summary>Offset away from nearby zombies so they spread out instead of stacking.</summary>
	private Vector3 GetSeparationOffset()
	{
		var push = Vector3.Zero;
		var myPos = WorldPosition;

		foreach ( var other in Scene.GetAllComponents<ZombieAI>() )
		{
			if ( other == this || !other.IsValid() || other.IsDead ) continue;

			var away = (myPos - other.WorldPosition).WithZ( 0 );
			var d = away.Length;
			if ( d > 0.1f && d < SeparationRadius )
				push += away.Normal * (1f - d / SeparationRadius);
		}

		return push * SeparationStrength;
	}

	// ── Damage ──────────────────────────────────────────────────────────────────
	private bool IsHeadshot( Vector3 hitPos )
	{
		if ( !Renderer.IsValid() || hitPos == default ) return false;
		var bounds = Renderer.Bounds;
		var height = bounds.Maxs.z - bounds.Mins.z;
		return height > 1f && hitPos.z > bounds.Maxs.z - height * 0.2f;
	}

	public void OnDamage( in Sandbox.DamageInfo info )
	{
		if ( IsDead || !Networking.IsHost ) return;

		var attacker = info.Attacker?.GetComponentInParent<PlayerPawn>();
		var headshot = IsHeadshot( info.Position );

		var damage = info.Damage;
		if ( headshot ) damage *= 2f;
		if ( attacker.IsValid() && ZombiesPlayerState.For( attacker )?.HasPerk( ZombiesPerk.DoubleTap ) == true ) damage *= 2f;
		if ( ZombiesRoundSystem.Current?.IsPowerUpActive( ZombiesPowerUpType.InstaKill ) == true ) damage = Health + 1f;

		// One brief impact, even for headshots; group near-simultaneous shotgun pellets.
		if ( damage > 0f && _timeSinceBloodImpact >= 0.03f )
		{
			_timeSinceBloodImpact = 0;
			SpawnBlood( info.Position == default ? WorldPosition + Vector3.Up * 30f : info.Position );
		}
		Health -= damage;

		var eco = attacker?.GetComponent<ZombiesPlayerEconomy>();

		if ( Health <= 0 )
		{
			eco?.AddPoints( headshot ? 100 : 60 );
			eco?.AddKill();
			Kill( attacker?.GameObject );
		}
		else
		{
			eco?.AddPoints( 10 );
			PlaySound( "zombie.pain" );
		}
	}

	/// <summary>Host: kill this zombie (from damage, or a Nuke with no attacker).</summary>
	public void Kill( GameObject attacker )
	{
		if ( IsDead || !Networking.IsHost ) return;
		IsDead = true;
		Anim = AnimState.Dead;

		if ( Agent.IsValid() )
		{
			Agent.Stop();
			Agent.Enabled = false;
		}

		GoRagdoll( attacker.IsValid() ? (WorldPosition - attacker.WorldPosition).WithZ( 0 ).Normal : Vector3.Zero );

		// Models without physics: topple the whole body instead.
		if ( !_ragdolled && _rb.IsValid() )
		{
			_rb.MotionEnabled = true;
			_rb.Enabled = true;

			var dir = attacker.IsValid()
				? (WorldPosition - attacker.WorldPosition).WithZ( 0 ).Normal
				: Vector3.Random.WithZ( 0 ).Normal;

			_rb.Velocity = dir * 120f + Vector3.Up * 100f;
			_rb.AngularVelocity = Vector3.Random * 8f;
		}

		PlaySound( "zombie.die" );

		// Corpses stop soaking up bullets meant for the zombies behind them.
		GameObject.Tags.Remove( "enemy" );

		ZombiesRoundSystem.Current?.OnZombieKilled( WorldPosition );

		GameObject.DestroyAsync( CorpseLifetime );
	}

	private bool _ragdolled;

	[Rpc.Broadcast]
	private void GoRagdoll( Vector3 push )
	{
		// Ragdoll the hidden human driver; the zombie mesh stays bone-merged onto it.
		if ( !Renderer.IsValid() || Renderer.Model?.Physics is null ) return;
		_ragdolled = true;
		Renderer.UseAnimGraph = false;

		if ( _rb.IsValid() ) _rb.Enabled = false;
		foreach ( var c in Components.GetAll<Collider>() ) c.Enabled = false;

		var physics = Components.Create<ModelPhysics>();
		physics.Model = Renderer.Model;
		physics.Renderer = Renderer;

		foreach ( var part in physics.Bodies )
			if ( part.Component is Rigidbody rb ) rb.Velocity = push * 200f + Vector3.Up * 60f;
	}

	[Rpc.Broadcast]
	private void PlaySound( string sound )
	{
		Sound.Play( sound, WorldPosition );
	}

	private TimeSince _timeSinceBloodImpact = 1f;

	private void SpawnBlood( Vector3 pos )
	{
		if ( Application.IsDedicatedServer ) return;

		var prefabFile = ResourceLibrary.Get<PrefabFile>( "prefabs/impact_fx/impact_zombie_blood.prefab" );
		if ( prefabFile is null ) return;

		var prefab = SceneUtility.GetPrefabScene( prefabFile );
		if ( !prefab.IsValid() ) return;

		var blood = prefab.Clone( new CloneConfig { StartEnabled = false } );
		blood.WorldPosition = pos;
		blood.NetworkMode = NetworkMode.Never;
		blood.Enabled = true;
		blood.DestroyAsync( 0.6f );
	}
}
