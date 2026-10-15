namespace Facepunch;

/// <summary>
/// A Zombies map's own place for a buy station: the station stands here, its front along this object's forward, its
/// foot on the floor under it. <see cref="ZombiesRoundSystem.PlaceBuyStations"/> takes the spots of each kind in their
/// <see cref="Order"/>, and places any station without one as it always has. Riverside places its own
/// (Tools/riverside_map.py): the weapon crate in the store, the workbench by the office, wall weapons on walls.
/// </summary>
public sealed class ZombiesStationSpot : Component
{
	[Property] public ZombiesBuyKind Kind { get; set; } = ZombiesBuyKind.WallWeapon;

	/// <summary>Spots of one kind are used lowest first: the first wall weapon (the pistol) takes the lowest.</summary>
	[Property] public int Order { get; set; }

	protected override void DrawGizmos()
	{
		Gizmo.Draw.Color = new Color( 1f, 0.75f, 0.3f, 0.8f );
		Gizmo.Draw.LineBBox( new BBox( new Vector3( -20f, -32f, 0f ), new Vector3( 20f, 32f, 70f ) ) );
		Gizmo.Draw.Arrow( Vector3.Up * 35f, Vector3.Up * 35f + Vector3.Forward * 40f );
	}
}
