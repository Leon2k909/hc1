using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public sealed class ZombiesGameMode : Component, IGameEventHandler<PlayerSpawnedEvent>
{
    protected override void OnAwake()
    {
        base.OnAwake();
        if ( Networking.IsHost )
        {
            Components.GetOrCreate<ZombiesRoundSystem>();
        }
    }

    protected override void OnStart()
    {
        base.OnStart();
        
        if ( Networking.IsHost )
        {
            // Give all players the economy component
            foreach ( var p in Scene.GetAllComponents<PlayerPawn>() )
            {
                if ( !p.Components.TryGet<ZombiesPlayerEconomy>( out _ ) )
                {
                    p.Components.Create<ZombiesPlayerEconomy>();
                }
            }
        }
    }

    void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent eventArgs )
    {
        if ( Networking.IsHost )
        {
            var player = eventArgs.Player;
            if ( player.IsValid() && !player.Components.TryGet<ZombiesPlayerEconomy>( out _ ) )
            {
                player.Components.Create<ZombiesPlayerEconomy>();
            }
        }
    }
}
