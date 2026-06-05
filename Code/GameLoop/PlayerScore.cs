using Sandbox.Events;

namespace Facepunch.UI;

public record OnScoreAddedEvent : IGameEvent
{
	public int Score { get; set; }
	public string Reason { get; set; }
}

/// <summary>
/// Plop this on something you're using <see cref="ScoreAttribute"/> for. We could codegen this attribute on components that use it to save this hassle.
/// </summary>
public interface IScore
{
	/// <summary>
	/// Looks for a bunch of score attributes from components on a <see cref="Client"/>, and returns a formatted, sorted list of values.
	/// </summary>
	/// <param name="Client"></param>
	/// <returns></returns>
	public static IEnumerable<(object Value, ScoreAttribute Attribute)> Find( Client Client )
	{
		var components = Client.GetComponentsInChildren<IScore>();
		var values = new List<(object Value, MemberDescription Member, ScoreAttribute Attribute)>();

		foreach ( var comp in components )
		{
			var type = TypeLibrary.GetType( comp.GetType() );

			foreach ( var member in type.Members )
			{
				if ( member.GetCustomAttribute<ScoreAttribute>() is not { } scoreAttribute )
					continue;

				if ( scoreAttribute.ShowTeamOnly && !Client.IsFriendly( Client.Local ) )
					continue;

				// Support ShowIf, which looks for a method with a boolean return to see if we can display a value
				var show = type.GetMethod( scoreAttribute.ShowIf )?.InvokeWithReturn<bool>( comp, null ) ?? true;
				if ( !show )
					continue;

				// Support special formatting values
				values.Add( (
					string.Format( scoreAttribute.Format, type.GetValue( comp, member.Name ) ),
					member, scoreAttribute
				) );
			}
		}

		return values.OrderBy( x => x.Member.GetCustomAttribute<OrderAttribute>()?.Value ?? 0 )
			// We don't need to expose x.Member
			.Select( x => (x.Value, x.Attribute) );
	}
}

[AttributeUsage( AttributeTargets.Property, AllowMultiple = false )]
public class ScoreAttribute : System.Attribute
{
	public string Name { get; set; }
	public string Format { get; set; } = "{0}";
	public string ShowIf { get; set; } = null;
	public bool ShowTeamOnly { get; set; } = false;

	public ScoreAttribute( string name )
	{
		Name = name;
	}
}

/// <summary>
/// Handles all the player score values.
/// </summary>
public sealed class PlayerScore : Component,
	IGameEventHandler<KillEvent>,
	IGameEventHandler<BombDefusedEvent>,
	IGameEventHandler<BombDetonatedEvent>,
	IGameEventHandler<BombPlantedEvent>,
	IGameEventHandler<RoundCounterIncrementedEvent>,
	IGameEventHandler<RoundCounterResetEvent>,
	IGameEventHandler<ResetScoresEvent>,
	IScore
{
	[Property] public Client Client { get; set; }

	[Sync( SyncFlags.FromHost ), Property, ReadOnly, Score( "Kills" )]
	public int Kills { get; set; } = 0;

	[Sync( SyncFlags.FromHost ), Property, ReadOnly, Score( "Deaths" )]
	public int Deaths { get; set; } = 0;

	[Sync( SyncFlags.FromHost ), Property, ReadOnly, Score( "Points" ), Order( -1 )]
	public int Score { get; private set; } = 0;

	[Sync( SyncFlags.FromHost ), Property, ReadOnly]
	public int KillStreak { get; set; } = 0;

	/// <summary>
	/// This player's chosen streak mode. Set by the owning client from their
	/// <see cref="GameSettings"/> on spawn; the host reads it when evaluating rewards.
	/// Each player can independently choose killstreaks or scorestreaks.
	/// </summary>
	[Sync]
	public bool UseScorestreaks { get; set; } = false;

	/// <summary>
	/// Accumulated score toward the next scorestreak reward (does not reset on death).
	/// Only relevant when <see cref="UseScorestreaks"/> is true for this player.
	/// </summary>
	[Sync( SyncFlags.FromHost ), Property, ReadOnly]
	public int ScorestreakPoints { get; private set; } = 0;

	/// <summary>
	/// Number of UAVs the player has earned and banked to be called in.
	/// </summary>
	[Sync( SyncFlags.FromHost ), Property, ReadOnly]
	public int BankedUAVs { get; set; } = 0;

	/// Score threshold for a UAV in scorestreak mode (≈ 6 kills, or fewer with objectives mixed in).
	private const int UavScorestreakCost = 150;

	protected override void OnStart()
	{
		// If this is the local player's score component, seed the preference from their settings.
		if ( Client.IsValid() && Client == Client.Local )
		{
			UseScorestreaks = GameSettingsSystem.Current.UseScorestreaks;
		}
	}

	/// <summary>
	/// Adds score to this player.
	/// When <paramref name="countsTowardStreak"/> is false the points won't feed the
	/// scorestreak meter (used for the UAV bonus itself to avoid double-counting).
	/// </summary>
	public void AddScore( int score, string reason = null, bool countsTowardStreak = true )
	{
		Score += score;

		// Feed scorestreak meter on the host (only positive score, only when enabled).
		if ( countsTowardStreak && Networking.IsHost && score > 0 && UseScorestreaks )
		{
			ScorestreakPoints += score;
			CheckScorestreakRewards();
		}

		if ( Client.IsBot ) return;

		using ( Rpc.FilterInclude( Network.Owner ) )
		{
			SendScoreAdded( score, reason );
		}
	}

	/// <summary>
	/// Fires any scorestreak rewards the player has banked enough points for,
	/// then awards the deployment bonus without re-feeding the meter.
	/// </summary>
	private void CheckScorestreakRewards()
	{
		if ( !Networking.IsHost ) return;

		var thisPlayer = Client?.PlayerPawn;
		if ( !thisPlayer.IsValid() ) return;

		while ( ScorestreakPoints >= UavScorestreakCost )
		{
			ScorestreakPoints -= UavScorestreakCost;
			BankedUAVs++;
			
			using ( Rpc.FilterInclude( Network.Owner ) )
			{
				SendScoreAdded( 0, "UAV Earned! Press [Scorestreak] to call in." );
			}
		}
	}

	[Rpc.Owner]
	public void CallInUAV()
	{
		if ( BankedUAVs > 0 )
		{
			BankedUAVs--;
			ScorestreakManager.Instance?.ActivateUAV( Client.Team );
			AddScore( 50, "UAV Deployed", countsTowardStreak: false );
		}
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void SendScoreAdded( int score, string reason = null )
	{
		Scene.Dispatch<OnScoreAddedEvent>( new OnScoreAddedEvent()
		{
			Score = score,
			Reason = reason
		} );
	}

	[Score( "Ratio", Format = "{0:0.00}" ), Order( 50 )]
	public float Ratio => (float)Kills / (float)Deaths.Clamp( 1, int.MaxValue );

	[Sync( SyncFlags.FromHost )]
	public NetList<int> ScoreHistory { get; private set; } = new();

	[Sync( SyncFlags.FromHost )]
	public bool WasBombPlanter { get; private set; }

	private const int KillScore = 25;
	private const int TeamKillScore = -25;
	private const int SuicideScore = -10;

	// Planting the C4 explosive
	private const int PlantScore = 25;

	// Bomb planter alive when the bomb explodes
	private const int BombExplodePlanterAliveScore = 35;

	// Bomb planter dead when the bomb explodes
	private const int BombExplodePlanterDeadScore = 10;

	// Other Ts alive when the bomb explodes
	private const int BombExplodeTeamAliveScore = 25;

	// Defusing bomb
	private const int DefuserScore = 50;

	// Other CTs alive when the bomb is defused
	private const int DefuseTeamAliveScore = 25;

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		var damageInfo = eventArgs.DamageInfo;

		if ( !damageInfo.Attacker.IsValid() ) return;
		if ( !damageInfo.Victim.IsValid() ) return;

		var thisPlayer = Client?.PlayerPawn;
		if ( !thisPlayer.IsValid() ) return;

		var killerPlayer = GameUtils.GetPlayerFromComponent( damageInfo.Attacker );
		var victimPlayer = GameUtils.GetPlayerFromComponent( damageInfo.Victim );
		var killerBot = GameUtils.GetLightweightBotFromComponent( damageInfo.Attacker );
		var victimBot = GameUtils.GetLightweightBotFromComponent( damageInfo.Victim );

		if ( !victimPlayer.IsValid() && !victimBot.IsValid() ) return;

		if ( !killerPlayer.IsValid() && !killerBot.IsValid() )
		{
			if ( victimPlayer == thisPlayer )
				Deaths++;

			return;
		}

		var killerTeam = GameUtils.GetTeamFromComponent( damageInfo.Attacker );
		var victimTeam = GameUtils.GetTeamFromComponent( damageInfo.Victim );
		var isFriendly = killerTeam != Team.Unassigned && killerTeam == victimTeam;
		var isSuicide = killerPlayer == victimPlayer;

		if ( killerPlayer == thisPlayer )
		{
			if ( isFriendly )
			{
				// Killed by friendly/teammate
				Kills--;
				AddScore( TeamKillScore, "Team kill" );
			}
			else if ( isSuicide )
			{
				// Killed by suicide
				Kills--;
				AddScore( SuicideScore, "Suicide" );
			}
			else
			{
				// Valid kill, add score
				Kills++;
				KillStreak++;
				AddScore( KillScore, "Killed a player" );

				// Killstreak mode: UAV fires at exactly 3 consecutive kills.
				// Scorestreak mode: UAV is handled inside AddScore → CheckScorestreakRewards.
				if ( !UseScorestreaks && KillStreak == 3 )
				{
					BankedUAVs++;
					
					using ( Rpc.FilterInclude( Network.Owner ) )
					{
						SendScoreAdded( 0, "UAV Earned! Press [Scorestreak] to call in." );
					}
				}
			}
		}
		else if ( victimPlayer == thisPlayer )
		{
			// Killstreak mode resets the streak on death; scorestreak mode carries it across deaths.
			if ( !UseScorestreaks )
			{
				KillStreak = 0;
			}
			// Only count as death if this wasn't a team kill
			if ( !isFriendly )
			{
				Deaths++;
			}
		}
	}

	void IGameEventHandler<BombPlantedEvent>.OnGameEvent( BombPlantedEvent eventArgs )
	{
		var thisPlayer = Client?.PlayerPawn;
		var planterPlayer = eventArgs.Planter;

		if ( planterPlayer == thisPlayer )
		{
			// Planter is the current player
			AddScore( PlantScore, "Planted the bomb" );

			WasBombPlanter = true;
		}
		else
		{
			WasBombPlanter = false;
		}
	}

	void IGameEventHandler<BombDefusedEvent>.OnGameEvent( BombDefusedEvent eventArgs )
	{
		var thisPlayer = Client?.PlayerPawn;
		var defuserPlayer = eventArgs.Defuser;

		if ( defuserPlayer == thisPlayer )
		{
			// Defuser is the current player
			AddScore( DefuserScore, "Defused the bomb" );

		}
		else if ( thisPlayer is not null )
		{
			// Defuser is a teammate
			if ( defuserPlayer.Team == thisPlayer.Team && thisPlayer.HealthComponent.State == LifeState.Alive )
			{
				AddScore( DefuseTeamAliveScore, "Team defused the bomb" );
			}
		}
	}

	void IGameEventHandler<BombDetonatedEvent>.OnGameEvent( BombDetonatedEvent eventArgs )
	{
		var thisPlayer = Client?.PlayerPawn;
		var planterPlayer = GameUtils.PlayerPawns
			.FirstOrDefault( x => x.Client.GetComponent<PlayerScore>() is { WasBombPlanter: true } );

		if ( planterPlayer == thisPlayer )
		{
			if ( planterPlayer?.HealthComponent.State == LifeState.Alive )
			{
				// Planter is alive when the bomb explodes
				AddScore( BombExplodePlanterAliveScore, "Bomb exploded" );
			}
			else
			{
				// Planter is dead when the bomb explodes
				AddScore( BombExplodePlanterDeadScore, "Bomb exploded" );
			}
		}
		else if ( planterPlayer?.Team == thisPlayer?.Team && thisPlayer.HealthComponent.State == LifeState.Alive )
		{
			// Teammate is alive when the bomb explodes
			AddScore( BombExplodeTeamAliveScore, "Bomb exploded" );
		}
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent eventArgs )
	{
		Kills = 0;
		Deaths = 0;
		Score = 0;
		KillStreak = 0;
		ScorestreakPoints = 0;
		BankedUAVs = 0;

		ScoreHistory.Clear();

		WasBombPlanter = false;
	}

	void IGameEventHandler<RoundCounterIncrementedEvent>.OnGameEvent( RoundCounterIncrementedEvent eventArgs )
	{
		ScoreHistory.Add( Score - ScoreHistory.LastOrDefault() );
	}

	void IGameEventHandler<RoundCounterResetEvent>.OnGameEvent( RoundCounterResetEvent eventArgs )
	{
		ScoreHistory.Clear();
	}
}
