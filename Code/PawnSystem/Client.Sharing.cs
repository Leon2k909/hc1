using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Client
{
	// Lives on the client state, so deaths/respawns don't remove the player's last shared builds or crosshair.
	[Sync( SyncFlags.FromHost ), Change( nameof( OnSharedBuildChanged ) )] public string SharedPrimaryBuild { get; private set; } = "";
	[Sync( SyncFlags.FromHost ), Change( nameof( OnSharedBuildChanged ) )] public string SharedSecondaryBuild { get; private set; } = "";
	[Sync( SyncFlags.FromHost )] public string SharedCrosshairSettings { get; private set; } = "";

	private RealTimeSince _sinceSharingCheck = 1f;
	private RealTimeSince _sinceSharingReceived = 1f;
	private string _sentPrimaryBuild;
	private string _sentSecondaryBuild;
	private string _sentCrosshairSettings;

	private void UpdateSharing()
	{
		if ( !IsLocalPlayer || _sinceSharingCheck < 1f )
			return;
		_sinceSharingCheck = 0f;

		var primary = _sentPrimaryBuild ?? "";
		var secondary = _sentSecondaryBuild ?? "";
		if ( PlayerPawn.IsValid() && PlayerPawn.Inventory.IsValid()
			&& PlayerPawn.HealthComponent?.State == LifeState.Alive )
		{
			primary = ShareHeldGun( EquipmentSlot.Primary );
			secondary = ShareHeldGun( EquipmentSlot.Secondary );
		}
		else if ( _sentPrimaryBuild is null )
		{
			// A joining player or spectator can also share their selected class before their first spawn.
			primary = GunsmithLoadoutManager.ExportWeaponBuildCode( GunsmithLoadoutManager.GetPrimaryResource() );
			secondary = GunsmithLoadoutManager.ExportWeaponBuildCode( GunsmithLoadoutManager.GetSecondaryResource() );
		}

		var crosshair = CrosshairManager.ShareSettings();
		if ( primary == _sentPrimaryBuild && secondary == _sentSecondaryBuild && crosshair == _sentCrosshairSettings )
			return;

		PublishSharing( primary, secondary, crosshair );
		_sentPrimaryBuild = primary;
		_sentSecondaryBuild = secondary;
		_sentCrosshairSettings = crosshair;
	}

	private string ShareHeldGun( EquipmentSlot slot )
	{
		var gun = PlayerPawn.Inventory.Equipment.FirstOrDefault( x => x.IsValid() && x.Enabled
			&& x.Resource.IsValid() && x.Resource.Slot == slot );
		if ( gun.IsValid() )
			return gun.ApplySavedAttachments ? GunsmithLoadoutManager.ExportWeaponBuildCode( gun.Resource )
				: GunsmithLoadoutManager.BuildCode( gun.Resource );

		var legacy = PlayerPawn.GetComponentsInChildren<SWB.Base.Weapon>( true )
			.FirstOrDefault( x => x.Enabled && x.GunsmithResource.IsValid() && x.GunsmithResource.Slot == slot );
		return legacy.IsValid() ? GunsmithLoadoutManager.ExportWeaponBuildCode( legacy.GunsmithResource ) : "";
	}

	[Rpc.Host]
	private void PublishSharing( string primary, string secondary, string crosshair )
	{
		if ( IsBot || Connection is null || Rpc.Caller != Connection || _sinceSharingReceived < .25f )
			return;
		_sinceSharingReceived = 0f;

		if ( !IsSharedGun( primary, EquipmentSlot.Primary ) || !IsSharedGun( secondary, EquipmentSlot.Secondary )
			|| !SharedCrosshair.TryRead( crosshair, out var settings ) )
			return;

		SharedPrimaryBuild = primary ?? "";
		SharedSecondaryBuild = secondary ?? "";
		SharedCrosshairSettings = settings.ToJson();
	}

	/// <summary>
	/// Everyone else draws this player's guns in the build they share (<see cref="Equipment.FitHolderBuild"/>), which can
	/// arrive after a gun is drawn (a new spawn's class, a part changed mid-match), so the guns are fitted again.
	/// </summary>
	private void OnSharedBuildChanged( string before, string after )
	{
		if ( this == Local || !PlayerPawn.IsValid() )
			return;

		foreach ( var equipment in PlayerPawn.GetComponentsInChildren<Equipment>( true ) )
			equipment.RefitHolderBuild();

		PlayerPawn.GetComponentInChildren<EquipmentMountPoints>( true )?.RefitHolderBuilds();
	}

	private static bool IsSharedGun( string code, EquipmentSlot slot ) => string.IsNullOrEmpty( code )
		|| GunsmithLoadoutManager.TryGetSharedBuildWeapon( code, out var resource ) && resource.Slot == slot;
}
