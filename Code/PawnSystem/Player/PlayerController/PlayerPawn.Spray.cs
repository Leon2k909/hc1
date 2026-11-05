namespace Facepunch;

public partial class PlayerPawn
{
	internal Vector3 SprayEyePosition => WorldPosition + Vector3.Up * (Height + _smoothEyeHeight);
}
