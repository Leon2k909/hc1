namespace Facepunch.UI;

/// <summary>
/// Quick Play: a random match in one of the modes the player has ticked on the hub's featured Multiplayer screen, on a
/// random ticked match map that has that mode. The ticks are kept in cookies as the modes and maps left out, so a new
/// mode or map starts out ticked.
/// </summary>
public static class QuickPlayFilter
{
	private const string ModesCookie = "quickplay_excluded_modes";
	private const string MapsCookie = "quickplay_excluded_maps";

	/// <summary>Every mode Quick Play can pick from: those the match maps have, less Zombies, which has its own tab.</summary>
	public static List<GameMode> Modes => GameMode.AllUnique
		.Where( m => !string.Equals( m.Ident, "zombies", StringComparison.OrdinalIgnoreCase ) )
		.Where( m => MapsFor( m ).Count > 0 )
		.ToList();

	/// <summary>Every match map with at least one of those modes.</summary>
	public static List<SceneFile> Maps
	{
		get
		{
			var modes = Modes;
			return GameUtils.GetMatchMaps()
				.Where( map => GameMode.GetAll( map ).Any( x => modes.Any( m => m.Ident == x.Ident ) ) )
				.ToList();
		}
	}

	public static string MapTitle( SceneFile map ) => map.GetMetadata( "Title", map.ResourceName );

	/// <summary>Every match map with <paramref name="mode"/>, ticked or not.</summary>
	public static List<SceneFile> MapsFor( GameMode mode ) => GameUtils.GetMatchMaps()
		.Where( map => GameMode.GetAll( map ).Any( x => x.Ident == mode.Ident ) )
		.ToList();

	private static HashSet<string> Read( string cookie ) =>
		Cookie.Get( cookie, "" ).Split( ',', StringSplitOptions.RemoveEmptyEntries ).ToHashSet();

	private static void Write( string cookie, HashSet<string> value ) => Cookie.Set( cookie, string.Join( ",", value ) );

	public static bool IsIncluded( GameMode mode ) => !Read( ModesCookie ).Contains( mode.Ident );
	public static bool IsIncluded( SceneFile map ) => !Read( MapsCookie ).Contains( map.ResourcePath );

	public static List<GameMode> Included => Modes.Where( IsIncluded ).ToList();
	public static List<SceneFile> IncludedMaps => Maps.Where( IsIncluded ).ToList();

	/// <summary>Ticks or unticks a mode. The last ticked mode can't be unticked: there'd be nothing to play.</summary>
	public static void Toggle( GameMode mode ) => Toggle( ModesCookie, mode.Ident, Included.Count );

	/// <summary>Ticks or unticks a map, again keeping at least one.</summary>
	public static void Toggle( SceneFile map ) => Toggle( MapsCookie, map.ResourcePath, IncludedMaps.Count );

	private static void Toggle( string cookie, string key, int includedCount )
	{
		var excluded = Read( cookie );
		if ( !excluded.Remove( key ) )
		{
			if ( includedCount <= 1 ) return;
			excluded.Add( key );
		}
		Write( cookie, excluded );
	}

	public static void IncludeAll() => Write( ModesCookie, new() );
	public static void IncludeAllMaps() => Write( MapsCookie, new() );

	/// <summary>
	/// A random ticked mode that one of the ticked maps has, then one of those maps. If the ticks don't overlap (the only
	/// ticked mode isn't on any ticked map), the map ticks give way.
	/// </summary>
	public static bool TryPick( out GameMode mode, out SceneFile map )
	{
		var modes = Included;
		if ( modes.Count == 0 ) modes = Modes;

		var maps = IncludedMaps.Select( m => m.ResourcePath ).ToHashSet();
		var playable = modes.Where( m => MapsFor( m ).Any( x => maps.Contains( x.ResourcePath ) ) ).ToList();
		if ( playable.Count == 0 )
		{
			playable = modes;
			maps = Maps.Select( m => m.ResourcePath ).ToHashSet();
		}

		mode = playable.Count > 0 ? Game.Random.FromList( playable ) : null;
		map = mode is null ? null : Game.Random.FromList( MapsFor( mode ).Where( x => maps.Contains( x.ResourcePath ) ).ToList() );
		return mode is not null && map is not null;
	}
}
