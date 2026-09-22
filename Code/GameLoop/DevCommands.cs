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
}
