namespace Facepunch;

/// <summary>
/// A look for a piece of equipment: another model in place of its stock one, on the same origin and with the same body
/// groups. <see cref="ModelPath"/> is null for the stock look.
/// </summary>
public sealed record EquipmentSkin( string Id, string Name, string Item, string Picture, string StockModel = null, string ModelPath = null );

/// <summary>
/// The skins equipment can wear. A player wears the one they picked in the loadout's gear picker (a cookie per item, sent
/// to the host as <see cref="Client.EquipmentSkinPicks"/>), and an item's first skin until they do. To add one, add a line
/// here with its picture: everything that draws the item swaps by the stock model's name (<see cref="Apply"/>).
/// </summary>
public static class EquipmentSkins
{
	private const string HeGrenadeStock = "models/weapons/sbox_grenade_explosive/w_he_grenade.vmdl";
	private const string SmokeGrenadeStock = "models/weapons/sbox_grenade_smoke/w_smoke_grenade.vmdl";
	private const string FlashbangStock = "models/weapons/sbox_grenade_flash/w_flash_grenade.vmdl";
	private const string IncendiaryStock = "models/weapons/sbox_grenade_incendiary/w_incendiary_grenade.vmdl";

	public static IReadOnlyList<EquipmentSkin> All { get; } = new EquipmentSkin[]
	{
		new( "he_standard", "Standard", "he_grenade", "ui/weapons/grenades/skin_he_standard.png" ),
		new( "he_k31", "K-31", "he_grenade", "ui/weapons/grenades/skin_he_k31.png", HeGrenadeStock, "weapons/throwable/he_grenade/he_grenade_v2/he_grenade.vmdl" ),
		new( "smoke_standard", "Standard", "smoke_grenade", "ui/weapons/grenades/skin_smoke_standard.png" ),
		new( "smoke_k44", "K-44", "smoke_grenade", "ui/weapons/grenades/skin_smoke_k44.png", SmokeGrenadeStock, "weapons/throwable/m18_smoke_grenade/smoke_grenade_v2/smoke_grenade.vmdl" ),
		new( "flash_standard", "Standard", "flashbang_grenade", "ui/weapons/grenades/skin_flash_standard.png" ),
		new( "flash_k47", "K-47", "flashbang_grenade", "ui/weapons/grenades/skin_flash_k47.png", FlashbangStock, "weapons/throwable/flashbang/flashbang_v2/flashbang.vmdl" ),
		new( "incendiary_standard", "Standard", "molotov_grenade", "ui/weapons/grenades/skin_incendiary_standard.png" ),
		new( "incendiary_k52", "K-52", "molotov_grenade", "ui/weapons/grenades/skin_incendiary_k52.png", IncendiaryStock, "weapons/throwable/molotov_cocktail/incendiary_grenade_v2/incendiary_grenade.vmdl" ),
		new( "incendiary_anm14", "AN-M14", "molotov_grenade", "ui/weapons/grenades/skin_incendiary_anm14.png", IncendiaryStock, "weapons/throwable/molotov_cocktail/thermite_grenade_v2/thermite_grenade.vmdl" ),
		new( "incendiary_anm14_grey", "AN-M14 Early", "molotov_grenade", "ui/weapons/grenades/skin_incendiary_anm14_grey.png", IncendiaryStock, "weapons/throwable/molotov_cocktail/thermite_grenade_v2/thermite_grenade_early.vmdl" ),
	};

	private const string EquippedCookie = "hc1.equipment_skin.";
	private static string _localPicks;

	public static EquipmentSkin Find( string id ) => All.FirstOrDefault( x => x.Id == id );

	/// <summary>The skins <paramref name="resource"/> has, its default first. Empty for most equipment.</summary>
	public static List<EquipmentSkin> For( EquipmentResource resource ) => For( resource?.ResourceName );

	private static List<EquipmentSkin> For( string item ) => All.Where( x => x.Item == item ).ToList();

	/// <summary>The skin the local player wears on <paramref name="resource"/>.</summary>
	public static EquipmentSkin GetEquipped( EquipmentResource resource ) => GetEquipped( resource?.ResourceName );

	private static EquipmentSkin GetEquipped( string item ) => Resolve( item, Game.Cookies.Get<string>( EquippedCookie + item, "" ) );

	/// <summary>Wear <paramref name="skin"/> on its item from the next time it's drawn.</summary>
	public static void Equip( EquipmentSkin skin )
	{
		Game.Cookies.Set( EquippedCookie + skin.Item, skin.Id );
		_localPicks = null;
	}

	/// <summary>The local player's equipped skins' ids, one per item, comma-separated.</summary>
	public static string LocalPicks => _localPicks ??= string.Join( ",",
		All.Select( x => x.Item ).Distinct().Select( item => GetEquipped( item ).Id ) );

	/// <summary>
	/// What <paramref name="item"/> wears from some picks (skin ids, comma-separated, as <see cref="LocalPicks"/>): the first
	/// that's one of its skins, else its default. Null if it has none.
	/// </summary>
	private static EquipmentSkin Resolve( string item, string picks )
	{
		var skins = For( item );
		foreach ( var id in (picks ?? "").Split( ',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries ) )
		{
			if ( skins.FirstOrDefault( x => x.Id == id ) is { } skin )
				return skin;
		}

		return skins.FirstOrDefault();
	}

	/// <summary>What <paramref name="player"/> wears on <paramref name="resource"/>. Bots wear the default.</summary>
	public static EquipmentSkin SkinOf( EquipmentResource resource, PlayerPawn player )
	{
		var client = player.IsValid() ? player.Client : null;
		if ( !client.IsValid() || client.IsBot )
			return Resolve( resource?.ResourceName, null );

		// The host's own picks are its cookies: they need no syncing, and offline there's nothing to sync them over.
		var own = client.Connection is null || client.Connection == Connection.Local;
		return Resolve( resource?.ResourceName, own ? LocalPicks : client.EquipmentSkinPicks );
	}

	/// <summary> Dresses <paramref name="root"/>, one of an item's prefabs, in what <paramref name="player"/> wears on it. </summary>
	public static void Apply( GameObject root, EquipmentResource resource, PlayerPawn player ) => Apply( root, SkinOf( resource, player ) );

	/// <summary>
	/// Puts <paramref name="skin"/>'s model on whatever in <paramref name="root"/> draws the stock one, which leaves a
	/// viewmodel's arms alone. A model that hasn't compiled stays stock rather than showing as an error.
	/// </summary>
	public static void Apply( GameObject root, EquipmentSkin skin )
	{
		if ( !root.IsValid() || skin?.ModelPath is null )
			return;

		var model = Model.Load( skin.ModelPath );
		if ( model is null || model.IsError )
			return;

		foreach ( var renderer in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			if ( renderer.Model?.Name != skin.StockModel )
				continue;

			var groups = renderer.BodyGroups;
			renderer.Model = model;
			renderer.BodyGroups = groups;
		}
	}
}
