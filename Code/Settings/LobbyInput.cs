using Sandbox.Network;

namespace Facepunch;

/// <summary>
/// Who a lobby is for, by what they play with: Settings → Game → Lobby Input, and the custom game page's INPUT. Saved in
/// the settings by number, so add new ones last.
/// </summary>
public enum LobbyInput
{
	Any,
	Controller,
	MouseKeyboard
}

/// <summary>
/// Controller-only and mouse-and-keyboard-only lobbies. A lobby carries its rule in its lobby data (<see cref="DataKey"/>),
/// which the session list and Ranked's matchmaking read before joining. In the match the host syncs it
/// (<see cref="GameMode.LobbyInputRule"/>), and <see cref="LobbyInputGuard"/> holds each player to it.
/// </summary>
public static class LobbyInputRules
{
	/// <summary>The lobby data key. Kept short: Steam limits lobby data.</summary>
	public const string DataKey = "input";

	/// <summary>The player's own choice (Settings → Game → Lobby Input).</summary>
	public static LobbyInput Preference => GameSettingsSystem.Current?.LobbyInput ?? LobbyInput.Any;

	/// <summary>
	/// What the player is playing with: the last button pressed. A pad's buttons and triggers count as the controller's,
	/// a key or a mouse button as mouse and keyboard's. Moving the mouse or a stick alone changes nothing.
	/// </summary>
	public static LobbyInput Device => Input.UsingController ? LobbyInput.Controller : LobbyInput.MouseKeyboard;

	public static LobbyInput Of( LobbyInformation lobby ) => FromData( lobby.Data?.GetValueOrDefault( DataKey ) );

	/// <summary>
	/// Sets the rule of the next lobby this machine makes. Call it just before <c>Networking.CreateLobby</c>, which copies
	/// the data into the new lobby. The engine keeps lobby data until the game closes (a lobby you were in sent you its
	/// own), so every lobby is stamped, open ones too.
	/// </summary>
	public static void Stamp( LobbyInput rule ) => Networking.SetData( DataKey, ToData( rule ) );

	/// <summary>
	/// Whether the player may join a lobby with this rule. With a preference, only lobbies for that input. With none,
	/// open lobbies and those for what they're playing with now.
	/// </summary>
	public static bool CanJoin( LobbyInput lobby ) => Preference == LobbyInput.Any
		? lobby == LobbyInput.Any || lobby == Device
		: lobby == Preference;

	public static string ToData( LobbyInput rule ) => rule switch
	{
		LobbyInput.Controller => "pad",
		LobbyInput.MouseKeyboard => "kbm",
		_ => "any"
	};

	/// <summary>A lobby with no rule (an older build's, or the editor's network menu) is open to everyone.</summary>
	public static LobbyInput FromData( string value ) => value switch
	{
		"pad" => LobbyInput.Controller,
		"kbm" => LobbyInput.MouseKeyboard,
		_ => LobbyInput.Any
	};

	/// <summary>The rule's name, in English: Tr it where it's shown.</summary>
	public static string Title( LobbyInput rule ) => rule switch
	{
		LobbyInput.Controller => "Controller Only",
		LobbyInput.MouseKeyboard => "Mouse & Keyboard Only",
		_ => "Any Input"
	};

	/// <summary>What the rule means for who can join, in English.</summary>
	public static string Help( LobbyInput rule ) => rule switch
	{
		LobbyInput.Controller => "Only players on a controller can join.",
		LobbyInput.MouseKeyboard => "Only players on mouse and keyboard can join.",
		_ => "Anyone can join, whatever they play with."
	};

	public static string Icon( LobbyInput rule ) => rule switch
	{
		LobbyInput.Controller => "sports_esports",
		LobbyInput.MouseKeyboard => "mouse",
		_ => "devices"
	};
}
