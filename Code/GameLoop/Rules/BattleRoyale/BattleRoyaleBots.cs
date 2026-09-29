namespace Facepunch;

public sealed partial class LightweightBotManager
{
	/// <summary>
	/// Whether a bot here could walk to the rest of the map: not up on a roof or in a sealed room. The battle royale's
	/// drop points and zone circles only go where this holds.
	/// </summary>
	public bool IsWalkable( Vector3 position ) => IsOnMainNavMesh( position );
}
