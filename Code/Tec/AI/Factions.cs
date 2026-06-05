using Facepunch;

namespace Tec.AI;

public enum Faction
{
    Unassigned,
    A,
    B
}

public enum FactionRelation
{
    Undefined, // Neutral is Undefined
    Friendly,
    Hostile
}

public static class Factions
{
    private static readonly Dictionary<(Faction, Faction), FactionRelation> Relations = new()
    {
        { (Faction.Unassigned, Faction.B), FactionRelation.Friendly },
        { (Faction.A, Faction.B), FactionRelation.Friendly },
        { (Faction.Unassigned, Faction.A), FactionRelation.Hostile }
    };

    public static FactionRelation GetRelation(Faction a, Faction b)
    {
        FactionRelation relation;

        if (Relations.TryGetValue((a, b), out relation))
        {
            return relation;
        }

        if (Relations.TryGetValue((b, a), out relation))
        {
            return relation;
        }

        return FactionRelation.Undefined;
    }

    public static Faction ToFaction( this Facepunch.Team team )
    {
	    switch ( team )
	    {
		    case Team.Unassigned:
			    return Faction.Unassigned;
		    case Team.Terrorist:
			    return Faction.A;
		    case Team.CounterTerrorist:
			    return Faction.B;
		    default:
			    throw new ArgumentOutOfRangeException( nameof(team), team, null );
	    }
    }
}
