using Sandbox.Diagnostics;
using Sandbox.MovieMaker;
using Sandbox.MovieMaker.Compiled;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Facepunch;

/// <summary>
/// Records the match for the Theater (<see cref="TheaterController"/>), on every machine that plays it, so each player
/// keeps their own replays (<see cref="TheaterReplays"/>).
/// <para>
/// Only the soldiers go in the recording: every player's and bot's body, clothing and guns, from spawn until the body is
/// removed. The map isn't recorded: the sidecar names its MapInstance and playback loads it again. A living body
/// records its anim graph's inputs, which playback runs through the same anim graph at full frame rate, and a dead one
/// its ragdoll's key bones. Captures happen <see cref="SampleRate"/> times a second at the end of the frame, once its
/// animation and physics are done, and the file is written on a worker thread after the match, a life at a time
/// (<see cref="TheaterReplays.WriteClip"/>). A soldier's first capture sets up its tracks, the costly part, so soldiers
/// who spawn together are spread over a few captures (<see cref="AdmitWaiting"/>).
/// </para>
/// <para>
/// What each soldier does with their guns goes in an actions file beside it (<see cref="TheaterReplays.Actions"/>), for
/// the first-person view: what they hold, from their equipment, and whether they're aiming, sprinting, reloading or out
/// of ammo, from state every machine is sent, at each capture; and their shots, from the shot effects every machine plays
/// (<see cref="NoteShot"/>). None of it is in the recording: the first-person gun isn't a soldier's renderer, and the
/// anim graph's attack and reload triggers are spent by the end of the frame.
/// </para>
/// </summary>
public sealed partial class MatchRecorder : Component, Component.ISceneStage
{
	/// <summary> Settings → Game → Theater Recording, the player's own and on by default. </summary>
	public static bool RecordingOff => GameSettingsSystem.Current is { } settings && !settings.TheaterRecording;

	/// <summary> Captures a second. Playback blends positions and bones between them. </summary>
	public const int SampleRate = 15;

	/// <summary> Shorter recordings (a match left straight away) aren't saved. </summary>
	const float MinimumSeconds = 20f;

	const float MaximumSeconds = 30f * 60f;

		/// <summary> S&D's in-memory history, even when saving Theater matches is disabled. </summary>
		const float ReplayBufferSeconds = 8f;
		const float ReplayAfterKill = 0.35f;

	/// <summary> How long recording carries on once the match is over. </summary>
	const float EndDelay = 3f;

	/// <summary> How often a dead body is checked for having come to rest. </summary>
	const float SettleInterval = 0.5f;

	/// <summary> A body whose key bones moved less than this between checks has come to rest. </summary>
	const float SettleDistance = 0.05f;

	/// <summary> How often a body's anim graph is checked for parameters the game has started setting. </summary>
	const float ParameterScanInterval = 2f;

	/// <summary>
	/// How long a capture can take before soldiers who've just spawned wait for the next one (one is always taken).
	/// Setting up a soldier's tracks is the costly part of recording, and a round's respawn brings ten or more at once.
	/// </summary>
	const double AdmitBudgetMicroseconds = 3000;

	/// <summary> Modes that aren't recorded: battle royale's map and field are too big, and zombies aren't soldiers. </summary>
	static readonly string[] SkippedModes = { "battle_royale", "zombies" };

	/// <summary> The recorder recording now, which the game's shots reach through <see cref="NoteShot"/>. </summary>
	static MatchRecorder _active;

	MovieRecorder _recorder;
		MovieRecorder _replayRecorder;
		RendererCapturer _rendererCapturer;
		SkinnedCapturer _skinnedCapturer;
	TheaterReplays.Info _info;
	TheaterReplays.Actions _actions;

		/// <summary> Only the current round's captured lives; the full Theater history stays separate. </summary>
		readonly Dictionary<string, Soldier> _replaySoldiers = new();
		float _replayRoundStart;
		float _nextReplayTrim;

	/// <summary> Each build code's index in the actions' <see cref="TheaterReplays.Actions.Builds"/>. </summary>
	readonly Dictionary<string, int> _builds = new();

	/// <summary>
	/// The build index of each gun noted this capture: a respawn brings many soldiers holding the same guns, and a build
	/// code reads dozens of cookies. Only for the capture, as nothing announces a build changing (a weapon level, a camo).
	/// </summary>
	readonly Dictionary<EquipmentResource, int> _buildsThisCapture = new();

	double _startTime;
	double _stopTime = -1;
	int _frame = -1;
	bool _restartPass;
	bool _finished;

	/// <summary> The soldier whose first capture this is (see <see cref="AdmitWaiting"/>), else null. </summary>
	Soldier _admitting;

	int _captures;
	double _captureMicroseconds;
	double _slowestCapture;

	/// <summary> The soldiers being recorded, by the object whose renderers are captured. </summary>
	readonly Dictionary<GameObject, Soldier> _soldiers = new();

	/// <summary> The same soldiers, by their body's renderer, for <see cref="SkinnedCapturer"/>. </summary>
	readonly Dictionary<SkinnedModelRenderer, Soldier> _bodies = new();

	/// <summary> How many lives each name has had, for its tracks' names. </summary>
	readonly Dictionary<string, int> _lives = new();

	/// <summary> Soldiers found but not yet recorded, as <see cref="AdmitBudgetMicroseconds"/> allows, by their scope too. </summary>
	readonly List<Soldier> _waiting = new();
	readonly HashSet<GameObject> _waitingScopes = new();

	/// <summary> The soldiers whose blocks start again this capture (see <see cref="Restart"/>). </summary>
	readonly List<Soldier> _restarting = new();

	readonly Dictionary<Model, KeyBones> _keyBones = new();

	/// <summary> Each anim graph's parameters of a type playback can set, found once: finding them throws for the rest. </summary>
	readonly Dictionary<AnimationGraph, string[]> _graphParameters = new();

	readonly List<GameObject> _gone = new();
	readonly List<LightweightCombatBot> _bots = new();
	readonly List<PlayerBody> _playerBodies = new();

		public bool IsRecording => !_finished && (_recorder is not null || _replayRecorder is not null);

	sealed class Soldier
	{
		/// <summary> The object named as the soldier's track: the bot, or the player's pawn. </summary>
		public GameObject Root;

		/// <summary> The object whose renderers are captured: the bot, or the player's body. </summary>
		public GameObject Scope;

		public LightweightCombatBot Bot;
		public PlayerBody PlayerBody;
		public SkinnedModelRenderer Body;
		public TheaterReplays.Soldier Entry;

		/// <summary> What it's found as, for its <see cref="Entry"/>: "Bot" or "Player", its name, team and Steam ID. </summary>
		public string Kind;
		public string Name;
		public Team Team;
		public ulong SteamId;

		public bool Named;
			public bool ReplayNamed;
		public bool Restart;
		public GameObject LastParent;

		public bool Settled;
		public TimeUntil NextSettleCheck;

		/// <summary> A dead body's key bones at this check and the last, swapped at each check. </summary>
		public Vector3[] Pose;
		public Vector3[] LastPose;
		public bool HasLastPose;

		public readonly List<string> Parameters = new();
		public readonly HashSet<string> KnownParameters = new( StringComparer.OrdinalIgnoreCase );
		public TimeUntil NextParameterScan;
		public bool ScannedParameters;

		public TheaterReplays.LifeActions Actions;

		/// <summary> A player's equipment in hand at the last capture, and its reloading and ammo. </summary>
		public Equipment Equipment;
		public Reloadable Reloadable;
		public WeaponAmmo Ammo;

		public SkinnedModelRenderer FindBody() => Bot.IsValid() ? Bot.Renderer : PlayerBody.IsValid() ? PlayerBody.Renderer : null;

		/// <summary>
		/// The object that leaves its parent when the soldier dies: a player's body (the scope) leaves the pawn, and a
		/// bot's body leaves the bot (LightweightCombatBot's OnKill).
		/// </summary>
		public GameObject Leaver => Bot.IsValid() && Body.IsValid() ? Body.GameObject : Scope;

		public bool IsDead()
		{
			if ( Body.IsValid() && !Body.UseAnimGraph )
				return true;

			if ( Bot.IsValid() )
				return !Bot.IsAlive || Scope.Tags.Has( "dead" );

			// A player's body is left behind as a ragdoll when the pawn dies.
			return PlayerBody.IsValid() && (PlayerBody.IsRagdoll || Scope.Parent != Root);
		}
	}

	/// <summary> A ragdoll's bones: those with physics bodies and their parents, the rest follow them. </summary>
	sealed record KeyBones( string[] Names, int[] Indices );

	protected override void OnStart()
	{
			var theater = CanRecord( out var reason );
			var mode = GetComponent<GameMode>();
			var replay = mode?.Ident == "defuse" && !Application.IsHeadless;
			if ( !theater && !replay )
		{
			Log.Info( $"Theater: not recording this match ({reason})." );
			return;
		}

			_recorder = theater ? new MovieRecorder( Scene, CaptureOptions() ) : null;
			_replayRecorder = replay ? new MovieRecorder( Scene, CaptureOptions( MovieTime.FromSeconds( ReplayBufferSeconds ) ) ) : null;
		_startTime = Time.NowDouble;

		var sceneFile = Scene.Source as SceneFile;

			_info = theater ? new TheaterReplays.Info
		{
			Version = TheaterReplays.CurrentVersion,
			Maps = Scene.GetAllComponents<MapInstance>()
				.Where( x => !string.IsNullOrWhiteSpace( x.MapName ) )
				.Select( x => new TheaterReplays.MapEntry
				{
					Name = x.MapName,
					NoOrigin = x.NoOrigin,
					Position = x.WorldPosition,
					Rotation = x.WorldRotation,
					Scale = x.WorldScale
				} )
				.ToList(),
			MapTitle = sceneFile?.GetMetadata( "Title", null ) ?? Scene.Name,
			Mode = mode?.Title,
			ModeIdent = mode?.Ident,
			RecordedBy = (ulong)Game.SteamId
			} : null;

		_actions = new TheaterReplays.Actions();
		_active = this;

			if ( theater )
				Log.Info( $"Theater: recording {_info.MapTitle} ({_info.Mode})." );
			else
				Log.Info( "S&D: keeping an eight-second replay buffer; Theater saving is off." );
	}

		MovieRecorderOptions CaptureOptions( MovieTime? bufferDuration = null ) => new MovieRecorderOptions( SampleRate, bufferDuration )
			.WithComponentCapturer( _rendererCapturer ??= new RendererCapturer( this ) )
			.WithComponentCapturer( _skinnedCapturer ??= new SkinnedCapturer( this ) )
			.WithCaptureAction( CaptureSoldiers );

	bool CanRecord( out string reason )
	{
		reason = null;

		if ( RecordingOff )
			reason = "Theater Recording is off in the settings";
		else if ( Application.IsHeadless )
			reason = "dedicated server";
		else if ( GetComponent<GameMode>() is { } mode && SkippedModes.Contains( mode.Ident ) )
			reason = $"{mode.Ident} isn't recorded";
		else if ( !Scene.GetAllComponents<MapInstance>().Any( x => !string.IsNullOrWhiteSpace( x.MapName ) ) )
			reason = "the scene has no map to load for playback";

		return reason is null;
	}

	protected override void OnDestroy()
	{
		Finish();
	}

	void ISceneStage.End()
	{
			if ( !IsRecording )
			return;

		var now = Time.NowDouble;
		var elapsed = now - _startTime;

		if ( _stopTime < 0 && (Facepunch.UI.EndOfMatchScreen.IsAnyVisible || MapVoteSystem.Instance.IsValid()) )
			_stopTime = now + EndDelay;

			if ( _stopTime >= 0 && now >= _stopTime )
		{
			Finish();
			return;
		}

			// Theater's file limit and preference must not turn off S&D's bounded in-match replays.
			if ( _recorder is not null && (elapsed >= MaximumSeconds || RecordingOff) )
			{
				FinishTheaterRecording( save: !RecordingOff );
				if ( _replayRecorder is null )
				{
					Finish();
					return;
				}
			}

		// Scene time can step back on a client while it syncs with the host: wait for it.
		var frame = (int)(elapsed * SampleRate);
		if ( frame <= _frame )
			return;

		_frame = frame;

		var timer = FastTimer.StartNew();
		var time = frame / (float)SampleRate;

		_buildsThisCapture.Clear();
		RefreshSoldiers( time );

			var movieTime = MovieTime.FromFrames( frame, SampleRate );
			AdvanceAndCapture( _recorder, movieTime );
			AdvanceAndCapture( _replayRecorder, movieTime );

		// Soldiers whose blocks start again (see Restart) are left out of that capture and caught up a tick later: their
		// recorders then see a capture they missed, finish their blocks and start new ones at the same frame.
		if ( _restarting.Count > 0 )
		{
			_restartPass = true;
				AdvanceAndCapture( _recorder, movieTime + MovieTime.Epsilon );
				AdvanceAndCapture( _replayRecorder, movieTime + MovieTime.Epsilon );
			_restartPass = false;

			foreach ( var soldier in _restarting )
				soldier.Restart = false;

			_restarting.Clear();
		}

		if ( _waiting.Count > 0 )
			AdmitWaiting( time, timer );

			if ( _recorder is null && time >= _nextReplayTrim )
			{
				_nextReplayTrim = time + 1f;
				TrimReplayActions( MathF.Max( _replayRoundStart, time - ReplayBufferSeconds ) );
			}

		var micros = timer.ElapsedMicroSeconds;
		_captures++;
		_captureMicroseconds += micros;
		_slowestCapture = Math.Max( _slowestCapture, micros );
	}

		static void AdvanceAndCapture( MovieRecorder recorder, MovieTime time )
		{
			if ( recorder is null )
				return;

			recorder.Advance( time - recorder.Time );
			recorder.Capture();
		}

	/// <summary>
	/// Starts a soldier's blocks again at this frame. Blocks blend between their samples, so this goes where the values
	/// jump (a body moving into another parent's space), and where they stop changing (a body at rest), so the rest of
	/// its time is stored as constants.
	/// </summary>
	void Restart( Soldier soldier )
	{
		if ( soldier.Restart )
			return;

		soldier.Restart = true;
		_restarting.Add( soldier );
	}

	void RefreshSoldiers( float time )
	{
		_gone.Clear();

		foreach ( var scope in _soldiers.Keys )
		{
			if ( !scope.IsValid() )
				_gone.Add( scope );
		}

		foreach ( var scope in _gone )
		{
			var soldier = _soldiers[scope];
			soldier.Entry.Removed = time;

			if ( soldier.Body is not null )
				_bodies.Remove( soldier.Body );

			_soldiers.Remove( scope );
		}

		FindNewSoldiers();

		foreach ( var soldier in _soldiers.Values )
			UpdateSoldier( soldier, time );
	}

	/// <summary> Living bots and players' bodies that aren't recorded yet join <see cref="_waiting"/>. </summary>
	void FindNewSoldiers()
	{
		// The bots' shared list of the living, else a search of the scene.
		var bots = Scene.GetSystem<BotSystem>()?.AliveBots;
		if ( bots is null )
		{
			_bots.Clear();
			Scene.GetAll( _bots );
			bots = _bots;
		}

		foreach ( var bot in bots )
		{
			if ( !bot.IsValid() )
				continue;

			var go = bot.GameObject;
			if ( IsKnown( go ) || !bot.IsAlive || go.Tags.Has( "dead" ) )
				continue;

			Wait( new Soldier { Root = go, Scope = go, Bot = bot, Kind = "Bot", Name = bot.BotName, Team = bot.Team } );
		}

		_playerBodies.Clear();
		Scene.GetAll( _playerBodies );

		foreach ( var body in _playerBodies )
		{
			var go = body.GameObject;
			if ( IsKnown( go ) )
				continue;

			// Only bodies still on a living pawn: a ragdoll from before recording started isn't worth a track.
			var pawn = body.Player;
			if ( !pawn.IsValid() || !pawn.Client.IsValid() || go.Parent != pawn.GameObject || body.IsRagdoll )
				continue;

			var client = pawn.Client;
			var name = client.DisplayName;

			// A player bot's name is "BOT <name>": the Theater marks bots itself.
			if ( client.IsBot && name.StartsWith( "BOT " ) )
				name = name[4..];

			Wait( new Soldier
			{
				Root = pawn.GameObject,
				Scope = go,
				PlayerBody = body,
				Kind = client.IsBot ? "Bot" : "Player",
				Name = name,
				Team = pawn.Team,
				SteamId = client.IsBot ? 0 : client.SteamId
			} );
		}
	}

	bool IsKnown( GameObject scope ) => _soldiers.ContainsKey( scope ) || _waitingScopes.Contains( scope );

	void Wait( Soldier soldier )
	{
		_waiting.Add( soldier );
		_waitingScopes.Add( soldier.Scope );
	}

	/// <summary>
	/// Records soldiers who've just spawned, players first (playback starts on the recording player's own), one capture of
	/// their own each, for as long as this capture is within <see cref="AdmitBudgetMicroseconds"/>. The rest wait for the
	/// next capture, and spawn that much later in the replay.
	/// </summary>
	void AdmitWaiting( float time, FastTimer timer )
	{
		var admitted = 0;

		while ( _waiting.Count > 0 && (admitted == 0 || timer.ElapsedMicroSeconds < AdmitBudgetMicroseconds) )
		{
			var index = _waiting.FindIndex( x => x.Kind == "Player" );
			var soldier = _waiting[Math.Max( index, 0 )];

			_waiting.RemoveAt( Math.Max( index, 0 ) );
			_waitingScopes.Remove( soldier.Scope );

			// Gone or dead before its turn (rare: a few captures at most): its body may have left the objects its tracks
			// would be named by.
			if ( !soldier.Scope.IsValid() || !soldier.Root.IsValid() || soldier.IsDead() )
				continue;

			AddSoldier( soldier, time );
			UpdateSoldier( soldier, time );

			// Captures again at the same time: the soldiers already captured are skipped.
			_admitting = soldier;
				_recorder?.Capture();
				_replayRecorder?.Capture();
			_admitting = null;

			admitted++;
		}
	}

	void AddSoldier( Soldier soldier, float time )
	{
		var kind = soldier.Kind;
		var name = string.IsNullOrWhiteSpace( soldier.Name ) ? kind : soldier.Name;

		// "#n", not "(n)": the recorder treats "Name (2)" as another copy of "Name" and would reuse its track.
		var key = $"{kind}: {name}";
		var life = _lives.GetValueOrDefault( key ) + 1;
		_lives[key] = life;

		soldier.Entry = new TheaterReplays.Soldier
		{
			Track = $"{key} #{life}",
			Body = PathFrom( soldier.Root, soldier.FindBody()?.GameObject ),
			Name = name,
			Team = soldier.Team,
			Bot = kind == "Bot",
			SteamId = soldier.SteamId,
				ObjectId = soldier.Root.Id,
			Spawned = time
		};

		soldier.LastParent = soldier.Leaver.Parent;

		// A bot's sprint isn't sent to clients: playback works it out from its speed.
		soldier.Actions = new TheaterReplays.LifeActions { Sprinting = soldier.Bot.IsValid() ? null : new() };
		_actions.Lives[soldier.Entry.Track] = soldier.Actions;

		_soldiers[soldier.Scope] = soldier;
			_info?.Soldiers.Add( soldier.Entry );
	}

	/// <summary> The names of the objects from <paramref name="root"/> down to <paramref name="go"/>, which are its tracks' names. </summary>
	static string PathFrom( GameObject root, GameObject go )
	{
		var names = new List<string>();

		for ( ; go.IsValid() && go != root; go = go.Parent )
		{
			if ( go is Scene )
				return "";

			names.Add( go.Name );
		}

		names.Reverse();
		return string.Join( "/", names );
	}

	void UpdateSoldier( Soldier soldier, float time )
	{
		if ( !soldier.Body.IsValid() )
		{
			if ( soldier.Body is not null )
				_bodies.Remove( soldier.Body );

			soldier.Body = soldier.FindBody();

			if ( soldier.Body.IsValid() )
				_bodies[soldier.Body] = soldier;
		}

		if ( soldier.Entry.Died < 0f && soldier.IsDead() )
			soldier.Entry.Died = time;

		if ( soldier.Entry.Died < 0f )
			CaptureActions( soldier, time );

		// A player's body leaves the pawn when it dies, and a bot's the bot: its position jumps from its parent's space
		// to the world's.
		var parent = soldier.Leaver.Parent;
		if ( parent != soldier.LastParent )
		{
			soldier.LastParent = parent;

				if ( soldier.Named || soldier.ReplayNamed )
				Restart( soldier );
		}

		if ( soldier.Entry.Died >= 0f )
			CheckSettled( soldier );
	}

	/// <summary>
	/// A soldier fired, or swung a melee weapon. The game's shot effects call this, which every machine plays for every
	/// shot, so each recording has everyone's. <paramref name="soldier"/> is the bot, or the player's pawn.
	/// </summary>
	public static void NoteShot( GameObject soldier, bool suppressed = false )
	{
		if ( _active is { IsRecording: true } recorder && soldier.IsValid() )
			recorder.AddShot( soldier, suppressed );
	}

	void AddShot( GameObject root, bool suppressed )
	{
		foreach ( var soldier in _soldiers.Values )
		{
			if ( soldier.Root != root || soldier.Entry.Died >= 0f || soldier.Actions is not { } actions )
				continue;

			Append( actions.Shots, (float)(Time.NowDouble - _startTime) );

			if ( suppressed && actions.Held.Count > 0 )
				actions.Held[^1].Suppressed = true;

			return;
		}
	}

	/// <summary> What a living soldier has in their hands, and whether they're aiming, sprinting, reloading or out of ammo. </summary>
	void CaptureActions( Soldier soldier, float time )
	{
		if ( soldier.Actions is not { } actions )
			return;

		if ( soldier.Bot.IsValid() )
		{
			var bot = soldier.Bot;
			NoteHeld( soldier, bot.WeaponResource, null, time );
			Toggle( actions.Aiming, bot.IsAimingIn, time );
			Toggle( actions.Reloading, bot.IsReloading, time );
			return;
		}

		var pawn = soldier.PlayerBody.IsValid() ? soldier.PlayerBody.Player : null;
		if ( !pawn.IsValid() )
			return;

		var equipment = pawn.CurrentEquipment;
		if ( equipment != soldier.Equipment || actions.Held.Count == 0 )
		{
			soldier.Equipment = equipment;
			soldier.Reloadable = equipment.IsValid() ? equipment.GetComponentInChildren<Reloadable>() : null;
			soldier.Ammo = equipment.IsValid() ? equipment.GetComponentInChildren<WeaponAmmo>() : null;
			NoteHeld( soldier, equipment.IsValid() ? equipment.Resource : null, equipment, time );
		}

		Toggle( actions.Aiming, equipment.IsValid() && equipment.HasTag( "aiming" ), time );
		Toggle( actions.Sprinting, pawn.IsSprinting, time );
		Toggle( actions.Reloading, soldier.Reloadable.IsValid() && soldier.Reloadable.IsReloading, time );
		Toggle( actions.Empty, soldier.Ammo.IsValid() && !soldier.Ammo.HasAmmo, time );
	}

	/// <summary>
	/// A new thing in a soldier's hands: a player's equipment, each time it changes (so drawing the same gun again plays
	/// its deploy), or a bot's gun.
	/// </summary>
	void NoteHeld( Soldier soldier, EquipmentResource resource, Equipment equipment, float time )
	{
		var weapon = resource.IsValid() ? resource.ResourcePath : "";
		var held = soldier.Actions.Held;

		if ( equipment is null && held.Count > 0 && held[^1].Weapon == weapon )
			return;

		var at = MathF.Round( time, 2 );
		if ( held.Count > 0 && at < held[^1].At )
			at = held[^1].At;

		held.Add( new TheaterReplays.Held
		{
			At = at,
			Weapon = weapon,
			// The build the gun is drawn with here (Equipment.FitHolderBuild): this machine's saved one on its own player's
			// gun, the holder's shared one on anyone else's. A bot's gun has none.
			Build = !equipment.IsValid() || !equipment.ApplySavedAttachments || !resource.IsValid() ? -1
				: equipment.IsOwnBuild ? BuildIndex( resource ) : CodeIndex( equipment.HolderBuild )
		} );
	}

	/// <summary> A build code's place in the replay's list of builds, adding it the first time. -1 for none. </summary>
	int CodeIndex( string code )
	{
		if ( string.IsNullOrEmpty( code ) )
			return -1;

		if ( !_builds.TryGetValue( code, out var index ) )
		{
			index = _actions.Builds.Count;
			_actions.Builds.Add( code );
			_builds[code] = index;
		}

		return index;
	}

	int BuildIndex( EquipmentResource resource )
	{
		if ( _buildsThisCapture.TryGetValue( resource, out var index ) )
			return index;

		index = CodeIndex( Facepunch.Gunsmith.GunsmithLoadoutManager.ExportWeaponBuildCode( resource ) );
		_buildsThisCapture[resource] = index;
		return index;
	}

	/// <summary> Adds a time when a state starts or stops (<see cref="TheaterReplays.LifeActions"/>). </summary>
	static void Toggle( List<float> toggles, bool on, float time )
	{
		if ( toggles is not null && on != (toggles.Count % 2 == 1) )
			Append( toggles, time );
	}

	/// <summary> Adds a time to a list kept in order: scene time can step back on a client while it syncs with the host. </summary>
	static void Append( List<float> times, float time )
	{
		time = MathF.Round( time, 2 );
		if ( times.Count > 0 && time < times[^1] )
			time = times[^1];

		times.Add( time );
	}

	/// <summary> Restarts a dead body's blocks once it has come to rest, so the rest of its time is stored as constants. </summary>
	void CheckSettled( Soldier soldier )
	{
		if ( !soldier.NextSettleCheck )
			return;

		soldier.NextSettleCheck = SettleInterval;

		var body = soldier.Body;
		var bones = body.IsValid() && !body.UseAnimGraph ? GetKeyBones( body.Model ) : null;
		var sceneModel = body.IsValid() ? body.SceneModel : null;

		if ( bones is null || !sceneModel.IsValid() )
		{
			soldier.HasLastPose = false;
			return;
		}

		var count = bones.Indices.Length;
		if ( soldier.Pose is null || soldier.Pose.Length != count )
		{
			soldier.Pose = new Vector3[count];
			soldier.LastPose = new Vector3[count];
			soldier.HasLastPose = false;
		}

		var pose = soldier.Pose;
		for ( var i = 0; i < count; i++ )
			pose[i] = sceneModel.GetBoneWorldTransform( bones.Indices[i] ).Position;

		if ( soldier.HasLastPose )
		{
			var last = soldier.LastPose;
			var moved = 0f;
			for ( var i = 0; i < count; i++ )
				moved = MathF.Max( moved, last[i].Distance( pose[i] ) );

			if ( !soldier.Settled && moved <= SettleDistance )
			{
				soldier.Settled = true;
				Restart( soldier );
			}
			else if ( soldier.Settled && moved > SettleDistance )
			{
				soldier.Settled = false;
			}
		}

		soldier.Pose = soldier.LastPose;
		soldier.LastPose = pose;
		soldier.HasLastPose = true;
	}

	KeyBones GetKeyBones( Model model )
	{
		if ( model is null || model.IsError )
			return null;

		if ( _keyBones.TryGetValue( model, out var keyBones ) )
			return keyBones;

		var bones = new List<BoneCollection.Bone>();

		if ( model.Physics?.Parts is { Count: > 0 } parts )
		{
			foreach ( var part in parts )
			{
				// Walk up to the root: every bone above one with a body moves it.
				for ( var bone = model.Bones.GetBone( part.BoneName ); bone is not null && !bones.Contains( bone ); bone = bone.Parent )
					bones.Add( bone );
			}
		}
		else
		{
			bones.AddRange( model.Bones.AllBones );
		}

		bones.Sort( ( a, b ) => a.Index.CompareTo( b.Index ) );
		keyBones = new KeyBones( bones.Select( x => x.Name ).ToArray(), bones.Select( x => x.Index ).ToArray() );
		_keyBones[model] = keyBones;

		return keyBones;
	}

	/// <summary> The names of an anim graph's parameters playback can set, in the graph's order. </summary>
	string[] GetGraphParameters( AnimationGraph graph )
	{
		if ( _graphParameters.TryGetValue( graph, out var names ) )
			return names;

		var supported = new List<string>();

		for ( var i = 0; i < graph.ParamCount; i++ )
		{
			// Null (or out of the engine's table) for a type playback can't set.
			Type type;
			try { type = graph.GetParameterType( i ); }
			catch ( IndexOutOfRangeException ) { type = null; }

			if ( type is not null )
				supported.Add( graph.GetParameterName( i ) );
		}

		names = supported.ToArray();
		_graphParameters[graph] = names;

		return names;
	}

	/// <summary>
	/// The recorder's capture action: every soldier's renderers, and through them the objects above them. Only the
	/// soldiers whose blocks restart in the restart pass, and only the one being admitted in its own capture.
	/// </summary>
	void CaptureSoldiers( MovieRecorder recorder )
	{
		if ( _admitting is not null )
		{
			CaptureSoldier( recorder, _admitting );
			return;
		}

		if ( _restartPass )
		{
			foreach ( var soldier in _restarting )
				CaptureSoldier( recorder, soldier );

			return;
		}

		foreach ( var soldier in _soldiers.Values )
		{
			if ( !soldier.Restart )
				CaptureSoldier( recorder, soldier );
		}
	}

		void CaptureSoldier( MovieRecorder recorder, Soldier soldier )
	{
		if ( !soldier.Scope.IsValid() )
			return;

			var replay = recorder == _replayRecorder;
			if ( replay && soldier.Entry.Died >= 0f && soldier.Entry.Died < _replayRoundStart )
				return;

			if ( replay ? !soldier.ReplayNamed : !soldier.Named )
		{
				if ( !soldier.Root.IsValid() )
					return;

				// Each recorder must name the root explicitly before capturing any child. Sharing Named between them
				// made the second recorder derive a different name from the live object.
			recorder.GetTrackRecorder( soldier.Root, soldier.Entry.Track );
				if ( replay )
				{
					soldier.ReplayNamed = true;
					_replaySoldiers[soldier.Entry.Track] = soldier;
				}
				else
				{
					soldier.Named = true;
				}
		}

		CaptureRenderers( recorder, soldier.Scope );

		// A bot's body once it has left the bot. Its tracks were made while it was the bot's, so they stay under the
		// soldier's, and its Parent records the move.
		var leaver = soldier.Leaver;
		if ( leaver != soldier.Scope && !IsWithin( leaver, soldier.Scope ) )
			CaptureRenderers( recorder, leaver );
	}

	/// <summary>
	/// Every renderer on <paramref name="scope"/> and under it. Disabled ones too, so a hidden gun or holstered part
	/// records being hidden. Not a model built at runtime (a gunsmith sticker): a replay can only name models that are
	/// files.
	/// </summary>
	static void CaptureRenderers( MovieRecorder recorder, GameObject scope )
	{
		foreach ( var renderer in scope.GetComponentsInChildren<ModelRenderer>( true, true ) )
		{
			if ( renderer.Model is { IsProcedural: true } )
				continue;

			recorder.GetTrackRecorder( renderer )?.Capture();
		}
	}

	static bool IsWithin( GameObject go, GameObject ancestor )
	{
		for ( var parent = go.Parent; parent.IsValid(); parent = parent.Parent )
		{
			if ( parent == ancestor )
				return true;
		}

		return false;
	}

	void Finish()
	{
			if ( _finished )
			return;

		_finished = true;

		if ( _active == this )
			_active = null;

			FinishTheaterRecording( save: !RecordingOff );
			_replayRecorder = null;
			_replaySoldiers.Clear();
		_soldiers.Clear();
		_bodies.Clear();
		_waiting.Clear();
		_waitingScopes.Clear();
		_restarting.Clear();
		}

		void FinishTheaterRecording( bool save )
		{
			if ( _recorder is null )
				return;

			var recorder = _recorder;
			var info = _info;
			var actions = _actions;
			var seconds = (float)recorder.Time.TotalSeconds;
			_recorder = null;

			// The worker owns the full recorder and sidecars from here. Continuing live replays get detached copies
			// of only their recent state, so a later death or suppressed shot cannot mutate what is being saved.
			if ( !_finished && _replayRecorder is not null )
				DetachReplayMetadata( seconds );

		var average = _captures > 0 ? _captureMicroseconds / _captures : 0;
		Log.Info( $"Theater: stopped after {seconds:0}s. {_captures} captures, {average:0} us on average, {_slowestCapture:0} us at most." );

			if ( !save )
				return;

			if ( seconds < MinimumSeconds )
		{
			Log.Info( $"Theater: not saving a recording under {MinimumSeconds:0}s." );
			return;
		}

		info.Duration = seconds;
		info.Recorded = DateTime.Now;

		_ = Save( recorder, info, actions );
	}

	/// <summary>
	/// Saves the replay on a worker thread (<see cref="Write"/>): nothing touches the recorder once recording has stopped.
	/// None of it runs on the main thread, where a long match's recording, a hundred megabytes and more of JSON, would
	/// stop the game for seconds.
	/// </summary>
	static async Task Save( MovieRecorder recorder, TheaterReplays.Info info, TheaterReplays.Actions actions )
	{
		var id = TheaterReplays.NewId();

		try
		{
			await GameTask.RunInThreadAsync( () => Write( id, recorder, info, actions ) );
		}
		catch ( TaskCanceledException )
		{
			// The game ended while it saved. The worker thread finished the job anyway: only waiting for it was cut short.
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: couldn't save the replay: {e}" );
			TheaterReplays.Delete( id );
		}
	}

	/// <summary> Writes the recording, its actions, then its sidecar, and prunes the old replays. On a worker thread. </summary>
	static void Write( string id, MovieRecorder recorder, TheaterReplays.Info info, TheaterReplays.Actions actions )
	{
		FileSystem.Data.CreateDirectory( TheaterReplays.Folder );

		var bytes = TheaterReplays.WriteClip( TheaterReplays.MoviePath( id ), recorder.ToClip() );

		// Without its actions a replay still plays, with an idle first-person gun.
		try
		{
			FileSystem.Data.WriteAllText( TheaterReplays.ActionsPath( id ), Json.Serialize( actions ) );
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: couldn't save the replay's actions: {e.Message}" );
		}

		FileSystem.Data.WriteJson( TheaterReplays.InfoPath( id ), info );

		Log.Info( $"Theater: saved {id}: {info.Duration:0}s, {info.Soldiers.Count} lives, {bytes / 1024} KB." );
		TheaterReplays.Prune();
	}

	/// <summary>
	/// What every renderer records. Not <see cref="ModelRenderer.RenderType"/>: the viewer's own body is shadows-only
	/// in first person, and the theater shows it.
	/// </summary>
	sealed class RendererCapturer : ComponentCapturer<ModelRenderer>
	{
		// A constructor with a parameter keeps it out of MovieRecorderOptions.Default, which makes every capturer with none.
		public RendererCapturer( MatchRecorder owner ) { }

		protected override void OnCapture( IMovieTrackRecorder recorder, ModelRenderer renderer )
		{
			recorder.Property( nameof( ModelRenderer.Model ) ).Capture();
			recorder.Property( nameof( ModelRenderer.Tint ) ).Capture();
			recorder.Property( nameof( ModelRenderer.MaterialOverride ) ).Capture();
			recorder.Property( nameof( ModelRenderer.MaterialGroup ) ).Capture();

			if ( renderer.HasBodyGroups )
				recorder.Property( nameof( ModelRenderer.BodyGroups ) ).Capture();
		}
	}

	/// <summary>
	/// A soldier's body records the anim graph parameters the game sets while it's alive, and its ragdoll's key bones
	/// once it's dead. Other skinned renderers (clothing, guns) follow a body or keep their model's pose.
	/// </summary>
	sealed class SkinnedCapturer : ComponentCapturer<SkinnedModelRenderer>
	{
		readonly MatchRecorder _owner;

		public SkinnedCapturer( MatchRecorder owner )
		{
			_owner = owner;
		}

		protected override void OnCapture( IMovieTrackRecorder recorder, SkinnedModelRenderer renderer )
		{
			recorder.Property( nameof( SkinnedModelRenderer.BoneMergeTarget ) ).Capture();

			if ( renderer.BoneMergeTarget.IsValid() )
				return;

			recorder.Property( nameof( SkinnedModelRenderer.CreateBoneObjects ) ).Capture();
			recorder.Property( nameof( SkinnedModelRenderer.UseAnimGraph ) ).Capture();

			if ( !_owner._bodies.TryGetValue( renderer, out var soldier ) )
				return;

			if ( renderer.UseAnimGraph )
				CaptureParameters( recorder, renderer, soldier );
			else
				CaptureBones( recorder, renderer );
		}

		void CaptureParameters( IMovieTrackRecorder recorder, SkinnedModelRenderer renderer, Soldier soldier )
		{
			if ( soldier.NextParameterScan )
			{
				// The first scan is at once. After it, each body keeps a phase of its own, so those that spawned together
				// don't all scan in the same capture.
				soldier.NextParameterScan = soldier.ScannedParameters
					? ParameterScanInterval
					: ParameterScanInterval * Game.Random.Float( 0.5f, 1.5f );

				soldier.ScannedParameters = true;
				ScanParameters( renderer, soldier );
			}

			if ( soldier.Parameters.Count == 0 )
				return;

			var parameters = recorder.Property( nameof( SkinnedModelRenderer.Parameters ) );

			foreach ( var name in soldier.Parameters )
				parameters.Property( name ).Capture();
		}

		/// <summary> Only the parameters the game has set: the rest stay at the graph's defaults. </summary>
		void ScanParameters( SkinnedModelRenderer renderer, Soldier soldier )
		{
			if ( renderer.Parameters.Graph is not { } graph )
				return;

			foreach ( var name in _owner.GetGraphParameters( graph ) )
			{
				if ( soldier.KnownParameters.Contains( name ) || !renderer.Parameters.Contains( name ) )
					continue;

				soldier.KnownParameters.Add( name );
				soldier.Parameters.Add( name );
			}
		}

		void CaptureBones( IMovieTrackRecorder recorder, SkinnedModelRenderer renderer )
		{
			if ( _owner.GetKeyBones( renderer.Model ) is not { } keyBones )
				return;

			var bones = recorder.Property( "Bones" );

			foreach ( var name in keyBones.Names )
				bones.Property( name ).Capture();
		}
	}
}
