namespace Facepunch.Gunsmith;

/// <summary>Art authored in weapon bind space, following the animated grip or magazine bone.</summary>
public sealed class GunsmithBoneAttachment : GunsmithAttachment
{
	[Property] public string BoneName { get; set; }
	[Property] public string HiddenBodygroup { get; set; }
	[Property] public System.Collections.Generic.Dictionary<string, Model> ModelVariants { get; set; } = new();
	private SkinnedModelRenderer weaponRenderer;
	private Transform bindPose;
	private bool hasBone;
	private ulong hiddenMask;
	private ulong originalChoice;

	protected override void OnInitialize()
	{
		weaponRenderer = AttachmentPoint?.GetComponentInParent<SkinnedModelRenderer>( true );
		if ( !weaponRenderer.IsValid() || weaponRenderer.Model is null ) return;
		var model = weaponRenderer.Model;
		var renderer = Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
		if ( renderer.IsValid() && ModelVariants.TryGetValue( model.Name, out var variant ) ) renderer.Model = variant;
		for ( int i = 0; i < model.BoneCount; i++ )
		{
			if ( model.GetBoneName( i ) != BoneName ) continue;
			bindPose = model.GetBoneTransform( i );
			hasBone = true;
			break;
		}
		if ( !string.IsNullOrEmpty( HiddenBodygroup ) )
		{
			var part = model.Parts.All.FirstOrDefault( p => p.Name == HiddenBodygroup );
			if ( part is not null )
			{
				hiddenMask = part.Mask;
				originalChoice = weaponRenderer.BodyGroups & hiddenMask;
			}
		}
		RefreshMount();
	}

	protected override void OnUpdate() => RefreshMount();

	public void RefreshMount()
	{
		if ( !weaponRenderer.IsValid() ) return;
		if ( hasBone && weaponRenderer.TryGetBoneTransform( BoneName, out var current ) )
		{
			WorldPosition = current.PointToWorld( bindPose.PointToLocal( Vector3.Zero ) );
			WorldRotation = current.Rotation * bindPose.Rotation.Inverse;
			WorldScale = current.Scale / bindPose.Scale;
		}
		else WorldTransform = weaponRenderer.WorldTransform;
		weaponRenderer.BodyGroups &= ~hiddenMask;
	}

	public override void Unequip()
	{
		if ( weaponRenderer.IsValid() && hiddenMask != 0 )
			weaponRenderer.BodyGroups = (weaponRenderer.BodyGroups & ~hiddenMask) | originalChoice;
		hiddenMask = 0;
	}

	protected override void OnDestroy() => Unequip();
}
