using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public record PointsAwardedEvent( int Amount ) : Sandbox.Events.IGameEvent;

public sealed class ZombiesPlayerEconomy : Component
{
	public const int StartingPoints = 500;

	[Property, Sync( SyncFlags.FromHost )] public int Points { get; private set; } = StartingPoints;

	/// <summary>Total kills this game, for the game-over screen.</summary>
	[Sync( SyncFlags.FromHost )] public int Kills { get; private set; }

	public void AddPoints( int amount )
	{
		if ( !Networking.IsHost ) return;

		if ( ZombiesRoundSystem.Current?.IsPowerUpActive( ZombiesPowerUpType.DoublePoints ) == true )
			amount *= 2;

		Points += amount;
		RememberPoints();
		RpcShowPoints( amount );
	}

	public void AddKill()
	{
		if ( Networking.IsHost ) Kills++;
	}

	[Rpc.Broadcast]
	private void RpcShowPoints( int amount )
	{
		if ( IsProxy ) return;
		Scene.Dispatch( new PointsAwardedEvent( amount ) );
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

	/// <summary>The pawn is replaced on respawn, so remember this player's points for their next life.</summary>
	private void RememberPoints()
	{
		if ( GetComponent<PlayerPawn>() is { } pawn && pawn.Client.IsValid() )
			ZombiesGameMode.CarriedPoints[pawn.Client] = Points;
	}

	public void ResetEconomy()
	{
		if ( !Networking.IsHost ) return;
		Points = StartingPoints;
		Kills = 0;
		RememberPoints();
	}
}
