namespace Facepunch;

public sealed class AnimationHelper : Component
{
	[Property] public SkinnedModelRenderer Target { get; set; }

	[Property] public GameObject EyeSource { get; set; }


	[Property, Range( 0.5f, 1.5f )] public float Height { get; set; } = 1.0f;

	[Property] public GameObject IkLeftHand { get; set; }
	[Property] public GameObject IkRightHand { get; set; }
	[Property] public GameObject IkLeftFoot { get; set; }
	[Property] public GameObject IkRightFoot { get; set; }
	/// <summary>An override in this model's own wrist axes, rather than a legacy weapon socket's axes.</summary>
	public Transform? LeftHandOverride { get; set; }

	public void ProceduralHitReaction( float damageScale = 1.0f, Vector3 force = default )
	{
		var boneId = 0;
		var tx = Target.GetBoneObject( boneId );

		if ( !tx.IsValid() ) return;

		var localToBone = tx.Transform.Local.Position;
		if ( localToBone == Vector3.Zero ) localToBone = Vector3.One;

		Target.SetBool( "hit", true );
		Target.Set( "hit_bone", boneId );
		Target.Set( "hit_offset", localToBone );
		Target.Set( "hit_direction", force.Normal );
		Target.Set( "hit_strength", (force.Length / 1000.0f) * damageScale );
	}

	protected override void OnUpdate()
	{
		Target.Set( "scale_height", Height );

		// SetIk( "left_hand", ... );
		// SetIk( "right_hand", ... );

		if ( LeftHandOverride is { } leftHand ) SetIk( "hand_left", leftHand, convertHandAxes: false );
		else if ( IkLeftHand.IsValid() && IkLeftHand.Active ) SetIk( "hand_left", IkLeftHand.Transform.World );
		else ClearIk( "hand_left" );

		if ( IkRightHand.IsValid() && IkRightHand.Active ) SetIk( "hand_right", IkRightHand.Transform.World );
		else ClearIk( "hand_right" );

		if ( IkLeftFoot.IsValid() && IkLeftFoot.Active ) SetIk( "foot_left", IkLeftFoot.Transform.World );
		else ClearIk( "foot_left" );

		if ( IkRightFoot.IsValid() && IkRightFoot.Active ) SetIk( "foot_right", IkRightFoot.Transform.World );
		else ClearIk( "foot_right" );
	}

	public void SetIk( string name, Transform tx, bool convertHandAxes = true )
	{
		// convert local to model
		tx = Target.Transform.World.ToLocal( tx );
		if ( convertHandAxes ) tx = MilitaryUniform.HandIkTransform( Target.Model, name, tx );

		Target.SetBool( $"ik.{name}.enabled", true );
		Target.Set( $"ik.{name}.position", tx.Position );
		Target.Set( $"ik.{name}.rotation", tx.Rotation );
	}

	public void ClearIk( string name )
	{
		Target.SetBool( $"ik.{name}.enabled", false );
	}

	public Transform GetEyeWorldTransform
	{
		get
		{
			if ( EyeSource.IsValid() ) return EyeSource.Transform.World;

			return Transform.World;
		}
	}


	/// <summary>
	/// Have the player look at this point in the world
	/// </summary>
	public void WithLook( Vector3 lookDirection )
	{
		Target.SetLookDirection( "aim_body", lookDirection );
		Target.Set( "aim_body_weight", 1f );
	}

	public void WithVelocity( Vector3 Velocity )
	{
		var dir = Velocity;
		var forward = Target.WorldRotation.Forward.Dot( dir );
		var sideward = Target.WorldRotation.Right.Dot( dir );

		var angle = MathF.Atan2( sideward, forward ).RadianToDegree().NormalizeDegrees();

		Target.Set( "move_direction", angle );
		Target.Set( "move_speed", Velocity.Length );
		Target.Set( "move_groundspeed", Velocity.WithZ( 0 ).Length );
		Target.Set( "move_y", sideward );
		Target.Set( "move_x", forward );
		Target.Set( "move_z", Velocity.z );
	}

	public void WithWishVelocity( Vector3 Velocity )
	{
		var dir = Velocity;
		var forward = Target.WorldRotation.Forward.Dot( dir );
		var sideward = Target.WorldRotation.Right.Dot( dir );

		var angle = MathF.Atan2( sideward, forward ).RadianToDegree().NormalizeDegrees();

		Target.Set( "wish_direction", angle );
		Target.Set( "wish_speed", Velocity.Length );
		Target.Set( "wish_groundspeed", Velocity.WithZ( 0 ).Length );
		Target.Set( "wish_y", sideward );
		Target.Set( "wish_x", forward );
		Target.Set( "wish_z", Velocity.z );
	}

	public Rotation AimAngle
	{
		set
		{
			value = Target.WorldRotation.Inverse * value;
			var ang = value.Angles();

			Target.Set( "aim_body_pitch", ang.pitch );
			Target.Set( "aim_body_yaw", ang.yaw );
		}
	}


	public float FootShuffle
	{
		get => Target.GetFloat( "move_shuffle" );
		set => Target.Set( "move_shuffle", value );
	}

	public float DuckLevel
	{
		get => Target.GetFloat( "duck" );
		set => Target.Set( "duck", value );
	}

	public float VoiceLevel
	{
		get => Target.GetFloat( "voice" );
		set => Target.Set( "voice", value );
	}

	public bool IsSitting
	{
		get => Target.GetFlag( "b_sit" );
		set => Target.SetBool( "b_sit", value );
	}

	public bool IsGrounded
	{
		get => Target.GetFlag( "b_grounded" );
		set => Target.SetBool( "b_grounded", value );
	}

	public bool IsSwimming
	{
		get => Target.GetFlag( "b_swim" );
		set => Target.SetBool( "b_swim", value );
	}

	public float SkidAmount
	{
		get => Target.GetFloat( "skid" );
		set => Target.Set( "skid", value );
	}

	public bool IsClimbing
	{
		get => Target.GetFlag( "b_climbing" );
		set => Target.SetBool( "b_climbing", value );
	}

	public bool IsNoclipping
	{
		get => Target.GetFlag( "b_noclip" );
		set => Target.SetBool( "b_noclip", value );
	}

	public bool IsWeaponLowered
	{
		get => Target.GetFlag( "b_weapon_lower" );
		set => Target.SetBool( "b_weapon_lower", value );
	}

	public enum HoldTypes
	{
		None,
		Pistol,
		Rifle,
		Shotgun,
		HoldItem,
		Punch,
		Swing,
		RPG
	}

	public HoldTypes HoldType
	{
		get => (HoldTypes)Target.GetInt( "holdtype" );
		set => Target.Set( "holdtype", (int)value );
	}

	public enum Hand
	{
		Both,
		Right,
		Left
	}

	public Hand Handedness
	{
		get => (Hand)Target.GetInt( "holdtype_handedness" );
		set => Target.Set( "holdtype_handedness", (int)value );
	}

	public void TriggerJump()
	{
		Target.SetBool( "b_jump", true );
	}

	public void TriggerDeploy()
	{
		Target.SetBool( "b_deploy", true );
	}

	public enum MoveStyles
	{
		Auto,
		Walk,
		Run
	}

	/// <summary>
	/// We can force the model to walk or run, or let it decide based on the speed.
	/// </summary>
	public MoveStyles MoveStyle
	{
		get => (MoveStyles)Target.GetInt( "move_style" );
		set => Target.Set( "move_style", (int)value );
	}
}
