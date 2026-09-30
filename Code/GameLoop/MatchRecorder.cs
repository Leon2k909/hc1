using Sandbox.Diagnostics;
using Sandbox.MovieMaker;
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
/// animation and physics are done, and the file is written on a worker thread after the match.
/// </para>
/// <para>
/// What each soldier does with their guns goes in an actions file beside it (<see cref="TheaterReplays.Actions"/>), for
/// the first-person view: what they hold, from their equipment, and whether they're aiming, sprinting, reloading or out
/// of ammo, from state every machine is sent, at each capture; and their shots, from the shot effects every machine plays
/// (<see cref="NoteShot"/>). None of it is in the recording: the first-person gun isn't a soldier's renderer, and the
/// anim graph's attack and reload triggers are spent by the end of the frame.
/// </para>
/// </summary>
public sealed class MatchRecorder : Component, Component.ISceneStage
{
	/// <summary> Settings → Game → Theater Recording, the player's own and on by default. </summary>
	public static bool RecordingOff => GameSettingsSystem.Current is { } settings && !settings.TheaterRecording;

	/// <summary> Captures a second. Playback blends positions and bones between them. </summary>
	public const int SampleRate = 15;

	/// <summary> Shorter recordings (a match left straight away) aren't saved. </summary>
	const float MinimumSeconds = 20f;

	const float MaximumSeconds = 30f * 60f;

	/// <summary> How long recording carries on once the match is over. </summary>
	const float EndDelay = 3f;

	/// <summary> How often a dead body is checked for having come to rest. </summary>
	const float SettleInterval = 0.5f;

	/// <summary> A body whose key bones moved less than this between checks has come to rest. </summary>
	const float SettleDistance = 0.05f;

	/// <summary> How often a body's anim graph is checked for parameters the game has started setting. </summary>
	const float ParameterScanInterval = 2f;

	/// <summary> Modes that aren't recorded: battle royale's map and field are too big, and zombies aren't soldiers. </summary>
	static readonly string[] SkippedModes = { "battle_royale", "zombies" };

	/// <summary> The recorder recording now, which the game's shots reach through <see cref="NoteShot"/>. </summary>
	static MatchRecorder _active;

	MovieRecorder _recorder;
	TheaterReplays.Info _info;
	TheaterReplays.Actions _actions;

	/// <summary> Each build code's index in the actions' <see cref="TheaterReplays.Actions.Builds"/>. </summary>
	readonly Dictionary<string, int> _builds = new();
	double _startTime;
	double _stopTime = -1;
	int _frame = -1;
	bool _restartPass;
	bool _anyRestart;
	bool _finished;

	int _captures;
	double _captureMicroseconds;
	double _slowestCapture;

	/// <summary> The soldiers being recorded, by the object whose renderers are captured. </summary>
	readonly Dictionary<GameObject, Soldier> _soldiers = new();

	/// <summary> The same soldiers, by their body's renderer, for <see cref="SkinnedCapturer"/>. </summary>
	readonly Dictionary<SkinnedModelRenderer, Soldier> _bodies = new();

	/// <summary> How many lives each name has had, for its tracks' names. </summary>
	readonly Dictionary<string, int> _lives = new();

	readonly Dictionary<Model, KeyBones> _keyBones = new();
	readonly List<GameObject> _gone = new();

	public bool IsRecording => _recorder is not null && !_finished;

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

		public bool Named;
		public bool Restart;
		public GameObject LastParent;

		public bool Settled;
		public TimeUntil NextSettleCheck;
		public Vector3[] LastPose;

		public readonly List<string> Parameters = new();
		public readonly HashSet<string> KnownParameters = new( StringComparer.OrdinalIgnoreCase );
		public TimeUntil NextParameterScan;

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
		if ( !CanRecord( out var reason ) )
		{
			Log.Info( $"Theater: not recording this match ({reason})." );
			return;
		}

		var options = new MovieRecorderOptions( SampleRate )
			.WithComponentCapturer( new RendererCapturer( this ) )
			.WithComponentCapturer( new SkinnedCapturer( this ) )
			.WithCaptureAction( CaptureSoldiers );

		_recorder = new MovieRecorder( Scene, options );
		_startTime = Time.NowDouble;

		var mode = GetComponent<GameMode>();
		var sceneFile = Scene.Source as SceneFile;

		_info = new TheaterReplays.Info
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
		};

		_actions = new TheaterReplays.Actions();
		_active = this;

		Log.Info( $"Theater: recording {_info.MapTitle} ({_info.Mode})." );
	}

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
		if ( _recorder is null || _finished )
			return;

		var now = Time.NowDouble;
		var elapsed = now - _startTime;

		if ( _stopTime < 0 && (Facepunch.UI.EndOfMatchScreen.IsAnyVisible || MapVoteSystem.Instance.IsValid()) )
			_stopTime = now + EndDelay;

		if ( elapsed >= MaximumSeconds || (_stopTime >= 0 && now >= _stopTime) )
		{
			Finish();
			return;
		}

		// Scene time can step back on a client while it syncs with the host: wait for it.
		var frame = (int)(elapsed * SampleRate);
		if ( frame <= _frame )
			return;

		_frame = frame;

		var timer = FastTimer.StartNew();

		RefreshSoldiers( frame / (float)SampleRate );

		_recorder.Advance( MovieTime.FromFrames( frame, SampleRate ) - _recorder.Time );
		_recorder.Capture();

		// Soldiers whose blocks start again (see Restart) are left out of that capture and caught up a tick later: their
		// recorders then see a capture they missed, finish their blocks and start new ones at the same frame.
		if ( _anyRestart )
		{
			_recorder.Advance( MovieTime.Epsilon );
			_restartPass = true;
			_recorder.Capture();
			_restartPass = false;
			_anyRestart = false;

			foreach ( var soldier in _soldiers.Values )
				soldier.Restart = false;
		}

		var micros = timer.ElapsedMicroSeconds;
		_captures++;
		_captureMicroseconds += micros;
		_slowestCapture = Math.Max( _slowestCapture, micros );
	}

	/// <summary>
	/// Starts a soldier's blocks again at this frame. Blocks blend between their samples, so this goes where the values
	/// jump (a body moving into another parent's space), and where they stop changing (a body at rest), so the rest of
	/// its time is stored as constants.
	/// </summary>
	void Restart( Soldier soldier )
	{
		soldier.Restart = true;
		_anyRestart = true;
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

		foreach ( var bot in Scene.GetAllComponents<LightweightCombatBot>() )
		{
			var go = bot.GameObject;
			if ( _soldiers.ContainsKey( go ) || !bot.IsAlive || go.Tags.Has( "dead" ) )
				continue;

			AddSoldier( new Soldier { Root = go, Scope = go, Bot = bot }, "Bot", bot.BotName, bot.Team, 0, time );
		}

		foreach ( var body in Scene.GetAllComponents<PlayerBody>() )
		{
			var go = body.GameObject;
			if ( _soldiers.ContainsKey( go ) )
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

			AddSoldier( new Soldier { Root = pawn.GameObject, Scope = go, PlayerBody = body },
				client.IsBot ? "Bot" : "Player", name, pawn.Team, client.IsBot ? 0 : client.SteamId, time );
		}

		foreach ( var soldier in _soldiers.Values )
			UpdateSoldier( soldier, time );
	}

	void AddSoldier( Soldier soldier, string kind, string name, Team team, ulong steamId, float time )
	{
		name = string.IsNullOrWhiteSpace( name ) ? kind : name;

		// "#n", not "(n)": the recorder treats "Name (2)" as another copy of "Name" and would reuse its track.
		var key = $"{kind}: {name}";
		var life = _lives.GetValueOrDefault( key ) + 1;
		_lives[key] = life;

		soldier.Entry = new TheaterReplays.Soldier
		{
			Track = $"{key} #{life}",
			Body = PathFrom( soldier.Root, soldier.FindBody()?.GameObject ),
			Name = name,
			Team = team,
			Bot = kind == "Bot",
			SteamId = steamId,
			Spawned = time
		};

		soldier.LastParent = soldier.Leaver.Parent;

		// A bot's sprint isn't sent to clients: playback works it out from its speed.
		soldier.Actions = new TheaterReplays.LifeActions { Sprinting = soldier.Bot.IsValid() ? null : new() };
		_actions.Lives[soldier.Entry.Track] = soldier.Actions;

		_soldiers[soldier.Scope] = soldier;
		_info.Soldiers.Add( soldier.Entry );
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

			if ( soldier.Named )
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
		if ( equipment != soldier.Equipment || !actions.Held.Any() )
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
			// A player's gun here wears this machine's saved build, whoever holds it (Equipment.CreateWorldModel), so the
			// replay's does too. A bot's gun has none.
			Build = equipment.IsValid() && equipment.ApplySavedAttachments && resource.IsValid() ? BuildIndex( resource ) : -1
		} );
	}

	int BuildIndex( EquipmentResource resource )
	{
		var code = Facepunch.Gunsmith.GunsmithLoadoutManager.ExportWeaponBuildCode( resource );
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
			soldier.LastPose = null;
			return;
		}

		var pose = new Vector3[bones.Indices.Length];
		for ( var i = 0; i < pose.Length; i++ )
			pose[i] = sceneModel.GetBoneWorldTransform( bones.Indices[i] ).Position;

		if ( soldier.LastPose is { } last && last.Length == pose.Length )
		{
			var moved = 0f;
			for ( var i = 0; i < pose.Length; i++ )
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

		soldier.LastPose = pose;
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

	/// <summary> The recorder's capture action: every soldier's renderers, and through them the objects above them. </summary>
	void CaptureSoldiers( MovieRecorder recorder )
	{
		foreach ( var soldier in _soldiers.Values )
		{
			if ( soldier.Restart != _restartPass || !soldier.Scope.IsValid() )
				continue;

			if ( !soldier.Named )
			{
				// Makes the root's track first, under the soldier's name: its renderers' tracks go under it.
				soldier.Named = true;
				recorder.GetTrackRecorder( soldier.Root, soldier.Entry.Track );
			}

			CaptureRenderers( recorder, soldier.Scope );

			// A bot's body once it has left the bot. Its tracks were made while it was the bot's, so they stay under the
			// soldier's, and its Parent records the move.
			var leaver = soldier.Leaver;
			if ( leaver != soldier.Scope && !IsWithin( leaver, soldier.Scope ) )
				CaptureRenderers( recorder, leaver );
		}
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
		if ( _recorder is null || _finished )
			return;

		_finished = true;

		if ( _active == this )
			_active = null;

		var recorder = _recorder;
		var info = _info;
		var actions = _actions;
		var seconds = (float)recorder.Time.TotalSeconds;

		_recorder = null;
		_soldiers.Clear();
		_bodies.Clear();

		var average = _captures > 0 ? _captureMicroseconds / _captures : 0;
		Log.Info( $"Theater: stopped after {seconds:0}s. {_captures} captures, {average:0} us on average, {_slowestCapture:0} us at most." );

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
	/// Writes the recording, its actions, then its sidecar. Turning it into JSON takes the longest, so that and the writing
	/// happen on a worker thread: nothing touches the recorder once recording has stopped.
	/// </summary>
	static async Task Save( MovieRecorder recorder, TheaterReplays.Info info, TheaterReplays.Actions actions )
	{
		var id = TheaterReplays.NewId();

		try
		{
			FileSystem.Data.CreateDirectory( TheaterReplays.Folder );

			string json;
			try
			{
				json = await GameTask.RunInThreadAsync( () => Json.Serialize( recorder.ToClip() ) );
			}
			catch ( Exception e )
			{
				Log.Warning( $"Theater: couldn't save on a worker thread ({e.Message}), saving on the main thread." );
				json = Json.Serialize( recorder.ToClip() );
			}

			await GameTask.RunInThreadAsync( () => FileSystem.Data.WriteAllText( TheaterReplays.MoviePath( id ), json ) );

			// Without its actions a replay still plays, with an idle first-person gun.
			try
			{
				var actionsJson = await GameTask.RunInThreadAsync( () => Json.Serialize( actions ) );
				await GameTask.RunInThreadAsync( () => FileSystem.Data.WriteAllText( TheaterReplays.ActionsPath( id ), actionsJson ) );
			}
			catch ( Exception e )
			{
				Log.Warning( $"Theater: couldn't save the replay's actions: {e.Message}" );
			}

			FileSystem.Data.WriteJson( TheaterReplays.InfoPath( id ), info );

			Log.Info( $"Theater: saved {id}: {info.Duration:0}s, {info.Soldiers.Count} lives, {json.Length / 1024} KB." );
			TheaterReplays.Prune();
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: couldn't save the replay: {e}" );
			TheaterReplays.Delete( id );
		}
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

		static void CaptureParameters( IMovieTrackRecorder recorder, SkinnedModelRenderer renderer, Soldier soldier )
		{
			if ( soldier.NextParameterScan )
			{
				soldier.NextParameterScan = ParameterScanInterval;
				ScanParameters( renderer, soldier );
			}

			if ( soldier.Parameters.Count == 0 )
				return;

			var parameters = recorder.Property( nameof( SkinnedModelRenderer.Parameters ) );

			foreach ( var name in soldier.Parameters )
				parameters.Property( name ).Capture();
		}

		/// <summary> Only the parameters the game has set: the rest stay at the graph's defaults. </summary>
		static void ScanParameters( SkinnedModelRenderer renderer, Soldier soldier )
		{
			if ( renderer.Parameters.Graph is not { } graph )
				return;

			for ( var i = 0; i < graph.ParamCount; i++ )
			{
				// Null (or out of the engine's table) for a type playback can't set.
				Type type;
				try { type = graph.GetParameterType( i ); }
				catch ( IndexOutOfRangeException ) { type = null; }

				if ( type is null )
					continue;

				var name = graph.GetParameterName( i );
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
