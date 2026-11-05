using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	checks++;
	if ( !condition ) throw new Exception( message );
}

foreach ( var mode in Enum.GetValues<FireMode>() )
{
	var original = new Shootable { CurrentFireMode = mode };
	var dropped = new DroppedEquipment();
	((IDroppedWeaponState)original).CopyToDroppedWeapon( dropped );
	Check( dropped.GetComponent<DroppedFireSelector>().Mode == mode, "Selector snapshot" );
	Check( dropped.ComponentCount == 1, "Only a passive snapshot is added" );
	var pickup = new Shootable { PendingPull = true, IsBurstFiring = true, BurstCount = 2 };
	((IDroppedWeaponState)pickup).CopyFromDroppedWeapon( dropped );
	Check( pickup.CurrentFireMode == mode, "Round-trip selector" );
	Check( !pickup.PendingPull && !pickup.IsBurstFiring && pickup.BurstCount == 0, "No carried trigger or burst" );
	Check( pickup.Equipment.ViewModel.Mode == mode, "Viewmodel selector matches" );
	var redropped = new DroppedEquipment();
	((IDroppedWeaponState)pickup).CopyToDroppedWeapon( redropped );
	Check( redropped.GetComponent<DroppedFireSelector>().Mode == mode, "Repeated transfer" );
	// The next drop overwrites any snapshot, rather than keeping an old selector setting.
	original.CurrentFireMode = mode == FireMode.Semi ? FireMode.Automatic : FireMode.Semi;
	((IDroppedWeaponState)original).CopyToDroppedWeapon( dropped );
	Check( dropped.GetComponent<DroppedFireSelector>().Mode == original.CurrentFireMode, "Snapshot refreshed" );
}

foreach ( var (saved, supported, expected) in new[]
{
	(FireMode.Automatic, new[] { FireMode.Semi, FireMode.Burst }, FireMode.Burst),
	(FireMode.Burst, new[] { FireMode.Semi, FireMode.Automatic }, FireMode.Automatic),
	(FireMode.Automatic, new[] { FireMode.Semi }, FireMode.Semi),
	(FireMode.Burst, new[] { FireMode.Semi }, FireMode.Semi),
	(FireMode.Semi, new[] { FireMode.Automatic }, FireMode.Automatic)
} )
{
	var dropped = new DroppedEquipment();
	dropped.GetOrAddComponent<DroppedFireSelector>().Mode = saved;
	var pickup = new Shootable { FireModes = supported };
	((IDroppedWeaponState)pickup).CopyFromDroppedWeapon( dropped );
	Check( pickup.CurrentFireMode == expected, "Compatible fitted selector" );
	Check( pickup.Equipment.ViewModel.Mode == expected, "Compatible viewmodel" );
}

foreach ( var missing in new[] { true, false } )
{
	var dropped = new DroppedEquipment();
	if ( !missing ) dropped.GetOrAddComponent<DroppedFireSelector>().Mode = (FireMode)999;
	var pickup = new Shootable { CurrentFireMode = FireMode.Semi };
	((IDroppedWeaponState)pickup).CopyFromDroppedWeapon( dropped );
	Check( pickup.CurrentFireMode == FireMode.Semi, "Missing or corrupt snapshot keeps prefab default" );
}
Console.WriteLine( $"Passed {checks} fire selector checks." );

namespace Facepunch
{
	public enum FireMode { Semi, Automatic, Burst }
	public class Component;
	public enum SyncFlags { FromHost }
	[AttributeUsage( AttributeTargets.Property )]
	public sealed class SyncAttribute( SyncFlags flags ) : Attribute
	{
		public SyncFlags Flags { get; } = flags;
	}
	public interface IDroppedWeaponState
	{
		void CopyToDroppedWeapon( DroppedEquipment dropped );
		void CopyFromDroppedWeapon( DroppedEquipment dropped );
	}
	public class DroppedEquipment
	{
		private readonly Dictionary<Type, Component> components = new();
		public int ComponentCount => components.Count;
		public T GetComponent<T>() where T : Component => components.GetValueOrDefault( typeof(T) ) as T;
		public T GetOrAddComponent<T>() where T : Component, new()
		{
			if ( GetComponent<T>() is { } current ) return current;
			var added = new T();
			components.Add( typeof(T), added );
			return added;
		}
	}
	public class ViewModel
	{
		public FireMode Mode { get; private set; }
		public void OnFireMode( FireMode mode ) => Mode = mode;
	}
	public class Equipment
	{
		public ViewModel ViewModel { get; } = new();
	}
	public partial class Shootable
	{
		public FireMode CurrentFireMode { get; set; } = FireMode.Automatic;
		public IReadOnlyList<FireMode> FireModes { get; set; } = Enum.GetValues<FireMode>();
		public Equipment Equipment { get; } = new();
		private bool _dryFirePullPending;
		public bool PendingPull { get => _dryFirePullPending; set => _dryFirePullPending = value; }
		public bool IsBurstFiring { get; set; }
		public int BurstCount { get; set; }
		private void ClearBurst() { IsBurstFiring = false; BurstCount = 0; }
	}
}
