namespace Facepunch;

public partial class DroppedEquipment
{
	/// <summary>Release keeps the holder's linear velocity; remote movement comes from replicated state.</summary>
	internal static Vector3 InheritedVelocity( Equipment source )
	{
		var owner = source.IsValid() ? source.Owner : null;
		if ( !owner.IsValid() ) return Vector3.Zero;
		var controller = owner.CharacterController;
		var velocity = owner.IsLocallyControlled && controller.IsValid()
			? controller.Velocity : owner.SyncedVelocity;
		return float.IsFinite( velocity.x ) && float.IsFinite( velocity.y ) && float.IsFinite( velocity.z )
			? velocity : Vector3.Zero;
	}
}
