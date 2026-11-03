namespace Facepunch;

/// <summary>
/// Behavior that makes a ping follow a player until they're no longer visible.
/// </summary>
public partial class PlayerPingReceiver : Component, IPingReceiver
{
	[RequireComponent] PlayerPawn Player { get; set; }

	private Vector3 _lastKnownPosition = Vector3.Zero;
	private bool _wasLost = false;

	string IPingReceiver.Text => "";
	string IPingReceiver.Icon => "ui/minimaps/enemy_icon.png";
	Color? IPingReceiver.Color => "#EE4B2B";

	bool IPingReceiver.ShouldShow() => UpdateTracking();

	Vector3 IPingReceiver.Position
	{
		get
		{
			UpdateTracking();
			return _lastKnownPosition;
		}
	}

	private bool UpdateTracking()
	{
		// Either HUD may ask for visibility before position; losing the target stays latched until a new ping.
		if ( _wasLost ) return false;
		if ( !Player.IsValid() || !Player.HealthComponent.IsValid() || Player.HealthComponent.State != LifeState.Alive
			|| !Player.Spottable.IsValid() || !Player.Spottable.IsSpotted )
		{
			_wasLost = true;
			return false;
		}

		_lastKnownPosition = Player.AimRay.Position + Vector3.Up * 32f;
		return true;
	}

	void IPingReceiver.OnPing()
	{
		_wasLost = false;
		UpdateTracking();
	}
}
