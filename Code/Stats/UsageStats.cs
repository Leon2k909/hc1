using System.Text;
using Facepunch.Gunsmith;

namespace Facepunch;

/// <summary>
/// What players pick, so the dev can see which guns, attachments, camos and perks get used (dev_usage). Each life a player
/// spawns with their class counts once, on their own client, when <see cref="PlayerLoadout.ClassSwapWindow"/> has passed,
/// so a class picked just after spawning counts rather than the one they spawned with. Bots, and modes without classes
/// (Gun Game, Zombies), don't count. The stats are s&amp;box's, whose global stats add every player's up:
/// - use-lives: lives counted;
/// - use-gun-&lt;weapon&gt;: lives with the weapon in the class (primary, secondary, lethal or tactical);
/// - use-att-&lt;weapon&gt;-&lt;part&gt;: lives with the attachment on that weapon (parts share file names across weapons);
/// - use-camo-&lt;camo&gt;: lives with the camo on the primary or secondary, or use-camo-none, or use-camo-custom (a custom
///   colour);
/// - use-perk-&lt;perk&gt;: lives with the perk;
/// - use-kill-&lt;weapon&gt;: kills with the weapon in those modes, for kills per life. The older kills-&lt;weapon&gt; counts
///   every mode, and from before these stats.
/// </summary>
public static class UsageStats
{
	/// <summary> The published game, whose global stats dev_usage reads. In the editor Stats.Global is the local package's,
	/// which reads 0. </summary>
	private const string Package = "verarp.razedtest";

	/// <summary> The order <see cref="GunsmithLoadoutManager.ApplyAttachments"/> picks a camo in, when more than one is saved. </summary>
	private static readonly GunsmithPartType[] CamoOrder =
	{
		GunsmithPartType.Camoflague3D, GunsmithPartType.GlowingCamo, GunsmithPartType.AnimatedCamo,
		GunsmithPartType.MasteryCamo, GunsmithPartType.Camoflague
	};

	/// <summary> Owner side, when our pawn spawns (not a bot's): counts the class we have once the swap window has passed. </summary>
	public static async void CountLife()
	{
		try
		{
			await GameTask.DelaySeconds( PlayerLoadout.ClassSwapWindow );

			// Back in the menu, or a mode without classes.
			if ( !PlayerLoadout.ClassesEnabled )
				return;

			Record();
		}
		catch ( Exception e )
		{
			Log.Warning( $"Usage stats: couldn't count a life ({e.Message})" );
		}
	}

	/// <summary> Owner side, for a kill of ours with <paramref name="weapon"/>. </summary>
	public static void CountKill( EquipmentResource weapon )
	{
		if ( weapon.IsValid() && PlayerLoadout.ClassesEnabled )
			Stats.Increment( $"use-kill-{weapon.ResourceName}" );
	}

	private static void Record()
	{
		Stats.Increment( "use-lives" );

		foreach ( var weapon in GunsmithLoadoutManager.GetLoadoutResources() )
		{
			Stats.Increment( $"use-gun-{weapon.ResourceName}" );
			if ( weapon.Slot is not (EquipmentSlot.Primary or EquipmentSlot.Secondary) )
				continue;

			foreach ( var category in Enum.GetValues<GunsmithPartType>().Where( AttachmentUnlocks.IsAttachment ) )
			{
				if ( GunsmithLoadoutManager.TryGetAttachment( weapon, category, out var part ) && part.IsValid() )
					Stats.Increment( $"use-att-{weapon.ResourceName}-{part.ResourceName}" );
			}

			Stats.Increment( $"use-camo-{Camo( weapon )}" );
		}

		var classIndex = GunsmithLoadoutManager.GetActiveClassIndex();
		foreach ( var category in Enum.GetValues<PerkCategory>() )
		{
			if ( GunsmithLoadoutManager.GetPerkResource( classIndex, (int)category ) is { } perk )
				Stats.Increment( $"use-perk-{perk.ResourceName}" );
		}
	}

	/// <summary> The camo the weapon wears: a custom colour over any camo part, as ApplyAttachments paints it. </summary>
	private static string Camo( EquipmentResource weapon )
	{
		if ( GunsmithLoadoutManager.GetUseCustomCamoColor( weapon ) && GunsmithLoadoutManager.GetCustomCamoColor( weapon ).a > 0.001f )
			return "custom";

		foreach ( var category in CamoOrder )
		{
			if ( GunsmithLoadoutManager.TryGetAttachment( weapon, category, out var camo ) && camo.IsValid() )
				return camo.ResourceName;
		}

		return "none";
	}

	/// <summary>
	/// Prints what players pick, every player's added up, from the published game's global stats: each gun's share of
	/// lives and kills per life, the attachments by their share of the gun's lives, and the camos and perks. Writes it to
	/// usage.csv in the game's data folder too, for a spreadsheet. <paramref name="filter"/> keeps only the rows whose gun
	/// or part name has it in, e.g. "m4".
	/// </summary>
	[ConCmd( "dev_usage" )]
	public static async void Print( string filter = "" )
	{
		try
		{
			var package = Sandbox.Services.Stats.GetGlobalStats( Package );
			await package.Refresh();

			// Every stat the game has, to tell a fetch that came back empty from one with none of these yet.
			var all = 0;
			var stats = new Dictionary<string, Sandbox.Services.Stats.GlobalStat>( StringComparer.OrdinalIgnoreCase );
			foreach ( var stat in package )
			{
				all++;
				if ( stat.Name?.StartsWith( "use-", StringComparison.OrdinalIgnoreCase ) ?? false )
					stats[stat.Name] = stat;
			}

			Log.Info( Report( stats, all, filter, out var csv ) );
			FileSystem.Data.WriteAllText( "usage.csv", csv );
			Log.Info( "dev_usage: also written to usage.csv in the game's data folder" );
		}
		catch ( Exception e )
		{
			Log.Warning( $"dev_usage: couldn't read the global stats ({e.Message})" );
		}
	}

	private static string Report( Dictionary<string, Sandbox.Services.Stats.GlobalStat> stats, int all, string filter, out string csv )
	{
		double Total( string name ) => stats.TryGetValue( name, out var stat ) ? stat.Sum : 0;
		long Players( string name ) => stats.TryGetValue( name, out var stat ) ? stat.Players : 0;
		bool Shown( params string[] names ) => string.IsNullOrEmpty( filter )
			|| names.Any( x => x?.Contains( filter, StringComparison.OrdinalIgnoreCase ) ?? false );
		string Share( double part, double whole ) => whole > 0 ? $"{100 * part / whole:0.0}%" : "-";

		var lives = Total( "use-lives" );
		var text = new StringBuilder();
		var rows = new StringBuilder( "section,gun,name,category,lives,share,players,kills,kills per life\n" );
		text.AppendLine( $"Usage in {Package}: {lives:0} lives from {Players( "use-lives" )} players ({all} global stats read)" );
		if ( lives <= 0 )
		{
			text.AppendLine( "  Nothing yet: the stats come from the published game, from players' lives in modes with classes." );
			csv = rows.ToString();
			return text.ToString();
		}

		var weapons = ResourceLibrary.GetAll<EquipmentResource>()
			.GroupBy( x => x.ResourceName, StringComparer.OrdinalIgnoreCase )
			.ToDictionary( x => x.Key, x => x.First(), StringComparer.OrdinalIgnoreCase );

		// Guns, most picked first.
		text.AppendLine( "\nGUNS                          lives   of all  players    kills  kills/life" );
		var guns = stats.Keys.Where( x => x.StartsWith( "use-gun-", StringComparison.OrdinalIgnoreCase ) )
			.Select( x => x["use-gun-".Length..] )
			.OrderByDescending( x => Total( $"use-gun-{x}" ) )
			.ToList();
		foreach ( var gun in guns )
		{
			var name = weapons.TryGetValue( gun, out var weapon ) ? weapon.Name : gun;
			if ( !Shown( gun, name ) ) continue;

			var picked = Total( $"use-gun-{gun}" );
			var kills = Total( $"use-kill-{gun}" );
			text.AppendLine( $"  {name,-26} {picked,7:0} {Share( picked, lives ),8} {Players( $"use-gun-{gun}" ),8} {kills,8:0} {(picked > 0 ? kills / picked : 0),11:0.00}" );
			rows.AppendLine( $"gun,{Csv( name )},{Csv( name )},{weapon?.Slot},{picked:0},{Share( picked, lives )},{Players( $"use-gun-{gun}" )},{kills:0},{(picked > 0 ? kills / picked : 0):0.00}" );
		}

		// Attachments, under their gun, by their share of the gun's lives.
		text.AppendLine( "\nATTACHMENTS                   lives  of gun's  players" );
		var attachments = stats.Keys.Where( x => x.StartsWith( "use-att-", StringComparison.OrdinalIgnoreCase ) )
			.Select( x => x["use-att-".Length..] )
			.Select( x =>
			{
				// The gun's own name can have a dash in it, so it's the longest gun the stat starts with.
				var gun = guns.Where( g => x.StartsWith( g + "-", StringComparison.OrdinalIgnoreCase ) ).MaxBy( g => g.Length );
				return (Stat: $"use-att-{x}", Gun: gun, Part: gun is null ? x : x[(gun.Length + 1)..]);
			} )
			.OrderByDescending( x => Total( $"use-gun-{x.Gun}" ) )
			.ThenBy( x => x.Gun )
			.ThenByDescending( x => Total( x.Stat ) );
		string lastGun = null;
		foreach ( var (stat, gun, part) in attachments )
		{
			weapons.TryGetValue( gun ?? "", out var weapon );
			var gunName = weapon?.Name ?? gun ?? "?";
			var partResource = ResourceLibrary.GetAll<GunsmithPart>()
				.FirstOrDefault( x => x.ResourceName.Equals( part, StringComparison.OrdinalIgnoreCase ) && (weapon is null || x.Supports( weapon )) );
			var partName = partResource?.Name ?? part;
			if ( !Shown( gun, gunName, part, partName ) ) continue;

			if ( gun != lastGun )
				text.AppendLine( $"  {gunName}" );
			lastGun = gun;

			var picked = Total( stat );
			var category = partResource?.Category.ToString() ?? "";
			text.AppendLine( $"    {$"{partName} ({category})",-26} {picked,7:0} {Share( picked, Total( $"use-gun-{gun}" ) ),9} {Players( stat ),8}" );
			rows.AppendLine( $"attachment,{Csv( gunName )},{Csv( partName )},{category},{picked:0},{Share( picked, Total( $"use-gun-{gun}" ) )},{Players( stat )},," );
		}

		// Camos and perks, most picked first. A camo is counted on the primary and the secondary, so its share is of
		// every gun that could wear one.
		var camoable = stats.Keys.Where( x => x.StartsWith( "use-camo-", StringComparison.OrdinalIgnoreCase ) ).Sum( Total );
		text.AppendLine( "\nCAMOS                         guns   of guns  players" );
		foreach ( var stat in stats.Keys.Where( x => x.StartsWith( "use-camo-", StringComparison.OrdinalIgnoreCase ) ).OrderByDescending( Total ) )
		{
			var camo = stat["use-camo-".Length..];
			var name = camo switch
			{
				"none" => "(none)",
				"custom" => "(custom colour)",
				_ => ResourceLibrary.GetAll<GunsmithPart>().FirstOrDefault( x => x.ResourceName.Equals( camo, StringComparison.OrdinalIgnoreCase ) )?.Name ?? camo
			};
			if ( !Shown( camo, name ) ) continue;

			text.AppendLine( $"  {name,-26} {Total( stat ),7:0} {Share( Total( stat ), camoable ),8} {Players( stat ),8}" );
			rows.AppendLine( $"camo,,{Csv( name )},,{Total( stat ):0},{Share( Total( stat ), camoable )},{Players( stat )},," );
		}

		text.AppendLine( "\nPERKS                         lives   of all  players" );
		foreach ( var stat in stats.Keys.Where( x => x.StartsWith( "use-perk-", StringComparison.OrdinalIgnoreCase ) ).OrderByDescending( Total ) )
		{
			var perk = stat["use-perk-".Length..];
			var resource = PerkResource.All.FirstOrDefault( x => x.ResourceName.Equals( perk, StringComparison.OrdinalIgnoreCase ) );
			var name = resource?.Name ?? perk;
			if ( !Shown( perk, name ) ) continue;

			text.AppendLine( $"  {name,-26} {Total( stat ),7:0} {Share( Total( stat ), lives ),8} {Players( stat ),8}" );
			rows.AppendLine( $"perk,,{Csv( name )},{resource?.Category},{Total( stat ):0},{Share( Total( stat ), lives )},{Players( stat )},," );
		}

		csv = rows.ToString();
		return text.ToString();
	}

	private static string Csv( string value ) => value is null ? "" : $"\"{value.Replace( "\"", "\"\"" )}\"";
}
