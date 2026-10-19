namespace Facepunch;

public sealed partial class ViewModelClothing
{
	const string ShirtColour = "materials/operators/first_person/fp_army_shirt_color.png";
	const string GlovesColour = "materials/operators/first_person/fp_fingerless_gloves_albedo.png";
	const string ShirtNormal = "materials/operators/first_person/fp_army_shirt_normal.png";
	const string GlovesNormal = "materials/operators/first_person/fp_fingerless_gloves_normal.png";
	static readonly Dictionary<Material, Material> DetailedMaterials = new();

	// Copies retain the garment's normal, roughness, AO and alpha-test settings, and the renderer keeps its outfit tint.
	// They belong to the first-person clothing only and are shared across respawns and outfit changes.
	static void ApplyDetailedMaterials( SkinnedModelRenderer renderer )
	{
		if ( !renderer.IsValid() || renderer.Model is null ) return;
		for ( int i = 0; i < renderer.Model.Materials.Length; i++ )
		{
			var original = renderer.Model.Materials[i];
			if ( original is null || original.IsError ) continue;
			var path = original.Name;
			var colour = path.Contains( "/army_shirt/", StringComparison.OrdinalIgnoreCase ) ? ShirtColour
				: path.Contains( "/fingerless_gloves/", StringComparison.OrdinalIgnoreCase ) ? GlovesColour : null;
			if ( colour is null ) continue;
			var normalPath = colour == ShirtColour ? ShirtNormal : GlovesNormal;

			if ( !DetailedMaterials.TryGetValue( original, out var material ) || material is null || material.IsError )
			{
				var texture = Texture.Load( colour );
				if ( texture is null || !texture.IsValid || texture.IsError ) continue;
				var normal = Texture.Load( normalPath );
				if ( normal is null || !normal.IsValid || normal.IsError ) continue;
				texture.MarkUsed( Math.Max( texture.Width, texture.Height ) );
				normal.MarkUsed( Math.Max( normal.Width, normal.Height ) );
				material = original.CreateCopy( $"hc1-first-person-{original.Name}" );
				material.Set( "g_tColor", texture );
				material.Set( "g_tNormal", normal );
				DetailedMaterials[original] = material;
			}
			if ( renderer.Materials.GetOverride( i ) != material ) renderer.Materials.SetOverride( i, material );
		}
	}
}
