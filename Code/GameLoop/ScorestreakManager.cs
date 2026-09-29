using Sandbox;
using Sandbox.Events;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

/// <summary>
/// Manages active scorestreaks for both teams.
/// </summary>
public sealed class ScorestreakManager : Component, IGameEventHandler<ResetScoresEvent>
{
	public static ScorestreakManager Instance { get; private set; }

	[Sync( SyncFlags.FromHost )]
	public bool IsUavActiveTerrorist { get; private set; }

	[Sync( SyncFlags.FromHost )]
	public bool IsUavActiveCounterTerrorist { get; private set; }

	private TimeUntil uavEndTimeTerrorist;
	private TimeUntil uavEndTimeCounterTerrorist;
	private ReconDroneVisual terroristDrone;
	private ReconDroneVisual counterTerroristDrone;

	protected override void OnStart()
	{
		Instance = this;
	}

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost )
			return;

		if ( IsUavActiveTerrorist && uavEndTimeTerrorist )
		{
			IsUavActiveTerrorist = false;
			RemoveDrone( Team.Terrorist );
		}

		if ( IsUavActiveCounterTerrorist && uavEndTimeCounterTerrorist )
		{
			IsUavActiveCounterTerrorist = false;
			RemoveDrone( Team.CounterTerrorist );
		}
	}

	public void ActivateUAV( Team team )
	{
		if ( !Networking.IsHost ) return;

		if ( team == Team.Terrorist )
		{
			IsUavActiveTerrorist = true;
			uavEndTimeTerrorist = 30f; // 30 seconds
			EnsureDrone( Team.Terrorist );
		}
		else if ( team == Team.CounterTerrorist )
		{
			IsUavActiveCounterTerrorist = true;
			uavEndTimeCounterTerrorist = 30f; // 30 seconds
			EnsureDrone( Team.CounterTerrorist );
		}
	}

	public bool IsUavActiveForTeam( Team team )
	{
		if ( team == Team.Terrorist ) return IsUavActiveTerrorist;
		if ( team == Team.CounterTerrorist ) return IsUavActiveCounterTerrorist;
		return false;
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;
		IsUavActiveTerrorist = false;
		IsUavActiveCounterTerrorist = false;
		RemoveDrone( Team.Terrorist );
		RemoveDrone( Team.CounterTerrorist );
	}

	private void EnsureDrone( Team team )
	{
		var drone = FindDrone( team );
		if ( !drone.IsValid() ) drone = ReconDroneVisual.Spawn( Scene, team );
		if ( team == Team.Terrorist ) terroristDrone = drone;
		else counterTerroristDrone = drone;
		if ( drone.IsValid() ) drone.Refresh();
	}

	private ReconDroneVisual FindDrone( Team team )
	{
		var cached = team == Team.Terrorist ? terroristDrone : counterTerroristDrone;
		return cached.IsValid() ? cached : Scene.GetAllComponents<ReconDroneVisual>().FirstOrDefault( d => d.ReconTeam == team );
	}

	private void RemoveDrone( Team team )
	{
		var drone = FindDrone( team );
		if ( drone.IsValid() ) drone.GameObject.Destroy();
		if ( team == Team.Terrorist ) terroristDrone = null;
		else counterTerroristDrone = null;
	}

	protected override void OnDestroy()
	{
		if ( Instance == this ) Instance = null;
		if ( !Networking.IsHost ) return;
		if ( terroristDrone.IsValid() ) terroristDrone.GameObject.Destroy();
		if ( counterTerroristDrone.IsValid() ) counterTerroristDrone.GameObject.Destroy();
	}
}
