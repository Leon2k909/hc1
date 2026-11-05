namespace Facepunch;

public sealed class SpectateController : Pawn
{
	[RequireComponent] PawnCameraController PawnCameraController { get; set; }
	[Property] public float FlySpeed = 10f;
	public override CameraComponent Camera => PawnCameraController.Camera;

	/// <summary>
	/// What are we called?
	/// </summary>
	public override string DisplayName => "Spectator";

	protected override void OnUpdate()
	{
		if ( !IsLocallyControlled )
			return;

		if ( Input.Suppressed || GameUtils.IsInteractiveMouseUiOpen() )
			return;

		EyeAngles += Input.AnalogLook;
		EyeAngles = EyeAngles.WithPitch( EyeAngles.pitch.Clamp( -90, 90 ) );
		WorldRotation = EyeAngles.ToRotation();

		// Use the player's existing binds: sprint crosses the map quickly, while walk
		// gives finer camera placement. Precision takes priority if both are held.
		var speed = FlySpeed * (Input.Down( "Walk" ) ? 0.25f : Input.Down( "Run" ) ? 4f : 1f);
		WorldPosition += Input.AnalogMove * WorldRotation * speed * Time.Delta;
	}

	public override void OnDePossess()
	{
		PawnCameraController.SetActive( false );
	}

	public override void OnPossess()
	{
		PawnCameraController.SetActive( true );
	}
}
