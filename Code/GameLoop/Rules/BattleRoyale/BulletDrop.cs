namespace Facepunch;

/// <summary>
/// Turns on real bullet drop (<see cref="Shootable"/>'s Ballistics values) for this game mode. Without it, shots go
/// dead straight along the sights.
/// </summary>
[Title( "Bullet Drop" ), Icon( "south_east" )]
public sealed class BulletDrop : Component
{
	/// <summary>Whether the active game mode has bullet drop.</summary>
	public static bool IsActive => GameMode.Instance.IsValid() && GameMode.Instance.Get<BulletDrop>() is not null;
}
