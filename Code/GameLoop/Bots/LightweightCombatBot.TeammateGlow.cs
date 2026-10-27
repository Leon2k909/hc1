namespace Facepunch;

public sealed partial class LightweightCombatBot
{
	private HighlightOutline _teammateGlow;

	private void UpdateTeammateGlow()
	{
		var show = IsAlive && Renderer.IsValid() && TeammateOcclusionGlow.IsTeammate( Team );
		if ( !show )
		{
			if ( _teammateGlow.IsValid() )
				_teammateGlow.Enabled = false;
			return;
		}

		if ( !_teammateGlow.IsValid() )
		{
			_teammateGlow = Components.GetOrCreate<HighlightOutline>();
			_teammateGlow.Flags |= ComponentFlags.NotSaved | ComponentFlags.NotNetworked;
		}

		TeammateOcclusionGlow.Apply( _teammateGlow, Team.GetColor() );
		_teammateGlow.Enabled = true;
	}
}
