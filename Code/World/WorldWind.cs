namespace Facepunch;

/// <summary>A shared outdoor air velocity, in metres per second. Map authors can override the default light breeze.</summary>
[Title( "World Wind" ), Category( "Environment" )]
public sealed class WorldWind : Component
{
	[Property, Sync( SyncFlags.FromHost )] public Vector3 Velocity { get; set; } = new( 0.39f, -0.52f, 0 );
	[Property, Sync( SyncFlags.FromHost ), Range( 0, 1 )] public float GustStrength { get; set; } = 0.35f;
	[Sync( SyncFlags.FromHost )] public TimeSince Elapsed { get; private set; }

	public const float UnitsPerMetre = 39.3701f;

	protected override void OnStart()
	{
		if ( !IsProxy ) Elapsed = 0;
	}

	public Vector3 Sample( Vector3 position ) => Sample( position, Elapsed, Velocity * UnitsPerMetre, GustStrength );

	/// <summary>Travelling gusts shared by nearby clouds, with a small change in heading. Zero wind stays zero.</summary>
	public static Vector3 Sample( Vector3 position, float time, Vector3 velocity, float gustStrength )
	{
		var speed = velocity.Length;
		if ( speed < 0.001f ) return Vector3.Zero;
		var direction = velocity / speed;
		var across = Vector3.Cross( Vector3.Up, direction );
		var phase = Vector3.Dot( position, direction ) * 0.0035f - time * 0.55f;
		var gust = MathF.Sin( phase ) * 0.65f + MathF.Sin( phase * 0.43f + time * 0.13f ) * 0.35f;
		return velocity * (1 + gust * gustStrength)
			+ across * (speed * gustStrength * 0.2f * MathF.Sin( phase * 0.71f ));
	}

	/// <summary>Create once on the host so all smoke uses the same weather, including late joiners.</summary>
	public static WorldWind Ensure( Scene scene )
	{
		var existing = scene.GetAllComponents<WorldWind>().FirstOrDefault();
		if ( existing.IsValid() || !Networking.IsHost ) return existing;
		var go = new GameObject( scene, true, "World Wind" );
		go.Flags |= GameObjectFlags.NotSaved;
		var wind = go.AddComponent<WorldWind>();
		go.NetworkSpawn();
		return wind;
	}
}
