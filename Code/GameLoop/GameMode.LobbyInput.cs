namespace Facepunch;

partial class GameMode
{
	/// <summary>
	/// Who this lobby is for by input (<see cref="LobbyInputRules"/>), from the host's lobby data. It's synced rather than
	/// read from each machine's own lobby data: the engine never clears that, so a client can hold a key left over from
	/// a lobby it was in before, which the new lobby's handshake didn't overwrite.
	/// </summary>
	[Sync( SyncFlags.FromHost )] public LobbyInput LobbyInputRule { get; private set; }

	/// <summary>
	/// Host, every update (<see cref="LobbyInputGuard"/>): keeps <see cref="LobbyInputRule"/> to the lobby's data. The lobby
	/// can be made after the mode starts (GameNetworkManager makes it in its own OnStart), and a host who took the lobby
	/// over keeps the rule the old host gave it.
	/// </summary>
	internal void KeepLobbyInputRule()
	{
		var rule = Networking.IsActive
			? LobbyInputRules.FromData( Networking.GetData( LobbyInputRules.DataKey ) )
			: LobbyInput.Any;

		if ( LobbyInputRule != rule )
			LobbyInputRule = rule;
	}
}
