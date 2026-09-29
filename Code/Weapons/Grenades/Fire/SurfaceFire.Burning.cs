namespace Facepunch;

/// <summary>
/// The cells burning now, the same on every machine (see <see cref="Receive"/>), and the scorched ground they leave.
/// </summary>
public sealed partial class SurfaceFire
{
	private struct Burning
	{
		public long Key;
		public Vector3 Ground;
		/// <summary> When it lit, in this machine's <see cref="Time.Now"/>. </summary>
		public float LitAt;
		public float Duration;
		/// <summary> The flames' length at their height, in metres. </summary>
		public float Flame;
		public FireFuel Fuel;
		public float Seed;
		public float FlameDebt;
		public float SmokeDebt;
		public float EmberDebt;
	}

	/// <summary> What burnt ground looks like: terrain painted to ash, a burnt patch, or the slag where thermite burnt. </summary>
	private enum ScorchKind : byte
	{
		Terrain,
		Patch,
		Thermite,
	}

	/// <summary> Scorched ground: where, how wide (units) and what kind. </summary>
	private readonly record struct ScorchMark( Vector3 Position, float Width, ScorchKind Kind );

	/// <summary> The thermite scorch's width in units: the drops of iron reach about 1.5 m, most within 0.35 m. </summary>
	private const float ThermiteScorchWidth = 60f;

	private readonly List<Burning> _burning = new();
	private readonly Dictionary<long, int> _burningIndex = new();

	/// <summary> Every scorch mark so far, kept on every machine; the host sends them to late joiners. </summary>
	private readonly List<ScorchMark> _scorched = new();

	private void AddBurning( long key, Vector3 ground, float litAt, float duration, float flame, FireFuel fuel )
	{
		if ( _burningIndex.TryGetValue( key, out var index ) )
		{
			var existing = _burning[index];
			existing.LitAt = litAt;
			existing.Duration = duration;
			existing.Flame = flame;
			_burning[index] = existing;
			return;
		}

		// A snapshot can carry cells that have already burnt out here.
		if ( Time.Now > litAt + duration ) return;

		_burningIndex[key] = _burning.Count;
		_burning.Add( new Burning
		{
			Key = key,
			Ground = ground,
			LitAt = litAt,
			Duration = duration,
			Flame = flame,
			Fuel = fuel,
			Seed = Game.Random.Float( 0f, 1000f ),
		} );
	}

	/// <summary> Cells that have burnt out leave scorched ground. </summary>
	private void ExpireBurning()
	{
		var now = Time.Now;
		for ( var i = _burning.Count - 1; i >= 0; i-- )
		{
			var burning = _burning[i];
			if ( now <= burning.LitAt + burning.Duration ) continue;

			var last = _burning.Count - 1;
			_burningIndex.Remove( burning.Key );
			if ( i != last )
			{
				_burning[i] = _burning[last];
				_burningIndex[_burning[i].Key] = i;
			}

			_burning.RemoveAt( last );
			Scorch( burning );
		}
	}

	/// <summary>
	/// 0 to 1: how hard a cell burns now. Grass flames come up as the front reaches the cell and die down over the flames'
	/// last few seconds there. A lit patch of anything else grows, burns, then dies down over its last third.
	/// </summary>
	private static float Envelope( in Burning burning, float now )
	{
		var age = now - burning.LitAt;
		if ( age < 0f || age > burning.Duration ) return 0f;

		var left = burning.Duration - age;
		float rise, fall;
		if ( FireFuels.Spreads( burning.Fuel ) )
		{
			rise = age / 1.5f;
			fall = left / MathF.Min( 6f, burning.Duration * 0.5f );
		}
		else
		{
			rise = age / MathF.Max( 2f, burning.Duration * 0.2f );
			fall = left / (burning.Duration * 0.35f);
		}

		return SmoothStep( Math.Clamp( rise, 0f, 1f ) ) * SmoothStep( Math.Clamp( fall, 0f, 1f ) );
	}

	private static float SmoothStep( float x ) => x * x * (3f - 2f * x);

	/// <summary> Grass on terrain burns to ash where the cell is; anything else leaves a burnt patch. </summary>
	private void Scorch( in Burning burning )
	{
		if ( burning.Fuel is FireFuel.CuredGrass or FireFuel.GreenGrass )
		{
			var (ix, iy, _) = Unpack( burning.Key );
			var centre = new Vector3( (ix + 0.5f) * CellSize, (iy + 0.5f) * CellSize, burning.Ground.z );
			AddScorch( new ScorchMark( centre, CellSize, ScorchKind.Terrain ) );
			return;
		}

		AddScorch( new ScorchMark( burning.Ground, CellSize * 1.6f, ScorchKind.Patch ) );
	}

	/// <summary> Host: the slag and scorch where a thermite grenade burnt out, on every machine. </summary>
	public void MarkThermiteScorch( Vector3 ground )
	{
		if ( !Networking.IsHost ) return;

		AddScorch( new ScorchMark( ground, ThermiteScorchWidth, ScorchKind.Thermite ) );
		ReceiveScorch( PackScorch( _scorched.Count - 1, 1 ) );
	}

	private void AddScorch( ScorchMark mark )
	{
		_scorched.Add( mark );
		if ( Application.IsDedicatedServer ) return;

		// Terrain that can't be painted gets a burnt patch instead.
		if ( mark.Kind != ScorchKind.Terrain || !PaintTerrain( mark.Position, mark.Width * 0.5f ) )
			PlaceScorchDecal( mark );
	}

	private byte[] PackScorch( int start, int count )
	{
		var stream = ByteStream.Create( 8 + count * 17 );
		stream.Write( count );
		for ( var i = start; i < start + count; i++ )
		{
			var mark = _scorched[i];
			stream.Write( mark.Position );
			stream.Write( mark.Width );
			stream.Write( (byte)mark.Kind );
		}

		var data = stream.ToArray();
		stream.Dispose();
		return data;
	}

	/// <summary> Scorch marks from the host: a late joiner's, or where thermite burnt out. </summary>
	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void ReceiveScorch( byte[] data )
	{
		if ( Networking.IsHost ) return;

		var stream = ByteStream.CreateReader( data );
		var count = stream.Read<int>();
		for ( var i = 0; i < count; i++ )
		{
			var position = stream.Read<Vector3>();
			var width = stream.Read<float>();
			var kind = (ScorchKind)stream.Read<byte>();
			AddScorch( new ScorchMark( position, width, kind ) );
		}

		stream.Dispose();
	}
}
