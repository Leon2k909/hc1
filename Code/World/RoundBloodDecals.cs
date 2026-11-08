namespace Facepunch;

/// <summary>
/// Round-local blood decals. Like Sandbox's Decal Merger, stamps on the same plane
/// are composited before rendering. Blood uses a single colour, so only coverage
/// needs to be accumulated and previously baked stamps can be discarded.
/// </summary>
public sealed class RoundBloodDecals : GameObjectSystem<RoundBloodDecals>
{
	private const int TileSize = 64;
	private const int Resolution = 128;
	private const int MaxTiles = 256;
	private const int MaskSize = 64;
	private static readonly byte[][] Masks = Enumerable.Range( 0, 8 ).Select( CreateMask ).ToArray();

	private readonly record struct TileKey( Guid Receiver, Vector3 Normal, int Plane, int X, int Y );
	private sealed record Tile( GameObject Object, Texture Texture, Color32[] Pixels );
	private readonly Dictionary<TileKey, Tile> _tiles = new();
	private readonly HashSet<Tile> _dirty = new();

	public RoundBloodDecals( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, 0, Upload, "Round blood decals" );
	}

	public static void OnDamage( Scene scene, DamageInfo damage )
	{
		const DamageFlags excluded = DamageFlags.Burn | DamageFlags.Zone | DamageFlags.FallDamage;
		if ( Application.IsDedicatedServer || damage.Damage <= 0 || (damage.Flags & excluded) != 0
			|| damage.Victim is not (PlayerPawn or LightweightCombatBot) ) return;

		var position = damage.Position;
		if ( position == default || (position - damage.Victim.WorldPosition).LengthSquared > 128 * 128 )
			position = damage.Victim.WorldPosition + Vector3.Up * 36;
		scene.GetSystem<RoundBloodDecals>()?.Splat( damage.Victim.GameObject.Root, position, damage.Force );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	public static void ResetRound()
	{
		Game.ActiveScene?.GetSystem<RoundBloodDecals>()?.Clear();
	}

	public void Splat( GameObject victim, Vector3 position, Vector3 force )
	{
		if ( Application.IsDedicatedServer || Scene.IsEditor ) return;
		var trace = Scene.Trace.IgnoreGameObjectHierarchy( victim )
			.WithoutTags( "player", "enemy", "ragdoll", "corpse", "trigger", "playerclip", "movement", "grenade", "water", BreakableGlass.Tag );
		var floor = trace.Ray( position + Vector3.Up * 2, position + Vector3.Down * 144 ).Run();
		if ( floor.Normal.z >= .7f ) Paint( floor );

		if ( force.IsNearZeroLength ) return;
		var wall = trace.Ray( position, position + force.Normal * 112 ).Run();
		if ( MathF.Abs( wall.Normal.z ) <= .25f ) Paint( wall );
	}

	private void Paint( SceneTraceResult hit )
	{
		if ( !hit.Hit || hit.StartedSolid || !hit.GameObject.IsValid()
			|| !hit.Body.IsValid() || hit.Body.BodyType != PhysicsBodyType.Static ) return;

		// Quantize the contact plane before choosing axes so consecutive impacts agree on tile coordinates.
		var normal = new Vector3( MathF.Round( hit.Normal.x * 200 ), MathF.Round( hit.Normal.y * 200 ),
			MathF.Round( hit.Normal.z * 200 ) ).Normal;
		var plane = (int)MathF.Round( hit.HitPosition.Dot( normal ) * 4 );
		var rotation = Rotation.LookAt( -normal, MathF.Abs( normal.z ) > .95f ? Vector3.Forward : Vector3.Up );
		var u = hit.HitPosition.Dot( -rotation.Left );
		var v = hit.HitPosition.Dot( -rotation.Up );
		var radius = Random.Shared.Float( 7, 13 );
		var angle = Random.Shared.Float( 0, MathF.Tau );
		var sine = MathF.Sin( angle );
		var cosine = MathF.Cos( angle );
		var mask = Masks[Random.Shared.Next( Masks.Length )];

		for ( int x = TileIndex( u - radius ); x <= TileIndex( u + radius ); x++ )
		for ( int y = TileIndex( v - radius ); y <= TileIndex( v + radius ); y++ )
		{
			var key = new TileKey( hit.GameObject.Id, normal, plane, x, y );
			_tiles.TryGetValue( key, out var tile );
			// Keep existing marks for the round. New surface tiles are bounded in memory.
			if ( tile is null && _tiles.Count >= MaxTiles ) continue;
			var changed = false;
			for ( int py = Pixel( v - radius, y ); py < Pixel( v + radius, y ); py++ )
			for ( int px = Pixel( u - radius, x ); px < Pixel( u + radius, x ); px++ )
			{
				var du = (x * TileSize + (px + .5f) * TileSize / Resolution - u) / radius;
				var dv = (y * TileSize + (py + .5f) * TileSize / Resolution - v) / radius;
				var mx = (int)MathF.Floor( (du * cosine - dv * sine + 1) * MaskSize / 2 );
				var my = (int)MathF.Floor( (du * sine + dv * cosine + 1) * MaskSize / 2 );
				if ( (uint)mx >= MaskSize || (uint)my >= MaskSize ) continue;
				var coverage = mask[my * MaskSize + mx];
				if ( coverage == 0 ) continue;
				if ( tile is null )
				{
					tile = CreateTile( key, rotation );
					_tiles.Add( key, tile );
				}
				var index = py * Resolution + px;
				var alpha = coverage + (tile.Pixels[index].a * (255 - coverage) + 127) / 255;
				tile.Pixels[index] = Blood( (byte)alpha );
				changed = true;
			}
			if ( changed ) _dirty.Add( tile );
		}
	}

	private Tile CreateTile( TileKey key, Rotation rotation )
	{
		var pixels = new Color32[Resolution * Resolution];
		Array.Fill( pixels, Blood( 0 ) );
		var texture = Texture.Create( Resolution, Resolution, ImageFormat.RGBA8888 )
			.WithDynamicUsage().WithData( pixels ).Finish();
		var go = Scene.CreateObject();
		go.Enabled = false;
		go.Name = "Round blood decal tile";
		go.NetworkMode = NetworkMode.Never;
		go.Flags |= GameObjectFlags.NotSaved;
		go.WorldRotation = rotation;
		go.WorldPosition = key.Normal * (key.Plane / 4f + .04f)
			- rotation.Left * ((key.X + .5f) * TileSize) - rotation.Up * ((key.Y + .5f) * TileSize);
		var decal = go.Components.Create<Decal>();
		decal.Decals = [new DecalDefinition { ColorTexture = texture, Width = TileSize, Height = TileSize, ColorMix = 1 }];
		decal.Depth = 1.5f;
		decal.Parallax = 0;
		decal.AttenuationAngle = 1;
		return new Tile( go, texture, pixels );
	}

	private void Upload()
	{
		foreach ( var tile in _dirty )
		{
			tile.Texture.Update( tile.Pixels, 0, 0, Resolution, Resolution );
			tile.Object.Enabled = true;
		}
		_dirty.Clear();
	}

	private void Clear()
	{
		_dirty.Clear();
		foreach ( var tile in _tiles.Values )
		{
			if ( tile.Object.IsValid() ) tile.Object.Destroy();
			tile.Texture.Dispose();
		}
		_tiles.Clear();
	}

	public override void Dispose()
	{
		Clear();
		base.Dispose();
	}

	private static int TileIndex( float value ) => (int)MathF.Floor( value / TileSize );
	private static int Pixel( float value, int tile ) => Math.Clamp( (int)MathF.Ceiling( (value - tile * TileSize) * Resolution / TileSize ), 0, Resolution );
	private static Color32 Blood( byte alpha ) => new( 78, 6, 10, alpha );

	private static byte[] CreateMask( int seed )
	{
		var random = new Random( seed );
		var pixels = new byte[MaskSize * MaskSize];
		// Irregular central impact, then increasingly small satellite droplets.
		Dab( 0, 0, .29f, .22f );
		for ( int i = 0; i < 22; i++ )
		{
			var angle = random.Float( 0, MathF.Tau );
			var distance = i < 8 ? random.Float( .08f, .32f ) : random.Float( .37f, .85f );
			var radius = i < 8 ? random.Float( .08f, .21f ) : random.Float( .023f, .071f );
			Dab( MathF.Cos( angle ) * distance, MathF.Sin( angle ) * distance, radius, radius * random.Float( .5f, 1.2f ) );
		}
		return pixels;

		void Dab( float x, float y, float rx, float ry )
		{
			for ( int py = 0; py < MaskSize; py++ )
			for ( int px = 0; px < MaskSize; px++ )
			{
				var dx = (2f * (px + .5f) / MaskSize - 1 - x) / rx;
				var dy = (2f * (py + .5f) / MaskSize - 1 - y) / ry;
				var value = (byte)(224 * Math.Clamp( (1 - dx * dx - dy * dy) * 5, 0, 1 ));
				var index = py * MaskSize + px;
				pixels[index] = Math.Max( pixels[index], value );
			}
		}
	}
}
