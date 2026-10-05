namespace Facepunch;

/// <summary>An outfit a team's soldiers can wear.</summary>
public sealed record OperatorOutfit( string Id, string Name, Team Team, string Description, string ModelPath,
	MilitaryUniformStyle Style = MilitaryUniformStyle.Standard )
{
	/// <summary>
	/// The outfit's picture. The Tactical Operator's is drawn by Tools/operator_portraits.py and couldn't be committed from
	/// where it was made, so until it's there the card shows the Military Operator's.
	/// </summary>
	public string Portrait
	{
		get
		{
			var path = $"ui/operators/{(Id == "field" ? "field_military" : Id)}.png";
			return FileSystem.Mounted.FileExists( path ) ? $"/{path}" : "/ui/operators/military.png";
		}
	}
}

/// <summary>
/// The teams' outfits. A player wears the one they equipped for their team on the Operators page (a cookie per team,
/// sent to the host as <see cref="Client.OperatorPicks"/>), and a team's first outfit until they do. Bots are issued
/// one at random (<see cref="Roll"/>).
/// </summary>
public static class OperatorOutfits
{
	public static IReadOnlyList<OperatorOutfit> All { get; } = new OperatorOutfit[]
	{
		new( "military", "Military Operator", Team.CounterTerrorist,
			"Camouflage fatigues, tactical vest, combat helmet, headset and boots.", MilitaryUniform.HumanModelPath ),
		new( "tactical", "Tactical Operator", Team.CounterTerrorist,
			"Dark camouflage fatigues, black plate carrier, combat helmet, balaclava, gloves and boots.",
			MilitaryUniform.HumanModelPath, MilitaryUniformStyle.Tactical ),
		new( "field", "Field Operator", Team.Terrorist,
			"Camouflage fatigues, olive tactical vest, combat helmet, gloves and boots.",
			MilitaryUniform.HumanModelPath, MilitaryUniformStyle.Field )
	};

	private const string EquippedCookie = "hc1.operator.";
	private static string _localPicks;

	public static OperatorOutfit Find( string id ) => All.FirstOrDefault( x => x.Id == id ) ?? All[0];

	/// <summary>
	/// The outfits <paramref name="team"/> wears, its default first. A team with none of its own (free-for-all's
	/// Unassigned) wears Red Team's, as <see cref="HumanOutfitter"/> always dressed it.
	/// </summary>
	public static List<OperatorOutfit> ForTeam( Team team )
	{
		var outfits = All.Where( x => x.Team == team ).ToList();
		return outfits.Count > 0 ? outfits : All.Where( x => x.Team == Team.Terrorist ).ToList();
	}

	/// <summary>The outfit the local player wears on <paramref name="team"/>.</summary>
	public static OperatorOutfit GetEquipped( Team team ) => Resolve( team, Game.Cookies.Get<string>( EquippedCookie + team, "" ) );

	public static bool IsEquipped( OperatorOutfit outfit ) => GetEquipped( outfit.Team ) == outfit;

	/// <summary>Wear <paramref name="outfit"/> on its team from the next spawn.</summary>
	public static void Equip( OperatorOutfit outfit )
	{
		Game.Cookies.Set( EquippedCookie + outfit.Team, outfit.Id );
		_localPicks = null;
	}

	/// <summary>The local player's equipped outfits' ids, one per team, comma-separated.</summary>
	public static string LocalPicks => _localPicks ??= string.Join( ",",
		All.Select( x => x.Team ).Distinct().Select( team => GetEquipped( team ).Id ) );

	/// <summary>
	/// What a soldier on <paramref name="team"/> wears, from their picks (outfit ids, comma-separated, as
	/// <see cref="LocalPicks"/>): the first that's one of the team's, else the team's default.
	/// </summary>
	public static OperatorOutfit Resolve( Team team, string picks )
	{
		var outfits = ForTeam( team );
		foreach ( var id in (picks ?? "").Split( ',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries ) )
		{
			if ( outfits.FirstOrDefault( x => x.Id == id ) is { } outfit )
				return outfit;
		}

		return outfits[0];
	}

	/// <summary>An outfit for a bot on <paramref name="team"/>, each of the team's as likely.</summary>
	public static OperatorOutfit Roll( Team team ) => Game.Random.FromList( ForTeam( team ) );
}
