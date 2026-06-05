namespace Facepunch;

/// <summary>
/// Ensures a PartySystem component exists in every scene.
/// Runs on both host and clients — the component itself is network-spawned by the host.
/// </summary>
public sealed class PartyGameObjectSystem : GameObjectSystem<PartyGameObjectSystem>, ISceneStartup
{
	public PartyGameObjectSystem( Scene scene ) : base( scene ) { }

	void ISceneStartup.OnHostInitialize()
	{
		// Only spawn when a network lobby is actually active.
		// Menu scenes without GameNetworkManager have no active lobby.
		if ( !Networking.IsActive ) return;

		var go = new GameObject( true, "PartySystem" );
		go.AddComponent<PartySystem>();
		go.NetworkSpawn();
	}
}
