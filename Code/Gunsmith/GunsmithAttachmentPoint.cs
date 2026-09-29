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

	/// <summary>The fitted barrel's <see cref="GunsmithPart.MuzzleShift"/> on this weapon, zero for the factory barrel.</summary>
	public static Vector3 MuzzleShift( GameObject weapon ) =>
		weapon.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
			.FirstOrDefault( p => p.Category == GunsmithPartType.Barrel && p.CurrentPart.IsValid() )?.CurrentPart.MuzzleShift
		?? Vector3.Zero;

	/// <summary>
	/// Where the shots leave the fitted barrel, from the factory muzzle: its <see cref="GunsmithPart.MuzzleShift"/>, plus
	/// its own flash hider's <see cref="GunsmithPart.TipShift"/> while no muzzle device is fitted. Zero for the factory barrel.
	/// </summary>
	public static Vector3 DischargeShift( GameObject weapon )
	{
		var points = weapon.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray();
		var barrel = points.FirstOrDefault( p => p.Category == GunsmithPartType.Barrel && p.CurrentPart.IsValid() )?.CurrentPart;
		if ( !barrel.IsValid() ) return Vector3.Zero;
		var device = points.Any( p => p.Category == GunsmithPartType.Muzzle && p.CurrentPart.IsValid() );
		return device ? barrel.MuzzleShift : barrel.MuzzleShift + barrel.TipShift;
	}

	/// <summary>
	/// Set the gunsmith part to this part
	/// </summary>
	/// <param name="part"></param>
	public void SetPart( GunsmithPart part )
	{
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
