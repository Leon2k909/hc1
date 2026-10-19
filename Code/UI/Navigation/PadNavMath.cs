namespace Facepunch.UI;

/// <summary>
/// The D-pad's arithmetic for <see cref="PadNavigation"/>: where the focus goes next, from the targets' screen
/// rectangles, and a slider's next value. Nothing here touches the UI, so Tools/PadNavChecks can run it.
/// </summary>
public static class PadNavMath
{
	/// <summary>
	/// A slider's next value from the D-pad: about fifty presses from end to end on the slider's own steps, so a fine
	/// one (a sensitivity's 0.01) doesn't take hundreds, and four times as far once it's been held a while.
	/// </summary>
	public static float SliderStep( float value, float min, float max, float step, int direction, float heldFor )
	{
		var range = max - min;
		if ( range <= 0f ) return value;

		var fine = step > 0f ? step : range / 100f;
		var unit = MathF.Max( fine, MathF.Round( range / 50f / fine ) * fine );
		if ( heldFor > 1.2f ) unit *= 4f;

		var next = value + direction * unit;
		next = min + MathF.Round( (next - min) / fine ) * fine;
		return Math.Clamp( next, min, max );
	}

	/// <summary>
	/// The index of the rectangle the focus moves to from <paramref name="from"/> in <paramref name="direction"/> (a unit
	/// axis, y down), or -1 if nothing lies that way. The nearest edge that way wins, with sideways distance counted
	/// three times over, so a move stays in its column or row: down a list rather than across to the next column.
	/// </summary>
	public static int Pick( Rect from, IReadOnlyList<Rect> candidates, Vector2 direction, int skip = -1 )
	{
		var best = -1;
		var bestScore = float.MaxValue;
		var centre = from.Center;
		var vertical = direction.y != 0f;

		for ( var i = 0; i < candidates.Count; i++ )
		{
			if ( i == skip ) continue;
			var rect = candidates[i];

			// Its middle has to be past ours that way.
			var along = Vector2.Dot( rect.Center - centre, direction );
			if ( along < 1f ) continue;

			// How far its near edge is past our far one (overlapping counts as touching).
			var gap = direction.x > 0f ? rect.Left - from.Right
				: direction.x < 0f ? from.Left - rect.Right
				: direction.y > 0f ? rect.Top - from.Bottom
				: from.Top - rect.Bottom;
			gap = MathF.Max( gap, 0f );

			// How far apart they are sideways: 0 while they overlap, and a little for their middles, to break ties.
			var sideways = vertical
				? SpanGap( from.Left, from.Right, rect.Left, rect.Right )
				: SpanGap( from.Top, from.Bottom, rect.Top, rect.Bottom );
			var offset = vertical ? MathF.Abs( rect.Center.x - centre.x ) : MathF.Abs( rect.Center.y - centre.y );

			var score = gap + sideways * 3f + offset * 0.1f;
			if ( score < bestScore )
			{
				bestScore = score;
				best = i;
			}
		}

		return best;
	}

	/// <summary>
	/// How far apart two rectangles are: the gap between their edges (0 where they overlap), plus a little of the distance
	/// between their middles to break ties. Picks the control that takes the place of one that went away.
	/// </summary>
	public static float Distance( Rect a, Rect b )
	{
		var dx = SpanGap( a.Left, a.Right, b.Left, b.Right );
		var dy = SpanGap( a.Top, a.Bottom, b.Top, b.Bottom );
		return MathF.Sqrt( dx * dx + dy * dy ) + 0.1f * a.Center.Distance( b.Center );
	}

	private static float SpanGap( float aMin, float aMax, float bMin, float bMax ) =>
		MathF.Max( 0f, MathF.Max( aMin - bMax, bMin - aMax ) );
}
