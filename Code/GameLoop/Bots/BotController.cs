namespace Facepunch;

/// <summary>
/// Interface for pawns that can be controlled by bots
/// </summary>
public interface IBotController
{
	/// <summary>
	/// Enable this component
	/// </summary>
	public bool Enabled { set; }

	/// <summary>
	/// Update bot control logic for this pawn
	/// </summary>
	/// <param name="bot">The bot controller driving this pawn</param>
	void OnControl( BotController bot );
}

public class BotController : Component
{
	[RequireComponent]
	public Client Client { get; private set; }

	[Property] public float ControlInterval { get; set; } = 0.1f;

	private Pawn _cachedPawn;
	private IBotController _cachedController;
	private Component _cachedControllerComponent;
	private TimeSince _timeSinceLastControl;

	protected override void OnFixedUpdate()
	{
		if ( IsProxy )
			return;

		if ( !Client.IsValid() || !Client.IsBot )
			return;

		var currentPawn = Client?.Pawn;
		if ( !currentPawn.IsValid() )
			return;

		if ( GameUtils.IsCombatFrozen )
			return;

		if ( _cachedPawn != currentPawn || !_cachedControllerComponent.IsValid() )
		{
			_cachedPawn = currentPawn;
			_cachedController = currentPawn.GetComponentInChildren<IBotController>( true );
			_cachedControllerComponent = _cachedController as Component;
		}

		if ( _cachedController is null )
			return;

		if ( !_cachedControllerComponent.IsValid() )
			return;

		if ( ControlInterval > 0f && _timeSinceLastControl < ControlInterval )
			return;

		_timeSinceLastControl = 0f;
		_cachedControllerComponent.Enabled = true;
		_cachedController.OnControl( this );
	}
}
