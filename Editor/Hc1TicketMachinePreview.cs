using Editor;
using Sandbox;
using System;
using System.IO;
using System.Linq;

// Temporary visual QA: sync only the newly authored hood lamps into the running map.
public static class Hc1TicketMachinePreview
{
	[ConCmd( "hc1_ticket_machine_lights" )]
	public static void Lights()
	{
		var scene = Game.ActiveScene;
		if ( !Game.IsPlaying || scene is null ) return;
		using var scope = scene.Push();
		var count = 0;
		foreach ( var sign in new[] { -1, 1 } )
		foreach ( var n in new[] { 700, 1060, 1100 } )
		{
			var xs = new[] { -8.95f, 2f };
			for ( var k = 0; k < xs.Length; k++ )
			{
				var name = $"Ticket {(sign == 1 ? "East" : "West")} {n} lamp {k + 1}";
				var lamp = scene.GetAllComponents<PointLight>().FirstOrDefault( light => light.GameObject.Name == name );
				if ( lamp is null ) lamp = new GameObject( true, name ).AddComponent<PointLight>();
				lamp.WorldPosition = new Vector3( n - sign * xs[k], -sign * 1138.05f, 57.25f );
				lamp.LightColor = new Color( .8f, .65f, .475f );
				lamp.Radius = 10;
				lamp.Shadows = false;
				lamp.FogStrength = 0;
				count++;
			}
		}
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/railhead/ticket_machine" );
		Directory.CreateDirectory( folder );
		File.WriteAllText( Path.Combine( folder, "lights.txt" ), $"{count} reference hood lamps in the running map at the saved scene positions\n" );
	}
}
