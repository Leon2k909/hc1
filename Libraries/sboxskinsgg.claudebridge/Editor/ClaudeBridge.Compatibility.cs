using Sandbox;
using System;
using System.Globalization;
using System.Linq;
using System.Text.Json;

// Shared contracts used by the newer helper files alongside the 1.7 dispatcher.
public static partial class ClaudeBridge
{
	internal const int IpcProtocolVersion = 1;
	internal static bool IsRunning => _running;
	internal static string IpcDirectory => _ipcDir;
	internal static string[] RegisteredCommands => _handlers.Keys.OrderBy( x => x ).ToArray();

	internal static IBridgeHandler GetHandler( string command )
	{
		if ( !_handlers.ContainsKey( command ) ) RegisterHandlers();
		return _handlers.TryGetValue( command, out var handler ) ? handler : null;
	}

	internal static GameObject ResolveGameObject( Scene scene, string id )
		=> scene != null && Guid.TryParse( id, out var guid ) ? scene.Directory.FindByGuid( guid ) : null;

	internal static string GetGameAssemblyFingerprint()
		=> string.Join( "|", AppDomain.CurrentDomain.GetAssemblies()
			.Where( a => a.GetName().Name.StartsWith( "package.", StringComparison.Ordinal )
				&& !a.GetName().Name.EndsWith( ".editor", StringComparison.Ordinal ) )
			.OrderBy( a => a.GetName().Name )
			.Select( a => $"{a.GetName().Name}:{a.ManifestModule.ModuleVersionId}" ) );

	internal static bool TryUnwrapStructuredJsonString( JsonElement value, out JsonElement structured )
	{
		structured = default;
		if ( value.ValueKind != JsonValueKind.String ) return false;
		var text = value.GetString()?.Trim();
		if ( string.IsNullOrEmpty( text ) || (text[0] != '{' && text[0] != '[') ) return false;
		try
		{
			using var doc = JsonDocument.Parse( text );
			structured = doc.RootElement.Clone();
			return true;
		}
		catch ( JsonException ) { return false; }
	}

	internal static float[] ExtractFloats( string text )
		=> (text ?? "").Trim( ' ', '(', ')', '[', ']' )
			.Split( new[] { ',', ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries )
			.Select( x => float.Parse( x, NumberStyles.Float, CultureInfo.InvariantCulture ) ).ToArray();

	internal static Vector3 ParseVector3Flexible( JsonElement value )
	{
		if ( TryUnwrapStructuredJsonString( value, out var structured ) ) value = structured;
		if ( value.ValueKind == JsonValueKind.Object ) return ParseVector3( value );
		var values = value.ValueKind == JsonValueKind.Array
			? value.EnumerateArray().Select( x => x.GetSingle() ).ToArray()
			: value.ValueKind == JsonValueKind.Number ? new[] { value.GetSingle() }
			: ExtractFloats( value.GetString() );
		if ( values.Length == 1 ) return new Vector3( values[0], values[0], values[0] );
		if ( values.Length != 3 ) throw new ArgumentException( "Expected three vector coordinates." );
		return new Vector3( values[0], values[1], values[2] );
	}

	internal static Color ParseColor( JsonElement value )
		=> VisualHelpers.ParseColorElement( value, Color.White );

	internal static string ElementToValueString( JsonElement value )
	{
		if ( value.ValueKind == JsonValueKind.Null || value.ValueKind == JsonValueKind.Undefined ) return null;
		if ( value.ValueKind == JsonValueKind.String ) return value.GetString();
		if ( value.ValueKind == JsonValueKind.Array )
			return string.Join( ",", value.EnumerateArray().Select( x => x.ToString() ) );
		if ( value.ValueKind == JsonValueKind.Object )
		{
			foreach ( var keys in new[] { new[] { "x", "y", "z" }, new[] { "pitch", "yaw", "roll" }, new[] { "r", "g", "b", "a" } } )
			{
				if ( !value.TryGetProperty( keys[0], out _ ) ) continue;
				return string.Join( ",", keys.Select( key => value.TryGetProperty( key, out var part ) ? part.ToString() : key == "a" ? "1" : "0" ) );
			}
		}
		return value.GetRawText();
	}
}
