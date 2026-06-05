namespace Facepunch;

partial class GameMode
{
	[Property, Sync( SyncFlags.FromHost )] public bool UnlimitedMoney { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public int MaxBalance { get; set; } = 16000;

	/// <summary>
	/// When true, hardcore rules apply (reduced HUD info, friendly fire, etc.)
	/// </summary>
	[Property, Sync( SyncFlags.FromHost )] public bool Hardcore { get; set; }

}
