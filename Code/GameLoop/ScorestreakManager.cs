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
		}

		if ( IsUavActiveCounterTerrorist && uavEndTimeCounterTerrorist )
		{
			IsUavActiveCounterTerrorist = false;
		}
	}

	public void ActivateUAV( Team team )
	{
		if ( !Networking.IsHost ) return;

		if ( team == Team.Terrorist )
		{
			IsUavActiveTerrorist = true;
			uavEndTimeTerrorist = 30f; // 30 seconds
		}
		else if ( team == Team.CounterTerrorist )
		{
			IsUavActiveCounterTerrorist = true;
			uavEndTimeCounterTerrorist = 30f; // 30 seconds
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
		IsUavActiveTerrorist = false;
		IsUavActiveCounterTerrorist = false;
	}
}
