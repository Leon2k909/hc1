namespace Facepunch.Gunsmith;

/// <summary>Remove common clipboard formatting without changing the case-sensitive build payload.</summary>
internal static class WeaponBuildCodeText
{
	internal static bool TryNormalize( string text, int maximumLength, out string clean )
	{
		clean = null;
		if ( string.IsNullOrWhiteSpace( text ) || text.Length > maximumLength ) return false;
		text = text.Trim();

		if ( text.StartsWith( "```", StringComparison.Ordinal ) )
		{
			if ( text.Length < 6 || !text.EndsWith( "```", StringComparison.Ordinal ) ) return false;
			text = text[3..^3].Trim();
			var endOfHeader = text.IndexOfAny( new[] { '\r', '\n' } );
			if ( endOfHeader >= 0 && text[..endOfHeader].Trim().ToLowerInvariant() is "text" or "txt" or "hc1" )
				text = text[(endOfHeader + 1)..];
		}
		else if ( text[0] is '`' or '"' or '\'' )
		{
			if ( text.Length < 2 || text[^1] != text[0] ) return false;
			text = text[1..^1];
		}

		var normalized = new string( text.Where( c => !char.IsWhiteSpace( c ) && c is not ('\u200b' or '\ufeff' or '\u2060') ).ToArray() );
		if ( normalized.Length == 0 || !normalized.All( c => c is >= 'A' and <= 'Z' or >= 'a' and <= 'z'
			or >= '0' and <= '9' or '-' or '_' or '+' or '/' or '=' ) ) return false;

		clean = normalized;
		return true;
	}
}
