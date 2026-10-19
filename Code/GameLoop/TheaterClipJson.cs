using System;
using System.IO;
using System.Text.Json;

namespace Facepunch;

/// <summary>
/// A Theater recording's file, put together from its lives' JSON (<see cref="TheaterReplays.WriteClip"/>) exactly as the
/// engine's Json.Serialize writes the whole clip, and buffered. Nothing here touches the engine, so Tools/TheaterJsonChecks
/// can run it against .NET's own serializer.
/// <para>
/// A clip's JSON is "{", a line end, "  \"Tracks\": [", its lives' entries one after another, split by commas (each a
/// line end, an indent and its object), then a line end, "  ]", a line end and "}". A clip holding only one life is the
/// same with that life's entry alone, so <see cref="AddLife"/> takes the entry out of each and lays it in the file's.
/// </para>
/// <para>
/// Lives are serialised with a Utf8JsonWriter of our own (<see cref="WriterOptions"/>), which escapes with .NET's default
/// encoder: that writes the '+' in every block's base64 samples (and '&amp;', '&lt;', '&gt;', ''', '`') as \u00XX and a
/// quote as ", where Json.Serialize leaves them as they are and writes \". They're put back, so the file is byte for
/// byte what Json.Serialize writes, and no bigger. Escapes of anything else read the same either way and stay: a name with
/// letters outside ASCII keeps them escaped, where Json.Serialize writes them out.
/// </para>
/// </summary>
public sealed class TheaterClipJson( Stream stream ) : IDisposable
{
	/// <summary> Laid out as Json.Serialize lays it out: two-space indents and the platform's line ends. </summary>
	public static JsonWriterOptions WriterOptions => new() { Indented = true, SkipValidation = true };

	/// <summary> A life's JSON isn't laid out as expected (an s&amp;box update?). </summary>
	public sealed class LayoutException( string message ) : Exception( message );

	readonly byte[] _buffer = new byte[64 * 1024];
	int _count;

	byte[] _start;
	byte[] _end;
	int _lives;

	/// <summary> Bytes written so far. </summary>
	public long Written { get; private set; }

	/// <summary> Adds a life from the JSON of a clip holding only it. </summary>
	public void AddLife( ReadOnlySpan<byte> json )
	{
		if ( _start is null )
		{
			var newLine = NewLineAfterBrace( json );
			_start = Ascii( "{" + newLine + "  \"Tracks\": [" );
			_end = Ascii( newLine + "  ]" + newLine + "}" );
		}

		if ( json.Length <= _start.Length + _end.Length || !json.StartsWith( _start ) || !json.EndsWith( _end )
			|| json[_start.Length] != _end[0] )
			throw new LayoutException( "a life's clip isn't a single entry in Tracks" );

		if ( _lives++ == 0 )
			Write( _start );
		else
			WriteByte( (byte)',' );

		WriteRelaxed( json[_start.Length..^_end.Length] );
	}

	/// <summary> Closes the clip once its lives are in. </summary>
	public void Finish()
	{
		if ( _lives == 0 )
			throw new InvalidOperationException( "A clip with no lives is written whole." );

		Write( _end );
	}

	/// <summary> Writes a whole clip's JSON, with its escapes as Json.Serialize writes them. </summary>
	public void WriteWhole( ReadOnlySpan<byte> json )
	{
		WriteRelaxed( json );
	}

	/// <summary> The line end Json.Serialize indents with, from the one after a clip's opening brace. </summary>
	static string NewLineAfterBrace( ReadOnlySpan<byte> json )
	{
		if ( json.Length >= 3 && json[0] == '{' && json[1] == '\r' && json[2] == '\n' )
			return "\r\n";

		if ( json.Length >= 2 && json[0] == '{' && json[1] == '\n' )
			return "\n";

		throw new LayoutException( "a clip doesn't start with a brace and a line end" );
	}

	static byte[] Ascii( string text )
	{
		var bytes = new byte[text.Length];
		for ( var i = 0; i < text.Length; i++ )
			bytes[i] = (byte)text[i];

		return bytes;
	}

	void WriteRelaxed( ReadOnlySpan<byte> json )
	{
		while ( !json.IsEmpty )
		{
			var escape = json.IndexOf( (byte)'\\' );
			if ( escape < 0 )
			{
				Write( json );
				return;
			}

			Write( json[..escape] );
			json = json[escape..];

			if ( TryReadPrintableEscape( json, out var character ) )
			{
				if ( character == '"' )
					WriteByte( (byte)'\\' );

				WriteByte( character );
				json = json[6..];
				continue;
			}

			// Any other escape reads the same either way. It's copied whole, so a backslash it escapes isn't taken for the
			// start of another.
			var length = Math.Min( json.Length, json.Length > 1 && json[1] == 'u' ? 6 : 2 );
			Write( json[..length] );
			json = json[length..];
		}
	}

	/// <summary> A "\u00XX" escape of a printable ASCII character other than the backslash (written "\\" either way). </summary>
	static bool TryReadPrintableEscape( ReadOnlySpan<byte> json, out byte character )
	{
		character = 0;

		if ( json.Length < 6 || json[1] != 'u' || json[2] != '0' || json[3] != '0' )
			return false;

		var high = HexDigit( json[4] );
		var low = HexDigit( json[5] );
		if ( high < 0 || low < 0 )
			return false;

		var value = high * 16 + low;
		if ( value < 0x20 || value > 0x7E || value == '\\' )
			return false;

		character = (byte)value;
		return true;
	}

	static int HexDigit( byte value ) => value switch
	{
		>= (byte)'0' and <= (byte)'9' => value - '0',
		>= (byte)'A' and <= (byte)'F' => value - 'A' + 10,
		>= (byte)'a' and <= (byte)'f' => value - 'a' + 10,
		_ => -1
	};

	void Write( ReadOnlySpan<byte> bytes )
	{
		while ( !bytes.IsEmpty )
		{
			if ( _count == _buffer.Length )
				Flush();

			var length = Math.Min( bytes.Length, _buffer.Length - _count );
			bytes[..length].CopyTo( _buffer.AsSpan( _count ) );

			_count += length;
			Written += length;
			bytes = bytes[length..];
		}
	}

	void WriteByte( byte value )
	{
		if ( _count == _buffer.Length )
			Flush();

		_buffer[_count++] = value;
		Written++;
	}

	void Flush()
	{
		stream.Write( _buffer, 0, _count );
		_count = 0;
	}

	public void Dispose()
	{
		Flush();
		stream.Dispose();
	}
}
