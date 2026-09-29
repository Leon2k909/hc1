namespace Facepunch;

/// <summary>
/// How a body goes down. People shot dead seldom go limp on the spot: a hit to the brain or the upper spine does that,
/// and so do a blast or a fall. Most sag as their muscles let go. The knees buckle, they stumble on the way they were
/// going, sink to their knees and slump over, sit back, or go down on the side of a leg that gave out.
/// </summary>
public enum DeathStyle
{
	/// <summary> Limp at once: head, neck and spine hits, blasts, falls, and anyone already down or in the air. </summary>
	Drop,
	/// <summary> The knees give out within a second, and the body folds forward or to one side. </summary>
	Buckle,
	/// <summary> Carried on by their own momentum, a stumble, then down the way they were going. </summary>
	Stagger,
	/// <summary> Sinks to the knees over a couple of seconds, the head dropping first, then slumps over. </summary>
	Slump,
	/// <summary> The legs fold under them onto their backside, then they go over backwards. </summary>
	SitBack,
	/// <summary> The shot leg gives way first, and they go down on that side. </summary>
	LegGives
}

/// <summary>
/// A death, worked out the same on every machine from what they were all sent (<see cref="Choose"/>): the kill's damage
/// and where it landed, and the victim's id, so every machine rolls the same dice. Only how fast the victim was moving
/// can differ a little between machines, as it does in life.
/// </summary>
public struct DeathPlan
{
	public DeathStyle Style;
	/// <summary> Seconds from the kill until the body is fully limp. </summary>
	public float Duration;
	/// <summary> Level direction the body goes over in at the end; zero to let it fall as it will. </summary>
	public Vector3 FallDirection;
	/// <summary> Level direction of the shot leg's side from the body, for <see cref="DeathStyle.LegGives"/>. </summary>
	public Vector3 HitSide;
	/// <summary> How the victim was moving: the body keeps it. </summary>
	public Vector3 Velocity;
	public Vector3 HitPosition;
	/// <summary> The jolt the hit gives the part it hit (every part, for a blast), in units a second. </summary>
	public Vector3 HitVelocity;
	public bool Blast;

	public static DeathPlan Limp => new() { Style = DeathStyle.Drop };

	/// <param name="damage">The killing hit.</param>
	/// <param name="victim">The victim's id, the same on every machine.</param>
	/// <param name="position">The victim's feet.</param>
	/// <param name="facing">Which way the victim faced.</param>
	/// <param name="velocity">How the victim was moving.</param>
	/// <param name="crouched">Crouched: less far to go down.</param>
	/// <param name="down">Prone, knocked down or in the air: nothing to collapse from.</param>
	public static DeathPlan Choose( DamageInfo damage, Guid victim, Vector3 position, Rotation facing, Vector3 velocity,
		bool crouched, bool down )
	{
		var dice = new Dice( Seed( victim, damage.Position ) );
		var forward = facing.Forward.WithZ( 0f ).Normal;
		var right = facing.Right.WithZ( 0f ).Normal;
		var moving = velocity.WithZ( 0f ).Length > 120f;
		var hitbox = damage.Hitbox;
		var flags = damage.Flags;
		var direction = damage.Force.IsNearZeroLength ? Vector3.Zero : damage.Force.Normal;

		var plan = new DeathPlan
		{
			Velocity = velocity,
			HitPosition = damage.Position,
			Blast = flags.HasFlag( DamageFlags.Explosion ),
			HitSide = (damage.Position - position).WithZ( 0f ).Dot( right ) >= 0f ? right : -right
		};

		// A blast throws the whole body; a bullet only jolts the part it hits. Neither knocks anyone over by itself.
		plan.HitVelocity = plan.Blast
			? (direction + Vector3.Up * 0.25f).Normal * Math.Clamp( damage.Damage * 3f, 120f, 450f )
			: direction * Math.Clamp( damage.Damage * 1.2f, 30f, 120f );

		var roll = dice.Next();
		plan.Style = true switch
		{
			_ when down || plan.Blast || flags.HasFlag( DamageFlags.FallDamage ) => DeathStyle.Drop,
			// Burning and the gas wear someone down rather than stop them.
			_ when flags.HasFlag( DamageFlags.Burn ) || flags.HasFlag( DamageFlags.Zone ) => DeathStyle.Slump,
			// The brain, brain stem or upper spine: switched off at once.
			_ when HasAny( hitbox, HitboxTags.Head | HitboxTags.Neck | HitboxTags.Spine ) => DeathStyle.Drop,
			_ when flags.HasFlag( DamageFlags.Melee ) => roll < 0.5f ? DeathStyle.Buckle : DeathStyle.Slump,
			// The chest: the heart and lungs. Many go down at once, most within a second or two.
			_ when HasAny( hitbox, HitboxTags.Chest | HitboxTags.Clavicle ) => roll switch
			{
				< 0.3f => DeathStyle.Drop,
				< 0.7f => DeathStyle.Buckle,
				< 0.85f => moving ? DeathStyle.Stagger : DeathStyle.Buckle,
				_ => DeathStyle.Slump
			},
			// The belly and pelvis: they double over the wound, or the hips give and they sit.
			_ when hitbox.HasFlag( HitboxTags.Stomach ) => roll switch
			{
				< 0.1f => DeathStyle.Drop,
				< 0.35f => DeathStyle.Buckle,
				< 0.75f => DeathStyle.Slump,
				_ => moving ? DeathStyle.Stagger : DeathStyle.SitBack
			},
			_ when HasAny( hitbox, HitboxTags.Leg | HitboxTags.Ankle ) => roll < 0.65f ? DeathStyle.LegGives : DeathStyle.Slump,
			_ when HasAny( hitbox, HitboxTags.Arm | HitboxTags.Hand ) => roll < 0.5f ? DeathStyle.Buckle : DeathStyle.Slump,
			_ => roll < 0.4f ? DeathStyle.Drop : DeathStyle.Buckle
		};

		// On the move, a buckle carries on the way they were going; crouched, there's less far to go.
		if ( plan.Style == DeathStyle.Buckle && moving && dice.Next() < 0.4f )
			plan.Style = DeathStyle.Stagger;
		if ( crouched && plan.Style is DeathStyle.Stagger or DeathStyle.SitBack )
			plan.Style = DeathStyle.Buckle;

		var burning = flags.HasFlag( DamageFlags.Burn ) || flags.HasFlag( DamageFlags.Zone );
		plan.Duration = plan.Style switch
		{
			DeathStyle.Buckle => dice.Range( 0.55f, 0.9f ),
			DeathStyle.Stagger => dice.Range( 0.8f, 1.2f ),
			DeathStyle.Slump => burning ? dice.Range( 2.2f, 3.2f ) : dice.Range( 1.6f, 2.6f ),
			DeathStyle.SitBack => dice.Range( 1.1f, 1.6f ),
			DeathStyle.LegGives => dice.Range( 0.8f, 1.3f ),
			_ => 0f
		};
		if ( crouched )
			plan.Duration *= 0.7f;

		var side = dice.Next() < 0.5f ? right : -right;
		plan.FallDirection = plan.Style switch
		{
			DeathStyle.Buckle => dice.Next() < 0.6f ? forward : (side + forward * 0.4f).Normal,
			DeathStyle.Stagger => moving ? velocity.WithZ( 0f ).Normal : forward,
			DeathStyle.Slump => dice.Next() < 0.7f ? forward : (side + forward * 0.5f).Normal,
			DeathStyle.SitBack => -forward,
			DeathStyle.LegGives => (plan.HitSide + forward * 0.3f).Normal,
			_ => Vector3.Zero
		};

		return plan;
	}

	private static bool HasAny( HitboxTags hitbox, HitboxTags any ) => ((int)hitbox & (int)any) != 0;

	/// <summary>
	/// The same on every machine: a hash of the victim's id and where the killing hit landed. A Guid's hash is made from
	/// its bits (a string's is randomised per process, so don't use one here).
	/// </summary>
	private static uint Seed( Guid victim, Vector3 position )
	{
		var hash = 2166136261u;
		hash = (hash ^ (uint)victim.GetHashCode()) * 16777619u;
		hash = (hash ^ (uint)(int)MathF.Round( position.x * 8f )) * 16777619u;
		hash = (hash ^ (uint)(int)MathF.Round( position.y * 8f )) * 16777619u;
		hash = (hash ^ (uint)(int)MathF.Round( position.z * 8f )) * 16777619u;
		return hash;
	}

	/// <summary> A tiny xorshift, so the dice are the same on every machine whatever the platform's own Random does. </summary>
	private struct Dice
	{
		private uint _state;

		public Dice( uint seed ) => _state = seed == 0 ? 0x9E3779B9u : seed;

		public float Next()
		{
			_state ^= _state << 13;
			_state ^= _state >> 17;
			_state ^= _state << 5;
			return (_state >> 8) * (1f / 16777216f);
		}

		public float Range( float min, float max ) => min + (max - min) * Next();
	}
}

/// <summary>
/// Takes a ragdoll down as a dying person goes down (<see cref="DeathPlan"/>), then leaves it limp. Everything is done at
/// the velocity level, so it doesn't depend on the physics' torque units:
/// <list type="bullet">
/// <item>Weight: the body's gravity is eased back in (<see cref="Rigidbody.GravityScale"/>), so it sinks rather than
/// dropping like a stone while the legs still hold some of it.</item>
/// <item>Muscle tone: each joint's bend speed is damped, harder while the muscles still work. Under the body's weight a
/// joint with tone gives way slowly, and one without folds at once. The arms go first (the gun falls from the hands),
/// then the legs, then the back and neck.</item>
/// <item>Balance: the chest is kept over the hips, easing toward the way the body will go over, so it sinks upright and
/// then topples that way instead of tipping over stiff like a plank.</item>
/// </list>
/// Runs on every machine, like the ragdoll itself. Theater records the bodies' bones as it does any ragdoll's.
/// </summary>
public sealed class DyingBody : Component
{
	/// <summary> How far the chest leans out over the hips toward <see cref="DeathPlan.FallDirection"/> before it goes. </summary>
	private const float LeanDistance = 16f;
	/// <summary> The balance's spring: about 1.5 Hz, critically damped. </summary>
	private const float BalanceFrequency = 1.5f;

	public ModelPhysics Physics { get; set; }
	public DeathPlan Plan { get; set; }

	private enum Region { Pelvis, Spine, Neck, Head, Arm, Leg, HitLeg }

	private sealed class Part
	{
		public Rigidbody Body;
		public Region Region;
		public float GravityScale;
	}

	private readonly List<Part> _parts = new();
	private readonly List<(Rigidbody Parent, Rigidbody Child, Region Region)> _joints = new();
	private Rigidbody _chest;
	private Rigidbody _pelvis;
	private bool _started;
	private TimeSince _sinceStart;

	/// <summary> Takes <paramref name="physics"/>'s ragdoll, just switched on, down by <paramref name="plan"/>. </summary>
	public static void Begin( ModelPhysics physics, DeathPlan plan )
	{
		if ( !physics.IsValid() )
			return;

		var dying = physics.Components.GetOrCreate<DyingBody>();
		dying.Physics = physics;
		dying.Plan = plan;
	}

	protected override void OnStart()
	{
		_sinceStart = 0f;
	}

	protected override void OnFixedUpdate()
	{
		if ( !Physics.IsValid() || !Physics.Enabled )
		{
			Destroy();
			return;
		}

		if ( !_started && !TryStart() )
		{
			// The bodies come with the ragdoll; if they haven't in a second, there's nothing to do.
			if ( _sinceStart > 1f )
				Destroy();
			return;
		}

		var u = Plan.Duration > 0f ? _sinceStart / Plan.Duration : 1f;
		if ( Plan.Style == DeathStyle.Drop || u >= 1f )
		{
			Finish();
			return;
		}

		Apply( ToneAt( u ), Time.Delta );
	}

	protected override void OnDestroy()
	{
		RestoreGravity();
	}

	private bool TryStart()
	{
		if ( Physics.Bodies is not { Count: > 0 } bodies )
			return false;

		var bones = Physics.Model?.Bones;
		foreach ( var body in bodies )
		{
			if ( body.Component is not Rigidbody rigidbody || !rigidbody.IsValid() )
				continue;

			var name = bones is not null && body.Bone >= 0 && body.Bone < bones.AllBones.Count
				? bones.AllBones[body.Bone].Name
				: rigidbody.GameObject.Name;
			_parts.Add( new Part { Body = rigidbody, Region = Classify( name ), GravityScale = rigidbody.GravityScale } );
		}

		if ( _parts.Count == 0 )
			return false;

		_started = true;
		_sinceStart = 0f;

		// The highest part of the trunk is the chest, the lowest the hips.
		foreach ( var part in _parts )
		{
			if ( part.Region is not (Region.Spine or Region.Pelvis) )
				continue;

			if ( !_chest.IsValid() || part.Body.WorldPosition.z > _chest.WorldPosition.z )
				_chest = part.Body;
			if ( !_pelvis.IsValid() || part.Body.WorldPosition.z < _pelvis.WorldPosition.z )
				_pelvis = part.Body;
		}

		if ( _chest == _pelvis )
			_chest = null;

		// The leg on the side the shot came in, for LegGives: parts of a leg on that side of the hips.
		if ( Plan.Style == DeathStyle.LegGives && _pelvis.IsValid() )
		{
			foreach ( var part in _parts )
			{
				if ( part.Region == Region.Leg && (part.Body.WorldPosition - _pelvis.WorldPosition).WithZ( 0f ).Dot( Plan.HitSide ) > 0f )
					part.Region = Region.HitLeg;
			}
		}

		foreach ( var joint in Physics.Joints ?? new() )
		{
			if ( joint.Body1.Component is Rigidbody parent && joint.Body2.Component is Rigidbody child
				&& _parts.FirstOrDefault( x => x.Body == child ) is { } part )
				_joints.Add( (parent, child, part.Region) );
		}

		// The body keeps the way it was moving, and the hit jolts the part it struck (a blast throws all of it).
		Rigidbody struck = null;
		var nearest = float.MaxValue;
		foreach ( var part in _parts )
		{
			part.Body.Velocity = Plan.Velocity + (Plan.Blast ? Plan.HitVelocity : Vector3.Zero);
			part.Body.AngularVelocity = Vector3.Zero;

			var distance = part.Body.WorldPosition.DistanceSquared( Plan.HitPosition );
			if ( distance < nearest )
			{
				nearest = distance;
				struck = part.Body;
			}
		}

		if ( !Plan.Blast && struck.IsValid() )
			struck.Velocity += Plan.HitVelocity;

		// Sitting back: the hips go back as the legs fold under them.
		if ( Plan.Style == DeathStyle.SitBack && _pelvis.IsValid() )
			_pelvis.Velocity += Plan.FallDirection * 30f;

		return true;
	}

	private static Region Classify( string name )
	{
		var n = name.ToLowerInvariant();
		if ( n.Contains( "head" ) ) return Region.Head;
		if ( n.Contains( "neck" ) ) return Region.Neck;
		if ( n.Contains( "clav" ) || n.Contains( "arm" ) || n.Contains( "hand" ) || n.Contains( "shoulder" ) || n.Contains( "elbow" )
			|| n.Contains( "wrist" ) || n.Contains( "finger" ) )
			return Region.Arm;
		// The player models' thighs are l_hip and r_hip; the citizen's are leg_upper_L and leg_upper_R.
		if ( n.Contains( "leg" ) || n.Contains( "hip" ) || n.Contains( "thigh" ) || n.Contains( "calf" ) || n.Contains( "knee" )
			|| n.Contains( "shin" ) || n.Contains( "foot" ) || n.Contains( "ankle" ) || n.Contains( "toe" ) )
			return Region.Leg;
		if ( n.Contains( "pelvis" ) ) return Region.Pelvis;
		return Region.Spine;
	}

	/// <summary> What's left of each thing holding the body up, part of the way from the kill to limp (<see cref="ToneAt"/>). </summary>
	private struct Tone
	{
		/// <summary> Share of the body's weight still held off the ground (0-1). </summary>
		public float Support;
		/// <summary> Joint damping rates, per second, by the part a joint moves. </summary>
		public float Legs, HitLeg, Spine, Neck, Arms;
		/// <summary> How much of the balance is left (0-1), and how far toward the fall it leans (0-1). </summary>
		public float Balance, Lean;
		/// <summary> How fast the feet's grip stops the body sliding while it's still light (per second). </summary>
		public float Grip;
	}

	private Tone ToneAt( float u )
	{
		// 1 until from, easing to 0 by to.
		float Fade( float from, float to )
		{
			var f = Math.Clamp( (u - from) / MathF.Max( to - from, 0.001f ), 0f, 1f );
			return 1f - f * f * (3f - 2f * f);
		}

		switch ( Plan.Style )
		{
			case DeathStyle.Buckle:
				return new Tone
				{
					Support = 0.45f * Fade( 0f, 1f ), Legs = 6f * Fade( 0f, 0.6f ), HitLeg = 6f * Fade( 0f, 0.6f ),
					Spine = 18f * Fade( 0.3f, 1f ), Neck = 12f * Fade( 0.2f, 0.9f ), Arms = 8f * Fade( 0f, 0.3f ),
					Balance = Fade( 0.5f, 1f ), Lean = 1f - Fade( 0.45f, 1f ), Grip = 3f
				};

			case DeathStyle.Stagger:
				return new Tone
				{
					Support = 0.35f * Fade( 0.2f, 1f ), Legs = 12f * Fade( 0.3f, 0.8f ), HitLeg = 12f * Fade( 0.3f, 0.8f ),
					Spine = 14f * Fade( 0.4f, 1f ), Neck = 10f * Fade( 0.3f, 0.9f ), Arms = 6f * Fade( 0f, 0.3f ),
					Balance = 0.8f * Fade( 0.3f, 0.9f ), Lean = 1f - Fade( 0.2f, 0.8f ), Grip = 0.4f
				};

			case DeathStyle.Slump:
				return new Tone
				{
					// Most of the weight held at first, sinking to the knees by halfway, then the rest goes.
					Support = u < 0.55f ? MathX.Lerp( 0.85f, 0.35f, 1f - Fade( 0.05f, 0.55f ) ) : 0.35f * Fade( 0.55f, 1f ),
					Legs = 10f * Fade( 0.1f, 0.7f ), HitLeg = 10f * Fade( 0.1f, 0.7f ),
					Spine = 20f * Fade( 0.5f, 1f ), Neck = 10f * Fade( 0.2f, 0.8f ), Arms = 5f * Fade( 0f, 0.35f ),
					Balance = Fade( 0.6f, 1f ), Lean = 1f - Fade( 0.55f, 1f ), Grip = 3f
				};

			case DeathStyle.SitBack:
				return new Tone
				{
					Support = 0.7f * Fade( 0f, 1f ), Legs = 5f * Fade( 0f, 0.5f ), HitLeg = 5f * Fade( 0f, 0.5f ),
					Spine = 18f * Fade( 0.5f, 1f ), Neck = 12f * Fade( 0.3f, 0.9f ), Arms = 6f * Fade( 0f, 0.3f ),
					Balance = Fade( 0.5f, 1f ), Lean = 1f - Fade( 0.35f, 0.9f ), Grip = 2f
				};

			case DeathStyle.LegGives:
				return new Tone
				{
					Support = 0.6f * Fade( 0f, 1f ), Legs = 10f * Fade( 0.3f, 0.8f ), HitLeg = 0f,
					Spine = 16f * Fade( 0.4f, 1f ), Neck = 10f * Fade( 0.3f, 0.9f ), Arms = 6f * Fade( 0f, 0.3f ),
					Balance = Fade( 0.4f, 1f ), Lean = 1f - Fade( 0.15f, 0.7f ), Grip = 3f
				};

			default:
				return default;
		}
	}

	private void Apply( Tone tone, float dt )
	{
		// Weight comes back as the legs stop holding it.
		foreach ( var part in _parts )
		{
			if ( !part.Body.IsValid() )
				continue;

			part.Body.GravityScale = part.GravityScale * (1f - tone.Support);

			// While the body is still light its feet can't grip the floor, so its sliding is held back here.
			var velocity = part.Body.Velocity;
			var level = velocity.WithZ( 0f );
			part.Body.Velocity = velocity - level * (1f - MathF.Exp( -tone.Grip * tone.Support * dt ));
		}

		// Muscle tone: each joint's bend slows, the more so the more tone is left.
		foreach ( var (parent, child, region) in _joints )
		{
			if ( !parent.IsValid() || !child.IsValid() )
				continue;

			var rate = region switch
			{
				Region.Leg => tone.Legs,
				Region.HitLeg => tone.HitLeg,
				Region.Arm => tone.Arms,
				Region.Neck or Region.Head => tone.Neck,
				_ => tone.Spine
			};
			if ( rate <= 0f )
				continue;

			var relative = child.AngularVelocity - parent.AngularVelocity;
			child.AngularVelocity = parent.AngularVelocity + relative * MathF.Exp( -rate * dt );
		}

		// Balance: the chest held over the hips, leaning out toward the way it'll go over.
		if ( tone.Balance > 0f && _chest.IsValid() && _pelvis.IsValid() )
		{
			var offset = (_chest.WorldPosition - _pelvis.WorldPosition).WithZ( 0f );
			var target = Plan.FallDirection * (LeanDistance * tone.Lean);
			var relative = (_chest.Velocity - _pelvis.Velocity).WithZ( 0f );
			var omega = 2f * MathF.PI * BalanceFrequency;
			var push = (target - offset) * (omega * omega) - relative * (2f * omega);
			_chest.Velocity += push * (tone.Balance * dt);
		}
	}

	/// <summary> Limp: gravity back as it was, and nothing more from here. </summary>
	private void Finish()
	{
		RestoreGravity();
		Destroy();
	}

	private void RestoreGravity()
	{
		foreach ( var part in _parts )
		{
			if ( part.Body.IsValid() )
				part.Body.GravityScale = part.GravityScale;
		}
	}
}
