using System;
using System.Collections.Generic;
using System.Linq;
using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public sealed class HardpointManager : Component
{
	[Property] public float RelocationInterval { get; set; } = 60f;
	[Property] public float ScoreTickInterval { get; set; } = 1f;

	[Property, Sync( SyncFlags.FromHost )]
	public float RelocateTimer { get; set; } = 60f;

	private List<Vector3> _locations = new();
	private int _currentLocationIndex = -1;
	private HardpointZone _zone;

	private TimeSince _timeSinceLastScoreTick;
	private TimeSince _timeSinceLastRelocation;

	protected override void OnStart()
	{
		_timeSinceLastScoreTick = 0f;
		_timeSinceLastRelocation = 0f;
		RelocateTimer = RelocationInterval;

		if ( Networking.IsHost )
			InitHardpoint();
	}

	private void InitHardpoint()
	{
		_locations = SelectHardpointLocations();
		if ( _locations.Count == 0 )
			return;

		// Spawn the Zone object
		var go = new GameObject( true, "Hardpoint_Zone" );
		
		// Add HardpointZone component
		_zone = go.Components.Create<HardpointZone>();

		// Add Visuals (ModelRenderer)
		var mr = go.Components.Create<ModelRenderer>();
		mr.Model = Model.Load( "models/gameplay/flag_pole_base/flag_pole_base.vmdl" );
		_zone.FlagModel = mr;

		// Add Trigger (BoxCollider)
		var trigger = go.Components.Create<BoxCollider>();
		trigger.IsTrigger = true;
		trigger.Scale = new Vector3( 600f, 600f, 150f ); // 300f radius

		go.NetworkSpawn();

		RelocateZone();
	}

	private List<Vector3> SelectHardpointLocations()
	{
		// A map's own zone spots (ObjectiveSpot), if it has any.
		var spots = ObjectiveSpot.All( Scene, ObjectiveSpot.SpotKind.HotZone );
		if ( spots.Count > 0 )
			return spots.Select( x => x.WorldPosition ).ToList();

		var spawnPoints = GameUtils.GetSpawnPoints().Select( x => x.Transform.Position ).ToList();
		if ( spawnPoints.Count == 0 )
		{
			// Fallback coordinates if no spawn points are found
			return new List<Vector3> {
				new Vector3( 0, 0, 0 ),
				new Vector3( -1000, 0, 0 ),
				new Vector3( 1000, 0, 0 ),
				new Vector3( 0, -1000, 0 ),
				new Vector3( 0, 1000, 0 )
			};
		}

		// De-duplicate spawn points that are very close to each other (within 150 units)
		var uniquePoints = new List<Vector3>();
		foreach ( var p in spawnPoints )
		{
			if ( !uniquePoints.Any( x => x.Distance( p ) < 150f ) )
			{
				uniquePoints.Add( p );
			}
		}

		if ( uniquePoints.Count <= 5 )
		{
			return uniquePoints;
		}

		// Select 5 spread-out points
		var selected = new List<Vector3>();
		
		// 1. Pick the first point randomly
		selected.Add( uniquePoints[Game.Random.Int( 0, uniquePoints.Count - 1 )] );

		// 2. Iteratively pick the point that is furthest from the already selected points
		while ( selected.Count < 5 && selected.Count < uniquePoints.Count )
		{
			Vector3 bestPoint = uniquePoints[0];
			float maxMinDist = -1f;

			foreach ( var p in uniquePoints )
			{
				if ( selected.Contains( p ) )
					continue;

				// Find minimum distance to any already selected point
				float minDist = selected.Min( x => x.Distance( p ) );
				if ( minDist > maxMinDist )
				{
					maxMinDist = minDist;
					bestPoint = p;
				}
			}

			selected.Add( bestPoint );
		}

		return selected;
	}

	private void RelocateZone()
	{
		if ( !_zone.IsValid() || _locations.Count == 0 )
			return;

		// Pick a new location that is different from the current one (if multiple exist)
		int newIndex = _currentLocationIndex;
		if ( _locations.Count > 1 )
		{
			while ( newIndex == _currentLocationIndex )
			{
				newIndex = Game.Random.Int( 0, _locations.Count - 1 );
			}
		}
		else
		{
			newIndex = 0;
		}

		_currentLocationIndex = newIndex;
		Vector3 rawPos = _locations[_currentLocationIndex];

		// Try to trace to floor to make sure it stands on the ground properly
		var trace = Scene.Trace.Ray( rawPos + Vector3.Up * 50f, rawPos + Vector3.Down * 200f )
			.IgnoreGameObjectHierarchy( _zone.GameObject )
			.Run();

		Vector3 spawnPos = trace.Hit ? trace.HitPosition : rawPos;

		_zone.GameObject.WorldPosition = spawnPos;

		// Reset capture status
		_zone.ControllingTeam = Team.Unassigned;
		_zone.IsContested = false;
		_zone.ClearPlayers();
		_zone.UpdateVisuals();

		_timeSinceLastRelocation = 0f;

		Facepunch.UI.Toast.Instance?.Show( "The zone has moved!", Facepunch.UI.ToastType.Generic );
	}

	protected override void OnUpdate()
	{
		if ( !Networking.IsHost )
			return;

		// Tick down relocation timer
		RelocateTimer = RelocationInterval - _timeSinceLastRelocation;

		if ( _timeSinceLastRelocation >= RelocationInterval )
		{
			RelocateZone();
		}

		if ( _timeSinceLastScoreTick >= ScoreTickInterval )
		{
			_timeSinceLastScoreTick = 0f;
			TickScores();
		}
	}

	private void TickScores()
	{
		if ( !_zone.IsValid() || _zone.IsContested || _zone.ControllingTeam == Team.Unassigned )
			return;

		var teamScoring = GameMode.Instance?.Get<TeamScoring>();
		if ( teamScoring is null || !teamScoring.IsValid() )
			return;

		teamScoring.IncrementScore( _zone.ControllingTeam, 1 );
	}
}
