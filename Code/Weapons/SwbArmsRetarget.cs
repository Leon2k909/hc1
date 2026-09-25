namespace Facepunch;

/// <summary>
/// Poses the standard HC1 first-person arms from a SWB weapon's own animated arm skeleton, so SWB guns
/// show the same arms as every other weapon. The SWB model keeps its arm bones (for the animation data)
/// but not its arm meshes.
/// </summary>
/// <remarks>
/// Each HC1 bone copies its SWB counterpart's rotation through a constant offset worked out from the two
/// bind poses. Both bones are expressed in an anatomical frame (pointing down the bone, rolled by the palm),
/// so the rigs' different bone axes and rest poses cancel out. The HC1 arm keeps its own proportions: a
/// two-bone IK puts the hand where the SWB hand is and bends the elbow towards the SWB elbow. The pose is written
/// once the camera has placed the viewmodel, after the frame's animation update, as bone overrides as well as
/// straight into the render bones.
/// </remarks>
public sealed class SwbArmsRetarget : Component, ICameraSetup
{
	/// <summary>The SWB weapon renderer whose animated arm bones we follow.</summary>
	[Property] public SkinnedModelRenderer Source { get; set; }

	/// <summary>The HC1 arms renderer we pose. It shouldn't be bone merged or run its own animgraph.</summary>
	[Property] public SkinnedModelRenderer Arms { get; set; }

	/// <summary>0 puts the HC1 wrist on the SWB wrist, 1 lines the knuckles up instead.</summary>
	[Property, Range( 0, 1 )] public float KnuckleAnchor { get; set; } = 0.5f;

	/// <summary>Moves each hand towards its back, since our hands are thicker than the SWB ones and would sink into the grip.</summary>
	[Property, Range( 0, 2 )] public float PalmClearance { get; set; } = 0.25f;

	// HC1 bone, SWB bone, and the child each one points at ('#' is the side). No child: carry on from the parent.
	// SWB fingers have no metacarpals ("index_L" is the first phalanx), so the HC1 finger metas stay rigid in the palm.
	static readonly (string Bone, string From, string BoneAim, string FromAim)[] BoneMap =
	{
		("clavicle_#", "shoulder_L_#", "arm_upper_#", "upperarm_L_#"),
		("arm_upper_#", "upperarm_L_#", "arm_lower_#", "lowerarm_L_#"),
		("arm_lower_#", "lowerarm_L_#", "hand_#", "hand_L_#"),
		("arm_lower_#_twistctrl0", "twist_arm_1_L_#", "hand_#", "hand_L_#"),
		("arm_lower_#_twistctrl1", "twist_arm_2_L_#", "hand_#", "hand_L_#"),
		("arm_lower_#_twistctrl2", "twist_arm_3_L_#", "hand_#", "hand_L_#"),
		("hand_#", "hand_L_#", "finger_middle_0_#", "middle_L_#"),
		("finger_thumb_0_#", "thumb_L_#", "finger_thumb_1_#", "thumb_L_002_#"),
		("finger_thumb_1_#", "thumb_L_002_#", "finger_thumb_2_#", "thumb_L_001_#"),
		("finger_thumb_2_#", "thumb_L_001_#", null, null),
		("finger_index_0_#", "index_L_#", "finger_index_1_#", "index_L_003_#"),
		("finger_index_1_#", "index_L_003_#", "finger_index_2_#", "index_L_002_#"),
		("finger_index_2_#", "index_L_002_#", null, "index_L_001_#"),
		("finger_middle_0_#", "middle_L_#", "finger_middle_1_#", "middle_L_003_#"),
		("finger_middle_1_#", "middle_L_003_#", "finger_middle_2_#", "middle_L_002_#"),
		("finger_middle_2_#", "middle_L_002_#", null, "middle_L_001_#"),
		("finger_ring_0_#", "ring_L_#", "finger_ring_1_#", "ring_L_001_#"),
		("finger_ring_1_#", "ring_L_001_#", "finger_ring_2_#", "ring_L_002_#"),
		("finger_ring_2_#", "ring_L_002_#", null, "ring_L_003_#"),
		("finger_pinky_0_#", "pink_L_#", "finger_pinky_1_#", "pink_L_003_#"),
		("finger_pinky_1_#", "pink_L_003_#", "finger_pinky_2_#", "pink_L_002_#"),
		("finger_pinky_2_#", "pink_L_002_#", null, "pink_L_001_#"),
	};

	// Knuckles (index, middle, ring, pinky), for the palm normal and for lining the hands up.
	static readonly string[] ArmsKnuckleBones = { "finger_index_0_#", "finger_middle_0_#", "finger_ring_0_#", "finger_pinky_0_#" };
	static readonly string[] FromKnuckleBones = { "index_L_#", "middle_L_#", "ring_L_#", "pink_L_#" };

	sealed class Chain
	{
		public int Clavicle, Upper, Lower, Hand;
		public int FromShoulder, FromUpper, FromLower, FromHand;
		public Vector3 UpperAim, LowerAim, ArmsKnuckles, FromKnuckles, BackOfHand;
		public float UpperLength, LowerLength;
		public Rotation ForearmSwing;
	}

	sealed class Rig
	{
		public int[] Order, Parent, From, ForearmSide;
		public Transform[] BindLocal, Pose;
		public Rotation[] Offset;
		public bool[] Solved;
		public Chain[] Chains;
	}

	Rig _rig;
	Model _builtFrom, _builtArms;
	Transform[] _source;

	// Runs once the viewmodel is placed for the frame, after the scene's animation update, so both skeletons are final.
	void ICameraSetup.PostSetup( CameraComponent cc ) => Apply();

	void Apply()
	{
		if ( !Source.IsValid() || !Arms.IsValid() || !Arms.Enabled || Source.Model is null || Arms.Model is null ) return;
		var from = Source.SceneModel;
		var to = Arms.SceneModel;
		if ( !from.IsValid() || !to.IsValid() ) return;

		if ( Source.Model != _builtFrom || Arms.Model != _builtArms )
		{
			_builtFrom = Source.Model;
			_builtArms = Arms.Model;
			_rig = Build( _builtFrom, _builtArms );
			if ( _rig is null ) Log.Warning( $"SwbArmsRetarget: {_builtFrom.Name} has no SWB arm skeleton to drive {_builtArms.Name}" );
		}
		if ( _rig is null ) return;

		// Work in the arms' model space. (GetBoneLocalTransform is parent space, so go through world space.)
		var rig = _rig;
		var space = to.Transform;
		if ( _source?.Length != _builtFrom.BoneCount ) _source = new Transform[_builtFrom.BoneCount];
		for ( int i = 0; i < _source.Length; i++ ) _source[i] = space.ToLocal( from.GetBoneWorldTransform( i ) );
		for ( int i = 0; i < rig.Solved.Length; i++ ) rig.Solved[i] = false;

		foreach ( var chain in rig.Chains )
			SolveArm( rig, chain );

		// Everything else hangs off its parent; mapped bones take their SWB rotation.
		foreach ( var i in rig.Order )
		{
			if ( rig.Solved[i] ) continue;
			var parent = rig.Parent[i];
			var tx = parent >= 0 ? rig.Pose[parent].ToWorld( rig.BindLocal[i] ) : rig.BindLocal[i];
			if ( rig.From[i] >= 0 )
			{
				var rotation = _source[rig.From[i]].Rotation * rig.Offset[i];
				if ( rig.ForearmSide[i] >= 0 ) rotation = rig.Chains[rig.ForearmSide[i]].ForearmSwing * rotation;
				tx = new Transform( tx.Position, rotation );
			}
			rig.Pose[i] = tx;
		}

		// The engine re-poses the arms from their bind pose whenever the viewmodel moves, so the pose also goes in as
		// bone overrides (model space), which that re-pose keeps. Without them the arms vanish whenever the player moves.
		for ( int i = 0; i < rig.Pose.Length; i++ )
		{
			to.SetBoneOverride( i, rig.Pose[i] );
			to.SetBoneWorldTransform( i, space.ToWorld( rig.Pose[i] ) );
		}
	}

	void SolveArm( Rig rig, Chain chain )
	{
		var shoulder = _source[chain.FromShoulder];
		var upper = _source[chain.FromUpper];
		var lower = _source[chain.FromLower];
		var hand = _source[chain.FromHand];

		var clavicleRotation = shoulder.Rotation * rig.Offset[chain.Clavicle];
		var claviclePosition = shoulder.Position;
		var shoulderPosition = claviclePosition + clavicleRotation * rig.BindLocal[chain.Upper].Position;

		// The hand takes the SWB orientation, placed between the SWB wrist and where our knuckles meet the SWB knuckles.
		var handRotation = hand.Rotation * rig.Offset[chain.Hand];
		var knucklesLinedUp = hand.PointToWorld( chain.FromKnuckles ) - handRotation * chain.ArmsKnuckles;
		var target = Vector3.Lerp( hand.Position, knucklesLinedUp, KnuckleAnchor ) + handRotation * chain.BackOfHand * PalmClearance;

		// Two-bone IK with our own arm lengths. Out of reach, slide the shoulder (off screen) rather than stretch the arm.
		float a = chain.UpperLength, b = chain.LowerLength;
		var reach = (a + b) * 0.999f;
		var toTarget = target - shoulderPosition;
		if ( toTarget.Length > reach )
		{
			var slide = toTarget.Normal * (toTarget.Length - reach);
			claviclePosition += slide;
			shoulderPosition += slide;
			toTarget = target - shoulderPosition;
		}

		var distance = MathF.Max( toTarget.Length, MathF.Abs( a - b ) + 0.01f );
		var direction = toTarget.Normal;
		var pole = lower.Position - shoulderPosition;
		var bend = pole - direction * Vector3.Dot( pole, direction );
		if ( bend.LengthSquared < 0.0001f ) bend = Vector3.Cross( direction, Vector3.Up );
		bend = bend.Normal;
		var cos = Math.Clamp( (a * a + distance * distance - b * b) / (2f * a * distance), -1f, 1f );
		var elbow = shoulderPosition + direction * (a * cos) + bend * (a * MathF.Sqrt( 1f - cos * cos ));

		// Keep the SWB roll, swing the bones onto the solved joints.
		var upperRotation = upper.Rotation * rig.Offset[chain.Upper];
		upperRotation = Rotation.FromToRotation( upperRotation * chain.UpperAim, (elbow - shoulderPosition).Normal ) * upperRotation;
		var lowerRotation = lower.Rotation * rig.Offset[chain.Lower];
		chain.ForearmSwing = Rotation.FromToRotation( lowerRotation * chain.LowerAim, (target - elbow).Normal );

		rig.Pose[chain.Clavicle] = new Transform( claviclePosition, clavicleRotation );
		rig.Pose[chain.Upper] = new Transform( shoulderPosition, upperRotation );
		rig.Pose[chain.Lower] = new Transform( elbow, chain.ForearmSwing * lowerRotation );
		rig.Pose[chain.Hand] = new Transform( target, handRotation );
		rig.Solved[chain.Clavicle] = rig.Solved[chain.Upper] = rig.Solved[chain.Lower] = rig.Solved[chain.Hand] = true;
	}

	static Rig Build( Model from, Model arms )
	{
		var count = arms.BoneCount;
		var rig = new Rig
		{
			Parent = new int[count],
			From = new int[count],
			ForearmSide = new int[count],
			BindLocal = new Transform[count],
			Pose = new Transform[count],
			Offset = new Rotation[count],
			Solved = new bool[count],
			Chains = new Chain[2],
		};

		for ( int i = 0; i < count; i++ )
		{
			var parent = arms.GetBoneParent( i );
			var bind = arms.GetBoneTransform( i );
			rig.Parent[i] = parent;
			rig.BindLocal[i] = parent >= 0 ? arms.GetBoneTransform( parent ).ToLocal( bind ) : bind;
			rig.From[i] = -1;
			rig.ForearmSide[i] = -1;
		}

		// Parents before children.
		rig.Order = Enumerable.Range( 0, count ).OrderBy( i => Depth( arms, i ) ).ToArray();

		for ( int side = 0; side < 2; side++ )
		{
			var suffix = side == 0 ? "R" : "L";
			int A( string name ) => BoneIndex( arms, name?.Replace( "#", suffix ) );
			int S( string name ) => BoneIndex( from, name?.Replace( "#", suffix ) );

			var chain = new Chain
			{
				Clavicle = A( "clavicle_#" ),
				Upper = A( "arm_upper_#" ),
				Lower = A( "arm_lower_#" ),
				Hand = A( "hand_#" ),
				FromShoulder = S( "shoulder_L_#" ),
				FromUpper = S( "upperarm_L_#" ),
				FromLower = S( "lowerarm_L_#" ),
				FromHand = S( "hand_L_#" ),
			};
			var armsKnuckles = ArmsKnuckleBones.Select( A ).ToArray();
			var fromKnuckles = FromKnuckleBones.Select( S ).ToArray();
			var required = new[] { chain.Clavicle, chain.Upper, chain.Lower, chain.Hand, chain.FromShoulder, chain.FromUpper, chain.FromLower, chain.FromHand };
			if ( required.Concat( armsKnuckles ).Concat( fromKnuckles ).Any( i => i < 0 ) ) return null;

			var armsPalm = PalmNormal( arms, chain.Hand, armsKnuckles );
			var fromPalm = PalmNormal( from, chain.FromHand, fromKnuckles );

			foreach ( var link in BoneMap )
			{
				int bone = A( link.Bone ), source = S( link.From );
				if ( bone < 0 || source < 0 ) continue;

				// Collar bones run sideways, along the palm normal, so roll those by world up instead.
				var collar = bone == chain.Clavicle;
				var armsFrame = AnatomicalFrame( arms, bone, A( link.BoneAim ), collar ? Vector3.Up : armsPalm );
				var fromFrame = AnatomicalFrame( from, source, S( link.FromAim ), collar ? Vector3.Up : fromPalm );

				rig.From[bone] = source;
				rig.Offset[bone] = from.GetBoneTransform( source ).Rotation.Inverse * fromFrame * armsFrame.Inverse * arms.GetBoneTransform( bone ).Rotation;
				if ( link.Bone.StartsWith( "arm_lower_#_twist" ) ) rig.ForearmSide[bone] = side;
			}

			var upperBind = arms.GetBoneTransform( chain.Upper );
			var lowerBind = arms.GetBoneTransform( chain.Lower );
			var handBind = arms.GetBoneTransform( chain.Hand );
			chain.UpperAim = upperBind.Rotation.Inverse * (lowerBind.Position - upperBind.Position).Normal;
			chain.LowerAim = lowerBind.Rotation.Inverse * (handBind.Position - lowerBind.Position).Normal;
			chain.UpperLength = upperBind.Position.Distance( lowerBind.Position );
			chain.LowerLength = lowerBind.Position.Distance( handBind.Position );
			chain.ArmsKnuckles = handBind.PointToLocal( Centre( arms, armsKnuckles ) );
			chain.FromKnuckles = from.GetBoneTransform( chain.FromHand ).PointToLocal( Centre( from, fromKnuckles ) );
			chain.BackOfHand = handBind.Rotation.Inverse * (side == 0 ? -armsPalm : armsPalm);
			rig.Chains[side] = chain;
		}

		return rig;
	}

	static int BoneIndex( Model model, string name ) => name is not null && model.Bones.HasBone( name ) ? model.Bones.GetBone( name ).Index : -1;

	static int Depth( Model model, int bone )
	{
		var depth = 0;
		for ( var parent = model.GetBoneParent( bone ); parent >= 0; parent = model.GetBoneParent( parent ) ) depth++;
		return depth;
	}

	static Vector3 Centre( Model model, int[] bones )
	{
		var sum = Vector3.Zero;
		foreach ( var bone in bones ) sum += model.GetBoneTransform( bone ).Position;
		return sum / bones.Length;
	}

	/// <summary>Palm normal: out of the back of a left hand, out of the palm of a right one (mirroring flips the cross product). Knuckles are index, middle, ring, pinky.</summary>
	static Vector3 PalmNormal( Model model, int hand, int[] knuckles )
	{
		var forward = model.GetBoneTransform( knuckles[1] ).Position - model.GetBoneTransform( hand ).Position;
		var across = model.GetBoneTransform( knuckles[3] ).Position - model.GetBoneTransform( knuckles[0] ).Position;
		return Vector3.Cross( forward, across ).Normal;
	}

	/// <summary>Bind-pose frame pointing down the bone (tips carry on from their parent), rolled so up follows <paramref name="up"/>.</summary>
	static Rotation AnatomicalFrame( Model model, int bone, int aim, Vector3 up )
	{
		var position = model.GetBoneTransform( bone ).Position;
		var forward = aim >= 0
			? model.GetBoneTransform( aim ).Position - position
			: position - model.GetBoneTransform( model.GetBoneParent( bone ) ).Position;
		forward = forward.Normal;
		return Rotation.LookAt( forward, (up - forward * Vector3.Dot( forward, up )).Normal );
	}
}
