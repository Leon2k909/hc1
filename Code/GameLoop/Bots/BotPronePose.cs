namespace Facepunch;

/// <summary>A prone firing pose for the human and legacy rigs, applied after their normal animation.</summary>
public sealed class BotPronePose
{
	public static readonly Vector3 ProneEye = new( 24f, 0f, 24f );
	private Model _model;
	private SkinnedModelRenderer _body;
	private BoneCollection.Bone _pelvis, _neck;
	private BoneCollection.Bone[] _bones = Array.Empty<BoneCollection.Bone>();
	private bool[] _head = Array.Empty<bool>();
	private Transform[] _pose = Array.Empty<Transform>();
	private readonly List<SkinnedModelRenderer> _garments = new();

	public static Vector3 EyeOffset( bool crouching, float blend )
	{
		blend = blend.Clamp( 0f, 1f );
		var heightBlend = (1f - MathF.Cos( (80f * blend).DegreeToRadian() )) / (1f - MathF.Cos( 80f.DegreeToRadian() ));
		return new Vector3( ProneEye.x * blend, 0f, MathX.Lerp( crouching ? 44f : 64f, ProneEye.z, heightBlend ) );
	}

	public static BBox MovementBounds( bool crouching, float blend )
	{
		blend = blend.Clamp( 0f, 1f );
		var height = EyeOffset( crouching, blend ).z;
		var halfLength = MathX.Lerp( 16f, 44f, blend );
		var centre = new Vector3( -6f * blend, 0f, height * 0.5f );
		return BBox.FromPositionAndSize( centre, new Vector3( halfLength * 2f, 32f, height ) );
	}

	/// <summary>A rigid change of frame preserves the skeleton's lengths throughout the transition.</summary>
	internal static Transform PoseSpace( Transform root, Vector3 pelvis, float blend )
	{
		blend = blend.Clamp( 0f, 1f );
		var hips = root.PointToLocal( pelvis );
		var angle = (80f * blend).DegreeToRadian();
		var endAngle = 80f.DegreeToRadian();
		var lift = (12f - hips.z * MathF.Cos( endAngle )) / MathF.Sin( endAngle );
		// A straight downward lerp sinks the feet through the floor halfway down. Follow the rotation's arc instead.
		var height = hips.z * MathF.Cos( angle ) + lift * MathF.Sin( angle );
		var position = root.PointToWorld( new Vector3( MathX.Lerp( hips.x, -8f, blend ), hips.y * (1f - blend), height ) );
		return new Transform( position, root.Rotation * Rotation.FromPitch( 80f * blend ), root.Scale );
	}

	internal static Transform PoseBone( Transform bone, Transform from, Transform to, Vector3 neck, Rotation headLift, bool head )
	{
		var pose = to.ToWorld( from.ToLocal( bone ) );
		return head ? pose.WithPosition( neck + headLift * (pose.Position - neck) ).WithRotation( headLift * pose.Rotation ) : pose;
	}

	public void Apply( SkinnedModelRenderer body, float blend )
	{
		if ( blend <= 0f || !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null ) return;
		if ( _model != body.Model || _body != body ) Build( body );
		if ( _pelvis is null || _neck is null ) return;

		var scene = body.SceneModel;
		var root = body.WorldTransform;
		var hips = ReadAnimation( body, _pelvis ).Position;
		var from = new Transform( hips, root.Rotation, root.Scale );
		var to = PoseSpace( root, hips, blend );
		// Lift the head from the lowered torso so it can look along the sights.
		var neck = to.PointToWorld( from.PointToLocal( ReadAnimation( body, _neck ).Position ) );
		var headLift = root.Rotation * Rotation.FromPitch( -80f * blend ) * root.Rotation.Inverse;
		for ( var i = 0; i < _bones.Length; i++ )
		{
			_pose[i] = PoseBone( ReadAnimation( body, _bones[i] ), from, to, neck, headLift, _head[i] );
		}
		// Snapshot first: changing a parent may propagate to its descendants.
		for ( var i = 0; i < _bones.Length; i++ ) scene.SetBoneWorldTransform( _bones[i].Index, _pose[i] );
		foreach ( var garment in _garments )
		{
			if ( garment.IsValid() && garment.Enabled && garment.BoneMergeTarget == body && garment.SceneModel.IsValid() )
				garment.SceneModel.MergeBones( scene );
		}
	}

	private void Build( SkinnedModelRenderer body )
	{
		_body = body;
		_model = body.Model;
		_pelvis = _model.Bones.GetBone( "pelvis" );
		_neck = _model.Bones.GetBone( "neck_0" ) ?? _model.Bones.GetBone( "neck" );
		_bones = _model.Bones.AllBones.OrderBy( b => Depth( b.Index ) ).ToArray();
		_head = _bones.Select( b => Under( b.Index, _neck?.Index ?? -1 ) ).ToArray();
		_pose = new Transform[_bones.Length];
		_garments.Clear();
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>() )
			if ( garment != body && garment.BoneMergeTarget == body ) _garments.Add( garment );
	}

	// Read the unmodified animation even when the engine reuses a pose for LOD: never flatten last frame's prone pose again.
	private static Transform ReadAnimation( SkinnedModelRenderer body, BoneCollection.Bone bone ) =>
		body.TryGetBoneTransformAnimation( bone, out var pose ) ? pose : body.WorldTransform.ToWorld( bone.LocalTransform );

	private bool Under( int bone, int parent )
	{
		if ( parent < 0 ) return false;
		for ( var i = bone; i >= 0; i = _model.GetBoneParent( i ) ) if ( i == parent ) return true;
		return false;
	}

	private int Depth( int bone )
	{
		var depth = 0;
		for ( var i = _model.GetBoneParent( bone ); i >= 0; i = _model.GetBoneParent( i ) ) depth++;
		return depth;
	}
}
