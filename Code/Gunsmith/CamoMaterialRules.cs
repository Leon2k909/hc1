using System;

namespace Facepunch.Gunsmith;

/// <summary>Optical surfaces and the masks around them must keep their original materials when a gun is painted.</summary>
internal static class CamoMaterialRules
{
	internal enum Surface
	{
		Paintable,
		Lens,
		Reticle,
		Mask,
	}

	public static Surface Classify( string materialName, string shaderName, bool isOptic, bool isTransparent )
	{
		var name = FileStem( materialName );
		var shader = FileStem( shaderName );

		// These hide geometry or keep the inside of the eyepiece black. In particular, an animated camo's shader
		// would turn a hidden stencil/depth mask into an opaque painted polygon.
		if ( name.Contains( "stencil" ) || name.Contains( "depth_mask" ) || name.Contains( "baffle" )
			|| name is "hidden" or "nodraw" or "no_draw"
			|| (isOptic && name == "black_matte") )
			return Surface.Mask;

		// Use the shader as well as the filename: SWB's reflex_dot_shader variants don't end in "_dot.vmat",
		// and imported/renamed lens materials can have an arbitrary filename.
		if ( name.Contains( "reticle" ) || name.Contains( "hologram" ) || name.Contains( "crosshair" )
			|| name.Contains( "_dot_shader" ) || name.EndsWith( "_dot" ) || name.EndsWith( "_reddot" )
			|| name is "dot" or "red_dot"
			|| shader is "m4_optic_lens" or "swb_sam_red_dot" )
			return Surface.Reticle;

		// scope.vmat is the Hunter's view surface, while 3d_scope.vmat is the M700's live scope image.
		// Neither name contains "lens" or "glass". Avoid matching scope/holo/rmr in the directory: the housing
		// in those directories is still paintable when Camo on Optics is enabled.
		if ( name.Contains( "lens" ) || name.Contains( "glass" ) || shader.Contains( "lens" )
			|| shader is "swb_render_scope" or "scope" or "3dscope"
			|| (isOptic && isTransparent) )
			return Surface.Lens;

		return Surface.Paintable;
	}

	private static string FileStem( string path )
	{
		path = (path ?? "").Replace( '\\', '/' );
		var file = path[(path.LastIndexOf( '/' ) + 1)..];
		var extension = file.IndexOf( '.' );
		return (extension < 0 ? file : file[..extension]).ToLowerInvariant();
	}
}
