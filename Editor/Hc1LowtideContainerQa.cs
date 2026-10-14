using Editor;
using Sandbox;
using System.Collections.Generic;
using System.IO;
using System.Linq;

/// <summary>Read Lowtide container materials without changing the editor or match.</summary>
public static class Hc1LowtideContainerQa
{
	[ConCmd( "hc1_lowtide_container_check" )]
	public static void Check()
	{
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/containers" );
		Directory.CreateDirectory( folder );
		var report = new List<string>();
		foreach ( var colour in new[] { "blue", "red", "grey" } )
		{
			foreach ( var suffix in new[] { "", "_frame" } )
			{
				var path = $"materials/lowtide/containers/lt_container_{colour}{suffix}.vmat";
				var material = Material.Load( path );
				var color = material.GetTexture( "g_tColor" );
				var normal = material.GetTexture( "g_tNormal" );
				report.Add( $"{path}: error={material.IsError}, shader={material.ShaderName}, colour={color?.Width}x{color?.Height}, colour-mips={color?.Mips}, normal={normal?.Width}x{normal?.Height}, normal-mips={normal?.Mips}, specular={material.GetFeature( "F_SPECULAR" )}, metalness-texture={material.GetFeature( "F_METALNESS_TEXTURE" )}" );
			}
		}
		foreach ( var side in new[] { "east", "west" } )
		{
			var model = Model.Load( $"models/maps/lowtide/lowtide_dress_{side}.vmdl" );
			report.Add( $"{side}: model-error={model.IsError}, material-errors={model.Materials.Count( m => m is null || m.IsError )}" );
			foreach ( var material in model.Materials.Where( m => m?.ResourcePath.Contains( "/containers/" ) == true ) )
				report.Add( $"{side}: container-material={material.ResourcePath}" );
		}
		File.WriteAllLines( Path.Combine( folder, "native-material.txt" ), report );
		Log.Info( "Lowtide blue, red and grey container materials checked" );
	}
}
