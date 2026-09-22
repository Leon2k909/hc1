using Editor;
using Sandbox;
using Facepunch;
using SWB.Base;
using System;
using System.IO;
using System.Linq;
using System.Reflection;

/// <summary>Exercises tracer effects in a temporary scene without firing at players or changing loadouts.</summary>
public static class Hc1TracerQa
{
	[ConCmd( "hc1_tracer_qa" )]
	public static void Run()
	{
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var source = new GameObject( false, "Tracer QA" );
			var shoot = source.Components.Create<ShootInfo>();
			var hitscan = source.Components.Create<HitScanBulletInfo>();
			var physical = source.Components.Create<PhysicalBulletInfo>();
			var particle = shoot.BulletTracerParticle;
			Require( particle is not null, "tracer prefab is available" );
			Require( !shoot.UsesTracerRounds, "ordinary ammo is the default" );
			foreach ( BulletInfo bullet in new BulletInfo[] { hitscan, physical } )
			{
				shoot.UsesTracerRounds = false;
				shoot.BulletTracerChance = 1f;
				Require( !bullet.ShouldSpawnTracer( shoot ), "ordinary ammo blocks even 100% tracer chance" );
				shoot.UsesTracerRounds = true;
				Require( bullet.ShouldSpawnTracer( shoot ), "equipped tracer rounds enable trails" );
				shoot.BulletTracerChance = 0f;
				Require( !bullet.ShouldSpawnTracer( shoot ), "zero tracer chance is respected" );
				shoot.BulletTracerChance = 1f;
				shoot.BulletTracerParticle = null;
				Require( !bullet.ShouldSpawnTracer( shoot ), "missing effect has no trail" );
				shoot.BulletTracerParticle = particle;
				Require( !bullet.ShouldSpawnTracer( null ), "missing ammo settings have no trail" );
			}

			var bot = source.Components.Create<LightweightCombatBot>();
			bot.WeaponWorldModelPrefab = "";
			bot.MuzzleFlashPrefab = "";
			bot.ShootSound = "";
			Require( !bot.UsesTracerRounds, "bots start with ordinary ammo" );
			var effects = typeof( LightweightCombatBot ).GetMethod( "DoShootEffects", BindingFlags.Instance | BindingFlags.NonPublic );
			Require( effects is not null, "bot shot effect entry point exists" );
			var start = Vector3.Zero;
			var end = Vector3.Forward * 1000f;
			effects.Invoke( bot, new object[] { start, end, false } );
			Require( !scene.GetAllComponents<Tracer>().Any(), "ordinary bot shot spawns no beam" );
			effects.Invoke( bot, new object[] { start, end, true } );
			Require( scene.GetAllComponents<Tracer>().Count() == 1, "tracer bot shot spawns one beam" );
			bot.UsesTracerRounds = true;
			effects.Invoke( bot, new object[] { start, end, false } );
			Require( scene.GetAllComponents<Tracer>().Count() == 1, "observers use the shot payload, not local ammo state" );

			var folder = Path.Combine( Project.Current.GetRootPath(), "Sources", "UI", "qa", "menu-fixes" );
			Directory.CreateDirectory( folder );
			File.WriteAllText( Path.Combine( folder, "tracer-validation.txt" ),
				"PASS: ordinary/tracer ammo for hitscan, physical bullets and bot effects; shot payload controls observer trails.\n" );
			Log.Info( "HC1_TRACER_QA PASS: hitscan, physical and bot tracer gating" );
		}
		finally { scene.Destroy(); }
	}

	private static void Require( bool condition, string message )
	{
		if ( !condition ) throw new Exception( $"HC1_TRACER_QA FAIL: {message}" );
	}
}
