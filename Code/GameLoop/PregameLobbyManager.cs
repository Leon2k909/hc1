using Sandbox;
using Sandbox.Network;
using System.Linq;
using System;

namespace Facepunch;

public sealed class PregameLobbyManager : Component
{
    public static PregameLobbyManager Instance { get; private set; }

    [Sync( SyncFlags.FromHost ), Property] public string SelectedMapPath { get; set; }
    [Sync( SyncFlags.FromHost ), Property] public string SelectedGameMode { get; set; }
    [Sync( SyncFlags.FromHost ), Property] public bool IsHardcore { get; set; }

    protected override void OnStart()
    {
        Instance = this;

        if ( Networking.IsHost )
        {
            var map = GameUtils.GetAvailableMaps().FirstOrDefault();
            if ( map is not null )
            {
                SelectedMapPath = map.ResourcePath;
                var mode = GameMode.GetAll( map ).FirstOrDefault();
                if ( mode is not null )
                {
                    SelectedGameMode = mode.Ident;
                }
            }
        }
    }

    [Rpc.Owner]
    public void StartMatch()
    {
        if ( string.IsNullOrEmpty( SelectedMapPath ) || string.IsNullOrEmpty( SelectedGameMode ) )
            return;

        var map = ResourceLibrary.Get<SceneFile>( SelectedMapPath );
        if ( map is null ) return;

        var mode = GameMode.GetAll( map ).FirstOrDefault( x => x.Ident == SelectedGameMode );
        if ( mode is null ) return;

        GameMode.SetCurrent( mode );
        // Core modes are off for now, every match is hardcore. Put back with Core:
        // GameMode.SetHardcore( IsHardcore );
        GameMode.SetHardcore( true );

        Game.ActiveScene.Load( map );
    }

    [Rpc.Owner]
    public void SetMap( string mapPath )
    {
        SelectedMapPath = mapPath;
        
        var map = ResourceLibrary.Get<SceneFile>( SelectedMapPath );
        if ( map is not null )
        {
            // Auto-adjust gamemode if it doesn't support current
            if ( !GameMode.GetAll( map ).Any( x => x.Ident == SelectedGameMode ) )
            {
                var mode = GameMode.GetAll( map ).FirstOrDefault();
                if ( mode is not null )
                {
                    SelectedGameMode = mode.Ident;
                }
            }
        }
    }

    [Rpc.Owner]
    public void SetGameMode( string modeIdent )
    {
        SelectedGameMode = modeIdent;
    }

    [Rpc.Owner]
    public void SetHardcore( bool hardcore )
    {
        IsHardcore = hardcore;
    }

}
