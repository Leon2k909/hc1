namespace Facepunch;

/// <summary>
/// It's nice to be able to access a global anywhere.
/// </summary>
public static class GlobalGameNamespace
{
	/// <summary>
	/// Fetch a global.
	/// </summary>
	public static T GetGlobal<T>() where T : GlobalComponent
	{
		return Game.ActiveScene.GetSystem<GlobalSystem>().Get<T>();
	}

	/// <summary>
	/// <paramref name="english"/> in the player's language (<see cref="GameText"/>): <c>Tr( "PLAY NOW" )</c>. Use it
	/// where text is shown, on the machine showing it, never on text sent to other players.
	/// </summary>
	public static string Tr( string english ) => GameText.Get( english );

	/// <summary> <see cref="Tr(string)"/> of a format string, filled in: <c>Tr( "{0} XP TO LEVEL {1}", xp, level )</c>. </summary>
	public static string Tr( string english, params object[] args ) => GameText.Format( english, args );
}
