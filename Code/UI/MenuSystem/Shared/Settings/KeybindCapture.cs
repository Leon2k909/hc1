namespace Facepunch.UI;

/// <summary>Wait for a chord's main key, or accept a modifier on release if it was pressed alone.</summary>
internal sealed class KeybindCapture
{
	private string _pendingModifier;

	public void Reset() => _pendingModifier = null;

	public bool ShouldCapture( string button, bool pressed )
	{
		if ( string.IsNullOrWhiteSpace( button ) ) return false;
		var modifier = button.Trim().ToLowerInvariant() switch
		{
			"ctrl" or "control" or "leftcontrol" or "rightcontrol" => "ctrl",
			"shift" or "leftshift" or "rightshift" => "shift",
			"alt" or "leftalt" or "rightalt" => "alt",
			_ => null
		};

		if ( modifier is not null )
		{
			if ( pressed )
			{
				_pendingModifier = modifier;
				return false;
			}

			if ( _pendingModifier != modifier ) return false;
			Reset();
			return true;
		}

		if ( !pressed ) return false;
		Reset();
		return true;
	}
}
