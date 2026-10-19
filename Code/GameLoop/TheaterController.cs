using Sandbox.MovieMaker;
using Sandbox.MovieMaker.Compiled;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Facepunch;

/// <summary>
/// Plays a Theater replay (<see cref="TheaterReplays"/>, recorded by <see cref="MatchRecorder"/>) in
/// scenes/theater_playback.scene. It loads the match's map, then the recording, and drives the <see cref="MoviePlayer"/>
/// itself through a <see cref="TheaterClip"/>, so only the lives around the current time are played. The camera follows
/// a soldier from behind or looks out of their eyes, or flies free. <see cref="UI.TheaterOverlay"/> is its HUD.
/// </summary>
public sealed class TheaterController : Component, Component.ISceneStage
{
	/// <summary> The id of the replay to play, set by the Theater page. </summary>
	public const string ReplayCookie = "theater_replay";

	public static readonly float[] Speeds = { 0.25f, 0.5f, 1f, 2f, 4f };

	/// <summary> How long a paused replay animates after a seek, so the soldiers take up their new poses. </summary>
	const float SettleTime = 0.35f;

	const float MapTimeout = 120f;

	/// <summary> How quickly the first-person view settles on the eyes, per second: it takes the walk's bob out of the head. </summary>
	const float EyeSmoothing = 12f;

	/// <summary> How quickly the first-person view turns to where the soldier looks, per second. </summary>
	const float LookSmoothing = 20f;

	[Property] public MoviePlayer Player { get; set; }
	[Property] public CameraComponent ViewCamera { get; set; }

	public static TheaterController Current { get; private set; }

	public TheaterReplays.Info Info { get; private set; }
	public bool IsLoading { get; private set; } = true;

	/// <summary> What's loading, in English: translated when it's shown. </summary>
	public string LoadingStatus { get; private set; } = "Loading replay";

	/// <summary> Why the replay can't be played, in English, or null. </summary>
	public string Error { get; private set; }

	/// <summary> Seconds. </summary>
	public float Duration { get; private set; }

	/// <summary> Seconds into the replay. </summary>
	public float Position => (float)_position;

	public bool IsPaused { get; private set; }
	public bool IsAtEnd => Duration > 0f && _position >= Duration - 0.01;
	public float Speed { get; private set; } = 1f;
	public bool IsFreecam { get; private set; }

	/// <summary> Whether following looks out of the soldier's eyes rather than from behind them. </summary>
	public bool IsFirstPerson { get; private set; }

	/// <summary> Whether the camera is in a soldier's eyes now: first person, following someone alive. </summary>
	public bool ShowsFirstPerson => _inFirstPerson && !IsFreecam;

	/// <summary> The people in the replay, each with all their lives, in team then name order. </summary>
	public IReadOnlyList<Person> People => _people;

	/// <summary> Whom the camera follows (when not in freecam). </summary>
	public Person Following { get; private set; }

	/// <summary> Whether <see cref="Following"/> is alive at the current time. </summary>
	public bool FollowingAlive => _followLife?.Soldier?.IsAliveAt( Position ) ?? false;

	public sealed record Person( string Key, string Name, Team Team, bool Bot, ulong SteamId );

	readonly List<Person> _people = new();
	readonly List<MapInstance> _maps = new();
	readonly Dictionary<Model, (BoneCollection.Bone Bone, Transform Offset)> _hands = new();
	readonly Dictionary<Model, BoneCollection.Bone> _focusBones = new();

	TheaterClip _clip;
	TheaterReplays.Actions _actions;
	double _position;
	TimeUntil _settle;
	TheaterClip.Life _followLife;

	Vector3 _focus;
	float _facing;
	float _orbitYaw;
	float _orbitPitch = 14f;
	float _distance = 110f;
	bool _snapCamera = true;
	Angles _freeLook;
	float _freeSpeed = 500f;
	bool _looking;

	/// <summary> The followed soldier's renderers, down to shadows while the camera is in their eyes. </summary>
	readonly List<ModelRenderer> _hidden = new();
	GameObject _hiddenRoot;
	bool _inFirstPerson;
	Vector3 _eyeOffset;
	Rotation _eyeRotation;
	float _followFov;

	/// <summary> The first-person gun, while the camera is in someone's eyes. </summary>
	readonly TheaterViewModel _gun = new();

	protected override void OnEnabled()
	{
		Current = this;
	}

	protected override void OnDisabled()
	{
		if ( Current == this )
			Current = null;

		_gun.Clear();
		ShowSoldier();
		ShowCursor();
	}

	protected override void OnStart()
	{
		ShowCursor();
		_ = Load();
	}

	async Task Load()
	{
		var id = Game.Cookies.Get( ReplayCookie, "" );
		Info = TheaterReplays.ReadInfo( id );

		if ( Info is null || !FileSystem.Data.FileExists( TheaterReplays.MoviePath( id ) ) )
		{
			Fail( "This replay can't be found." );
			return;
		}

		if ( !Player.IsValid() || !ViewCamera.IsValid() )
		{
			Fail( "The Theater's scene is missing its player or camera." );
			return;
		}

		LoadingStatus = "Loading map";
		CreateMaps();

		var timeout = RealTime.Now + MapTimeout;
		while ( _maps.Any( x => x.IsValid() && !x.IsLoaded ) )
		{
			if ( RealTime.Now > timeout )
			{
				Fail( "The map didn't load." );
				return;
			}

			await Task.Frame();
			if ( !this.IsValid() )
				return;
		}

		LoadingStatus = "Loading recording";
		await Task.Frame();

		MovieClip clip;
		try
		{
			clip = await ReadClip( id );
		}
		catch ( TaskCanceledException )
		{
			// Play stopped while it was reading.
			return;
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: can't read replay {id}: {e}" );
			Fail( "This replay can't be read." );
			return;
		}

		if ( !this.IsValid() )
			return;

		if ( clip is null || clip.Duration <= MovieTime.Zero )
		{
			Fail( "This replay is empty." );
			return;
		}

		_actions = await ReadActions( id );
		if ( !this.IsValid() )
			return;

		Play( clip );
	}

	/// <summary>
	/// What the soldiers did with their guns, for the first-person gun (<see cref="TheaterReplays.Actions"/>). A replay
	/// recorded before there were actions has none, and its gun is idle.
	/// </summary>
	static async Task<TheaterReplays.Actions> ReadActions( string id )
	{
		var path = TheaterReplays.ActionsPath( id );

		try
		{
			if ( !FileSystem.Data.FileExists( path ) )
				return null;

			var json = await GameTask.RunInThreadAsync( () => FileSystem.Data.ReadAllText( path ) );
			return Json.Deserialize<TheaterReplays.Actions>( json );
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: can't read replay {id}'s actions, so its first-person gun is idle: {e.Message}" );
			return null;
		}
	}

	/// <summary>
	/// The recording, read and parsed on a worker thread (<see cref="TheaterReplays.ReadClip"/>): a long match's is tens of
	/// megabytes. Never on the main thread: the task is only cancelled once play has stopped, when nobody wants the clip.
	/// </summary>
	static Task<MovieClip> ReadClip( string id )
	{
		var path = TheaterReplays.MoviePath( id );
		return GameTask.RunInThreadAsync( () => TheaterReplays.ReadClip( path ) );
	}

	void CreateMaps()
	{
		foreach ( var entry in Info.Maps ?? new() )
		{
			if ( string.IsNullOrWhiteSpace( entry.Name ) )
				continue;

			var go = new GameObject( true, "Map" );
			go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			go.WorldTransform = new Transform( entry.Position, entry.Rotation, entry.Scale );

			var map = go.Components.Create<MapInstance>( false );
			map.UseMapFromLaunch = false;
			map.NoOrigin = entry.NoOrigin;
			map.EnableCollision = true;
			map.MapName = entry.Name;
			map.Enabled = true;

			_maps.Add( map );
		}
	}

	void Play( MovieClip clip )
	{
		LoadingStatus = "Placing soldiers";

		_clip = new TheaterClip( clip, Player.Binder, Info.Soldiers );
		Duration = (float)clip.Duration.TotalSeconds;
		_followFov = ViewCamera.FieldOfView;

		// The player's own clock is never used: this moves it, so it only ever plays what TheaterClip lists.
		Player.IsPlaying = false;
		Player.TimeScale = 1f;

		// Makes the objects for every life at once, then hides those not on at the start.
		_clip.ListAllTracks = true;
		Player.Clip = _clip;
		_clip.ListAllTracks = false;

		BuildPeople();

		var own = _people.FirstOrDefault( x => !x.Bot && x.SteamId == Info.RecordedBy && Info.RecordedBy != 0 );
		Follow( own ?? _people.FirstOrDefault() );

		_position = 0;
		ApplyPosition();

		IsLoading = false;
		Log.Info( $"Theater: playing {Info.MapTitle}, {Duration:0}s, {_clip.Lives.Count} lives, {clip.Tracks.Length} tracks." );
	}

	void BuildPeople()
	{
		_people.Clear();

		foreach ( var soldier in Info.Soldiers ?? new() )
		{
			var key = KeyOf( soldier );
			if ( _people.Any( x => x.Key == key ) )
				continue;

			_people.Add( new Person( key, soldier.Name, soldier.Team, soldier.Bot, soldier.SteamId ) );
		}

		_people.Sort( ( a, b ) => a.Team != b.Team
			? a.Team.CompareTo( b.Team )
			: string.Compare( a.Name, b.Name, StringComparison.OrdinalIgnoreCase ) );
	}

	static string KeyOf( TheaterReplays.Soldier soldier ) => $"{(soldier.Bot ? "bot" : "player")}:{soldier.Name}";

	void Fail( string error )
	{
		Error = error;
		IsLoading = false;
		Log.Warning( $"Theater: {error}" );
	}

	/// <summary> Leaves for the main menu's Theater page. </summary>
	public void Exit()
	{
		ShowCursor();
		GameUtils.ReturnToMainMenu( "/theater" );
	}

	public void TogglePause()
	{
		if ( IsAtEnd )
		{
			IsPaused = false;
			Seek( 0f );
			return;
		}

		IsPaused = !IsPaused;
	}

	public void SetSpeed( float speed )
	{
		Speed = Math.Clamp( speed, Speeds[0], Speeds[^1] );
	}

	public void Skip( float seconds ) => Seek( Position + seconds );

	public void Seek( float seconds )
	{
		if ( _clip is null )
			return;

		var from = _position;
		_position = Math.Clamp( seconds, 0f, Duration );

		if ( IsPaused )
			_settle = SettleTime;

		// A long jump puts the camera straight on the soldier, rather than flying it there.
		if ( Math.Abs( _position - from ) > 1.0 )
			_snapCamera = true;

		ApplyPosition();
	}

	public void ToggleCamera()
	{
		IsFreecam = !IsFreecam;

		if ( IsFreecam )
			_freeLook = ViewCamera.WorldRotation.Angles().WithRoll( 0f );
		else
			_snapCamera = true;
	}

	/// <summary> Between looking out of the soldier's eyes and following them from behind. From freecam, it follows in first person. </summary>
	public void ToggleFirstPerson()
	{
		if ( IsFreecam )
		{
			ToggleCamera();
			IsFirstPerson = true;
			return;
		}

		IsFirstPerson = !IsFirstPerson;
		_snapCamera = true;
	}

	/// <summary> Follows the next (or previous) person who's in the replay at this moment. </summary>
	public void NextPerson( int direction )
	{
		if ( _people.Count == 0 )
			return;

		var present = _people.Where( IsPresent ).ToList();
		if ( present.Count == 0 )
			present = _people;

		var index = present.IndexOf( Following );
		index = index < 0 ? 0 : (index + direction + present.Count) % present.Count;

		Follow( present[index] );

		if ( IsFreecam )
			ToggleCamera();
	}

	public void Follow( Person person )
	{
		Following = person;
		_followLife = null;
		_snapCamera = true;
		_orbitYaw = 0f;
	}

	bool IsPresent( Person person ) => Info.Soldiers.Any( x => KeyOf( x ) == person.Key && x.IsPresentAt( Position ) );

	protected override void OnUpdate()
	{
		// Here rather than in a panel: s&box's own menu takes whatever Escape is left after the scene's update.
		if ( Input.EscapePressed )
		{
			Input.EscapePressed = false;
			Exit();
			return;
		}

		if ( IsLoading || Error is not null || _clip is null )
			return;

		if ( Input.Pressed( "Jump" ) )
			TogglePause();

		if ( Input.Pressed( "FireMode" ) )
			ToggleCamera();

		// The spectators' Change View key.
		if ( Input.Pressed( "SpectatorMode" ) )
			ToggleFirstPerson();

		if ( !IsFreecam && Input.Pressed( "Right" ) )
			NextPerson( 1 );

		if ( !IsFreecam && Input.Pressed( "Left" ) )
			NextPerson( -1 );

		if ( !IsPaused )
		{
			_position += Time.Delta * Speed;

			if ( _position >= Duration )
			{
				_position = Duration;
				IsPaused = true;
			}
		}

		ApplyPosition();
		UpdateLookInput();

		if ( IsFreecam )
			UpdateFreecam();
		else
			UpdateFollowCamera();
	}

	void ApplyPosition()
	{
		_clip.SetTime( _position );
		Player.Position = MovieTime.FromSeconds( _position );

		// The anim graphs run at the frame rate from the recorded parameters: at the replay's speed, frozen while paused.
		var rate = AnimationRate;

		foreach ( var life in _clip.Active )
		{
			foreach ( var renderer in life.GetRenderers( Player.Binder ) )
			{
				if ( renderer.SceneModel is { } model && !renderer.BoneMergeTarget.IsValid() )
					model.PlaybackRate = renderer.PlaybackRate * rate;
			}
		}
	}

	/// <summary> How fast animations run: at the replay's speed, frozen while paused (once a seek has settled). </summary>
	float AnimationRate => IsPaused ? (_settle > 0f ? 1f : 0f) : Speed;

	void ISceneStage.End()
	{
		if ( _clip is null )
			return;

		foreach ( var life in _clip.Active )
		{
			foreach ( var renderer in life.GetRenderers( Player.Binder ) )
			{
				// A ragdoll's bones stay on the model after a seek back to when it was alive.
				if ( renderer.UseAnimGraph && renderer.SceneModel.IsValid() && renderer.SceneModel.HasBoneOverrides() )
					renderer.ClearPhysicsBones();
			}

			FollowHand( life );
		}
	}

	/// <summary>
	/// A bot's gun was on an object it moved to the hand every frame (<see cref="LightweightCombatBot.FollowHand"/>).
	/// Its recorded place lags the hand, which animates at the frame rate here, so it's put in the hand again.
	/// </summary>
	void FollowHand( TheaterClip.Life life )
	{
		var hold = life.GetWeaponHold( Player.Binder );
		var root = life.GetRoot( Player.Binder );
		if ( hold is null || root is null || hold.Parent != root || !hold.Active )
			return;

		var body = life.GetBody( Player.Binder );
		if ( body is null || body.Model is null || !body.SceneModel.IsValid() )
			return;

		if ( !_hands.TryGetValue( body.Model, out var hand ) )
		{
			var bones = body.Model.Bones;
			var bone = MilitaryUniform.UsesHumanSkeleton( body.Model ) ? null
				: bones.GetBone( "hold_r" ) ?? bones.GetBone( "hold_R" );
			var offset = global::Transform.Zero;

			if ( bone is null )
			{
				bone = bones.GetBone( "r_hand" ) ?? bones.GetBone( "hand_R" );
				offset = MilitaryUniform.WeaponHandOffset( body.Model );
			}

			_hands[body.Model] = hand = (bone, offset);
		}

		if ( hand.Bone is not null && body.TryGetBoneTransform( hand.Bone, out var transform ) )
			hold.WorldTransform = transform.WithScale( 1f ).ToWorld( hand.Offset );
	}

	/// <summary>
	/// Holding the right mouse button (off the HUD's controls) looks around: the cursor hides while it's held. In first
	/// person the soldier does the looking.
	/// </summary>
	void UpdateLookInput()
	{
		var overControls = UI.TheaterOverlay.Instance?.IsPointerOverControls() ?? false;

		if ( Input.Pressed( "attack2" ) && !overControls && !ShowsFirstPerson )
		{
			_looking = true;
			HideCursor();
		}

		if ( _looking && !Input.Down( "attack2" ) )
		{
			_looking = false;
			ShowCursor();
		}

		if ( _looking )
		{
			var look = Input.AnalogLook;

			if ( IsFreecam )
			{
				_freeLook += look;
				_freeLook.pitch = Math.Clamp( _freeLook.pitch, -89f, 89f );
			}
			else if ( !ShowsFirstPerson )
			{
				_orbitYaw += look.yaw;
				_orbitPitch = Math.Clamp( _orbitPitch + look.pitch, -40f, 75f );
			}
		}

		var wheel = overControls || ShowsFirstPerson ? 0f : Input.MouseWheel.y;
		if ( wheel == 0f )
			return;

		if ( IsFreecam )
			_freeSpeed = Math.Clamp( _freeSpeed * (1f + wheel * 0.15f), 100f, 5000f );
		else
			_distance = Math.Clamp( _distance * (1f - wheel * 0.1f), 40f, 500f );
	}

	void UpdateFreecam()
	{
		EndFirstPerson();

		var rotation = _freeLook.ToRotation();
		var move = Vector3.Zero;

		if ( Input.Down( "Forward" ) ) move += rotation.Forward;
		if ( Input.Down( "Backward" ) ) move -= rotation.Forward;
		if ( Input.Down( "Right" ) ) move += rotation.Right;
		if ( Input.Down( "Left" ) ) move -= rotation.Right;
		if ( Input.Down( "Use" ) ) move += Vector3.Up;
		if ( Input.Down( "PrevSlot" ) ) move -= Vector3.Up;

		var speed = _freeSpeed;
		if ( Input.Down( "Run" ) ) speed *= 3f;
		if ( Input.Down( "Walk" ) ) speed *= 0.25f;

		if ( !move.IsNearZeroLength )
			ViewCamera.WorldPosition += move.Normal * speed * Time.Delta;

		ViewCamera.WorldRotation = rotation;
	}

	void UpdateFollowCamera()
	{
		_followLife = FindLife( Following, _position );

		var body = _followLife?.GetBody( Player.Binder );
		if ( body is null || !body.Active )
		{
			EndFirstPerson();
			return;
		}

		var alive = _followLife.Soldier?.IsAliveAt( Position ) ?? true;

		// A dead soldier is watched from behind until they're back.
		if ( IsFirstPerson && alive && UpdateFirstPerson( _followLife, body ) )
			return;

		if ( _inFirstPerson )
		{
			EndFirstPerson();
			_snapCamera = true;
		}

		var focus = GetFocus( body, alive );
		var facing = alive ? body.WorldRotation.Yaw() : _facing;

		if ( _snapCamera || focus.Distance( _focus ) > 300f )
		{
			_snapCamera = false;
			_focus = focus;
			_facing = facing;
		}
		else
		{
			_focus = Vector3.Lerp( _focus, focus, 1f - MathF.Exp( -Time.Delta * 12f ) );
			_facing += DeltaDegrees( _facing, facing ) * (1f - MathF.Exp( -Time.Delta * 4f ));
		}

		var rotation = Rotation.From( _orbitPitch, _facing + _orbitYaw, 0f );
		var desired = _focus - rotation.Forward * _distance + rotation.Right * 16f;

		// Only the map has collision here: the replayed soldiers have none.
		var trace = Scene.Trace.Ray( _focus, desired ).Radius( 5f ).Run();

		ViewCamera.WorldPosition = trace.Hit ? trace.EndPosition : desired;
		ViewCamera.WorldRotation = rotation;
	}

	/// <summary>
	/// Looks out of the soldier's eyes (their model's "eyes" attachment) where they were looking: the direction the game
	/// gave their body's anim graph (aim_body, in the body's space), which for a player is their view. Their own models
	/// only cast shadows, as in the game, and the field of view is the player's own. Their gun is the first-person one,
	/// doing what they did with it (<see cref="TheaterViewModel"/>).
	/// </summary>
	bool UpdateFirstPerson( TheaterClip.Life life, SkinnedModelRenderer body )
	{
		var root = life.GetRoot( Player.Binder );
		if ( root is null || !TryGetEyes( body, out var eyes ) )
			return false;

		// A seek, or a new pair of eyes, puts the gun straight where it's going too.
		var snap = _snapCamera || !_inFirstPerson;

		HideSoldier( root );

		var look = body.GetVector( "aim_body" );
		var direction = look.IsNearZeroLength ? body.WorldRotation.Forward : body.WorldRotation * look.Normal;
		var rotation = Rotation.LookAt( direction, Vector3.Up );

		// Kept relative to the soldier's root, so the smoothing takes the bob out of the head without trailing a runner.
		var offset = eyes - root.WorldPosition;

		if ( _snapCamera || !_inFirstPerson )
		{
			_snapCamera = false;
			_eyeOffset = offset;
			_eyeRotation = rotation;
		}
		else
		{
			// Faster at a faster replay, so the view keeps up with the soldier.
			var rate = MathF.Max( 1f, IsPaused ? 1f : Speed );
			_eyeOffset = Vector3.Lerp( _eyeOffset, offset, 1f - MathF.Exp( -Time.Delta * EyeSmoothing * rate ) );
			_eyeRotation = Rotation.Slerp( _eyeRotation, rotation, 1f - MathF.Exp( -Time.Delta * LookSmoothing * rate ) );
		}

		_inFirstPerson = true;

		ViewCamera.WorldPosition = root.WorldPosition + _eyeOffset;
		ViewCamera.WorldRotation = _eyeRotation;

		// The gun narrows the field of view as they aim, and its animation moves the camera.
		_gun.Update( life, root, body, _actions, ViewCamera, _position, AnimationRate,
			GameSettingsSystem.Current?.FieldOfView ?? _followFov, snap );

		return true;
	}

	/// <summary> Back from first person: the soldier shows again, without the first-person gun, and the camera has its own field of view. </summary>
	void EndFirstPerson()
	{
		_gun.Clear();
		ShowSoldier();

		if ( !_inFirstPerson )
			return;

		_inFirstPerson = false;
		ViewCamera.FieldOfView = _followFov;
	}

	/// <summary>
	/// Where the soldier's eyes are: their model's "eyes" attachment, else just above the head bone. The attachment is
	/// taken in the body's space and placed where the body is now: its pose is from the last animation update, before
	/// this frame's move, and in world space the view would trail a running soldier by a frame.
	/// </summary>
	static bool TryGetEyes( SkinnedModelRenderer body, out Vector3 eyes )
	{
		if ( body.GetAttachment( "eyes", false ) is { } attachment )
		{
			eyes = body.WorldTransform.PointToWorld( attachment.Position );
			return true;
		}

		if ( body.TryGetBoneTransform( "head", out var head ) )
		{
			eyes = head.Position + Vector3.Up * 4f;
			return true;
		}

		eyes = default;
		return false;
	}

	/// <summary> Leaves only the shadows of the soldier whose eyes the camera is in: their body, clothing and guns. </summary>
	void HideSoldier( GameObject root )
	{
		// Every life's objects are made when the replay loads, so its renderers only need finding once.
		if ( root == _hiddenRoot )
			return;

		ShowSoldier();
		_hiddenRoot = root;

		foreach ( var renderer in root.GetComponentsInChildren<ModelRenderer>( true, true ) )
		{
			if ( renderer.RenderType != ModelRenderer.ShadowRenderType.On )
				continue;

			renderer.RenderType = ModelRenderer.ShadowRenderType.ShadowsOnly;
			_hidden.Add( renderer );
		}
	}

	void ShowSoldier()
	{
		foreach ( var renderer in _hidden )
		{
			if ( renderer.IsValid() )
				renderer.RenderType = ModelRenderer.ShadowRenderType.On;
		}

		_hidden.Clear();
		_hiddenRoot = null;
	}

	/// <summary> The life of <paramref name="person"/> to show at <paramref name="seconds"/>: the living one, else their body. </summary>
	TheaterClip.Life FindLife( Person person, double seconds )
	{
		if ( person is null )
			return null;

		var time = (float)seconds;
		TheaterClip.Life body = null;

		foreach ( var life in _clip.Lives )
		{
			if ( life.Soldier is not { } soldier || KeyOf( soldier ) != person.Key )
				continue;

			if ( soldier.IsAliveAt( time ) )
				return life;

			if ( soldier.IsPresentAt( time ) && (body is null || soldier.Spawned > body.Soldier.Spawned) )
				body = life;
		}

		return body;
	}

	Vector3 GetFocus( SkinnedModelRenderer body, bool alive )
	{
		if ( !_focusBones.TryGetValue( body.Model, out var bone ) )
		{
			var bones = body.Model.Bones;
			bone = bones.GetBone( "spine3" ) ?? bones.GetBone( "spine_2" ) ?? bones.GetBone( "spine2" ) ?? bones.GetBone( "pelvis" );
			_focusBones[body.Model] = bone;
		}

		if ( bone is not null && body.TryGetBoneTransform( bone, out var transform ) )
			return transform.Position + Vector3.Up * (alive ? 10f : 6f);

		return body.WorldPosition + Vector3.Up * (alive ? 56f : 12f);
	}

	static float DeltaDegrees( float from, float to )
	{
		var delta = (to - from) % 360f;
		if ( delta > 180f ) delta -= 360f;
		if ( delta < -180f ) delta += 360f;
		return delta;
	}

	static void HideCursor()
	{
		Input.EnableVirtualCursor = false;
		Mouse.Visible = false;
		Mouse.CursorType = "none";
		Mouse.Visibility = MouseVisibility.Hidden;
	}

	static void ShowCursor()
	{
		Input.EnableVirtualCursor = true;
		Mouse.Visible = true;
		Mouse.CursorType = null;
		Mouse.Visibility = MouseVisibility.Visible;
	}
}
