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

	public static int GetActiveClassIndex() => Game.Cookies.Get<int>( "hc1.loadout.active_class", 0 );
	public static void SetActiveClassIndex( int index ) => Game.Cookies.Set( "hc1.loadout.active_class", index );

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
	public const string UspResourceName = "weapons/usp/usp.equip";
	public const string LegacyUspSResourceName = "weapons/usp_sd/usp_sd.equip";
	public const string UspSuppressorResourceName = "gunsmith/usp/barrel/usp_suppressor.gnsmth";

	/// <summary>
	/// Returns the ResourceName of the player's chosen primary, or null if unset.
	/// </summary>
	public static string GetPrimary()
	{
		var v = Game.Cookies.Get<string>( PrimaryCookieKey, "" );
		return string.IsNullOrEmpty( v ) ? null : v;
	}

	public static bool GetCamoOnOptics() => Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.camoonoptics", false );

	public static bool GetEmblemOnGun( EquipmentResource resource ) =>
		Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.emblemOnGun", false );
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

	public static bool GetUseCustomCamoColor( EquipmentResource resource ) =>
		Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomcamo", false );

	public static void SetUseCustomCamoColor( EquipmentResource resource, bool value ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomcamo", value );

	public static Color GetCustomCamoColor( EquipmentResource resource )
	{
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

	public static bool GetUseCustomAnimatedCamoSpeed( EquipmentResource resource ) =>
		Game.Cookies.Get<bool>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomanimationspeed", false );

	public static void SetUseCustomAnimatedCamoSpeed( EquipmentResource resource, bool value ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.usecustomanimationspeed", value );

	public static Vector2 GetCustomAnimatedCamoSpeed( EquipmentResource resource )
	{
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
	public static int GetCustomCamoFinish( EquipmentResource resource ) =>
		Game.Cookies.Get<int>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.camofinish", 1 );

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
		var val = Game.Cookies.Get<string>( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.reticlecolor", "" );
		if ( string.IsNullOrEmpty( val ) ) return Color.Red;
		if ( Color.TryParse( val, out var col ) ) return col;
		return Color.Red;
	}

	public static void SetCustomReticleColor( EquipmentResource resource, Color color ) =>
		Game.Cookies.Set( $"hc1.gunsmith.class{GetActiveClassIndex()}.{resource.ResourcePath}.reticlecolor", color.Hex );

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

	public static bool IsMergedWeaponResource( EquipmentResource resource ) =>
		resource.IsValid() && IsLegacyMergedResourceName( resource.ResourcePath );

	public static string GetSlot( EquipmentSlot slot ) => slot switch
	{
		EquipmentSlot.Primary => GetPrimary(),
		EquipmentSlot.Secondary => GetSecondary(),
		_ => null
	};

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

	public static EquipmentResource GetSlotResource( EquipmentSlot slot )
	{
		var value = GetSlot( slot );
		if ( string.IsNullOrEmpty( value ) )
			return null;

		return ResourceLibrary.GetAll<EquipmentResource>()
			.FirstOrDefault( r => r.ResourcePath.Equals( value, StringComparison.OrdinalIgnoreCase )
			                     || r.ResourceName.Equals( value, StringComparison.OrdinalIgnoreCase ) );
	}

	public static IEnumerable<EquipmentResource> GetLoadoutResources()
	{
		foreach ( var slot in new[] { EquipmentSlot.Primary, EquipmentSlot.Secondary, EquipmentSlot.Tactical, EquipmentSlot.Lethal } )
		{
			var resource = GetSlotResource( slot );
			if ( resource.IsValid() )
				yield return resource;
		}
	}

	public static void SetAttachment( EquipmentResource resource, GunsmithPartType category, GunsmithPart part )
	{
		if ( !resource.IsValid() )
			return;

		Game.Cookies.Set( AttachmentCookieKey( resource.ResourcePath, category ), part?.ResourcePath ?? NoneAttachmentValue );
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

	public static string ExportWeaponBuildCode( EquipmentResource resource )
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
		};

		foreach ( var category in Enum.GetValues<GunsmithPartType>() )
		{
			if ( TryGetAttachment( resource, category, out var part ) && part.IsValid() )
				payload.Attachments[category.ToString()] = part.ResourcePath;
		}

		var json = JsonSerializer.Serialize( payload );
		return WeaponBuildCodePrefix + EncodeBase64Url( Encoding.UTF8.GetBytes( json ) );
	}

	public static bool TryImportWeaponBuildCode( EquipmentResource resource, string code, out string error )
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
				? $"This code is for {expected.Name}. Select that weapon first."
				: "This code is for a different weapon.";
			return false;
		}

		var partsToApply = new Dictionary<GunsmithPartType, GunsmithPart>();
		foreach ( var entry in payload.Attachments ?? new Dictionary<string, string>() )
		{
			if ( !Enum.TryParse<GunsmithPartType>( entry.Key, out var category ) )
			{
				error = $"Unknown attachment category: {entry.Key}.";
				return false;
			}

			var part = ResourceLibrary.GetAll<GunsmithPart>()
				.FirstOrDefault( x => x.Category == category
					&& x.Supports( resource )
					&& (x.ResourcePath.Equals( entry.Value, StringComparison.OrdinalIgnoreCase )
						|| x.ResourceName.Equals( entry.Value, StringComparison.OrdinalIgnoreCase )) );

			if ( !part.IsValid() )
			{
				error = $"Missing or incompatible {category} attachment.";
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

		return true;
	}

	private static bool TryDecodeWeaponBuildCode( string code, out SharedWeaponBuild payload, out string error )
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
		// Ammunition is a loadout option, so its preview slot needs no external mesh or mounting socket.
		if ( root.Components.Get<GunsmithWeapon>( FindMode.EverythingInSelf ).IsValid()
			&& !attachmentPoints.Any( x => x.Category == GunsmithPartType.Ammunition )
			&& ResourceLibrary.GetAll<GunsmithPart>().Any( x => x.Category == GunsmithPartType.Ammunition && x.Supports( resource ) ) )
		{
			var slot = new GameObject( root, true, "Ammunition" );
			slot.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			var point = slot.Components.Create<GunsmithAttachmentPoint>();
			point.Category = GunsmithPartType.Ammunition;
			attachmentPoints.Add( point );
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
			else
			{
				// Broken/missing barrel part — nuke the cookie entirely (empty string, NOT __none)
				// so TryGetAttachment returns false and the barrel logic stops firing.
				Game.Cookies.Set( AttachmentCookieKey( resource.ResourcePath, GunsmithPartType.Barrel ), "" );
				Game.Cookies.Set( AttachmentCookieKey( resource.ResourceName, GunsmithPartType.Barrel ), "" );
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
		TryGetAttachment( resource, GunsmithPartType.Reticle, out var customReticleShape );

		foreach ( var renderer in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			// Only re-skin the gun itself — never the first-person arms / hands.
			if ( renderer.Model is not null && renderer.Model == armsModel )
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
				renderer.Tint = hasCamo ? camoTint : Color.White;
				continue;
			}
			var mats = matsNullable.Value;

			if ( camoMat is not null )
			{
				// Material camo: preserve lenses and reticles while painting the housing.
				for ( int i = 0; i < mats.Length; i++ )
				{
					var matName = GetMaterialFileName( mats[i] );
					
					// Reticle Customization (and skipping glass/lens)
					if ( matName.Contains( "lens" ) || matName.Contains( "glass" ) || IsReticleMaterial( matName ) )
					{
						if ( IsReticleMaterial( matName ) )
						{
							var reticleCopy = mats[i].CreateCopy();
							reticleCopy.Set( "g_vSightLightColor", customReticleColor );
							if ( customReticleShape != null && !string.IsNullOrEmpty( customReticleShape.CamoTexture ) )
							{
								var texPath = customReticleShape.CamoTexture.Replace(".png", ".vtex");
								var tex = Texture.Load( FileSystem.Mounted, texPath );
								if ( tex != null )
								{
									reticleCopy.Set( "RedDot", tex );
									reticleCopy.Set( "g_tRedDot", tex );
									reticleCopy.Set( "g_flUseReticleTexture", 1f );
								}
							}
							renderer.Materials.SetOverride( i, reticleCopy );
						}
						else
						{
							renderer.Materials.SetOverride( i, mats[i] );
						}
						continue;
					}

					// Conditionally skip sight/optic body
					if ( !camoOnOptics && (isOptic || IsOpticMaterial( mats[i] )) )
					{
						renderer.Materials.SetOverride( i, mats[i] );
						continue;
					}

					// The animated shader replaces the material outright, which would drop this material's
					// normal / roughness / AO maps and leave the gun completely unshaded — bright camos
					// then blow out and dark ones read flat. Carry the source maps across so it still
					// lights like metal, and put AO's contribution to direct light back to full.
					var animCopy = camoMat.CreateCopy();

					foreach ( var mapName in SurfaceMapNames )
					{
						var srcMap = mats[i].GetTexture( mapName );
						if ( srcMap is not null )
							animCopy.Set( mapName, srcMap );
					}

					animCopy.Set( "g_flAmbientOcclusionDirectDiffuse", 1f );
					animCopy.Set( "g_flAmbientOcclusionDirectSpecular", 1f );
					if ( camoPart.Category == GunsmithPartType.Camoflague )
						ApplyPaintFinish( animCopy );

					renderer.Materials.SetOverride( i, animCopy );
				}

				renderer.Tint = Color.White;
			}
			else if ( camoTex is not null )
			{
				// Texture camo: copy each material, swap ONLY its colour for the camo pattern,
				// keep everything else (normal, roughness, AO) so lighting stays correct.
				for ( int i = 0; i < mats.Length; i++ )
				{
					var matName = GetMaterialFileName( mats[i] );
					
					// Reticle Customization (and skipping glass/lens)
					if ( matName.Contains( "lens" ) || matName.Contains( "glass" ) || IsReticleMaterial( matName ) )
					{
						if ( IsReticleMaterial( matName ) )
						{
							var reticleCopy = mats[i].CreateCopy();
							reticleCopy.Set( "g_vSightLightColor", customReticleColor );
							if ( customReticleShape != null && !string.IsNullOrEmpty( customReticleShape.CamoTexture ) )
							{
								var texPath = customReticleShape.CamoTexture.Replace(".png", ".vtex");
								var tex = Texture.Load( FileSystem.Mounted, texPath );
								if ( tex != null )
								{
									reticleCopy.Set( "RedDot", tex );
									reticleCopy.Set( "g_tRedDot", tex );
									reticleCopy.Set( "g_flUseReticleTexture", 1f );
								}
							}
							renderer.Materials.SetOverride( i, reticleCopy );
						}
						else
						{
							renderer.Materials.SetOverride( i, mats[i] );
						}
						continue;
					}

					// Conditionally skip sight/optic body
					if ( !camoOnOptics && (isOptic || IsOpticMaterial( mats[i] )) )
					{
						renderer.Materials.SetOverride( i, mats[i] );
						continue;
					}

					var copy = mats[i].CreateCopy();
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

				renderer.Tint = Color.White;
			}
			else
			{
				for ( int i = 0; i < mats.Length; i++ )
				{
					var matName = GetMaterialFileName( mats[i] );

					// Reticle Customization (and skipping glass/lens)
					if ( matName.Contains( "lens" ) || matName.Contains( "glass" ) || IsReticleMaterial( matName ) )
					{
						if ( IsReticleMaterial( matName ) )
						{
							var reticleCopy = mats[i].CreateCopy();
							reticleCopy.Set( "g_vSightLightColor", customReticleColor );
							if ( customReticleShape != null && !string.IsNullOrEmpty( customReticleShape.CamoTexture ) )
							{
								var texPath = customReticleShape.CamoTexture.Replace(".png", ".vtex");
								var tex = Texture.Load( FileSystem.Mounted, texPath );
								if ( tex != null )
								{
									reticleCopy.Set( "RedDot", tex );
									reticleCopy.Set( "g_tRedDot", tex );
									reticleCopy.Set( "g_flUseReticleTexture", 1f );
								}
							}
							renderer.Materials.SetOverride( i, reticleCopy );
						}
						else
						{
							renderer.Materials.SetOverride( i, mats[i] );
						}
						continue;
					}

					// Conditionally skip sight/optic body
					if ( !camoOnOptics && (isOptic || IsOpticMaterial( mats[i] )) )
					{
						renderer.Materials.SetOverride( i, mats[i] );
						continue;
					}

					if ( hasCamo )
					{
						var copy = mats[i].CreateCopy();
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

						// Apply gloss/matte finish when using custom colour camo.
						if ( useCustomCamo )
						{
							copy.Set( "g_flModelTintAmount", 1f );
							var finish = GetCustomCamoFinish( resource );
							finish = System.Math.Clamp( finish, 0, FinishMetalness.Length - 1 );
							copy.Set( "g_flMetalness", FinishMetalness[finish] );
							copy.Set( "TextureRoughness", Texture.White );
							copy.Set( "g_flRoughnessScaleFactor", FinishRoughness[finish] );
						}

						renderer.Materials.SetOverride( i, copy );
					}
					else
					{
						renderer.Materials.SetOverride( i, mats[i] );
					}
				}

				renderer.Tint = Color.White;
			}
		}

		// Hide replaced geometry after painting, so every camo branch preserves
		// the barrel kit's silhouette. Removing the kit restores original slots
		// through the normal material pass above.
		var hiddenMaterials = attachmentPoints.Where( p => p.CurrentPart.IsValid() )
			.SelectMany( p => p.CurrentPart.HiddenWeaponMaterials ?? new List<string>() )
			.ToHashSet( StringComparer.OrdinalIgnoreCase );
		if ( hiddenMaterials.Count > 0 )
		{
			var nodraw = Material.Load( "attachments/m4a1/materials/hidden.vmat" );
			foreach ( var renderer in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( renderer.Model is null ) continue;
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

	private static bool IsReticleMaterial( string fileName )
	{
		// "reddot_rmr" is the housing's folder, not a reticle. Match the material
		// filename so v_rmr.vmat gets painted while v_rmr_red_dot.vmat stays clear.
		return fileName.Contains( "reticle" ) || fileName.Contains( "hologram" )
			|| fileName.Contains( "_dot." ) || fileName.Contains( "_reddot." )
			|| fileName.StartsWith( "dot." ) || fileName.StartsWith( "red_dot." );
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

		part = ResourceLibrary.GetAll<GunsmithPart>()
			.FirstOrDefault( x => (x.ResourcePath.Equals( value, StringComparison.OrdinalIgnoreCase )
			                     || x.ResourceName.Equals( value, StringComparison.OrdinalIgnoreCase ))
			                     && x.Category == category
			                     && x.Supports( resource ) );

		return part.IsValid();
	}

	private static bool IsLegacyMergedResourceName( string resourceName ) =>
		!string.IsNullOrEmpty( resourceName )
		&& resourceName.Equals( LegacyUspSResourceName, StringComparison.OrdinalIgnoreCase );

	private static void MigrateLegacyUspSLoadout()
	{
		Game.Cookies.Set( SecondaryCookieKey, UspResourceName );
		Game.Cookies.Set( AttachmentCookieKey( UspResourceName, GunsmithPartType.Barrel ), UspSuppressorResourceName );
	}

	private static string AttachmentCookieKey( string weaponId, GunsmithPartType category ) =>
		$"hc1.gunsmith.class{GetActiveClassIndex()}.{weaponId}.{category}";

}
