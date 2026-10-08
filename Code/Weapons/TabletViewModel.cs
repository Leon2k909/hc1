namespace Facepunch;

/// <summary>
/// The recon octocopter's ground station, held in both hands by its side grips with the screen towards the eye, low in
/// the view as one is carried ready. The arms keep their real bone lengths and are solved onto the grips each frame, as
/// <see cref="DefuseViewModel"/> does. While the operator is looking through the drone it isn't drawn: the feed is the
/// whole screen.
/// <para>
/// The tablet's own frame: the screen faces -X, Y is the holder's left, Z up; its grips are vertical handles at
/// (1.02, ±6.85, -0.43), 6.2 inches long, behind the case's sides (<c>asset-info.json</c>).
/// </para>
/// </summary>
public sealed class TabletViewModel : Component, ICameraSetup
{
	[Property] public SkinnedModelRenderer Device { get; set; }
	[Property] public SkinnedModelRenderer Arms { get; set; }

	/// <summary>Where the station sits in front of the eye, and its tilt back towards it (pitch, positive tips the top away).</summary>
	[Property] public Vector3 HoldPosition { get; set; } = new( 15f, 0f, -7.5f );
	[Property] public float HoldPitch { get; set; } = 32f;

	/// <summary>The left wrist in the tablet's frame (the right is its mirror): outside the grip, a little low.</summary>
	[Property] public Vector3 WristOffset { get; set; } = new( -0.2f, 8.6f, -1.6f );

	private Model rig;
	private Transform[] bind, local, pose;
	private int[] order;
	private TimeSince deployed;
	private float lowered;

	protected override void OnStart() => deployed = 0;

	void ICameraSetup.PostSetup( CameraComponent camera )
	{
		if ( !Device.IsValid() || !Arms.IsValid() ) return;

		var owner = GetComponent<ViewModel>()?.Equipment?.Owner;
		var piloting = ReconOctocopter.IsPiloting( owner );
		Device.Enabled = !piloting;
		Arms.Enabled = !piloting;
		if ( piloting )
		{
			// Back from the drone, the station comes up again from where it was held.
			deployed = 0.25f;
			return;
		}
		if ( Arms.Model is null || !Arms.SceneModel.IsValid() ) return;

		// Drawn up from the waist; held lower and flatter while running.
		var draw = 1f - Math.Clamp( deployed / 0.35f, 0f, 1f );
		draw *= draw;
		lowered = lowered.LerpTo( owner is { IsSprinting: true } ? 1f : 0f, Time.Delta * 8f );
		Device.LocalPosition = HoldPosition + new Vector3( -lowered * 1.5f, 0f, -draw * 9f - lowered * 2.5f );
		Device.LocalRotation = Rotation.From( new Angles( HoldPitch + draw * 25f + lowered * 15f, 0f, 0f ) );

		Arms.BoneMergeTarget = null;
		Arms.UseAnimGraph = false;
		if ( rig != Arms.Model ) BuildRig();
		if ( rig is null ) return;

		Array.Copy( bind, pose, bind.Length );
		PoseArm( "L", 1 );
		PoseArm( "R", -1 );
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
		for ( int i = 0; i < bind.Length; i++ )
			local[i] = rig.GetBoneParent( i ) < 0 ? bind[i] : bind[rig.GetBoneParent( i )].ToLocal( bind[i] );
		order = Enumerable.Range( 0, bind.Length ).OrderBy( Depth ).ToArray();
	}

	int Depth( int i ) { int n = 0; while ( (i = rig.GetBoneParent( i )) >= 0 ) n++; return n; }
	int Bone( string name ) => rig.Bones.GetBone( name ).Index;
	bool Under( int i, int ancestor ) { while ( i >= 0 ) { if ( i == ancestor ) return true; i = rig.GetBoneParent( i ); } return false; }

	/// <summary>
	/// One arm onto its grip: the palm against the handle's outer side, the hand pointing back round it (away from the
	/// holder, in and up) so the fingers close behind it and the thumb comes over the front to the stick.
	/// </summary>
	void PoseArm( string side, int sign )
	{
		int upper = Bone( "arm_upper_" + side ), lower = Bone( "arm_lower_" + side ), hand = Bone( "hand_" + side );
		int middle = Bone( "finger_middle_0_" + side ), index = Bone( "finger_index_0_" + side ), pinky = Bone( "finger_pinky_0_" + side );
		var frame = Arms.WorldTransform.ToLocal( Device.WorldTransform );
		var wrist = frame.PointToWorld( WristOffset.WithY( sign * WristOffset.y ) );

		var forward = (bind[middle].Position - bind[hand].Position).Normal;
		var across = bind[pinky].Position - bind[index].Position;
		// For the right hand this is the palm, for the left the back of the hand (its fingers run the other way), so one
		// target frame turns both palms inwards, onto their grips.
		var palm = Vector3.Cross( forward, across ).Normal;
		var bindFrame = Rotation.LookAt( forward, palm );
		var pointing = new Vector3( 0.75f, -sign * 0.35f, 0.55f ).Normal;
		var targetFrame = frame.Rotation * Rotation.LookAt( pointing, Vector3.Left );
		var handRotation = targetFrame * bindFrame.Inverse * bind[hand].Rotation;

		var shoulder = new Vector3( -3f, sign * 7f, -10f );
		float a = bind[upper].Position.Distance( bind[lower].Position ), b = bind[lower].Position.Distance( bind[hand].Position );
		var to = wrist - shoulder;
		if ( to.Length > (a + b) * .99f ) { shoulder += to.Normal * (to.Length - (a + b) * .99f); to = wrist - shoulder; }
		float distance = Math.Max( to.Length, MathF.Abs( a - b ) + .01f );
		var direction = to.Normal;
		// The elbows hang down and a little out, as they do holding something at the chest.
		var pole = new Vector3( 4f, sign * 12f, -20f ) - shoulder;
		var bend = (pole - direction * Vector3.Dot( pole, direction )).Normal;
		float cos = Math.Clamp( (a * a + distance * distance - b * b) / (2 * a * distance), -1f, 1f );
		var elbow = shoulder + direction * a * cos + bend * a * MathF.Sqrt( 1 - cos * cos );
		var upperRot = Rotation.FromToRotation( (bind[lower].Position - bind[upper].Position).Normal, (elbow - shoulder).Normal ) * bind[upper].Rotation;
		var lowerRot = Rotation.FromToRotation( (bind[hand].Position - bind[lower].Position).Normal, (wrist - elbow).Normal ) * bind[lower].Rotation;
		pose[upper] = new Transform( shoulder, upperRot );
		pose[lower] = new Transform( elbow, lowerRot );
		pose[hand] = new Transform( wrist, handRotation );
		foreach ( var i in order )
		{
			if ( i == upper || i == lower || i == hand || !Under( i, upper ) ) continue;
			pose[i] = pose[rig.GetBoneParent( i )].ToWorld( local[i] );
		}
	}
}
