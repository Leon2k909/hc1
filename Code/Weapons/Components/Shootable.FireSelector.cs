namespace Facepunch;

/// <summary>Mechanical selector state carried by the gun, independent of its owner's trigger input.</summary>
public sealed class DroppedFireSelector : Component
{
	[Sync( SyncFlags.FromHost )] public FireMode Mode { get; set; }
}

public partial class Shootable : IDroppedWeaponState
{
	void IDroppedWeaponState.CopyToDroppedWeapon( DroppedEquipment dropped )
	{
		// A passive snapshot: never put a firing action on the dropped object.
		dropped.GetOrAddComponent<DroppedFireSelector>().Mode = CurrentFireMode;
	}

	void IDroppedWeaponState.CopyFromDroppedWeapon( DroppedEquipment dropped )
	{
		if ( dropped.GetComponent<DroppedFireSelector>() is not { } state
			|| !System.Enum.IsDefined( typeof( FireMode ), state.Mode ) ) return;

		CurrentFireMode = state.Mode;
		// The selector persists, but a previous owner's trigger pull or unfinished burst does not.
		_dryFirePullPending = false;
		ClearBurst();
		KeepFireModeFitted();
		Equipment.ViewModel?.OnFireMode( CurrentFireMode );
	}

	/// <summary>
	/// After the fire control group changes: a fire mode the new selector lacks becomes its counterpart (burst for
	/// automatic and back, as the M4's group and the M4A1's differ), else the selector's first.
	/// </summary>
	internal void KeepFireModeFitted()
	{
		var modes = FireModes;
		if ( modes.Count == 0 || modes.Contains( CurrentFireMode ) ) return;
		var counterpart = CurrentFireMode switch
		{
			FireMode.Automatic => FireMode.Burst,
			FireMode.Burst => FireMode.Automatic,
			_ => FireMode.Semi
		};
		CurrentFireMode = modes.Contains( counterpart ) ? counterpart : modes[0];
		ClearBurst();
		Equipment.ViewModel?.OnFireMode( CurrentFireMode );
	}
}
