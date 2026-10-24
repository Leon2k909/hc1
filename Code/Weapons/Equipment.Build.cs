using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Equipment
{
	/// <summary>
	/// Whether this is the local player's own gun, which wears this machine's saved loadout. Anyone else's gun (another
	/// player's, a player-pawn bot's) wears the build its holder shares (<see cref="HolderBuild"/>).
	/// </summary>
	public bool IsOwnBuild => Owner.IsValid() && Owner.Client.IsValid() && Owner.Client == Client.Local;

	/// <summary>
	/// The build this gun's holder has it in, as a build code (<see cref="GunsmithLoadoutManager.ExportWeaponBuildCode"/>):
	/// on their own machine their saved loadout's, and anywhere else the one they last shared for its slot
	/// (<see cref="Client.SharedPrimaryBuild"/>, sent from the gun in their hands each second). Empty for a gun with no
	/// saved parts (Gun Game's, a bot's), a slot builds aren't shared for (knives), or one its holder hasn't shared yet.
	/// </summary>
	public string HolderBuild
	{
		get
		{
			if ( !ApplySavedAttachments || !Resource.IsValid() )
				return "";

			if ( IsOwnBuild )
				return GunsmithLoadoutManager.ExportWeaponBuildCode( Resource );

			var client = Owner.IsValid() ? Owner.Client : null;
			if ( !client.IsValid() || client.IsBot )
				return "";

			var shared = Resource.Slot switch
			{
				EquipmentSlot.Primary => client.SharedPrimaryBuild,
				EquipmentSlot.Secondary => client.SharedSecondaryBuild,
				_ => ""
			};

			return GunsmithLoadoutManager.TryGetSharedBuildWeapon( shared, out var resource )
				&& resource.ResourcePath.Equals( Resource.ResourcePath, StringComparison.OrdinalIgnoreCase ) ? shared : "";
		}
	}

	/// <summary>
	/// Fits the holder's build to <paramref name="root"/>, a copy of this gun (its world model, or its holstered copy):
	/// this machine's saved loadout on the local player's own gun, else <see cref="HolderBuild"/>. Each player's machine
	/// used to fit its own loadout to every gun it drew, so everyone else's guns wore the viewer's parts and camo.
	/// <paramref name="refit"/> fits a copy already fitted, so one with no build to wear goes back to the factory gun.
	/// </summary>
	public void FitHolderBuild( GameObject root, bool refit = false )
	{
		if ( !ApplySavedAttachments || !Resource.IsValid() || !root.IsValid() )
			return;

		if ( IsOwnBuild )
		{
			GunsmithLoadoutManager.ApplyAttachments( Resource, root );
			return;
		}

		var build = HolderBuild;
		if ( build.Length > 0 )
			GunsmithLoadoutManager.ApplyBuild( Resource, root, build );
		else if ( refit )
			GunsmithLoadoutManager.ApplyBuild( Resource, root, GunsmithLoadoutManager.BuildCode( Resource ) );
	}

	/// <summary> Fits the world model again when the holder's shared build changes (<see cref="Client"/>'s OnSharedBuildChanged). </summary>
	public void RefitHolderBuild()
	{
		if ( WorldModel.IsValid() )
			FitHolderBuild( WorldModel.GameObject, refit: true );
	}
}
