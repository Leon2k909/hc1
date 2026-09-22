using Sandbox;
using Facepunch;
using System;
using System.Reflection;

/// <summary>Checks the weapon damage route against a zombie in an isolated scene.</summary>
public static class Hc1ZombieDamageQa
{
	[ConCmd( "hc1_zombie_damage_qa" )]
	public static void Run()
	{
		if ( Game.IsPlaying ) throw new Exception( "Stop play before running zombie damage QA." );
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var root = new GameObject( true, "Zombie damage QA" );
			var renderer = root.Components.Create<SkinnedModelRenderer>();
			renderer.Model = Model.Load( ZombieAI.DriverModel );
			root.Components.Create<NavMeshAgent>();
			var zombie = root.Components.Create<ZombieAI>();
			typeof( ZombieAI ).GetMethod( "OnStart", BindingFlags.Instance | BindingFlags.NonPublic ).Invoke( zombie, null );
			var body = new GameObject( root, true, "Body" );
			var hit = new Facepunch.DamageInfo( null, 10f, Position: new Vector3( 0, 0, 30 ) );
			Require( Tec.Utils.CreateDamageInfo( hit ).Position == hit.Position, "hit position survives conversion" );
			Require( root.TakeDamage( hit ) && zombie.Health == 90f, "root hit deals damage once" );
			Require( body.TakeDamage( hit ) && zombie.Health == 80f, "child mesh hit reaches zombie once" );
			var head = renderer.Bounds.Maxs - Vector3.Up;
			Require( body.TakeDamage( hit with { Position = head } ) && zombie.Health == 60f, "headshot doubles damage" );
			body.TakeDamage( hit with { Damage = 100f } );
			var deadHealth = zombie.Health;
			Require( deadHealth <= 0f, "lethal damage kills zombie" );
			body.TakeDamage( hit );
			Require( zombie.Health == deadHealth, "dead zombie ignores further damage" );
			Log.Info( "HC1_ZOMBIE_DAMAGE_QA PASS: root hit, child hit, headshot, kill and corpse guard" );
		}
		finally { scene.Destroy(); }
	}

	private static void Require( bool condition, string message )
	{
		if ( !condition ) throw new Exception( $"HC1_ZOMBIE_DAMAGE_QA FAIL: {message}" );
	}
}
