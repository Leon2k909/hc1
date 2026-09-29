using Sandbox.Clutter;

namespace Facepunch;

/// <summary>
/// A clutter scatterer that places a planned list instead of random points: each placement names its entry and has its
/// own spot, turn and size, and only its height comes from the ground below. Ridgeback's trees, bushes and hedgerows
/// are planned by Tools/ridgeback_trees.py, which writes them into ridgeback_trees.clutter.
/// </summary>
public class PlannedScatterer : Scatterer
{
	private const int RecordSize = 7;

	/// <summary>
	/// The placements: base64 of 7-byte records, each an entry index (byte), x and y (int16, world units), yaw (byte,
	/// 256ths of a turn) and scale (byte, 0.25 + value / 255 * 2.25).
	/// </summary>
	[Property, Hide] public string Placements { get; set; }

	/// <summary>
	/// Entries that lie with the ground's slope (bushes, hedges). The rest stand upright, as trees grow.
	/// </summary>
	[Property] public List<int> AlignedEntries { get; set; } = [];

	/// <summary>
	/// How far each placement is sunk into the ground, so none stands on its edge on a slope.
	/// </summary>
	[Property] public float Sink { get; set; } = 4f;

	private string _decodedFrom;
	private byte[] _decoded;

	protected override List<ClutterInstance> Generate( BBox bounds, ClutterDefinition clutter, Scene scene = null )
	{
		scene ??= Game.ActiveScene;
		if ( scene is null || clutter is null || clutter.IsEmpty || string.IsNullOrEmpty( Placements ) )
			return [];

		// Every tile of a volume reads the same list, so it's decoded once.
		if ( !ReferenceEquals( _decodedFrom, Placements ) )
		{
			_decoded = Convert.FromBase64String( Placements );
			_decodedFrom = Placements;
		}

		var data = _decoded;
		var points = new List<Vector3>();
		var records = new List<int>();

		for ( var i = 0; i + RecordSize <= data.Length; i += RecordSize )
		{
			var x = (short)(data[i + 1] | data[i + 2] << 8);
			var y = (short)(data[i + 3] | data[i + 4] << 8);

			// Half-open, so a placement on the line between two tiles is only placed once.
			if ( x < bounds.Mins.x || x >= bounds.Maxs.x || y < bounds.Mins.y || y >= bounds.Maxs.y )
				continue;

			points.Add( new Vector3( x, y, 0f ) );
			records.Add( i );
		}

		var instances = new List<ClutterInstance>( points.Count );
		if ( points.Count == 0 )
			return instances;

		var traces = BatchTraceGround( scene, points, scene.GetBounds() );

		for ( var k = 0; k < traces.Length; k++ )
		{
			var trace = traces[k];
			if ( !trace.Hit )
				continue;

			var record = records[k];
			var index = data[record];
			if ( index >= clutter.Entries.Count || clutter.Entries[index]?.HasAsset is not true )
				continue;

			var yaw = data[record + 5] * (360f / 256f);
			var scale = 0.25f + data[record + 6] / 255f * 2.25f;
			var rotation = AlignedEntries?.Contains( index ) is true
				? GetAlignedRotation( trace.Normal, yaw )
				: Rotation.FromYaw( yaw );

			instances.Add( new ClutterInstance
			{
				Transform = new Transform( trace.HitPosition + Vector3.Down * Sink, rotation, scale ),
				Entry = clutter.Entries[index]
			} );
		}

		return instances;
	}
}
