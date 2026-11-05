namespace Facepunch;

/// <summary>A brief impact layered over the driver's current pose, including its bone-merged zombie body.</summary>
public sealed class ZombieHitReactionPose
{
	private const float Spring = 16f;
	private Vector3 _torso, _torsoVelocity, _head, _headVelocity;
	private Model _model;
	private SkinnedModelRenderer _driver;
	private BoneCollection.Bone[] _bones = Array.Empty<BoneCollection.Bone>();
	private Transform[] _pose = Array.Empty<Transform>();
	private int[] _spines = Array.Empty<int>();
	private bool[][] _groups = Array.Empty<bool[]>();
	private int _neck = -1;
	private bool[] _inHead = Array.Empty<bool>();
	private readonly List<SkinnedModelRenderer> _bodies = new();

	public void Trigger( Vector3 localPush, float strength, bool headshot, float side )
	{
		var push = localPush.WithZ( 0f );
		push = push.IsNearZeroLength ? Vector3.Backward : push.Normal;
		strength = strength.Clamp( .55f, 1.2f );
		side = side.Clamp( -1f, 1f );
		// Critical damping peaks after about 60ms, then settles without a looping stagger or a navigation stop.
		var impulse = Spring * MathF.E;
		var torso = new Vector3( push.x * 11f, -push.x * side * 5f, -push.y * 11f );
		var head = new Vector3( push.x * (headshot ? 18f : 5f), -push.x * side * 6f, -push.y * (headshot ? 16f : 5f) );
		_torsoVelocity = Limit( _torsoVelocity + torso * (headshot ? .65f : 1f) * strength * impulse, 650f );
		_headVelocity = Limit( _headVelocity + head * strength * impulse, 950f );
	}

	/// <summary>Runs after animation, from BotSystem, so a sequence update cannot erase the impact.</summary>
	public bool Apply( SkinnedModelRenderer driver, float delta )
	{
		if ( _torso.LengthSquared + _head.LengthSquared + _torsoVelocity.LengthSquared + _headVelocity.LengthSquared < .001f ) return false;
		Step( ref _torso, ref _torsoVelocity, delta );
		Step( ref _head, ref _headVelocity, delta );
		_torso = Limit( _torso, 17f );
		_head = Limit( _head, 24f );
		if ( !driver.IsValid() || !driver.SceneModel.IsValid() || driver.Model is null ) return false;
		if ( _driver != driver || _model != driver.Model ) Build( driver );
		if ( _spines.Length == 0 ) return false;

		// Read the animation, never last frame's edited pose: animation LOD can reuse a pose for several frames.
		foreach ( var bone in _bones )
			_pose[bone.Index] = driver.TryGetBoneTransformAnimation( bone, out var animated )
				? animated : driver.WorldTransform.ToWorld( bone.LocalTransform );
		var space = driver.WorldRotation;
		for ( var i = 0; i < _spines.Length; i++ )
			Rotate( _spines[i], _groups[i], space * Rotation.From( _torso.x / _spines.Length, _torso.y / _spines.Length, _torso.z / _spines.Length ) * space.Inverse );
		if ( _neck >= 0 ) Rotate( _neck, _inHead, space * Rotation.From( _head.x, _head.y, _head.z ) * space.Inverse );
		// Parents can propagate transforms, so finish solving before writing the upper-body pose.
		foreach ( var bone in _bones ) driver.SceneModel.SetBoneWorldTransform( bone.Index, _pose[bone.Index] );
		foreach ( var body in _bodies )
			if ( body.IsValid() && body.Enabled && body.BoneMergeTarget == driver && body.SceneModel.IsValid() )
				body.SceneModel.MergeBones( driver.SceneModel );
		return true;
	}

	private static void Step( ref Vector3 position, ref Vector3 velocity, float delta )
	{
		delta = MathF.Max( 0f, delta );
		var decay = MathF.Exp( -Spring * delta );
		var term = velocity + position * Spring;
		position = (position + term * delta) * decay;
		velocity = (velocity - term * (Spring * delta)) * decay;
	}

	private static Vector3 Limit( Vector3 value, float limit ) =>
		new( value.x.Clamp( -limit, limit ), value.y.Clamp( -limit, limit ), value.z.Clamp( -limit, limit ) );

	private void Rotate( int pivot, bool[] group, Rotation rotation )
	{
		var at = _pose[pivot].Position;
		foreach ( var bone in _bones )
		{
			if ( !group[bone.Index] ) continue;
			var pose = _pose[bone.Index];
			_pose[bone.Index] = pose.WithPosition( at + rotation * (pose.Position - at) ).WithRotation( rotation * pose.Rotation );
		}
	}

	private void Build( SkinnedModelRenderer driver )
	{
		_driver = driver;
		_model = driver.Model;
		_spines = new[] { "spine_0", "spine_1", "spine_2" }.Select( n => _model.Bones.GetBone( n )?.Index ?? -1 ).Where( i => i >= 0 ).ToArray();
		var root = _spines.FirstOrDefault( -1 );
		_bones = _model.Bones.AllBones.Where( b => Under( b.Index, root ) ).OrderBy( b => Depth( b.Index ) ).ToArray();
		_pose = new Transform[_model.BoneCount];
		_groups = _spines.Select( spine => Enumerable.Range( 0, _model.BoneCount ).Select( i => Under( i, spine ) ).ToArray() ).ToArray();
		_neck = (_model.Bones.GetBone( "neck_0" ) ?? _model.Bones.GetBone( "neck" ) ?? _model.Bones.GetBone( "head" ))?.Index ?? -1;
		_inHead = Enumerable.Range( 0, _model.BoneCount ).Select( i => Under( i, _neck ) ).ToArray();
		_bodies.Clear();
		foreach ( var body in driver.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
			if ( body != driver && body.BoneMergeTarget == driver ) _bodies.Add( body );
	}

	private bool Under( int index, int ancestor )
	{
		if ( ancestor < 0 ) return false;
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
