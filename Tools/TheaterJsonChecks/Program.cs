// Checks TheaterClipJson (Code/GameLoop): that a recording put together from its lives' JSON, each serialised through a
// Utf8JsonWriter of our own, is byte for byte what the engine's Json.Serialize writes for the whole clip. The engine's
// options are mirrored here (indented, the relaxed encoder); the clip is a model laid out like MovieMaker's ClipModel,
// with blocks as a JsonArray as the engine has them. `dotnet run --project Tools/TheaterJsonChecks`.
using Facepunch;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

var failures = 0;

void Check( bool ok, string what )
{
	Console.WriteLine( (ok ? "ok    " : "FAIL  ") + what );
	if ( !ok ) failures++;
}

// Json.Initialize's options, as far as writing goes.
JsonSerializerOptions EngineOptions( string newLine = null )
{
	var options = new JsonSerializerOptions( JsonSerializerOptions.Default )
	{
		WriteIndented = true,
		PropertyNameCaseInsensitive = true,
		NumberHandling = JsonNumberHandling.AllowReadingFromString | JsonNumberHandling.AllowNamedFloatingPointLiterals,
		DefaultIgnoreCondition = JsonIgnoreCondition.Never,
		ReadCommentHandling = JsonCommentHandling.Skip,
		MaxDepth = 512,
		Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
	};

	if ( newLine is not null )
		options.NewLine = newLine;

	return options;
}

// Json.Serialize( object ): the old way, the whole clip as one string.
byte[] Whole( Clip clip, JsonSerializerOptions options ) => Encoding.UTF8.GetBytes( JsonSerializer.Serialize( (object)clip, options ) );

// TheaterReplays.WriteClipByLife's way: each life through one reused writer and buffer, laid in by TheaterClipJson.
// Returns the file and what TheaterClipJson counted as written.
(byte[] File, long Written) ByLifeCounted( Clip clip, JsonSerializerOptions options, JsonWriterOptions writerOptions )
{
	var output = new MemoryStream();
	var buffer = new MemoryStream();
	long written;

	using ( var writer = new Utf8JsonWriter( buffer, writerOptions ) )
	using ( var file = new TheaterClipJson( output ) )
	{
		foreach ( var life in clip.Tracks )
		{
			buffer.SetLength( 0 );
			writer.Reset();

			// Json.Serialize( writer, clip ).
			JsonSerializer.Serialize( writer, new Clip( [life] ), options );
			writer.Flush();

			file.AddLife( buffer.GetBuffer().AsSpan( 0, (int)buffer.Length ) );
		}

		file.Finish();
		written = file.Written;
	}

	return (output.ToArray(), written);
}

byte[] ByLife( Clip clip, JsonSerializerOptions options, JsonWriterOptions writerOptions ) => ByLifeCounted( clip, options, writerOptions ).File;

// TheaterReplays.WriteWholeClip's way: the whole clip through our writer, escapes put right.
byte[] WholeByWriter( Clip clip, JsonSerializerOptions options, JsonWriterOptions writerOptions )
{
	var output = new MemoryStream();
	var buffer = new MemoryStream();

	using ( var writer = new Utf8JsonWriter( buffer, writerOptions ) )
	using ( var file = new TheaterClipJson( output ) )
	{
		JsonSerializer.Serialize( writer, clip, options );
		writer.Flush();
		file.WriteWhole( buffer.GetBuffer().AsSpan( 0, (int)buffer.Length ) );
	}

	return output.ToArray();
}

bool SameJson( byte[] a, byte[] b ) => JsonNode.DeepEquals( JsonNode.Parse( a ), JsonNode.Parse( b ) );

string FirstDifference( byte[] a, byte[] b )
{
	var i = 0;
	while ( i < a.Length && i < b.Length && a[i] == b[i] ) i++;
	if ( i == a.Length && i == b.Length ) return "none";

	var from = Math.Max( 0, i - 30 );
	string Around( byte[] x ) => from >= x.Length ? "" : Encoding.UTF8.GetString( x, from, Math.Min( 60, x.Length - from ) );
	return $"at byte {i} of {a.Length}/{b.Length}: [{Around( a )}] vs [{Around( b )}]";
}

var engine = EngineOptions();
var writerOptions = TheaterClipJson.WriterOptions;

// Built from character codes, so this file stays plain ASCII with no escapes to get wrong.
const char Backslash = (char)92;
const char Quote = (char)34;
string Chars( params int[] codes ) => new string( codes.Select( x => (char)x ).ToArray() );

// Every ASCII character a name or a value could hold, those the default encoder escapes among them: + < > & ' ` and the
// quote and backslash, a line end, a tab, a carriage return, controls and DEL.
var asciiNames = "abcXYZ019 :#_-./+<>&'`" + Quote + Backslash + Chars( 10, 9, 13, 1, 31, 127 );

// Letters outside ASCII, an emoji (a surrogate pair) and the line separator.
string[] unicode = { Chars( 0xE9 ), Chars( 0xDF ), Chars( 0x416 ), Chars( 0x4E2D ), char.ConvertFromUtf32( 0x1F600 ), Chars( 0x2028 ) };

Clip RandomClip( Random random, int lives, bool withUnicode, int maxSamples = 600 )
{
	string Text( int length )
	{
		var text = new StringBuilder();
		for ( var i = 0; i < length; i++ )
		{
			if ( withUnicode && random.Next( 6 ) == 0 )
				text.Append( unicode[random.Next( unicode.Length )] );
			else
				text.Append( asciiNames[random.Next( asciiNames.Length )] );
		}

		return text.ToString();
	}

	JsonArray Blocks()
	{
		var blocks = new JsonArray();
		for ( var i = random.Next( 4 ); i > 0; i-- )
		{
			var start = random.Next( 100000 );
			var block = new JsonObject { ["TimeRange"] = $"{start},{start + random.Next( 1, 9000 )}" };

			if ( random.Next( 2 ) == 0 )
			{
				var samples = new byte[random.Next( maxSamples )];
				random.NextBytes( samples );
				block["SampleRate"] = 15;
				block["Samples"] = Convert.ToBase64String( samples );
			}
			else
			{
				block["Value"] = random.Next( 3 ) switch
				{
					0 => JsonValue.Create( random.Next( 2 ) == 0 ),
					1 => JsonValue.Create( random.NextDouble() * 1000 ),
					_ => JsonValue.Create( Text( random.Next( 12 ) ) )
				};
			}

			blocks.Add( block );
		}

		return blocks.Count > 0 ? blocks : null;
	}

	Track Make( int depth, int order )
	{
		var reference = depth == 0 || random.Next( 3 ) == 0;
		var children = depth < 4 && random.Next( 3 ) > 0
			? Enumerable.Range( 0, random.Next( 1, 4 ) ).Select( x => Make( depth + 1, x ) ).ToList()
			: null;

		return new Track(
			Kind: reference ? "Reference" : "Property",
			Name: depth == 0 ? $"Bot: {Text( 6 )} #{order}" : Text( random.Next( 1, 10 ) ),
			Type: reference ? "Sandbox.GameObject" : "Sandbox.MovieMaker.BindingReference`1[[Facepunch.Thing+Nested]]",
			Id: reference ? new Guid( random.Next(), 1, 2, new byte[8] ) : null,
			Metadata: depth == 0 ? new Meta( Guid.Empty, random.Next( 2 ) == 0 ? "prefabs/bots/hc1_combat_bot.prefab" : null, 1000 + order ) : null,
			Children: children,
			Blocks: reference ? null : Blocks() );
	}

	return new Clip( Enumerable.Range( 0, lives ).Select( x => Make( 0, x ) ).ToList() );
}

// 1. Hand-made: the escapes that differ between the encoders, and escapes that look like them.
{
	// The six characters of a written escape, in a name: it must stay a backslash and "u002B", not become a '+'.
	var literalEscape = "literal " + Backslash + "u002B and " + Backslash + Backslash + "u0022, ends in a backslash " + Backslash;

	var clip = new Clip(
	[
		new Track( "Reference", "Bot: Raven #1", "Sandbox.GameObject", Guid.Parse( "af0516ad-e7d4-4cd4-8dd8-00f77ae1f62c" ),
			new Meta( Guid.Parse( "d6dc0bb9-2d15-4d6f-afe1-59b444d61458" ), "prefabs/bots/hc1_combat_bot.prefab", 1000 ),
			[
				new Track( "Property", "Enabled", "System.Boolean", null, null, null,
					new JsonArray( new JsonObject { ["TimeRange"] = "720,369600", ["Value"] = true } ) ),
				new Track( "Property", "a+b<c>d&e'f`g" + Quote + "h" + Backslash + "i", "Facepunch.Outer+Inner", null, null, null,
					new JsonArray( new JsonObject { ["TimeRange"] = "0,1", ["SampleRate"] = 15, ["Samples"] = "H4sI+/+/+A==" } ) ),
				new Track( "Property", literalEscape, "System.String", null, null, null,
					new JsonArray( new JsonObject { ["TimeRange"] = "0,1", ["Value"] = "tab" + Chars( 9 ) + "line" + Chars( 10 ) + "null" + Chars( 0 ) + "del" + Chars( 127 ) } ) )
			], null ),
		new Track( "Reference", "Player: Leon #1", "Sandbox.GameObject", Guid.Parse( "11111111-2222-3333-4444-555555555555" ),
			new Meta( Guid.Empty, null, 1001 ), null, null )
	] );

	var whole = Whole( clip, engine );
	var byLife = ByLife( clip, engine, writerOptions );
	var text = Encoding.UTF8.GetString( whole );

	Check( whole.AsSpan().SequenceEqual( byLife ), $"hand-made clip, by life: {FirstDifference( whole, byLife )}" );
	Check( whole.AsSpan().SequenceEqual( WholeByWriter( clip, engine, writerOptions ) ), "hand-made clip, whole through our writer" );
	Check( text.Contains( "H4sI+/+/+A==" ), "base64's '+' is written as it is" );
	Check( text.Contains( "literal " + Backslash + Backslash + "u002B" ), "a written escape in a name stays written out" );

	// What the fix is for: our writer on its own escapes the '+'.
	var buffer = new MemoryStream();
	using ( var writer = new Utf8JsonWriter( buffer, writerOptions ) )
		JsonSerializer.Serialize( writer, clip, engine );

	Check( Encoding.UTF8.GetString( buffer.ToArray() ).Contains( "H4sI" + Backslash + "u002B" ), "our writer alone writes '+' as an escape" );
}

// 2. Random clips of ASCII: byte for byte.
var asciiSame = 0;
for ( var seed = 1; seed <= 300; seed++ )
{
	var clip = RandomClip( new Random( seed ), 1 + seed % 40, withUnicode: false );
	var whole = Whole( clip, engine );
	var byLife = ByLife( clip, engine, writerOptions );

	if ( whole.AsSpan().SequenceEqual( byLife ) )
		asciiSame++;
	else if ( asciiSame + 5 > seed )
		Console.WriteLine( $"      random ASCII clip {seed}: {FirstDifference( whole, byLife )}" );
}

Check( asciiSame == 300, $"300 random ASCII clips, by life, byte for byte ({asciiSame})" );

// 3. Random clips with letters outside ASCII: the same JSON (they stay escaped).
var unicodeSame = 0;
for ( var seed = 1; seed <= 100; seed++ )
{
	var clip = RandomClip( new Random( 1000 + seed ), 1 + seed % 20, withUnicode: true );
	if ( SameJson( Whole( clip, engine ), ByLife( clip, engine, writerOptions ) ) )
		unicodeSame++;
}

Check( unicodeSame == 100, $"100 random clips with Unicode names read back the same ({unicodeSame})" );

// 4. Big: many lives and long samples, past the file's 64 KB buffer many times over.
{
	var clip = RandomClip( new Random( 77 ), 600, withUnicode: false, maxSamples: 20_000 );
	var whole = Whole( clip, engine );
	var (byLife, written) = ByLifeCounted( clip, engine, writerOptions );

	Check( whole.AsSpan().SequenceEqual( byLife ), $"600 lives, {whole.Length / 1024} KB: {FirstDifference( whole, byLife )}" );
	Check( written == byLife.Length, $"Written is the file's length ({written})" );
}

// 5. Linux line ends.
{
	var options = EngineOptions( "\n" );
	var lfWriter = TheaterClipJson.WriterOptions;
	lfWriter.NewLine = "\n";

	var clip = RandomClip( new Random( 5 ), 12, withUnicode: false );
	var whole = Whole( clip, options );
	Check( whole.AsSpan().SequenceEqual( ByLife( clip, options, lfWriter ) ), "line feeds alone, by life" );
}

// 6. Layouts it mustn't splice: they throw, and TheaterReplays writes the clip whole instead.
{
	bool Throws( byte[] json )
	{
		try { new TheaterClipJson( new MemoryStream() ).AddLife( json ); return false; }
		catch ( TheaterClipJson.LayoutException ) { return true; }
	}

	var one = RandomClip( new Random( 9 ), 1, false ).Tracks;
	var life = Encoding.UTF8.GetBytes( JsonSerializer.Serialize( new Clip( one ), engine ) );
	var extra = Encoding.UTF8.GetBytes( JsonSerializer.Serialize( new ClipWithMore( one, 3 ), engine ) );
	var compact = Encoding.UTF8.GetBytes( JsonSerializer.Serialize( new Clip( one ) ) );

	Check( !Throws( life ), "a life's clip splices" );
	Check( Throws( extra ), "a clip with another property after Tracks doesn't" );
	Check( Throws( compact ), "an unindented clip doesn't" );

	var empty = false;
	try { new TheaterClipJson( new MemoryStream() ).Finish(); }
	catch ( InvalidOperationException ) { empty = true; }
	Check( empty, "a clip with no lives isn't spliced" );
}

Console.WriteLine( failures == 0 ? "All checks passed." : $"{failures} check(s) failed." );
return failures == 0 ? 0 : 1;

// MovieMaker's ClipModel and TrackModel, as far as their JSON goes.
sealed record Clip( [property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] List<Track> Tracks );

sealed record ClipWithMore( [property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] List<Track> Tracks, int Version );

sealed record Meta( Guid ReferenceId, [property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] string PrefabSource, int Order );

sealed record Track( string Kind, string Name, string Type,
	[property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] Guid? Id,
	[property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] Meta Metadata,
	[property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] List<Track> Children,
	[property: JsonIgnore( Condition = JsonIgnoreCondition.WhenWritingNull )] JsonArray Blocks );
