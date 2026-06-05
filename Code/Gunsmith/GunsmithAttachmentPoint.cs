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
	/// Set the gunsmith part to this part
	/// </summary>
	/// <param name="part"></param>
	public void SetPart( GunsmithPart part )
	{
		if ( CurrentGameObject.IsValid() )
		{
			CurrentGameObject.Destroy();
		}

		CurrentPart = part;

		ResetCategoryBodygroups();

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

			var attachment = CurrentGameObject.GetComponent<GunsmithAttachment>();
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

	private void ApplyBodygroups()
	{
		if ( !CurrentPart.IsValid() || CurrentPart.Bodygroups is null )
			return;

		var renderer = GetComponentInParent<SkinnedModelRenderer>();
		if ( !renderer.IsValid() )
		{
			Log.Warning( $"ApplyBodygroups FAILED: SkinnedModelRenderer not found on parent of {GameObject.Name}" );
			return;
		}

		Log.Warning( $"ApplyBodygroups on {renderer.GameObject.Name}: before BodyGroups={renderer.BodyGroups}" );
		foreach ( var kv in CurrentPart.Bodygroups )
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

		var renderer = GetComponentInParent<SkinnedModelRenderer>();
		if ( !renderer.IsValid() )
		{
			Log.Warning( $"ResetBodygroups FAILED: SkinnedModelRenderer not found on parent of {GameObject.Name}" );
			return;
		}

		Log.Warning( $"ResetBodygroups on {renderer.GameObject.Name}: before BodyGroups={renderer.BodyGroups}" );
		// Reset effected bodygroups
		foreach ( var kv in part.Bodygroups )
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
		if ( !GunsmithPart.Categories.TryGetValue( Category, out var parts ) || parts is null )
			return;

		var resource = GetComponentInParent<GunsmithWeapon>()?.Resource ??
		               GetComponentInParent<Equipment>()?.Resource;

		foreach ( var part in parts )
		{
			if ( resource.IsValid() && !part.Supports( resource ) )
				continue;

			ResetBodygroups( part );
		}
	}
}
