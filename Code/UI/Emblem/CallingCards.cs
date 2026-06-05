using Sandbox;

namespace Facepunch.UI;

/// <summary>
/// Defines the visual style of a player's calling card (the banner shown
/// on the lobby roster, scoreboard, and player info panels).
/// </summary>
public record CallingCardDef(
    string Id,
    string Name,
    string BgColor,        // CSS hex or rgba — card background
    string AccentColor,    // Accent stripe / glow colour
    bool Locked = false    // True = hidden until future unlock system
)
{
    /// <summary>Inline CSS background-color for the card body.</summary>
    public string BgStyle => $"background-color: {BgColor};";

    /// <summary>Inline CSS color for the accent bar.</summary>
    public string AccentStyle => $"background-color: {AccentColor};";
}

public static class CallingCards
{
    private const string Cookie = "hc1.barracks.callingcard";

    public static readonly CallingCardDef[] All =
    {
        new( "default",  "OPERATOR",    "#0d0d1a", "#4466ff"   ),
        new( "gold",     "GOLD RUSH",   "#1a1000", "#ffd700"   ),
        new( "crimson",  "CRIMSON OPS", "#1a0000", "#cc2200"   ),
        new( "ocean",    "DEEP WATER",  "#001018", "#0099cc"   ),
        new( "forest",   "HUNTER",      "#0a1200", "#44aa22"   ),
        new( "void",     "VOID",        "#050005", "#8800ff"   ),
        new( "ember",    "EMBER",       "#180800", "#ff6600"   ),
        new( "frost",    "FROST",       "#00080f", "#44ccff"   ),
        new( "royal",    "ROYALTY",     "#06001a", "#9966ff"   ),
        new( "nuclear",  "NUCLEAR",     "#0a0a00", "#aaff00"   ),
        new( "arctic",   "ARCTIC",      "#0a1218", "#aaddff"   ),
        new( "shadow",   "SHADOW",      "#050505", "#888888"   ),
        new( "rose",     "ROSE",        "#140008", "#ff44aa"   ),
        new( "bronze",   "BRONZE",      "#120a00", "#cd7f32"   ),
        new( "neon",     "NEON CITY",   "#000a14", "#00ffcc"   ),
        new( "obsidian", "OBSIDIAN",    "#080808", "#333333"   ),
    };

    public static string GetSelected()
        => Game.Cookies.Get<string>( Cookie, "default" );

    public static void SetSelected( string id )
        => Game.Cookies.Set( Cookie, id );

    public static CallingCardDef GetSelectedDef()
    {
        var id = GetSelected();
        return System.Array.Find( All, c => c.Id == id ) ?? All[0];
    }
}
