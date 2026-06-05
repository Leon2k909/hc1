using Sandbox;

namespace Facepunch;

public sealed class PingMarker : Component, IMarkerObject
{
    Vector3 IMarkerObject.MarkerPosition => Transform.Position;
    string IMarkerObject.MarkerIcon => "ui/ping_icon.png";
    float IMarkerObject.MarkerMaxDistance => 4096f;
    string IMarkerObject.DisplayText => "Ping";

    private TimeSince _timeSinceCreated;

    protected override void OnStart()
    {
        _timeSinceCreated = 0;
    }

    protected override void OnUpdate()
    {
        if ( Networking.IsHost && _timeSinceCreated > 5f )
        {
            GameObject.Destroy();
        }
    }
}
