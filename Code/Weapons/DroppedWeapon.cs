using Sandbox.Diagnostics;
using Sandbox.Events;

namespace Facepunch;

public record EquipmentDroppedEvent( DroppedEquipment Dropped, PlayerPawn Player ) : IGameEvent;
public record EquipmentPickedUpEvent( PlayerPawn Player, DroppedEquipment Dropped, Equipment Equipment ) : IGameEvent;

public partial class DroppedEquipment : Component, IUse, Component.ICollisionListener, IMarkerObject
{
	[Property] public EquipmentResource Resource { get; set; }
	[Sync( SyncFlags.FromHost )] public bool ApplySavedAttachments { get; set; } = true;

	public Rigidbody Rigidbody { get; private set; }

	/// <summary>
	/// Dropped guns clean themselves up after this long so respawn modes don't fill with weapons.
	/// Special items (the bomb) never expire.
	/// </summary>
	public const float Lifetime = 180f;

	private TimeSince _timeSinceDropped = 0;

	protected override void OnUpdate()
	{
		if ( !Networking.IsHost || Resource is null || Resource.Slot == EquipmentSlot.Special ) return;
		if ( _timeSinceDropped > Lifetime ) GameObject.Destroy();
	}

	/// <summary>
	/// Creates a world instance of a dropped piece of equipment. Takes in a <see cref="EquipmentResource"/>, position, rotation, and optionally a held weapon to inherit data from.
	/// </summary>
	/// <param name="resource"></param>
	/// <param name="positon"></param>
	/// <param name="rotation"></param>
	/// <param name="heldWeapon"></param>
	/// <param name="networkSpawn"></param>
	/// <returns></returns>
	public static DroppedEquipment Create( EquipmentResource resource, Vector3 positon, Rotation? rotation = null, Equipment heldWeapon = null, bool networkSpawn = true )
	{
		Assert.True( Networking.IsHost );

		var go = new GameObject();
		go.Flags |= GameObjectFlags.NotSaved;
		go.WorldPosition = positon;
		go.WorldRotation = rotation ?? Rotation.Identity;
		go.Name = resource.Name;
		go.Tags.Add( "pickup" );

		var wmPrefabFile = resource.MainPrefab.Scene.Source as PrefabFile;
		var worldModel = resource.WorldModel;
		var bounds = worldModel.Bounds;

		var droppedWeapon = go.Components.Create<DroppedEquipment>();
		droppedWeapon.Resource = resource;
		droppedWeapon.ApplySavedAttachments = heldWeapon?.ApplySavedAttachments ?? true;

		var renderer = go.Components.Create<SkinnedModelRenderer>();
		renderer.Model = worldModel;

		renderer.BodyGroups |= resource.WorldModelBodyGroups;

		// Box the model where it is: a gun model isn't centred above its origin.
		var collider = go.Components.Create<BoxCollider>();
		collider.Scale = bounds.Size;
		collider.Center = bounds.Center;

		droppedWeapon.Rigidbody = go.Components.Create<Rigidbody>();

		go.Components.Create<DestroyBetweenRounds>();

		if ( resource.Slot == EquipmentSlot.Special )
		{
			Game.ActiveScene.Dispatch( new BombDroppedEvent() );

			Spottable spottable = go.GetComponent<Spottable>();
			spottable.Team = Team.Terrorist;
		}

		Game.ActiveScene.Dispatch( new EquipmentDroppedEvent( droppedWeapon, heldWeapon?.Owner ) );

		if ( heldWeapon is not null )
		{
			foreach ( var state in heldWeapon.GetComponentsInChildren<IDroppedWeaponState>( true ) )
			{
				state.CopyToDroppedWeapon( droppedWeapon );
			}
		}

		if ( networkSpawn )
		{
			go.NetworkSpawn();
		}

		return droppedWeapon;
	}

	public UseResult CanUse( PlayerPawn player )
	{
		if ( player.Inventory.Has( Resource ) )
			return true;
		if ( player.Inventory.CanTake( Resource ) == PlayerInventory.PickupResult.None ) return "Can't pick this up";
		return true;
	}

	/// <summary>
	/// Rounds left in this dropped weapon (magazine + spare).
	/// </summary>
	public int RoundsLeft => GetComponent<WeaponAmmo>() is { } a ? a.Ammo + a.ReserveAmmo : 0;

	/// <summary>
	/// The player's weapon that could use this gun's ammo: the same weapon, or one of the same category
	/// (rifles share rifle rounds, pistols share pistol rounds…). Null if none, or it's already full.
	/// </summary>
	public WeaponAmmo FindScavengeTarget( PlayerPawn player )
	{
		if ( !player.IsValid() || RoundsLeft <= 0 ) return null;

		var candidates = player.Inventory.Equipment
			.Where( x => x.IsValid() && x.Resource is not null )
			.Where( x => x.Resource == Resource
				|| ( x.Resource.Category == Resource.Category && x.Resource.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary ) )
			.OrderByDescending( x => x.Resource == Resource );

		foreach ( var equipment in candidates )
		{
			var ammo = equipment.GetComponentInChildren<WeaponAmmo>( true );
			if ( ammo.IsValid() && ammo.ReserveAmmo < ammo.GetMaxReserve() ) return ammo;
		}
		return null;
	}

	/// <summary>
	/// Take spare rounds on contact while leaving the dropped gun available for an explicit pickup.
	/// </summary>
	private bool TryScavenge( PlayerPawn player )
	{
		var target = FindScavengeTarget( player );
		if ( !target.IsValid() ) return false;

		var source = GetComponent<WeaponAmmo>();
		var room = target.GetMaxReserve() - target.ReserveAmmo;
		// Leave at least one magazine round in the gun so Use can still pick up a usable weapon.
		var taken = Math.Min( room, source.ReserveAmmo + Math.Max( 0, source.Ammo - 1 ) );
		if ( taken <= 0 ) return false;

		// Empty the spare ammo first, then the magazine.
		var fromReserve = Math.Min( taken, source.ReserveAmmo );
		source.ReserveAmmo -= fromReserve;
		source.Ammo -= taken - fromReserve;

		target.ReceiveReserve( taken );

		return true;
	}

	private bool _isUsed;

	public void OnUse( PlayerPawn player )
	{
		if ( _isUsed ) return;
		_isUsed = true;

		if ( !player.IsValid() )
		{
			_isUsed = false;
			return;
		}

		// Contact scavenges ammo; Use explicitly swaps for the physical gun.
		if ( player.Inventory.Has( Resource ) )
		{
			var carried = player.Inventory.Equipment.FirstOrDefault( x => x.IsValid() && x.Resource == Resource );
			if ( carried.IsValid() )
			{
				DroppedEquipment.Create( carried.Resource, player.WorldPosition + Vector3.Up * 32f, Rotation.Identity, carried );
				player.Inventory.RemoveWeapon( carried );
			}
		}

		var currentActiveSlot = player.CurrentEquipment?.Resource.Slot ?? EquipmentSlot.Melee;
		var weapon = player.Inventory.Give( Resource, Resource.Slot < currentActiveSlot, ApplySavedAttachments, this );

		if ( !weapon.IsValid() )
		{
			_isUsed = false;
			return;
		}

		Game.ActiveScene.Dispatch( new EquipmentPickedUpEvent( player, this, weapon ) );

		GameObject.Destroy();
	}

	void ICollisionListener.OnCollisionStart( Collision collision )
	{
		if ( !Networking.IsHost ) return;

		// Conna: this is longer than Daenerys Targaryen's full title.
		if ( collision.Other.GameObject.Root.GetComponentInChildren<PlayerPawn>() is { } player )
		{
			// Don't pickup weapons if we're dead.
			if ( player.HealthComponent.State != LifeState.Alive )
				return;

			// If we last respawned less than 2 seconds ago then don't pickup. This is because
			// we need to give a chance for the owner to update its position. I want to add a way
			// to specify that Transform can be changed on non-owner too (prediction.)
			if ( player.TimeSinceLastRespawn < 2f )
				return;

			// Walking over a gun that takes the same ammo as ours strips its rounds, CoD-style.
			if ( TryScavenge( player ) )
				return;

			if ( player.Inventory.CanTake( Resource ) != PlayerInventory.PickupResult.Pickup )
				return;

			// Don't auto-pickup if we already have a weapon in this slot.
			if ( player.Inventory.HasInSlot( Resource.Slot ) )
				return;

			OnUse( player );
		}
	}

	/// <summary>The middle of the gun's model in the world, which E aims for (see PlayerPawn.PickupReach).</summary>
	public Vector3 Center => WorldTransform.PointToWorld( Resource?.WorldModel?.Bounds.Center ?? Vector3.Zero );

	/// <summary>
	/// Where is the marker?
	/// </summary>
	Vector3 IMarkerObject.MarkerPosition => Center + Vector3.Up * 8f;

	/// <summary>
	/// What text?
	/// </summary>
	string IMarkerObject.DisplayText => $"{Resource.Name}";

	/// <summary>The prompt only shows where E reaches the gun (the marker sits 8 above its middle).</summary>
	float IMarkerObject.MarkerMaxDistance => PlayerPawn.PickupReach - 8f;

	string IMarkerObject.InputHint => "Use";

	bool IMarkerObject.LookOpacity => false;
}
