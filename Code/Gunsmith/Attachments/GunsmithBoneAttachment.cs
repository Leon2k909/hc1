namespace Facepunch.Gunsmith;

/// <summary>Art authored in weapon bind space, following the animated grip or magazine bone.</summary>
public sealed class GunsmithBoneAttachment : GunsmithAttachment, ICameraSetup
{
	[Property] public string BoneName { get; set; }
	[Property] public string HiddenBodygroup { get; set; }
	[Property] public string HiddenBone { get; set; }
	[Property] public System.Collections.Generic.Dictionary<string, Model> ModelVariants { get; set; } = new();
	/// <summary>Mount the attachment origin at the named bone instead of preserving weapon bind-space origin.</summary>
	[Property] public bool MountAtBone { get; set; }
	[Property] public bool UseWeaponOrigin { get; set; }
	[Property] public Vector3 WeaponSpaceOffset { get; set; }
	[Property] public float WeaponSpaceScale { get; set; } = 1f;
	[Property] public bool FitMp5MuzzleToBarrel { get; set; }
	[Property, ShowIf( nameof( MountAtBone ), true )] public Vector3 BoneOffset { get; set; }
	[Property, ShowIf( nameof( MountAtBone ), true )] public Angles BoneAngles { get; set; }
	[Property, ShowIf( nameof( MountAtBone ), true )] public Vector3 ModelScaleMultiplier { get; set; } = Vector3.One;
	private SkinnedModelRenderer weaponRenderer;
	private GunsmithAttachmentPoint mp5BarrelPoint;
	private Transform bindPose;
	private bool hasBone;
	private ulong hiddenMask;
	private ulong originalChoice;
	private Transform? originalHiddenBoneTransform;

	protected override void OnInitialize()
	{
		weaponRenderer = AttachmentPoint?.GetComponentInParent<SkinnedModelRenderer>( true );
		if ( !weaponRenderer.IsValid() || weaponRenderer.Model is null ) return;
		var model = weaponRenderer.Model;
		if ( FitMp5MuzzleToBarrel )
			mp5BarrelPoint = weaponRenderer.GameObject.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
				.FirstOrDefault( p => p.Category == GunsmithPartType.Barrel );
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

	// Viewmodels are repositioned by camera setup after the regular update.
	void ICameraSetup.PostSetup( CameraComponent cc )
	{
		GunsmithMw22Attachment.FollowingCamera = true;
		try { RefreshMount(); }
		finally { GunsmithMw22Attachment.FollowingCamera = false; }
	}

	public void RefreshMount()
	{
		if ( !weaponRenderer.IsValid() ) return;
		if ( UseWeaponOrigin )
		{
			var root = GunsmithMw22Attachment.BoneDelta( weaponRenderer, "weapon_root" );
			WorldTransform = root;
			var offset = WeaponSpaceOffset;
			if ( FitMp5MuzzleToBarrel && mp5BarrelPoint.IsValid() )
			{
				var barrel = mp5BarrelPoint.CurrentPart?.ResourcePath;
				// Devices sit against the barrel part's front face (printed by Tools/fit_mp5_barrels.py).
				// The rail grip keeps the MP5's own barrel, so its muzzle stays put.
				if ( barrel?.EndsWith( "/barrel_short.gnsmth", System.StringComparison.OrdinalIgnoreCase ) == true )
					offset += new Vector3( -1.22f, 0, 0 );
				else if ( barrel?.EndsWith( "/barrel_integral_suppressor.gnsmth", System.StringComparison.OrdinalIgnoreCase ) == true )
					offset += new Vector3( 5.31f, 0, 0 );
				else if ( barrel?.EndsWith( "/barrel_monolithic_suppressor.gnsmth", System.StringComparison.OrdinalIgnoreCase ) == true )
					offset += new Vector3( 1.71f, 0, 0 );
			}
			WorldPosition = root.PointToWorld( offset );
			WorldScale = root.Scale * WeaponSpaceScale;
			weaponRenderer.BodyGroups &= ~hiddenMask;
			RefreshHiddenBone();
			return;
		}
		if ( hasBone && weaponRenderer.TryGetBoneTransform( BoneName, out var current ) )
		{
			if ( MountAtBone )
			{
				WorldPosition = current.PointToWorld( BoneOffset );
				WorldRotation = current.Rotation * Rotation.From( BoneAngles );
				WorldScale = current.Scale * ModelScaleMultiplier;
			}
			else
			{
				WorldPosition = current.PointToWorld( bindPose.PointToLocal( Vector3.Zero ) );
				WorldRotation = current.Rotation * bindPose.Rotation.Inverse;
				WorldScale = current.Scale / bindPose.Scale;
			}
		}
		else if ( MountAtBone )
		{
			var transform = weaponRenderer.WorldTransform;
			WorldPosition = transform.PointToWorld( BoneOffset );
			WorldRotation = transform.Rotation * Rotation.From( BoneAngles );
			WorldScale = weaponRenderer.WorldScale * ModelScaleMultiplier;
		}
		else WorldTransform = weaponRenderer.WorldTransform;
		weaponRenderer.BodyGroups &= ~hiddenMask;
		RefreshHiddenBone();
	}

	private void RefreshHiddenBone()
	{
		if ( string.IsNullOrEmpty( HiddenBone ) || weaponRenderer.Model is null
			|| !weaponRenderer.Model.Bones.HasBone( HiddenBone ) ) return;
		var bone = weaponRenderer.Model.Bones.GetBone( HiddenBone );
		if ( !weaponRenderer.TryGetBoneTransformAnimation( bone, out var animated ) ) return;
		// Keep the pre-attachment pose. Later animation queries can include our
		// collapsed override, which would leave the bone hidden on unequip.
		if ( !originalHiddenBoneTransform.HasValue ) originalHiddenBoneTransform = animated;
		weaponRenderer.SetBoneTransform( bone, animated.WithScale( Vector3.One * 0.001f ) );
	}

	public override void Unequip()
	{
		if ( weaponRenderer.IsValid() && hiddenMask != 0 )
			weaponRenderer.BodyGroups = (weaponRenderer.BodyGroups & ~hiddenMask) | originalChoice;
		if ( weaponRenderer.IsValid() && originalHiddenBoneTransform.HasValue
			&& weaponRenderer.Model is not null && weaponRenderer.Model.Bones.HasBone( HiddenBone ) )
			weaponRenderer.SetBoneTransform( weaponRenderer.Model.Bones.GetBone( HiddenBone ), originalHiddenBoneTransform.Value );
		originalHiddenBoneTransform = null;
		hiddenMask = 0;
	}

	protected override void OnDestroy() => Unequip();
}
