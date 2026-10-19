using System.Text;
using System.Text.Json;

namespace Facepunch.Gunsmith;

/// <summary>
/// Stores the player's preferred weapons chosen in the gunsmith.
/// Persists via Game.Cookies so it survives sessions.
/// </summary>
public static class GunsmithLoadoutManager
{
	private const string WeaponBuildCodePrefix = "HC1W1-";
	public const int MaxSharedBuildCodeLength = 16384;

	/// <summary>
	/// Bumped by everything that can change which part <see cref="TryGetAttachment"/> returns: an attachment, the active
	/// class or an optic's tune saved, a part unlocked (a weapon level, a point, a prestige, UNLOCK ALL) or a part loaded.
	/// Every shot asks for most of the gun's slots, so the answers, and what the guns work out from them
	/// (<see cref="GunsmithAttachmentEffects.For"/>, <see cref="Equipment.RefreshAmmunitionLoadout"/>), are kept until
	/// it changes, and a shot reads no cookies.
	/// </summary>
	public static int Version { get; private set; }

	/// <summary> Throws away every kept answer (<see cref="Version"/>). </summary>
	public static void MarkChanged()
	{
		Version++;
		Fitted.Clear();
	}

	/// <summary> A build is being fitted (<see cref="ApplyBuild"/>, <see cref="TryReadWithBuild{T}"/>): nothing read now is the saved loadout. </summary>
	internal static bool IsFittingBuild => _fitting is not null;

	/// <summary> <see cref="TryGetAttachment"/>'s answers since the last <see cref="MarkChanged"/>. </summary>
	private static readonly Dictionary<(EquipmentResource, GunsmithPartType), (bool Found, GunsmithPart Part)> Fitted = new();

	public static int GetActiveClassIndex() => Game.Cookies.Get<int>( "hc1.loadout.active_class", 0 );
	public static void SetActiveClassIndex( int index )
	{
		Game.Cookies.Set( "hc1.loadout.active_class", index );
		MarkChanged();
	}

	public static List<int> GetActiveClassIndices()
	{
		var str = Game.Cookies.Get<string>( "hc1.loadout.class_indices", "0,1,2,3,4" );
		if ( string.IsNullOrEmpty( str ) ) return new List<int> { 0, 1, 2, 3, 4 };
		return str.Split( ',' ).Select( int.Parse ).ToList();
	}

	private static void SetActiveClassIndices( List<int> indices )
	{
		Game.Cookies.Set( "hc1.loadout.class_indices", string.Join( ",", indices ) );
	}

	public static void CreateNewClass()
	{
		var indices = GetActiveClassIndices();
		if ( indices.Count >= 10 ) return;

		int newIdx = indices.Count > 0 ? indices.Max() + 1 : 0;
		indices.Add( newIdx );
		SetActiveClassIndices( indices );
		SetClassName( newIdx, $"CUSTOM {indices.Count}" );
		SetActiveClassIndex( newIdx );
	}

	public static void DeleteClass( int index )
	{
		var indices = GetActiveClassIndices();
		if ( indices.Count <= 1 ) return; // Prevent deleting last class

		if ( indices.Remove( index ) )
		{
			SetActiveClassIndices( indices );
			
			// Select another class if we deleted the active one
			if ( GetActiveClassIndex() == index )
			{
				SetActiveClassIndex( indices[0] );
			}
		}
	}

	private static string PrimaryCookieKey => $"hc1.loadout.class{GetActiveClassIndex()}.primary";
	private static string SecondaryCookieKey => $"hc1.loadout.class{GetActiveClassIndex()}.secondary";
	private static string TacticalCookieKey => $"hc1.loadout.class{GetActiveClassIndex()}.tactical";
	private static string LethalCookieKey => $"hc1.loadout.class{GetActiveClassIndex()}.lethal";

	private static string NoneAttachmentValue = "__none";

	/// <summary>
	/// The primary of a class that hasn't picked one, so every class spawns with a gun. The gunsmith scene previews it
	/// for such classes too.
	/// </summary>
	public const string DefaultPrimaryResourceName = "weapons/m4a1/m4a1.equip";
	public const string UspResourceName = "weapons/usp/usp.equip";
	public const string LegacyUspSResourceName = "weapons/usp_sd/usp_sd.equip";
	public const string UspSuppressorResourceName = "gunsmith/usp/barrel/usp_suppressor.gnsmth";

	/// <summary>
	/// Returns the ResourceName of the player's chosen primary, or <see cref="DefaultPrimaryResourceName"/> if unset.
	/// </summary>
	public static string GetPrimary()
	{
		var v = Game.Cookies.Get<string>( PrimaryCookieKey, "" );
		return string.IsNullOrEmpty( v ) ? DefaultPrimaryResourceName : v;
	}

	public static bool GetCamoOnOptics() => _fitting?.CamoOnOptics
		?? Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.camoonoptics", false );

	public static bool GetEmblemOnGun( EquipmentResource resource ) => _fitting?.EmblemOnGun
		?? Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.emblemOnGun", false );
	public static void SetEmblemOnGun( EquipmentResource resource, bool value ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.emblemOnGun", value );

	private static readonly string[] DefaultClassNames = { "ASSAULT", "SNIPER", "SUPPORT", "STEALTH", "CUSTOM" };

	public static string GetClassName( int idx ) =>
		Game.Cookies.Get<string>( $"hc1.gunsmith.class{idx}.name",
			idx >= 0 && idx < DefaultClassNames.Length ? DefaultClassNames[idx] : $"CLASS {idx + 1}" );

	public static void SetClassName( int idx, string name ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{idx}.name", name );
	public static void SetCamoOnOptics( bool value ) => Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.camoonoptics", value );

	public static bool IsFavorite( string resourcePath ) => Game.Cookies.Get<bool>( $"hc1.gunsmith.favorite.{resourcePath}", false );
	public static void SetFavorite( string resourcePath, bool isFavorite ) => Game.Cookies.Set( $"hc1.gunsmith.favorite.{resourcePath}", isFavorite );

	public static bool GetUseCustomCamoColor( EquipmentResource resource ) => _fitting?.UseCustomCamo
		?? Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomcamo", false );

	public static void SetUseCustomCamoColor( EquipmentResource resource, bool value ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomcamo", value );

	public static Color GetCustomCamoColor( EquipmentResource resource )
	{
		if ( _fitting is { } build )
		{
			var opacity = build.CustomCamoOpacity.Clamp( 0f, 1f );
			return Color.TryParse( build.CustomCamo ?? "", out var color ) ? color.WithAlpha( opacity ) : Color.White.WithAlpha( opacity );
		}

		var val = Game.Cookies.Get<string>( CustomCamoColorKey( resource ), "" );
		if ( string.IsNullOrEmpty( val ) )
			return Color.White.WithAlpha( Game.Cookies.Get<float>( CustomCamoOpacityKey( resource ), 1f ).Clamp( 0f, 1f ) );

		if ( Color.TryParse( val, out var col ) )
			return col.WithAlpha( Game.Cookies.Get<float>( CustomCamoOpacityKey( resource ), col.a ).Clamp( 0f, 1f ) );

		return Color.White;
	}

	public static void SetCustomCamoColor( EquipmentResource resource, Color color )
	{
		Game.Cookies.Set( CustomCamoColorKey( resource ), color.Hex );
		Game.Cookies.Set( CustomCamoOpacityKey( resource ), color.a.Clamp( 0f, 1f ) );
	}

	public static bool GetUseCustomAnimatedCamoSpeed( EquipmentResource resource ) => _fitting?.UseCustomAnimatedSpeed
		?? Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomanimationspeed", false );

	public static void SetUseCustomAnimatedCamoSpeed( EquipmentResource resource, bool value ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomanimationspeed", value );

	public static Vector2 GetCustomAnimatedCamoSpeed( EquipmentResource resource )
	{
		if ( _fitting is { } build )
			return new Vector2( build.CustomAnimatedSpeedX, build.CustomAnimatedSpeedY );

		var valX = Game.Cookies.Get<float>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.animationspeedx", 0.0f );
		var valY = Game.Cookies.Get<float>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.animationspeedy", 0.0f );
		return new Vector2( valX, valY );
	}

	public static void SetCustomAnimatedCamoSpeed( EquipmentResource resource, Vector2 speed )
	{
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.animationspeedx", speed.x );
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.animationspeedy", speed.y );
	}

	/// <summary>0 = Matte, 1 = Semi-Gloss, 2 = Gloss, 3 = Chrome</summary>
	public static int GetCustomCamoFinish( EquipmentResource resource ) => _fitting?.CustomCamoFinish
		?? Game.Cookies.Get<int>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.camofinish", 1 );

	public static void SetCustomCamoFinish( EquipmentResource resource, int finish ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.camofinish", finish );

	public static readonly string[] FinishNames = { "Matte", "Semi-Gloss", "Gloss", "Chrome" };
	public static readonly float[] FinishMetalness = { 0.0f, 0.15f, 0.6f, 1.0f };
	public static readonly float[] FinishRoughness = { 0.85f, 0.55f, 0.2f, 0.05f };

	private static string CustomCamoColorKey( EquipmentResource resource ) =>
		$"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.customcamo";

	private static string CustomCamoOpacityKey( EquipmentResource resource ) =>
		$"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.customcamoopacity";

	public static Color GetCustomReticleColor( EquipmentResource resource )
	{
		var val = _fitting is { } build ? build.ReticleColor
			: Game.Cookies.Get<string>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.reticlecolor", "" );
		if ( string.IsNullOrEmpty( val ) ) return Color.Red;
		if ( Color.TryParse( val, out var col ) ) return col;
		return Color.Red;
	}

	public static void SetCustomReticleColor( EquipmentResource resource, Color color ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.reticlecolor", color.Hex );

	private static string ReticleSettingKey( EquipmentResource resource, string setting ) =>
		$"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.reticle{setting}";

	public static float GetCustomReticleScale( EquipmentResource resource ) =>
		(_fitting?.ReticleScale ?? Game.Cookies.Get<float>( ReticleSettingKey( resource, "scale" ), 1f )).Clamp( 0.25f, 3f );

	public static void SetCustomReticleScale( EquipmentResource resource, float scale ) =>
		Game.Cookies.Set( ReticleSettingKey( resource, "scale" ), scale.Clamp( 0.25f, 3f ) );

	public static float GetCustomReticleRotation( EquipmentResource resource ) =>
		(_fitting?.ReticleRotation ?? Game.Cookies.Get<float>( ReticleSettingKey( resource, "rotation" ), 0f )).Clamp( -180f, 180f );

	public static void SetCustomReticleRotation( EquipmentResource resource, float degrees ) =>
		Game.Cookies.Set( ReticleSettingKey( resource, "rotation" ), degrees.Clamp( -180f, 180f ) );

	/// <summary>Reticle position in lens UV units, limited to eight percent from centre on each axis.</summary>
	public static Vector2 GetCustomReticleOffset( EquipmentResource resource ) => new(
		(_fitting?.ReticleOffsetX ?? Game.Cookies.Get<float>( ReticleSettingKey( resource, "offsetx" ), 0f )).Clamp( -0.08f, 0.08f ),
		(_fitting?.ReticleOffsetY ?? Game.Cookies.Get<float>( ReticleSettingKey( resource, "offsety" ), 0f )).Clamp( -0.08f, 0.08f ) );

	public static void SetCustomReticleOffset( EquipmentResource resource, Vector2 offset )
	{
		Game.Cookies.Set( ReticleSettingKey( resource, "offsetx" ), offset.x.Clamp( -0.08f, 0.08f ) );
		Game.Cookies.Set( ReticleSettingKey( resource, "offsety" ), offset.y.Clamp( -0.08f, 0.08f ) );
	}

	/// <summary>An optic's tune is kept per weapon and per optic, as each sight is set up on its own gun.</summary>
	private static string OpticTuneKey( EquipmentResource resource, GunsmithPart optic, string setting ) =>
		$"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.optic.{optic.ResourcePath}.{setting}";

	/// <summary>
	/// The optic's tuned Eye Position (<see cref="OpticTuning"/>): Picatinny slots along the rail from where it mounts,
	/// forward positive. 0 for an optic that doesn't take tuning.
	/// </summary>
	public static int GetOpticEyePosition( EquipmentResource resource, GunsmithPart optic )
	{
		if ( !resource.IsValid() || !OpticTuning.IsTunable( optic ) ) return 0;
		var slots = _fitting is { } build
			? (build.Attachments?.GetValueOrDefault( nameof( GunsmithPartType.Optic ) ) ?? "")
				.Equals( optic.ResourcePath, StringComparison.OrdinalIgnoreCase ) ? build.OpticEye : 0
			: Game.Cookies.Get<int>( OpticTuneKey( resource, optic, "eye" ), 0 );
		return OpticTuning.ClampSlots( resource, slots );
	}

	public static void SetOpticEyePosition( EquipmentResource resource, GunsmithPart optic, int slots )
	{
		if ( !resource.IsValid() || !OpticTuning.IsTunable( optic ) ) return;
		Game.Cookies.Set( OpticTuneKey( resource, optic, "eye" ), OpticTuning.ClampSlots( resource, slots ) );
		MarkChanged();
	}

	/// <summary>
	/// The optic's tuned zero in metres (<see cref="OpticTuning.ZeroChoices"/>), or 0 for the gun's own
	/// (<see cref="Shootable.ZeroRange"/>).
	/// </summary>
	public static int GetOpticZero( EquipmentResource resource, GunsmithPart optic )
	{
		if ( !resource.IsValid() || !OpticTuning.IsTunable( optic ) ) return 0;
		var zero = _fitting is { } build
			? (build.Attachments?.GetValueOrDefault( nameof( GunsmithPartType.Optic ) ) ?? "")
				.Equals( optic.ResourcePath, StringComparison.OrdinalIgnoreCase ) ? build.OpticZero : 0
			: Game.Cookies.Get<int>( OpticTuneKey( resource, optic, "zero" ), 0 );
		return Math.Clamp( zero, 0, OpticTuning.Zeros[^1] );
	}

	public static void SetOpticZero( EquipmentResource resource, GunsmithPart optic, int metres )
	{
		if ( !resource.IsValid() || !OpticTuning.IsTunable( optic ) ) return;
		Game.Cookies.Set( OpticTuneKey( resource, optic, "zero" ), Math.Clamp( metres, 0, OpticTuning.Zeros[^1] ) );
		MarkChanged();
	}

	/// <summary>
	/// Saves <paramref name="resourceName"/> as the preferred primary.
	/// </summary>
	public static void SetPrimary( string resourceName ) =>
		Game.Cookies.Set( PrimaryCookieKey, resourceName ?? "" );

	public static string GetSecondary()
	{
		var v = Game.Cookies.Get<string>( SecondaryCookieKey, "" );
		if ( IsLegacyMergedResourceName( v ) )
		{
			MigrateLegacyUspSLoadout();
			return UspResourceName;
		}

		return string.IsNullOrEmpty( v ) ? null : v;
	}

	public static void SetSecondary( string resourceName )
	{
		if ( IsLegacyMergedResourceName( resourceName ) )
		{
			MigrateLegacyUspSLoadout();
			return;
		}

		Game.Cookies.Set( SecondaryCookieKey, resourceName ?? "" );
	}

	public static string GetTactical()
	{
		var v = Game.Cookies.Get<string>( TacticalCookieKey, "" );
		return string.IsNullOrEmpty( v ) ? null : v;
	}

	public static void SetTactical( string resourceName ) =>
		Game.Cookies.Set( TacticalCookieKey, resourceName ?? "" );

	public static string GetLethal()
	{
		var v = Game.Cookies.Get<string>( LethalCookieKey, "" );
		return string.IsNullOrEmpty( v ) ? null : v;
	}

	public static void SetLethal( string resourceName ) =>
		Game.Cookies.Set( LethalCookieKey, resourceName ?? "" );

	public static string GetPerk( int category )
	{
		var v = Game.Cookies.Get<string>( $"hc1.loadout.class{GetActiveClassIndex()}.perk{category}", "" );
		return string.IsNullOrEmpty( v ) ? null : v;
	}

	public static void SetPerk( int category, string resourceName ) =>
		Game.Cookies.Set( $"hc1.loadout.class{GetActiveClassIndex()}.perk{category}", resourceName ?? "" );

	/// <summary>
	/// The perk a class has in <paramref name="category"/>, or null. Reads any class, not just the active one.
	/// </summary>
	public static PerkResource GetPerkResource( int classIndex, int category )
	{
		var value = Game.Cookies.Get<string>( $"hc1.loadout.class{classIndex}.perk{category}", "" );
		if ( string.IsNullOrEmpty( value ) ) return null;

		return PerkResource.All.FirstOrDefault( x => x.ResourcePath.Equals( value, StringComparison.OrdinalIgnoreCase )
		                                             || x.ResourceName.Equals( value, StringComparison.OrdinalIgnoreCase )
		                                             || x.Name.Equals( value, StringComparison.OrdinalIgnoreCase ) );
	}

	public static bool IsMergedWeaponResource( EquipmentResource resource ) =>
		resource.IsValid() && IsLegacyMergedResourceName( resource.ResourcePath );

	public static string GetSlot( EquipmentSlot slot ) => slot switch
	{
		EquipmentSlot.Primary => GetPrimary(),
		EquipmentSlot.Secondary => GetSecondary(),
		EquipmentSlot.Tactical => GetTactical(),
		EquipmentSlot.Lethal => GetLethal(),
		_ => null
	};

	/// <summary>
	/// What a class has in <paramref name="slot"/> (a resource path or name), or null. Reads any class, not just the
	/// active one, e.g. for the in-match class picker.
	/// </summary>
	public static string GetSlot( int classIndex, EquipmentSlot slot )
	{
		var key = ClassSlotCookieKey( classIndex, slot );
		if ( key is null ) return null;

		var value = Game.Cookies.Get<string>( key, "" );
		if ( IsLegacyMergedResourceName( value ) ) return UspResourceName;
		if ( string.IsNullOrEmpty( value ) ) return slot == EquipmentSlot.Primary ? DefaultPrimaryResourceName : null;
		return value;
	}

	/// <summary>
	/// Puts <paramref name="resourceName"/> (null for nothing) in a class's slot. Writes any class, not just the active
	/// one, e.g. for editing classes from the in-match class picker.
	/// </summary>
	public static void SetSlot( int classIndex, EquipmentSlot slot, string resourceName )
	{
		var key = ClassSlotCookieKey( classIndex, slot );
		if ( key is not null )
			Game.Cookies.Set( key, resourceName ?? "" );
	}

	/// <summary>
	/// Puts a perk (null for none) in a class's perk <paramref name="category"/>. Writes any class, not just the active one.
	/// </summary>
	public static void SetPerk( int classIndex, int category, string resourceName ) =>
		Game.Cookies.Set( $"hc1.loadout.class{classIndex}.perk{category}", resourceName ?? "" );

	private static string ClassSlotCookieKey( int classIndex, EquipmentSlot slot ) => slot switch
	{
		EquipmentSlot.Primary => $"hc1.loadout.class{classIndex}.primary",
		EquipmentSlot.Secondary => $"hc1.loadout.class{classIndex}.secondary",
		EquipmentSlot.Tactical => $"hc1.loadout.class{classIndex}.tactical",
		EquipmentSlot.Lethal => $"hc1.loadout.class{classIndex}.lethal",
		_ => null
	};

	/// <summary>
	/// What a class can put in <paramref name="slot"/>: every weapon or piece of equipment made for it, by category then name.
	/// </summary>
	public static IEnumerable<EquipmentResource> GetSlotChoices( EquipmentSlot slot ) => ResourceLibrary.GetAll<EquipmentResource>()
		.Where( x => x.Slot == slot && x.MainPrefab.IsValid() && x.ViewModelPrefab.IsValid() && !IsMergedWeaponResource( x ) )
		.OrderBy( x => x.Category )
		.ThenBy( x => x.Name );

	public static void SetSlot( EquipmentSlot slot, string resourceName )
	{
		switch ( slot )
		{
			case EquipmentSlot.Primary:
				SetPrimary( resourceName );
				break;
			case EquipmentSlot.Secondary:
				SetSecondary( resourceName );
				break;
			case EquipmentSlot.Tactical:
				SetTactical( resourceName );
				break;
			case EquipmentSlot.Lethal:
				SetLethal( resourceName );
				break;
		}
	}

	/// <summary>
	/// Returns the EquipmentResource for the saved primary, or null if unresolvable.
	/// </summary>
	public static EquipmentResource GetPrimaryResource() =>
		GetSlotResource( EquipmentSlot.Primary );

	public static EquipmentResource GetSecondaryResource() =>
		GetSlotResource( EquipmentSlot.Secondary );

	public static EquipmentResource GetSlotResource( EquipmentSlot slot ) => FindEquipment( GetSlot( slot ) );

	public static EquipmentResource GetSlotResource( int classIndex, EquipmentSlot slot ) => FindEquipment( GetSlot( classIndex, slot ) );

	private static EquipmentResource FindEquipment( string value )
	{
		if ( string.IsNullOrEmpty( value ) )
			return null;

		return ResourceLibrary.GetAll<EquipmentResource>()
			.FirstOrDefault( r => r.ResourcePath.Equals( value, StringComparison.OrdinalIgnoreCase )
			                     || r.ResourceName.Equals( value, StringComparison.OrdinalIgnoreCase ) );
	}

	/// <summary>
	/// The slots a class fills, in the order they're given out.
	/// </summary>
	public static EquipmentSlot[] ClassSlots => new[] { EquipmentSlot.Primary, EquipmentSlot.Secondary, EquipmentSlot.Lethal, EquipmentSlot.Tactical };

	public static IEnumerable<EquipmentResource> GetLoadoutResources()
	{
		foreach ( var slot in ClassSlots )
		{
			var resource = GetSlotResource( slot );
			if ( resource.IsValid() )
				yield return resource;
		}
	}

	public static IEnumerable<EquipmentResource> GetLoadoutResources( int classIndex )
	{
		foreach ( var slot in ClassSlots )
		{
			var resource = GetSlotResource( classIndex, slot );
			if ( resource.IsValid() )
				yield return resource;
		}
	}

	public static void SetAttachment( EquipmentResource resource, GunsmithPartType category, GunsmithPart part )
	{
		if ( !resource.IsValid() )
			return;

		Game.Cookies.Set( AttachmentCookieKey( resource.ResourcePath, category ), part?.ResourcePath ?? NoneAttachmentValue );
		MarkChanged();
	}

	public static bool HasAttachment( EquipmentResource resource, GunsmithPart part )
	{
		if ( !resource.IsValid() || !part.IsValid() )
			return false;

		return TryGetAttachment( resource, part.Category, out var equippedPart )
		       && equippedPart.IsValid()
		       && (equippedPart.ResourcePath.Equals( part.ResourcePath, StringComparison.OrdinalIgnoreCase )
		           || equippedPart.ResourceName.Equals( part.ResourceName, StringComparison.OrdinalIgnoreCase ));
	}

	/// <summary>Read only for the local shooter's loadout; observers receive the shot effect over RPC.</summary>
	public static bool UsesTracerRounds( EquipmentResource resource ) =>
		TryGetAttachment( resource, GunsmithPartType.Ammunition, out var ammo )
		&& ammo.IsValid() && ammo.UsesTracerRounds;

	/// <summary>
	/// The weapon's build in the active class as a build code. A shared code leaves out the parts its level hasn't
	/// unlocked, as they're not on the gun; <paramref name="withLockedParts"/> keeps them, for a saved build
	/// (<see cref="GunsmithPresets"/>), which should come back whole once they unlock.
	/// </summary>
	public static string ExportWeaponBuildCode( EquipmentResource resource, bool withLockedParts = false )
	{
		if ( !resource.IsValid() )
			return "";

		var payload = new SharedWeaponBuild()
		{
			Version = 1,
			Weapon = resource.ResourcePath,
			Attachments = new Dictionary<string, string>(),
			CamoOnOptics = GetCamoOnOptics(),
			EmblemOnGun = GetEmblemOnGun( resource ),
			UseCustomCamo = GetUseCustomCamoColor( resource ),
			CustomCamo = GetCustomCamoColor( resource ).Hex,
			CustomCamoOpacity = GetCustomCamoColor( resource ).a.Clamp( 0f, 1f ),
			CustomCamoFinish = GetCustomCamoFinish( resource ),
			UseCustomAnimatedSpeed = GetUseCustomAnimatedCamoSpeed( resource ),
			CustomAnimatedSpeedX = GetCustomAnimatedCamoSpeed( resource ).x,
			CustomAnimatedSpeedY = GetCustomAnimatedCamoSpeed( resource ).y,
			ReticleColor = GetCustomReticleColor( resource ).Hex,
			ReticleScale = GetCustomReticleScale( resource ),
			ReticleRotation = GetCustomReticleRotation( resource ),
			ReticleOffsetX = GetCustomReticleOffset( resource ).x,
			ReticleOffsetY = GetCustomReticleOffset( resource ).y,
		};

		var saved = withLockedParts && _fitting is null;
		bool Fitted( GunsmithPartType category, out GunsmithPart part ) =>
			saved ? TryGetSavedAttachment( resource, category, out part ) : TryGetAttachment( resource, category, out part );

		foreach ( var category in Enum.GetValues<GunsmithPartType>() )
		{
			if ( Fitted( category, out var part ) && part.IsValid() )
				payload.Attachments[category.ToString()] = part.ResourcePath;
		}

		if ( Fitted( GunsmithPartType.Optic, out var optic ) && optic.IsValid() )
		{
			payload.OpticEye = GetOpticEyePosition( resource, optic );
			payload.OpticZero = GetOpticZero( resource, optic );
		}

		var json = JsonSerializer.Serialize( payload );
		return WeaponBuildCodePrefix + EncodeBase64Url( Encoding.UTF8.GetBytes( json ) );
	}

	/// <summary>
	/// A build code for <paramref name="resource"/> with only <paramref name="parts"/> fitted, no camo and the factory
	/// reticle, for <see cref="ApplyBuild"/>: a bot's issued gun (a suppressor, say), whatever the local loadout holds.
	/// </summary>
	public static string BuildCode( EquipmentResource resource, params GunsmithPart[] parts )
	{
		var payload = new SharedWeaponBuild { Version = 1, Weapon = resource?.ResourcePath };
		foreach ( var part in parts )
		{
			if ( part.IsValid() )
				payload.Attachments[part.Category.ToString()] = part.ResourcePath;
		}

		return WeaponBuildCodePrefix + EncodeBase64Url( Encoding.UTF8.GetBytes( JsonSerializer.Serialize( payload ) ) );
	}

	public static bool TryImportWeaponBuildCode( EquipmentResource resource, string code, out GunsmithMessage error )
	{
		error = null;

		if ( !resource.IsValid() )
		{
			error = "Select a weapon before importing a build.";
			return false;
		}

		if ( string.IsNullOrWhiteSpace( code ) )
		{
			error = "Paste a build code first.";
			return false;
		}

		if ( !TryDecodeWeaponBuildCode( code, out var payload, out error ) )
			return false;

		if ( payload.Version != 1 )
		{
			error = "This build code version is not supported.";
			return false;
		}

		if ( string.IsNullOrWhiteSpace( payload.Weapon ) || !payload.Weapon.Equals( resource.ResourcePath, StringComparison.OrdinalIgnoreCase ) )
		{
			var expected = ResourceLibrary.GetAll<EquipmentResource>()
				.FirstOrDefault( x => x.ResourcePath.Equals( payload.Weapon ?? "", StringComparison.OrdinalIgnoreCase ) );

			error = expected.IsValid()
				? new GunsmithMessage( "This code is for {0}. Select that weapon first.", expected.Name )
				: "This code is for a different weapon.";
			return false;
		}

		var partsToApply = new Dictionary<GunsmithPartType, GunsmithPart>();
		foreach ( var entry in payload.Attachments ?? new Dictionary<string, string>() )
		{
			if ( !Enum.TryParse<GunsmithPartType>( entry.Key, out var category ) )
			{
				error = new GunsmithMessage( "Unknown attachment category: {0}.", entry.Key );
				return false;
			}

			var part = ResourceLibrary.GetAll<GunsmithPart>()
				.FirstOrDefault( x => x.Category == category
					&& x.Supports( resource )
					&& (x.ResourcePath.Equals( entry.Value, StringComparison.OrdinalIgnoreCase )
						|| x.ResourceName.Equals( entry.Value, StringComparison.OrdinalIgnoreCase )) );

			if ( !part.IsValid() )
			{
				error = new GunsmithMessage( "Missing or incompatible {0} attachment.",
					new GunsmithMessage( category == GunsmithPartType.RearGrip ? "Rear Grip" : category.ToString() ) );
				return false;
			}

			partsToApply[category] = part;
		}

		foreach ( var category in Enum.GetValues<GunsmithPartType>() )
			SetAttachment( resource, category, null );

		foreach ( var entry in partsToApply )
			SetAttachment( resource, entry.Key, entry.Value );

		SetCamoOnOptics( payload.CamoOnOptics );
		SetEmblemOnGun( resource, payload.EmblemOnGun );
		SetUseCustomCamoColor( resource, payload.UseCustomCamo );

		if ( Color.TryParse( payload.CustomCamo, out var customCamo ) )
			SetCustomCamoColor( resource, customCamo.WithAlpha( payload.CustomCamoOpacity.Clamp( 0f, 1f ) ) );

		SetCustomCamoFinish( resource, payload.CustomCamoFinish.Clamp( 0, FinishNames.Length - 1 ) );
		SetUseCustomAnimatedCamoSpeed( resource, payload.UseCustomAnimatedSpeed );
		SetCustomAnimatedCamoSpeed( resource, new Vector2( payload.CustomAnimatedSpeedX, payload.CustomAnimatedSpeedY ) );

		if ( Color.TryParse( payload.ReticleColor, out var reticleColor ) )
			SetCustomReticleColor( resource, reticleColor );
		SetCustomReticleScale( resource, payload.ReticleScale );
		SetCustomReticleRotation( resource, payload.ReticleRotation );
		SetCustomReticleOffset( resource, new Vector2( payload.ReticleOffsetX, payload.ReticleOffsetY ) );

		if ( partsToApply.TryGetValue( GunsmithPartType.Optic, out var optic ) )
		{
			SetOpticEyePosition( resource, optic, payload.OpticEye );
			SetOpticZero( resource, optic, payload.OpticZero );
		}

		return true;
	}

	/// <summary> Resolves an incoming scoreboard build without applying it or consulting local loadout cookies. </summary>
	public static bool TryGetSharedBuildWeapon( string code, out EquipmentResource resource )
	{
		resource = null;
		if ( string.IsNullOrWhiteSpace( code ) || code.Length > MaxSharedBuildCodeLength
			|| !TryDecodeWeaponBuildCode( code, out var payload, out _ ) || payload.Version != 1
			|| string.IsNullOrWhiteSpace( payload.Weapon ) || payload.Weapon.Length > 256
			|| !float.IsFinite( payload.CustomCamoOpacity ) || !float.IsFinite( payload.CustomAnimatedSpeedX )
			|| !float.IsFinite( payload.CustomAnimatedSpeedY ) || !float.IsFinite( payload.ReticleScale )
			|| !float.IsFinite( payload.ReticleRotation ) || !float.IsFinite( payload.ReticleOffsetX ) || !float.IsFinite( payload.ReticleOffsetY )
			|| payload.Attachments?.Any( x => !Enum.TryParse<GunsmithPartType>( x.Key, out var category )
				|| !Enum.IsDefined( category ) || string.IsNullOrWhiteSpace( x.Value ) || x.Value.Length > 256 ) == true )
			return false;

		resource = ResourceLibrary.GetAll<EquipmentResource>().FirstOrDefault( x =>
			x.IsValid() && x.ResourcePath.Equals( payload.Weapon, StringComparison.OrdinalIgnoreCase )
			&& x.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary && !IsMergedWeaponResource( x ) );
		return resource.IsValid();
	}

	private static bool TryDecodeWeaponBuildCode( string code, out SharedWeaponBuild payload, out GunsmithMessage error )
	{
		payload = null;
		error = null;

		var clean = code.Trim();
		if ( clean.StartsWith( WeaponBuildCodePrefix, StringComparison.OrdinalIgnoreCase ) )
			clean = clean.Substring( WeaponBuildCodePrefix.Length );

		clean = clean.Replace( "\r", "" ).Replace( "\n", "" ).Replace( " ", "" );

		try
		{
			var json = Encoding.UTF8.GetString( DecodeBase64Url( clean ) );
			payload = JsonSerializer.Deserialize<SharedWeaponBuild>( json );
		}
		catch ( Exception )
		{
			error = "That build code is not valid.";
			return false;
		}

		if ( payload is null )
		{
			error = "That build code is empty.";
			return false;
		}

		return true;
	}

	private static string EncodeBase64Url( byte[] data ) =>
		Convert.ToBase64String( data ).TrimEnd( '=' ).Replace( '+', '-' ).Replace( '/', '_' );

	private static byte[] DecodeBase64Url( string value )
	{
		var base64 = value.Replace( '-', '+' ).Replace( '_', '/' );
		base64 = base64.PadRight( base64.Length + (4 - base64.Length % 4) % 4, '=' );
		return Convert.FromBase64String( base64 );
	}

	private sealed class SharedWeaponBuild
	{
		public int Version { get; set; }
		public string Weapon { get; set; }
		public Dictionary<string, string> Attachments { get; set; } = new();
		public bool CamoOnOptics { get; set; }
		public bool EmblemOnGun { get; set; }
		public bool UseCustomCamo { get; set; }
		public string CustomCamo { get; set; }
		public float CustomCamoOpacity { get; set; } = 1f;
		public int CustomCamoFinish { get; set; } = 1;
		public bool UseCustomAnimatedSpeed { get; set; }
		public float CustomAnimatedSpeedX { get; set; }
		public float CustomAnimatedSpeedY { get; set; }
		public string ReticleColor { get; set; }
		public float ReticleScale { get; set; } = 1f;
		public float ReticleRotation { get; set; }
		public float ReticleOffsetX { get; set; }
		public float ReticleOffsetY { get; set; }
		/// <summary>The fitted optic's Eye Position, in rail slots (<see cref="GetOpticEyePosition"/>).</summary>
		public int OpticEye { get; set; }
		/// <summary>The fitted optic's zero in metres, 0 for the gun's own (<see cref="GetOpticZero"/>).</summary>
		public int OpticZero { get; set; }
	}

	/// <summary>
	/// Surface maps carried from a weapon's own material onto a camo material that replaces it, so the
	/// gun keeps its shading instead of rendering as a flat, evenly lit shape.
	/// </summary>
	private static readonly string[] SurfaceMapNames =
	{
		"TextureNormal",
		"TextureRoughness",
		"TextureAmbientOcclusion",
		"TextureMetalness",
	};

	/// <summary>
	/// A build <see cref="ApplyBuild"/> is fitting. While it's set, the getters <see cref="ApplyAttachments"/> reads (the
	/// attachments, camo, finish and reticle) return its values rather than the saved loadout's.
	/// </summary>
	private static SharedWeaponBuild _fitting;

	/// <summary>
	/// Fits a build code (<see cref="ExportWeaponBuildCode"/>) to <paramref name="root"/> as <see cref="ApplyAttachments"/>
	/// fits the saved loadout, saving nothing: the Theater's first-person gun wears the build the match was played with.
	/// Its parts aren't checked against the weapon's level, as they were when the code was made. False, with nothing
	/// fitted, for a code that can't be read or is for another weapon.
	/// </summary>
	public static bool ApplyBuild( EquipmentResource resource, GameObject root, string code )
	{
		if ( !resource.IsValid() || !root.IsValid() || string.IsNullOrWhiteSpace( code )
			|| !TryDecodeWeaponBuildCode( code, out var build, out _ )
			|| !resource.ResourcePath.Equals( build.Weapon ?? "", StringComparison.OrdinalIgnoreCase ) )
			return false;

		_fitting = build;
		try { ApplyAttachments( resource, root ); }
		finally { _fitting = null; }

		return true;
	}

	/// <summary>
	/// Runs <paramref name="read"/> with a build code (<see cref="ExportWeaponBuildCode"/>) standing in for the saved
	/// loadout, as <see cref="ApplyBuild"/> fits one, saving nothing: the gunsmith's COMPARE works out a saved build's
	/// figures this way (<see cref="GunsmithStats.Compute(EquipmentResource, string)"/>). Parts the weapon's level
	/// hasn't unlocked are left off, as they would be on the gun. False for a code that can't be read or is for another
	/// weapon.
	/// </summary>
	public static bool TryReadWithBuild<T>( EquipmentResource resource, string code, Func<T> read, out T value )
	{
		value = default;
		if ( !resource.IsValid() || read is null || string.IsNullOrWhiteSpace( code )
			|| !TryDecodeWeaponBuildCode( code, out var build, out _ )
			|| !resource.ResourcePath.Equals( build.Weapon ?? "", StringComparison.OrdinalIgnoreCase ) )
			return false;

		foreach ( var category in Enum.GetValues<GunsmithPartType>() )
		{
			if ( TryGetBuildAttachment( build, resource, category, out var part ) && !AttachmentUnlocks.IsUnlocked( resource, part ) )
				build.Attachments.Remove( category.ToString() );
		}

		_fitting = build;
		try { value = read(); }
		finally { _fitting = null; }

		return true;
	}

	public static void ApplyAttachments( EquipmentResource resource, GameObject root, GunsmithPart previewCamo = null )
	{
		if ( !resource.IsValid() || !root.IsValid() )
			return;

		GameObject FindMuzzle( GameObject go )
		{
			if ( go.Name.Equals( "muzzle", System.StringComparison.OrdinalIgnoreCase ) ) return go;
			foreach ( var child in go.Children )
			{
				var found = FindMuzzle( child );
				if ( found.IsValid() ) return found;
			}
			return null;
		}

		var attachmentPoints = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToList();
		// Ammunition, the action and the trigger are loadout options, so their preview slots need no external mesh or
		// mounting socket (AttachmentUnlocks.IsInternalSlot).
		if ( root.Components.Get<GunsmithWeapon>( FindMode.EverythingInSelf ).IsValid() )
		{
			foreach ( var category in new[] { GunsmithPartType.Action, GunsmithPartType.Trigger, GunsmithPartType.Ammunition } )
			{
				if ( attachmentPoints.Any( x => x.Category == category )
					|| !ResourceLibrary.GetAll<GunsmithPart>().Any( x => x.Category == category && x.Supports( resource ) ) )
					continue;

				var slot = new GameObject( root, true, category.ToString() );
				slot.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
				var point = slot.Components.Create<GunsmithAttachmentPoint>();
				point.Category = category;
				attachmentPoints.Add( point );
			}
		}
		
		if ( TryGetAttachment( resource, GunsmithPartType.Barrel, out var barrelPart ) )
		{
			if ( barrelPart.IsValid() && barrelPart.MainPrefab.IsValid() )
			{
				// Valid barrel part with a real prefab — create the attachment point if needed.
				if ( !attachmentPoints.Any( x => x.Category == GunsmithPartType.Barrel ) )
				{
					var muzzle = FindMuzzle( root );
					if ( muzzle.IsValid() )
					{
						var point = muzzle.Components.Create<GunsmithAttachmentPoint>();
						point.Category = GunsmithPartType.Barrel;
						attachmentPoints.Add( point );
					}
				}
			}
			// A bodygroup barrel (ModifyBodygroups) has no prefab: it switches the weapon's own barrel in its Barrel slot.
			// A build being fitted (ApplyBuild) isn't the saved loadout, so there's nothing to clear.
			else if ( _fitting is null && (!barrelPart.IsValid() || !barrelPart.ModifyBodygroups) )
			{
				// Broken/missing barrel part — nuke the cookie entirely (empty string, NOT __none)
				// so TryGetAttachment returns false and the barrel logic stops firing.
				Game.Cookies.Set( AttachmentCookieKey( resource.ResourcePath, GunsmithPartType.Barrel ), "" );
				Game.Cookies.Set( AttachmentCookieKey( resource.ResourceName, GunsmithPartType.Barrel ), "" );
				MarkChanged();
			}
		}

		if ( TryGetAttachment( resource, GunsmithPartType.Muzzle, out var muzzlePart )
			&& muzzlePart.IsValid() && muzzlePart.MainPrefab.IsValid()
			&& !attachmentPoints.Any( x => x.Category == GunsmithPartType.Muzzle ) )
		{
			var muzzle = FindMuzzle( root );
			if ( muzzle.IsValid() )
			{
				var point = muzzle.Components.Create<GunsmithAttachmentPoint>();
				point.Category = GunsmithPartType.Muzzle;
				attachmentPoints.Add( point );
			}
		}

		foreach ( var point in attachmentPoints )
		{
			point.SetPart( TryGetAttachment( resource, point.Category, out var part ) ? part : null );
			// The optic's tuned Eye Position, which RefreshMount (below) slides it along the rail by.
			if ( point.Category == GunsmithPartType.Optic )
				point.OpticRailShift = OpticTuning.RailShift( GetOpticEyePosition( resource, point.CurrentPart ) );
		}

		// A barrel kit and optic can affect the same gas-block bodygroup. Restore
		// active choices after every category has reset its previous bodygroups.
		foreach ( var point in attachmentPoints ) point.ApplyBodygroups();
		foreach ( var mount in root.Components.GetAll<GunsmithBoneAttachment>( FindMode.EverythingInSelfAndDescendants ) )
			mount.RefreshMount();

		var useCustomCamo = GetUseCustomCamoColor( resource );

		// Apply Camo. A texture camo re-paints each of the gun's materials' COLOUR while keeping
		// that material's own normal / roughness / AO — so the gun still reads as proper metal,
		// not a flat sticker. A plain colour camo just tints. Clears itself when none is equipped.
		GunsmithPart camoPart = previewCamo;
		if ( !camoPart.IsValid() )
		{
			TryGetAttachment( resource, GunsmithPartType.Camoflague3D, out camoPart );
			if ( !camoPart.IsValid() )
			{
				TryGetAttachment( resource, GunsmithPartType.GlowingCamo, out camoPart );
				if ( !camoPart.IsValid() )
				{
					TryGetAttachment( resource, GunsmithPartType.AnimatedCamo, out camoPart );
					if ( !camoPart.IsValid() )
					{
						TryGetAttachment( resource, GunsmithPartType.MasteryCamo, out camoPart );
						if ( !camoPart.IsValid() )
						{
							TryGetAttachment( resource, GunsmithPartType.Camoflague, out camoPart );
						}
					}
				}
			}
		}
		
		var customCamoColor = useCustomCamo ? GetCustomCamoColor( resource ) : Color.White;
		var customCamoOpacity = customCamoColor.a.Clamp( 0f, 1f );
		var hasCustomCamo = useCustomCamo && customCamoOpacity > 0.001f;
		var hasCamo = camoPart.IsValid() || hasCustomCamo;
		var camoTint = hasCustomCamo ? GetCustomCamoPaintTint( customCamoColor ) : (camoPart.IsValid() ? camoPart.CamoTint : Color.White);

		Texture camoTex = null;
		if ( hasCamo && !useCustomCamo && camoPart.IsValid() && !string.IsNullOrEmpty( camoPart.CamoTexture ) )
		{
			try { camoTex = Texture.Load( camoPart.CamoTexture ); }
			catch ( System.Exception e ) { Log.Warning( $"Gunsmith: couldn't load camo '{camoPart.CamoTexture}': {e.Message}" ); }
		}
		// A solid colour is paint too, like a Cerakote job: its colour replaces the gun's, as a pattern's does, over the
		// gun's own normal and AO. As a tint it multiplied the gun's dark colour, so it barely showed on most of the gun
		// and turned lighter parts (the FAMAS's magazine) lime.
		else if ( hasCamo && !useCustomCamo && camoPart.IsValid() && camoPart.Category == GunsmithPartType.Camoflague
			&& string.IsNullOrEmpty( camoPart.CamoMaterial ) )
		{
			camoTex = FlatTexture( camoPart.CamoTint );
		}

		Material camoMat = null;
		if ( hasCamo && !useCustomCamo && camoPart.IsValid() && !string.IsNullOrEmpty( camoPart.CamoMaterial ) )
		{
			try { camoMat = Material.Load( camoPart.CamoMaterial ); }
			catch ( System.Exception e ) { Log.Warning( $"Gunsmith: couldn't load camo material '{camoPart.CamoMaterial}': {e.Message}" ); }
		}

		// Animated camos with only a CamoTexture (no CamoMaterial) get a synthesised scrolling material
		// so they actually animate instead of rendering as a static texture.
		if ( camoMat is null && camoPart.IsValid() && camoPart.Category == GunsmithPartType.AnimatedCamo
			&& !string.IsNullOrEmpty( camoPart.CamoTexture ) && camoTex is not null )
		{
			var baseMat = Material.Load( "gunsmith/Camos/1_animated.vmat" );
			if ( baseMat is not null )
			{
				camoMat = baseMat.CreateCopy();
				camoMat.Set( "TextureColor", camoTex );
				camoMat.Set( "g_tColor", camoTex );
				camoMat.Set( "g_vTexCoordScrollSpeed", new Vector2( -0.025f, -0.040f ) );
			}
		}

		if ( camoMat is not null && GetUseCustomAnimatedCamoSpeed( resource ) )
		{
			var customSpeed = GetCustomAnimatedCamoSpeed( resource );
			camoMat = camoMat.CreateCopy();
			camoMat.Set( "g_vTexCoordScrollSpeed", customSpeed );
			camoMat.Set( "g_vSelfIllumScrollSpeed", customSpeed );
		}

		// The shared first-person arms model, used to skip the hands so they don't get camo'd.

		var armsModel = Model.Load( "models/first_person/v_first_person_arms_human.vmdl" );

		// Pre-compute once — same value for every renderer in the loop below.
		var camoOnOptics = GetCamoOnOptics();
		var customReticleColor = GetCustomReticleColor( resource );
		var customReticleScale = GetCustomReticleScale( resource );
		var customReticleRotation = GetCustomReticleRotation( resource );
		var customReticleOffset = GetCustomReticleOffset( resource );
		TryGetAttachment( resource, GunsmithPartType.Reticle, out var customReticleShape );
		Texture reticleShape = null;
		if ( customReticleShape.IsValid() && !string.IsNullOrEmpty( customReticleShape.CamoTexture ) )
		{
			try { reticleShape = Texture.Load( customReticleShape.CamoTexture ); }
			catch ( System.Exception e ) { Log.Warning( $"Gunsmith: couldn't load reticle '{customReticleShape.CamoTexture}': {e.Message}" ); }
		}

		foreach ( var renderer in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			// Only re-skin the gun itself — never the first-person arms / hands.
			if ( renderer.Model is not null && renderer.Model == armsModel )
				continue;

			// Nor the sleeves, gloves and skin drawn over them (ViewModelClothing's body wears a MilitaryUniform).
			if ( renderer.GetComponentInParent<MilitaryUniform>( true ).IsValid() )
				continue;

			// A sticker is vinyl over the paint, so the camo doesn't go on it.
			if ( renderer.Components.Get<GunsmithSticker>( FindMode.EverythingInSelf ).IsValid() )
				continue;

			// Nor the blood and dirt over it (FirstPersonGrime), which picks its own slots.
			if ( renderer.Components.Get<GrimeSkin>( FindMode.EverythingInSelf ).IsValid() )
				continue;

			// Separate optic meshes obey the same camo toggle as built-in optic bodygroups.
			var isOptic = false;
			var currentObj = renderer.GameObject;
			while ( currentObj.IsValid() )
			{
				var point = currentObj.Components.Get<GunsmithAttachmentPoint>( FindMode.EverythingInSelf );
				if ( point.IsValid() && point.Category == GunsmithPartType.Optic )
				{
					isOptic = true;
					break;
				}
				currentObj = currentObj.Parent;
			}

			renderer.MaterialOverride = null;

			// ImmutableArray<Material>? — unwrap before iterating.
			var matsNullable = renderer.Model?.Materials;
			if ( !matsNullable.HasValue )
			{
				renderer.Tint = hasCamo && !isOptic ? camoTint : Color.White;
				continue;
			}
			var mats = matsNullable.Value;

			// Every camo type goes through the same protection pass, including custom colour and no-camo resets.
			for ( int i = 0; i < mats.Length; i++ )
			{
				var original = mats[i];
				if ( original is null )
				{
					renderer.Materials.SetOverride( i, null );
					continue;
				}

				var opticMaterial = isOptic || IsOpticMaterial( original );
				var surface = CamoMaterialRules.Classify( original.Name, original.ShaderName, opticMaterial, false );
				if ( surface == CamoMaterialRules.Surface.Paintable && opticMaterial
					&& (original.GetFeature( "F_TRANSLUCENT" ) == 1 || original.GetFeature( "F_ALPHA_TEST" ) == 1) )
					surface = CamoMaterialRules.Surface.Lens;
				if ( surface != CamoMaterialRules.Surface.Paintable )
				{
					if ( surface == CamoMaterialRules.Surface.Reticle )
					{
						var reticleCopy = original.CreateCopy();
						reticleCopy.Set( "g_vSightLightColor", customReticleColor );
						ApplyReticleShape( reticleCopy, GetMaterialFileName( original ), reticleShape, customReticleScale, customReticleRotation, customReticleOffset );
						renderer.Materials.SetOverride( i, reticleCopy );
					}
					else
					{
						renderer.Materials.SetOverride( i, original );
					}
					continue;
				}

				// Camo on Optics paints the housing, never the sight's optical surfaces or light-blocking masks.
				if ( !camoOnOptics && opticMaterial )
				{
					renderer.Materials.SetOverride( i, original );
					continue;
				}

				if ( camoMat is not null )
				{
					// The animated shader replaces the material outright, which would drop this material's
					// normal / roughness / AO maps and leave the gun completely unshaded — bright camos
					// then blow out and dark ones read flat. Carry the source maps across so it still
					// lights like metal, and put AO's contribution to direct light back to full.
					var animCopy = camoMat.CreateCopy();

					foreach ( var mapName in SurfaceMapNames )
					{
						var srcMap = original.GetTexture( mapName );
						if ( srcMap is not null )
							animCopy.Set( mapName, srcMap );
					}

					animCopy.Set( "g_flAmbientOcclusionDirectDiffuse", 1f );
					animCopy.Set( "g_flAmbientOcclusionDirectSpecular", 1f );
					if ( camoPart.Category == GunsmithPartType.Camoflague )
						ApplyPaintFinish( animCopy );

					renderer.Materials.SetOverride( i, animCopy );
				}
				else if ( camoTex is not null )
				{
					// Swap only the colour map, keeping the source material's normals, roughness and AO.
					var copy = original.CreateCopy();
					// TextureColor is the albedo slot these shaders actually expose (see any .vmat).
					// "Color" / "g_tColor" are no-ops and leave the copy on its default white albedo.
					copy.Set( "g_flUseFactoryFinish", 0f );
					copy.Set( "TextureColor", camoTex );
					copy.Set( "Color", camoTex );
					copy.Set( "g_tColor", camoTex );
					// Printed paint is a satin coating, rather than the gun's original
					// polished metal. Keep the source normal and AO detail underneath.
					if ( camoPart.Category == GunsmithPartType.Camoflague )
						ApplyPaintFinish( copy );
					if ( camoPart.IsValid() && camoPart.Category == GunsmithPartType.GlowingCamo )
					{
						copy.Set( "g_bUseSelfIllum", true );
						copy.Set( "g_flSelfIllumScale", 5.0f );
						copy.Set( "SelfIllumMask", camoTex );
						copy.Set( "g_vSelfIllumTint", camoPart.CamoTint );
					}
					renderer.Materials.SetOverride( i, copy );
				}
				else if ( hasCustomCamo )
				{
					// Below full opacity the gun's own colour shows through the paint.
					var copy = original.CreateCopy();
					var paint = CustomPaintTexture( original, customCamoColor );
					copy.Set( "g_flUseFactoryFinish", 0f );
					copy.Set( "TextureColor", paint );
					copy.Set( "Color", paint );
					copy.Set( "g_tColor", paint );
					ApplyCustomFinish( copy, GetCustomCamoFinish( resource ) );
					renderer.Materials.SetOverride( i, copy );
				}
				else if ( hasCamo )
				{
					var copy = original.CreateCopy();
					copy.Set( "g_vColorTint", camoTint );
					copy.Set( "Color", camoTint );
					if ( !useCustomCamo && camoPart.IsValid() && camoPart.Category == GunsmithPartType.Camoflague )
						ApplyPaintFinish( copy );

					if ( camoPart.IsValid() && camoPart.Category == GunsmithPartType.GlowingCamo )
					{
						copy.Set( "g_bUseSelfIllum", true );
						copy.Set( "g_flSelfIllumScale", 5.0f );
						copy.Set( "SelfIllumMask", Texture.White );
						copy.Set( "g_vSelfIllumTint", camoTint );
					}

					renderer.Materials.SetOverride( i, copy );
				}
				else
				{
					renderer.Materials.SetOverride( i, original );
				}
			}

			renderer.Tint = Color.White;
		}

		// Hide replaced geometry after painting, so every camo branch preserves
		// the barrel kit's silhouette. Removing the kit restores original slots
		// through the normal material pass above.
		var hiddenMaterials = attachmentPoints.Where( p => p.CurrentPart.IsValid() )
			.SelectMany( p => p.CurrentPart.HiddenWeaponMaterials ?? new List<string>() )
			.ToHashSet( StringComparer.OrdinalIgnoreCase );
		var hideableMaterials = ResourceLibrary.GetAll<GunsmithPart>()
			.Where( p => p.IsValid() && p.Supports( resource ) )
			.SelectMany( p => p.HiddenWeaponMaterials ?? new List<string>() )
			.ToHashSet( StringComparer.OrdinalIgnoreCase );
		if ( hideableMaterials.Count > 0 )
		{
			var nodraw = Material.Load( "attachments/m4a1/materials/hidden.vmat" );
			foreach ( var renderer in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( renderer.Model is null || renderer.Components.Get<GrimeSkin>( FindMode.EverythingInSelf ).IsValid() ) continue;
				for ( int i = 0; i < renderer.Model.Materials.Length; i++ )
				{
					var original = renderer.Model.Materials[i];
					if ( hideableMaterials.Contains( original.Name ) )
						renderer.Materials.SetOverride( i, hiddenMaterials.Contains( original.Name ) ? nodraw : original );
				}
			}
		}
		if ( hiddenMaterials.Count > 0 )
		{
			var nodraw = Material.Load( "attachments/m4a1/materials/hidden.vmat" );
			foreach ( var renderer in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( renderer.Model is null || renderer.Components.Get<GrimeSkin>( FindMode.EverythingInSelf ).IsValid() ) continue;
				// Barrel prefabs retain the original MP5 receiver as a separate
				// clipped mesh. Hide only the native skinned copy of this material.
				if ( renderer.Components.Get<GunsmithMp5NativeReceiver>() is not null ) continue;
				for ( int i = 0; i < renderer.Model.Materials.Length; i++ )
					if ( hiddenMaterials.Contains( renderer.Model.Materials[i].Name ) )
						renderer.Materials.SetOverride( i, nodraw );
			}
		}
		foreach ( var mount in root.Components.GetAll<GunsmithMw22Attachment>( FindMode.EverythingInSelfAndDescendants ) ) mount.RefreshMount();
		foreach ( var factory in root.Components.GetAll<GunsmithMw22Factory>( FindMode.EverythingInSelfAndDescendants ) ) factory.Refresh();
	}

	private static string GetMaterialFileName( Material material )
	{
		var path = (material.Name ?? "").Replace( '\\', '/' );
		return path[(path.LastIndexOf( '/' ) + 1)..].ToLowerInvariant();
	}

	/// <summary>
	/// Draws the chosen reticle shape on an optic's lens. Only m4_optic_lens centres its mask on the lens; the SWB
	/// reflex masks are placed per model, and the scout scope keeps its drawn crosshair.
	/// </summary>
	private static void ApplyReticleShape( Material reticle, string fileName, Texture shape, float scale, float rotation, Vector2 offset )
	{
		if ( fileName.StartsWith( "scout_" ) || reticle.ShaderName?.Contains( "m4_optic_lens" ) != true )
			return;

		reticle.Set( "g_flReticleScale", scale );
		reticle.Set( "g_flReticleRotation", rotation );
		reticle.Set( "g_vReticleOffset", offset );
		if ( shape is not null )
		{
			reticle.Set( "g_tRedDot", shape );
			reticle.Set( "g_flUseReticleTexture", 1f );
		}
	}

	private static bool IsOpticMaterial( Material material )
	{
		var name = (material.Name ?? "").ToLowerInvariant();
		return name.Contains( "sight" ) || name.Contains( "scope" )
			|| name.Contains( "holo" ) || name.Contains( "optic" )
			|| name.Contains( "reddot" ) || name.Contains( "rmr" );
	}

	private static void ApplyPaintFinish( Material material )
	{
		// Source weapons use both scalar and texture-based shader variants.
		material.Set( "TextureMetalness", Texture.Black );
		material.Set( "g_tMetalness", Texture.Black );
		material.Set( "g_flMetalness", 0f );
		material.Set( "TextureRoughness", Texture.White );
		material.Set( "g_tRoughness", Texture.White );
		material.Set( "g_flRoughnessScaleFactor", 0.65f );
		material.Set( "g_flRoughness", 0.65f );
		material.Set( "g_flSelfIllumScale", 0f );
		material.Set( "g_flSelfIllumBrightness", 0f );
		material.Set( "g_flAmbientOcclusionDirectDiffuse", 1f );
		material.Set( "g_flAmbientOcclusionDirectSpecular", 1f );
	}

	private static readonly Dictionary<uint, Texture> FlatTextures = new();

	/// <summary> A flat texture of <paramref name="color"/>: a solid colour's paint, or a flat map for a finish. </summary>
	private static Texture FlatTexture( Color color )
	{
		static byte Byte( float value ) => (byte)(value.Clamp( 0f, 1f ) * 255f + 0.5f);
		var rgb = new[] { Byte( color.r ), Byte( color.g ), Byte( color.b ) };
		var key = (uint)(rgb[0] << 16 | rgb[1] << 8 | rgb[2]);
		if ( FlatTextures.TryGetValue( key, out var texture ) && texture.IsValid() )
			return texture;

		const int size = 4;
		var data = new byte[size * size * 4];
		for ( var i = 0; i < data.Length; i += 4 )
		{
			data[i] = rgb[0];
			data[i + 1] = rgb[1];
			data[i + 2] = rgb[2];
			data[i + 3] = byte.MaxValue;
		}

		texture = Texture.Create( size, size ).WithStaticUsage().WithData( data ).Finish();
		FlatTextures[key] = texture;
		return texture;
	}

	/// <summary> The most a colour map is read back at, across, to paint over it (<see cref="CustomPaintTexture"/>). </summary>
	private const int PaintOverSize = 512;

	private sealed record ColourMap( Color32[] Pixels, int Width, int Height );

	/// <summary> Colour maps read back to paint over, or null for one that couldn't be read. </summary>
	private static readonly Dictionary<Texture, ColourMap> ColourMaps = new();
	private static readonly Dictionary<(Texture, uint), Texture> PaintedOver = new();

	/// <summary>
	/// The colour map for <paramref name="material"/> under a custom colour: the paint, flat, at full opacity, and below it
	/// the material's own colour showing through it, as through a thin coat. Flat paint if the material's own map can't
	/// be read.
	/// </summary>
	private static Texture CustomPaintTexture( Material material, Color paint )
	{
		var opacity = paint.a.Clamp( 0f, 1f );
		var source = opacity < 0.995f ? material.GetTexture( "TextureColor" ) ?? material.GetTexture( "g_tColor" ) : null;
		if ( source is null || !source.IsValid() || !TryReadColourMap( source, out var map ) )
			return FlatTexture( paint.WithAlpha( 1f ) );

		static byte Byte( float value ) => (byte)(value.Clamp( 0f, 1f ) * 255f + 0.5f);
		var key = (source, (uint)(Byte( paint.r ) << 24 | Byte( paint.g ) << 16 | Byte( paint.b ) << 8 | Byte( opacity )));
		if ( PaintedOver.TryGetValue( key, out var texture ) && texture.IsValid() )
			return texture;

		// A colour picker's drag makes a new one each step, so the cache doesn't grow without end. A texture a gun still
		// wears stays alive through its material.
		if ( PaintedOver.Count >= 64 )
			PaintedOver.Clear();

		var keep = 1f - opacity;
		var r = Byte( paint.r ) * opacity + 0.5f;
		var g = Byte( paint.g ) * opacity + 0.5f;
		var b = Byte( paint.b ) * opacity + 0.5f;
		var data = new byte[map.Width * map.Height * 4];
		for ( int p = 0, j = 0; p < map.Pixels.Length; p++, j += 4 )
		{
			var pixel = map.Pixels[p];
			data[j] = (byte)(pixel.r * keep + r);
			data[j + 1] = (byte)(pixel.g * keep + g);
			data[j + 2] = (byte)(pixel.b * keep + b);
			data[j + 3] = pixel.a;
		}

		texture = Texture.Create( map.Width, map.Height ).WithStaticUsage().WithData( data ).Finish();
		PaintedOver[key] = texture;
		return texture;
	}

	/// <summary> Reads <paramref name="source"/> back once, at its first mip no more than <see cref="PaintOverSize"/> across. </summary>
	private static bool TryReadColourMap( Texture source, out ColourMap map )
	{
		if ( ColourMaps.TryGetValue( source, out map ) )
			return map is not null;

		try
		{
			var mip = 0;
			while ( mip < source.Mips - 1 && Math.Max( source.Width >> mip, source.Height >> mip ) > PaintOverSize )
				mip++;

			var width = Math.Max( 1, source.Width >> mip );
			var height = Math.Max( 1, source.Height >> mip );
			var pixels = source.GetPixels( mip );
			if ( pixels is not null && pixels.Length == width * height )
				map = new ColourMap( pixels, width, height );
		}
		catch ( Exception e )
		{
			Log.Warning( $"Gunsmith: couldn't read '{source.ResourcePath}' to paint over it ({e.Message})" );
		}

		ColourMaps[source] = map;
		return map is not null;
	}

	/// <summary> The custom colour's finish (<see cref="FinishNames"/>), set the way <see cref="ApplyPaintFinish"/> sets satin. </summary>
	private static void ApplyCustomFinish( Material material, int finish )
	{
		finish = Math.Clamp( finish, 0, FinishMetalness.Length - 1 );
		var metalness = FinishMetalness[finish];
		var metalnessMap = FlatTexture( new Color( metalness, metalness, metalness ) );
		material.Set( "TextureMetalness", metalnessMap );
		material.Set( "g_tMetalness", metalnessMap );
		material.Set( "g_flMetalness", metalness );
		material.Set( "TextureRoughness", Texture.White );
		material.Set( "g_tRoughness", Texture.White );
		material.Set( "g_flRoughnessScaleFactor", FinishRoughness[finish] );
		material.Set( "g_flRoughness", FinishRoughness[finish] );
		material.Set( "g_flSelfIllumScale", 0f );
		material.Set( "g_flSelfIllumBrightness", 0f );
		material.Set( "g_flAmbientOcclusionDirectDiffuse", 1f );
		material.Set( "g_flAmbientOcclusionDirectSpecular", 1f );
	}

	private static Color GetCustomCamoPaintTint( Color color )
	{
		var amount = color.a.Clamp( 0f, 1f );
		return new Color(
			1f + (color.r - 1f) * amount,
			1f + (color.g - 1f) * amount,
			1f + (color.b - 1f) * amount,
			0f );
	}

	public static bool TryGetAttachment( EquipmentResource resource, GunsmithPartType category, out GunsmithPart part )
	{
		if ( _fitting is { } build )
			return TryGetBuildAttachment( build, resource, category, out part );

		part = null;
		if ( !resource.IsValid() )
			return false;

		// The saved part, worked out once until the loadout or the unlocks change (Version).
		if ( Fitted.TryGetValue( (resource, category), out var fitted ) && (fitted.Part is null || fitted.Part.IsValid()) )
		{
			part = fitted.Part;
			return fitted.Found;
		}

		var found = TryGetUnlockedAttachment( resource, category, out part );
		Fitted[(resource, category)] = (found, part);
		return found;
	}

	private static bool TryGetUnlockedAttachment( EquipmentResource resource, GunsmithPartType category, out GunsmithPart part )
	{
		if ( !TryGetSavedAttachment( resource, category, out part ) )
			return false;

		// A part the weapon's level hasn't unlocked (AttachmentUnlocks) stays saved but isn't fitted: it reads as no
		// choice saved, not as "none", which ApplyAttachments would take as a broken barrel and clear.
		if ( part.IsValid() && !AttachmentUnlocks.IsUnlocked( resource, part ) )
		{
			part = null;
			return false;
		}

		return true;
	}

	/// <summary> Saved attachments the weapon's level hasn't unlocked yet, which stay off the gun until it has. </summary>
	public static List<GunsmithPart> GetLockedAttachments( EquipmentResource resource ) => Enum.GetValues<GunsmithPartType>()
		.Where( AttachmentUnlocks.IsAttachment )
		.Select( category => TryGetSavedAttachment( resource, category, out var part ) ? part : null )
		.Where( part => part.IsValid() && !AttachmentUnlocks.IsUnlocked( resource, part ) )
		.ToList();

	/// <summary> The part a build has in a slot. A build code only lists the slots with a part in them. </summary>
	private static bool TryGetBuildAttachment( SharedWeaponBuild build, EquipmentResource resource, GunsmithPartType category, out GunsmithPart part )
	{
		part = null;
		if ( !resource.IsValid() || build.Attachments is null || !build.Attachments.TryGetValue( category.ToString(), out var value )
			|| string.IsNullOrEmpty( value ) )
			return false;

		part = PartsNamed( value ).FirstOrDefault( x => x.IsValid() && x.Category == category );

		return part.IsValid();
	}

	private static Dictionary<string, List<GunsmithPart>> _partsByName;
	private static int _partsByNameVersion = -1;

	/// <summary>
	/// The parts whose path or name is <paramref name="value"/>, in the library's order, as a search of every part would
	/// find them. The index is made again when a part loads (<see cref="GunsmithPart.LibraryVersion"/>).
	/// </summary>
	private static List<GunsmithPart> PartsNamed( string value )
	{
		if ( _partsByName is null || _partsByNameVersion != GunsmithPart.LibraryVersion )
		{
			var index = new Dictionary<string, List<GunsmithPart>>( StringComparer.OrdinalIgnoreCase );
			void Add( string key, GunsmithPart part )
			{
				if ( key is null ) return;
				if ( !index.TryGetValue( key, out var list ) ) index[key] = list = new List<GunsmithPart>();
				// A part whose path and name are the same is listed once.
				if ( list.Count == 0 || list[^1] != part ) list.Add( part );
			}

			foreach ( var part in ResourceLibrary.GetAll<GunsmithPart>() )
			{
				Add( part.ResourcePath, part );
				Add( part.ResourceName, part );
			}

			_partsByName = index;
			_partsByNameVersion = GunsmithPart.LibraryVersion;
		}

		return value is not null && _partsByName.TryGetValue( value, out var parts ) ? parts : NoParts;
	}

	private static readonly List<GunsmithPart> NoParts = new();

	/// <summary> The part saved in a slot, locked or not. </summary>
	private static bool TryGetSavedAttachment( EquipmentResource resource, GunsmithPartType category, out GunsmithPart part )
	{
		part = null;
		if ( !resource.IsValid() )
			return false;

		var value = Game.Cookies.Get( AttachmentCookieKey( resource.ResourcePath, category ), "" );
		if ( string.IsNullOrEmpty( value ) )
		{
			value = Game.Cookies.Get( AttachmentCookieKey( resource.ResourceName, category ), "" );
			if ( string.IsNullOrEmpty( value ) )
				return false;
		}

		if ( value.Equals( NoneAttachmentValue, StringComparison.OrdinalIgnoreCase ) )
			return true;

		part = PartsNamed( value ).FirstOrDefault( x => x.IsValid() && x.Category == category && x.Supports( resource ) );

		return part.IsValid();
	}

	private static bool IsLegacyMergedResourceName( string resourceName ) =>
		!string.IsNullOrEmpty( resourceName )
		&& resourceName.Equals( LegacyUspSResourceName, StringComparison.OrdinalIgnoreCase );

	private static void MigrateLegacyUspSLoadout()
	{
		Game.Cookies.Set( SecondaryCookieKey, UspResourceName );
		Game.Cookies.Set( AttachmentCookieKey( UspResourceName, GunsmithPartType.Barrel ), UspSuppressorResourceName );
		MarkChanged();
	}

	private static string AttachmentCookieKey( string weaponId, GunsmithPartType category ) =>
		$"hc1.gunsmith.class{GetActiveClassIndex()}.{weaponId}.{category}";

}
