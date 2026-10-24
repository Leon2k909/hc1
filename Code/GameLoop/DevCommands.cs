namespace Facepunch;

public static class DevCommands
{
	/// <summary>Hold ADS without input, for testing optics through the editor bridge.</summary>
	[ConVar( "dev_force_aim", Saved = false )] public static bool ForceAim { get; set; }

	/// <summary>Walk without input (1 forward, -1 back), for testing movement through the editor bridge.</summary>
	[ConVar( "dev_force_move", Saved = false )] public static float ForceMove { get; set; }

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
		GameUtils.LoadMap( map );
	}

	/// <summary>Start the zombies mode the same way the hub's Zombies button does.</summary>
	[ConCmd( "dev_zombies" )]
	public static void Zombies( string mapContains = "flatgrass" )
	{
		var mode = GameObject.GetPrefab( "prefabs/game_modes/zombies.prefab" )?.GetComponent<GameMode>();
		if ( !mode.IsValid() ) { Log.Warning( "dev_zombies: no zombies mode prefab" ); return; }

		var scene = ResourceLibrary.GetAll<SceneFile>()
			.FirstOrDefault( s => s.ResourcePath?.Contains( mapContains, StringComparison.OrdinalIgnoreCase ) ?? false )
			?? GameUtils.GetAvailableMaps().FirstOrDefault();
		if ( scene is null ) { Log.Warning( "dev_zombies: no map" ); return; }

		GameMode.SetCurrent( mode );
		GameMode.SetHardcore( false );
		GameUtils.LoadMap( scene );
	}

	/// <summary>Zombies: give the local player points.</summary>
	[ConCmd( "dev_points" )]
	public static void Points( int amount = 10000 )
	{
		Client.Local?.PlayerPawn?.GetComponent<ZombiesPlayerEconomy>()?.AddPoints( amount );
	}

	/// <summary>Zombies: hurt the local player (100 = downs you without Iron Tonic).</summary>
	[ConCmd( "dev_hurt" )]
	public static void Hurt( float amount = 100f )
	{
		var pawn = Client.Local?.PlayerPawn;
		pawn?.HealthComponent?.TakeDamage( new DamageInfo( pawn, amount ) );
	}

	/// <summary>Hardcore: shoot the local player in the leg, for testing the limp through the editor bridge.</summary>
	[ConCmd( "dev_legshot" )]
	public static void LegShot( float damage = 1f )
	{
		var pawn = Client.Local?.PlayerPawn;
		pawn?.HealthComponent?.TakeDamage( new DamageInfo( pawn, damage, Hitbox: HitboxTags.Leg ) );
	}

	/// <summary>Fall damage on the local player, as if they'd landed hard, for testing the limp it leaves.</summary>
	[ConCmd( "dev_fall" )]
	public static void Fall( float damage = 10f )
	{
		var pawn = Client.Local?.PlayerPawn;
		pawn?.HealthComponent?.TakeDamage( new DamageInfo( pawn, damage, Flags: DamageFlags.FallDamage ) );
	}

	/// <summary>
	/// Mantle whatever's in front of the local player, the way they're looking, as a Jump press moving forward would, and
	/// log the climb or vault it planned or why it couldn't (the bridge's held inputs don't reach the movement).
	/// </summary>
	[ConCmd( "dev_mantle" )]
	public static void Mantle()
	{
		var pawn = Client.Local?.PlayerPawn;
		pawn?.TryStartMantle( !pawn.CharacterController.IsOnGround, ignoreInput: true, log: true );
	}

	/// <summary> Slides where you're looking, as if you'd pressed Duck at a rifle's sprint, and logs the speed or why not. </summary>
	[ConCmd( "dev_slide" )]
	public static void Slide()
	{
		var pawn = Client.Local?.PlayerPawn;
		if ( !pawn.IsValid() ) return;

		pawn.CharacterController.Velocity = pawn.EyeAngles.WithPitch( 0 ).Forward * 285f;
		pawn.TryStartSlide( ignoreInput: true, log: true );
	}

	/// <summary>Jump the local player again the moment they land, for testing jump stamina through the editor bridge.</summary>
	[ConCmd( "dev_jumps" )]
	public static async void Jumps( int count = 6 )
	{
		var pawn = Client.Local?.PlayerPawn;
		for ( var i = 0; i < count; i++ )
		{
			while ( pawn.IsValid() && !pawn.CharacterController.IsOnGround )
				await GameTask.Delay( 1 );

			if ( !pawn.IsValid() ) return;
			pawn.Jump();
			await GameTask.DelaySeconds( 0.1f );
		}
	}

	/// <summary>
	/// Press Prone as the local player <paramref name="count"/> times, <paramref name="interval"/> seconds apart, logging the
	/// prone stamina and how far the body's height got each time, for testing prone spam through the editor bridge.
	/// </summary>
	[ConCmd( "dev_prone" )]
	public static async void Prone( int count = 6, float interval = 0.2f )
	{
		var pawn = Client.Local?.PlayerPawn;
		for ( var i = 0; i < count && pawn.IsValid(); i++ )
		{
			var height = pawn.CharacterController.Height;
			pawn.ToggleProne();
			Log.Info( $"dev_prone: height {height:F1}, then {(pawn.IsProne ? "down" : "up")}, fatigue {pawn.ProneFatigue:F2}" );
			await GameTask.DelaySeconds( interval );
		}

		if ( pawn.IsValid() )
			Log.Info( $"dev_prone: height {pawn.CharacterController.Height:F1}, fatigue {pawn.ProneFatigue:F2}" );
	}

	/// <summary>Press E as the local player, on whatever they're looking at, for testing through the editor bridge.</summary>
	[ConCmd( "dev_use" )]
	public static void Use()
	{
		Client.Local?.PlayerPawn?.DevUse();
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

	/// <summary>Zombies: kill every zombie (like the Clean Sweep power-up, no points).</summary>
	[ConCmd( "dev_nuke" )]
	public static void Nuke()
	{
		foreach ( var z in Game.ActiveScene.GetAllComponents<ZombieAI>().ToList() )
			z.Kill( null );
	}

	/// <summary>
	/// Zombies: hit the nearest zombie as the local player, the way a bullet does (head 1 for a headshot), for testing
	/// the hitmarker, points and score feed through the editor bridge. Host only, like the zombies' damage.
	/// </summary>
	[ConCmd( "dev_zombie_hit" )]
	public static void ZombieHit( float damage = 1000f, int head = 0 )
	{
		var pawn = Client.Local?.PlayerPawn;
		if ( !pawn.IsValid() ) return;

		var zombie = Game.ActiveScene.GetAllComponents<ZombieAI>()
			.Where( z => z.Health > 0f && z.GameObject.Tags.Has( "enemy" ) )
			.OrderBy( z => z.WorldPosition.Distance( pawn.WorldPosition ) )
			.FirstOrDefault();
		if ( zombie is null ) { Log.Warning( "dev_zombie_hit: no zombie" ); return; }

		// ZombieAI.IsHeadshot goes by the hit's height: from the head bone up is the head.
		var position = zombie.WorldPosition + Vector3.Up * 40f;
		if ( head != 0 && zombie.GetComponent<SkinnedModelRenderer>() is { } renderer && renderer.TryGetBoneTransform( "head", out var bone ) )
			position = bone.Position + Vector3.Up * 2f;

		zombie.OnDamage( new Sandbox.DamageInfo( damage, pawn.GameObject, null ) { Position = position } );
	}

	/// <summary>Zombies: use the nearest buy station of a kind (perk name, "box", or "wall").</summary>
	[ConCmd( "dev_buy" )]
	public static void Buy( string what )
	{
		var pawn = Client.Local?.PlayerPawn;
		if ( pawn is null ) return;

		var station = Game.ActiveScene.GetAllComponents<ZombiesBuyStation>()
			.Where( s => what.Equals( "box", StringComparison.OrdinalIgnoreCase ) ? s.Kind == ZombiesBuyKind.WeaponCrate
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

	/// <summary>Live-tune the current weapon's optic aim correction (not saved), e.g. dev_optic_correction 0 0 -1.5.</summary>
	[ConCmd( "dev_optic_correction" )]
	public static void OpticCorrection( float x, float y, float z )
	{
		var manual = Client.Local?.PlayerPawn?.CurrentEquipment?.GetComponentInChildren<ManualOffset>( true );
		if ( manual.IsValid() ) manual.OpticAimCorrection = new Vector3( x, y, z );
	}

	/// <summary>Select an optic for live ADS calibration.</summary>
	[ConCmd( "dev_optic" )]
	public static void Optic( string name )
	{
		var equipment = Client.Local?.PlayerPawn?.CurrentEquipment;
		if ( !equipment.IsValid() || !equipment.ViewModel.IsValid() ) return;
		var part = ResourceLibrary.GetAll<Facepunch.Gunsmith.GunsmithPart>()
			.FirstOrDefault( p => p.IsValid() && p.Category == Facepunch.Gunsmith.GunsmithPartType.Optic
				&& p.Supports( equipment.Resource ) && p.ResourcePath.Contains( name, StringComparison.OrdinalIgnoreCase ) );
		if ( !part.IsValid() ) { Log.Warning( $"dev_optic: no optic matching {name}" ); return; }
		Facepunch.Gunsmith.GunsmithLoadoutManager.SetAttachment( equipment.Resource, Facepunch.Gunsmith.GunsmithPartType.Optic, part );
		Facepunch.Gunsmith.GunsmithLoadoutManager.ApplyAttachments( equipment.Resource, equipment.ViewModel.GameObject );
		Log.Info( $"dev_optic: {part.ResourcePath}" );
	}

	/// <summary>
	/// Corner slicing: put the local player where it cants the gun hardest within <paramref name="radius"/> (a wall's edge
	/// beside the sights), looking past it, for testing through the editor bridge with dev_force_aim 1. Side 1 only takes
	/// corners that lean the sights right, -1 left. Then logs the cant as it eases in.
	/// </summary>
	[ConCmd( "dev_corner" )]
	public static async void Corner( float radius = 1500f, int side = 0 )
	{
		var pawn = Client.Local?.PlayerPawn;
		if ( !pawn.IsValid() ) return;

		// Look from the camera's own height, so the fan sees what it will once the player is there.
		var camera = pawn.CameraController?.Camera;
		var eyeHeight = camera.IsValid() ? camera.WorldPosition.z - pawn.WorldPosition.z : 64f;

		var scene = Game.ActiveScene;
		var best = 0f;
		var bestPoint = Vector3.Zero;
		var bestYaw = 0f;
		for ( var i = 0; i < 80; i++ )
		{
			if ( scene.NavMesh.GetRandomPoint( pawn.WorldPosition, radius ) is not { } point )
				continue;

			for ( var yaw = 0f; yaw < 360f; yaw += 15f )
			{
				var lean = ViewModel.FindCornerLean( scene, point + Vector3.Up * eyeHeight, new Angles( 0f, yaw, 0f ), pawn.GameObject.Root );
				if ( side != 0 && MathF.Sign( lean ) != side ) continue;
				if ( MathF.Abs( lean ) <= MathF.Abs( best ) ) continue;

				best = lean;
				bestPoint = point;
				bestYaw = yaw;
			}
		}

		if ( best == 0f ) { Log.Warning( "dev_corner: no corner found" ); return; }

		pawn.Teleport( bestPoint, Rotation.FromYaw( bestYaw ) );
		Log.Info( $"dev_corner: lean {best:0.00} at {bestPoint} yaw {bestYaw:0}" );

		for ( var i = 0; i < 4; i++ )
		{
			await GameTask.DelaySeconds( 0.5f );
			Log.Info( $"dev_corner: cant {pawn.CurrentEquipment?.ViewModel?.CornerRoll:0.0} deg" );
		}
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

	/// <summary>Show a toast locally: dev_toast ct / dev_toast t for the round-win banners, anything else as a plain toast.</summary>
	[ConCmd( "dev_toast" )]
	public static void ShowToast( string which = "ct", float duration = 8f )
	{
		if ( which.Equals( "ct", StringComparison.OrdinalIgnoreCase ) )
			UI.Toast.Instance?.Show( "Blue Team Wins!", UI.ToastType.CounterTerroristsWin, duration );
		else if ( which.Equals( "t", StringComparison.OrdinalIgnoreCase ) )
			UI.Toast.Instance?.Show( "Red Team Wins!", UI.ToastType.TerroristsWin, duration );
		else
			UI.Toast.Instance?.Show( which, UI.ToastType.Generic, duration );
	}

	/// <summary>Show a medal locally: dev_medal oneshot|headshot|streak|double|triple|fury|frenzy|handling|endurance [seconds on screen].</summary>
	[ConCmd( "dev_medal" )]
	public static void ShowMedal( string which = "oneshot", float seconds = 1.6f )
	{
		var hud = Game.ActiveScene?.GetAllComponents<UI.MainHUD>().FirstOrDefault();
		if ( hud?.MedalFeed is null ) { Log.Warning( "dev_medal: no medal feed (needs a local pawn in play mode)" ); return; }
		hud.MedalFeed.Preview( which, seconds );
	}

	/// <summary>Close the in-game pause/settings menu, as Escape would.</summary>
	[ConCmd( "dev_closemenu" )]
	public static void CloseMenu()
	{
		UI.PauseMenuPanel.CloseAny();
	}

	/// <summary>
	/// Press Escape as the key does, so whatever takes Escape (the menus' back steps, the quit prompt, the pause menu)
	/// gets it. It's pressed as the next update starts (<see cref="DevEscapeSystem"/>): the bridge runs commands at any
	/// point in the frame, and an Escape left over after the scene's update is taken by the editor.
	/// </summary>
	[ConCmd( "dev_escape" )]
	public static void PressEscape()
	{
		DevEscapeSystem.Pending = true;
	}

	/// <summary>Open a main menu page by route, e.g. dev_menu /new.</summary>
	[ConCmd( "dev_menu" )]
	public static void Menu( string route )
	{
		if ( UI.MainMenuRoot.Instance.IsValid() ) Sandbox.UI.Navigation.NavigationExtensions.Navigate( UI.MainMenuRoot.Instance, "/" + route.TrimStart( '/' ) );
	}

	/// <summary>
	/// Click a visible UI element by its classes, for testing menus without a mouse: dev_click squad-cog, or
	/// dev_click privacy-option 2 for the third. Dotted classes must all match (side-link.friends-all). It fires the
	/// element's onclick, which bubbles up to its parents' handlers like a real click. Hover-only UI isn't reached.
	/// </summary>
	[ConCmd( "dev_click" )]
	public static void Click( string classes, int index = 0 )
	{
		var wanted = classes.Split( '.', StringSplitOptions.RemoveEmptyEntries );
		var matches = Game.ActiveScene.GetAllComponents<PanelComponent>()
			.Where( x => x.Panel is not null )
			.SelectMany( x => x.Panel.Descendants )
			.Where( x => x.IsVisible && wanted.All( x.HasClass ) )
			.ToList();

		if ( index < 0 || index >= matches.Count )
		{
			Log.Warning( $"dev_click: {matches.Count} visible element(s) with .{string.Join( ".", wanted )}" );
			return;
		}

		matches[index].CreateEvent( "onclick" );
		Log.Info( $"dev_click: clicked .{string.Join( ".", wanted )} ({index + 1} of {matches.Count})" );
	}

	/// <summary>
	/// Switch the game's language and save it, as the settings page does:
	/// dev_language uk|us|fr|de|es|pt|it|pl|ru|ua|tr|ja|ko|zh|tw. "uk" is English (UK), so Ukrainian is "ua".
	/// </summary>
	[ConCmd( "dev_language" )]
	public static void SetLanguage( string language )
	{
		GameLanguage? picked = language.ToLowerInvariant() switch
		{
			"uk" or "en" => GameLanguage.EnglishUK,
			"us" => GameLanguage.EnglishUS,
			"fr" => GameLanguage.French,
			"de" => GameLanguage.German,
			"es" => GameLanguage.Spanish,
			"pt" or "br" => GameLanguage.PortugueseBrazil,
			"it" => GameLanguage.Italian,
			"pl" => GameLanguage.Polish,
			"ru" => GameLanguage.Russian,
			"ua" => GameLanguage.Ukrainian,
			"tr" => GameLanguage.Turkish,
			"ja" or "jp" => GameLanguage.Japanese,
			"ko" or "kr" => GameLanguage.Korean,
			"zh" or "cn" => GameLanguage.ChineseSimplified,
			"tw" or "hk" => GameLanguage.ChineseTraditional,
			_ => null
		};
		if ( picked is null )
		{
			Log.Warning( $"dev_language: {language}? Use uk, us, fr, de, es, pt, it, pl, ru, ua, tr, ja, ko, zh or tw (now {GameText.Current})" );
			return;
		}
		GameText.SetLanguage( picked.Value );
		Log.Info( $"dev_language: {GameText.Current}" );
	}

	/// <summary>Log the text shown in English since the language was last set, because its tables don't have it.</summary>
	[ConCmd( "dev_text_missing" )]
	public static void TextMissing()
	{
		var missing = GameText.Missing.OrderBy( x => x, StringComparer.OrdinalIgnoreCase ).ToList();
		Log.Info( $"dev_text_missing: {missing.Count} in {GameText.Current}" );
		foreach ( var text in missing )
			Log.Info( $"  {text}" );
	}

	/// <summary>
	/// Fill the hub's FRIENDS card to check its layout without friends in a match: you, plus made-up offline rows (Steam
	/// ids 1 and up, which no account has) up to [rows]. Run it again to take them all off.
	/// </summary>
	[ConCmd( "dev_friends_sample" )]
	public static void FriendsSample( int rows = 1 )
	{
		var me = (ulong)Game.SteamId;
		if ( RecentFriends.Contains( me ) )
		{
			RecentFriends.Forget( me );
			for ( ulong id = 1; id < 20; id++ ) RecentFriends.Forget( id );
			Log.Info( "dev_friends_sample: took the sample rows off the FRIENDS card" );
			return;
		}

		rows = Math.Clamp( rows, 1, 20 );
		for ( ulong id = 1; id < (ulong)rows; id++ ) RecentFriends.Remember( id );
		RecentFriends.Remember( me );
		Log.Info( $"dev_friends_sample: added {rows} sample row(s) to the FRIENDS card (run it again to undo)" );
	}

	/// <summary>Forget every remembered friend (the hub's FRIENDS card), real ones included.</summary>
	[ConCmd( "dev_friends_clear" )]
	public static void FriendsClear()
	{
		RecentFriends.Clear();
		Log.Info( "dev_friends_clear: FRIENDS card emptied" );
	}

	/// <summary>
	/// Fill the HUD's list of who's talking (Voices) to check its layout with nobody talking: you, a squadmate, a dead
	/// enemy and a spectator, all with your avatar. Run it again to take them off.
	/// </summary>
	[ConCmd( "dev_voices_sample" )]
	public static void VoicesSample()
	{
		Facepunch.UI.Voices.ShowSample = !Facepunch.UI.Voices.ShowSample;
		Log.Info( Facepunch.UI.Voices.ShowSample
			? "dev_voices_sample: sample rows in the list of who's talking (run it again to take them off)"
			: "dev_voices_sample: took the sample rows off the list of who's talking" );
	}

	/// <summary>
	/// Set the match's weather (host): dev_weather clear|drizzle|steady|showers [mm/h]. With a rate the rain holds at
	/// it; without one it follows the kind's own schedule. With no arguments it logs the weather now.
	/// </summary>
	[ConCmd( "dev_weather" )]
	public static void SetWeather( string kind = "", float rate = -1f )
	{
		var scene = Game.ActiveScene;
		if ( scene is null ) return;
		var weather = Weather.Ensure( scene );
		if ( !weather.IsValid() )
		{
			Log.Warning( "dev_weather: only the host can set the weather" );
			return;
		}

		if ( string.IsNullOrWhiteSpace( kind ) )
		{
			Log.Info( $"dev_weather: {weather.Kind}, {weather.RainRate:0.##} mm/h" );
			return;
		}

		if ( weather.IsProxy )
		{
			Log.Warning( "dev_weather: only the host can set the weather" );
			return;
		}

		if ( !Enum.TryParse<WeatherKind>( kind, true, out var parsed ) )
		{
			Log.Warning( "dev_weather: clear, drizzle, steady or showers" );
			return;
		}

		weather.Set( parsed, rate );
		Log.Info( $"dev_weather: {weather.Kind}, {weather.RainRate:0.##} mm/h" );
	}

	/// <summary>
	/// Holds every puddle at a fill, 0-1 of its hollow (this machine only), to look at them without waiting for the rain
	/// to fill them. With no argument, or below 0, they follow the rain again. Puddles only show while it rains.
	/// </summary>
	[ConCmd( "dev_puddles" )]
	public static void SetPuddles( float fill = -1f )
	{
		RainPuddles.ForcedFill = fill < 0f ? -1f : Math.Clamp( fill, 0f, 1f );
		Log.Info( fill < 0f ? "dev_puddles: following the rain" : $"dev_puddles: held at {RainPuddles.ForcedFill:0.##}" );
	}

	/// <summary>
	/// A lightning strike <paramref name="distance"/> m off in the way you're looking (this machine only), flash and
	/// thunder: dev_thunder [metres] [cloud]. It only shows while it rains.
	/// </summary>
	[ConCmd( "dev_thunder" )]
	public static void Thunder( float distance = 1500f, int cloud = 0 )
	{
		var camera = Game.ActiveScene?.Camera;
		var forward = camera.IsValid() ? camera.WorldRotation.Forward : Vector3.Forward;
		var bearing = MathF.Atan2( forward.y, forward.x );
		distance = MathF.Max( distance, 50f );
		RainView.RequestStrike( distance, bearing, cloud != 0 );
		// A flash in the cloud is heard from the cloud over it, about 6 km up.
		var heard = cloud != 0 ? MathF.Sqrt( distance * distance + 6000f * 6000f ) : distance;
		Log.Info( $"dev_thunder: {(cloud != 0 ? "in the cloud" : "to the ground")} {distance:0} m off, heard in {heard / 338f:0.0} s" );
	}
}

/// <summary> Presses Escape for <see cref="DevCommands.PressEscape"/> as the scene's update starts, before anything takes it. </summary>
public sealed class DevEscapeSystem : GameObjectSystem<DevEscapeSystem>
{
	public static bool Pending { get; set; }

	public DevEscapeSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.StartUpdate, 0, PressPending, "DevEscape" );
	}

	private void PressPending()
	{
		if ( !Pending ) return;

		Pending = false;
		Input.EscapePressed = true;
	}
}
