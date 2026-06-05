using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public record PointsAwardedEvent( int Amount ) : Sandbox.Events.IGameEvent;

public sealed class ZombiesPlayerEconomy : Component
{
    [Property, Sync] public int Points { get; private set; } = 500; // Starting points

    public void AddPoints( int amount )
    {
        if ( !Networking.IsHost ) return;
        Points += amount;
        RpcShowPoints( amount );
    }

    [Broadcast]
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
            return true;
        }
        return false;
    }
}
