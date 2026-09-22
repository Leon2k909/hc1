using Sandbox.Events;

namespace Facepunch;

public partial class PlayerPawn :
	IGameEventHandler<EquipmentDeployedEvent>,
	IGameEventHandler<EquipmentHolsteredEvent>
{
	/// <summary>
	/// What weapon are we using?
	/// </summary>
	[Property, ReadOnly] public Equipment CurrentEquipment { get; private set; }

	public GameObject ViewModelGameObject => CameraController.CameraObject;

	/// <summary>
	/// How inaccurate are things like gunshots?
	/// </summary>
	public float Spread { get; set; }

	/// <summary>
	/// Can we open and use the buy menu?
	/// </summary>
	public bool CanBuy => HealthComponent.State == LifeState.Alive && IsInBuyZone;

	private bool IsInBuyZone => Client?.BuyMenuMode is BuyMenuMode.EnabledEverywhere
		|| Client?.BuyMenuMode is BuyMenuMode.EnabledInBuyZone && GetZone<BuyZone>() is not null;

	private void UpdateRecoilAndSpread()
	{
		// No bloom. Bullets go exactly where the crosshair points whether hipfiring or aimed, moving
		// or still, grounded or in the air. Spread also drives the crosshair gap, so zeroing it here
		// keeps the crosshair honest instead of animating a spread the bullets no longer have.
		// Recoil is untouched — that still kicks your aim, it just doesn't randomise the shot.
		Spread = 0f;
	}

	void IGameEventHandler<EquipmentDeployedEvent>.OnGameEvent( EquipmentDeployedEvent eventArgs )
	{
		CurrentEquipment = eventArgs.Equipment;
	}

	void IGameEventHandler<EquipmentHolsteredEvent>.OnGameEvent( EquipmentHolsteredEvent eventArgs )
	{
		if ( eventArgs.Equipment == CurrentEquipment )
			CurrentEquipment = null;
	}

	[Rpc.Owner]
	private void SetCurrentWeapon( Equipment equipment )
	{
		SetCurrentEquipment( equipment );
	}

	[Rpc.Owner]
	private void ClearCurrentWeapon()
	{
		if ( CurrentEquipment.IsValid() ) CurrentEquipment.Holster();
	}

	public void Holster()
	{
		if ( IsProxy )
		{
			if ( Networking.IsHost )
				ClearCurrentWeapon();

			return;
		}

		CurrentEquipment?.Holster();
	}

	public TimeSince TimeSinceWeaponDeployed { get; private set; }

	public void SetCurrentEquipment( Equipment weapon )
	{
		if ( weapon == CurrentEquipment ) 
			return;

		ClearCurrentWeapon();

		if ( IsProxy )
		{
			if ( Networking.IsHost )
				SetCurrentWeapon( weapon );

			return;
		}

		TimeSinceWeaponDeployed = 0;

		weapon.Deploy();
	}

	public void ClearViewModel()
	{
		foreach ( var weapon in Inventory.Equipment )
		{
			weapon.DestroyViewModel();
		}
	}

	public void CreateViewModel( bool playDeployEffects = true )
	{
		if ( CameraController.Mode != CameraMode.FirstPerson )
			return;

		var weapon = CurrentEquipment;
		if ( weapon.IsValid() )
			weapon.CreateViewModel( playDeployEffects );
	}
}
