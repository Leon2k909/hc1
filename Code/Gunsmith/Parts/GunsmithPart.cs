namespace Facepunch.Gunsmith;

public enum GunsmithPartType
{
	Charm,
	Camoflague,
	Barrel,
	Stock,
	Underbarrel,
	Optic,
	Sticker,
	MasteryCamo,
	AnimatedCamo,
	GlowingCamo,
	Reticle,
	Camoflague3D,
	// Append to preserve the numeric values stored by existing assets/builds.
	Muzzle,
	Ammunition = 13,
	RearGrip = 14,
	Magazine = 15,
	Laser = 16
}

[GameResource( "HC1/Gunsmith Part", "gnsmth", "A gunsmith part" )]
public partial class GunsmithPart : GameResource
{
	/// <summary>
	/// What's this part called?
	/// </summary>
	[Property]
	public string Name { get; set; }

	/// <summary>
	/// The category for this part
	/// </summary>
	[Property]
	public GunsmithPartType Category { get; set; }

	/// <summary>
	/// Prefab!
	/// </summary>
	[Property] 
	public GameObject MainPrefab { get; set; }

	/// <summary>Original weapon material slots replaced by this kit's geometry.</summary>
	[Property] public List<string> HiddenWeaponMaterials { get; set; } = new();
	[Property] public bool IsSuppressor { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Ammunition )]
	public bool UsesTracerRounds { get; set; }
	[Property] public string Description { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine )]
	public int MagazineCapacity { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine )]
	public float ReloadTimeMultiplier { get; set; } = 1f;
	/// <summary>
	/// A magazine of another kind than the weapon's own (a box magazine on a drum-fed gun) reloads with its own viewmodel
	/// animations: the animgraph's reload_variant, 0 keeping the weapon's reload. Its reload times and foley then replace
	/// the weapon's (<see cref="Reloadable"/>); <see cref="ReloadTimeMultiplier"/> still applies on top.
	/// </summary>
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine ), Group( "Reload" )]
	public int ReloadAnimation { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine ), Group( "Reload" )]
	public float ReloadTime { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine ), Group( "Reload" )]
	public float EmptyReloadTime { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine ), Group( "Reload" )]
	public Dictionary<float, SoundEvent> ReloadSounds { get; set; } = new();
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Magazine ), Group( "Reload" )]
	public Dictionary<float, SoundEvent> EmptyReloadSounds { get; set; } = new();
	/// <summary>
	/// A bodygroup barrel of another length: how far it moves the muzzle from the factory barrel's, in the weapon's
	/// bind space. Muzzle devices and discharge effects follow it (<see cref="GunsmithAttachmentPoint.MuzzleShift"/>).
	/// </summary>
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Barrel )]
	public Vector3 MuzzleShift { get; set; }

	/// <summary>
	/// Recoil multipliers for parts whose effect isn't implied by their name (see <see cref="GunsmithAttachmentEffects"/>),
	/// e.g. a heavier fixed stock. 1 leaves recoil unchanged.
	/// </summary>
	[Property, Group( "Effects" )] public float VerticalRecoilScale { get; set; } = 1f;
	[Property, Group( "Effects" )] public float HorizontalRecoilScale { get; set; } = 1f;

	/// <summary>
	/// Which weapons does this part support? By default, if it's empty, it's universal
	/// </summary>
	[Property]
	public List<EquipmentResource> EligibleEquipment { get; set; } = new();

	/// <summary>
	/// The weapon level required to unlock this part.
	/// </summary>
	[Property]
	public int RequiredLevel { get; set; } = 0;

	[Property]
	public bool ModifyBodygroups { get; set; } = false;

	[Property, ShowIf( nameof( ModifyBodygroups ), true )]
	public Dictionary<string, int> Bodygroups { get; set; } = new();

	/// <summary>Explicit choices for models whose bodygroup layouts differ from the viewmodel.</summary>
	[Property] public Dictionary<string, Dictionary<string, int>> ModelBodygroups { get; set; } = new();
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Optic )] public bool OverrideAimOffset { get; set; }
	[Property, ShowIf( nameof( OverrideAimOffset ), true )] public Vector3 OpticAimOffset { get; set; }
	[Property, ShowIf( nameof( OverrideAimOffset ), true )] public Angles OpticAimAngles { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Optic ), Range( 1, 8 )] public float OpticMagnification { get; set; } = 1f;
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Optic ), Range( 0.05f, 0.5f )]
	public float OpticLensDiameter { get; set; } = 0.3f;
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Optic )]
	public bool OpticOverlayDot { get; set; } = true;

	public Dictionary<string, int> GetBodygroups( Model model ) =>
		model is not null && ModelBodygroups is not null && ModelBodygroups.TryGetValue( model.Name, out var groups )
			? groups ?? Bodygroups : Bodygroups;

	[Property, ShowIf( nameof(Category), GunsmithPartType.Camoflague ), ShowIf( nameof(Category), GunsmithPartType.MasteryCamo ), ShowIf( nameof(Category), GunsmithPartType.AnimatedCamo ), ShowIf( nameof(Category), GunsmithPartType.Camoflague3D )]
	public Color CamoTint { get; set; } = Color.White;

	/// <summary>
	/// Optional camo pattern image (square, tiling PNG works best). When set, this texture
	/// is wrapped over the whole gun instead of using the flat <see cref="CamoTint"/> colour.
	/// </summary>
	[Property, ImageAssetPath, ShowIf( nameof(Category), GunsmithPartType.Camoflague ), ShowIf( nameof(Category), GunsmithPartType.MasteryCamo ), ShowIf( nameof(Category), GunsmithPartType.AnimatedCamo ), ShowIf( nameof(Category), GunsmithPartType.Reticle ), ShowIf( nameof(Category), GunsmithPartType.Camoflague3D )]
	public string CamoTexture { get; set; }

	/// <summary>
	/// Optional material replacement for camos. Allows using a .vmat directly (e.g. for animated shaders).
	/// </summary>
	[Property, ResourceType("vmat"), ShowIf( nameof(Category), GunsmithPartType.AnimatedCamo ), ShowIf( nameof(Category), GunsmithPartType.Camoflague3D )]
	public string CamoMaterial { get; set; }

	/// <summary>
	/// The flat sticker artwork (square PNG, transparency supported) shown in the gunsmith
	/// and projected onto the gun. Used when <see cref="Category"/> is Sticker.
	/// </summary>
	[Property, ImageAssetPath, ShowIf( nameof(Category), GunsmithPartType.Sticker )]
	public string StickerImage { get; set; }

	/// <summary>
	/// The reticle drawn large on a transparent square (white, tinted with the chosen reticle colour) for the
	/// Customize tab. <see cref="CamoTexture"/> is the lens mask, where the shape is only a few pixels wide.
	/// </summary>
	[Property, ImageAssetPath, ShowIf( nameof(Category), GunsmithPartType.Reticle )]
	public string ReticlePreview { get; set; }

	/// <summary>
	/// Is this a universal attachment?
	/// </summary>
	public bool IsUniversal => EligibleEquipment.Count() < 1;

	public bool Supports( EquipmentResource resource )
	{
		if ( IsUniversal ) return true;
		if ( resource is null ) return false;
		foreach ( var eq in EligibleEquipment )
		{
			if ( eq.IsValid() && string.Equals( eq.ResourcePath, resource.ResourcePath, System.StringComparison.OrdinalIgnoreCase ) )
				return true;
		}
		return false;
	}
}
