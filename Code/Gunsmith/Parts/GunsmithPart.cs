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
	Camoflague3D
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
