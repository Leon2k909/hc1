namespace Facepunch;

/// <summary>
/// The fine alpha-tested floor grating sparkles under camera motion. Replace only the
/// grating slots with the opaque, mip-filtered steel-over-dark-tray material, leaving
/// all other mesh materials and Riverdale's baked indirect lighting untouched.
/// </summary>
public sealed class RiverdaleGratingStabilizer : Component
{
	private static readonly string MaterialPath = "materials/riverdale/visuals/rv_grating_stable.vmat";

	protected override void OnStart()
	{
		var renderer = Components.Get<ModelRenderer>();
		if ( renderer?.Model is null ) return;
		var stable = Material.Load( MaterialPath );
		if ( stable is null || stable.IsError )
		{
			Log.Warning( $"Riverdale: grating material unavailable: {MaterialPath}" );
			return;
		}
		for ( var i = 0; i < renderer.Model.Materials.Length; i++ )
		{
			var original = renderer.Model.Materials[i];
			if ( original?.Name?.EndsWith( "/rv_grating", System.StringComparison.OrdinalIgnoreCase ) == true ||
				original?.Name?.EndsWith( "/rv_grating.vmat", System.StringComparison.OrdinalIgnoreCase ) == true )
				renderer.Materials.SetOverride( i, stable );
		}
	}
}
