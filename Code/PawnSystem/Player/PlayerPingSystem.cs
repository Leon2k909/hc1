using Sandbox;

namespace Facepunch;

public sealed class PlayerPingSystem : Component
{
    [RequireComponent] public PlayerPawn Pawn { get; set; }

    protected override void OnUpdate()
    {
        if ( IsProxy ) return;

        if ( Input.Pressed( "ping" ) )
        {
            DoPing();
        }
    }

    private void DoPing()
    {
        var cam = Scene.Camera;
        if ( !cam.IsValid() ) return;

        var tr = Scene.Trace.Ray( cam.Transform.Position, cam.Transform.Position + cam.Transform.Rotation.Forward * 5000f )
            .IgnoreGameObjectHierarchy( Pawn.GameObject )
            .Run();

        if ( tr.Hit )
        {
            RpcSpawnPing( tr.HitPosition );
        }
    }

    [Broadcast]
    private void RpcSpawnPing( Vector3 pos )
    {
        var ping = GameObject.Clone( "prefabs/ping_marker.prefab", new CloneConfig { Transform = new global::Transform(pos) } );
        ping.NetworkSpawn();
    }
}
