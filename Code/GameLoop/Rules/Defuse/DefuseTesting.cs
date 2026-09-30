namespace Facepunch;

/// <summary>Editor-only local host preference; never changes a published or ranked match.</summary>
public static class DefuseTesting
{
	[ConVar( "dev_defuse_planter", Saved = true )] public static bool ForcePlanter { get; set; } = true;

	public static bool IsForced( Client client ) => Game.IsEditor && Networking.IsHost && ForcePlanter
		&& GameMode.Instance is { Ident: "defuse", IsRanked: false }
		&& client.IsValid() && !client.IsBot && client.Connection == Connection.Local;

	public static void PrepareRound()
	{
		var player = GameUtils.AllPlayers.FirstOrDefault( IsForced );
		if ( !player.IsValid() || player.Team == Team.Terrorist ) return;
		// Exchange places to preserve team sizes through halftime.
		var replacement = GameUtils.GetPlayers( Team.Terrorist ).FirstOrDefault( x => x.IsBot );
		if ( player.Team == Team.CounterTerrorist && replacement.IsValid() ) replacement.AssignTeam( Team.CounterTerrorist );
		player.AssignTeam( Team.Terrorist );
	}

	[ConCmd( "dev_defuse" )]
	public static void Start( string mapContains = "flatgrass" )
	{
		if ( !Game.IsEditor ) return;
		var mode = GameObject.GetPrefab( "prefabs/game_modes/bomb_defusal.prefab" )?.GetComponent<GameMode>();
		var map = GameUtils.GetAvailableMaps().FirstOrDefault( x => x.ResourcePath.Contains( mapContains, StringComparison.OrdinalIgnoreCase ) );
		if ( !mode.IsValid() || map is null ) return;
		GameMode.SetCurrent( mode );
		GameUtils.LoadMap( map );
	}
}
