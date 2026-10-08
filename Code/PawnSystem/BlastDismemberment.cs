namespace Facepunch;

[Flags]
public enum BlastLimb
{
	None = 0,
	LeftLeg = 1,
	RightLeg = 2,
	LeftArm = 4,
	RightArm = 8
}

/// <summary>Releases exposed knee/elbow joints after a lethal close blast. No bleeding is simulated.</summary>
public static class BlastDismemberment
{
	// A gameplay threshold for a near-contact blast, independent of the grenade's wider damage radius.
	public const float SeverDistance = 40f;
	private const string SplitTrousers = "models/dismemberment/trousers.vmdl";
	private const string SplitShirt = "models/dismemberment/shirt.vmdl";
	private static readonly (BlastLimb Limb, string Bone)[] Cuts =
	{
		(BlastLimb.LeftLeg, "leg_lower_L"), (BlastLimb.RightLeg, "leg_lower_R"),
		(BlastLimb.LeftArm, "arm_lower_L"), (BlastLimb.RightArm, "arm_lower_R")
	};

	/// <summary>The host checks each joint in the victim's current pose, including cover, before broadcasting the kill.</summary>
	public static BlastLimb Select( HealthComponent health, Vector3 origin, SceneTrace trace )
	{
		var renderer = GameUtils.GetPlayerFromComponent( health )?.Body?.Renderer
			?? GameUtils.GetLightweightBotFromComponent( health )?.Renderer;
		if ( !renderer.IsValid() || renderer.Model?.Name != MilitaryUniform.HumanModelPath ) return BlastLimb.None;

		var result = BlastLimb.None;
		foreach ( var (limb, name) in Cuts )
		{
			if ( !renderer.TryGetBoneTransform( name, out var joint )
				|| !InRange( origin.DistanceSquared( joint.Position ) ) ) continue;
			var hit = trace.WithoutTags( "player", "enemy", "movement", "grenade", "particles" )
				.IgnoreGameObjectHierarchy( health.GameObject.Root ).Ray( origin, joint.Position ).Run();
			if ( !hit.Hit && !hit.StartedSolid ) result |= limb;
		}
		return SupportedLimbs( renderer, result );
	}

	public static bool InRange( float distanceSquared ) => distanceSquared >= 0f && distanceSquared <= SeverDistance * SeverDistance;

	/// <summary>Called after the ragdoll's initial velocities are set, once its physics bodies and joints exist.</summary>
	public static BlastLimb Apply( ModelPhysics physics, BlastLimb requested, Vector3 origin )
	{
		if ( requested == BlastLimb.None || !physics.IsValid() || !physics.Renderer.IsValid()
			|| physics.Model?.Name != MilitaryUniform.HumanModelPath ) return BlastLimb.None;
		// Leave an ordinary ragdoll if its outfit cannot be split; releasing the joint alone stretches its mesh.
		requested = SupportedLimbs( physics.Renderer, requested );

		var released = BlastLimb.None;
		foreach ( var (limb, name) in Cuts )
		{
			if ( (requested & limb) == 0 ) continue;
			var bone = physics.Model.Bones.GetBone( name );
			if ( bone is null ) continue;
			var severed = new HashSet<Rigidbody>();
			foreach ( var part in physics.Bodies )
			{
				if ( part.Component is not Rigidbody body || !body.IsValid()
					|| part.Bone < 0 || part.Bone >= physics.Model.Bones.AllBones.Count ) continue;
				for ( var b = physics.Model.Bones.AllBones[part.Bone]; b is not null; b = b.Parent )
				{
					if ( b != bone ) continue;
					severed.Add( body );
					break;
				}
			}

			var removed = false;
			foreach ( var joint in physics.Joints.ToArray() )
			{
				if ( !joint.Component.IsValid() || joint.Body1.Component is not Rigidbody a || joint.Body2.Component is not Rigidbody b ) continue;
				if ( severed.Contains( a ) == severed.Contains( b ) ) continue;
				joint.Component.Destroy();
				physics.Joints.Remove( joint );
				removed = true;
			}
			if ( !removed ) continue;
			released |= limb;
			foreach ( var body in severed )
			{
				body.Velocity += (body.WorldPosition - origin).Normal * 90f;
				body.AngularVelocity += new Vector3( 1.5f, -1f, 0.75f );
			}
		}

		if ( released != BlastLimb.None ) SplitClothing( physics.Renderer, released );
		return released;
	}

	private static void SplitClothing( SkinnedModelRenderer body, BlastLimb limbs )
	{
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
		{
			if ( garment == body || garment.BoneMergeTarget != body ) continue;
			var path = garment.Model?.Name ?? "";
			var legs = path.Contains( "cargo_pants", StringComparison.OrdinalIgnoreCase ) || path == SplitTrousers;
			var arms = path.Contains( "army_shirt", StringComparison.OrdinalIgnoreCase ) || path == SplitShirt;
			if ( !(legs && (limbs & (BlastLimb.LeftLeg | BlastLimb.RightLeg)) != 0)
				&& !(arms && (limbs & (BlastLimb.LeftArm | BlastLimb.RightArm)) != 0) ) continue;
			var model = Model.Load( legs ? SplitTrousers : SplitShirt );
			if ( model is null || model.IsError ) continue;
			garment.Model = model;
			garment.SetBodyGroup( "LeftCut", garment.GetBodyGroup( "LeftCut" ) == 1
				|| (limbs & (legs ? BlastLimb.LeftLeg : BlastLimb.LeftArm)) != 0 ? 1 : 0 );
			garment.SetBodyGroup( "RightCut", garment.GetBodyGroup( "RightCut" ) == 1
				|| (limbs & (legs ? BlastLimb.RightLeg : BlastLimb.RightArm)) != 0 ? 1 : 0 );
			var leftCut = garment.GetBodyGroup( "LeftCut" ) == 1;
			var rightCut = garment.GetBodyGroup( "RightCut" ) == 1;
			garment.SetBodyGroup( "CutPattern", leftCut && rightCut ? 2 : leftCut ? 0 : 1 );
		}
	}

	private static BlastLimb SupportedLimbs( SkinnedModelRenderer body, BlastLimb requested )
	{
		if ( requested == BlastLimb.None ) return BlastLimb.None;
		var supported = BlastLimb.None;
		foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
		{
			if ( garment == body || garment.BoneMergeTarget != body || !garment.Enabled ) continue;
			var path = garment.Model?.Name ?? "";
			var legs = path.Contains( "cargo_pants", StringComparison.OrdinalIgnoreCase ) || path == SplitTrousers;
			var arms = path.Contains( "army_shirt", StringComparison.OrdinalIgnoreCase ) || path == SplitShirt;
			var limbs = requested & (legs ? BlastLimb.LeftLeg | BlastLimb.RightLeg
				: arms ? BlastLimb.LeftArm | BlastLimb.RightArm : BlastLimb.None);
			if ( limbs == BlastLimb.None ) continue;
			var split = Model.Load( legs ? SplitTrousers : SplitShirt );
			if ( split is not null && !split.IsError && split.Parts.Get( "LeftCut" ) is not null
				&& split.Parts.Get( "RightCut" ) is not null && split.Parts.Get( "CutPattern" ) is not null ) supported |= limbs;
		}
		return supported;
	}
}
