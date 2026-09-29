namespace Facepunch;

/// <summary>
/// A map's own place for a mode's objective, on the floor. Without these, Domination puts its flags at the spawn
/// points furthest apart and in the middle, and Hot Zone spreads its zones over the spawn points, which on a map
/// with spawn roads puts objectives in the spawns. Belltower places its own (Tools/belltower_map.py).
/// </summary>
public sealed class ObjectiveSpot : Component
{
	public enum SpotKind
	{
		/// <summary>A Domination flag. A map needs at least three; they're named and ordered by their labels.</summary>
		Domination,

		/// <summary>One of the places a Hot Zone moves between.</summary>
		HotZone,
	}

	[Property] public SpotKind Kind { get; set; }

	/// <summary>
	/// The flag's letter for Domination (A, B, C); for a Hot Zone, the place's name.
	/// </summary>
	[Property] public string Label { get; set; }

	/// <summary>
	/// The scene's active spots of this kind, ordered by label.
	/// </summary>
	public static List<ObjectiveSpot> All( Scene scene, SpotKind kind ) => scene.GetAllComponents<ObjectiveSpot>()
		.Where( x => x.Kind == kind )
		.OrderBy( x => x.Label, StringComparer.OrdinalIgnoreCase )
		.ToList();
}
