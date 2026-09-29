namespace Facepunch;

/// <summary>Two-handed field device pose. Arms keep their actual bone lengths and fingers;
/// the camera places the model first, then IK fits both wrists to its handles.</summary>
public sealed class DefuseViewModel : Component, ICameraSetup
{
	[Property] public SkinnedModelRenderer Device { get; set; }
	[Property] public SkinnedModelRenderer Arms { get; set; }
	private Model rig;
	private Transform[] bind, local, pose;
	private int[] order;
	private TimeSince deployed;
	private float plantBlend;
	protected override void OnStart() => deployed = 0;

	void ICameraSetup.PostSetup( CameraComponent camera )
	{
		if ( !Device.IsValid() || !Arms.IsValid() || Arms.Model is null || !Arms.SceneModel.IsValid() ) return;
		var vm = GetComponent<ViewModel>();
		var planting = vm?.Equipment?.GetComponentInChildren<DefuseC4>();
		plantBlend = plantBlend.LerpTo( planting is { IsPlanting: true } ? 1f : 0f, Time.Delta * 8f );
		float progress = planting?.Progress ?? 0;
		float draw = 1f - Math.Clamp( deployed / .35f, 0f, 1f );
		float setDown = Math.Clamp( (progress - .8f) / .2f, 0, 1 );
		Device.LocalPosition = new Vector3( 22f - plantBlend * 1.5f, 0, -6.8f - draw * 9f + plantBlend * 1f - setDown * 7f );
		Device.LocalRotation = Rotation.From( new Angles( -25f + plantBlend * 8f + setDown * 25f, 0, 0 ) );
		Arms.BoneMergeTarget = null;
		Arms.UseAnimGraph = false;
		if ( rig != Arms.Model ) BuildRig();
		if ( rig is null ) return;
		Array.Copy( bind, pose, bind.Length );
		PoseArm( "L", 1, progress );
		PoseArm( "R", -1, progress );
		var scene = Arms.SceneModel;
		for ( int i = 0; i < pose.Length; i++ )
		{
			scene.SetBoneOverride( i, pose[i] );
			scene.SetBoneWorldTransform( i, Arms.WorldTransform.ToWorld( pose[i] ) );
		}
	}

	void BuildRig()
	{
		rig = Arms.Model;
		bind = Enumerable.Range( 0, rig.BoneCount ).Select( rig.GetBoneTransform ).ToArray();
		pose = new Transform[bind.Length];
		local = new Transform[bind.Length];
		for ( int i = 0; i < bind.Length; i++ ) local[i] = rig.GetBoneParent(i) < 0 ? bind[i] : bind[rig.GetBoneParent(i)].ToLocal(bind[i]);
		order = Enumerable.Range( 0, bind.Length ).OrderBy( Depth ).ToArray();
	}

	int Depth( int i ) { int n = 0; while ( (i = rig.GetBoneParent(i)) >= 0 ) n++; return n; }
	int Bone( string name ) => rig.Bones.GetBone( name ).Index;
	bool Under( int i, int ancestor ) { while ( i >= 0 ) { if ( i == ancestor ) return true; i = rig.GetBoneParent(i); } return false; }

	void PoseArm( string side, int sign, float progress )
	{
		int upper = Bone("arm_upper_"+side), lower = Bone("arm_lower_"+side), hand = Bone("hand_"+side);
		int middle = Bone("finger_middle_0_"+side), index = Bone("finger_index_0_"+side), pinky = Bone("finger_pinky_0_"+side);
		var frame = Arms.WorldTransform.ToLocal( Device.WorldTransform );
		var wristLocal = new Vector3( -3.2f, sign * 6.3f, 1.4f );
		// The right hand moves to the keypad and taps during arming, then returns to support the device.
		float tapBlend = sign < 0 ? plantBlend * (1f - Math.Clamp( (progress-.72f)/.12f, 0, 1 )) : 0;
		var tap = new Vector3( -2.9f, -3.9f, 5.6f + MathF.Abs( MathF.Sin( progress * MathF.PI * 12 ) ) * .35f );
		wristLocal = Vector3.Lerp( wristLocal, tap, tapBlend );
		var wrist = frame.PointToWorld( wristLocal );
		var forward = (bind[middle].Position - bind[hand].Position).Normal;
		var across = bind[pinky].Position - bind[index].Position;
		var palm = Vector3.Cross( forward, across ).Normal;
		var bindFrame = Rotation.LookAt( forward, palm );
		var targetFrame = frame.Rotation * Rotation.LookAt( Vector3.Forward, Vector3.Left );
		var handRotation = targetFrame * bindFrame.Inverse * bind[hand].Rotation;
		var shoulder = new Vector3( -3, sign * 7, -10 );
		float a = bind[upper].Position.Distance( bind[lower].Position ), b = bind[lower].Position.Distance( bind[hand].Position );
		var to = wrist - shoulder;
		if ( to.Length > (a+b)*.99f ) { shoulder += to.Normal * (to.Length-(a+b)*.99f); to = wrist-shoulder; }
		float distance = Math.Max( to.Length, MathF.Abs(a-b)+.01f );
		var direction = to.Normal;
		var pole = new Vector3( 2, sign*14, -17 ) - shoulder;
		var bend = (pole - direction * Vector3.Dot( pole, direction )).Normal;
		float cos = Math.Clamp( (a*a+distance*distance-b*b)/(2*a*distance), -1f, 1f );
		var elbow = shoulder + direction*a*cos + bend*a*MathF.Sqrt(1-cos*cos);
		var upperRot = Rotation.FromToRotation( (bind[lower].Position-bind[upper].Position).Normal, (elbow-shoulder).Normal ) * bind[upper].Rotation;
		var lowerRot = Rotation.FromToRotation( (bind[hand].Position-bind[lower].Position).Normal, (wrist-elbow).Normal ) * bind[lower].Rotation;
		pose[upper] = new Transform( shoulder, upperRot );
		pose[lower] = new Transform( elbow, lowerRot );
		pose[hand] = new Transform( wrist, handRotation );
		foreach ( var i in order )
		{
			if ( i == upper || i == lower || i == hand || !Under(i,upper) ) continue;
			pose[i] = pose[rig.GetBoneParent(i)].ToWorld( local[i] );
		}
	}
}
