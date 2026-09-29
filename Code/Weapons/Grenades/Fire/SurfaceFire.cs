namespace Facepunch;

/// <summary> Who lit a fire, so its kills go to them (<see cref="SurfaceFire"/>, <see cref="ThermiteGrenade"/>). </summary>
public sealed class FireSource
{
	public PlayerPawn Pawn { get; init; }
	public Client Client { get; init; }

	/// <summary> The thrower's pawn now: someone who died and came back still gets the kills. </summary>
	public PlayerPawn Attacker => Client.IsValid() && Client.PlayerPawn.IsValid() ? Client.PlayerPawn
		: Pawn.IsValid() ? Pawn : null;

	public static FireSource From( PlayerPawn pawn ) => new() { Pawn = pawn, Client = pawn.IsValid() ? pawn.Client : null };
}

/// <summary>
/// Fire on the ground: grass, floorboards and upholstery that thermite (<see cref="ThermiteGrenade"/>) lit. One per scene,
/// made on the host by <see cref="Ensure"/> and networked, like <see cref="WorldWind"/>.
/// <para>
/// The host runs the fire on a grid of cells about a metre across (<see cref="CellSize"/>). Cured grass carries a running
/// fire: each cell that lights works out when each of its 16 neighbours will catch, from how fast the fire runs that way
/// (<see cref="FireFuels"/>: with the wind, across it or against it, up or down the slope), and the earliest catches first
/// (Finney's minimum travel time method). Other fuels only burn where they're lit. A cell burns while the front crosses
/// it and for its flames' residence time after, then it's burnt out, and a fire with nothing left to burn goes out.
/// </para>
/// <para>
/// The host sends each cell to every machine as it lights (<see cref="Receive"/>, which also runs on the host), so every
/// machine has the same list of burning cells: it draws them (SurfaceFire.Render.cs), and the host works out the heat
/// from them (SurfaceFire.Heat.cs). Where they burn out, the ground is left burnt (SurfaceFire.Terrain.cs, and scorch
/// decals).
/// </para>
/// </summary>
[Title( "Surface Fire" ), Category( "Environment" ), Icon( "local_fire_department" )]
public sealed partial class SurfaceFire : Component, IDescription
{
	/// <summary> The grid's cells, about a metre across. </summary>
	public const float CellSize = 40f;

	/// <summary> Floors this far apart are different cells, so a fire upstairs isn't one downstairs. </summary>
	private const float LayerHeight = 100f;

	/// <summary> Enough for a burn of about 6 ha, far past anything a match sees; stops a runaway one. </summary>
	private const int MaxLitCells = 60000;
	private const int MaxProbedCells = 250000;
	private const int MaxLitPerUpdate = 150;

	/// <summary> A backing fire crawls: a cell burns this long at most while the front crosses it. </summary>
	private const float MaxCrossTime = 120f;

	/// <summary> m/s: slower than this, the fire goes out that way. </summary>
	private const float SpreadFloor = 0.002f;

	/// <summary> A wall this high between two cells stops the fire. </summary>
	private const float BarrierHeight = 20f;

	/// <summary> How far above and below a burning cell its neighbours' ground is looked for. </summary>
	private const float ProbeUp = 64f;
	private const float ProbeDown = 160f;

	private const float SendInterval = 0.1f;
	private const int RecordsPerMessage = 400;

	string IDescription.DisplayName => "Fire";

	// Only thermite lights one, so the kill feed shows the grenade that did.
	string IDescription.Icon => "ui/weapons/grenades/fire_grenade_01.png";

	/// <summary> The 8 cells around one, then the 8 a knight's move away, so a fire isn't square or diamond-shaped. </summary>
	private static readonly (int X, int Y)[] Neighbours =
	{
		(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1),
		(2, 1), (1, 2), (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2), (2, -1),
	};

	private struct Cell
	{
		public Vector3 Ground;
		public FireFuel Fuel;
		public bool Lit;
		public FireSource Source;
	}

	private struct Arrival
	{
		public float Time;
		public long Key;
		public float Rate;
		public FireSource Source;
	}

	/// <summary> A lit cell, as sent to every machine. </summary>
	private struct Record
	{
		public long Key;
		public Vector3 Ground;
		/// <summary> When it lit, in the host's <see cref="Time.Now"/>: it's sent as how long ago. </summary>
		public float LitAt;
		public float Duration;
		public float Flame;
		public FireFuel Fuel;
	}

	// Host only.
	private readonly Dictionary<long, Cell> _cells = new();
	private readonly Dictionary<long, long> _probes = new();
	private readonly List<Arrival> _heap = new();
	private readonly List<Record> _outbox = new();
	private int _litCount;
	private TimeSince _sinceSent;
	private WorldWind _wind;

	/// <summary> The scene's fire, if anything has lit one. </summary>
	public static SurfaceFire Get( Scene scene ) => scene?.GetAllComponents<SurfaceFire>().FirstOrDefault();

	/// <summary> Host: the scene's fire, made if there isn't one yet. </summary>
	public static SurfaceFire Ensure( Scene scene )
	{
		var existing = Get( scene );
		if ( existing.IsValid() || !Networking.IsHost || scene is null ) return existing;

		var go = new GameObject( scene, true, "Surface Fire" );
		go.Flags |= GameObjectFlags.NotSaved;
		var fire = go.AddComponent<SurfaceFire>();
		go.AddComponent<DestroyBetweenRounds>();
		go.NetworkSpawn();
		return fire;
	}

	protected override void OnStart()
	{
		// A late joiner asks for what's burning now, and what has burnt.
		if ( IsProxy ) RequestSnapshot();
	}

	protected override void OnUpdate()
	{
		if ( Networking.IsHost )
		{
			RunFire();
			SendLit();
			UpdateHeat();
		}

		ExpireBurning();

		if ( !Application.IsDedicatedServer )
		{
			Render();
			FlushTerrain();
		}
	}

	protected override void OnDestroy()
	{
		DestroyVisuals();
	}

	/// <summary>
	/// Host: light whatever burns on the ground at <paramref name="point"/>, which catches with the given chance.
	/// <paramref name="minBurn"/> keeps it burning at least that long: something burning on it keeps it alight.
	/// Returns true if it lit (or was already alight).
	/// </summary>
	public bool Ignite( Vector3 point, FireSource source, float chance = 1f, float minBurn = 0f )
	{
		if ( !Networking.IsHost || _litCount >= MaxLitCells ) return false;
		return TryCellAt( point, out var key ) && IgniteCell( key, source, chance, minBurn );
	}

	/// <summary>
	/// Host: a drop of burning metal lands at <paramref name="point"/>, and lights what's there with that fuel's chance
	/// (<see cref="FireFuels.Behaviour.SpatterIgnition"/>).
	/// </summary>
	public bool Spatter( Vector3 point, FireSource source )
	{
		if ( !Networking.IsHost || _litCount >= MaxLitCells ) return false;
		if ( !TryCellAt( point, out var key ) ) return false;
		return IgniteCell( key, source, FireFuels.Of( _cells[key].Fuel ).SpatterIgnition, 0f );
	}

	private bool IgniteCell( long key, FireSource source, float chance, float minBurn )
	{
		var cell = _cells[key];
		if ( cell.Fuel == FireFuel.None ) return false;

		if ( cell.Lit )
		{
			if ( minBurn > 0f ) KeepBurning( key, minBurn );
			return true;
		}

		if ( chance < 1f && Game.Random.Float() >= chance ) return false;

		// A spot fire in grass starts slowly: until it has grown into a front, it burns like a flank.
		var rate = 0f;
		if ( FireFuels.Spreads( cell.Fuel ) )
		{
			var windKmh = WindKmh( cell.Ground, out _ );
			rate = FireFuels.RateAt( FireFuels.HeadRate( cell.Fuel, windKmh ), FireFuels.LengthToBreadth( windKmh ), 0f );
		}

		Light( key, cell, Time.Now, rate, source, minBurn );
		return true;
	}

	/// <summary> Anything burning within <paramref name="radius"/> of a point: flames on the ground or burning thermite. </summary>
	public static bool IsBurningNear( Scene scene, Vector3 point, float radius )
	{
		var radiusSq = radius * radius;
		foreach ( var grenade in scene.GetAllComponents<ThermiteGrenade>() )
		{
			if ( grenade.IsBurning && grenade.WorldPosition.DistanceSquared( point ) < radiusSq )
				return true;
		}

		var fire = Get( scene );
		if ( !fire.IsValid() ) return false;

		foreach ( var burning in fire._burning )
		{
			if ( burning.Ground.DistanceSquared( point ) < radiusSq )
				return true;
		}

		return false;
	}

	private void Light( long key, Cell cell, float litAt, float rate, FireSource source, float minBurn )
	{
		cell.Lit = true;
		cell.Source = source;
		_cells[key] = cell;
		_litCount++;

		var behaviour = FireFuels.Of( cell.Fuel );
		var spreads = FireFuels.Spreads( cell.Fuel );
		var duration = spreads
			? MathF.Min( CellSize / FireFuels.Metre / MathF.Max( rate, SpreadFloor ), MaxCrossTime ) + behaviour.Residence
			: behaviour.PatchBurn;
		var flame = spreads ? FireFuels.FlameLength( cell.Fuel, rate ) : behaviour.PatchFlame;

		_outbox.Add( new Record
		{
			Key = key,
			Ground = cell.Ground,
			LitAt = MathF.Min( litAt, Time.Now ),
			Duration = MathF.Max( duration, minBurn ),
			Flame = flame,
			Fuel = cell.Fuel,
		} );

		if ( spreads ) SpreadFrom( key, cell, litAt );
	}

	/// <summary> Something burning on a lit cell (thermite) keeps it alight until then. </summary>
	private void KeepBurning( long key, float minBurn )
	{
		var index = _burningIndex.GetValueOrDefault( key, -1 );
		if ( index < 0 ) return;

		var burning = _burning[index];
		var left = burning.LitAt + burning.Duration - Time.Now;
		if ( left >= minBurn ) return;

		_outbox.Add( new Record
		{
			Key = key,
			Ground = burning.Ground,
			LitAt = burning.LitAt,
			Duration = burning.Duration + (minBurn - left),
			Flame = burning.Flame,
			Fuel = burning.Fuel,
		} );
	}

	/// <summary> When each neighbour of a cell that lit at <paramref name="litAt"/> will catch from it. </summary>
	private void SpreadFrom( long key, Cell cell, float litAt )
	{
		if ( _cells.Count >= MaxProbedCells ) return;

		var (ix, iy, _) = Unpack( key );
		var windKmh = WindKmh( cell.Ground, out var windDirection );
		var lengthToBreadth = FireFuels.LengthToBreadth( windKmh );

		foreach ( var (dx, dy) in Neighbours )
		{
			// A knight's move jumps between two cells: both have to carry the fire.
			if ( Math.Abs( dx ) + Math.Abs( dy ) == 3 )
			{
				var (ax, ay, bx, by) = Math.Abs( dx ) == 2 ? (dx / 2, 0, dx / 2, dy) : (0, dy / 2, dx, dy / 2);
				if ( !CarriesFire( ix + ax, iy + ay, cell.Ground.z ) || !CarriesFire( ix + bx, iy + by, cell.Ground.z ) )
					continue;
			}

			if ( !TryProbe( ix + dx, iy + dy, cell.Ground.z, out var nextKey ) ) continue;

			var next = _cells[nextKey];
			if ( next.Lit || !FireFuels.Spreads( next.Fuel ) ) continue;

			var offset = next.Ground - cell.Ground;
			var run = offset.WithZ( 0 ).Length;
			if ( run < 1f ) continue;

			var slope = MathF.Atan2( offset.z, run ).RadianToDegree();
			var cosFromWind = windDirection.IsNearZeroLength ? 0f : Vector3.Dot( offset.WithZ( 0 ) / run, windDirection );
			var rate = FireFuels.RateAt( FireFuels.HeadRate( next.Fuel, windKmh ), lengthToBreadth, cosFromWind )
				* FireFuels.SlopeFactor( slope );
			if ( rate < SpreadFloor ) continue;
			if ( IsBarrier( cell.Ground, next.Ground ) ) continue;

			Push( new Arrival
			{
				Time = litAt + offset.Length / FireFuels.Metre / rate,
				Key = nextKey,
				Rate = rate,
				Source = cell.Source,
			} );
		}
	}

	private bool CarriesFire( int ix, int iy, float fromZ ) =>
		TryProbe( ix, iy, fromZ, out var key ) && FireFuels.Spreads( _cells[key].Fuel );

	/// <summary> Host: light the cells whose time has come. </summary>
	private void RunFire()
	{
		var now = Time.Now;
		var lit = 0;

		while ( _heap.Count > 0 && _heap[0].Time <= now && lit < MaxLitPerUpdate )
		{
			var arrival = Pop();
			if ( !_cells.TryGetValue( arrival.Key, out var cell ) || cell.Lit ) continue;

			if ( _litCount >= MaxLitCells )
			{
				_heap.Clear();
				break;
			}

			Light( arrival.Key, cell, arrival.Time, arrival.Rate, arrival.Source, 0f );
			lit++;
		}
	}

	/// <summary> The 2 m wind here, as the 10 m wind in km/h the fire models use, and which way it blows. </summary>
	private float WindKmh( Vector3 position, out Vector3 direction )
	{
		if ( !_wind.IsValid() ) _wind = WorldWind.Ensure( Scene );

		var wind = _wind.IsValid() && _wind.Active
			? _wind.Sample( position ).WithZ( 0 ) / WorldWind.UnitsPerMetre
			: Vector3.Zero;
		var speed = wind.Length;
		direction = speed > 0.01f ? wind / speed : Vector3.Zero;
		return speed * 3.6f / 0.723f;
	}

	private bool IsBarrier( Vector3 from, Vector3 to ) =>
		Trace( from + Vector3.Up * BarrierHeight, to + Vector3.Up * BarrierHeight ).Hit;

	private SceneTraceResult Trace( Vector3 from, Vector3 to ) => Scene.Trace.Ray( from, to )
		.IgnoreDynamic()
		.WithoutTags( "player", "trigger", "playerclip", "clutter", "ragdoll", "corpse", "grenade", "particles", "movement", "enemy" )
		.Run();

	/// <summary> The cell a point on the ground is in, found and classified if it hasn't been yet. </summary>
	private bool TryCellAt( Vector3 point, out long key )
	{
		var tr = Trace( point + Vector3.Up * 16f, point + Vector3.Down * 96f );
		key = 0;
		if ( !tr.Hit || tr.StartedSolid ) return false;

		key = KeyAt( tr.HitPosition );
		if ( !_cells.ContainsKey( key ) )
			_cells[key] = new Cell { Ground = tr.HitPosition, Fuel = FireFuels.Classify( tr ) };
		return true;
	}

	/// <summary>
	/// The cell in column (ix, iy) under a fire at height <paramref name="fromZ"/>: its ground is looked for once from each
	/// floor's height, and remembered.
	/// </summary>
	private bool TryProbe( int ix, int iy, float fromZ, out long key )
	{
		var probeKey = Pack( ix, iy, FloorToInt( fromZ / LayerHeight ) );
		if ( _probes.TryGetValue( probeKey, out key ) ) return key != long.MinValue;

		var centre = new Vector3( (ix + 0.5f) * CellSize, (iy + 0.5f) * CellSize, fromZ );
		var tr = Trace( centre + Vector3.Up * ProbeUp, centre + Vector3.Down * ProbeDown );
		if ( !tr.Hit || tr.StartedSolid )
		{
			_probes[probeKey] = key = long.MinValue;
			return false;
		}

		key = Pack( ix, iy, FloorToInt( tr.HitPosition.z / LayerHeight ) );
		if ( !_cells.ContainsKey( key ) )
			_cells[key] = new Cell { Ground = tr.HitPosition, Fuel = FireFuels.Classify( tr ) };

		_probes[probeKey] = key;
		return true;
	}

	private static int FloorToInt( float value ) => (int)MathF.Floor( value );

	/// <summary> Integer division rounding down, so -1 / 6 is -1, as the grid's cells go. </summary>
	private static int FloorDiv( int value, int divisor ) => value >= 0 ? value / divisor : (value - divisor + 1) / divisor;

	private static long KeyAt( Vector3 point ) =>
		Pack( FloorToInt( point.x / CellSize ), FloorToInt( point.y / CellSize ), FloorToInt( point.z / LayerHeight ) );

	/// <summary> 21 bits each: ±42 km across and ±100 km up, far beyond any map. </summary>
	private static long Pack( int ix, int iy, int iz ) =>
		((long)(ix & 0x1FFFFF) << 42) | ((long)(iy & 0x1FFFFF) << 21) | (long)(iz & 0x1FFFFF);

	private static (int X, int Y, int Z) Unpack( long key )
	{
		static int Signed( long bits ) => (int)(bits << 43 >> 43);
		return (Signed( key >> 42 ), Signed( key >> 21 ), Signed( key ));
	}

	// A binary heap of arrivals, soonest first.
	private void Push( Arrival arrival )
	{
		_heap.Add( arrival );
		var i = _heap.Count - 1;
		while ( i > 0 )
		{
			var parent = (i - 1) / 2;
			if ( _heap[parent].Time <= arrival.Time ) break;
			_heap[i] = _heap[parent];
			i = parent;
		}

		_heap[i] = arrival;
	}

	private Arrival Pop()
	{
		var top = _heap[0];
		var last = _heap[^1];
		_heap.RemoveAt( _heap.Count - 1 );
		if ( _heap.Count == 0 ) return top;

		var i = 0;
		while ( true )
		{
			var child = i * 2 + 1;
			if ( child >= _heap.Count ) break;
			if ( child + 1 < _heap.Count && _heap[child + 1].Time < _heap[child].Time ) child++;
			if ( _heap[child].Time >= last.Time ) break;
			_heap[i] = _heap[child];
			i = child;
		}

		_heap[i] = last;
		return top;
	}

	/// <summary> Host: send the cells that lit since the last message. </summary>
	private void SendLit()
	{
		if ( _outbox.Count == 0 || _sinceSent < SendInterval ) return;
		_sinceSent = 0;

		for ( var start = 0; start < _outbox.Count; start += RecordsPerMessage )
			Receive( Pack( _outbox, start, Math.Min( RecordsPerMessage, _outbox.Count - start ) ) );

		_outbox.Clear();
	}

	private static byte[] Pack( List<Record> records, int start, int count )
	{
		var stream = ByteStream.Create( 8 + count * 33 );
		var now = Time.Now;
		stream.Write( count );
		for ( var i = start; i < start + count; i++ )
		{
			var record = records[i];
			stream.Write( record.Key );
			stream.Write( record.Ground );
			stream.Write( now - record.LitAt );
			stream.Write( record.Duration );
			stream.Write( record.Flame );
			stream.Write( (byte)record.Fuel );
		}

		var data = stream.ToArray();
		stream.Dispose();
		return data;
	}

	/// <summary> Every machine: cells that lit, or burn longer, with how long ago they lit. </summary>
	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void Receive( byte[] data )
	{
		var stream = ByteStream.CreateReader( data );
		var count = stream.Read<int>();
		var now = Time.Now;

		for ( var i = 0; i < count; i++ )
		{
			var key = stream.Read<long>();
			var ground = stream.Read<Vector3>();
			var age = stream.Read<float>();
			var duration = stream.Read<float>();
			var flame = stream.Read<float>();
			var fuel = (FireFuel)stream.Read<byte>();
			AddBurning( key, ground, now - age, duration, flame, fuel );
		}

		stream.Dispose();
	}

	/// <summary> Host: a late joiner's copy of the fire, as it is now. </summary>
	[Rpc.Host]
	private void RequestSnapshot()
	{
		var caller = Rpc.Caller;
		if ( caller is null ) return;

		var records = new List<Record>( _burning.Count );
		foreach ( var burning in _burning )
		{
			records.Add( new Record
			{
				Key = burning.Key,
				Ground = burning.Ground,
				LitAt = burning.LitAt,
				Duration = burning.Duration,
				Flame = burning.Flame,
				Fuel = burning.Fuel,
			} );
		}

		using ( Rpc.FilterInclude( caller ) )
		{
			for ( var start = 0; start < records.Count; start += RecordsPerMessage )
				Receive( Pack( records, start, Math.Min( RecordsPerMessage, records.Count - start ) ) );

			for ( var start = 0; start < _scorched.Count; start += RecordsPerMessage * 2 )
				ReceiveScorch( PackScorch( start, Math.Min( RecordsPerMessage * 2, _scorched.Count - start ) ) );
		}
	}
}
