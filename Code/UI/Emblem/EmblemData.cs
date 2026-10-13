using Sandbox;
using System.Collections.Generic;
using System.Text.Json;

namespace Facepunch.UI;

public enum EmblemIconType { MaterialIcon = 0, Emoji = 1, Letter = 2 }

public class EmblemLayer
{
    public string Icon { get; set; } = "star";
    /// <summary>Whether Icon is a Material Icon name, an emoji, or a letter.</summary>
    public EmblemIconType IconType { get; set; } = EmblemIconType.MaterialIcon;
    public Color Color { get; set; } = Color.White;
    public float X { get; set; } = 50f;
    public float Y { get; set; } = 50f;
    public float Scale { get; set; } = 1f;
    public float Rotation { get; set; } = 0f;
}

public class EmblemData
{
    public List<EmblemLayer> Layers { get; set; } = new();

    public string ToJson()
    {
        return JsonSerializer.Serialize( this );
    }

    public static EmblemData FromJson( string json )
    {
        if ( string.IsNullOrWhiteSpace( json ) ) return new EmblemData();
        try
        {
            return JsonSerializer.Deserialize<EmblemData>( json );
        }
        catch
        {
            return new EmblemData();
        }
    }
}
