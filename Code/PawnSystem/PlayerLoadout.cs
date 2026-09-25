using Facepunch.Gunsmith;

namespace Facepunch;

public partial class PlayerLoadout : Component
{
	[Property] public Client Client { get; set; }

	/// <summary>
	/// The equipment of the class this player picked (host only), given to them each time they spawn.
	/// </summary>
	[Property] public List<EquipmentResource> Equipment { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public bool HasDefuseKit { get; set; }

	/// <summary>
	/// How long after spawning picking a class still swaps what the player is holding, as in CoD. Later picks wait
	/// for the next spawn. Spawn protection counts too.
	/// </summary>
	public const float ClassSwapWindow = 5f;

	/// <summary>
	/// Are classes used in this game mode (e.g. not in Gun Game)?
	/// </summary>
	public static bool ClassesEnabled => GameMode.Instance?.Get<DefaultEquipment>() is { LoadoutsEnabled: true };

	private string _sentClass;
	private TimeSince _sinceClassCheck = 1f;

	// Whether the player has picked a class in this match yet: the first pick after joining always swaps straight
	// away, like choosing a class before deploying in CoD. The owner (for the UI) and the host (which decides) each
	// keep their own, since the host's own player is both.
	private bool _ownerPicked;
	private bool _hostPicked;

	private Client Owner => Components.Get<Client>();

	private bool CanSwapNow( bool firstPick )
	{
		var pawn = Owner?.PlayerPawn;
		if ( !ClassesEnabled || !pawn.IsValid() || !pawn.HealthComponent.IsValid() || pawn.HealthComponent.State != LifeState.Alive )
			return false;

		return firstPick || pawn.HealthComponent.IsGodMode || pawn.TimeSinceLastRespawn < ClassSwapWindow;
	}

	protected override void OnUpdate()
	{
		// Owner side: keep the host's copy of our class in step with our saved classes, e.g. after gunsmith edits.
		if ( IsProxy || _sinceClassCheck < 1f || Owner is not { IsLocalPlayer: true } )
			return;

		_sinceClassCheck = 0f;
		SendActiveClass( false );
	}

	/// <summary>
	/// Owner side: tell the host to spawn us with the active gunsmith class. <paramref name="picked"/> is a class
	/// chosen in the class menu: it's sent even if its weapons haven't changed (a class with the same guns still
	/// swaps attachments). Returns whether the player's equipment is swapped straight away.
	/// </summary>
	public bool SendActiveClass( bool picked )
	{
		var paths = GunsmithLoadoutManager.GetLoadoutResources().Select( x => x.ResourcePath ).ToArray();
		var key = string.Join( ",", paths );
		if ( !picked && key == _sentClass )
			return false;

		var swapNow = CanSwapNow( picked && !_ownerPicked );
		_ownerPicked |= picked;
		_sentClass = key;

		SelectClass( paths, picked );
		return swapNow;
	}

	[Rpc.Host]
	private void SelectClass( string[] resourcePaths, bool picked )
	{
		var client = Owner;
		if ( !client.IsValid() || Rpc.Caller != client.Connection )
			return;

		Equipment = resourcePaths
			.Select( x => ResourceLibrary.Get<EquipmentResource>( x ) )
			.Where( x => x.IsValid() && GunsmithLoadoutManager.ClassSlots.Contains( x.Slot ) )
			.ToList();

		var swapNow = CanSwapNow( picked && !_hostPicked );
		_hostPicked |= picked;

		if ( swapNow )
			GiveClass( client.PlayerPawn );
	}

	private void GiveClass( PlayerPawn pawn )
	{
		var inventory = pawn.Inventory;
		foreach ( var held in inventory.Equipment.Where( x => GunsmithLoadoutManager.ClassSlots.Contains( x.Resource.Slot ) ).ToList() )
			inventory.RemoveWeapon( held );

		foreach ( var resource in Equipment )
			inventory.Give( resource, false );

		// The mode's own loadout fills any slot the class leaves empty, as on spawn (DefaultEquipment).
		if ( GameMode.Instance?.Get<DefaultEquipment>()?.GetLoadout( pawn.Team ) is { } defaults )
		{
			foreach ( var resource in defaults.Equipment.Where( x => !inventory.HasInSlot( x.Slot ) ) )
				inventory.Give( resource, false );
		}

		inventory.SwitchToBest();
		inventory.RefillAmmo();
	}
}
