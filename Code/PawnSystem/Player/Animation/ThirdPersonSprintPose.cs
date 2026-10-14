namespace Facepunch;

/// <summary>A two-handed chest carry layered over the running animation, for players and combat bots.</summary>
public sealed class ThirdPersonSprintPose
{
	private readonly BotSupportHand _grip = new( true );
	private readonly BotSupportHand _support = new();
	private readonly BotWeaponPose _weaponShape = new();
	private SkinnedModelRenderer _body;
	private Model _model;
	private int _pelvis = -1, _neck = -1, _leftShoulder = -1, _rightShoulder = -1, _rightHand = -1;
	private Transform _handToWeapon;
	private Vector3? _indexInHand;
	private WorldModel _mountedGun;
	private Transform _normalGunLocal;
	private BoneCollection.Bone[] _armBones = Array.Empty<BoneCollection.Bone>();
	private GameObject[] _boneObjects = Array.Empty<GameObject>();
	private bool _updateBoneObjects;

	public static float UpdateBlend( float blend, bool sprinting, float delta ) => sprinting
		? MathF.Min( 1f, blend + MathF.Max( 0f, delta ) / .18f )
		: MathF.Max( 0f, blend - MathF.Max( 0f, delta ) / .22f );

	public bool Apply( SkinnedModelRenderer body, WorldModel gun, float blend, float supportWeight = 1f, bool updateBoneObjects = true, Transform? handToWeaponOverride = null )
	{
		// Each frame starts from the authored hand socket. A corrected grip must also release on the final
		// frame of the fade, on weapon switches, and when a reload or another stance takes over.
		Reset();
		if ( blend <= 0f || !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null
			|| !gun.IsValid() || !gun.ModelRenderer.IsValid() || gun.ModelRenderer.Model is null
			|| !gun.IkLeftHand.IsValid() || !gun.IkLeftHand.Active ) return false;
		if ( _body != body || _model != body.Model || _updateBoneObjects != updateBoneObjects ) Build( body, updateBoneObjects );
		if ( _pelvis < 0 || _neck < 0 || _leftShoulder < 0 || _rightShoulder < 0 || _rightHand < 0 ) return false;

		var scene = body.SceneModel;
		var shoulders = (scene.GetBoneWorldTransform( _leftShoulder ).Position + scene.GetBoneWorldTransform( _rightShoulder ).Position) * .5f;
		var up = (scene.GetBoneWorldTransform( _neck ).Position - scene.GetBoneWorldTransform( _pelvis ).Position).Normal;
		var left = (scene.GetBoneWorldTransform( _leftShoulder ).Position - scene.GetBoneWorldTransform( _rightShoulder ).Position).Normal;
		var forward = left.Cross( up ).Normal;
		if ( forward.IsNearZeroLength || up.IsNearZeroLength ) return false;
		var chest = new Transform( shoulders, Rotation.LookAt( forward, up ), body.WorldScale );
		blend = blend.Clamp( 0f, 1f );
		var weight = blend * blend * (3f - 2f * blend);
		var mount = handToWeaponOverride ?? _handToWeapon;
		if ( _indexInHand is { } index && gun.Muzzle.IsValid() )
		{
			// Put the index knuckle beside the trigger rather than under the pistol grip. The cloud M4's bore
			// is higher in model space than the ported guns', so their fixed socket cannot give the same grip.
			var bore = gun.WorldTransform.PointToLocal( gun.Muzzle.WorldPosition ).z;
			var correction = (bore - 1.5f - mount.PointToLocal( index ).z).Clamp( -2f, 6f );
			mount = mount.ToWorld( new Transform( new Vector3( 0f, 0f, -correction * weight ) ) );
		}
		var stock = _weaponShape.ButtstockContact( gun );
		var rightShoulder = chest.PointToLocal( scene.GetBoneWorldTransform( _rightShoulder ).Position );
		var pocket = chest.PointToWorld( new Vector3( 6f, rightShoulder.y + 1.5f, 1f ) );
		// Keep the pad on the animated chest, but absorb most of the shoulders' twisting stride in the arms.
		// Following that twist completely swings the muzzle sideways across the body on every other step.
		var carryForward = Vector3.Lerp( scene.Transform.Rotation.Forward, forward, .25f ).Normal;
		var carryFrame = Rotation.LookAt( carryForward, up );
		var weaponToWrist = mount.ToLocal( global::Transform.Zero );
		var supportLocal = gun.WorldTransform.PointToLocal( gun.IkLeftHand.WorldPosition );
		var wrist = global::Transform.Zero;
		var bestError = float.MaxValue;
		Transform Candidate( float extraYaw, out float error )
		{
			var rotation = carryFrame * Rotation.From( 20f, 50f + extraYaw, -10f );
			// Looking far sideways while moving must not put the muzzle behind the chest's front surface.
			var relative = (chest.Rotation.Inverse * rotation).Angles();
			rotation = chest.Rotation * Rotation.From( relative.pitch, relative.yaw.Clamp( -75f, 75f ), relative.roll );
			var carried = new Transform( pocket - rotation * stock, rotation );
			var candidate = carried.ToWorld( weaponToWrist );
			var leftTarget = carried.PointToWorld( supportLocal );
			error = _grip.Reachable( body, candidate.Position ).Distance( candidate.Position )
				+ _support.Reachable( body, leftTarget ).Distance( leftTarget ) * supportWeight;
			return candidate;
		}
		// A bullpup or a long handguard needs a slightly more diagonal carry. Turn about the stock pad until
		// both grips fit the arms, instead of letting the support hand hang short of its grip during a step.
		for ( var extraYaw = 0f; extraYaw <= 75f; extraYaw += 5f )
		{
			var candidate = Candidate( extraYaw, out var error );
			if ( error < bestError ) { bestError = error; wrist = candidate; }
			if ( error >= .001f ) continue;
			// Refine the first reachable angle so a changing stride does not jump between five-degree poses.
			var low = MathF.Max( 0f, extraYaw - 5f );
			var high = extraYaw;
			for ( var i = 0; i < 4 && high > low; i++ )
			{
				var middle = (low + high) * .5f;
				var refined = Candidate( middle, out var refinedError );
				if ( refinedError < .001f ) { high = middle; wrist = refined; }
				else low = middle;
			}
			break;
		}
		var animatedWrist = scene.GetBoneWorldTransform( _rightHand ).WithScale( 1f );
		wrist = new Transform( Vector3.Lerp( animatedWrist.Position, wrist.Position, weight ), Rotation.Lerp( animatedWrist.Rotation, wrist.Rotation, weight ) );
		// Keep the intermediate stock outside the torso as well as keeping both grips within reach.
		_mountedGun = gun;
		_normalGunLocal = gun.LocalTransform;
		var intermediateGun = wrist.ToWorld( mount );
		gun.WorldTransform = intermediateGun;
		var shift = _weaponShape.Fit( body, gun, _support, _grip, wrist.Position, supportWeight, chestFront: 6f, preferSideways: true );
		wrist = wrist.WithPosition( wrist.Position + shift );
		_grip.ApplyWithPole( body, wrist, chest.Rotation * new Vector3( 3f, -5f, -16f ), poleWeight: weight );
		MountWeapon( gun, mount );
		var hand = body.WorldTransform.ToLocal( gun.IkLeftHand.WorldTransform );
		hand = MilitaryUniform.HandIkTransform( body.Model, "hand_left", hand );
		_support.ApplyWithPole( body, body.WorldTransform.ToWorld( hand ), chest.Rotation * new Vector3( 3f, 5f, -16f ), supportWeight, weight );
		// Players' guns and holstered equipment use bone objects; bots normally use their cheaper hand follower.
		for ( var i = 0; i < _armBones.Length; i++ )
			if ( _boneObjects[i].IsValid() ) _boneObjects[i].WorldTransform = scene.GetBoneWorldTransform( _armBones[i].Index );
		MountWeapon( gun, mount );
		return true;
	}

	public void Reset()
	{
		if ( _mountedGun.IsValid() ) _mountedGun.LocalTransform = _normalGunLocal;
		_mountedGun = null;
	}

	private void MountWeapon( WorldModel gun, Transform mount ) => gun.WorldTransform = _body.SceneModel.GetBoneWorldTransform( _rightHand ).WithScale( 1f ).ToWorld( mount );

	private void Build( SkinnedModelRenderer body, bool updateBoneObjects )
	{
		_body = body;
		_model = body.Model;
		_updateBoneObjects = updateBoneObjects;
		int Bone( string human, string legacy ) => (_model.Bones.GetBone( human ) ?? _model.Bones.GetBone( legacy ))?.Index ?? -1;
		_pelvis = Bone( "pelvis", "pelvis" );
		_neck = Bone( "neck_0", "neck" );
		_leftShoulder = Bone( "arm_upper_L", "l_upperarm" );
		_rightShoulder = Bone( "arm_upper_R", "r_upperarm" );
		_rightHand = Bone( "hand_R", "r_hand" );
		var index = _model.Bones.GetBone( "finger_index_0_R" );
		_indexInHand = index is not null && _rightHand >= 0
			? _model.GetBoneTransform( _rightHand ).PointToLocal( _model.GetBoneTransform( index.Index ).Position ) : null;
		var hold = MilitaryUniform.UsesHumanSkeleton( _model ) ? null : _model.Bones.GetBone( "hold_r" ) ?? _model.Bones.GetBone( "hold_R" );
		_handToWeapon = hold is null || _rightHand < 0 ? MilitaryUniform.WeaponHandOffset( _model )
			: _model.GetBoneTransform( _rightHand ).ToLocal( _model.GetBoneTransform( hold.Index ) );
		_armBones = _model.Bones.AllBones.Where( b => Under( b.Index, _leftShoulder ) || Under( b.Index, _rightShoulder ) )
			.OrderBy( b => Depth( b.Index ) ).ToArray();
		_boneObjects = _armBones.Select( b => updateBoneObjects ? body.GetBoneObject( b.Index ) : null ).ToArray();
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
