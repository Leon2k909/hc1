using Editor;
using Sandbox;
using System.IO;

/// <summary>Read the red container's loaded material without changing the editor or match.</summary>
public static class Hc1LowtideContainerQa
{
	[ConCmd( "hc1_lowtide_container_check" )]
	public static void Check()
	{
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/container-pass" );
		Directory.CreateDirectory( folder );
		var material = Material.Load( "materials/lowtide/containers/lt_container_red.vmat" );
		var color = material.GetTexture( "g_tColor" );
		var normal = material.GetTexture( "g_tNormal" );
		File.WriteAllLines( Path.Combine( folder, "native-material.txt" ), new[]
		{
			$"material-error={material.IsError}, shader={material.ShaderName}",
			$"colour-dimensions={color?.Width}x{color?.Height}, mips={color?.Mips}",
			$"normal-dimensions={normal?.Width}x{normal?.Height}, mips={normal?.Mips}",
			$"specular={material.GetFeature( "F_SPECULAR" )}, metalness-texture={material.GetFeature( "F_METALNESS_TEXTURE" )}"
		} );
		Log.Info( $"Lowtide red-container material error={material.IsError}" );
	}
}
