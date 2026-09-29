using Sandbox.Network;

namespace Facepunch;

/// <summary>Settings for the custom game being started (CreateLobbyPage), cleared when the main menu is opened again.</summary>
public sealed class CustomGameSettings
{
    public static CustomGameSettings Current { get; private set; }

    public int PlayerLimit { get; private init; }
    public bool FillWithBots { get; private init; }

    /// <summary>Public games are listed in the server browser (SESSIONS); Friends and Invite Only games aren't.</summary>
    public LobbyPrivacy Privacy { get; private init; }

    public static void Configure( int playerLimit, bool fillWithBots, LobbyPrivacy privacy )
    {
        Current = new()
        {
            PlayerLimit = Math.Clamp( playerLimit, 2, 10 ),
            FillWithBots = fillWithBots,
            Privacy = privacy
        };
    }

    public static void Reset() => Current = null;

    public LobbyConfig CreateLobbyConfig() => new()
    {
        Name = LobbyName,
        Privacy = Privacy,
        MaxPlayers = PlayerLimit,
        DestroyWhenHostLeaves = true
    };

    /// <summary>What the server browser lists it as, so players can tell whose game it is.</summary>
    private static string LobbyName
    {
        get
        {
            var host = Connection.Local?.DisplayName;
            return string.IsNullOrWhiteSpace( host ) ? "Razed Custom Game" : $"{host}'s Custom Game";
        }
    }
}
