using System.Text.Json.Nodes;
using System.Threading.Tasks;

namespace Facepunch;

/// <summary>
/// The picture on a map's vote card. The scene's own <see cref="MapInformation.Image"/> if it's a wide screenshot,
/// otherwise the wide thumbnail of the cloud map its MapInstance loads, fetched from sbox.game once and cached.
/// (Flatgrass has no image of its own, and Innocent Hotel's is a small square that looks poor stretched to 16:9.)
/// </summary>
public static class MapArt
{
	/// <summary> Scene path → picture: null while it's being fetched, "" if there's none. </summary>
	private static readonly Dictionary<string, string> art = new();

	/// <summary> The map's picture, or null/"" (show a placeholder) while it loads or if it has none. </summary>
	public static string Get( SceneFile map )
	{
		if ( map is null )
			return "";

		if ( art.TryGetValue( map.ResourcePath, out var cached ) )
			return cached;

		var image = map.GetMetadata( "Image", "" );
		if ( IsWide( image ) )
			return art[map.ResourcePath] = image;

		art[map.ResourcePath] = null;
		_ = FetchCloudThumb( map, image );
		return null;
	}

	private static async Task FetchCloudThumb( SceneFile map, string fallback )
	{
		var thumb = "";

		try
		{
			var ident = FindCloudMap( map.GameObjects );
			var package = string.IsNullOrEmpty( ident ) ? null : await Package.FetchAsync( ident, false );
			thumb = new[] { package?.ThumbWide, package?.Thumb }.FirstOrDefault( x => !string.IsNullOrWhiteSpace( x ) ) ?? "";
		}
		catch ( Exception e )
		{
			Log.Warning( $"MapArt: couldn't fetch the cloud thumbnail for {map.ResourcePath}: {e.Message}" );
		}

		art[map.ResourcePath] = !string.IsNullOrEmpty( thumb ) ? thumb : fallback ?? "";
	}

	/// <summary> A picture that fills a 16:9 card without looking stretched or blurry. </summary>
	private static bool IsWide( string image )
	{
		if ( string.IsNullOrWhiteSpace( image ) )
			return false;

		var texture = Texture.Load( image, false );
		return texture.IsValid() && texture.Width >= 960 && texture.Width >= texture.Height * 1.5f;
	}

	/// <summary> The cloud map ident (e.g. "facepunch.flatgrass") of the scene's MapInstance. </summary>
	private static string FindCloudMap( IEnumerable<JsonObject> objects )
	{
		if ( objects is null )
			return null;

		foreach ( var go in objects )
		{
			if ( go?["Components"] is JsonArray components )
			{
				foreach ( var component in components.OfType<JsonObject>() )
				{
					if ( component["__type"]?.ToString() == "Sandbox.MapInstance" )
						return component["MapName"]?.ToString();
				}
			}

			if ( go?["Children"] is JsonArray children && FindCloudMap( children.OfType<JsonObject>() ) is { } found )
				return found;
		}

		return null;
	}
}
