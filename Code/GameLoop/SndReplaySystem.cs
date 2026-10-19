using Sandbox.Events;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

/// <summary>S&D's private death replays and host-controlled round highlight intermission.</summary>
public sealed class SndReplaySystem : Component,
	IGameEventHandler<KillEvent>, IGameEventHandler<RoundCounterIncrementedEvent>,
	IGameEventHandler<RoundCounterResetEvent>, IGameEventHandler<PlayerSpawnedEvent>
{
	public const float KillcamSeconds = 5f;
	public const float BestPlaySeconds = SndReplayScoring.WindowSeconds + 0.35f;
	const float CaptureDelay = 0.45f;
	const float PresentationDelay = 0.8f;

	public static SndReplaySystem Current => GameMode.Instance.IsValid()
		? GameMode.Instance.GetComponent<SndReplaySystem>() : null;
	public static bool IsShowingReplay => Current is { Active: true, IsVisible: true };
	public static bool IsHoldingRound => Current is { Active: true, HoldingRound: true };
	public bool IsSupported => GetComponent<GameMode>()?.Ident == "defuse";
	public bool IsVisible => IsSupported && (HoldingRound || _playback is not null || _personalPending);

	[Sync( SyncFlags.FromHost )] public bool HoldingRound { get; private set; }
	[Sync( SyncFlags.FromHost )] public int ReplayId { get; private set; }
	[Sync( SyncFlags.FromHost )] public int HighlightId { get; private set; }
	[Sync( SyncFlags.FromHost )] public string HighlightName { get; private set; } = "";
	[Sync( SyncFlags.FromHost )] public int HighlightKills { get; private set; }
	[Sync( SyncFlags.FromHost )] public float StartsAt { get; private set; }
	[Sync( SyncFlags.FromHost )] public float EndsAt { get; private set; }
	[Sync( SyncFlags.FromHost )] public int VotesRequired { get; private set; } = 1;
	[Sync( SyncFlags.FromHost )] public NetList<Guid> SkipVoters { get; private set; } = new();
	// The continuation survives host migration, including the match-winning Post Game redirect.
	[Sync( SyncFlags.FromHost )] public StateComponent ResumeState { get; private set; }
	[Sync( SyncFlags.FromHost )] public StateComponent HeldState { get; private set; }
	[Sync( SyncFlags.FromHost )] public float ResumeDelay { get; private set; }

	public string PlayerName => HoldingRound ? HighlightName : _personalName;
	public int VotesCast => SkipVoters?.Count ?? 0;
	public bool HasVoted => Connection.Local is { } local && SkipVoters.Contains( local.Id );
	public bool CanVote => HoldingRound && Connection.Local is { } local && EligibleConnections().Contains( local.Id );
	public bool IsPreparing => _playback is null;
	public float SecondsLeft => HoldingRound ? MathF.Max( 0f, EndsAt - Time.Now )
		: _playback is null ? KillcamSeconds : MathF.Max( 0f, _personalDuration - (RealTime.Now - _personalStarted) );

	readonly SndReplayScoring _scoring = new();
	readonly SndReplayVotes _votes = new();
	readonly List<KillRequest> _pending = new();
	readonly Dictionary<PlayerPawn, bool> _frozen = new();
	readonly HashSet<Guid> _seenVictims = new();
	int _nextKillId;
	int _bestId;
	int _bestScore;
	int _bestKills;
	string _bestName;
	int _wantedClipId;
	int _bestClipId;
	int _clearedThrough;
	int _votingReplay;
	bool _roundEnded;
	SndReplayClip _bestClip;
	SndReplayPlayback _playback;
	int _playingSharedId;
	bool _personalPending;
	string _personalName = "";
	float _personalStarted;
	float _personalDuration;

	sealed record KillRequest( int Id, Guid Shooter, Guid VictimConnection, string Name, float At );

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent ev )
	{
		if ( !Networking.IsHost || !IsSupported || _roundEnded || GameUtils.IsCombatFrozen ) return;
		var damage = ev.DamageInfo;
		var attacker = SoldierObject( damage.Attacker );
		var victim = SoldierObject( damage.Victim );
		if ( !attacker.IsValid() || !victim.IsValid() || attacker == victim || !_seenVictims.Add( victim.Id ) ) return;

		var victimPlayer = GameUtils.GetPlayerFromComponent( damage.Victim );
		var victimConnection = victimPlayer?.Client?.Connection?.Id ?? Guid.Empty;
		var name = GameUtils.GetDescription( damage.Attacker )?.DisplayName ?? "Unknown";
		var id = ++_nextKillId;
		var attackerTeam = GameUtils.GetTeamFromComponent( damage.Attacker );
		var victimTeam = GameUtils.GetTeamFromComponent( damage.Victim );
		var best = false;
		if ( attackerTeam != Team.Unassigned && victimTeam != Team.Unassigned && attackerTeam != victimTeam )
		{
			var score = _scoring.Record( attacker.Id, Time.Now, damage.Hitbox.HasFlag( HitboxTags.Head ),
				attacker.WorldPosition.Distance( victim.WorldPosition ) );
			if ( score.Value > _bestScore )
			{
				_bestScore = score.Value;
				_bestId = id;
				_bestKills = score.Kills;
				_bestName = name;
				best = true;
			}
		}

		// Metadata is latched before OnKill removes the inventory and detaches the body. Only the host selects highlights.
		QueueKill( id, attacker.Id, victimConnection, name, Time.Now, best );
	}

	static GameObject SoldierObject( Component component )
	{
		var player = GameUtils.GetPlayerFromComponent( component );
		if ( player.IsValid() ) return player.GameObject;
		return GameUtils.GetLightweightBotFromComponent( component )?.GameObject;
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	void QueueKill( int id, Guid shooter, Guid victimConnection, string name, float at, bool best )
	{
		if ( !IsSupported || id <= _clearedThrough ) return;
		if ( best ) _wantedClipId = id;
		if ( Application.IsHeadless ) return;
		var personal = Connection.Local is { } local && victimConnection == local.Id;
		if ( !best && !personal ) return;
		if ( _pending.Any( x => x.Id == id ) ) return;
		_pending.Add( new( id, shooter, victimConnection, name, at ) );
		if ( personal )
		{
			_personalPending = true;
			_personalName = name;
		}
	}

	/// <summary>Called after victory scoring has dispatched its final-match redirect.</summary>
	public void OnRoundWon()
	{
		if ( !Networking.IsHost || !IsSupported || _roundEnded ) return;
		_roundEnded = true;
		var machine = GetComponent<GameMode>()?.StateMachine;
		if ( _bestId == 0 || !machine.IsValid() || !machine.NextState.IsValid() ) return;

		ResumeState = machine.NextState;
		ResumeDelay = MathF.Max( 0f, machine.NextStateTime - Time.Now );
		HeldState = machine.CurrentState;
		machine.ClearTransition();
		ReplayId++;
		HighlightId = _bestId;
		HighlightName = _bestName;
		HighlightKills = _bestKills;
		StartsAt = Time.Now + PresentationDelay;
		EndsAt = StartsAt + BestPlaySeconds;
		HoldingRound = true;
		SkipVoters.Clear();
		_votes.Begin( ReplayId, EligibleConnections() );
		_votingReplay = ReplayId;
		VotesRequired = _votes.Required;
		foreach ( var player in GameUtils.PlayerPawns ) Freeze( player );
	}

	IEnumerable<Guid> EligibleConnections() => Scene.GetAllComponents<Client>()
		.Where( x => x.IsValid() && !x.IsBot && x.IsConnected && x.Team != Team.Unassigned && x.Connection is not null )
		.Select( x => x.Connection.Id ).Distinct();

	void Freeze( PlayerPawn player )
	{
		if ( !player.IsValid() ) return;
		_frozen.TryAdd( player, player.IsFrozen );
		player.IsFrozen = true;
	}

	void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent ev )
	{
		if ( Networking.IsHost && HoldingRound ) Freeze( ev.Player );
	}

	public void Skip()
	{
		if ( HoldingRound )
		{
			if ( CanVote && !HasVoted ) VoteSkip( ReplayId );
		}
		else if ( IsVisible )
		{
			_personalPending = false;
			// Keep a pending best-play snapshot, but no longer start its personal killcam.
			for ( var i = 0; i < _pending.Count; i++ ) _pending[i] = _pending[i] with { VictimConnection = Guid.Empty };
			StopPlayback( true );
		}
	}

	[Rpc.Host]
	void VoteSkip( int replayId )
	{
		if ( !Networking.IsHost || !HoldingRound || replayId != ReplayId || Rpc.Caller is not { } caller ) return;
		RefreshVotes();
		if ( _votes.TryVote( replayId, caller.Id ) ) SkipVoters.Add( caller.Id );
		if ( _votes.HasMajority ) FinishShared();
	}

	void RefreshVotes()
	{
		var eligible = EligibleConnections().ToHashSet();
		if ( _votingReplay != ReplayId )
		{
			_votes.Begin( ReplayId, eligible );
			foreach ( var voter in SkipVoters ) _votes.TryVote( ReplayId, voter );
			_votingReplay = ReplayId;
		}
		_votes.Refresh( eligible );
		for ( var i = SkipVoters.Count - 1; i >= 0; i-- )
			if ( !eligible.Contains( SkipVoters[i] ) ) SkipVoters.RemoveAt( i );
		VotesRequired = _votes.Required;
	}

	protected override void OnUpdate()
	{
		if ( !IsSupported ) return;
		if ( Networking.IsHost && HoldingRound )
		{
			RefreshVotes();
			if ( Time.Now >= EndsAt || _votes.HasMajority || _votes.EligibleCount == 0 ) FinishShared();
		}
		if ( Application.IsHeadless ) return;
		CapturePending();

		if ( HoldingRound )
		{
			_personalPending = false;
			if ( _playback is not null && _playingSharedId != ReplayId ) StopPlayback( false );
			if ( _playback is null && _bestClipId == HighlightId && _bestClip is not null && Time.Now >= StartsAt && Time.Now < EndsAt )
				StartPlayback( _bestClip, true );
		}
		else if ( _playingSharedId != 0 ) StopPlayback( true );
		else if ( _playback is not null && (RealTime.Now - _personalStarted >= _personalDuration
			|| (Client.Local?.PlayerPawn?.HealthComponent?.State == LifeState.Alive)) ) StopPlayback( true );

		if ( IsVisible && !Input.Suppressed && !GameUtils.IsInteractiveMouseUiOpen() && Input.Pressed( "Jump" ) ) Skip();
	}

	void CapturePending()
	{
		var recorder = GetComponent<MatchRecorder>();
		for ( var i = _pending.Count - 1; i >= 0; i-- )
		{
			var request = _pending[i];
			if ( Time.Now < request.At + CaptureDelay ) continue;
			_pending.RemoveAt( i );
			var best = request.Id == _wantedClipId;
			var personal = request.VictimConnection != Guid.Empty && request.VictimConnection == Connection.Local?.Id;
			if ( !best && !personal ) continue;
			SndReplayClip clip = null;
			try { clip = recorder?.CaptureReplay( request.Shooter, request.At, best ? BestPlaySeconds : KillcamSeconds ); }
			catch ( Exception e ) { Log.Warning( $"S&D: couldn't prepare a replay: {e.Message}" ); }
			if ( best ) { _bestClip = clip; _bestClipId = request.Id; }
			if ( personal )
			{
				_personalPending = false;
				if ( !HoldingRound && Client.Local?.PlayerPawn?.HealthComponent?.State == LifeState.Dead && clip is not null )
				{
					_personalName = request.Name;
					StartPlayback( clip with { Start = MathF.Max( clip.Start, clip.End - KillcamSeconds ) }, false );
				}
			}
		}
	}

	void StartPlayback( SndReplayClip clip, bool shared )
	{
		StopPlayback( false );
		try
		{
			_playback = new SndReplayPlayback( Scene, clip );
			_playingSharedId = shared ? ReplayId : 0;
			_personalStarted = RealTime.Now;
			_personalDuration = clip.Duration;
		}
		catch ( Exception e )
		{
			Log.Warning( $"S&D: couldn't show the replay: {e.Message}" );
			StopPlayback( false );
			if ( shared ) _bestClip = null; // A bad local clip must not retry expensive setup every frame.
		}
	}

	protected override void OnPreRender()
	{
		if ( _playback is null ) return;
		try { _playback.Update( _playingSharedId != 0 ? MathF.Max( 0f, Time.Now - StartsAt ) : RealTime.Now - _personalStarted ); }
		catch ( Exception e )
		{
			Log.Warning( $"S&D: replay playback stopped: {e.Message}" );
			_bestClip = null;
			StopPlayback( true );
		}
	}

	void FinishShared()
	{
		if ( !Networking.IsHost || !HoldingRound ) return;
		var next = ResumeState;
		var held = HeldState;
		var delay = ResumeDelay;
		HoldingRound = false;
		ResumeState = null;
		HeldState = null;
		RestoreFrozen();
		var machine = GetComponent<GameMode>()?.StateMachine;
		if ( machine.IsValid() && machine.CurrentState == held && next.IsValid() ) machine.Transition( next, delay );
	}

	void RestoreFrozen()
	{
		var modeFreeze = GetComponent<GameMode>()?.Get<FreezePlayers>() is not null;
		foreach ( var pair in _frozen ) if ( pair.Key.IsValid() ) pair.Key.IsFrozen = pair.Value || modeFreeze;
		_frozen.Clear();
	}

	void StopPlayback( bool finishDeathcam )
	{
		_playback?.Dispose();
		_playback = null;
		_playingSharedId = 0;
		if ( finishDeathcam && Client.Local is { IsValid: true } local && local.PlayerPawn is { IsValid: true } pawn
			&& pawn.IsLocallyControlled && pawn.HealthComponent?.State == LifeState.Dead ) pawn.GameObject.Destroy();
	}

	void IGameEventHandler<RoundCounterIncrementedEvent>.OnGameEvent( RoundCounterIncrementedEvent ev ) => ResetRound();
	void IGameEventHandler<RoundCounterResetEvent>.OnGameEvent( RoundCounterResetEvent ev ) => ResetRound();
	void ResetRound()
	{
		if ( !Networking.IsHost || !IsSupported ) return;
		if ( HoldingRound ) FinishShared();
		_roundEnded = false;
		_bestId = _bestScore = _bestKills = 0;
		_bestName = null;
		_scoring.Reset();
		_seenVictims.Clear();
		ClearRoundClips( _nextKillId );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	void ClearRoundClips( int through )
	{
		_clearedThrough = Math.Max( _clearedThrough, through );
		_pending.Clear();
		_wantedClipId = _bestClipId = 0;
		_bestClip = null;
		_personalPending = false;
		StopPlayback( false );
		GetComponent<MatchRecorder>()?.ResetReplayRound();
	}

	protected override void OnDisabled()
	{
		StopPlayback( false );
		_personalPending = false;
		_pending.Clear();
		_bestClip = null;
		if ( Networking.IsHost ) FinishShared();
	}
}
