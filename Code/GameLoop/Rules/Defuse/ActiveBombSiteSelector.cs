using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Selects one bomb site to be active at the start of this state, enabling spawn points with that
/// site's name as a tag.
/// </summary>
public sealed class ActiveBombSiteSelector : Component,
	IGameEventHandler<EnterStateEvent>
{
	[Sync( SyncFlags.FromHost )] public BombSite CurrentBombSite { get; set; }

	public void OnGameEvent( EnterStateEvent eventArgs )
	{
		var bombSites = Scene.Components
			.GetAll<BombSite>( FindMode.EverythingInSelfAndDescendants )
			.ToArray();

		if ( bombSites.Length == 0 )
		{
			Log.Info( "No bomb sites found! Creating default sites A & B and team spawn points dynamically." );

			// 1. Bombsite A at (-600, 0, 32)
			var siteAGo = new GameObject( true, "bombsite_a" );
			siteAGo.WorldPosition = new Vector3( -600f, 0f, 32f );
			var zoneA = siteAGo.Components.Create<Zone>();
			var boxA = siteAGo.Components.Create<BoxCollider>();
			boxA.Scale = new Vector3( 400f, 400f, 120f );
			boxA.IsTrigger = true;
			var siteA = siteAGo.Components.Create<BombSite>();
			siteA.Index = 0;

			// 2. Bombsite B at (600, 0, 32)
			var siteBGo = new GameObject( true, "bombsite_b" );
			siteBGo.WorldPosition = new Vector3( 600f, 0f, 32f );
			var zoneB = siteBGo.Components.Create<Zone>();
			var boxB = siteBGo.Components.Create<BoxCollider>();
			boxB.Scale = new Vector3( 400f, 400f, 120f );
			boxB.IsTrigger = true;
			var siteB = siteBGo.Components.Create<BombSite>();
			siteB.Index = 1;

			// Spawns for Site A:
			// CT spawns near A
			for ( int i = 0; i < 5; i++ )
			{
				var ctGo = new GameObject( true, $"ct_spawn_a_{i}" );
				ctGo.WorldPosition = new Vector3( -400f + (i * 50f), -150f, 32f );
				ctGo.WorldRotation = Rotation.FromYaw( 90f );
				ctGo.Tags.Add( "bombsite_a" );
				var spawn = ctGo.Components.Create<TeamSpawnPoint>();
				spawn.Team = Team.CounterTerrorist;
			}
			// T spawns near A
			for ( int i = 0; i < 5; i++ )
			{
				var tGo = new GameObject( true, $"t_spawn_a_{i}" );
				tGo.WorldPosition = new Vector3( -800f + (i * 50f), 150f, 32f );
				tGo.WorldRotation = Rotation.FromYaw( -90f );
				tGo.Tags.Add( "bombsite_a" );
				var spawn = tGo.Components.Create<TeamSpawnPoint>();
				spawn.Team = Team.Terrorist;
			}

			// Spawns for Site B:
			// CT spawns near B
			for ( int i = 0; i < 5; i++ )
			{
				var ctGo = new GameObject( true, $"ct_spawn_b_{i}" );
				ctGo.WorldPosition = new Vector3( 400f + (i * 50f), -150f, 32f );
				ctGo.WorldRotation = Rotation.FromYaw( 90f );
				ctGo.Tags.Add( "bombsite_b" );
				var spawn = ctGo.Components.Create<TeamSpawnPoint>();
				spawn.Team = Team.CounterTerrorist;
			}
			// T spawns near B
			for ( int i = 0; i < 5; i++ )
			{
				var tGo = new GameObject( true, $"t_spawn_b_{i}" );
				tGo.WorldPosition = new Vector3( 800f + (i * 50f), 150f, 32f );
				tGo.WorldRotation = Rotation.FromYaw( -90f );
				tGo.Tags.Add( "bombsite_b" );
				var spawn = tGo.Components.Create<TeamSpawnPoint>();
				spawn.Team = Team.Terrorist;
			}

			bombSites = Scene.Components
				.GetAll<BombSite>( FindMode.EverythingInSelfAndDescendants )
				.ToArray();
		}

		var bombSite = Random.Shared.FromArray( bombSites );

		CurrentBombSite = bombSite;

		var name = bombSite.GameObject.Name.ToLower();
		// Every spawn, the ones the last round's site switched off included. GetComponentsInChildren only finds enabled
		// ones, so the first round at the other site switched every spawn off, and both teams spawned together at the
		// world's origin (TeamSpawnAssigner's and the bots' fallback).
		var spawns = Scene.Components.GetAll<TeamSpawnPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray();

		foreach ( var spawn in spawns )
		{
			// Another mode's spawns, under an object the mode leaves off, stay as they are.
			if ( !spawn.GameObject.Active )
				continue;

			spawn.Enabled = spawn.GameObject.Tags.Contains( name );
		}

		foreach ( var team in GameUtils.Teams )
		{
			if ( !spawns.Any( x => x.Enabled && x.GameObject.Active && x.Team == team ) )
				Log.Warning( $"Retakes: {bombSite.GameObject.Name} has no spawns for {team}" );
		}

		GameMode.Instance.ShowToast( $"Retakes: {bombSite.Zone.DisplayName}", duration: 3f );
	}
}
