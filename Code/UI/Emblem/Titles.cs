using Sandbox;

namespace Facepunch.UI;

/// <summary>
/// Defines a player title (e.g. "LONE WOLF", "VETERAN").
/// </summary>
public record TitleDef(
    string Id,
    string Text,
    string Color, // CSS hex or rgba for the text
    bool Locked = false
);

public static class Titles
{
    private const string Cookie = "hc1.barracks.title";

    public static readonly TitleDef[] All =
    {
        new( "default",    "NO TITLE",      "rgba(255,255,255,0.3)" ),
        new( "recruit",    "RECRUIT",       "#ffffff" ),
        new( "veteran",    "VETERAN",       "#aaddff" ),
        new( "lonewolf",   "LONE WOLF",     "#888888" ),
        new( "sharpshoot", "SHARPSHOOTER",  "#44ccff" ),
        new( "bloodthirs", "BLOODTHIRSTY",  "#cc2200" ),
        new( "ghost",      "GHOST",         "#00ffcc" ),
        new( "juggernaut", "JUGGERNAUT",    "#ff6600" ),
        new( "ninja",      "NINJA",         "#8800ff" ),
        new( "commander",  "COMMANDER",     "#ffd700" ),
        new( "immortal",   "IMMORTAL",      "#ff44aa" ),
        new( "sureshot",   "SURE SHOT",     "#44aa22" ),
        new( "assassin",   "ASSASSIN",      "#333333" ),
        new( "spectre",    "SPECTRE",       "#9966ff" ),
        new( "toxic",      "TOXIC",         "#aaff00" ),
        new( "champion",   "CHAMPION",      "#cd7f32" )
    };

    public static string GetSelected()
        => Game.Cookies.Get<string>( Cookie, "default" );

    public static void SetSelected( string id )
        => Game.Cookies.Set( Cookie, id );

    public static TitleDef GetSelectedDef()
    {
        var id = GetSelected();
        return System.Array.Find( All, c => c.Id == id ) ?? All[0];
    }
}
