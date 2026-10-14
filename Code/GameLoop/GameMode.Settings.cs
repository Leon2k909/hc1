namespace Facepunch;

partial class GameMode
{
	[Property, Sync( SyncFlags.FromHost )] public bool UnlimitedMoney { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public int MaxBalance { get; set; } = 16000;

	/// <summary>
	/// When true, hardcore rules apply (reduced HUD info, friendly fire, etc.)
	/// </summary>
	[Property, Sync( SyncFlags.FromHost )] public bool Hardcore { get; set; }

	/// <summary>Use health damage instead of hardcore trauma, regardless of the menu's default ruleset.</summary>
	[Property, Sync( SyncFlags.FromHost )] public bool UsesStandardHealth { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public bool HealthRegenerationEnabled { get; set; } = true;

	/// <summary>Armour is opt-in. Ordinary multiplayer modes use health only.</summary>
	[Property, Sync( SyncFlags.FromHost )] public bool ArmorEnabled { get; set; }

	/// <summary>Head protection is only available in modes that explicitly enable it and armour.</summary>
	[Property, Sync( SyncFlags.FromHost )] public bool HelmetsEnabled { get; set; }

	/// <summary>Reuse another mode's map objects, such as Defuse's bomb sites and team spawns.</summary>
	[Property] public string MapObjectMode { get; set; }

	public static bool IsHardcore => Instance.IsValid()
		? !Instance.UsesStandardHealth && Instance.Hardcore
		: ActiveHardcore;

}
