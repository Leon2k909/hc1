namespace Facepunch;

public partial class WorldModel : WeaponModel
{
	/// <summary>The drone station is held at the chest with both hands, independently of the weapon socket.</summary>
	[Property] public bool UseTabletPose { get; set; }

	/// <summary>
	/// Optional left hand IK target on the weapon (e.g. foregrip position).
	/// When set, the player's AnimationHelper will IK the left hand here.
	/// </summary>
	[Property] public GameObject IkLeftHand { get; set; }
}
