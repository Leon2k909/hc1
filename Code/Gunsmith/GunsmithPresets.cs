using System.Text.Json;

namespace Facepunch.Gunsmith;

/// <summary>
/// Named builds saved for a weapon (the gunsmith's BUILDS), so one gun can have several sets of attachments. Each is the
/// weapon's build code, the one Share Build makes (attachments, camo and reticle), kept in one cookie per weapon, so
/// builds are shared by every class. Applying one imports its code into the active class, the same as pasting it into
/// Share Build, and links the class's weapon to it, so the gunsmith can say which build a class carries and whether
/// it's been changed since (<see cref="GetCurrent(EquipmentResource)"/>).
/// </summary>
public static class GunsmithPresets
{
	public const int MaxPerWeapon = 8;
	public const int MaxNameLength = 24;

	public sealed class Preset
	{
		/// <summary> Stays the same through a rename, so a class's link holds. Builds saved before it had one get one on load. </summary>
		public string Id { get; set; }
		public string Name { get; set; }
		public string Code { get; set; }
	}

	private static string CookieKey( EquipmentResource resource ) => $"hc1.gunsmith.presets.{resource.ResourcePath}";

	/// <summary> The build the active class's weapon was last saved as or put on from. </summary>
	private static string LinkCookieKey( EquipmentResource resource ) =>
		$"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{resource.ResourcePath}.build";

	public static List<Preset> Get( EquipmentResource resource )
	{
		if ( !resource.IsValid() )
			return new();

		var json = Game.Cookies.Get<string>( CookieKey( resource ), "" );
		if ( string.IsNullOrWhiteSpace( json ) )
			return new();

		List<Preset> presets;
		try
		{
			presets = JsonSerializer.Deserialize<List<Preset>>( json )?.Where( x => !string.IsNullOrWhiteSpace( x?.Code ) ).ToList() ?? new();
		}
		catch ( JsonException )
		{
			return new();
		}

		var missing = false;
		foreach ( var preset in presets.Where( x => string.IsNullOrEmpty( x.Id ) ) )
		{
			preset.Id = NewId();
			missing = true;
		}

		if ( missing )
			Store( resource, presets );

		return presets;
	}

	private static void Store( EquipmentResource resource, List<Preset> presets ) =>
		Game.Cookies.Set( CookieKey( resource ), JsonSerializer.Serialize( presets ) );

	private static string NewId() => Guid.NewGuid().ToString( "N" );

	/// <summary> The weapon's build in the active class as a build is saved: with parts its level hasn't unlocked yet. </summary>
	private static string CurrentCode( EquipmentResource resource ) =>
		GunsmithLoadoutManager.ExportWeaponBuildCode( resource, withLockedParts: true );

	private static string CleanName( string name )
	{
		name = (name ?? "").Trim().ToUpperInvariant();
		return name.Length > MaxNameLength ? name.Substring( 0, MaxNameLength ).TrimEnd() : name;
	}

	/// <summary>
	/// Saves the weapon's build in the active class as a new build called <paramref name="name"/> (a numbered name if
	/// it's blank), or over the build with that name, and links the class's weapon to it.
	/// </summary>
	public static bool Save( EquipmentResource resource, string name, out Preset saved, out GunsmithMessage error )
	{
		error = null;
		saved = null;
		if ( !resource.IsValid() )
		{
			error = "Select a weapon first.";
			return false;
		}

		var presets = Get( resource );
		name = CleanName( name );
		if ( name.Length == 0 )
			name = NextName( presets );

		var index = presets.FindIndex( x => string.Equals( x.Name, name, StringComparison.OrdinalIgnoreCase ) );
		if ( index < 0 && presets.Count >= MaxPerWeapon )
		{
			error = new GunsmithMessage( "A weapon keeps {0} builds. Delete one first.", MaxPerWeapon );
			return false;
		}

		saved = index >= 0 ? presets[index] : new Preset { Id = NewId(), Name = name };
		saved.Code = CurrentCode( resource );
		if ( index < 0 )
			presets.Add( saved );

		Store( resource, presets );
		Link( resource, saved );
		return true;
	}

	/// <summary> Saves the weapon's build in the active class over <paramref name="preset"/>, keeping its name. </summary>
	public static bool Update( EquipmentResource resource, Preset preset )
	{
		if ( !resource.IsValid() || preset is null )
			return false;

		var presets = Get( resource );
		var stored = presets.FirstOrDefault( x => x.Id == preset.Id );
		if ( stored is null )
			return false;

		stored.Code = CurrentCode( resource );
		Store( resource, presets );
		Link( resource, stored );
		return true;
	}

	public static bool Rename( EquipmentResource resource, Preset preset, string name, out GunsmithMessage error )
	{
		error = null;
		if ( !resource.IsValid() || preset is null )
			return false;

		name = CleanName( name );
		if ( name.Length == 0 )
		{
			error = "Give the build a name.";
			return false;
		}

		var presets = Get( resource );
		var stored = presets.FirstOrDefault( x => x.Id == preset.Id );
		if ( stored is null )
			return false;

		if ( presets.Any( x => x.Id != stored.Id && string.Equals( x.Name, name, StringComparison.OrdinalIgnoreCase ) ) )
		{
			error = new GunsmithMessage( "{0} is already a build's name.", name );
			return false;
		}

		stored.Name = name;
		Store( resource, presets );
		return true;
	}

	/// <summary> Puts the build on the weapon in the active class, and links the class's weapon to it. </summary>
	public static bool Apply( EquipmentResource resource, Preset preset, out GunsmithMessage error )
	{
		if ( !GunsmithLoadoutManager.TryImportWeaponBuildCode( resource, preset?.Code, out error ) )
			return false;

		// A code read back can differ in its last digits (a colour through hex), so the build keeps what the class now
		// exports, and reads as on the gun rather than changed.
		var presets = Get( resource );
		var stored = presets.FirstOrDefault( x => x.Id == preset.Id );
		if ( stored is not null )
		{
			stored.Code = CurrentCode( resource );
			Store( resource, presets );
		}

		Link( resource, stored ?? preset );
		return true;
	}

	public static void Delete( EquipmentResource resource, Preset preset )
	{
		if ( !resource.IsValid() || preset is null )
			return;

		var presets = Get( resource );
		presets.RemoveAll( x => x.Id == preset.Id );
		Store( resource, presets );

		if ( Game.Cookies.Get<string>( LinkCookieKey( resource ), "" ) == preset.Id )
			Game.Cookies.Set( LinkCookieKey( resource ), "" );
	}

	private static void Link( EquipmentResource resource, Preset preset ) =>
		Game.Cookies.Set( LinkCookieKey( resource ), preset?.Id ?? "" );

	/// <summary>
	/// The build the active class's weapon carries, and whether it's been changed since. That's the linked build while
	/// the gun matches it, else any build it matches (one saved in another class, say), else the linked build, changed.
	/// No build when it matches none and none is linked.
	/// </summary>
	public static (Preset Build, bool Modified) GetCurrent( EquipmentResource resource ) =>
		GetCurrent( resource, Get( resource ) );

	public static (Preset Build, bool Modified) GetCurrent( EquipmentResource resource, List<Preset> presets )
	{
		if ( !resource.IsValid() || presets is null || presets.Count == 0 )
			return (null, false);

		var code = CurrentCode( resource );
		var linkedId = Game.Cookies.Get<string>( LinkCookieKey( resource ), "" );
		var linked = string.IsNullOrEmpty( linkedId ) ? null : presets.FirstOrDefault( x => x.Id == linkedId );

		if ( linked is not null && linked.Code == code )
			return (linked, false);

		var match = presets.FirstOrDefault( x => x.Code == code );
		if ( match is not null )
			return (match, false);

		return linked is not null ? (linked, true) : (null, false);
	}

	private static string NextName( List<Preset> presets )
	{
		for ( var i = presets.Count + 1; ; i++ )
		{
			var name = $"BUILD {i}";
			if ( !presets.Any( x => string.Equals( x.Name, name, StringComparison.OrdinalIgnoreCase ) ) )
				return name;
		}
	}
}

/// <summary>
/// Text for the player, kept in English with the values that fill it in and translated only when it's shown
/// (<see cref="Shown"/>), so a message already on screen changes language with the rest.
/// </summary>
public sealed class GunsmithMessage
{
	/// <summary> The English, a format string when there are <see cref="Args"/> ("{0} deleted."). </summary>
	public string English { get; }

	/// <summary> The values for its placeholders. Messages among them are shown translated, and a list of them joined. </summary>
	public object[] Args { get; }

	public GunsmithMessage( string english, params object[] args )
	{
		English = english ?? "";
		Args = args ?? Array.Empty<object>();
	}

	/// <summary> The message in the player's language. </summary>
	public string Shown => Args.Length == 0 ? Tr( English ) : Tr( English, Args.Select( Show ).ToArray() );

	private static object Show( object arg ) => arg switch
	{
		GunsmithMessage message => message.Shown,
		IEnumerable<GunsmithMessage> list => string.Join( ", ", list.Select( x => x.Shown ) ),
		_ => arg
	};

	public static implicit operator GunsmithMessage( string english ) => english is null ? null : new GunsmithMessage( english );

	public override string ToString() => Shown;
}
