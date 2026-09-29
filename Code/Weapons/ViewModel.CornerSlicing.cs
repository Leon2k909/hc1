namespace Facepunch;

/// <summary>
/// Corner slicing, like Black Ops 6's (Settings → Game → Corner Slicing): aiming down sights with a wall's edge beside
/// the sights cants the gun, its sights leaning towards the opening and its body swinging over the wall. The gun only
/// turns about the line of sight, so the sights stay on target. It's only the first-person gun: the view, the body,
/// its hitboxes and the shots don't change, so it gives nobody an advantage.
/// </summary>
public partial class ViewModel
{
	/// <summary>How far the gun cants at a corner, in degrees.</summary>
	private const float CornerCant = 15f;

	/// <summary>The fan of rays, level with the eye, that looks for a wall's edge: half its width in degrees and its rays.</summary>
	private const float CornerFanHalfWidth = 32f;
	private const int CornerFanRays = 9;
	private const float CornerRayLength = 400f;

	/// <summary>The wall beside the edge counts in full this close, fading out by <see cref="CornerWallFar"/>.</summary>
	private const float CornerWallNear = 40f;
	private const float CornerWallFar = 110f;

	/// <summary>Walls only: people, bodies, loose props and see-through glass don't make a corner.</summary>
	private static readonly string[] CornerIgnoreTags =
	{
		"trigger", "playerclip", "movement", "player", LightweightBotManager.BotTag, "enemy", "ragdoll", "corpse",
		"debris", "gib", "pickup", "weapon", "viewmodel", "glass"
	};

	// Each ray's hit, from the right of the sights to the left. Only used on the main thread, one fan at a time.
	private static readonly float[] CornerDistance = new float[CornerFanRays];
	private static readonly Vector3[] CornerPosition = new Vector3[CornerFanRays];
	private static readonly Vector3[] CornerNormal = new Vector3[CornerFanRays];
	private static readonly bool[] CornerHit = new bool[CornerFanRays];

	/// <summary>The gun's cant this frame in degrees, a roll about the line of sight: positive leans the sights right.</summary>
	public float CornerRoll { get; private set; }

	private void UpdateCornerSlicing( CameraComponent cc )
	{
		var slicing = GameSettingsSystem.Current.CornerSlicing
			&& Equipment.IsValid() && Equipment.HasTag( "aiming" ) && !Equipment.HasTag( "scoped" )
			&& Owner.CameraController.IsValid() && Owner.CameraController.Mode == CameraMode.FirstPerson;

		var lean = slicing ? FindCornerLean( Scene, cc.WorldPosition, Owner.EyeAngles, Owner.GameObject.Root ) : 0f;
		CornerRoll = CornerRoll.LerpTo( lean * CornerCant, Time.Delta * 6f );
	}

	/// <summary>
	/// -1 (lean left) to 1 (lean right): how far to cant the gun at <paramref name="eye"/> looking along
	/// <paramref name="view"/>, 0 away from corners. <paramref name="ignore"/> is the one looking, whose own body doesn't count.
	/// </summary>
	public static float FindCornerLean( Scene scene, Vector3 eye, Angles view, GameObject ignore )
	{
		// Looking well up or down, the wall beside the sights isn't what's in view.
		var level = 1f - Fade( MathF.Abs( view.pitch ), 35f, 60f );
		if ( level <= 0f ) return 0f;

		var step = 2f * CornerFanHalfWidth / (CornerFanRays - 1);

		// From the right of the sights to the left (a bigger yaw turns left).
		for ( var i = 0; i < CornerFanRays; i++ )
		{
			var direction = Rotation.FromYaw( view.yaw - CornerFanHalfWidth + i * step ).Forward;
			var tr = scene.Trace.Ray( eye, eye + direction * CornerRayLength )
				.IgnoreGameObjectHierarchy( ignore )
				.WithoutTags( CornerIgnoreTags )
				.Run();

			CornerHit[i] = tr.Hit;
			CornerDistance[i] = tr.Hit ? tr.Distance : CornerRayLength;
			CornerPosition[i] = tr.EndPosition;
			CornerNormal[i] = tr.Normal;
		}

		// A wall's edge between two neighbouring rays: the nearer one hit the wall, the other went on past its end.
		var leanRight = 0f;
		var leanLeft = 0f;
		for ( var i = 0; i + 1 < CornerFanRays; i++ )
		{
			var wallOnLeft = CornerDistance[i + 1] < CornerDistance[i];
			var near = wallOnLeft ? i + 1 : i;
			var far = wallOnLeft ? i : i + 1;
			var farDirection = Rotation.FromYaw( view.yaw - CornerFanHalfWidth + far * step ).Forward;

			if ( !IsWallEdge( eye, near, far, farDirection ) )
				continue;

			// Strongest with the wall close and its edge near the sights.
			var edgeAngle = -CornerFanHalfWidth + (i + 0.5f) * step;
			var strength = (1f - Fade( CornerDistance[near], CornerWallNear, CornerWallFar ))
				* (1f - Fade( MathF.Abs( edgeAngle ), 8f, CornerFanHalfWidth ));

			// The sights lean away from the wall, towards the opening. Edges on both sides (a doorway) cancel out.
			if ( wallOnLeft ) leanRight = MathF.Max( leanRight, strength );
			else leanLeft = MathF.Max( leanLeft, strength );
		}

		return (leanRight - leanLeft) * level;
	}

	/// <summary>
	/// Whether the <paramref name="far"/> ray went past the end of the wall the <paramref name="near"/> ray hit, rather than
	/// along the same wall (seen at a glancing angle, one flat wall's distances jump too) or into a corner of the room.
	/// </summary>
	private static bool IsWallEdge( Vector3 eye, int near, int far, Vector3 farDirection )
	{
		if ( !CornerHit[near] ) return false;

		var nearDistance = CornerDistance[near];
		var farDistance = CornerDistance[far];
		if ( nearDistance >= CornerWallFar || farDistance < nearDistance + 32f ) return false;

		// A wall, not a floor, ramp or ceiling.
		var normal = CornerNormal[near];
		if ( MathF.Abs( normal.z ) > 0.7f ) return false;

		// Where the far ray would meet the wall if it went on. Running almost along the wall, that's past the ray's reach.
		var towardsWall = Vector3.Dot( farDirection, normal );
		if ( towardsWall > -0.05f ) return false;

		var wallDistance = Vector3.Dot( CornerPosition[near] - eye, normal ) / towardsWall;
		return farDistance > wallDistance * 1.25f + 24f;
	}

	/// <summary>0 at <paramref name="from"/> easing to 1 at <paramref name="to"/>.</summary>
	private static float Fade( float value, float from, float to )
	{
		var t = ((value - from) / (to - from)).Clamp( 0f, 1f );
		return t * t * (3f - 2f * t);
	}
}
