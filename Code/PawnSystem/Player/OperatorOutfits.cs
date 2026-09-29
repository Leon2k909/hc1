namespace Facepunch;

/// <summary>The outfits currently used by the two team model pools.</summary>
public sealed record OperatorOutfit( string Id, string Name, Team Team, string Description, string ModelPath,
	MilitaryUniformStyle Style = MilitaryUniformStyle.Standard )
{
	public string Portrait => $"/ui/operators/{(Id == "field" ? "field_military" : Id)}.png";
}

public static class OperatorOutfits
{
	public static IReadOnlyList<OperatorOutfit> All => new OperatorOutfit[]
	{
		new( "military", "Military Operator", Team.CounterTerrorist,
			"Camouflage fatigues, tactical vest, combat helmet, headset and boots.", MilitaryUniform.HumanModelPath ),
		new( "field", "Field Operator", Team.Terrorist,
			"Camouflage fatigues, olive tactical vest, combat helmet, gloves and boots.",
			MilitaryUniform.HumanModelPath, MilitaryUniformStyle.Field )
	};

	public static OperatorOutfit Find( string id ) => All.FirstOrDefault( x => x.Id == id ) ?? All[0];
}
