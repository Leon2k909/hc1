namespace Facepunch;

/// <summary>
/// Where a map's battle royale is fought: the first circle, centred on this object. Without one the match takes in the
/// whole navmesh (<see cref="BattleRoyaleMatch.EnsureFirstCircle"/>), which suits Flatgrass. Ridgeback's navmesh also
/// covers ledges up in its mountains, which nobody can reach, so it says where its valley is instead.
/// </summary>
[Title( "Battle Royale Area" ), Icon( "radio_button_unchecked" )]
public sealed class BattleRoyaleArea : Component
{
	/// <summary> The first circle's radius. </summary>
	[Property] public float Radius { get; set; } = 20000f;

	protected override void DrawGizmos()
	{
		Gizmo.Draw.Color = Color.Cyan.WithAlpha( Gizmo.IsSelected ? 0.9f : 0.5f );
		Gizmo.Draw.LineCircle( Vector3.Zero, Radius, 0f, 360f, 128 );
	}
}
