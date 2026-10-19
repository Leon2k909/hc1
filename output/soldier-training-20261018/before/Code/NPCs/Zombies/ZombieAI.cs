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
	/// <summary>Invisible citizen that plays NMRIH's zombie clips (ZombieClips, Tools/zombie_anims.py) as sequences.</summary>
	public const string DriverModel = "models/zombie/zombie_driver.vmdl";
	/// <summary>Stand-in driver if that one's missing: the citizen, walking with its human animgraph.</summary>
	public const string CitizenModel = "models/citizen_human/citizen_human_male.vmdl";

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
	/// <summary>Counts swings, so every client starts each one and picks the same attack clip.</summary>
	[Sync( SyncFlags.FromHost )] private int SwingCount { get; set; }

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
	/// <summary>When it groans next while it hunts (host).</summary>
	private TimeUntil _nextGroan;
	/// <summary>Hits a moment apart (a burst, a shotgun's pellets) get one grunt.</summary>
	private TimeSince _timeSincePain = 10f;

	public float MoveSpeed => Speed switch
	{
		ZombieSpeed.Sprint => 215f,
		ZombieSpeed.Jog => 135f,
		_ => 70f
	};

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
		_nextGroan = Game.Random.Float( 0.5f, 6f );
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
			// Physics moved it: KeepOut starts again from wherever it lands.
			_hasStep = false;
			return;
		}

		// Not leaping, so the agent should be driving. Recover if something switched it off.
		if ( Agent.IsValid() && !Agent.Enabled )
			Agent.Enabled = true;

		if ( Agent.IsValid() && Agent.Enabled )
			KeepOut();

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

		if ( Agent.IsValid() && Agent.Enabled && WaitForDoor() )
			return;

		var toTarget = (_target.WorldPosition - WorldPosition).WithZ( 0 );
		if ( toTarget.LengthSquared > 0.1f )
			WorldRotation = Rotation.Lerp( WorldRotation, Rotation.LookAt( toTarget.Normal, Vector3.Up ), Time.Delta * 10f );

		var dist = WorldPosition.Distance( _target.WorldPosition );
		var attacking = _timeSinceAttackStart < AttackAnimHold;

		if ( Agent.IsValid() && Agent.Enabled )
		{
			// It stops at arm's length to swing rather than walking on into them.
			var close = WorldPosition.WithZ( 0 ).Distance( _target.WorldPosition.WithZ( 0 ) ) < StandOff
				&& MathF.Abs( WorldPosition.z - _target.WorldPosition.z ) < 48f;
			if ( close || attacking && dist < AttackRange )
				Agent.Stop();
			else
				MoveToward( _target.WorldPosition + GetSeparationOffset() );
		}

		if ( !attacking && _nextGroan <= 0f )
		{
			_nextGroan = Game.Random.Float( 5f, 12f );
			PlayVoice( ZombieVoice.Groan );
		}

		if ( !attacking )
			SetAnim( Agent.IsValid() && Agent.Velocity.Length > 10f ? AnimState.Move : AnimState.Idle );

		// Start the attack after selecting idle/move so this update can't overwrite its attack pose.
		if ( dist <= AttackRange && _lastAttack > AttackCooldown && !_swingPending )
			StartSwing();

		UpdateStuck( dist );
	}

	/// <summary>The longest (s) the agent keeps going for a goal that has moved a little, before it's sent the new one.</summary>
	private const float RepathInterval = 0.2f;
	private TimeSince _timeSinceMoveTo;

	/// <summary>
	/// Send the agent after <paramref name="goal"/>. A new goal is a path search, and the player and the zombies round it
	/// move every frame, so every zombie searched every frame. Now a goal that has only moved a little (a twentieth of the
	/// way there, 2 to 32 units) waits up to <see cref="RepathInterval"/>. Close in, every few units still count. A stopped
	/// or new agent has no goal, and gets this one at once.
	/// </summary>
	private void MoveToward( Vector3 goal )
	{
		if ( _timeSinceMoveTo < RepathInterval && Agent.TargetPosition is { } current )
		{
			var tolerance = (WorldPosition.Distance( goal ) * 0.05f).Clamp( 2f, 32f );
			if ( current.DistanceSquared( goal ) < tolerance * tolerance )
				return;
		}

		_timeSinceMoveTo = 0;
		Agent.MoveTo( goal );
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

	// ── Keeping out of shut doors and players (host) ────────────────────────────
	/// <summary>
	/// How close its centre comes to a player's. Its capsule (16) and their box (12 to a side, 17 at the corners) touch at
	/// 28-33. Walked into them, it pinned them: their box started inside its capsule, and the controller could only hop
	/// them about trying to get out.
	/// </summary>
	private const float PlayerClearance = 34f;
	/// <summary>Where it stops short of its target to swing at them: inside AttackRange, outside PlayerClearance.</summary>
	private const float StandOff = 40f;
	/// <summary>A step longer than this is a teleport, not a walk.</summary>
	private const float MaxStep = 120f;

	private Vector3 _lastStep;
	private bool _hasStep;

	/// <summary>
	/// The navmesh agent moves a zombie with no collision, and doors are left out of the navmesh so paths go through
	/// doorways. FindDoorAhead only stops it for a door within 80 straight ahead, so on Innocent Hotel zombies coming at a
	/// door from an angle walked through it. So each update the agent's last step is checked, and taken back if it went
	/// into a shut door (which it then opens and waits for, as WaitForDoor does) or into a player.
	/// </summary>
	private void KeepOut()
	{
		var to = WorldPosition;
		var from = _lastStep;
		if ( !_hasStep || from.DistanceSquared( to ) > MaxStep * MaxStep )
		{
			_lastStep = to;
			_hasStep = true;
			return;
		}

		if ( from.DistanceSquared( to ) < 0.0001f )
			return;

		var door = ShutDoorOnStep( from, to );
		if ( door.IsValid() )
		{
			if ( !_door.IsValid() && door.OpenForNpc( from ) )
			{
				_door = door;
				_doorGiveUp = 2f;
				Agent.Stop();
				SetAnim( AnimState.Attack );
			}
		}
		else if ( PlayerInTheWay( from, to ) is { } blocker )
		{
			// Someone else stepped in front of it: they're who it goes for now.
			if ( blocker != _target && IsValidTarget( blocker ) )
			{
				_target = blocker;
				_timeSinceRetarget = 0;
			}
		}
		else
		{
			_lastStep = to;
			return;
		}

		Agent.SetAgentPosition( from );
		WorldPosition = from;
	}

	/// <summary>A door that isn't open enough to get through, if the zombie's body ran into it on the step from
	/// <paramref name="from"/> to <paramref name="to"/>.</summary>
	private TerrorTown.MapMover ShutDoorOnStep( Vector3 from, Vector3 to )
	{
		var waist = Vector3.Up * 40f;
		var tr = Scene.Trace.Sphere( 16f, from + waist, to + waist )
			.WithTag( TerrorTown.MapMover.DoorTag )
			.IgnoreGameObjectHierarchy( GameObject )
			.Run();

		// Started inside it: the door shut on it, so let it get out.
		if ( !tr.Hit || tr.StartedSolid )
			return null;

		var door = tr.GameObject?.GetComponentInParent<TerrorTown.MapMover>();
		return door.IsValid() && door.OpenAmount < TerrorTown.MapMover.OpenEnough ? door : null;
	}

	/// <summary>A player the step took it nearer to, within PlayerClearance. Downed players count: one stood on would get
	/// up inside it.</summary>
	private PlayerPawn PlayerInTheWay( Vector3 from, Vector3 to )
	{
		foreach ( var pawn in LivingPawns() )
		{
			if ( !pawn.IsValid() || pawn.HealthComponent.State != LifeState.Alive )
				continue;

			var at = pawn.WorldPosition;
			if ( MathF.Abs( at.z - to.z ) > 72f )
				continue;

			var near = to.WithZ( 0 ).Distance( at.WithZ( 0 ) );
			if ( near < PlayerClearance && near < from.WithZ( 0 ).Distance( at.WithZ( 0 ) ) )
				return pawn;
		}

		return null;
	}

	private TerrorTown.MapMover _door;
	private TimeUntil _doorGiveUp;
	private TimeSince _timeSinceDoorCheck;

	/// <summary>A shut door in the way: shove it open and wait until it's open enough to get through.</summary>
	private bool WaitForDoor()
	{
		if ( _door.IsValid() )
		{
			if ( _door.OpenAmount < TerrorTown.MapMover.OpenEnough && _doorGiveUp.Relative > 0f && _door.OpenForNpc( WorldPosition ) )
				return true;

			_door = null;
			// Waiting at a door isn't being wedged.
			_stuckAnchor = WorldPosition;
			_timeSinceStuck = 0;
			return false;
		}

		if ( _timeSinceDoorCheck < 0.1f )
			return false;

		_timeSinceDoorCheck = 0;
		var door = TerrorTown.MapMover.FindDoorAhead( Scene, WorldPosition, Agent.Velocity );
		if ( !door.IsValid() || !door.OpenForNpc( WorldPosition ) )
			return false;

		_door = door;
		_doorGiveUp = 2f;
		Agent.Stop();
		SetAnim( AnimState.Attack );
		return true;
	}

	private static bool IsValidTarget( PlayerPawn p ) =>
		p.IsValid() && p.HealthComponent.State == LifeState.Alive && ZombiesPlayerState.For( p )?.IsDowned != true;

	private PlayerPawn FindTarget()
	{
		PlayerPawn nearest = null;
		var nearestDistance = float.MaxValue;
		foreach ( var pawn in LivingPawns() )
		{
			if ( !IsValidTarget( pawn ) )
				continue;

			var distance = WorldPosition.DistanceSquared( pawn.WorldPosition );
			if ( distance < nearestDistance )
			{
				nearest = pawn;
				nearestDistance = distance;
			}
		}

		return nearest;
	}

	/// <summary>
	/// The living player pawns, from this frame's <see cref="BotSystem"/> list: every zombie searched the scene for them
	/// several times a frame. Pawns whose state changed since are checked again by the callers.
	/// </summary>
	private List<PlayerPawn> LivingPawns() => Scene.GetSystem<BotSystem>()?.AlivePawns
		?? Scene.GetAllComponents<PlayerPawn>().Where( x => x.HealthComponent.IsValid() ).ToList();

	private void StartSwing()
	{
		_lastAttack = 0;
		_timeSinceAttackStart = 0;
		_swingPending = true;
		SwingCount++;
		SetAnim( AnimState.Attack );
		PlayVoice( ZombieVoice.Attack );
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
	private int _playingSwing = -1;

	private Vector3 _lastPos;
	private Vector3 _smoothVel;

	private void UpdateAnimation()
	{
		if ( !Renderer.IsValid() || Anim == AnimState.Dead ) return;

		// Velocity from position deltas, so proxies animate too.
		var vel = Time.Delta > 0f ? (WorldPosition - _lastPos) / Time.Delta : Vector3.Zero;
		_lastPos = WorldPosition;
		if ( vel.Length > 600f ) vel = Vector3.Zero; // teleports / spawn
		_smoothVel = _smoothVel.LerpTo( vel.WithZ( 0 ), Time.Delta * 10f );

		if ( Renderer.UseAnimGraph ) UpdateAnimGraph();
		else UpdateSequence();
	}

	/// <summary>A per-zombie constant in [0, 1), the same on every client: its walk, and where in the cycle it
	/// starts, so a crowd doesn't march in step.</summary>
	private float Quirk => (GameObject.Id.GetHashCode() & 0xffff) / 65536f;

	private ZombieClip MoveClip => Speed == ZombieSpeed.Walk
		? ZombieClips.Walks[(int)(Quirk * ZombieClips.Walks.Length)]
		: ZombieClips.Run;

	private static int Scramble( int x )
	{
		unchecked
		{
			var h = (uint)x * 0x9E3779B1u;
			return (int)((h ^ (h >> 16)) & 0x7fffffff);
		}
	}

	/// <summary>The zombie driver's clips, crossfaded.</summary>
	private void UpdateSequence()
	{
		var seq = Renderer.Sequence;
		switch ( Anim )
		{
			case AnimState.Move:
			{
				var clip = MoveClip;
				if ( _playingSeq != clip.Name ) Play( clip, true, Quirk * clip.Duration );

				// Feet keep pace with the ground: Walkers (70) play the walk (made for 70) at 1x. Past 1.4x its cadence
				// turns frantic, so faster feet slide a little instead. Jogs are the run slowed down. Each zombie starts
				// at its own point in the cycle (Quirk), so a crowd doesn't march in step; a rate of its own would make
				// its feet slide.
				var (min, max) = Speed == ZombieSpeed.Walk ? (0.6f, 1.4f) : (0.55f, 1.3f);
				seq.PlaybackRate = (_smoothVel.Length / clip.Speed).Clamp( min, max );
				break;
			}

			case AnimState.Attack:
			{
				// Each swing picks an attack; pounding on a door repeats it.
				if ( _playingSwing != SwingCount || _playingSeq?.StartsWith( "attack" ) != true || seq.IsFinished )
				{
					var clip = ZombieClips.Attacks[Scramble( GameObject.Id.GetHashCode() + SwingCount ) % ZombieClips.Attacks.Length];
					// Start part-way in, so the blow lands when the damage does (AttackWindup).
					Play( clip, false, (clip.Hit - AttackWindup).Clamp( 0f, clip.Duration ) );
					_playingSwing = SwingCount;
				}
				seq.PlaybackRate = 1f;
				break;
			}

			default:
				if ( _playingSeq != ZombieClips.Idle.Name ) Play( ZombieClips.Idle, true, Quirk * ZombieClips.Idle.Duration );
				seq.PlaybackRate = 1f;
				break;
		}
	}

	private void Play( ZombieClip clip, bool loop, float time )
	{
		var seq = Renderer.Sequence;
		seq.Blending = true;
		seq.Name = clip.Name;
		seq.Looping = loop;
		seq.Time = time;
		_playingSeq = clip.Name;
	}

	/// <summary>Fallback citizen driver: its human anim graph.</summary>
	private void UpdateAnimGraph()
	{
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
		Renderer.SetBool( "b_grounded", true );
		// Keep the unarmed pose while moving, then use the punch upper-body pose
		// only for the attack window so the arms visibly join the lunge.
		var closeToTarget = IsValidTarget( _target )
			&& WorldPosition.DistanceSquared( _target.WorldPosition ) <= 200f * 200f;
		Renderer.Set( "holdtype", Anim == AnimState.Attack ? 5 : ReachesWhileClose && closeToTarget ? 6 : 0 );
		Renderer.Set( "aim_body_weight", 1f );

		if ( Anim == AnimState.Attack && _playingSeq != "attack" )
		{
			_playingSeq = "attack";
			Renderer.SetBool( "b_attack", true );
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

		// This frame's list of them (BotSystem): every zombie searching the scene for the rest, every frame, was n² finds.
		var zombies = Scene.GetSystem<BotSystem>()?.Zombies ?? Scene.GetAllComponents<ZombieAI>().ToList();
		foreach ( var other in zombies )
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

		// Bullets stop on the capsule, so go by height: from the jaw up (the head bone is the top of the neck).
		// Zombies hunch and lunge, so their head is well below the capsule's top.
		if ( Renderer.TryGetBoneTransform( "head", out var head ) )
			return hitPos.z > head.Position.z - 1f;

		var bounds = Renderer.Bounds;
		var height = bounds.Maxs.z - bounds.Mins.z;
		return height > 1f && hitPos.z > bounds.Maxs.z - height * 0.2f;
	}

	public void OnDamage( in Sandbox.DamageInfo info )
	{
		if ( IsDead || !Networking.IsHost ) return;

		var attacker = info.Attacker?.GetComponentInParent<PlayerPawn>();

		// Fire (SurfaceFire) isn't a hit: no blood, hitmarker or flinch, and only the kill pays.
		var burn = info.Tags?.Has( "burn" ) == true;
		var headshot = !burn && IsHeadshot( info.Position );

		var damage = info.Damage;
		if ( headshot ) damage *= 2f;
		if ( attacker.IsValid() && ZombiesPlayerState.For( attacker )?.HasPerk( ZombiesPerk.HotShot ) == true ) damage *= 2f;
		if ( ZombiesRoundSystem.Current?.IsPowerUpActive( ZombiesPowerUpType.OneHitKills ) == true ) damage = Health + 1f;

		// One brief impact, even for headshots; group near-simultaneous shotgun pellets.
		if ( damage > 0f && !burn && _timeSinceBloodImpact >= 0.03f )
		{
			_timeSinceBloodImpact = 0;
			SpawnBlood( info.Position == default ? WorldPosition + Vector3.Up * 30f : info.Position );
		}
		Health -= damage;

		if ( damage > 0f && !burn && attacker.IsValid() )
			ShowHitmarker( attacker, Health <= 0, headshot );

		var eco = attacker?.GetComponent<ZombiesPlayerEconomy>();

		if ( Health <= 0 )
		{
			eco?.AddPoints( headshot ? 100 : 60, "Killed a zombie" );
			eco?.AddKill();
			Kill( attacker?.GameObject );
		}
		else if ( !burn )
		{
			eco?.AddPoints( 10 );
			if ( _timeSincePain > 0.35f )
			{
				_timeSincePain = 0;
				PlayVoice( ZombieVoice.Pain );
			}
		}
	}

	/// <summary>Host: kill this zombie (from damage, or a Clean Sweep with no attacker).</summary>
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
			_rb.RigidbodyFlags |= RigidbodyFlags.DisableCollisionSounds;
			_rb.MotionEnabled = true;
			_rb.Enabled = true;

			var dir = attacker.IsValid()
				? (WorldPosition - attacker.WorldPosition).WithZ( 0 ).Normal
				: Vector3.Random.WithZ( 0 ).Normal;

			_rb.Velocity = dir * 120f + Vector3.Up * 100f;
			_rb.AngularVelocity = Vector3.Random * 8f;
		}

		PlayVoice( ZombieVoice.Death );

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
		// Footsteps look through corpses to the floor (PlayerFootsteps), and players walk through them (their movement
		// ignores "ragdoll").
		GameObject.Tags.Add( "corpse" );
		GameObject.Tags.Add( "ragdoll" );

		if ( _rb.IsValid() ) _rb.Enabled = false;
		foreach ( var c in Components.GetAll<Collider>() ) c.Enabled = false;

		// Bumping into a corpse is silent: no flesh impact sounds from its bodies.
		ModelPhysics physics;
		if ( IsProxy )
		{
			physics = CreateLocalCorpse();
		}
		else
		{
			physics = Components.Create<ModelPhysics>();
			physics.RigidbodyFlags |= RigidbodyFlags.DisableCollisionSounds;
			physics.Model = Renderer.Model;
			physics.Renderer = Renderer;
		}

		foreach ( var part in physics.Bodies )
		{
			if ( part.Component is not Rigidbody rb ) continue;
			rb.RigidbodyFlags |= RigidbodyFlags.DisableCollisionSounds;
			rb.Velocity = push * 200f + Vector3.Up * 60f;
		}
	}

	private GameObject _localCorpse;

	/// <summary>
	/// The corpse on a machine that doesn't own the zombie. The engine builds no ragdoll on an object another machine
	/// owns (ModelPhysics.CreatePhysics returns on a proxy), so on every client a zombie's body stood in its bind pose, a
	/// T-pose, and the driver's physics can't go on the zombie itself. So it's a local object: a copy of the hidden
	/// driver whose bodies start from the zombie's pose, with the zombie mesh moved across and bone-merged onto it. It
	/// goes when the zombie does.
	/// </summary>
	private ModelPhysics CreateLocalCorpse()
	{
		var corpse = new GameObject( true, "Zombie corpse" );
		corpse.WorldTransform = Renderer.WorldTransform;
		corpse.Tags.Add( "corpse" );
		corpse.Tags.Add( "ragdoll" );

		var driver = corpse.Components.Create<SkinnedModelRenderer>();
		driver.Model = Renderer.Model;
		driver.UseAnimGraph = false;
		driver.RenderType = Renderer.RenderType;
		driver.RenderOptions.Game = Renderer.RenderOptions.Game;
		driver.Tint = Renderer.Tint;

		// Built from the zombie's own renderer, so the bodies start where its bones are, then they drive the copy.
		var physics = corpse.Components.Create<ModelPhysics>( false );
		physics.RigidbodyFlags |= RigidbodyFlags.DisableCollisionSounds;
		physics.Model = Renderer.Model;
		physics.Renderer = Renderer;
		physics.Enabled = true;
		physics.Renderer = driver;

		foreach ( var mesh in Components.GetAll<SkinnedModelRenderer>( FindMode.InDescendants ).ToList() )
		{
			if ( mesh == Renderer || mesh.BoneMergeTarget != Renderer ) continue;
			mesh.GameObject.SetParent( corpse, true );
			mesh.BoneMergeTarget = driver;
		}

		Renderer.Enabled = false;
		corpse.DestroyAsync( CorpseLifetime );
		_localCorpse = corpse;
		return physics;
	}

	protected override void OnDestroy()
	{
		if ( _localCorpse.IsValid() )
			_localCorpse.Destroy();

		// A recycled zombie stops groaning. A dead one's rattle isn't parented to it, so it plays out.
		if ( !IsDead )
			_voice?.Stop( 0.1f );
	}

	// ── Voice (Tools/zombie_sounds.py) ──────────────────────────────────────────
	private enum ZombieVoice { Groan, Attack, Pain, Death }

	private SoundHandle _voice;

	/// <summary>
	/// Its voice, from the mouth, following it. A new sound cuts the last one short, since it has one throat. Each set is
	/// synthesised (Tools/zombie_sounds.py); until its event has compiled, s&box's stock zombie sound plays instead.
	/// </summary>
	[Rpc.Broadcast]
	private void PlayVoice( ZombieVoice voice )
	{
		if ( Application.IsDedicatedServer )
			return;

		var (path, stock) = voice switch
		{
			ZombieVoice.Attack => ("sounds/zombies/zombie_attack.sound", "zombie.attack"),
			ZombieVoice.Pain => ("sounds/zombies/zombie_pain.sound", "zombie.pain"),
			ZombieVoice.Death => ("sounds/zombies/zombie_death.sound", "zombie.die"),
			_ => ("sounds/zombies/zombie_groan.sound", null),
		};

		var mouth = WorldPosition + Vector3.Up * 58f;
		var evt = ResourceLibrary.Get<SoundEvent>( path );
		if ( evt is null && stock is null )
			return;

		_voice?.Stop( 0.08f );
		_voice = evt is not null ? Sound.Play( evt, mouth ) : Sound.Play( stock, mouth );
		if ( _voice is null || voice == ZombieVoice.Death )
			return;

		// It moves while it groans. A dying one's last breath stays where it fell.
		_voice.Parent = GameObject;
		_voice.FollowParent = true;
	}

	/// <summary>
	/// The shooter's hitmarker, and on a kill the kill sound, on whichever machine is viewing them. A bot's hit sends them
	/// through HealthComponent's DamageGivenEvent and KillEvent, but zombies take damage here instead.
	/// </summary>
	[Rpc.Broadcast]
	private void ShowHitmarker( PlayerPawn attacker, bool kill, bool headshot )
	{
		if ( !attacker.IsValid() || !attacker.IsViewer )
			return;

		Crosshair.Instance?.ShowHit( kill, headshot );
		if ( kill )
			KillSounds.OnZombieKill( headshot );
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
