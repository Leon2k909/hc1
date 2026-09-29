using System.Text.Json;

namespace Facepunch.Gunsmith;

/// <summary>
/// Named builds saved for a weapon (the gunsmith's PRESETS). Each is the weapon's build code, the one Share Build makes
/// (attachments, camo and reticle), kept in one cookie per weapon, so presets are shared by every class. Applying one
/// imports its code into the active class, the same as pasting it into Share Build.
/// </summary>
public static class GunsmithPresets
{
	public const int MaxPerWeapon = 8;
	public const int MaxNameLength = 24;

	public sealed class Preset
	{
		public string Name { get; set; }
		public string Code { get; set; }
	}

	private static string CookieKey( EquipmentResource resource ) => $"hc1.gunsmith.presets.{resource.ResourcePath}";

	public static List<Preset> Get( EquipmentResource resource )
	{
		if ( !resource.IsValid() )
			return new();

		var json = Game.Cookies.Get<string>( CookieKey( resource ), "" );
		if ( string.IsNullOrWhiteSpace( json ) )
			return new();

		try
		{
			return JsonSerializer.Deserialize<List<Preset>>( json )?.Where( x => !string.IsNullOrWhiteSpace( x?.Code ) ).ToList() ?? new();
		}
		catch ( JsonException )
		{
			return new();
		}
	}

	private static void Store( EquipmentResource resource, List<Preset> presets ) =>
		Game.Cookies.Set( CookieKey( resource ), JsonSerializer.Serialize( presets ) );

	/// <summary>
	/// Saves the weapon's build in the active class as <paramref name="name"/> (a numbered name if it's blank), replacing
	/// a preset with the same name.
	/// </summary>
	public static bool Save( EquipmentResource resource, string name, out GunsmithMessage error )
	{
		error = null;
		if ( !resource.IsValid() )
		{
			error = "Select a weapon first.";
			return false;
		}

		var presets = Get( resource );
		name = (name ?? "").Trim().ToUpperInvariant();
		if ( name.Length > MaxNameLength )
			name = name.Substring( 0, MaxNameLength ).TrimEnd();
		if ( name.Length == 0 )
			name = NextName( presets );

		var index = presets.FindIndex( x => string.Equals( x.Name, name, StringComparison.OrdinalIgnoreCase ) );
		if ( index < 0 && presets.Count >= MaxPerWeapon )
		{
			error = new GunsmithMessage( "A weapon keeps {0} presets. Delete one first.", MaxPerWeapon );
			return false;
		}

		var preset = new Preset { Name = name, Code = GunsmithLoadoutManager.ExportWeaponBuildCode( resource ) };
		if ( index >= 0 ) presets[index] = preset;
		else presets.Add( preset );

		Store( resource, presets );
		return true;
	}

	/// <summary> Puts the preset's build on the weapon in the active class. </summary>
	public static bool Apply( EquipmentResource resource, Preset preset, out GunsmithMessage error ) =>
		GunsmithLoadoutManager.TryImportWeaponBuildCode( resource, preset?.Code, out error );

	public static void Delete( EquipmentResource resource, Preset preset )
	{
		if ( !resource.IsValid() || preset is null )
			return;

		var presets = Get( resource );
		presets.RemoveAll( x => string.Equals( x.Name, preset.Name, StringComparison.OrdinalIgnoreCase ) );
		Store( resource, presets );
	}

	/// <summary> Whether the weapon's build in the active class is exactly this preset. </summary>
	public static bool IsCurrent( EquipmentResource resource, Preset preset ) =>
		resource.IsValid() && preset is not null && preset.Code == GunsmithLoadoutManager.ExportWeaponBuildCode( resource );

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
