using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

/// <summary>
/// The Theater's saved matches, in the game's data folder. Each has its recording, <c>replays/&lt;id&gt;.movie</c> (a
/// MovieMaker clip, see <see cref="MatchRecorder"/>), and a sidecar, <c>replays/&lt;id&gt;.json</c> (<see cref="Info"/>),
/// which the Theater page lists and playback reads first. The sidecar is written after the recording, so a recording
/// without one is unfinished or broken. Beside them, <c>replays/&lt;id&gt;.actions</c> (<see cref="Actions"/>) has what
/// the soldiers did with their guns, for the first-person view: replays from before it have none.
/// </summary>
public static class TheaterReplays
{
	public const string Folder = "replays";

	/// <summary> Only the newest this many are kept. </summary>
	public const int MaxReplays = 20;

	/// <summary> Replays older than this are deleted. </summary>
	public const int MaxAgeDays = 7;

	/// <summary> Sidecars of another version aren't listed: their recordings may not play. </summary>
	public const int CurrentVersion = 1;

	/// <summary> What a replay's sidecar holds. </summary>
	public sealed class Info
	{
		public int Version { get; set; }

		/// <summary> The match scene's MapInstances. The recording has no map in it: playback loads these again. </summary>
		public List<MapEntry> Maps { get; set; } = new();

		/// <summary> The map's name as the menus show it. </summary>
		public string MapTitle { get; set; }

		/// <summary> The mode's title in English, translated when it's shown. </summary>
		public string Mode { get; set; }

		public string ModeIdent { get; set; }

		public DateTime Recorded { get; set; }

		/// <summary> Seconds. </summary>
		public float Duration { get; set; }

		/// <summary> The Steam ID of whoever recorded it, so playback starts on their own soldier. </summary>
		public ulong RecordedBy { get; set; }

		/// <summary> Every life in the recording, in the order they spawned. </summary>
		public List<Soldier> Soldiers { get; set; } = new();
	}

	public sealed class MapEntry
	{
		public string Name { get; set; }
		public bool NoOrigin { get; set; }
		public Vector3 Position { get; set; }
		public Rotation Rotation { get; set; } = Rotation.Identity;
		public Vector3 Scale { get; set; } = Vector3.One;
	}

	/// <summary> One life of a player or bot: its root track in the recording, and when it spawned, died and was removed. </summary>
	public sealed class Soldier
	{
		/// <summary> The name of its root track, and of the object playback creates for it. </summary>
		public string Track { get; set; }

		/// <summary> Its body's object under that root, as a path of object names ("Body", "human"), empty for the root. </summary>
		public string Body { get; set; }

		public string Name { get; set; }
		public Team Team { get; set; }
		public bool Bot { get; set; }

		/// <summary> A player's Steam ID, 0 for bots. </summary>
		public ulong SteamId { get; set; }

		/// <summary> Seconds into the recording. </summary>
		public float Spawned { get; set; }

		/// <summary> Seconds into the recording, or -1 if it never died. </summary>
		public float Died { get; set; } = -1f;

		/// <summary> When its body was removed, or -1 if it was still there at the end. </summary>
		public float Removed { get; set; } = -1f;

		public bool IsAliveAt( float time ) => time >= Spawned && (Died < 0f || time < Died) && (Removed < 0f || time < Removed);
		public bool IsPresentAt( float time ) => time >= Spawned && (Removed < 0f || time < Removed);
	}

	/// <summary>
	/// What each life did with its guns, which the recording itself can't show: the first-person gun
	/// (<see cref="TheaterViewModel"/>) plays it. It's a file of its own, as a long match's is hundreds of kilobytes and
	/// the Theater page reads every sidecar.
	/// </summary>
	public sealed class Actions
	{
		/// <summary> Gunsmith build codes (<see cref="Gunsmith.GunsmithLoadoutManager.ExportWeaponBuildCode"/>), which <see cref="Held.Build"/> points into. </summary>
		public List<string> Builds { get; set; } = new();

		/// <summary> By each life's <see cref="Soldier.Track"/>. </summary>
		public Dictionary<string, LifeActions> Lives { get; set; } = new();
	}

	/// <summary>
	/// One life's guns. Times are seconds into the recording. The lists of toggles hold when a state started and stopped,
	/// alternately, so it's on at a time when an odd number of them are at or before it (<see cref="IsOn"/>).
	/// </summary>
	public sealed class LifeActions
	{
		/// <summary> What it had in its hands, from when. </summary>
		public List<Held> Held { get; set; } = new();

		/// <summary> When it fired, or swung a melee weapon. </summary>
		public List<float> Shots { get; set; } = new();

		/// <summary> Aiming down the sights, or a bot shouldering its gun in a fight. </summary>
		public List<float> Aiming { get; set; } = new();

		/// <summary> Null for a bot, whose sprint playback works out from its speed. </summary>
		public List<float> Sprinting { get; set; }

		public List<float> Reloading { get; set; } = new();

		/// <summary> The magazine being empty. Players only. </summary>
		public List<float> Empty { get; set; } = new();

		public static bool IsOn( List<float> toggles, float time ) => toggles is not null && CountUpTo( toggles, time ) % 2 == 1;

		/// <summary> How many of <paramref name="times"/> (in order) are at or before <paramref name="time"/>. </summary>
		public static int CountUpTo( List<float> times, float time )
		{
			if ( times is null )
				return 0;

			int low = 0, high = times.Count;
			while ( low < high )
			{
				var middle = (low + high) / 2;
				if ( times[middle] <= time ) low = middle + 1;
				else high = middle;
			}

			return low;
		}

		/// <summary> What it held at <paramref name="time"/>, as an index into <see cref="Held"/>, or -1 before the first. </summary>
		public int HeldAt( float time )
		{
			int low = 0, high = Held.Count;
			while ( low < high )
			{
				var middle = (low + high) / 2;
				if ( Held[middle].At <= time ) low = middle + 1;
				else high = middle;
			}

			return low - 1;
		}
	}

	public sealed class Held
	{
		public float At { get; set; }

		/// <summary> Its <see cref="EquipmentResource"/>'s path, empty for nothing in its hands. </summary>
		public string Weapon { get; set; } = "";

		/// <summary> Its build, an index into <see cref="Actions.Builds"/>, or -1 for the gun as it comes (a bot's). </summary>
		public int Build { get; set; } = -1;

		/// <summary> Whether its shots were suppressed, which picks its muzzle flash. </summary>
		public bool Suppressed { get; set; }
	}

	public sealed record Entry( string Id, Info Info );

	public static string MoviePath( string id ) => $"{Folder}/{id}.movie";
	public static string InfoPath( string id ) => $"{Folder}/{id}.json";
	public static string ActionsPath( string id ) => $"{Folder}/{id}.actions";

	/// <summary> A new replay's id, from the time it was saved. </summary>
	public static string NewId()
	{
		var id = DateTime.Now.ToString( "yyyyMMdd_HHmmss" );
		var unique = id;

		for ( var i = 2; FileSystem.Data.FileExists( MoviePath( unique ) ) || FileSystem.Data.FileExists( InfoPath( unique ) ); i++ )
			unique = $"{id}_{i}";

		return unique;
	}

	/// <summary> The finished replays, newest first. </summary>
	public static List<Entry> List()
	{
		var list = new List<Entry>();
		if ( !FileSystem.Data.DirectoryExists( Folder ) )
			return list;

		foreach ( var file in FileSystem.Data.FindFile( Folder, "*.json" ) )
		{
			var id = WithoutExtension( file, ".json" );
			if ( id is null || !FileSystem.Data.FileExists( MoviePath( id ) ) )
				continue;

			if ( ReadInfo( id ) is { } info )
				list.Add( new Entry( id, info ) );
		}

		return list.OrderByDescending( x => x.Info.Recorded ).ToList();
	}

	/// <summary> A replay's sidecar, or null if it's missing, unreadable or from another version. </summary>
	public static Info ReadInfo( string id )
	{
		if ( string.IsNullOrWhiteSpace( id ) || !FileSystem.Data.FileExists( InfoPath( id ) ) )
			return null;

		try
		{
			var info = FileSystem.Data.ReadJson<Info>( InfoPath( id ) );
			return info?.Version == CurrentVersion ? info : null;
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: can't read {InfoPath( id )}: {e.Message}" );
			return null;
		}
	}

	public static void Delete( string id )
	{
		if ( string.IsNullOrWhiteSpace( id ) )
			return;

		// Sidecar first, so a half-deleted replay is never listed.
		DeleteFile( InfoPath( id ) );
		DeleteFile( MoviePath( id ) );
		DeleteFile( ActionsPath( id ) );
	}

	/// <summary>
	/// Keeps the newest <see cref="MaxReplays"/> from the last <see cref="MaxAgeDays"/> days. Also deletes recordings
	/// with no sidecar (a crash while saving, or the old Theater's files), once they're an hour old: a replay being
	/// saved right now has no sidecar yet either.
	/// </summary>
	public static void Prune()
	{
		if ( !FileSystem.Data.DirectoryExists( Folder ) )
			return;

		var now = DateTime.Now;
		var kept = 0;

		foreach ( var entry in List() )
		{
			if ( kept >= MaxReplays || (now - entry.Info.Recorded).TotalDays > MaxAgeDays )
			{
				Delete( entry.Id );
				continue;
			}

			kept++;
		}

		foreach ( var file in FileSystem.Data.FindFile( Folder, "*.movie" ).ToList() )
		{
			var id = WithoutExtension( file, ".movie" );
			if ( id is null || FileSystem.Data.FileExists( InfoPath( id ) ) )
				continue;

			if ( TryGetSavedTime( id, out var saved ) && (now - saved).TotalHours < 1 )
				continue;

			DeleteFile( MoviePath( id ) );
		}

		// Sidecars and actions whose recording is gone.
		foreach ( var file in FileSystem.Data.FindFile( Folder, "*.json" ).ToList() )
		{
			var id = WithoutExtension( file, ".json" );
			if ( id is not null && !FileSystem.Data.FileExists( MoviePath( id ) ) )
				DeleteFile( InfoPath( id ) );
		}

		foreach ( var file in FileSystem.Data.FindFile( Folder, "*.actions" ).ToList() )
		{
			var id = WithoutExtension( file, ".actions" );
			if ( id is not null && !FileSystem.Data.FileExists( MoviePath( id ) ) )
				DeleteFile( ActionsPath( id ) );
		}
	}

	/// <summary> When a replay was saved, from its id (<see cref="NewId"/>), or the old Theater's "Map_yyyyMMdd_HHmmss". </summary>
	static bool TryGetSavedTime( string id, out DateTime saved )
	{
		saved = default;
		var parts = id.Split( '_' );

		for ( var i = 0; i + 1 < parts.Length; i++ )
		{
			if ( DateTime.TryParseExact( $"{parts[i]}_{parts[i + 1]}", "yyyyMMdd_HHmmss", null,
				System.Globalization.DateTimeStyles.None, out saved ) )
				return true;
		}

		return false;
	}

	static string WithoutExtension( string file, string extension )
	{
		if ( string.IsNullOrEmpty( file ) || !file.EndsWith( extension, StringComparison.OrdinalIgnoreCase ) )
			return null;

		var id = file[..^extension.Length];
		return id.Length > 0 ? id : null;
	}

	static void DeleteFile( string path )
	{
		try
		{
			if ( FileSystem.Data.FileExists( path ) )
				FileSystem.Data.DeleteFile( path );
		}
		catch ( Exception e )
		{
			Log.Warning( $"Theater: can't delete {path}: {e.Message}" );
		}
	}
}
