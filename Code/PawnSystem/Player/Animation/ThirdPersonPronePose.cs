namespace Facepunch;

/// <summary>
/// Lying prone, face down or on the back (supine), layered over the animated pose for the human and legacy player
/// skeletons. The pelvis and legs lie along the body's heading, the chest is propped up just far enough to bring the
/// eyes to the camera, and the head and arms keep their animated aim, carried to the lying neck and shoulders, so the
/// gun still points where the player looks (<see cref="ShoulderGun"/> brings it up to the eye). Rolling between the two
/// turns the body about its own length.
/// </summary>
public sealed class ThirdPersonPronePose
{
	/// <summary>How high the pelvis bone lies over the floor: about half the hips' depth, face down or on the back.</summary>
	public const float PelvisHeight = 5.5f;

	/// <summary>The legs' tilt from upright: a little short of flat, so the feet rest lower than the hips.</summary>
	private const float LegTilt = 87f;

	/// <summary>A face-down body's feet point their toes back, as a person's do lying flat, rather than into the floor.</summary>
	private const float PlantarFlex = 60f;

	/// <summary>The furthest the chest props itself up from the floor.</summary>
	private const float MaxRaise = 70f;

	/// <summary>How far each ankle lies out from under its hip: legs apart face down, closer on the back.</summary>
	private const float LegSpreadFaceDown = 4f, LegSpreadSupine = 2f;

	/// <summary>The ankle bones' height over the floor: on the shins and turned-back feet, or on the heels.</summary>
	private const float AnkleHeightFaceDown = 4f, AnkleHeightSupine = 3.5f;

	private Model _model;
	private SkinnedModelRenderer _body;
	private bool _updateBoneObjects;
	private int _pelvis = -1, _spine = -1, _neck = -1, _clavicleL = -1, _clavicleR = -1;
	private int[] _feet = Array.Empty<int>();
	private int[][] _footBones = Array.Empty<int[]>();
	private Leg[] _legs = Array.Empty<Leg>();
	private BoneCollection.Bone[] _bones = Array.Empty<BoneCollection.Bone>();
	private Group[] _group = Array.Empty<Group>();
	private Transform[] _anim = Array.Empty<Transform>();
	private Transform[] _pose = Array.Empty<Transform>();
	private GameObject[] _boneObjects = Array.Empty<GameObject>();
	private Vector3 _eyeAboveNeck;
	private readonly BotSupportHand _rightHand = new( true );
	private readonly BotSupportHand _leftHand = new();

	private enum Group { None, Lower, Upper, Head, Arms }

	private sealed class Leg
	{
		public int Upper, Lower, Foot;
		public bool Left;
		public int[] Bones, Segments;
	}

	/// <summary>
	/// Pose <paramref name="body"/> <paramref name="blend"/> of the way down. <paramref name="supine"/> is how far it has
	/// rolled onto its back, <paramref name="proneYaw"/> the heading from its feet to its head, and
		/// <paramref name="eye"/> where its eyes are once it lies there, on a floor at <paramref name="ground"/>.
		/// <paramref name="crawl"/> blends in alternating leg strokes at <paramref name="crawlPhase"/>.
	/// </summary>
		public void Apply( SkinnedModelRenderer body, float blend, float supine, float proneYaw, Vector3 eye, float ground,
			float crawl, float crawlPhase,
		bool updateBoneObjects = true )
	{
		if ( blend <= 0f || !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null ) return;
		if ( _body != body || _model != body.Model || _updateBoneObjects != updateBoneObjects ) Build( body, updateBoneObjects );
		if ( _pelvis < 0 ) return;
		blend = blend.Clamp( 0f, 1f );
		supine = supine.Clamp( 0f, 1f );
		var roll = supine * supine * (3f - 2f * supine);
		crawl = crawl.Clamp( 0f, 1f ) * blend * (1f - roll);

		// Always read the unmodified animation: a reused LOD pose must never lie down again each frame.
		foreach ( var bone in _bones )
			_anim[bone.Index] = body.TryGetBoneTransformAnimation( bone, out var pose )
				? pose : body.WorldTransform.ToWorld( bone.LocalTransform );

		var rootRotation = body.WorldRotation;
		var flex = Rotation.FromPitch( PlantarFlex * blend * (1f - roll) );
		for ( var i = 0; i < _feet.Length; i++ ) TurnAbout( _footBones[i], _anim[_feet[i]].Position, rootRotation * flex * rootRotation.Inverse );

		var pelvis = _anim[_pelvis].Position;
		var spine = _anim[_spine].Position;
		var neck = _anim[_neck].Position;
		var shoulders = (_anim[_clavicleL].Position + _anim[_clavicleR].Position) * 0.5f;
		var toSpine = rootRotation.Inverse * (spine - pelvis);
		var toNeck = rootRotation.Inverse * (neck - spine);

		// Lying flat along the heading, then spun about the body's own length onto its back.
		var heading = Rotation.FromYaw( proneYaw );
		var spin = Rotation.FromYaw( 180f * roll );
		var lowerLying = heading * Rotation.FromPitch( LegTilt ) * spin;
		Rotation UpperLying( float raise ) => heading * Rotation.FromPitch( LegTilt - raise ) * spin;

		// Prop the chest up until, with the eyes at the camera, the hips rest on the floor.
		var neckLying = eye - rootRotation * _eyeAboveNeck;
		var neckOverHips = neckLying.z - ground - PelvisHeight;
		float low = 0f, high = MaxRaise;
		for ( var i = 0; i < 12; i++ )
		{
			var mid = (low + high) * 0.5f;
			if ( (lowerLying * toSpine + UpperLying( mid ) * toNeck).z < neckOverHips ) low = mid; else high = mid;
		}
		var raise = (low + high) * 0.5f;
		var upperLying = UpperLying( raise );
		var pelvisLying = neckLying - lowerLying * toSpine - upperLying * toNeck;

		var lowerRotation = Rotation.Slerp( rootRotation, lowerLying, blend );
		var upperRotation = Rotation.Slerp( rootRotation, upperLying, blend );
		var hips = Vector3.Lerp( pelvis, pelvisLying, blend );
		// Going down and getting up, keep the feet out of the floor as the legs swing up. Lying, the legs are laid
		// out on the floor below instead.
		var lowest = float.MaxValue;
		foreach ( var foot in _feet ) lowest = MathF.Min( lowest, (hips + lowerRotation * (rootRotation.Inverse * (_anim[foot].Position - pelvis))).z );
		var clearance = _anim[_feet[0]].Position.z - ground;
		if ( lowest < ground + clearance ) hips.z += (ground + clearance - lowest) * MathF.Min( 1f, (1f - blend) * 3f );

		var fromLower = new Transform( pelvis, rootRotation );
		var toLower = new Transform( hips, lowerRotation );
		var fromUpper = new Transform( spine, rootRotation );
		var toUpper = new Transform( toLower.PointToWorld( fromLower.PointToLocal( spine ) ), upperRotation );
		var headShift = toUpper.PointToWorld( fromUpper.PointToLocal( neck ) ) - neck;
		var armShift = toUpper.PointToWorld( fromUpper.PointToLocal( shoulders ) ) - shoulders;

		foreach ( var bone in _bones )
		{
			var i = bone.Index;
			var anim = _anim[i];
			_pose[i] = _group[i] switch
			{
				Group.Lower => toLower.ToWorld( fromLower.ToLocal( anim ) ),
				Group.Upper => toUpper.ToWorld( fromUpper.ToLocal( anim ) ),
				Group.Head => anim.WithPosition( anim.Position + headShift ),
				Group.Arms => anim.WithPosition( anim.Position + armShift ),
				_ => anim
			};
		}

		// Resting legs stretch along the ground. While moving, the ankles alternate between a tucked knee and a
		// push backward, so the body visibly crawls instead of sliding forward on two motionless legs.
		foreach ( var leg in _legs ) LayLeg( leg, lowerRotation, ground, blend, roll, crawl, crawlPhase );

		// Parents can propagate changes to children, so solve the whole pose before writing any of it.
		foreach ( var bone in _bones )
			if ( _group[bone.Index] != Group.None ) body.SceneModel.SetBoneWorldTransform( bone.Index, _pose[bone.Index] );
		// The held gun and holstered equipment hang from bone GameObjects, updated before this layer runs.
		foreach ( var bone in _bones )
			if ( _group[bone.Index] != Group.None && _boneObjects[bone.Index].IsValid() ) _boneObjects[bone.Index].WorldTransform = _pose[bone.Index];
		MergeGarments( body );
	}

	/// <summary>
	/// After <see cref="Apply"/>, bring <paramref name="gun"/> up to the shoulder with its sights at
	/// <paramref name="eye"/>, aimed along <paramref name="aim"/>, and the support hand onto its grip, by
	/// <paramref name="weight"/>. The rifle hold carries a gun at the hip, which lying down put it under the floor. The
	/// gun rides the right hand's bone object, so it follows the hand. <paramref name="buttToEye"/> is how far in front of
	/// the gun's back the eye sits (<see cref="LightweightCombatBot.EyeOnGun"/>).
	/// </summary>
	public void ShoulderGun( SkinnedModelRenderer body, WorldModel gun, Vector3 eye, Vector3 aim, float weight, float buttToEye )
	{
		if ( weight <= 0f || !gun.IsValid() || !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null || aim.IsNearZeroLength ) return;
		var handBone = body.Model.Bones.GetBone( "hand_R" ) ?? body.Model.Bones.GetBone( "r_hand" );
		var handObject = handBone is null ? null : body.GetBoneObject( handBone.Index );
		if ( !handObject.IsValid() ) return;

		// The gun's mount on the hand as it is, so the hand keeps its grip whatever the socket.
		var hand = body.SceneModel.GetBoneWorldTransform( handBone.Index );
		handObject.WorldTransform = hand;
		var mount = hand.ToLocal( gun.WorldTransform );
		var rotation = Rotation.LookAt( aim.Normal, Vector3.Up );
		var sighted = new Transform( eye - rotation * LightweightCombatBot.EyeOnGun( gun, buttToEye ), rotation );
		if ( !_rightHand.Apply( body, sighted.ToWorld( mount.ToLocal( global::Transform.Zero ) ), weight ) ) return;
		UpdateArmObjects( body );

		var grip = gun.IkLeftHand;
		if ( grip.IsValid() && grip.Active )
		{
			var target = MilitaryUniform.HandIkTransform( body.Model, "hand_left", body.WorldTransform.ToLocal( grip.WorldTransform ) );
			if ( _leftHand.Apply( body, body.WorldTransform.ToWorld( target ), weight ) ) UpdateArmObjects( body );
		}
		MergeGarments( body );
	}

		private void LayLeg( Leg leg, Rotation lowerRotation, float ground, float blend, float roll, float crawl, float crawlPhase )
	{
		var upper = _pose[leg.Upper];
		var lower = _pose[leg.Lower];
		var foot = _pose[leg.Foot];
		var reach = _anim[leg.Upper].Position.Distance( _anim[leg.Lower].Position ) + _anim[leg.Lower].Position.Distance( _anim[leg.Foot].Position );
		var outward = lowerRotation.Left * (leg.Left ? 1f : -1f);
			var step = MathF.Sin( crawlPhase + (leg.Left ? 0f : MathF.PI) );
			var extension = 0.97f - crawl * (0.11f - 0.1f * step);
			var ankle = upper.Position - lowerRotation.Up * (reach * extension)
				+ outward * (MathX.Lerp( LegSpreadFaceDown, LegSpreadSupine, roll ) + crawl * 1.5f);
			ankle.z = MathF.Max( ankle.z, ground + MathX.Lerp( AnkleHeightFaceDown, AnkleHeightSupine, roll )
				+ crawl * MathF.Max( 0f, -step ) * 2f );
			// Bring crawling knees out to the sides. Keeping an outward pole throughout the changeover avoids
			// flipping the knee when the resting downward bend transitions into a lifted crawling bend.
			var bend = Vector3.Lerp( lowerRotation.Forward, outward * 0.75f + Vector3.Up * 0.3f, crawl );
			var pole = Vector3.Lerp( (lower.Position - upper.Position).Normal, bend, blend );
		ThirdPersonSlidePose.SolveLeg( upper, lower, foot, Vector3.Lerp( foot.Position, ankle, blend ), pole, foot.Rotation,
			out var solvedUpper, out var solvedLower, out var solvedFoot );
		foreach ( var i in leg.Bones )
		{
			var segment = leg.Segments[i];
			var from = segment == 0 ? upper : segment == 1 ? lower : foot;
			var to = segment == 0 ? solvedUpper : segment == 1 ? solvedLower : solvedFoot;
			_pose[i] = to.ToWorld( from.ToLocal( _pose[i] ) );
		}
	}

	private void UpdateArmObjects( SkinnedModelRenderer body )
	{
		if ( !_updateBoneObjects ) return;
		foreach ( var bone in _bones )
			if ( _group[bone.Index] == Group.Arms && _boneObjects[bone.Index].IsValid() )
				_boneObjects[bone.Index].WorldTransform = body.SceneModel.GetBoneWorldTransform( bone.Index );
	}

	private static void MergeGarments( SkinnedModelRenderer body )
	{
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
			if ( garment != body && garment.IsValid() && garment.Enabled && garment.BoneMergeTarget == body && garment.SceneModel.IsValid() )
				garment.SceneModel.MergeBones( body.SceneModel );
	}

	private void TurnAbout( int[] bones, Vector3 pivot, Rotation turn )
	{
		foreach ( var i in bones )
		{
			var t = _anim[i];
			_anim[i] = new Transform( pivot + turn * (t.Position - pivot), turn * t.Rotation, t.Scale );
		}
	}

	private void Build( SkinnedModelRenderer body, bool updateBoneObjects )
	{
		_body = body;
		_model = body.Model;
		_updateBoneObjects = updateBoneObjects;
		int Find( params string[] names )
		{
			foreach ( var name in names ) if ( _model.Bones.GetBone( name ) is { } bone ) return bone.Index;
			return -1;
		}
		_pelvis = Find( "pelvis" );
		_spine = Find( "spine_0", "spine1", "spine_1" );
		_neck = Find( "neck_0", "neck" );
		_clavicleL = Find( "clavicle_L", "l_clavicle" );
		_clavicleR = Find( "clavicle_R", "r_clavicle" );
		var ankleL = Find( "ankle_L", "l_foot" );
		var ankleR = Find( "ankle_R", "r_foot" );
		_bones = _model.Bones.AllBones.OrderBy( b => Depth( b.Index ) ).ToArray();
		_group = new Group[_model.BoneCount];
		_anim = new Transform[_model.BoneCount];
		_pose = new Transform[_model.BoneCount];
		_boneObjects = new GameObject[_model.BoneCount];
		_legs = new[] { BuildLeg( ankleL, true ), BuildLeg( ankleR, false ) }.Where( l => l is not null ).ToArray();
		if ( _pelvis < 0 || _spine < 0 || _neck < 0 || _clavicleL < 0 || _clavicleR < 0 || _legs.Length < 2 )
		{
			_pelvis = -1;
			return;
		}
		_feet = new[] { ankleL, ankleR };
		foreach ( var bone in _bones )
		{
			var i = bone.Index;
			_group[i] = Under( i, _neck ) ? Group.Head
				: Under( i, _clavicleL ) || Under( i, _clavicleR ) ? Group.Arms
				: Under( i, _spine ) ? Group.Upper
				: Under( i, _pelvis ) ? Group.Lower
				: Group.None;
			_boneObjects[i] = updateBoneObjects && _group[i] != Group.None ? body.GetBoneObject( i ) : null;
		}
		_footBones = _feet.Select( foot => _bones.Where( b => Under( b.Index, foot ) ).Select( b => b.Index ).ToArray() ).ToArray();

		// Where a level look puts the eyes over the neck, from the bind pose.
		var eyeL = Find( "eye_L" );
		var eyeR = Find( "eye_R" );
		Vector3 Bind( int index ) => _model.Bones.AllBones.First( b => b.Index == index ).LocalTransform.Position;
		var neckBind = Bind( _neck );
		var eyes = eyeL >= 0 && eyeR >= 0 ? (Bind( eyeL ) + Bind( eyeR )) * 0.5f : neckBind + new Vector3( 4f, 0f, 7.3f );
		_eyeAboveNeck = eyes - neckBind;
	}

	private Leg BuildLeg( int foot, bool left )
	{
		var lower = foot < 0 ? -1 : _model.GetBoneParent( foot );
		var upper = lower < 0 ? -1 : _model.GetBoneParent( lower );
		if ( upper < 0 ) return null;
		var leg = new Leg { Upper = upper, Lower = lower, Foot = foot, Left = left,
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
