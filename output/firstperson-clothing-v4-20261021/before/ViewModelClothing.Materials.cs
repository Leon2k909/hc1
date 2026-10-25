namespace Facepunch;

public sealed partial class ViewModelClothing
{
	const string ShirtMaterial = "materials/operators/first_person/v3/shirt.vmat";
	const string GlovesMaterial = "materials/operators/first_person/v2/gloves.vmat";
	static readonly Dictionary<string, Material> SurfaceMaterials = new();
	static readonly string[] SurfaceTextures = {
		"g_tColor", "g_tNormal", "g_tRma", "g_tFineNormal", "g_tFineData",
		"g_tSleeveLeft", "g_tSleeveRight", "g_tCuffMain", "g_tCuffStrip"
	};

	static void RequestDetailedTextureMips()
	{
		foreach ( var pair in SurfaceMaterials )
		{
			// Hotload may retain a previously used revision in the cache.
			if ( pair.Key != ShirtMaterial && pair.Key != GlovesMaterial ) continue;
			var material = pair.Value;
			if ( material is null || material.IsError ) continue;
			foreach ( var key in SurfaceTextures )
			{
				var texture = material.GetTexture( key );
				if ( texture is null || !texture.IsValid || texture.IsError ) continue;
				texture.MarkUsed( Math.Max( texture.Width, texture.Height ) );
			}
		}
	}

	// These resources keep the original coverage, tint masks and fold normals.
	// Sleeve and cuff colour regions have their own authored pixel density;
	// fine surface detail repeats independently of the full-garment UV atlas.
	// Loading authored materials also lets resource hotload update existing sleeves.
	static void ApplyDetailedMaterials( SkinnedModelRenderer renderer )
	{
		if ( !renderer.IsValid() || renderer.Model is null ) return;
		for ( int i = 0; i < renderer.Model.Materials.Length; i++ )
		{
			var original = renderer.Model.Materials[i];
			if ( original is null || original.IsError ) continue;
			var path = original.Name;
			var surface = path.Contains( "/army_shirt/", StringComparison.OrdinalIgnoreCase ) ? ShirtMaterial
				: path.Contains( "/fingerless_gloves/", StringComparison.OrdinalIgnoreCase ) ? GlovesMaterial : null;
			if ( surface is null ) continue;

			if ( !SurfaceMaterials.TryGetValue( surface, out var material ) || material is null || material.IsError )
			{
				material = Material.Load( surface );
				if ( material is null || material.IsError ) continue;
				SurfaceMaterials[surface] = material;
			}
			// This method already runs at the clothing's 0.5-second refresh interval.
			// Renew the close-up mip request even when the shared material is cached.
			foreach ( var key in SurfaceTextures )
			{
				var texture = material.GetTexture( key );
				if ( texture is null || !texture.IsValid || texture.IsError ) continue;
				texture.MarkUsed( Math.Max( texture.Width, texture.Height ) );
			}
			if ( renderer.Materials.GetOverride( i ) != material ) renderer.Materials.SetOverride( i, material );
		}
	}
}
