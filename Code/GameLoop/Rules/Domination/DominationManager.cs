using System;
using System.Collections.Generic;
using System.Linq;
using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public sealed class DominationManager : Component
{
	[Property] public float ScoreTickInterval { get; set; } = 5f;

	private readonly List<DominationFlag> _flags = new();
	private TimeSince _timeSinceLastScoreTick;

	protected override void OnStart()
	{
		_timeSinceLastScoreTick = 0f;

		if ( Networking.IsHost )
		{
			SpawnFlags();
		}
	}

	private void SpawnFlags()
	{
		// A map's own flag spots (ObjectiveSpot), named by their labels.
		var spots = ObjectiveSpot.All( Scene, ObjectiveSpot.SpotKind.Domination );
		if ( spots.Count >= 3 )
		{
			foreach ( var spot in spots )
				CreateFlag( spot.Label, spot.WorldPosition );
			return;
		}

		var spawnPoints = GameUtils.GetSpawnPoints().Select( x => x.Transform.Position ).ToList();

		Vector3 posA, posB, posC;

		if ( spawnPoints.Count < 2 )
		{
			// Fallback coordinates if no spawn points are found
			posA = new Vector3( -1000, 0, 0 );
			posB = new Vector3( 0, 0, 0 );
			posC = new Vector3( 1000, 0, 0 );
		}
		else
		{
			// Find two spawn points furthest from each other
			Vector3 bestP1 = spawnPoints[0];
			Vector3 bestP2 = spawnPoints[1];
			float maxDistSq = 0f;

			for ( int i = 0; i < spawnPoints.Count; i++ )
			{
				for ( int j = i + 1; j < spawnPoints.Count; j++ )
				{
					float distSq = spawnPoints[i].DistanceSquared( spawnPoints[j] );
					if ( distSq > maxDistSq )
					{
						maxDistSq = distSq;
						bestP1 = spawnPoints[i];
						bestP2 = spawnPoints[j];
					}
				}
			}

			posA = bestP1;
			posC = bestP2;

			// Find spawn point closest to the midpoint of A and C
			Vector3 mid = (posA + posC) / 2f;
			Vector3 bestMid = mid;
			float minDistSq = float.MaxValue;

			foreach ( var p in spawnPoints )
			{
				if ( p == posA || p == posC )
					continue;

				float distSq = p.DistanceSquared( mid );
				if ( distSq < minDistSq )
				{
					minDistSq = distSq;
					bestMid = p;
				}
			}

			// If B ended up on A or C because there are only 2 spawn points, offset B
			if ( bestMid == posA || bestMid == posC )
			{
				posB = mid;
			}
			else
			{
				posB = bestMid;
			}
		}

		CreateFlag( "A", posA );
		CreateFlag( "B", posB );
		CreateFlag( "C", posC );
	}

	private void CreateFlag( string name, Vector3 pos )
	{
		// Try to trace to floor to make sure it stands on the ground properly
		var trace = Scene.Trace.Ray( pos + Vector3.Up * 50f, pos + Vector3.Down * 200f )
			.IgnoreGameObjectHierarchy( GameObject )
			.Run();

		Vector3 spawnPos = trace.Hit ? trace.HitPosition : pos;

		var go = new GameObject( true, $"Flag_{name}" );
		go.WorldPosition = spawnPos;

		var flag = go.Components.Create<DominationFlag>();
		flag.FlagName = name;

		// Add Visuals (ModelRenderer)
		var mr = go.Components.Create<ModelRenderer>();
		mr.Model = Model.Load( "models/gameplay/flag_pole_base/flag_pole_base.vmdl" );
		flag.FlagModel = mr;

		// Add Trigger (BoxCollider)
		var trigger = go.Components.Create<BoxCollider>();
		trigger.IsTrigger = true;
		trigger.Scale = new Vector3( 600f, 600f, 150f ); // 300f radius, 150f height

		go.NetworkSpawn();
		_flags.Add( flag );
	}

	protected override void OnUpdate()
	{
		if ( !Networking.IsHost )
			return;

		if ( _timeSinceLastScoreTick >= ScoreTickInterval )
		{
			_timeSinceLastScoreTick = 0f;
			TickScores();
		}
	}

	private void TickScores()
	{
		var teamScoring = GameMode.Instance?.Get<TeamScoring>();
		if ( teamScoring is null || !teamScoring.IsValid() )
			return;

		// Find flags dynamically in case they aren't fully resolved/spawning async
		var activeFlags = Scene.GetAllComponents<DominationFlag>().ToList();

		int tFlags = activeFlags.Count( x => x.ControllingTeam == Team.Terrorist );
		int ctFlags = activeFlags.Count( x => x.ControllingTeam == Team.CounterTerrorist );

		if ( tFlags > 0 )
		{
			teamScoring.IncrementScore( Team.Terrorist, tFlags );
		}

		if ( ctFlags > 0 )
		{
			teamScoring.IncrementScore( Team.CounterTerrorist, ctFlags );
		}
	}
}
