namespace Facepunch;

public partial class WorldModel : WeaponModel
{
	/// <summary>
	/// Optional left hand IK target on the weapon (e.g. foregrip position).
	/// When set, the player's AnimationHelper will IK the left hand here.
	/// </summary>
	[Property] public GameObject IkLeftHand { get; set; }
}
