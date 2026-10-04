using Facepunch;
using Sandbox.Events;

[Icon( "yard" )]
[Title( "Bomb Planting" ), Group( "Weapon Components" )]
public partial class DefuseC4 : WeaponInputAction, IGameEventHandler<EquipmentHolsteredEvent>
{
	[Property, Category( "Config" )] public float PlantTime { get; set; } = 4f;
	[Property, Category( "Config" )] public GameObject PlantedObjectPrefab { get; set; }
	[Property, Category( "Effects" )] public SoundEvent PlantingBeepSound { get; set; }
	[Property, Category( "Effects" )] public Curve PlantingBeepFrequency { get; set; } = new( new Curve.Frame( 0f, 0.7f ), new Curve.Frame( 1f, 0.2f ) );
	[Sync( SyncFlags.FromHost )] public bool IsPlanting { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSincePlantStart { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSincePlantCancel { get; private set; }
	public float Progress => IsPlanting ? Math.Clamp( TimeSincePlantStart / Math.Max( PlantTime, 0.1f ), 0f, 1f ) : 0f;
	private TimeSince TimeSinceBeep;
	private PlayerPawn planter;
	private Vector3 plantOrigin;
	private BombSite CurrentBombSite => Equipment.IsValid() && Equipment.Owner.IsValid() ? Equipment.Owner.GetZone<BombSite>() : null;

	protected override void OnEnabled() => BindTag( "planting", () => IsPlanting );

	public bool CanPlant()
	{
		var player = Equipment?.Owner;
		return Equipment.IsValid() && Equipment.IsDeployed && player.IsValid()
			&& player.Team == Team.Terrorist && player.HealthComponent.State == LifeState.Alive
			&& player.IsGrounded && CurrentBombSite is { Active: true }
			&& GameMode.Instance?.Get<BombPlantedEventComponent>() is { Active: true }
			&& !Scene.GetAllComponents<TimedExplosive>().Any( x => x.Active && !x.IsDefused );
	}

	private bool AuthorizedCaller() => Rpc.Caller is null || Rpc.Caller == Connection.Host || Rpc.Caller == Equipment?.Owner?.Client?.Connection;

	[Rpc.Host]
	internal void StartPlant()
	{
		if ( !AuthorizedCaller() || IsPlanting || !CanPlant() || Equipment.Owner.IsFrozen ) return;
		planter = Equipment.Owner;
		plantOrigin = planter.WorldPosition;
		TimeSincePlantStart = 0f;
		IsPlanting = true;
		planter.IsFrozen = true;
		SetPlantAnimation( planter, true );
		RadioSounds.Play( planter.Team, "Hidden", "Planting bomb" );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void SetPlantAnimation( PlayerPawn player, bool planting )
	{
		if ( player.IsValid() && player.BodyRenderer.IsValid() ) player.BodyRenderer.SetBool( "b_planting_bomb", planting );
	}

	/// <summary>Only the host completes a plant. Retakes can pre-place its bomb before the round starts.</summary>
	public void FinishPlant( Vector3? position = null, bool ignorePlanter = false )
	{
		if ( !Networking.IsHost || !Equipment.IsValid() || !PlantedObjectPrefab.IsValid() ) return;
		var player = Equipment.Owner;
		if ( !player.IsValid() || (!ignorePlanter && (!IsPlanting || !CanPlant() || TimeSincePlantStart < PlantTime)) ) return;
		if ( Scene.GetAllComponents<TimedExplosive>().Any( x => x.Active && !x.IsDefused ) ) return;

		var location = position ?? player.WorldPosition;
		var site = ignorePlanter ? Zone.GetAt( location ).Select( x => x.GetComponent<BombSite>() ).FirstOrDefault( x => x.IsValid() ) : CurrentBombSite;
		if ( !site.IsValid() ) return;
		var ground = Scene.Trace.Ray( location + Vector3.Up * 8, location - Vector3.Up * 32 )
			.IgnoreGameObjectHierarchy( player.GameObject ).WithoutTags( "player", "trigger", "pickup" ).Run();
		if ( ground.Hit ) location = ground.EndPosition;
		var planted = PlantedObjectPrefab.Clone( location, Rotation.FromYaw( player.WorldRotation.Yaw() ) );
		if ( !planted.IsValid() ) return;
		planted.GetComponent<TimedExplosive>()?.InitializeSite( site );
		planted.Network.SetOrphanedMode( NetworkOrphaned.ClearOwner );
		planted.NetworkSpawn();

		CancelPlantOnHost();
		// Capture the site and create the objective before destroying the carried equipment.
		var scene = Scene;
		player.Inventory.RemoveWeapon( Equipment );
		scene.Dispatch( new BombPlantedEvent( ignorePlanter ? null : player, planted, site ) );
	}

	[Rpc.Host]
	internal void CancelPlant()
	{
		if ( AuthorizedCaller() ) CancelPlantOnHost();
	}

	private void CancelPlantOnHost()
	{
		if ( !Networking.IsHost || !IsPlanting ) return;
		IsPlanting = false;
		TimeSincePlantCancel = 0f;
		if ( planter.IsValid() )
		{
			// A round transition may already have frozen everyone for the next round.
			planter.IsFrozen = GameMode.Instance?.Get<FreezePlayers>() is { Active: true };
			SetPlantAnimation( planter, false );
		}
		planter = null;
	}

	protected override void OnFixedUpdate()
	{
		// Process release before checking the completion time.
		base.OnFixedUpdate();
		if ( !Networking.IsHost || !IsPlanting ) return;
		if ( !CanPlant() || !planter.IsValid() || planter.WorldPosition.Distance( plantOrigin ) > 12f ) CancelPlantOnHost();
		else if ( TimeSincePlantStart >= PlantTime ) FinishPlant();
	}

	protected override void OnInputDown() { if ( CanPlant() ) StartPlant(); }
	protected override void OnInputUp() => CancelPlant();
	protected override void OnDisabled() => CancelPlantOnHost();
	protected override void OnDestroy() => CancelPlantOnHost();

	protected override void OnUpdate()
	{
		if ( !IsPlanting ) { TimeSinceBeep = 0f; return; }
		if ( TimeSinceBeep > PlantingBeepFrequency.Evaluate( Progress ) )
		{
			TimeSinceBeep = 0f;
			if ( PlantingBeepSound is not null ) Sound.Play( PlantingBeepSound, WorldPosition );
		}
	}

	void IGameEventHandler<EquipmentHolsteredEvent>.OnGameEvent( EquipmentHolsteredEvent e )
	{
		if ( e.Equipment == Equipment ) CancelPlantOnHost();
	}
}
