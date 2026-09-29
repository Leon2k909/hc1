namespace Facepunch;

/// <summary>Attaches a physical throwable to the animated hand in bone-local space.</summary>
public sealed class ThrowableViewModelGrip : Component, ICameraSetup
{
	[Property] public SkinnedModelRenderer Hands { get; set; }
	[Property] public ModelRenderer Item { get; set; }
	[Property] public float ItemCenterHeight { get; set; } = 2.7f;
	[Property] public Vector3 ItemOffset { get; set; }
	[Property] public Angles ItemAngleOffset { get; set; }

	void ICameraSetup.PostSetup( CameraComponent camera )
	{
		if ( !Hands.IsValid() || !Item.IsValid() ) return;
		var viewModel = GetComponent<ViewModel>();
		var throwable = viewModel?.Equipment?.GetComponentInChildren<Throwable>();
		Item.Enabled = Hands.Enabled && throwable.IsValid() && throwable.ThrowState != Throwable.State.Thrown;
		if ( !Item.Enabled ) return;

		var handObject = Hands.GetBoneObject( "hand_R" );
		if ( !handObject.IsValid()
			|| !Hands.TryGetBoneTransform( "hand_R", out var hand )
			|| !Hands.TryGetBoneTransform( "finger_index_0_R", out var index )
			|| !Hands.TryGetBoneTransform( "finger_pinky_0_R", out var pinky )
			|| !Hands.TryGetBoneTransform( "finger_middle_0_R", out var knuckle )
			|| !Hands.TryGetBoneTransform( "finger_middle_2_R", out var finger ) )
		{
			Item.Enabled = false;
			return;
		}

		// Camera setup has already moved the viewmodel, but render-bone world transforms
		// still describe its previous placement. Their relative pose is valid: cancel
		// that old placement and let the live bone hierarchy carry the item with the hand,
		// including any movement after this camera callback.
		var up = (hand.PointToLocal( index.Position ) - hand.PointToLocal( pinky.Position )).Normal;
		var rotation = Rotation.LookAt( Vector3.Forward, up );
		var centre = (hand.PointToLocal( knuckle.Position ) + hand.PointToLocal( finger.Position )) * 0.5f;
		if ( Item.GameObject.Parent != handObject ) Item.GameObject.SetParent( handObject, false );
		Item.LocalPosition = centre - rotation.Up * ItemCenterHeight + rotation * ItemOffset;
		Item.LocalRotation = rotation * ItemAngleOffset.ToRotation();
	}
}
