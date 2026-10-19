using Sandbox;
using static Sandbox.Clothing;

namespace Facepunch.Gunsmith;

/// <summary>
/// We'll use this for gunsmith weapons, to designate where we can display or attach something to a weapon.
/// </summary>
public partial class GunsmithAttachmentPoint : Component
{
	[Property]
	public GunsmithPartType Category { get; set; }

	[Property]
	public GameObject CurrentGameObject { get; set; }

	[Property]
	public GunsmithPart CurrentPart { get; set; }

	/// <summary>
	/// Bumped when a point is made or destroyed, or given a part (<see cref="SetPart"/>, which ApplyAttachments also calls
	/// on the points it makes once it has set their slot): the point lists <see cref="On"/> keeps, and what's worked out
	/// from them, are good until then.
	/// </summary>
	public static int Version { get; private set; }

	protected override void OnAwake() => Version++;

	protected override void OnDestroy() => Version++;

	private static readonly Dictionary<GameObject, (int Version, GunsmithAttachmentPoint[] Points)> Lists = new();

	/// <summary>
	/// Every point on <paramref name="root"/> and under it, disabled ones too, in the order
	/// <c>Components.GetAll( FindMode.EverythingInSelfAndDescendants )</c> finds them. The list is kept until a point
	/// changes (<see cref="Version"/>), so the per-frame mounting code doesn't walk the weapon's hierarchy every time.
	/// </summary>
	public static GunsmithAttachmentPoint[] On( GameObject root )
	{
		if ( !root.IsValid() ) return Array.Empty<GunsmithAttachmentPoint>();
		if ( Lists.TryGetValue( root, out var kept ) && kept.Version == Version ) return kept.Points;
		if ( Lists.Count > 256 )
			foreach ( var dead in Lists.Keys.Where( x => !x.IsValid() ).ToList() ) Lists.Remove( dead );
		var points = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray();
		Lists[root] = (Version, points);
		return points;
	}

	/// <summary>
	/// Whether <paramref name="root"/>'s optic slot, and its barrel or muzzle slot, hold a part that switches the weapon's
	/// own bodygroups (<see cref="GunsmithPart.ModifyBodygroups"/>).
	/// </summary>
	public static (bool Optic, bool Muzzle) BodygroupParts( GameObject root )
	{
		var optic = false;
		var muzzle = false;
		foreach ( var point in On( root ) )
		{
			if ( !point.CurrentPart.IsValid() || !point.CurrentPart.ModifyBodygroups ) continue;
			if ( point.Category == GunsmithPartType.Optic ) optic = true;
			if ( point.Category is GunsmithPartType.Barrel or GunsmithPartType.Muzzle ) muzzle = true;
		}
		return (optic, muzzle);
	}

	private static readonly Dictionary<Model, bool> MuzzleGroups = new();

	/// <summary>
	/// Puts the weapon's factory "muzzle" bodygroup back, as the world model and the viewmodel do every frame while no
	/// fitted part switches it. A model without the group is skipped: setting a group it hasn't got does nothing.
	/// </summary>
	internal static void ResetFactoryMuzzle( SkinnedModelRenderer renderer )
	{
		var model = renderer.Model;
		if ( model is null ) return;
		if ( !MuzzleGroups.TryGetValue( model, out var has ) )
			MuzzleGroups[model] = has = model.Parts.Get( "muzzle" ) is not null;
		if ( has ) renderer.SetBodyGroup( "muzzle", 0 );
	}

	/// <summary> The first point in <paramref name="category"/> on <paramref name="root"/> (<see cref="On"/>), or null. </summary>
	public static GunsmithAttachmentPoint First( GameObject root, GunsmithPartType category )
	{
		foreach ( var point in On( root ) )
			if ( point.Category == category ) return point;
		return null;
	}

	/// <summary>
	/// For weapons other than the M4 that take its MW22 parts: the bone the parts follow instead of the M4's
	/// weapon_root. A weapon with this set has none of the M4's factory pieces to swap. A missing bone (e.g. on a
	/// single-bone world model) mounts on the model itself.
	/// </summary>
	[Property, Group( "MW22 Mount" )]
	public string MountBone { get; set; }

	/// <summary>
	/// Where this weapon's mount sits relative to the M4's, in the model's bind space.
	/// </summary>
	[Property, Group( "MW22 Mount" )]
	public Vector3 MountOffset { get; set; }

	/// <summary>
	/// Weapon bodygroups switched to these choices while this slot holds a part, and back to 0 while it's empty,
	/// e.g. a rail that's only there under an optic. Where several fitted slots set the same bodygroup, the highest
	/// choice wins, so such choices run from most to least shown (a muzzle tip: factory, a longer barrel's, none).
	/// </summary>
	[Property]
	public Dictionary<string, int> FittedBodygroups { get; set; } = new();

	/// <summary>
	/// A sticker point's room: how wide (along the point's local Y) and high (along its Z) the flat patch it sits on
	/// is, in the model's units. The point's +X is the patch's outward normal. <see cref="GunsmithSticker"/> fits the
	/// artwork inside it at the artwork's own shape.
	/// </summary>
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Sticker )]
	public Vector2 StickerSize { get; set; } = new( 1.5f, 1.5f );

	/// <summary>
	/// The bone a sticker rides when the point can't sit under that bone's object: the point is then a child of the
	/// model's own object, placed in the model's bind space, and <see cref="GunsmithSticker"/> follows the bone's
	/// animation from there. The older guns' viewmodels use it, since their bone objects' frames differ gun to gun.
	/// Empty: the sticker stays on the point.
	/// </summary>
	[Property, ShowIf( nameof( Category ), GunsmithPartType.Sticker )]
	public string StickerBone { get; set; }

	/// <summary>
	/// An Optic point's tuned Eye Position (<see cref="OpticTuning"/>): how far the optic slides along the bore from where
	/// it mounts, in inches, forward positive. Set with the build by <see cref="GunsmithLoadoutManager.ApplyAttachments"/>.
	/// </summary>
	public float OpticRailShift { get; set; }

	/// <summary>The fitted barrel's <see cref="GunsmithPart.MuzzleShift"/> on this weapon, zero for the factory barrel.</summary>
	public static Vector3 MuzzleShift( GameObject weapon ) => FittedBarrel( On( weapon ) )?.MuzzleShift ?? Vector3.Zero;

	/// <summary>
	/// Where the shots leave the fitted barrel, from the factory muzzle: its <see cref="GunsmithPart.MuzzleShift"/>, plus
	/// its own flash hider's <see cref="GunsmithPart.TipShift"/> while no muzzle device is fitted. Zero for the factory barrel.
	/// </summary>
	public static Vector3 DischargeShift( GameObject weapon )
	{
		var points = On( weapon );
		var barrel = FittedBarrel( points );
		if ( !barrel.IsValid() ) return Vector3.Zero;
		var device = false;
		foreach ( var point in points )
			device |= point.Category == GunsmithPartType.Muzzle && point.CurrentPart.IsValid();
		return device ? barrel.MuzzleShift : barrel.MuzzleShift + barrel.TipShift;
	}

	private static GunsmithPart FittedBarrel( GunsmithAttachmentPoint[] points )
	{
		foreach ( var point in points )
			if ( point.Category == GunsmithPartType.Barrel && point.CurrentPart.IsValid() ) return point.CurrentPart;
		return null;
	}

	/// <summary>
	/// Set the gunsmith part to this part
	/// </summary>
	/// <param name="part"></param>
	public void SetPart( GunsmithPart part )
	{
		Version++;
		if ( CurrentGameObject.IsValid() )
		{
			CurrentGameObject.Components.Get<GunsmithAttachment>( FindMode.EverythingInSelf )?.Unequip();
			CurrentGameObject.Destroy();
		}

		var previousPart = CurrentPart;
		CurrentPart = part;

		ApplyBodygroups( previousPart );

		if ( CurrentPart is null )
		{
			CurrentGameObject = null;
			return;
		}

		if ( CurrentPart.MainPrefab.IsValid() )
		{
			CurrentGameObject = CurrentPart.MainPrefab.Clone( new CloneConfig()
			{
				Transform = new(),
				Parent = GameObject,
				StartEnabled = true,
			} );

			// Viewmodels render in the overlay pass. Their attachments must share it
			// or the gun draws over the new meshes regardless of their actual depth.
			var weaponRenderer = GetComponentInParent<SkinnedModelRenderer>( true );
			if ( weaponRenderer.IsValid() )
			{
				foreach ( var renderer in CurrentGameObject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				{
					renderer.RenderOptions.Game = weaponRenderer.RenderOptions.Game;
					renderer.RenderOptions.Overlay = weaponRenderer.RenderOptions.Overlay;
					renderer.RenderType = weaponRenderer.RenderType;
				}
			}

			// Equipment applies world-model loadouts before enabling their root.
			var attachment = CurrentGameObject.Components.Get<GunsmithAttachment>( FindMode.EverythingInSelf );
			if ( attachment.IsValid() )
			{
				attachment.Initialize( this );
			}
		}

	}

	/// <summary>Resolve the whole fitted build together so changing slots in either order gives the same mesh choices.</summary>
	private readonly HashSet<string> modifiedBodygroups = new();

	internal void ApplyBodygroups( GunsmithPart previousPart = null )
	{
		var renderer = GetComponentInParent<SkinnedModelRenderer>( true );
		if ( !renderer.IsValid() ) return;
		var points = renderer.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).ToArray();
		var choices = new Dictionary<string, int>();
		void Remember( GunsmithAttachmentPoint point, GunsmithPart part )
		{
			if ( !part.IsValid() || !part.ModifyBodygroups ) return;
			point.modifiedBodygroups.UnionWith( part.GetBodygroups( renderer.Model ).Keys );
			point.modifiedBodygroups.UnionWith( part.OpticBodygroups.Keys );
		}
		Remember( this, previousPart );
		// Reset only groups this build has touched; unrelated factory choices stay intact.
		foreach ( var point in points )
		{
			Remember( point, point.CurrentPart );
			foreach ( var key in point.modifiedBodygroups ) choices.TryAdd( key, 0 );
			foreach ( var key in point.FittedBodygroups.Keys ) choices.TryAdd( key, 0 );
		}
		var optic = points.Any( p => p.Category == GunsmithPartType.Optic && p.CurrentPart.IsValid() );
		void Merge( IReadOnlyDictionary<string, int> groups )
		{
			foreach ( var group in groups ) choices[group.Key] = Math.Max( choices.GetValueOrDefault( group.Key ), group.Value );
		}
		foreach ( var point in points.Where( p => p.CurrentPart.IsValid() ) )
		{
			Merge( point.FittedBodygroups );
			if ( !point.CurrentPart.ModifyBodygroups ) continue;
			Merge( point.CurrentPart.GetBodygroups( renderer.Model ) );
			if ( optic ) Merge( point.CurrentPart.OpticBodygroups );
		}
		foreach ( var choice in choices )
		{
			if ( int.TryParse( choice.Key, out var index ) ) renderer.SetBodyGroup( index, choice.Value );
			else renderer.SetBodyGroup( choice.Key, choice.Value );
		}
	}
}
