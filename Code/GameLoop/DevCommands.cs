namespace Facepunch;

public static class DevCommands
{
	/// <summary>Hold ADS without input, for testing optics through the editor bridge.</summary>
	[ConVar( "dev_force_aim", Saved = false )] public static bool ForceAim { get; set; }

	/// <summary>Nobody takes damage, so bots can't interrupt testing.</summary>
	[ConVar( "dev_no_damage", Saved = false )] public static bool NoDamage { get; set; }

	/// <summary>Jump straight from the menu into a match, e.g. for automated testing through the editor bridge.</summary>
	[ConCmd( "dev_quickplay" )]
	public static void QuickPlay( string mapContains = "tdm" )
	{
		var maps = GameUtils.GetAvailableMaps().ToList();
		var map = maps.FirstOrDefault( m => m.ResourcePath.Contains( mapContains, StringComparison.OrdinalIgnoreCase ) ) ?? maps.FirstOrDefault();
		var mode = map is null ? null : GameMode.GetAll( map ).FirstOrDefault();
		if ( mode is null ) { Log.Warning( "dev_quickplay: no map/mode found" ); return; }

		GameMode.SetCurrent( mode );
		Game.ActiveScene.Load( map );
	}

	/// <summary>Start the zombies mode the same way the hub's Zombies button does.</summary>
	[ConCmd( "dev_zombies" )]
	public static void Zombies()
	{
		var mode = GameObject.GetPrefab( "prefabs/game_modes/zombies.prefab" )?.GetComponent<GameMode>();
		if ( !mode.IsValid() ) { Log.Warning( "dev_zombies: no zombies mode prefab" ); return; }

		var scene = ResourceLibrary.GetAll<SceneFile>()
			.FirstOrDefault( s => s.ResourcePath?.Contains( "flatgrass", StringComparison.OrdinalIgnoreCase ) ?? false )
			?? GameUtils.GetAvailableMaps().FirstOrDefault();
		if ( scene is null ) { Log.Warning( "dev_zombies: no map" ); return; }

		GameMode.SetCurrent( mode );
		GameMode.SetHardcore( false );
		Game.ActiveScene.Load( scene );
	}

	/// <summary>Zombies: give the local player points.</summary>
	[ConCmd( "dev_points" )]
	public static void Points( int amount = 10000 )
	{
		Client.Local?.PlayerPawn?.GetComponent<ZombiesPlayerEconomy>()?.AddPoints( amount );
	}

	/// <summary>Zombies: hurt the local player (100 = downs you without Juggernog).</summary>
	[ConCmd( "dev_hurt" )]
	public static void Hurt( float amount = 100f )
	{
		var pawn = Client.Local?.PlayerPawn;
		pawn?.HealthComponent?.TakeDamage( new DamageInfo( pawn, amount ) );
	}

	/// <summary>Zombies: log round / player state, for checking things through the editor bridge.</summary>
	[ConCmd( "dev_zombies_info" )]
	public static void ZombiesInfo()
	{
		var rs = ZombiesRoundSystem.Current;
		var pawn = Client.Local?.PlayerPawn;
		var state = pawn?.GetComponent<ZombiesPlayerState>();
		Log.Info( $"dev_zombies_info: round={rs?.CurrentRound} intermission={rs?.IsIntermission} remaining={rs?.ZombiesRemainingInRound} alive={rs?.ZombiesAlive} gameOver={rs?.IsGameOver} " +
			$"zombies={Game.ActiveScene.GetAllComponents<ZombieAI>().Count()} stations={Game.ActiveScene.GetAllComponents<ZombiesBuyStation>().Count()} " +
			$"points={pawn?.GetComponent<ZombiesPlayerEconomy>()?.Points} hp={pawn?.HealthComponent?.Health}/{pawn?.HealthComponent?.MaxHealth} life={pawn?.HealthComponent?.State} " +
			$"downed={state?.IsDowned} perks={state?.Perks} prone={pawn?.IsProne} pos={pawn?.WorldPosition}" );
		Log.Info( $"dev_zombies_info: navmesh enabled={Game.ActiveScene.NavMesh.IsEnabled} generating={Game.ActiveScene.NavMesh.IsGenerating}" );
		foreach ( var z in Game.ActiveScene.GetAllComponents<ZombieAI>().Take( 8 ) )
		{
			var agent = z.GetComponent<NavMeshAgent>( true );
			Log.Info( $"dev_zombies_info:   components: {string.Join( ", ", z.Components.GetAll().Select( c => $"{c.GetType().Name}{(c.Enabled ? "" : "(off)")}" ) )} proxy={z.IsProxy} owner={z.Network.Owner?.DisplayName}" );
			Log.Info( $"dev_zombies_info:   zombie {z.Speed} hp={z.Health}/{z.MaxHealth} pos={z.WorldPosition} dist={(pawn.IsValid() ? z.WorldPosition.Distance( pawn.WorldPosition ) : 0):F0} " +
				$"agent={agent?.Enabled} vel={agent?.Velocity.Length:F0} target={agent?.TargetPosition} navPoint={Game.ActiveScene.NavMesh.GetClosestPoint( z.WorldPosition, 64f )}" );
		}
	}

	/// <summary>Zombies: kill every zombie (like the Nuke power-up, no points).</summary>
	[ConCmd( "dev_nuke" )]
	public static void Nuke()
	{
		foreach ( var z in Game.ActiveScene.GetAllComponents<ZombieAI>().ToList() )
			z.Kill( null );
	}

	/// <summary>Zombies: use the nearest buy station of a kind (perk name, "box", or "wall").</summary>
	[ConCmd( "dev_buy" )]
	public static void Buy( string what )
	{
		var pawn = Client.Local?.PlayerPawn;
		if ( pawn is null ) return;

		var station = Game.ActiveScene.GetAllComponents<ZombiesBuyStation>()
			.Where( s => what.Equals( "box", StringComparison.OrdinalIgnoreCase ) ? s.Kind == ZombiesBuyKind.MysteryBox
				: what.Equals( "wall", StringComparison.OrdinalIgnoreCase ) ? s.Kind == ZombiesBuyKind.WallWeapon
				: s.Kind == ZombiesBuyKind.Perk && s.Perk.ToString().Equals( what, StringComparison.OrdinalIgnoreCase ) )
			.OrderBy( s => s.WorldPosition.Distance( pawn.WorldPosition ) )
			.FirstOrDefault();
		if ( station is null ) { Log.Warning( $"dev_buy: no station for {what}" ); return; }

		IUse use = station;
		var result = use.CanUse( pawn );
		Log.Info( $"dev_buy: {station.Title} canUse={result.CanUse} reason={result.Reason}" );
		if ( result.CanUse ) use.OnUse( pawn );
	}

	/// <summary>Empty and reload the local player's current weapon, for testing reload visuals through the editor bridge.</summary>
	[ConCmd( "dev_reload" )]
	public static void Reload()
	{
		var equipment = Client.Local?.PlayerPawn?.CurrentEquipment;
		var reloadable = equipment?.GetComponentInChildren<Reloadable>( true );
		var ammo = equipment?.GetComponentInChildren<WeaponAmmo>( true );
		if ( !reloadable.IsValid() ) { Log.Warning( "dev_reload: no reloadable weapon" ); return; }

		if ( ammo.IsValid() ) ammo.Ammo = 0;
		reloadable.StartReload();
	}

	/// <summary>Switch the local player to their primary weapon.</summary>
	[ConCmd( "dev_primary" )]
	public static void Primary()
	{
		Client.Local?.PlayerPawn?.Inventory?.SwitchToSlot( EquipmentSlot.Primary );
	}

	/// <summary>Give the local player a weapon by resource name (e.g. dev_give m4a1) and equip it.</summary>
	[ConCmd( "dev_give" )]
	public static void Give( string name )
	{
		var resource = ResourceLibrary.GetAll<EquipmentResource>().FirstOrDefault( r => r.ResourceName.Equals( name, StringComparison.OrdinalIgnoreCase ) );
		if ( resource is null ) { Log.Warning( $"dev_give: no equipment named {name}" ); return; }
		Client.Local?.PlayerPawn?.Inventory?.Give( resource, true );
	}

	/// <summary>Log how the current weapon's ADS offset is being resolved.</summary>
	[ConCmd( "dev_aim_info" )]
	public static void AimInfo()
	{
		var pawn = Client.Local?.PlayerPawn;
		Log.Info( $"dev_aim_info: inventory = {string.Join( ", ", pawn?.Inventory?.Equipment.Select( e => $"{e.Resource?.ResourceName}({e.Resource?.Slot})" ) ?? Enumerable.Empty<string>() )}" );
		var equipment = pawn?.CurrentEquipment;
		if ( !equipment.IsValid() ) { Log.Info( "dev_aim_info: no equipment" ); return; }
		var manual = equipment.GetComponentInChildren<ManualOffset>( true );
		var hasOptic = equipment.TryGetOpticAim( out var optic );
		Log.Info( $"dev_aim_info: {equipment.Resource?.ResourceName} AimOffset={manual?.AimOffset} Angles={manual?.AimAngleOffset} opticAim={hasOptic} optic={optic?.ResourcePath} opticOffset={optic?.OpticAimOffset}" );
		foreach ( var point in equipment.ViewModel?.GameObject.Components.GetAll<Gunsmith.GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ) ?? Enumerable.Empty<Gunsmith.GunsmithAttachmentPoint>() )
			Log.Info( $"dev_aim_info:   {point.Category} = {point.CurrentPart?.ResourcePath}" );
	}

	/// <summary>Live-tune the current weapon's iron sight offset (not saved), e.g. dev_aim_offset -4 0 -0.5.</summary>
	[ConCmd( "dev_aim_offset" )]
	public static void AimOffset( float x, float y, float z )
	{
		var manual = Client.Local?.PlayerPawn?.CurrentEquipment?.GetComponentInChildren<ManualOffset>( true );
		if ( manual.IsValid() ) manual.AimOffset = new Vector3( x, y, z );
	}

	/// <summary>Log the model attachments of the current viewmodel (looking for sight reference points).</summary>
	[ConCmd( "dev_vm_attachments" )]
	public static void VmAttachments()
	{
		var renderer = Client.Local?.PlayerPawn?.CurrentEquipment?.ViewModel?.ModelRenderer;
		var model = renderer?.Model;
		if ( model is null ) return;
		for ( int i = 0; i < model.Attachments.Count; i++ )
		{
			var a = model.Attachments.All.ElementAt( i );
			var world = renderer.GetAttachment( a.Name );
			Log.Info( $"dev_vm_attachments: {a.Name} local={a.LocalTransform.Position} cam={world?.Position}" );
		}
		var cam = Client.Local?.PlayerPawn?.CameraController?.Camera;
		if ( cam.IsValid() )
			Log.Info( $"dev_vm_attachments: renderer rel cam = {cam.WorldTransform.ToLocal( renderer.WorldTransform ).Position} {cam.WorldTransform.ToLocal( renderer.WorldTransform ).Rotation.Angles()}" );
	}

	/// <summary>Load a scene file during play, e.g. dev_scene scenes/gunsmith.scene.</summary>
	[ConCmd( "dev_scene" )]
	public static void LoadScene( string path )
	{
		var scene = ResourceLibrary.Get<SceneFile>( path );
		if ( scene is null ) { Log.Warning( $"dev_scene: no scene at {path}" ); return; }
		Game.ActiveScene.Load( scene );
	}

	/// <summary>Open a main menu page by route, e.g. dev_menu /new.</summary>
	[ConCmd( "dev_menu" )]
	public static void Menu( string route )
	{
		if ( UI.MainMenuRoot.Instance.IsValid() ) Sandbox.UI.Navigation.NavigationExtensions.Navigate( UI.MainMenuRoot.Instance, "/" + route.TrimStart( '/' ) );
	}
}
