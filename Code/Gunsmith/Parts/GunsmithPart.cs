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
	Laser = 16,
	Rail = 17
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
	/// A barrel whose own flash hider is shorter than the factory one: how much further back than <see cref="MuzzleShift"/>
	/// (where a muzzle device mounts) its bare muzzle is. The shots leave from there while no muzzle device is fitted
	/// (<see cref="GunsmithAttachmentPoint.DischargeShift"/>).
	/// </summary>
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Barrel )]
	public Vector3 TipShift { get; set; }
	/// <summary>Change in optic mount position in the weapon's bind space when replacing its upper rail.</summary>
	[Property] public Vector3 OpticMountShift { get; set; }
	/// <summary>Rail ADS corrections measured in viewmodel camera space.</summary>
	[Property] public Vector3 RailOpticAimCorrection { get; set; }
	[Property] public Vector3 RailIronAimCorrection { get; set; }
	/// <summary>Additional bodygroup choices while this part and an optic are fitted together.</summary>
	[Property] public Dictionary<string, int> OpticBodygroups { get; set; } = new();

	/// <summary>
	/// Recoil multipliers for parts whose effect isn't implied by their name (see <see cref="GunsmithAttachmentEffects"/>),
	/// e.g. a heavier fixed stock. 1 leaves recoil unchanged.
	/// </summary>
	[Property, Group( "Effects" )] public float VerticalRecoilScale { get; set; } = 1f;
	[Property, Group( "Effects" )] public float HorizontalRecoilScale { get; set; } = 1f;
	/// <summary>
	/// Damage falloff distance multiplier for parts whose effect isn't implied by their name, e.g. a barrel of another
	/// length, by the muzzle energy it gives against the factory barrel. 1 (or 0, a part loaded before a hotload added
	/// this) leaves it unchanged.
	/// </summary>
	[Property, Group( "Effects" )] public float DamageFalloffScale { get; set; } = 1f;

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
	/// <summary>
	/// Magnified optics: the centre of the eyepiece's rear glass in the optic model's space, and the glass's diameter
	/// (inches). With a diameter, <see cref="OpticZoom"/> fills that glass with the magnified picture wherever it is on
	/// screen, and <see cref="OpticLensDiameter"/> is unused. Written by Tools/optic_eyepieces.py.
	/// </summary>
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Optic )] public Vector3 OpticEyepiece { get; set; }
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Optic )] public float OpticEyepieceDiameter { get; set; }
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
	/// The sticker's artwork: a PNG cropped to the sticker, transparent outside its cut. The gunsmith shows it, and
	/// <see cref="GunsmithSticker"/> prints it on the gun at its own shape. Used when <see cref="Category"/> is Sticker.
	/// </summary>
	[Property, ImageAssetPath, ShowIf( nameof(Category), GunsmithPartType.Sticker )]
	public string StickerImage { get; set; }

	/// <summary>
	/// What the sticker is printed with on the gun: <see cref="StickerImage"/>'s colours, cut out by an alpha test.
	/// Empty means the .vmat beside the image.
	/// </summary>
	[Property, ResourceType( "vmat" ), ShowIf( nameof(Category), GunsmithPartType.Sticker )]
	public string StickerMaterial { get; set; }

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
