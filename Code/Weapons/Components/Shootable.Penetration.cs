namespace Facepunch;

public partial class Shootable
{
	/// <summary>
	/// Impacts in shot order. Solid masonry and unspecified surfaces stop rounds. Only explicitly supported light
	/// materials can be crossed, after finding an exit on the exact shape hit within its permitted thickness.
	/// Limits are conservative gameplay rules in map units, not a ballistic simulation.
	/// </summary>
	public static IEnumerable<SceneTraceResult> ResolvePenetration( Scene scene, IEnumerable<SceneTraceResult> traces, float budget )
	{
		var remaining = budget.Clamp( 0f, 8f );
		foreach ( var entry in traces.OrderBy( x => x.Distance ) )
		{
			if ( !entry.Hit ) continue;
			// The stopping surface still receives its impact, even when no round emerges from it.
			yield return entry;
			if ( entry.StartedSolid || IsBody( entry ) || remaining <= 0f ) yield break;
			var limit = MathF.Min( remaining, PenetrableDepth( entry.Surface ) );
			if ( limit <= 0f || entry.Shape is null ) yield break;

			var direction = entry.Direction.Normal;
			var exits = scene.Trace.Ray( entry.EndPosition + direction * (limit + .125f),
				entry.EndPosition + direction * .01f ).WithoutTags( "trigger", "playerclip", "movement" ).RunAll();
			var exit = exits.FirstOrDefault( x => x.Hit && !x.StartedSolid && x.Shape == entry.Shape
				&& x.Normal.Dot( direction ) > .01f );
			if ( !exit.Hit ) yield break;
			var thickness = (exit.EndPosition - entry.EndPosition).Dot( direction );
			if ( thickness <= 0f || thickness > limit ) yield break;
			remaining -= thickness;
		}
	}

	private static float PenetrableDepth( Surface surface )
	{
		// Unknown/default, brick, stone, concrete and solid metal are intentionally not penetrable.
		for ( var depth = 0; surface is not null && depth < 8; depth++, surface = surface.GetBaseSurface() )
		{
			var name = surface.ResourceName?.ToLowerInvariant() ?? "";
			if ( name is "metal.sheet" ) return .125f;
			// Real window glass stops nothing, and maps model a pane's collision thicker than the glass: Belltower's
			// church windows are 2 units, the Ridgeback's breakable panes 0.5.
			if ( name is "glass" or "glass.pane" ) return 3f;
			if ( name is "wood" ) return 4f;
			if ( name is "plastic" ) return 2f;
			if ( name is "fabric" or "paper" or "cardboard" ) return 1f;
		}
		return 0f;
	}
}
