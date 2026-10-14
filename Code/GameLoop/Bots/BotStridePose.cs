namespace Facepunch;

/// <summary>Lengthen fast steps after animation without speeding up weapon layers or stretching the legs.</summary>
public sealed class BotStridePose
{
	private Model _model;
	private SkinnedModelRenderer _body;
	private BoneCollection.Bone[] _bones = Array.Empty<BoneCollection.Bone>();
	private Transform[] _pose = Array.Empty<Transform>();
	private readonly List<SkinnedModelRenderer> _garments = new();
	private Leg _left, _right;

	private sealed class Leg
	{
		public int Upper, Lower, Foot;
		public int[] Bones, Segments;
	}

	public void Apply( SkinnedModelRenderer body, Vector3 velocity, float scale )
	{
		if ( scale <= 1.001f || velocity.WithZ( 0f ).Length < 10f
			|| !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null ) return;
		if ( _body != body || _model != body.Model ) Build( body );
		if ( _left is null || _right is null ) return;
		scale = scale.Clamp( 1f, 1.55f );
		var direction = velocity.WithZ( 0f ).Normal;
		// A small hip drop gives the longer step room, while the two-bone solve keeps the boots at their animated height.
		var drop = body.WorldTransform.PointToWorld( Vector3.Down * (scale - 1f) * 6f ) - body.WorldPosition;
		foreach ( var bone in _bones )
		{
			var animated = body.TryGetBoneTransformAnimation( bone, out var pose )
				? pose : body.WorldTransform.ToWorld( bone.LocalTransform );
			_pose[bone.Index] = animated.WithPosition( animated.Position + drop );
		}
		PoseLeg( _left, direction, body.WorldPosition, drop, scale );
		PoseLeg( _right, direction, body.WorldPosition, drop, scale );
		foreach ( var bone in _bones ) body.SceneModel.SetBoneWorldTransform( bone.Index, _pose[bone.Index] );
		foreach ( var garment in _garments )
			if ( garment.IsValid() && garment.Enabled && garment.BoneMergeTarget == body && garment.SceneModel.IsValid() )
				garment.SceneModel.MergeBones( body.SceneModel );
	}

	private void PoseLeg( Leg leg, Vector3 direction, Vector3 origin, Vector3 drop, float scale )
	{
		var upper = _pose[leg.Upper];
		var lower = _pose[leg.Lower];
		var foot = _pose[leg.Foot];
		var ankle = foot.Position - drop;
		var target = ankle + direction * (ankle - origin).Dot( direction ) * (scale - 1f);
		// Clamp in the floor plane first: an unreachable target must not lift a planted boot off the floor.
		var reach = upper.Position.Distance( lower.Position ) + lower.Position.Distance( foot.Position ) - .01f;
		var height = upper.Position.z - target.z;
		var planarReach = MathF.Sqrt( MathF.Max( 0f, reach * reach - height * height ) );
		var planar = (target - upper.Position).WithZ( 0f );
		if ( planar.Length > planarReach ) target = (upper.Position + planar.Normal * planarReach).WithZ( target.z );
		ThirdPersonSlidePose.SolveLeg( upper, lower, foot, target, lower.Position - upper.Position, foot.Rotation,
			out var solvedUpper, out var solvedLower, out var solvedFoot );
		foreach ( var index in leg.Bones )
		{
			var segment = leg.Segments[index];
			var original = segment == 0 ? upper : segment == 1 ? lower : foot;
			var solved = segment == 0 ? solvedUpper : segment == 1 ? solvedLower : solvedFoot;
			_pose[index] = solved.ToWorld( original.ToLocal( _pose[index] ) );
		}
	}

	private void Build( SkinnedModelRenderer body )
	{
		_body = body;
		_model = body.Model;
		_bones = _model.Bones.AllBones.OrderBy( b => Depth( b.Index ) ).ToArray();
		_pose = new Transform[_model.BoneCount];
		_left = BuildLeg( "ankle_L", "l_foot" );
		_right = BuildLeg( "ankle_R", "r_foot" );
		_garments.Clear();
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
			if ( garment != body && garment.BoneMergeTarget == body ) _garments.Add( garment );
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
