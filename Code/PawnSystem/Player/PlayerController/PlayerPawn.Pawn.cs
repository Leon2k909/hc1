namespace Facepunch;

public partial class PlayerPawn
{
	/// <summary>
	/// Is this player the currently possessed controller
	/// </summary>
	public bool IsViewer => IsPossessed;

	/// <summary>
	/// What are we called?
	/// </summary>
	public override string DisplayName
	{
		get
		{
			var client = Client;
			return client is not null && client.IsValid() ? client.DisplayName : "Invalid Player";
		}
	}

	/// <summary>
	/// Is the player controlled by us?
	/// </summary>
	public override bool IsLocallyControlled
	{
		get
		{
			var client = Client;
			return base.IsLocallyControlled && (client is null || !client.IsValid() || !client.IsBot);
		}
	}

	/// <summary>
	/// Called when possessed.
	/// </summary>
	public override void OnPossess()
	{
		CameraController.SetActive( true );

		// if we're spectating a remote player, use the camera mode preference
		// otherwise: first person for now
		var spectateSystem = SpectateSystem.Instance;
		var client = Client;
		if ( spectateSystem.IsValid() && ( IsProxy || ( client is not null && client.IsValid() && client.IsBot ) ) )
		{
			CameraController.Mode = spectateSystem.CameraMode;
		}
		else
		{
			CameraController.Mode = CameraMode.FirstPerson;
		}
	}

	public override void OnDePossess()
	{
		CameraController.SetActive( false );
	}
}
