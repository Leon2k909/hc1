namespace Facepunch;

public partial class Client
{
	[Sync( SyncFlags.FromHost )] public int EnduranceXP { get; private set; }
	[Sync( SyncFlags.FromHost )] public int HandlingXP { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool TrainingReady { get; private set; }

	private RealTimeSince _timeSinceTrainingProfileSent = 10f;
	private Connection _trainingProfileConnection;
	private bool _wasLocalTrainingClient;
	private TimeSince _timeSinceTrainingSample;
	private TimeSince _timeSinceTrainingShot = 10f;
	private TimeSince _timeSinceTrainingHit = 10f;
	private PlayerPawn _trainingPawn;
	private Vector3 _trainingPosition;
	private bool _trainingWasRunning;
	private float _trainingMetres;

	public int GetTrainingXP( SoldierSkill skill ) => !IsBot && TrainingReady
		? skill == SoldierSkill.Endurance ? EnduranceXP : HandlingXP : 0;

	internal void UpdateTraining()
	{
		if ( IsBot ) return;
		if ( IsLocalPlayer )
		{
			_wasLocalTrainingClient = true;
			if ( !TrainingReady && _timeSinceTrainingProfileSent >= 1f )
			{
				InitializeTrainingOnOwner();
			}
			else if ( TrainingReady && _timeSinceTrainingProfileSent >= 1f
				&& (SoldierTraining.GetXP( SoldierSkill.Endurance ) != EnduranceXP
					|| SoldierTraining.GetXP( SoldierSkill.Handling ) != HandlingXP) )
			{
				// Reconnects reuse their host Client. Ask for its snapshot instead of importing stale cookies again.
				_timeSinceTrainingProfileSent = 0f;
				if ( Networking.IsHost ) ReceiveTrainingProgress( EnduranceXP, HandlingXP, 0 );
				else RequestTrainingSnapshot();
			}
			SoldierTraining.FlushIfDue();
		}

		if ( !Networking.IsHost || _timeSinceTrainingSample < 0.25f ) return;
		var elapsed = (float)_timeSinceTrainingSample;
		_timeSinceTrainingSample = 0f;
		SampleEndurance( elapsed );
		SampleWeaponPractice();
	}

	private void InitializeTrainingOnOwner()
	{
		if ( !IsLocalPlayer ) return;
		_wasLocalTrainingClient = true;
		_timeSinceTrainingProfileSent = 0f;
		var endurance = SoldierTraining.GetXP( SoldierSkill.Endurance );
		var handling = SoldierTraining.GetXP( SoldierSkill.Handling );
		if ( Networking.IsHost ) LoadTrainingProfile( endurance, handling );
		else RequestTrainingProfile( endurance, handling );
	}

	[Rpc.Host]
	private void RequestTrainingProfile( int enduranceXP, int handlingXP )
	{
		if ( Rpc.Caller != Connection ) return;
		LoadTrainingProfile( enduranceXP, handlingXP );
	}

	[Rpc.Host]
	private void RequestTrainingSnapshot()
	{
		if ( Rpc.Caller != Connection || !TrainingReady || IsBot ) return;
		ReceiveTrainingProgress( EnduranceXP, HandlingXP, 0 );
	}

	private void LoadTrainingProfile( int enduranceXP, int handlingXP )
	{
		if ( !Networking.IsHost || IsBot || (TrainingReady && _trainingProfileConnection == Connection) ) return;
		// As with the existing rank/weapon cookies, this is a local profile, not an anti-cheat backend.
		// Only its owner can import it, once per connection. Reused Clients keep the higher progress from either side.
		EnduranceXP = Math.Max( EnduranceXP, SoldierTrainingRules.ClampXP( enduranceXP ) );
		HandlingXP = Math.Max( HandlingXP, SoldierTrainingRules.ClampXP( handlingXP ) );
		_trainingProfileConnection = Connection;
		_trainingPawn = null;
		_trainingWasRunning = false;
		TrainingReady = true;
		ReceiveTrainingProgress( EnduranceXP, HandlingXP, 0 );
	}

	private bool CanEarnTraining()
	{
		var pawn = PlayerPawn;
		var mode = GameMode.Instance;
		return Networking.IsHost && TrainingReady && !IsBot && IsConnected
			&& pawn.IsValid() && pawn.Client == this && Pawn == pawn
			&& pawn.HealthComponent is { State: LifeState.Alive, IsGodMode: false }
			&& !pawn.IsFrozen && !pawn.IsNoclipping && !pawn.IsPilotingDrone
			&& pawn.TimeSinceLastRespawn > 1f && pawn.InPlayArea
			&& ZombiesPlayerState.For( pawn ) is not { IsDowned: true }
			&& !DevCommands.NoDamage && DevCommands.ForceMove == 0f
			&& !Facepunch.Gunsmith.FiringRangeSystem.IsActive
			&& mode.IsValid() && mode.Scene == Scene && mode.Get<PlayerStatsRule>() is { Active: true };
	}

	private void SampleEndurance( float elapsed )
	{
		var pawn = PlayerPawn;
		if ( !pawn.IsValid() )
		{
			_trainingPawn = null;
			_trainingWasRunning = false;
			return;
		}

		var controller = pawn.CharacterController;
		var velocity = pawn.IsLocallyControlled && controller.IsValid() ? controller.Velocity : pawn.SyncedVelocity;
		var grounded = pawn.IsLocallyControlled && controller.IsValid() ? controller.IsOnGround : pawn.SyncedIsGrounded;
		var running = CanEarnTraining() && grounded && pawn.IsSprinting && !pawn.IsProne && !pawn.IsCrouching
			&& !pawn.IsSliding && !pawn.IsMantling && !pawn.IsPipeClimbing && !pawn.IsFallKnockedDown;
		var distance = (pawn.WorldPosition - _trainingPosition).WithZ( 0f ).Length;
		var metres = SoldierTrainingRules.RunningMetres( distance, elapsed, velocity.WithZ( 0f ).Length,
			pawn.GetWishSpeed(), running && _trainingWasRunning && _trainingPawn == pawn );
		_trainingPawn = pawn;
		_trainingPosition = pawn.WorldPosition;
		_trainingWasRunning = running;

		_trainingMetres += metres;
		var award = (int)(_trainingMetres / SoldierTrainingRules.MetresPerEnduranceXP);
		if ( award <= 0 ) return;
		_trainingMetres -= award * SoldierTrainingRules.MetresPerEnduranceXP;
		AwardTraining( SoldierSkill.Endurance, award );
	}

	private bool IsTrainingWeapon( Equipment equipment )
		=> equipment.IsValid() && equipment.Owner == PlayerPawn && PlayerPawn.CurrentEquipment == equipment
			&& equipment.IsDeployed && equipment.Resource?.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary
			&& equipment.GetComponentInChildren<Shootable>().IsValid();

	/// <summary>Use the existing replicated discharge state; there is no client XP or practice-report RPC.</summary>
	private void SampleWeaponPractice()
	{
		if ( !CanEarnTraining() || !IsTrainingWeapon( PlayerPawn.CurrentEquipment )
			|| _timeSinceTrainingShot < SoldierTrainingRules.ShotAwardInterval ) return;
		var shotAge = MathF.Min( PlayerPawn.TimeSinceUnsuppressedShot, PlayerPawn.TimeSinceSuppressedShot );
		if ( shotAge < 0f || shotAge > 0.4f ) return;
		_timeSinceTrainingShot = 0f;
		AwardTraining( SoldierSkill.Handling, 1 );
	}

	internal void RecordTrainingHit( DamageInfo info )
	{
		if ( !CanEarnTraining() || info is null || info.Damage <= 0f
			|| GameUtils.GetPlayerFromComponent( info.Attacker ) != PlayerPawn
			|| !IsTrainingWeapon( info.Inflictor as Equipment )
			|| info.WasExplosion || info.WasFallDamage
			|| (info.Flags & (DamageFlags.Melee | DamageFlags.Burn | DamageFlags.Zone)) != 0 ) return;

		var victim = GameUtils.GetPlayerFromComponent( info.Victim );
		var bot = GameUtils.GetLightweightBotFromComponent( info.Victim );
		if ( victim == PlayerPawn || (!victim.IsValid() && !bot.IsValid()) ) return;
		var health = victim.IsValid() ? victim.HealthComponent : bot.HealthComponent;
		if ( health is not { State: LifeState.Alive, IsGodMode: false } ) return;
		var victimTeam = GameUtils.GetTeamFromComponent( info.Victim );
		if ( Team != Team.Unassigned && victimTeam == Team ) return;
		AwardTrainingHit( info.Hitbox.HasFlag( HitboxTags.Head ) );
	}

	internal void RecordZombieTrainingHit( Equipment equipment, bool headshot )
	{
		if ( CanEarnTraining() && IsTrainingWeapon( equipment ) ) AwardTrainingHit( headshot );
	}

	private void AwardTrainingHit( bool headshot )
	{
		// One reward for grouped shotgun pellets and a bounded rate for fast-firing weapons.
		if ( _timeSinceTrainingHit < SoldierTrainingRules.HitAwardInterval ) return;
		_timeSinceTrainingHit = 0f;
		AwardTraining( SoldierSkill.Handling, headshot ? 3 : 2 );
	}

	private void AwardTraining( SoldierSkill skill, int amount )
	{
		if ( !Networking.IsHost || !TrainingReady || IsBot || amount <= 0 ) return;
		var before = GetTrainingXP( skill );
		var after = SoldierTrainingRules.AddXP( before, amount );
		if ( before == after ) return;
		if ( skill == SoldierSkill.Endurance ) EnduranceXP = after;
		else HandlingXP = after;
		ReceiveTrainingProgress( EnduranceXP, HandlingXP, after - before );
	}

	[Rpc.Owner( NetFlags.HostOnly )]
	private void ReceiveTrainingProgress( int enduranceXP, int handlingXP, int careerXP )
	{
		if ( !IsLocalPlayer ) return;
		_wasLocalTrainingClient = true;
		SoldierTraining.Receive( enduranceXP, handlingXP, careerXP > 0 );
		// Practice contributes to the player's existing rank as well as the skill actually used.
		Progression.AddXP( Math.Clamp( careerXP, 0, 10 ) );
	}

	protected override void OnDisabled()
	{
		if ( _wasLocalTrainingClient || IsLocalPlayer ) SoldierTraining.Flush();
		base.OnDisabled();
	}

	protected override void OnDestroy()
	{
		if ( _wasLocalTrainingClient || IsLocalPlayer ) SoldierTraining.Flush();
		base.OnDestroy();
	}
}
