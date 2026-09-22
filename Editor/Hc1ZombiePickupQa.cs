using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Reflection;

public static class Hc1ZombiePickupQa
{
	[ConCmd( "hc1_zombie_pickup_qa" )]
	public static void Run()
	{
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var pickup = new GameObject( true, "Ammo QA" );
			typeof( ZombiesPowerUp ).GetMethod( "CreateAmmoCase", BindingFlags.Static | BindingFlags.NonPublic ).Invoke( null, new object[] { pickup } );
			var models = pickup.GetComponentsInChildren<ModelRenderer>().ToArray();
			Require( models.Length == 10 && models.All( r => r.Model is not null && !r.Model.IsError ), "ammo case and three magazine models load" );
			var camera = new GameObject( true, "Camera" ).Components.Create<CameraComponent>();
			camera.WorldPosition = new Vector3( 65, -70, 45 );
			camera.WorldRotation = Rotation.LookAt( new Vector3( 0, 0, 4 ) - camera.WorldPosition );
			camera.FieldOfView = 40f;
			camera.BackgroundColor = new Color( 0.09f, 0.11f, 0.13f );
			var light = new GameObject( true, "Light" ).Components.Create<DirectionalLight>();
			light.WorldRotation = Rotation.From( 40, 25, 0 );
			light.LightColor = Color.White * 2;
			light.SkyColor = Color.White * 0.6f;
			scene.EditorTick( 1f / 60, 1f / 60 );
			using var bitmap = new Bitmap( 800, 800 );
			camera.RenderToBitmap( bitmap );
			File.WriteAllBytes( Path.Combine( Path.GetTempPath(), "hc1-max-ammo.png" ), bitmap.ToPng() );

			var cc = new GameObject( true, "Crawl QA" ).Components.Create<Facepunch.CharacterController>();
			cc.Acceleration = 10f;
			foreach ( var speed in new[] { 50f, 12.5f } )
			{
				cc.Velocity = Vector3.Zero;
				for ( int i = 0; i < 60; i++ )
				{
					scene.EditorTick( 1f / 60, 1f / 60 );
					cc.Accelerate( Vector3.Forward * speed );
					cc.ApplyFriction( 4f, speed );
				}
				Require( cc.Velocity.x > speed * 0.5f, $"crawl moves at wish speed {speed}: {cc.Velocity}" );
			}
			Log.Info( "HC1_ZOMBIE_PICKUP_QA PASS: ammo models valid; normal and downed crawl retain velocity" );
		}
		finally { scene.Destroy(); }
	}

	private static void Require( bool condition, string message )
	{
		if ( !condition ) throw new Exception( message );
	}
}
