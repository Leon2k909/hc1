namespace Facepunch.Gunsmith;

/// <summary>
/// Attachments unlock with the weapon's level (<see cref="WeaponProgression"/>, 1-30), each weapon on its own ladder like
/// CoD's weapon levels. A weapon's parts are dealt out from level 2 to the top level, taking one slot's part at a time
/// in <see cref="SlotOrder"/>, so each level or two opens something for a different slot. Within a slot the plainer parts
/// come first: 1x optics before magnified ones, muzzle devices before suppressors, smaller magazines before bigger ones.
/// The factory part is always there. A part whose <see cref="GunsmithPart.RequiredLevel"/> is above 1 keeps that level
/// on every weapon instead (the M700's long range scope, level 4).
/// <para>Levels are the current weapon level, which prestige resets (<see cref="Progression.EnterPrestigeMode"/>).
/// A saved part that's locked again stays saved, but isn't fitted until it unlocks
/// (<see cref="GunsmithLoadoutManager.TryGetAttachment"/>).</para>
/// <para>Unlock points open a part early: one every <see cref="LevelsPerPoint"/> player levels, spent on any locked
/// attachment for one weapon. A point comes back once that weapon reaches the part's level anyway. The points and what
/// they bought belong to the prestige, like the weapon levels: a new prestige starts both again.</para>
/// </summary>
public static class AttachmentUnlocks
{
	/// <summary> Leon's Steam account (steamcommunity.com/id/leonsnailham): the only one shown the UNLOCK ALL switch. </summary>
	public const ulong DeveloperSteamId = 76561198271608270;

	private const string UnlockAllCookie = "hc1.gunsmith.dev_unlock_all";

	/// <summary> The lowest level a part can unlock at: level 1 is the factory gun. </summary>
	private const int FirstUnlockLevel = 2;

	public static bool IsDeveloper => Game.SteamId == DeveloperSteamId;

	/// <summary> The developer's switch: every attachment and camo unlocked, whatever the weapon's level. </summary>
	public static bool UnlockAll
	{
		get => IsDeveloper && Game.Cookies.Get( UnlockAllCookie, false );
		set
		{
			if ( IsDeveloper )
				Game.Cookies.Set( UnlockAllCookie, value );
		}
	}

	/// <summary> The Build tab's slots, which unlock by level. Camos, charms, stickers and reticles have their own rules. </summary>
	public static bool IsAttachment( GunsmithPartType category ) => category is GunsmithPartType.Muzzle or GunsmithPartType.Barrel
		or GunsmithPartType.Optic or GunsmithPartType.Underbarrel or GunsmithPartType.Stock or GunsmithPartType.RearGrip
		or GunsmithPartType.Magazine or GunsmithPartType.Ammunition or GunsmithPartType.Laser or GunsmithPartType.Rail;

	/// <summary> The order a weapon's slots take turns on its ladder: sights and muzzles first, as in CoD. </summary>
	private static GunsmithPartType[] SlotOrder => new[]
	{
		GunsmithPartType.Optic, GunsmithPartType.Muzzle, GunsmithPartType.Underbarrel, GunsmithPartType.Magazine,
		GunsmithPartType.Stock, GunsmithPartType.RearGrip, GunsmithPartType.Barrel, GunsmithPartType.Laser,
		GunsmithPartType.Ammunition, GunsmithPartType.Rail,
	};

	public static bool IsUnlocked( EquipmentResource weapon, GunsmithPart part )
	{
		if ( part is null || !IsAttachment( part.Category ) || UnlockAll )
			return true;
		if ( weapon is null )
			return false;
		return IsLevelUnlocked( weapon, part ) || Bought.Contains( BoughtKey( weapon, part ) );
	}

	/// <summary> Whether <paramref name="weapon"/>'s level has reached <paramref name="part"/>'s, points aside. </summary>
	private static bool IsLevelUnlocked( EquipmentResource weapon, GunsmithPart part ) =>
		WeaponProgression.GetLevel( weapon ) >= GetRequiredLevel( weapon, part );

	/// <summary> Whether <paramref name="part"/> is open on <paramref name="weapon"/> only because a point was spent on it. </summary>
	public static bool IsUnlockedByPoint( EquipmentResource weapon, GunsmithPart part ) =>
		weapon is not null && part is not null && IsAttachment( part.Category ) && !UnlockAll
		&& !IsLevelUnlocked( weapon, part ) && Bought.Contains( BoughtKey( weapon, part ) );

	/// <summary> The weapon level <paramref name="part"/> unlocks at on <paramref name="weapon"/> (1: from the start). </summary>
	public static int GetRequiredLevel( EquipmentResource weapon, GunsmithPart part )
	{
		if ( part is null || !IsAttachment( part.Category ) )
			return 1;
		if ( part.RequiredLevel > 1 )
			return Math.Min( part.RequiredLevel, WeaponProgression.MaxLevel );
		if ( weapon is null )
			return 1;
		return GetLadder( weapon ).TryGetValue( part.ResourcePath ?? "", out var level ) ? level : 1;
	}

	/// <summary> The attachments <paramref name="weapon"/> unlocks at <paramref name="level"/>. </summary>
	public static IEnumerable<GunsmithPart> GetUnlocksAt( EquipmentResource weapon, int level ) => weapon is null
		? Enumerable.Empty<GunsmithPart>()
		: GetWeaponParts( weapon ).Where( p => GetRequiredLevel( weapon, p ) == level );

	/// <summary> The weapon's slots that take attachments: its prefab's attachment points, plus ammunition when a part fits. </summary>
	public static HashSet<GunsmithPartType> GetSlots( EquipmentResource weapon )
	{
		var slots = new HashSet<GunsmithPartType>();
		if ( weapon is null )
			return slots;

		if ( weapon.ViewModelPrefab.IsValid() )
		{
			foreach ( var point in weapon.ViewModelPrefab.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( IsAttachment( point.Category ) )
					slots.Add( point.Category );
			}
		}

		// GunsmithLoadoutManager.ApplyAttachments adds an ammunition slot to every gun an ammunition part fits.
		slots.Add( GunsmithPartType.Ammunition );
		return slots;
	}

	/// <summary> The parts the gunsmith offers <paramref name="weapon"/>, in every slot it has. </summary>
	public static IEnumerable<GunsmithPart> GetWeaponParts( EquipmentResource weapon )
	{
		if ( weapon is null )
			return Enumerable.Empty<GunsmithPart>();

		var slots = GetSlots( weapon );
		return ResourceLibrary.GetAll<GunsmithPart>().Where( p => p.IsValid() && slots.Contains( p.Category ) && IsOffered( p ) && p.Supports( weapon ) );
	}

	/// <summary> GunsmithAttachmentBrowser's rule: a part with something to fit, a prefab or bodygroups (ammunition has neither). </summary>
	public static bool IsOffered( GunsmithPart part ) =>
		part.MainPrefab.IsValid() || part.ModifyBodygroups || part.Category == GunsmithPartType.Ammunition;

	/// <summary> Player levels per unlock point: one at level 5, 10, 15 and so on, 11 by the top level. </summary>
	public const int LevelsPerPoint = 5;

	/// <summary> The points the player's level has earned this prestige. </summary>
	public static int EarnedPoints => Progression.GetLevel() / LevelsPerPoint;

	/// <summary> The points tied up in parts that their weapon's level hasn't reached yet. </summary>
	public static int SpentPoints => Bought.Count( IsStillAhead );

	public static int AvailablePoints => Math.Max( 0, EarnedPoints - SpentPoints );

	/// <summary> The player level that earns the next point, or null past the last one. </summary>
	public static int? NextPointLevel
	{
		get
		{
			var level = (EarnedPoints + 1) * LevelsPerPoint;
			return level <= Progression.MaxLevel ? level : null;
		}
	}

	/// <summary>
	/// Spends a point to unlock <paramref name="part"/> on <paramref name="weapon"/> now. False if it's open already, isn't an
	/// attachment, or there's no point to spend.
	/// </summary>
	public static bool TrySpendPoint( EquipmentResource weapon, GunsmithPart part )
	{
		if ( weapon is null || part is null || !IsAttachment( part.Category ) || IsUnlocked( weapon, part ) || AvailablePoints <= 0 )
			return false;

		var bought = Bought;
		bought.Add( BoughtKey( weapon, part ) );
		Game.Cookies.Set( _boughtCookie, string.Join( ";", bought ) );
		return true;
	}

	/// <summary> What points bought this prestige: "weapon path|part path" pairs, kept after the weapon catches up. </summary>
	private static string BoughtCookie => $"hc1.gunsmith.point_unlocks.p{Progression.GetPrestige()}";

	private static string _boughtCookie;
	private static HashSet<string> _bought;

	private static HashSet<string> Bought
	{
		get
		{
			var cookie = BoughtCookie;
			if ( _bought is null || _boughtCookie != cookie )
			{
				_boughtCookie = cookie;
				_bought = new HashSet<string>( (Game.Cookies.Get<string>( cookie, "" ) ?? "").Split( ';', StringSplitOptions.RemoveEmptyEntries ),
					StringComparer.OrdinalIgnoreCase );
			}

			return _bought;
		}
	}

	private static string BoughtKey( EquipmentResource weapon, GunsmithPart part ) => $"{weapon.ResourcePath}|{part.ResourcePath}";

	/// <summary> Whether a bought part still holds its point: it and its weapon exist, and the weapon's level is short of it. </summary>
	private static bool IsStillAhead( string key )
	{
		var split = key.IndexOf( '|' );
		if ( split <= 0 )
			return false;

		var weapon = ResourceLibrary.Get<EquipmentResource>( key[..split] );
		var part = ResourceLibrary.Get<GunsmithPart>( key[(split + 1)..] );
		return weapon is not null && part is not null && !IsLevelUnlocked( weapon, part );
	}

	private sealed record Ladder( Dictionary<string, int> Levels, RealTimeSince Built );

	private static readonly Dictionary<string, Ladder> _ladders = new( StringComparer.OrdinalIgnoreCase );

	/// <summary> Part path to unlock level for <paramref name="weapon"/>, rebuilt now and then so new or changed parts show up. </summary>
	private static Dictionary<string, int> GetLadder( EquipmentResource weapon )
	{
		var key = weapon.ResourcePath ?? "";
		if ( _ladders.TryGetValue( key, out var cached ) && cached.Built < 5f )
			return cached.Levels;

		var levels = BuildLadder( weapon );
		_ladders[key] = new Ladder( levels, 0f );
		return levels;
	}

	private static Dictionary<string, int> BuildLadder( EquipmentResource weapon )
	{
		// Each slot's parts, plainest first; parts with a level of their own sit out of the deal.
		var queues = GetWeaponParts( weapon )
			.Where( p => p.RequiredLevel <= 1 )
			.GroupBy( p => p.Category )
			.ToDictionary( g => g.Key, g => new Queue<GunsmithPart>( g
				.OrderBy( Tier )
				.ThenBy( p => p.Name, StringComparer.OrdinalIgnoreCase )
				.ThenBy( p => p.ResourcePath, StringComparer.OrdinalIgnoreCase ) ) );

		// Deal: one part from each slot in turn, until every slot is empty.
		var sequence = new List<GunsmithPart>();
		var order = SlotOrder.Concat( queues.Keys ).Distinct().ToArray();
		while ( queues.Values.Any( q => q.Count > 0 ) )
		{
			foreach ( var slot in order )
			{
				if ( queues.TryGetValue( slot, out var queue ) && queue.Count > 0 )
					sequence.Add( queue.Dequeue() );
			}
		}

		// Spread the deal evenly over levels 2 to the top level.
		var levels = new Dictionary<string, int>( StringComparer.OrdinalIgnoreCase );
		var span = WeaponProgression.MaxLevel - FirstUnlockLevel + 1;
		for ( var i = 0; i < sequence.Count; i++ )
			levels[sequence[i].ResourcePath ?? ""] = FirstUnlockLevel + i * span / sequence.Count;
		return levels;
	}

	/// <summary> How far down its slot's list a part sits: the plainer and cheaper-feeling parts come first. </summary>
	private static float Tier( GunsmithPart part ) => part.Category switch
	{
		GunsmithPartType.Optic => part.OpticMagnification,
		GunsmithPartType.Muzzle or GunsmithPartType.Barrel => part.IsSuppressor ? 1f : 0f,
		GunsmithPartType.Magazine => part.MagazineCapacity,
		_ => 0f,
	};
}
