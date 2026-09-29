using Sandbox.Clutter;

namespace Facepunch;

/// <summary>
/// Grass that burnt on terrain turns to ash: each machine paints the terrain's control map with an ash material
/// (materials/terrain/burnt.tmat) where cells burnt out, and the grass clumps there go, because the grass clutter only
/// grows on meadow and dry meadow ground.
/// <para>
/// The ash goes on as the overlay of each texel it touches, over whichever of its two materials showed more, so the
/// ground between neighbouring texels blends smoothly into it: a hard change from one texel to the next shows the
/// 30-unit grid as blocks. It's full where a burnt cell is and fades out over about a texel past its edge.
/// </para>
/// <para>
/// The control map belongs to the terrain resource, which the editor shares and saves, so every texel painted is put
/// back, and the ash material taken off the terrain again, when the fire goes (between rounds, or when the scene
/// closes). Only the changed part of the map is sent to the GPU, and the collider's surfaces are left as they were.
/// </para>
/// </summary>
public sealed partial class SurfaceFire
{
	private const string BurntMaterialPath = "materials/terrain/burnt.tmat";

	/// <summary> The ash fades out over this many texels either side of a burnt cell's edge. </summary>
	private const float AshFadeTexels = 1f;

	/// <summary> The terrain holds up to 32 materials (5 bits a texel). </summary>
	private const int MaxTerrainMaterials = 32;

	private const float TerrainUploadInterval = 0.2f;
	private const float GrassUpdateInterval = 1.5f;

	/// <summary> A terrain this machine has painted ash on, and everything needed to put it back. </summary>
	private sealed class AshedTerrain
	{
		public Terrain Terrain;
		public TerrainStorage Storage;
		public byte AshIndex;
		public bool AddedMaterial;

		/// <summary> Each texel's value before it was first painted. </summary>
		public readonly Dictionary<int, uint> Original = new();

		/// <summary> Texels changed since the last upload (inclusive), empty when MinX > MaxX. </summary>
		public int MinX = int.MaxValue, MinY = int.MaxValue, MaxX = int.MinValue, MaxY = int.MinValue;

		/// <summary> World area whose grass has to be scattered again, and all the ground painted so far. </summary>
		public BBox? Grass;
		public BBox? Painted;

		public uint[] Staging;
	}

	private readonly List<AshedTerrain> _ashed = new();
	private TimeSince _sinceTerrainUpload;
	private TimeSince _sinceGrassUpdate;

	/// <summary>
	/// Paint ash over a burnt square of terrain, <paramref name="half"/> units either side of <paramref name="centre"/>.
	/// False if there's no terrain there that can take it.
	/// </summary>
	private bool PaintTerrain( Vector3 centre, float half )
	{
		var ashed = AshedAt( centre );
		if ( ashed is null ) return false;

		var storage = ashed.Storage;
		var resolution = storage.Resolution;
		var map = storage.ControlMap;
		if ( map is null || map.Length < resolution * resolution ) return false;

		var perTexel = storage.TerrainSize / resolution;
		var local = ashed.Terrain.WorldTransform.PointToLocal( centre );
		var localHalf = half / MathF.Max( ashed.Terrain.WorldScale.x, 0.001f );
		var fade = AshFadeTexels * perTexel;

		var x0 = Math.Max( 0, FloorToInt( (local.x - localHalf - fade) / perTexel ) );
		var x1 = Math.Min( resolution - 1, FloorToInt( (local.x + localHalf + fade) / perTexel ) );
		var y0 = Math.Max( 0, FloorToInt( (local.y - localHalf - fade) / perTexel ) );
		var y1 = Math.Min( resolution - 1, FloorToInt( (local.y + localHalf + fade) / perTexel ) );
		if ( x0 > x1 || y0 > y1 ) return false;

		for ( var y = y0; y <= y1; y++ )
		{
			for ( var x = x0; x <= x1; x++ )
			{
				// How far the texel's middle is outside the burnt square (negative inside it).
				var dx = MathF.Abs( (x + 0.5f) * perTexel - local.x ) - localHalf;
				var dy = MathF.Abs( (y + 0.5f) * perTexel - local.y ) - localHalf;
				var outside = new Vector2( MathF.Max( dx, 0f ), MathF.Max( dy, 0f ) ).Length + MathF.Min( MathF.Max( dx, dy ), 0f );
				var share = Math.Clamp( 0.5f - outside / (2f * fade), 0f, 1f );
				var ash = (byte)MathF.Round( share * 255f );
				if ( ash == 0 ) continue;

				var index = y * resolution + x;
				var old = new CompactTerrainMaterial( map[index] );
				if ( old.IsHole ) continue;

				CompactTerrainMaterial next;
				if ( ashed.Original.ContainsKey( index ) )
				{
					// Painted already: the ash is its overlay.
					if ( old.BlendFactor >= ash ) continue;
					next = old with { BlendFactor = ash };
				}
				else
				{
					var shown = old.BlendFactor >= 128 ? old.OverlayTextureId : old.BaseTextureId;
					next = new CompactTerrainMaterial( shown, ashed.AshIndex, ash );
					ashed.Original[index] = map[index];
				}

				map[index] = next.Packed;
				ashed.MinX = Math.Min( ashed.MinX, x );
				ashed.MinY = Math.Min( ashed.MinY, y );
				ashed.MaxX = Math.Max( ashed.MaxX, x );
				ashed.MaxY = Math.Max( ashed.MaxY, y );
			}
		}

		var area = BBox.FromPositionAndSize( centre, new Vector3( (half + fade) * 2f, (half + fade) * 2f, 2000f ) );
		ashed.Grass = ashed.Grass is BBox grass ? grass.AddBBox( area ) : area;
		ashed.Painted = ashed.Painted is BBox painted ? painted.AddBBox( area ) : area;
		return true;
	}

	/// <summary> The terrain under a point, readied for ash, or null if there's none that can take it. </summary>
	private AshedTerrain AshedAt( Vector3 point )
	{
		foreach ( var ashed in _ashed )
		{
			if ( Covers( ashed.Terrain, ashed.Storage, point ) )
				return ashed;
		}

		foreach ( var terrain in Scene.GetAllComponents<Terrain>() )
		{
			var storage = terrain.Storage;
			if ( !terrain.Active || storage is null || terrain.ControlMap is null ) continue;
			if ( !Covers( terrain, storage, point ) ) continue;
			if ( _ashed.Any( x => x.Terrain == terrain ) ) return null;

			var ash = ResourceLibrary.Get<TerrainMaterial>( BurntMaterialPath );
			if ( ash is null ) return null;

			var index = storage.Materials.IndexOf( ash );
			var added = false;
			if ( index < 0 )
			{
				if ( storage.Materials.Count >= MaxTerrainMaterials ) return null;
				storage.Materials.Add( ash );
				index = storage.Materials.Count - 1;
				added = true;
				terrain.UpdateMaterialsBuffer();
			}

			var ashed = new AshedTerrain { Terrain = terrain, Storage = storage, AshIndex = (byte)index, AddedMaterial = added };
			_ashed.Add( ashed );
			return ashed;
		}

		return null;
	}

	private static bool Covers( Terrain terrain, TerrainStorage storage, Vector3 point )
	{
		if ( !terrain.IsValid() || storage is null ) return false;
		var local = terrain.WorldTransform.PointToLocal( point );
		return local.x >= 0f && local.y >= 0f && local.x < storage.TerrainSize && local.y < storage.TerrainSize;
	}

	/// <summary> Every machine but a dedicated server: send new ash to the GPU, and scatter the grass round it again. </summary>
	private void FlushTerrain()
	{
		if ( _ashed.Count == 0 ) return;

		if ( _sinceTerrainUpload >= TerrainUploadInterval )
		{
			_sinceTerrainUpload = 0;
			foreach ( var ashed in _ashed )
				Upload( ashed );
		}

		if ( _sinceGrassUpdate >= GrassUpdateInterval )
		{
			_sinceGrassUpdate = 0;
			foreach ( var ashed in _ashed )
				RescatterGrass( ashed );
		}
	}

	/// <summary> The changed rectangle of the control map, to the GPU. </summary>
	private static void Upload( AshedTerrain ashed )
	{
		if ( ashed.MinX > ashed.MaxX ) return;

		var (x, y) = (ashed.MinX, ashed.MinY);
		var width = ashed.MaxX - ashed.MinX + 1;
		var height = ashed.MaxY - ashed.MinY + 1;
		ashed.MinX = ashed.MinY = int.MaxValue;
		ashed.MaxX = ashed.MaxY = int.MinValue;

		var texture = ashed.Terrain.IsValid() ? ashed.Terrain.ControlMap : null;
		if ( texture is null ) return;

		var count = width * height;
		if ( ashed.Staging is null || ashed.Staging.Length < count )
			ashed.Staging = new uint[count];

		var map = ashed.Storage.ControlMap;
		var resolution = ashed.Storage.Resolution;
		for ( var row = 0; row < height; row++ )
			Array.Copy( map, (y + row) * resolution + x, ashed.Staging, row * width, width );

		try
		{
			texture.Update( new ReadOnlySpan<uint>( ashed.Staging, 0, count ), x, y, width, height );
		}
		catch ( Exception e )
		{
			Log.Warning( $"SurfaceFire: couldn't update the terrain's ash ({e.Message})" );
		}
	}

	/// <summary> The grass tiles over new ash, or restored ground, are scattered again from the control map. </summary>
	private void RescatterGrass( AshedTerrain ashed )
	{
		if ( ashed.Grass is not BBox area ) return;
		ashed.Grass = null;
		RescatterGrass( area );
	}

	private void RescatterGrass( BBox area )
	{
		if ( Scene is null ) return;

		foreach ( var clutter in Scene.GetAllComponents<ClutterComponent>() )
		{
			if ( !clutter.IsValid() || !clutter.Active || !clutter.Infinite ) continue;

			try
			{
				clutter.InvalidateTilesInBounds( area );
			}
			catch ( Exception e )
			{
				// The scene is closing and its clutter system has gone: there's no grass to grow back.
				Log.Trace( $"SurfaceFire: grass not rescattered ({e.Message})" );
			}
		}
	}

	/// <summary> Put back every texel this fire painted, and take the ash material off the terrain again. </summary>
	private void RestoreTerrain()
	{
		foreach ( var ashed in _ashed )
		{
			var storage = ashed.Storage;
			var map = storage?.ControlMap;
			if ( map is not null && ashed.Original.Count > 0 )
			{
				var resolution = storage.Resolution;
				foreach ( var (index, value) in ashed.Original )
				{
					if ( index >= map.Length ) continue;
					map[index] = value;
					ashed.MinX = Math.Min( ashed.MinX, index % resolution );
					ashed.MinY = Math.Min( ashed.MinY, index / resolution );
					ashed.MaxX = Math.Max( ashed.MaxX, index % resolution );
					ashed.MaxY = Math.Max( ashed.MaxY, index / resolution );
				}

				ashed.Original.Clear();
				Upload( ashed );
			}

			if ( ashed.AddedMaterial && storage is not null )
			{
				if ( ashed.AshIndex == storage.Materials.Count - 1 )
					storage.Materials.RemoveAt( ashed.AshIndex );
				if ( ashed.Terrain.IsValid() )
					ashed.Terrain.UpdateMaterialsBuffer();
			}

			if ( ashed.Painted is BBox painted )
				RescatterGrass( painted );
		}

		_ashed.Clear();
	}
}
