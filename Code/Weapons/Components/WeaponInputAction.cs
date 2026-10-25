using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A weapon component that reacts to input actions.
/// </summary>
public abstract class WeaponInputAction : EquipmentComponent,
	IGameEventHandler<EquipmentDeployedEvent>
{
	/// <summary>
	/// What input action are we going to listen for?
	/// </summary>
	[Property, Category( "Base" )] public List<string> InputActions { get; set; } = new() { "Attack1" };
	
	/// <summary>
	/// Should we perform the action when ALL input actions match, or any?
	/// </summary>
	[Property, Category( "Base" )] public bool RequiresAllInputActions { get; set; }

	/// <summary>
	/// ActionGraphs action so you can do stuff with visual scripting.
	/// </summary>
	[Property, Category( "Base" )] public Action<WeaponInputAction> OnInputAction { get; set; }

	bool RunningWhileDeployed { get; set; }

	/// <summary>
	/// Whether <see cref="RunningWhileDeployed"/> has been worked out since the equipment was deployed. A new pawn's
	/// equipment can be deployed before the pawn is possessed (that comes by RPC after it spawns), so it's worked out on
	/// the first update the owner is ours. Without that, fire held through a respawn counted as a new pull.
	/// </summary>
	bool _heldInputChecked;

	/// <summary>
	/// Whether a button held since before the equipment was deployed counts as held. Fire doesn't, so a click held
	/// through a switch or a respawn isn't a new pull. Aiming does (<see cref="Aimable"/>): aim held through a switch
	/// aims the gun switched to once the new life's aim-release check has passed.
	/// </summary>
	protected virtual bool TakesInputHeldThroughDeploy => false;

	bool HeldSinceBeforeDeploy() => !TakesInputHeldThroughDeploy && InputActions.Any( x => Input.Down( x ) );

	// The body is a named method: hotload can't re-link static lambdas inside explicit generic interface methods
	// ("Unable to find matching substitution for a static method"), so they'd throw after every hotload.
	void IGameEventHandler<EquipmentDeployedEvent>.OnGameEvent( EquipmentDeployedEvent eventArgs ) => OnWeaponDeployed( eventArgs );

	void OnWeaponDeployed( EquipmentDeployedEvent eventArgs )
	{
		if ( eventArgs.Equipment != Equipment ) return;
		ResetInputState();
		_heldInputChecked = Equipment?.Owner?.IsLocallyControlled ?? false;
		if ( _heldInputChecked )
		{
			RunningWhileDeployed = HeldSinceBeforeDeploy();
		}
	}

	bool isDown = false;

	protected bool IsDown() => IsTakingInput;

	/// <summary>Discard the previous life/deploy's press; held input is checked when the owner is controlled locally.</summary>
	internal void ResetInputState()
	{
		isDown = false;
		RunningWhileDeployed = false;
		_heldInputChecked = false;
	}

	/// <summary>
	/// Whether the equipment takes this action's input: it's held, and wasn't held since before the equipment was
	/// deployed or clicked in a menu. The pawn's sprint goes by it (<c>PlayerPawn.IsPullingTrigger</c>).
	/// </summary>
	public bool IsTakingInput => isDown && !RunningWhileDeployed;

	/// <summary>
	/// Called when the input method succeeds.
	/// </summary>
	protected virtual void OnInput()
	{
		//
	}

	/// <summary>
	/// When the button is up
	/// </summary>
	protected virtual void OnInputUp()
	{
	}

	/// <summary>
	/// When the button is down
	/// </summary>
	protected virtual void OnInputDown()
	{
		//
	}

	protected virtual void OnInputUpdate()
	{
		//
	}

	/// <summary>Cancel queued actions when the gunsmith takes weapon input.</summary>
	protected virtual void OnInputSuppressed()
	{
	}

	protected override void OnFixedUpdate()
	{
		if ( !Equipment.IsValid() )
			return;
		
		// Don't execute weapon components on weapons that aren't deployed.
		if ( !Equipment.IsDeployed )
			return;
		
		if ( !Equipment.Owner.IsValid() )
			return;

		// We only care about input actions coming from the owning object.
		if ( !Equipment.Owner.IsLocallyControlled )
			return;

		// UI clicks must never reach OnInputUpdate (semi/burst fire reads input there).
		// Keep the release latch set even if the UI consumes the raw mouse button.
		if ( GameUtils.IsGunsmithStudioOpen() )
		{
			RunningWhileDeployed = true;
			_heldInputChecked = true;
			if ( isDown )
			{
				isDown = false;
				OnInputUp();
			}
			OnInputSuppressed();
			return;
		}

		if ( !_heldInputChecked )
		{
			RunningWhileDeployed = HeldSinceBeforeDeploy();
			_heldInputChecked = true;
		}

		if ( InputActions.All( x => !Input.Down( x ) ) )
		{
			RunningWhileDeployed = false;
		}

		if ( RunningWhileDeployed )
			return;

		OnInputUpdate();

		bool matched = false;

		// Clicking a class in the class menu, or anything at the Zombies workbench, isn't weapon input.
		var menuOpen = UI.ClassSelect.IsAnyOpen || UI.TacticalBuyMenu.IsAnyOpen || UI.ZombiesWorkbenchPanel.IsAnyOpen || Equipment.Owner.IsPipeClimbing;

		foreach ( var action in InputActions )
		{
			var down = !menuOpen && Input.Down( action );

			if ( RequiresAllInputActions && !down )
			{
				matched = false;
				break;
			}
			if ( down )
			{
				matched = true;
			}
		}

		if ( matched )
		{
			OnInput();
			OnInputAction?.Invoke( this );

			if ( !isDown )
			{
				OnInputDown();
				isDown = true;
			}
		}
		else
		{
			if ( isDown )
			{
				OnInputUp();
				isDown = false;
			}
		}
	}
}
