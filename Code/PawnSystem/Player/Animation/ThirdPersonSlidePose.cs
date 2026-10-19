namespace Facepunch;

/// <summary>A hip slide layered over the weapon animation, for both human and legacy player skeletons.</summary>
public sealed class ThirdPersonSlidePose
{
	private Model _model;
	private SkinnedModelRenderer _body;
	private int _pelvis = -1, _neck = -1;
	private BoneCollection.Bone[] _bones = Array.Empty<BoneCollection.Bone>();
	private Transform[] _pose = Array.Empty<Transform>();
	private GameObject[] _boneObjects = Array.Empty<GameObject>();
	private bool[] _head = Array.Empty<bool>();
	private bool _updateBoneObjects;
	private Leg _left, _right;

	private sealed class Leg
	{
		public int Upper, Lower, Foot;
		public int[] Bones, Segments;
	}

	internal static Transform HipSpace( Transform root, Vector3 hips, float blend )
	{
		blend = blend.Clamp( 0f, 1f );
		var weight = blend * blend * (3f - 2f * blend);
		// Sit onto the right hip, with the shoulders leaning back over the trailing arm.
		// The old shallow tilt left the character looking like a crouch hovering above the ground.
		var position = Vector3.Lerp( root.PointToLocal( hips ), new Vector3( -3f, -4f, 10f ), weight );
		return root.ToWorld( new Transform( position, Rotation.From( -27f * weight, 0f, -15f * weight ) ) );
	}

	/// <summary>Solve a knee without changing either segment's length, even when a target is out of reach.</summary>
	internal static void SolveLeg( Transform upper, Transform lower, Transform foot, Vector3 target, Vector3 pole,
		Rotation footRotation, out Transform solvedUpper, out Transform solvedLower, out Transform solvedFoot )
	{
		solvedUpper = upper;
		solvedLower = lower;
		solvedFoot = foot;
		var a = upper.Position.Distance( lower.Position );
		var b = lower.Position.Distance( foot.Position );
		var delta = target - upper.Position;
		if ( a < .001f || b < .001f || delta.IsNearZeroLength ) return;
		var direction = delta.Normal;
		var distance = delta.Length.Clamp( MathF.Abs( a - b ) + .001f, a + b - .001f );
		var ankle = upper.Position + direction * distance;
		var bend = pole - direction * pole.Dot( direction );
		if ( bend.Length < .001f ) bend = lower.Position - upper.Position - direction * (lower.Position - upper.Position).Dot( direction );
		if ( bend.Length < .001f ) bend = Vector3.Up - direction * direction.z;
		if ( bend.Length < .001f ) bend = Vector3.Forward - direction * direction.x;
		var along = (a * a + distance * distance - b * b) / (2f * distance);
		var knee = upper.Position + direction * along + bend.Normal * MathF.Sqrt( MathF.Max( 0f, a * a - along * along ) );
		solvedUpper = upper.WithRotation( Rotation.FromToRotation( lower.Position - upper.Position, knee - upper.Position ) * upper.Rotation );
		solvedLower = lower.WithPosition( knee ).WithRotation( Rotation.FromToRotation( foot.Position - lower.Position, ankle - knee ) * lower.Rotation );
		solvedFoot = foot.WithPosition( ankle ).WithRotation( footRotation );
	}

	internal static void SolveSlideLeg( Transform upper, Transform lower, Transform foot, Transform animatedFoot,
		Transform root, float blend, bool tucked, out Transform solvedUpper, out Transform solvedLower, out Transform solvedFoot )
	{
		blend = blend.Clamp( 0f, 1f );
		var weight = blend * blend * (3f - 2f * blend);
		var ankle = root.PointToWorld( tucked ? new Vector3( 11f, 10f, 5f ) : new Vector3( 25f, -7f, 4f ) );
		var animatedBend = lower.Position - upper.Position;
		// Spread the tucked knee sideways while the straight leg stays low instead of popping up
		// between the crouch and the full extension.
		var pole = Vector3.Lerp( animatedBend, root.Rotation * (tucked ? new Vector3( 2f, 14f, 13f ) : new Vector3( 0f, -6f, 7f )), weight );
		// Feet keep their rig's own axes; tip the extended boot's toe up and turn the tucked boot out.
		var rotation = root.Rotation * Rotation.From( tucked ? 0f : -17f * weight, tucked ? 18f * weight : 0f, 0f )
			* root.Rotation.Inverse * animatedFoot.Rotation;
		// Anchor the transition to the animated ankle, rather than the ankle lowered with the torso.
		// Otherwise the boots pass through the floor halfway into the slide.
		SolveLeg( upper, lower, foot, Vector3.Lerp( animatedFoot.Position, ankle, weight ), pole, rotation,
			out solvedUpper, out solvedLower, out solvedFoot );
	}

	public void Apply( SkinnedModelRenderer body, float blend, bool updateBoneObjects = true )
	{
		if ( blend <= 0f || !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null ) return;
		if ( _body != body || _model != body.Model || _updateBoneObjects != updateBoneObjects ) Build( body, updateBoneObjects );
		if ( _pelvis < 0 || _neck < 0 || _left is null || _right is null ) return;
		blend = blend.Clamp( 0f, 1f );

		// Always read the unmodified animation: a reused LOD pose must never slide down again each frame.
		foreach ( var bone in _bones )
			_pose[bone.Index] = body.TryGetBoneTransformAnimation( bone, out var pose )
				? pose : body.WorldTransform.ToWorld( bone.LocalTransform );
		var root = body.WorldTransform;
		var leftFoot = _pose[_left.Foot];
		var rightFoot = _pose[_right.Foot];
		var from = new Transform( _pose[_pelvis].Position, root.Rotation, root.Scale );
		var to = HipSpace( root, from.Position, blend );
		var neck = to.PointToWorld( from.PointToLocal( _pose[_neck].Position ) );
		var headLift = from.Rotation * to.Rotation.Inverse;
		foreach ( var bone in _bones )
		{
			var pose = to.ToWorld( from.ToLocal( _pose[bone.Index] ) );
			// Keep the animated look direction as the torso leans onto the hip.
			if ( _head[bone.Index] ) pose = pose.WithPosition( neck + headLift * (pose.Position - neck) ).WithRotation( headLift * pose.Rotation );
			_pose[bone.Index] = pose;
		}
		PoseLeg( _right, rightFoot, root, blend, false );
		PoseLeg( _left, leftFoot, root, blend, true );

		// Parents can propagate changes to children, so snapshot and solve the entire pose before writing it.
		foreach ( var bone in _bones ) body.SceneModel.SetBoneWorldTransform( bone.Index, _pose[bone.Index] );
		// The held gun and holstered equipment hang from bone GameObjects, updated before this layer runs.
		foreach ( var bone in _bones )
			if ( _boneObjects[bone.Index].IsValid() ) _boneObjects[bone.Index].WorldTransform = _pose[bone.Index];
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
			if ( garment != body && garment.IsValid() && garment.Enabled && garment.BoneMergeTarget == body && garment.SceneModel.IsValid() )
				garment.SceneModel.MergeBones( body.SceneModel );
	}

	private void PoseLeg( Leg leg, Transform animatedFoot, Transform root, float blend, bool tucked )
	{
		var upper = _pose[leg.Upper];
		var lower = _pose[leg.Lower];
		var foot = _pose[leg.Foot];
		SolveSlideLeg( upper, lower, foot, animatedFoot, root, blend, tucked,
			out var solvedUpper, out var solvedLower, out var solvedFoot );
		foreach ( var index in leg.Bones )
		{
			var segment = leg.Segments[index];
			var original = segment == 0 ? upper : segment == 1 ? lower : foot;
			var solved = segment == 0 ? solvedUpper : segment == 1 ? solvedLower : solvedFoot;
			_pose[index] = solved.ToWorld( original.ToLocal( _pose[index] ) );
		}
	}

	private void Build( SkinnedModelRenderer body, bool updateBoneObjects )
	{
		_updateBoneObjects = updateBoneObjects;
		_body = body;
		_model = body.Model;
		_pelvis = _model.Bones.GetBone( "pelvis" )?.Index ?? -1;
		_neck = (_model.Bones.GetBone( "neck_0" ) ?? _model.Bones.GetBone( "neck" ))?.Index ?? -1;
		_bones = _model.Bones.AllBones.OrderBy( b => Depth( b.Index ) ).ToArray();
		_pose = new Transform[_model.BoneCount];
		_head = new bool[_model.BoneCount];
		_boneObjects = new GameObject[_model.BoneCount];
		foreach ( var bone in _bones )
		{
			_head[bone.Index] = Under( bone.Index, _neck );
			_boneObjects[bone.Index] = updateBoneObjects ? body.GetBoneObject( bone.Index ) : null;
		}
		_left = BuildLeg( "ankle_L", "l_foot" );
		_right = BuildLeg( "ankle_R", "r_foot" );
	}

	private Leg BuildLeg( string human, string legacy )
	{
		var foot = (_model.Bones.GetBone( human ) ?? _model.Bones.GetBone( legacy ))?.Index ?? -1;
		var lower = foot < 0 ? -1 : _model.GetBoneParent( foot );
		var upper = lower < 0 ? -1 : _model.GetBoneParent( lower );
		if ( upper < 0 ) return null;
		var leg = new Leg { Upper = upper, Lower = lower, Foot = foot,
			Bones = _bones.Where( b => Under( b.Index, upper ) ).Select( b => b.Index ).ToArray(), Segments = new int[_model.BoneCount] };
		foreach ( var index in leg.Bones ) leg.Segments[index] = Under( index, foot ) ? 2 : Under( index, lower ) ? 1 : 0;
		return leg;
	}

	private bool Under( int bone, int ancestor )
	{
		if ( ancestor < 0 ) return false;
		for ( var i = bone; i >= 0; i = _model.GetBoneParent( i ) ) if ( i == ancestor ) return true;
		return false;
	}

	private int Depth( int bone )
	{
		var depth = 0;
		for ( var i = _model.GetBoneParent( bone ); i >= 0; i = _model.GetBoneParent( i ) ) depth++;
		return depth;
	}
}

