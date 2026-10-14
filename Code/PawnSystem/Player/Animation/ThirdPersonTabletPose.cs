namespace Facepunch;

/// <summary>Hold the drone station by both side grips, after the body's animation has been evaluated.</summary>
public sealed class ThirdPersonTabletPose
{
	private Model _model;
	private SkinnedModelRenderer _body;
	private BoneCollection.Bone[] _bones = Array.Empty<BoneCollection.Bone>();
	private Transform[] _pose = Array.Empty<Transform>();
	private GameObject[] _boneObjects = Array.Empty<GameObject>();
	private Arm _left, _right;

	private sealed class Arm
	{
		public int Upper, Lower, Hand;
		public int[] Bones, Segments;
		public Rotation PalmFrame;
	}

	public void Apply( SkinnedModelRenderer body, WorldModel station )
	{
		if ( !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null || !station.IsValid() ) return;
		if ( _body != body || _model != body.Model ) Build( body );
		if ( _left is null || _right is null ) return;
		foreach ( var bone in _bones )
			_pose[bone.Index] = body.TryGetBoneTransformAnimation( bone, out var pose )
				? pose : body.WorldTransform.ToWorld( bone.LocalTransform );

		// The shoulder height follows crouching and the torso animation. The screen faces back towards the operator.
		var shoulders = (_pose[_left.Upper].Position + _pose[_right.Upper].Position) * .5f;
		var frame = StationTransform( body.WorldTransform, shoulders );
		PoseArm( _left, frame, body.WorldRotation, 1 );
		PoseArm( _right, frame, body.WorldRotation, -1 );

		WriteArm( _left );
		WriteArm( _right );
		// The model is parented to the right hand's socket; place it after updating that hand.
		station.WorldTransform = frame;
		// Clothing was bone-merged before this pose, so bring sleeves and gloves onto the same hands.
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
			if ( garment != body && garment.Enabled && garment.BoneMergeTarget == body && garment.SceneModel.IsValid() )
				garment.SceneModel.MergeBones( body.SceneModel );
	}

	private void WriteArm( Arm arm )
	{
		foreach ( var index in arm.Bones )
		{
			_body.SceneModel.SetBoneWorldTransform( index, _pose[index] );
			if ( _boneObjects[index].IsValid() ) _boneObjects[index].WorldTransform = _pose[index];
		}
	}

	internal static Transform StationTransform( Transform body, Vector3 shoulders ) => new(
		shoulders + body.Rotation * (body.Scale * new Vector3( 12f, 0f, -8f )),
		body.Rotation * Rotation.FromPitch( 32f ), body.Scale );

	internal static void SolveArm( Transform upper, Transform lower, Transform hand, Vector3 wrist, Vector3 pole,
		Rotation handRotation, out Transform solvedUpper, out Transform solvedLower, out Transform solvedHand )
	{
		solvedUpper = upper;
		solvedLower = lower;
		solvedHand = hand;
		var a = upper.Position.Distance( lower.Position );
		var b = lower.Position.Distance( hand.Position );
		var delta = wrist - upper.Position;
		if ( a < .001f || b < .001f || delta.IsNearZeroLength ) return;
		var distance = delta.Length.Clamp( MathF.Abs( a - b ) + .001f, a + b - .001f );
		var direction = delta.Normal;
		wrist = upper.Position + direction * distance;
		var bend = pole - direction * pole.Dot( direction );
		if ( bend.IsNearZeroLength ) bend = Vector3.Up - direction * direction.z;
		if ( bend.IsNearZeroLength ) bend = Vector3.Forward - direction * direction.x;
		var along = (a * a + distance * distance - b * b) / (2f * distance);
		var elbow = upper.Position + direction * along + bend.Normal * MathF.Sqrt( MathF.Max( 0f, a * a - along * along ) );
		solvedUpper = upper.WithRotation( Rotation.FromToRotation( lower.Position - upper.Position, elbow - upper.Position ) * upper.Rotation );
		solvedLower = lower.WithPosition( elbow ).WithRotation( Rotation.FromToRotation( hand.Position - lower.Position, wrist - elbow ) * lower.Rotation );
		solvedHand = hand.WithPosition( wrist ).WithRotation( handRotation );
	}

	private void PoseArm( Arm arm, Transform frame, Rotation facing, int sign )
	{
		var upper = _pose[arm.Upper];
		var lower = _pose[arm.Lower];
		var hand = _pose[arm.Hand];
		var wrist = frame.PointToWorld( new Vector3( -.2f, sign * 8.6f, -1.6f ) );
		var pole = facing * new Vector3( 0f, sign * 12f, -20f );
		var pointing = new Vector3( .75f, -sign * .35f, .55f ).Normal;
		var handRotation = frame.Rotation * Rotation.LookAt( pointing, Vector3.Left ) * arm.PalmFrame.Inverse
			* _model.GetBoneTransform( arm.Hand ).Rotation;
		SolveArm( upper, lower, hand, wrist, pole, handRotation, out var solvedUpper, out var solvedLower, out var solvedHand );
		foreach ( var index in arm.Bones )
		{
			var segment = arm.Segments[index];
			var original = segment == 0 ? upper : segment == 1 ? lower : hand;
			var solved = segment == 0 ? solvedUpper : segment == 1 ? solvedLower : solvedHand;
			_pose[index] = solved.ToWorld( original.ToLocal( _pose[index] ) );
		}
	}

	private void Build( SkinnedModelRenderer body )
	{
		_body = body;
		_model = body.Model;
		_bones = _model.Bones.AllBones.OrderBy( b => Depth( b.Index ) ).ToArray();
		_pose = new Transform[_model.BoneCount];
		_boneObjects = new GameObject[_model.BoneCount];
		foreach ( var bone in _bones ) _boneObjects[bone.Index] = body.GetBoneObject( bone.Index );
		_left = BuildArm( "L" );
		_right = BuildArm( "R" );
	}

	private Arm BuildArm( string side )
	{
		var upper = _model.Bones.GetBone( "arm_upper_" + side );
		var lower = _model.Bones.GetBone( "arm_lower_" + side );
		var hand = _model.Bones.GetBone( "hand_" + side );
		var middle = _model.Bones.GetBone( "finger_middle_0_" + side );
		var index = _model.Bones.GetBone( "finger_index_0_" + side );
		var pinky = _model.Bones.GetBone( "finger_pinky_0_" + side );
		if ( upper is null || lower is null || hand is null || middle is null || index is null || pinky is null ) return null;
		var forward = (middle.LocalTransform.Position - hand.LocalTransform.Position).Normal;
		var across = pinky.LocalTransform.Position - index.LocalTransform.Position;
		var arm = new Arm { Upper = upper.Index, Lower = lower.Index, Hand = hand.Index,
			PalmFrame = Rotation.LookAt( forward, Vector3.Cross( forward, across ).Normal ),
			Bones = _bones.Where( b => Under( b.Index, upper.Index ) ).Select( b => b.Index ).ToArray(),
			Segments = new int[_model.BoneCount] };
		foreach ( var bone in arm.Bones ) arm.Segments[bone] = Under( bone, hand.Index ) ? 2 : Under( bone, lower.Index ) ? 1 : 0;
		return arm;
	}

	private bool Under( int index, int ancestor )
	{
		for ( var i = index; i >= 0; i = _model.GetBoneParent( i ) ) if ( i == ancestor ) return true;
		return false;
	}

	private int Depth( int index )
	{
		var depth = 0;
		for ( var i = _model.GetBoneParent( index ); i >= 0; i = _model.GetBoneParent( i ) ) depth++;
		return depth;
	}
}
