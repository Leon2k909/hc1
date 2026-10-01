using Sandbox.Events;
using Sandbox.Navigation;

namespace Facepunch;

/// <summary>
/// 1v1 and 2v2 Skirmish on a big map: the fight is held to a circle of it, as a small mode's map would be. Belltower's
/// team spawns are 104 m apart and Flatgrass's 211 m, so one bot and one player spent most of a match looking for each
/// other. On a map whose team spawns are already close (Innocent Hotel's) the arena stays off.
/// <para>
/// The host picks the circle once, when the mode has started and the navmesh is ready: round one of the map's
/// objective spots (its fight places) or the middle between the teams, wherever the navmesh gives it room. Its spawns
/// are a ring inside it, shared by both teams and picked away from the enemy (<see cref="PickSpawn"/>). A player
/// outside it gets the play area's "Return to the AO" (<see cref="PlayerPawn"/>), the radar draws it, and bots keep
/// their moves inside it (<see cref="Clamp"/>).
/// </para>
/// </summary>
public sealed class SkirmishArena : Component, IGameEventHandler<GamemodeInitializedEvent>
{
	/// <summary> The circle's radius: 1v1's 1000 (~25 m), 2v2's 1300 (~33 m), about a small mode's map. </summary>
	[Property] public float Radius { get; set; } = 1000f;

	/// <summary> The arena is only used where the teams' spawns are further apart than this many radii. </summary>
	[Property] public float BigMapSeparation { get; set; } = 2.2f;

	/// <summary> Whether the match is held to the circle. Synced, for the radar and the warning. </summary>
	[Sync( SyncFlags.FromHost )] public bool IsActive { get; private set; }
	[Sync( SyncFlags.FromHost )] public Vector3 Centre { get; private set; }
	[Sync( SyncFlags.FromHost )] public float ActiveRadius { get; private set; }

	/// <summary> The running arena, if this mode has one and it's in use. </summary>
	public static SkirmishArena Active => _current.IsValid() && _current.IsActive ? _current : null;

	private static SkirmishArena _current;

	/// <summary> <see cref="Active"/>, once the circle has been picked if that's still to do: for spawning. Host only. </summary>
	public static SkirmishArena Settled
	{
		get
		{
			if ( _current.IsValid() )
				_current.Settle();

			return Active;
		}
	}

	/// <summary> Its spawns, the host's only. </summary>
	private readonly List<Transform> _spawns = new();
	/// <summary> Picked, or found to be not needed on this map: either way it isn't looked at again. </summary>
	private bool _settled;
	/// <summary>
	/// The mode has started, and the map's objects for other modes are switched off (<see cref="GameModeObject"/>):
	/// before that, Belltower's Retakes spawns counted too, and made its teams' spawns look about half as far apart.
	/// </summary>
	private bool _modeStarted;

	/// <summary> Spawns on the ring, out from the middle by this share of the radius. </summary>
	private const float RingShare = 0.72f;
	private const int RingTries = 16;
	/// <summary> A spawn no closer than this to another, so two players never start in each other. </summary>
	private const float SpawnSpacing = 220f;
	private const int MinSpawns = 6;
	/// <summary> Bots keep their moves this far inside the edge. </summary>
	private const float EdgeMargin = 96f;

	protected override void OnEnabled() => _current = this;

	protected override void OnDisabled()
	{
		if ( _current == this )
			_current = null;
	}

	void IGameEventHandler<GamemodeInitializedEvent>.OnGameEvent( GamemodeInitializedEvent eventArgs ) => _modeStarted = true;

	protected override void OnUpdate()
	{
		// The first spawns may have come before the mode started, or while the navmesh was still building.
		if ( !_settled )
			Settle();
	}

	/// <summary> Is <paramref name="position"/> inside the circle? Height doesn't count. </summary>
	public bool Contains( Vector3 position ) =>
		position.WithZ( 0f ).DistanceSquared( Centre.WithZ( 0f ) ) <= ActiveRadius * ActiveRadius;

	/// <summary>
	/// <paramref name="position"/>, or if it's outside the arena (or near its edge), the nearest point well inside it.
	/// Every point a bot heads for goes through here (its <c>NavPoint</c>).
	/// </summary>
	public static Vector3 Clamp( Vector3 position )
	{
		if ( Active is not { } arena )
			return position;

		var offset = (position - arena.Centre).WithZ( 0f );
		var limit = MathF.Max( 0f, arena.ActiveRadius - EdgeMargin );
		if ( offset.Length <= limit )
			return position;

		return (arena.Centre + offset.Normal * limit).WithZ( position.z );
	}

	/// <summary> Its spawns, for anything that lists spawn points (<see cref="GameUtils.GetSpawnPoints(Team,string[])"/>). Host only. </summary>
	public IEnumerable<SpawnPointInfo> SpawnPoints => _spawns.Select( x => new SpawnPointInfo( x, Array.Empty<string>() ) );

	/// <summary>
	/// The spawn for someone on <paramref name="team"/>: as far from the enemy as the ring allows and out of their sight,
	/// near a living teammate if there is one, and never on someone. Host only.
	/// </summary>
	public SpawnPointInfo PickSpawn( Team team, GameObject spawning = null )
	{
		var people = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.GameObject != spawning && x.HealthComponent.State == LifeState.Alive )
			.Select( x => (Position: x.WorldPosition, Eyes: x.EyePosition, x.Team) )
			.Concat( GameUtils.LightweightBots
				.Where( x => x.IsValid() && x.GameObject != spawning && x.IsAlive )
				.Select( x => (Position: x.WorldPosition, Eyes: x.EyePosition, x.Team) ) )
			.ToArray();

		var best = float.NegativeInfinity;
		var chosen = _spawns.FirstOrDefault();
		foreach ( var spawn in _spawns )
		{
			var position = spawn.Position;
			var nearestEnemy = ActiveRadius * 2f;
			var nearestMate = float.MaxValue;
			var seen = false;
			var occupied = false;
			foreach ( var person in people )
			{
				var distance = person.Position.Distance( position );
				occupied |= distance < 96f;
				if ( team != Team.Unassigned && person.Team == team )
				{
					nearestMate = MathF.Min( nearestMate, distance );
					continue;
				}

				nearestEnemy = MathF.Min( nearestEnemy, distance );
				seen |= Sees( person.Eyes, position );
			}

			// Away from the enemy and out of their sight first; then with a teammate, as a pair starts together.
			var score = nearestEnemy
				- (seen ? 3000f : 0f)
				- (occupied ? 10000f : 0f)
				- (nearestMate < float.MaxValue ? nearestMate * 0.3f : 0f)
				+ Game.Random.Float( 0f, 60f );
			if ( score <= best )
				continue;

			best = score;
			chosen = spawn;
		}

		return new SpawnPointInfo( chosen, new[] { "arena" } );
	}

	private bool Sees( Vector3 eyes, Vector3 position ) => !Scene.Trace.Ray( eyes, position + Vector3.Up * 64f )
		.WithoutTags( "player", "ragdoll", "trigger", "playerclip", "movement", LightweightBotManager.BotTag, BreakableGlass.Tag )
		.Run().Hit;

	/// <summary>
	/// Picks the circle, if the map needs one and it hasn't been done. Host only; anywhere a spawn is wanted calls it
	/// first, since a mode's components start in no fixed order.
	/// </summary>
	public void Settle()
	{
		if ( _settled || !_modeStarted || IsProxy || (Networking.IsActive && !Networking.IsHost) )
			return;
		if ( Scene.NavMesh is not { IsEnabled: true } navMesh || navMesh.IsGenerating )
			return;

		_settled = true;

		var teamSpawns = Scene.GetAllComponents<TeamSpawnPoint>()
			.Where( x => x.Team != Team.Unassigned )
			.GroupBy( x => x.Team )
			.ToDictionary( x => x.Key, x => x.Select( s => s.WorldPosition ).ToArray() );
		var middle = Vector3.Zero;
		var anchor = (Vector3?)null;
		if ( teamSpawns.Count == 2 )
		{
			var centroids = teamSpawns.Values.Select( Average ).ToArray();
			var separation = centroids[0].WithZ( 0f ).Distance( centroids[1].WithZ( 0f ) );
			if ( separation <= Radius * BigMapSeparation )
			{
				Log.Info( $"Skirmish arena: not needed, the team spawns are {separation:0} apart" );
				return;
			}

			middle = (centroids[0] + centroids[1]) * 0.5f;
			anchor = teamSpawns.Values.First().First();
		}

		var candidates = Scene.GetAllComponents<ObjectiveSpot>()
			.Select( x => x.WorldPosition )
			.Append( middle )
			.ToList();
		for ( var i = 0; i < 8; i++ )
		{
			if ( navMesh.GetRandomPoint( middle, Radius * 3f ) is { } point )
				candidates.Add( point );
		}

		// Several good arenas: any of the best few, so a map isn't always fought over in the same place.
		var found = new List<(Vector3 Centre, List<Transform> Spawns, float Score)>();
		foreach ( var candidate in candidates.Shuffle() )
		{
			if ( TryArena( candidate, anchor, out var centre, out var spawns, out var score ) )
				found.Add( (centre, spawns, score) );
		}

		if ( found.Count == 0 )
		{
			Log.Warning( "Skirmish arena: no room for one on this map, so the match uses the whole of it" );
			return;
		}

		var pick = Random.Shared.FromArray( found.OrderByDescending( x => x.Score ).Take( 3 ).ToArray() );
		_spawns.Clear();
		_spawns.AddRange( pick.Spawns );
		Centre = pick.Centre;
		ActiveRadius = Radius;
		IsActive = true;
		Log.Info( $"Skirmish arena: {Radius:0} round {Centre}, {_spawns.Count} spawns (of {found.Count} places tried that fit)" );

		MoveEveryoneIn();
	}

	/// <summary>
	/// An arena round <paramref name="candidate"/>: its middle on the navmesh (joined to the team spawns', not up on a
	/// roof), and at least <see cref="MinSpawns"/> spawns on a ring inside it, each walkable to the middle without
	/// leaving it. The score is the spawns, plus a bonus for two on opposite sides that can't see each other.
	/// </summary>
	private bool TryArena( Vector3 candidate, Vector3? anchor, out Vector3 centre, out List<Transform> spawns, out float score )
	{
		spawns = new List<Transform>();
		score = 0f;
		centre = default;
		var navMesh = Scene.NavMesh;
		if ( navMesh.GetClosestPoint( candidate, 200f ) is not { } middle )
			return false;

		centre = middle;
		if ( anchor is { } spawn && navMesh.GetClosestPoint( spawn, 200f ) is { } start
		     && navMesh.CalculatePath( new CalculatePathRequest { Start = start, Target = middle } ).Status != NavMeshPathStatus.Complete )
			return false;

		var turn = Game.Random.Float( 0f, 360f / RingTries );
		for ( var i = 0; i < RingTries; i++ )
		{
			var angle = (turn + i * 360f / RingTries).DegreeToRadian();
			var target = middle + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * Radius * RingShare;
			if ( navMesh.GetClosestPoint( target, 200f ) is not { } point )
				continue;

			var reach = point.WithZ( 0f ).Distance( middle.WithZ( 0f ) );
			if ( reach < Radius * 0.45f || reach > Radius * 0.85f )
				continue;
			if ( spawns.Any( x => x.Position.Distance( point ) < SpawnSpacing ) )
				continue;
			if ( !WalksInside( point, middle, reach ) || !HasRoom( point ) )
				continue;

			spawns.Add( new Transform( point, Rotation.LookAt( (middle - point).WithZ( 0f ) ) ) );
		}

		if ( spawns.Count < MinSpawns )
			return false;

		score = spawns.Count;
		foreach ( var a in spawns )
		{
			var hidden = spawns.Any( b => b.Position.WithZ( 0f ).Distance( a.Position.WithZ( 0f ) ) > Radius * 1.2f
				&& !Sees( a.Position + Vector3.Up * 64f, b.Position ) );
			if ( hidden )
				score += 1f;
		}

		return true;
	}

	/// <summary> A navmesh route from <paramref name="from"/> to the middle that stays in the circle and isn't a long way round. </summary>
	private bool WalksInside( Vector3 from, Vector3 middle, float straight )
	{
		var path = Scene.NavMesh.CalculatePath( new CalculatePathRequest { Start = from, Target = middle } );
		if ( path.Status != NavMeshPathStatus.Complete || path.Points is null )
			return false;

		var length = 0f;
		var previous = from;
		foreach ( var point in path.Points )
		{
			if ( point.Position.WithZ( 0f ).Distance( middle.WithZ( 0f ) ) > Radius * 0.95f )
				return false;

			length += previous.Distance( point.Position );
			previous = point.Position;
		}

		return length <= MathF.Max( straight * 2f, 400f );
	}

	/// <summary> Standing room for a player there. </summary>
	private bool HasRoom( Vector3 point ) => !Scene.Trace.Box( new BBox( new Vector3( -16f, -16f, 0f ), new Vector3( 16f, 16f, 72f ) ),
			point + Vector3.Up * 4f, point + Vector3.Up * 4f )
		.WithoutTags( "player", "ragdoll", "trigger", "playerclip", "movement", LightweightBotManager.BotTag, BreakableGlass.Tag )
		.Run().Hit;

	/// <summary>
	/// Anyone spawned before the circle was picked (before the mode started, or while the navmesh was still building):
	/// players are moved to its spawns, and bots outside it are taken off, for the fill to put back inside.
	/// </summary>
	private void MoveEveryoneIn()
	{
		foreach ( var player in GameUtils.AllPlayers )
		{
			if ( player.PlayerPawn is { } pawn && pawn.IsValid() && pawn.HealthComponent.State == LifeState.Alive && !Contains( pawn.WorldPosition ) )
				player.Respawn( false );
		}

		foreach ( var bot in GameUtils.LightweightBots.ToArray() )
		{
			if ( bot.IsValid() && bot.IsAlive && !Contains( bot.WorldPosition ) )
				bot.GameObject.Destroy();
		}
	}

	private static Vector3 Average( Vector3[] points ) =>
		points.Aggregate( Vector3.Zero, ( sum, x ) => sum + x ) / MathF.Max( 1, points.Length );
}
