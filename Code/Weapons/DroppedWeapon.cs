using Sandbox.Diagnostics;
using Sandbox.Events;

namespace Facepunch;

public record EquipmentDroppedEvent( DroppedEquipment Dropped, PlayerPawn Player ) : IGameEvent;
public record EquipmentPickedUpEvent( PlayerPawn Player, DroppedEquipment Dropped, Equipment Equipment ) : IGameEvent;

public partial class DroppedEquipment : Component, IUse, Component.ICollisionListener, IMarkerObject
{
	[Property] public EquipmentResource Resource { get; set; }
	[Sync( SyncFlags.FromHost )] public bool ApplySavedAttachments { get; set; } = true;

	/// <summary>
	/// The build the gun is drawn with on the floor, on every machine, as a build code
	/// (<see cref="Gunsmith.GunsmithLoadoutManager.ExportWeaponBuildCode"/>): its parts, camo and reticle as its holder
	/// had them. Empty for the factory gun.
	/// </summary>
	[Sync( SyncFlags.FromHost )] public string Build { get; set; } = "";

	public Rigidbody Rigidbody { get; private set; }

	/// <summary>
	/// Dropped guns clean themselves up after this long so respawn modes don't fill with weapons.
	/// Special items (the bomb) never expire.
	/// </summary>
	public const float Lifetime = 180f;

	private TimeSince _timeSinceDropped = 0;

	protected override void OnUpdate()
	{
		UpdateModel();

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

		var bounds = FloorBounds( resource );

		var droppedWeapon = go.Components.Create<DroppedEquipment>();
		droppedWeapon.Resource = resource;
		droppedWeapon.ApplySavedAttachments = heldWeapon?.ApplySavedAttachments ?? true;
		droppedWeapon.Build = heldWeapon.IsValid() ? heldWeapon.HolderBuild : "";

		// A gun is drawn from its world model prefab, as in someone's hands, by each machine (UpdateModel). Only things
		// with no prefab (the cash bag, the drone) are the bare model.
		if ( resource.WorldModelPrefab is null )
		{
			var renderer = go.Components.Create<SkinnedModelRenderer>();
			renderer.Model = resource.WorldModel;
			renderer.BodyGroups |= resource.WorldModelBodyGroups;
		}

		// Fit the model where it is: a gun model isn't centred above its origin. Guns and knives get a ridged hull
		// (see RidgedProfile); grenades, the bomb and the like keep a box.
		var profile = resource.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary or EquipmentSlot.Melee
			? RidgedProfile( bounds.Size * 0.5f, Game.Random.Float( 0f, 1f ) < 0.5f ? 1f : -1f )
			: null;

		if ( profile is null )
		{
			var collider = go.Components.Create<BoxCollider>();
			collider.Scale = bounds.Size;
			collider.Center = bounds.Center;
		}
		else
		{
			var centre = bounds.Center;
			var halfLength = bounds.Size.x * 0.5f;
			var hull = go.Components.Create<HullCollider>( false );
			hull.Points = profile
				.SelectMany( p => new[]
				{
					new Vector3( centre.x - halfLength, centre.y + p.x, centre.z + p.y ),
					new Vector3( centre.x + halfLength, centre.y + p.x, centre.z + p.y )
				} )
				.ToList();
			hull.Center = Vector3.Zero;
			hull.Type = HullCollider.PrimitiveType.Points;
			hull.Enabled = true;
		}

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

	/// <summary>
	/// The bounds of the model the gun is drawn with on the floor (its world model prefab's renderer, which may sit off
	/// the prefab's root: the 1911's does), in the dropped object's space.
	/// </summary>
	private static BBox FloorBounds( EquipmentResource resource )
	{
		var prefab = resource.WorldModelPrefab;
		var renderer = prefab?.GetComponentInChildren<SkinnedModelRenderer>( true );
		if ( renderer?.Model is { } model )
			return model.Bounds.Transform( prefab.WorldTransform.ToLocal( renderer.WorldTransform ) );

		return resource.WorldModel?.Bounds ?? default;
	}

	private BBox? _bounds;
	private GameObject _model;
	private string _modelBuild;

	/// <summary>
	/// Draws the gun as it was held: its world model prefab with <see cref="Build"/> fitted, as Equipment.CreateWorldModel
	/// fits a gun in someone's hands, but from the build rather than this machine's own loadout. Each machine makes its
	/// own copy, which isn't networked, and makes it again if the build changes.
	/// </summary>
	private void UpdateModel()
	{
		var build = Build ?? "";
		if ( _modelBuild == build || Application.IsDedicatedServer || Resource?.WorldModelPrefab is not { } prefab )
			return;

		_modelBuild = build;
		_model?.Destroy();

		// A gun dropped before guns were drawn this way has its bare model on the root.
		if ( GetComponent<SkinnedModelRenderer>() is { } bare )
			bare.Enabled = false;

		_model = prefab.Clone( new CloneConfig { Name = "Model", Transform = new Transform(), Parent = GameObject, StartEnabled = false } );
		if ( !_model.IsValid() )
			return;

		_model.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		if ( _model.Components.TryGet<SkinnedModelRenderer>( out var renderer, FindMode.EverythingInSelfAndDescendants ) )
		{
			renderer.SetBodyGroup( "sight", 0 );
			renderer.SetBodyGroup( "muzzle", 0 );
		}

		if ( build.Length > 0 )
			Gunsmith.GunsmithLoadoutManager.ApplyBuild( Resource, _model, build );

		_model.Enabled = true;
	}

	/// <summary>How far off the middle the ridges sit, as a share of the half-width, so a gun dropped dead level still falls one way.</summary>
	private const float RidgeSkew = 0.2f;

	/// <summary>Facets on each slope from a side down to a ridge.</summary>
	private const int RidgeFacets = 4;

	/// <summary>
	/// A box the model's size let a dropped gun come to rest standing up, balanced on the box's narrow bottom (the
	/// user saw an AK-74M do it, 2026-10-14). A real gun can't stand: its magazine, grip and stock meet the ground at a
	/// few rounded points under a centre of mass inches up, so it falls onto a side. This is the gun's cross-section
	/// (y across, z up, from the middle of its bounds) with the box's sides kept for its middle half and a ridge
	/// along its bottom and its top, so the sides are the only faces it can rest on. Null where no such shape fits.
	/// </summary>
	private static List<Vector2> RidgedProfile( Vector3 half, float side )
	{
		if ( half.x <= 0f || half.y <= 0f || half.z <= half.y )
			return null;

		var ridge = new Vector2( side * RidgeSkew * half.y, -half.z );

		// A slope's far end has to be further from the middle than its near end, so its corners stay inside a circle
		// through the ridge.
		var shoulder = MathF.Min( half.z * 0.5f, 0.85f * MathF.Sqrt( half.z * half.z - half.y * half.y ) );

		var right = Slope( new Vector2( half.y, -shoulder ), ridge );
		var left = Slope( new Vector2( -half.y, -shoulder ), ridge );

		// Each facet of a slope has to tip the gun back towards the side it came from.
		var minTip = 0.05f * half.z;
		if ( !TipsBack( right, minTip ) || !TipsBack( left, minTip ) )
			return null;

		// The top is the bottom turned about the middle, which keeps the centre of mass there.
		var bottom = right.Concat( left.Take( RidgeFacets ) ).ToList();
		return bottom.Concat( bottom.Select( p => -p ) ).ToList();
	}

	/// <summary>
	/// Points from a side's corner to the ridge on a logarithmic spiral round the middle: each one further out than the
	/// last by enough that, with a facet underneath, the centre of mass hangs past its end nearer the side.
	/// </summary>
	private static Vector2[] Slope( Vector2 from, Vector2 to )
	{
		// Angles from straight down, towards +y.
		var angleFrom = MathF.Atan2( from.x, -from.y );
		var angleTo = MathF.Atan2( to.x, -to.y );
		var points = new Vector2[RidgeFacets + 1];

		for ( var i = 0; i <= RidgeFacets; i++ )
		{
			var f = (float)i / RidgeFacets;
			var angle = angleFrom + (angleTo - angleFrom) * f;
			var radius = from.Length * MathF.Pow( to.Length / from.Length, f );
			points[i] = new Vector2( radius * MathF.Sin( angle ), -radius * MathF.Cos( angle ) );
		}

		points[0] = from;
		points[RidgeFacets] = to;
		return points;
	}

	/// <summary>
	/// Whether, with each facet underneath, the centre of mass (the middle) hangs at least <paramref name="minTip"/>
	/// past the facet's end nearer the side, so the gun rolls back off it.
	/// </summary>
	private static bool TipsBack( Vector2[] slope, float minTip )
	{
		for ( var i = 0; i < slope.Length - 1; i++ )
		{
			if ( Vector2.Dot( slope[i], (slope[i + 1] - slope[i]).Normal ) < minTip )
				return false;
		}

		return true;
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
	public Vector3 Center => WorldTransform.PointToWorld( Resource is null ? Vector3.Zero : (_bounds ??= FloorBounds( Resource )).Center );

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
