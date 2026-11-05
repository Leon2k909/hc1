namespace Facepunch;

public partial class Shootable
{
	/// <summary>
	/// Close cover can clear the sights while still covering the bore. Keep the usual sight-aligned
	/// shot in the open, but fire from below the sights when solid cover occupies the first four feet
	/// of the bore line. Use the configured sight height, not the animated viewmodel's render position.
	/// </summary>
	private void ApplyCloseCoverClearance( ref Vector3 start, Vector3 forward, Rotation aim )
	{
		// Ballistic modes already trace from below the sights and follow the bore's actual trajectory.
		if ( BulletDrop.IsActive || !float.IsFinite( SightHeight ) || SightHeight <= 0f ) return;
		if ( !float.IsFinite( MaxRange ) || MaxRange <= 0f ) return;

		var bore = start - aim.Up * SightHeight;
		var reach = MathF.Min( MaxRange, 48f );
		var cover = BulletTrace( bore, bore + forward * reach ).RunAll()
			.Any( hit => hit.Hit && !IsBody( hit ) );
		if ( !cover ) return;

		// The full shot, including penetrable cover and anything beyond it, still goes through the
		// normal resolver. Do not replace it with a synthetic hit or consume a shot without impact.
		start = bore;
	}
}
