namespace Facepunch.Gunsmith;

/// <summary>Follows the M4A1's animated stock, with a bind-pose mount for its static world model.</summary>
public sealed class GunsmithStockAttachment : GunsmithAttachment
{
	[Property] public Vector3 StaticMount { get; set; } = new( -6.21926f, 0, 7.4147f );
	[Property] public Model WorldBodyReplacement { get; set; }
	private SkinnedModelRenderer weaponRenderer;
	private ModelRenderer replacementBody;
	private ulong replacedMask;
	private bool originalBaseVisible;

	protected override void OnInitialize()
	{
		weaponRenderer = AttachmentPoint?.GetComponentInParent<SkinnedModelRenderer>( true );
		// The world asset bakes the factory stock into its main mesh. Replace only
		// that mesh; the original magazine, sights and other bodygroups stay intact.
		if ( weaponRenderer.IsValid() && weaponRenderer.Model?.Name == "models/weapons/sbox_assault_m4a1/w_m4a1.vmdl"
			&& WorldBodyReplacement is not null && !WorldBodyReplacement.IsError && !replacementBody.IsValid() )
		{
			replacedMask = weaponRenderer.Model.Parts.Get( "M4A1" ).Mask;
			originalBaseVisible = (weaponRenderer.BodyGroups & replacedMask) != 0;
			var body = new GameObject( GameObject, true, "Stockless world body" );
			replacementBody = body.Components.Create<ModelRenderer>();
			replacementBody.Model = WorldBodyReplacement;
			replacementBody.RenderOptions.Game = weaponRenderer.RenderOptions.Game;
			replacementBody.RenderOptions.Overlay = weaponRenderer.RenderOptions.Overlay;
			replacementBody.RenderType = weaponRenderer.RenderType;
		}
		FollowStock();
	}

	protected override void OnUpdate() => FollowStock();

	private void FollowStock()
	{
		if ( !weaponRenderer.IsValid() ) return;
		if ( weaponRenderer.TryGetBoneTransform( "stock", out var stock ) )
		{
			WorldPosition = stock.Position;
			WorldRotation = stock.Rotation * Rotation.FromYaw( 180 );
		}
		else
		{
			WorldPosition = weaponRenderer.WorldTransform.PointToWorld( StaticMount );
			WorldRotation = weaponRenderer.WorldRotation;
		}
		WorldScale = weaponRenderer.WorldScale;
		if ( replacementBody.IsValid() )
		{
			replacementBody.WorldTransform = weaponRenderer.WorldTransform;
			weaponRenderer.BodyGroups &= ~replacedMask;
		}
	}

	public override void Unequip()
	{
		if ( weaponRenderer.IsValid() && replacedMask != 0 && originalBaseVisible )
			weaponRenderer.BodyGroups |= replacedMask;
		replacedMask = 0;
	}

	protected override void OnDestroy() => Unequip();
}
