namespace Facepunch;

/// <summary>
/// Where a Zombies map wants its zombies to come from: a gap in a fence, the edge of the woods, behind a building.
/// <see cref="ZombiesRoundSystem"/> spawns at these before anything else, picking one out of the players' sight, not
/// too near them and with a walk to someone. Without them it uses the map's spawn points or the navmesh round the
/// players. Riverside places its own (Tools/riverside_map.py). Put each on the navmesh.
/// </summary>
public sealed class ZombieSpawnPoint : Component
{
	protected override void DrawGizmos()
	{
		Gizmo.Draw.Color = new Color( 0.45f, 0.8f, 0.3f, 0.7f );
		Gizmo.Draw.LineCylinder( Vector3.Zero, Vector3.Up * 72f, 16f, 16f, 12 );
	}
}
