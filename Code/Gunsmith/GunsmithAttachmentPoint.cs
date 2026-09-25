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

	/// <summary>The fitted barrel's <see cref="GunsmithPart.MuzzleShift"/> on this weapon, zero for the factory barrel.</summary>
	public static Vector3 MuzzleShift( GameObject weapon ) =>
		weapon.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
			.FirstOrDefault( p => p.Category == GunsmithPartType.Barrel && p.CurrentPart.IsValid() )?.CurrentPart.MuzzleShift
		?? Vector3.Zero;

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

		CurrentPart = part;

		ResetCategoryBodygroups();
		ApplyFittedBodygroups();

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

		if ( CurrentPart.ModifyBodygroups )
		{
			ApplyBodygroups();
		}
	}

	private void ApplyFittedBodygroups()
	{
		if ( FittedBodygroups is null || FittedBodygroups.Count == 0 )
			return;

		var renderer = GetComponentInParent<SkinnedModelRenderer>( true );
		if ( !renderer.IsValid() )
			return;

		var fitted = renderer.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
			.Where( p => p.CurrentPart.IsValid() && p.FittedBodygroups is not null ).ToList();
		foreach ( var name in FittedBodygroups.Keys )
			renderer.SetBodyGroup( name, fitted.Select( p => p.FittedBodygroups.TryGetValue( name, out var choice ) ? choice : 0 )
				.DefaultIfEmpty( 0 ).Max() );
	}

	internal void ApplyBodygroups()
	{
		ApplyFittedBodygroups();
		if ( !CurrentPart.IsValid() || !CurrentPart.ModifyBodygroups || CurrentPart.Bodygroups is null )
			return;

		var renderer = GetComponentInParent<SkinnedModelRenderer>( true );
		if ( !renderer.IsValid() )
		{
			Log.Warning( $"ApplyBodygroups FAILED: SkinnedModelRenderer not found on parent of {GameObject.Name}" );
			return;
		}

		Log.Warning( $"ApplyBodygroups on {renderer.GameObject.Name}: before BodyGroups={renderer.BodyGroups}" );
		foreach ( var kv in CurrentPart.GetBodygroups( renderer.Model ) )
		{
			if ( int.TryParse( kv.Key, out var index ) )
			{
				renderer.SetBodyGroup( index, kv.Value );
			}
			else
			{
				renderer.SetBodyGroup( kv.Key, kv.Value );
			}
			Log.Warning( $"  SetBodyGroup {kv.Key} = {kv.Value} (now BodyGroups={renderer.BodyGroups})" );
		}
	}

	private void ResetBodygroups( GunsmithPart part )
	{
		if ( !part.IsValid() || part.Bodygroups is null )
			return;

		var renderer = GetComponentInParent<SkinnedModelRenderer>( true );
		if ( !renderer.IsValid() )
		{
			Log.Warning( $"ResetBodygroups FAILED: SkinnedModelRenderer not found on parent of {GameObject.Name}" );
			return;
		}

		Log.Warning( $"ResetBodygroups on {renderer.GameObject.Name}: before BodyGroups={renderer.BodyGroups}" );
		// Reset effected bodygroups
		foreach ( var kv in part.GetBodygroups( renderer.Model ) )
		{
			if ( int.TryParse( kv.Key, out var index ) )
			{
				renderer.SetBodyGroup( index, 0 );
			}
			else
			{
				renderer.SetBodyGroup( kv.Key, 0 );
			}
			Log.Warning( $"  ResetBodyGroup {kv.Key} = 0 (now BodyGroups={renderer.BodyGroups})" );
		}
	}

	private void ResetCategoryBodygroups()
	{
		var parts = ResourceLibrary.GetAll<GunsmithPart>()
			.Where( part => part.IsValid() && part.Category == Category );

		var resource = GetComponentInParent<GunsmithWeapon>( true )?.Resource ??
		               GetComponentInParent<Equipment>( true )?.Resource;

		foreach ( var part in parts )
		{
			if ( resource.IsValid() && !part.Supports( resource ) )
				continue;

			ResetBodygroups( part );
		}
	}
}
