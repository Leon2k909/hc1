using Sandbox.Diagnostics;

namespace Facepunch;

/// <summary>
/// The bots' shared picture of the match, built once a frame: which bots and players are alive, which teams have a
/// real player on them, and where this machine is looking from. Bots read these instead of each searching the scene,
/// which with a hundred bots added up to thousands of scene walks (and allocations) a frame. It also moves the bots'
/// guns onto their hands (see <see cref="FollowHands"/>) and times the bots for <c>dev_perf</c>.
/// </summary>
public sealed class BotSystem : GameObjectSystem<BotSystem>
{
	/// <summary>
	/// Turns off the bots' level-of-detail savings (thinking less often far from every player, no bone objects, no
	/// effects nobody can see), for comparing with <c>dev_perf</c>. Stored inverted so a hotload leaves the savings on.
	/// Bone objects are set when a bot spawns, so respawn the bots after changing it.
	/// </summary>
	[ConVar( "bot_lod_off", Saved = false )] public static bool LodOff { get; set; }

	public static bool LodEnabled => !LodOff;

	public BotSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.StartUpdate, -100, Refresh, "BotSystem.Refresh" );
		// After UpdateBones, finish both the weapon mount and support arm from the same animated pose.
		Listen( Stage.FinishUpdate, -100, FollowHands, "BotSystem.FollowHands" );
		Listen( Stage.FinishUpdate, 10000, EndFrame, "BotSystem.EndFrame" );
	}

	/// <summary> Every living bot. </summary>
	public List<LightweightCombatBot> AliveBots { get; } = new();

	/// <summary> Every living player pawn, the bots fight these too. </summary>
	public List<PlayerPawn> AlivePawns { get; } = new();

	/// <summary> The living pawns of real people (not bot clients): where the action is. </summary>
	public List<PlayerPawn> AlivePlayers { get; } = new();

	/// <summary> Does <paramref name="team"/> have a connected real player on it, alive or not? </summary>
	public bool TeamHasRealPlayer( Team team ) => _realPlayerTeams.Contains( team );

	/// <summary>
	/// Every real player is down, with a respawn coming (the mode has a respawner running). Bots hold back from fights of
	/// their own until someone's back, so they don't spend the wait bunching up on each other. In a round mode, where
	/// nobody comes back until the next round, this stays false and the bots finish the round.
	/// </summary>
	public bool AwaitingRespawn { get; private set; }

	/// <summary> Where this machine is looking from, for how big things look. </summary>
	public Vector3 ViewPosition { get; private set; }

	/// <summary> Is this machine drawing the scene at all? A server with no screen isn't. </summary>
	public bool HasView => _views.Count > 0;

	/// <summary>
	/// Screen pixels one unit covers one unit away, through the most zoomed camera drawing right now (a scope's
	/// picture-in-picture counts), so a bot's height in pixels is <c>height * this / distance</c>.
	/// </summary>
	public float PixelsPerUnit { get; private set; } = 600f;

	/// <summary> How many pixels tall a standing person <paramref name="distance"/> away looks on this screen. </summary>
	public float ScreenHeightAt( float distance ) => 72f * PixelsPerUnit / MathF.Max( distance, 1f );

	/// <summary> How many pixels tall a standing person at <paramref name="position"/> looks on this screen. </summary>
	public float ScreenHeightOf( Vector3 position ) => ScreenHeightAt( position.Distance( ViewPosition ) );

	private readonly List<LightweightCombatBot> _scratchBots = new();
	private readonly List<PlayerPawn> _scratchPawns = new();
	private readonly List<Client> _scratchClients = new();
	private readonly List<CameraComponent> _scratchCameras = new();
	private readonly HashSet<Team> _realPlayerTeams = new();
	private readonly List<Frustum> _views = new();

	private void Refresh()
	{
		_scratchBots.Clear();
		Scene.GetAll( _scratchBots );
		AliveBots.Clear();
		foreach ( var bot in _scratchBots )
		{
			if ( bot.IsValid() && bot.IsAlive )
				AliveBots.Add( bot );
		}

		_scratchClients.Clear();
		Scene.GetAll( _scratchClients );
		_realPlayerTeams.Clear();
		foreach ( var client in _scratchClients )
		{
			if ( client.IsValid() && client.IsConnected && !client.IsBot )
				_realPlayerTeams.Add( client.Team );
		}

		_scratchPawns.Clear();
		Scene.GetAll( _scratchPawns );
		AlivePawns.Clear();
		AlivePlayers.Clear();
		foreach ( var pawn in _scratchPawns )
		{
			if ( !pawn.IsValid() || pawn.HealthComponent is not { State: LifeState.Alive } )
				continue;

			AlivePawns.Add( pawn );
			if ( !pawn.Client.IsValid() || !pawn.Client.IsBot )
				AlivePlayers.Add( pawn );
		}

		AwaitingRespawn = AlivePlayers.Count == 0 && _realPlayerTeams.Count > 0 && RespawnerRunning();
		UpdateView();
	}

	/// <summary> Is a respawner bringing dead players back right now? Game modes turn theirs on and off by state. </summary>
	private bool RespawnerRunning() => Scene.GetAllComponents<Respawner>().Any( x => x.IsValid() && x.Active );

	private void UpdateView()
	{
		_views.Clear();
		var camera = Scene.Camera;
		if ( !camera.IsValid() )
			return;

		ViewPosition = camera.WorldPosition;
		var best = PixelsPerUnitFor( camera, Screen.Height, Screen.Width / MathF.Max( Screen.Height, 1f ) );
		_views.Add( camera.GetFrustum() );

		// A magnified optic draws the world again through its own narrow camera: through the scope, things look as big
		// as that camera makes them.
		_scratchCameras.Clear();
		Scene.GetAll( _scratchCameras );
		foreach ( var other in _scratchCameras )
		{
			if ( other == camera || !other.IsValid() || !other.Enabled || other.Orthographic || other.RenderTarget is null )
				continue;

			best = MathF.Max( best, PixelsPerUnitFor( other, Screen.Height, 1f ) );
		}

		PixelsPerUnit = best;
	}

	private static float PixelsPerUnitFor( CameraComponent camera, float screenHeight, float aspect )
	{
		var fov = camera.FieldOfView.Clamp( 1f, 170f ).DegreeToRadian();
		var halfHeight = camera.FovAxis == CameraComponent.Axis.Vertical
			? MathF.Tan( fov * 0.5f )
			: MathF.Tan( fov * 0.5f ) / MathF.Max( aspect, 0.1f );
		return screenHeight / (2f * MathF.Max( halfHeight, 0.001f ));
	}

	/// <summary>
	/// Could this machine's view show something <paramref name="radius"/> across at <paramref name="position"/>? With no
	/// camera (a server with no screen) nothing is on screen.
	/// </summary>
	public bool IsOnScreen( Vector3 position, float radius )
	{
		foreach ( var view in _views )
		{
			if ( view.IsInside( position, radius, true ) )
				return true;
		}

		return false;
	}

	/// <summary>
	/// Is an effect at <paramref name="position"/> worth making on this machine: on screen and at least
	/// <paramref name="minPixels"/> tall there (a person's height), or close enough to light up what is on screen?
	/// Always true with <c>bot_lod_off</c>.
	/// </summary>
	public static bool ShouldShowEffect( Vector3 position, float minPixels = 4f, float nearby = 1000f )
	{
		var system = Current;
		if ( !LodEnabled || system is null )
			return true;
		if ( !system.HasView )
			return false;

		var distance = position.Distance( system.ViewPosition );
		if ( distance < nearby )
			return true;

		return system.ScreenHeightAt( distance ) >= minPixels && system.IsOnScreen( position, 64f );
	}

	/// <summary>
	/// Would <paramref name="sound"/> played at <paramref name="position"/> be heard on this machine at all? Past its own
	/// <see cref="SoundEvent.Distance"/> (330 m for most guns) it's silent anyway, and every far fight's shots were a
	/// voice each for the mixer. The listener is on the camera. Always true with <c>bot_lod_off</c>.
	/// </summary>
	public static bool CanHear( SoundEvent sound, Vector3 position )
	{
		var system = Current;
		if ( !LodEnabled || system is null || sound is null || !sound.DistanceAttenuation )
			return true;

		return system.HasView && position.Distance( system.ViewPosition ) < sound.Distance;
	}

	/// <summary> The distance from <paramref name="position"/> to the nearest living real player, or MaxValue with none. </summary>
	public float DistanceToNearestPlayer( Vector3 position )
	{
		var best = float.MaxValue;
		foreach ( var player in AlivePlayers )
			best = MathF.Min( best, player.WorldPosition.DistanceSquared( position ) );

		return best == float.MaxValue ? best : MathF.Sqrt( best );
	}

	/// <summary>
	/// The distance from <paramref name="position"/> to the nearest living real player or this machine's camera (a dead
	/// player spectating counts), or MaxValue with neither.
	/// </summary>
	public float DistanceToNearestViewer( Vector3 position )
	{
		var distance = DistanceToNearestPlayer( position );
		return HasView ? MathF.Min( distance, position.Distance( ViewPosition ) ) : distance;
	}

	/// <summary>
	/// Bots have no bone objects (a GameObject per bone, moved every frame: a hundred bots made ten thousand), so each
	/// one's gun is moved onto its hand here, once the frame's animation is done.
	/// </summary>
	private void FollowHands()
	{
		foreach ( var bot in AliveBots )
		{
			if ( bot.IsValid() )
				bot.FinishWeaponPose();
		}
	}

	#region dev_perf

	private double _botMicroseconds;
	private double _thinkMicroseconds;
	private int _sampleFrames;
	private int _sampleTarget;
	private readonly List<float> _frameMs = new();
	private readonly List<float> _botMs = new();
	private long _bytes;
	private int _gen0, _gen1, _gen2;
	private int _minBots = int.MaxValue, _maxBots;
	private double _thinkTotal;

	/// <summary> Time spent in bot components this frame. </summary>
	public void AddBotTime( double microseconds ) => _botMicroseconds += microseconds;

	/// <summary> Of that, time spent thinking (host only). </summary>
	public void AddThinkTime( double microseconds ) => _thinkMicroseconds += microseconds;

	/// <summary> Record the next <paramref name="frames"/> frames and log a report. </summary>
	public void StartSampling( int frames )
	{
		_sampleTarget = Math.Max( 10, frames );
		_sampleFrames = 0;
		_frameMs.Clear();
		_botMs.Clear();
		_bytes = 0;
		_gen0 = _gen1 = _gen2 = 0;
		_thinkTotal = 0;
		_minBots = int.MaxValue;
		_maxBots = 0;
		Log.Info( $"dev_perf: sampling {_sampleTarget} frames with {AliveBots.Count} bots alive (bot LOD {(LodEnabled ? "on" : "off")})" );
	}

	private void EndFrame()
	{
		var botMs = (float)(_botMicroseconds / 1000.0);
		var thinkMs = _thinkMicroseconds / 1000.0;
		_botMicroseconds = 0;
		_thinkMicroseconds = 0;

		if ( _sampleTarget <= 0 )
			return;

		_frameMs.Add( RealTime.Delta * 1000f );
		_botMs.Add( botMs );
		_thinkTotal += thinkMs;
		_bytes += PerformanceStats.BytesAllocated;
		_gen0 += PerformanceStats.Gen0Collections;
		_gen1 += PerformanceStats.Gen1Collections;
		_gen2 += PerformanceStats.Gen2Collections;
		_minBots = Math.Min( _minBots, AliveBots.Count );
		_maxBots = Math.Max( _maxBots, AliveBots.Count );

		if ( ++_sampleFrames < _sampleTarget )
			return;

		_sampleTarget = 0;
		Report();
	}

	private void Report()
	{
		var frames = _frameMs.Count;
		var sorted = _frameMs.OrderBy( x => x ).ToList();
		float Percentile( float p ) => sorted[Math.Clamp( (int)(p * (frames - 1)), 0, frames - 1 )];
		var avg = _frameMs.Average();

		var lines = new List<string>
		{
			$"dev_perf over {frames} frames, bots alive {_minBots}-{_maxBots}, players {AlivePlayers.Count}, bot LOD {(LodEnabled ? "on" : "off")}",
			$"  frame ms: avg {avg:0.00} ({1000f / avg:0} fps)  p50 {Percentile( 0.5f ):0.00}  p95 {Percentile( 0.95f ):0.00}  p99 {Percentile( 0.99f ):0.00}  max {sorted[^1]:0.00}",
			$"  bot components ms/frame: avg {_botMs.Average():0.000}  max {_botMs.Max():0.000}  (thinking {_thinkTotal / frames:0.000})",
			$"  managed alloc {_bytes / (double)frames / 1024.0:0.0} KB/frame, GCs gen0 {_gen0} gen1 {_gen1} gen2 {_gen2}"
		};

		var history = Math.Min( frames, 200 );
		lines.Add( $"  engine timings, avg ms over the last {history} frames:" );
		foreach ( var timing in new[]
		{
			PerformanceStats.Timings.Update, PerformanceStats.Timings.Animation, PerformanceStats.Timings.Physics,
			PerformanceStats.Timings.NavMesh, PerformanceStats.Timings.Network, PerformanceStats.Timings.Particles,
			PerformanceStats.Timings.Audio, PerformanceStats.Timings.Ui, PerformanceStats.Timings.Render,
			PerformanceStats.Timings.Async, PerformanceStats.Timings.Editor, PerformanceStats.Timings.GcPause
		} )
		{
			var metric = timing.GetMetric( history );
			lines.Add( $"    {timing.Name,-10} avg {metric.Avg:0.000}  max {metric.Max:0.000}" );
		}

		Log.Info( string.Join( "\n", lines ) );
	}

	#endregion
}
