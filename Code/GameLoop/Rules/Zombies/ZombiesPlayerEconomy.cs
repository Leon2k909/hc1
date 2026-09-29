using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public record PointsAwardedEvent( int Amount ) : Sandbox.Events.IGameEvent;

public sealed class ZombiesPlayerEconomy : Component
{
	public const int StartingPoints = 500;

	[Property, Sync( SyncFlags.FromHost )] public int Points { get; private set; } = StartingPoints;

	/// <summary>Zombies killed this game (the scoreboard's kills), carried over between lives like the points.</summary>
	[Sync( SyncFlags.FromHost )] public int Kills { get; private set; }

	/// <param name="amount">The points before Point Boost.</param>
	/// <param name="reason">If set, the points also go in the score feed right of centre with this reason, as a bot
	/// kill's "Killed a player" does. It's sent in English and translated where it's shown.</param>
	public void AddPoints( int amount, string reason = null )
	{
		if ( !Networking.IsHost ) return;

		if ( ZombiesRoundSystem.Current?.IsPowerUpActive( ZombiesPowerUpType.PointBoost ) == true )
			amount *= 2;

		Points += amount;
		RememberPoints();
		RpcShowPoints( amount, reason );
	}

	public void AddKill()
	{
		if ( !Networking.IsHost ) return;

		Kills++;
		RememberPoints();
	}

	[Rpc.Broadcast]
	private void RpcShowPoints( int amount, string reason = null )
	{
		if ( IsProxy ) return;
		Scene.Dispatch( new PointsAwardedEvent( amount ) );

		if ( reason is not null )
			Scene.Dispatch( new Facepunch.UI.OnScoreAddedEvent { Score = amount, Reason = reason } );
	}

	public bool TrySpendPoints( int amount )
	{
		if ( !Networking.IsHost ) return false;

		if ( Points >= amount )
		{
			Points -= amount;
			RememberPoints();
			RpcShowPoints( -amount );
			return true;
		}
		return false;
	}

	public void SetPoints( int points )
	{
		if ( !Networking.IsHost ) return;
		Points = points;
		RememberPoints();
	}

	/// <summary>A new life picks up the points and kills of the last one.</summary>
	public void Restore( int points, int kills )
	{
		if ( !Networking.IsHost ) return;
		Points = points;
		Kills = kills;
		RememberPoints();
	}

	/// <summary>The pawn is replaced on respawn, so remember this player's points and kills for their next life.</summary>
	private void RememberPoints()
	{
		if ( GetComponent<PlayerPawn>() is { } pawn && pawn.Client.IsValid() )
		{
			ZombiesGameMode.CarriedPoints[pawn.Client] = Points;
			ZombiesGameMode.CarriedKills[pawn.Client] = Kills;
		}
	}

	public void ResetEconomy()
	{
		if ( !Networking.IsHost ) return;
		Points = StartingPoints;
		Kills = 0;
		RememberPoints();
	}
}
