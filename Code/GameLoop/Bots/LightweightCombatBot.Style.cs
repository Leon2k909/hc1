namespace Facepunch;

/// <summary>
/// How a soldier likes to fight, the way every player has their own game. Rolled once per name, weighted by the gun
/// it's issued (an SMG most often goes to someone who pushes, the LMG to someone who holds), and kept all match with
/// the rest of its <see cref="BotHabits"/>.
/// </summary>
public enum BotStyle
{
	/// <summary> Middle distance: strafes and steps up while it fires, and moves to a new spot every few strings. </summary>
	Rifleman,
	/// <summary> Pushes into close range: quick strafes side to side, a crouch for a moment mid-fight, and on at them. </summary>
	Rusher,
	/// <summary> Comes at the enemy round their side, closing in and hunting off to one flank, and moves once it's seen. </summary>
	Flanker,
	/// <summary>
	/// Holds an angle from further back: short peeks either side of its spot, crouched to shoot, backs off when rushed,
	/// doesn't chase far, and waits at spots on its way.
	/// </summary>
	Anchor,
	/// <summary> Long range: plants, often crouched, for aimed single shots, then moves a few metres before the next. </summary>
	Marksman,
}

/// <summary>
/// A soldier's habits in a fight: its <see cref="BotStyle"/>, then its own rolls within it, so two bots of one style still
/// fight differently. The bot manager keeps them with the name, like its gun.
/// </summary>
public struct BotHabits
{
	public BotStyle Style;
	/// <summary> 0 holds and waits for enemies to come, 1 pushes to them (<see cref="LightweightCombatBot.Aggression"/>). </summary>
	public float Aggression;
	/// <summary> The distance it likes to fight at, as a share of <see cref="LightweightCombatBot.PreferredRange"/>. </summary>
	public float Range;
	/// <summary> It walks in when the enemy is further off than this many times its range; closer, it fights from about there. </summary>
	public float CloseIn;
	/// <summary> A strafe: about how long (s) before it may turn back, and how fast, as a share of its walk. </summary>
	public float StrafeLeg;
	public float StrafePace;
	/// <summary> About the longest it stands still in a fight (s), for an aimed shot, before it moves again. </summary>
	public float Plant;
	/// <summary> The chance it crouches when it plants. </summary>
	public float CrouchPlant;
	/// <summary> How often it strafes, plants and pushes, against each other. </summary>
	public float StrafeWeight;
	public float PlantWeight;
	public float PushWeight;
	/// <summary> After this many strings of fire from about one place it moves to another. </summary>
	public int RelocateAfter;
	/// <summary> How long (s) it covers the place an enemy went out of sight before going after them. </summary>
	public float Patience;
	/// <summary> How long (s) it holds each spot it reaches while hunting, watching; 0 moves straight on. </summary>
	public float HoldAtSpot;
	/// <summary> The chance its first strafe in a fight goes left: people have a side they prefer to peek. </summary>
	public float LeftBias;

	/// <summary> Rolled: a default (all zero) struct is from before habits existed, or a hotload. </summary>
	public readonly bool IsSet => Range > 0f;

	/// <summary> A new soldier's habits, for the gun they're issued (<paramref name="category"/>, null if unknown). </summary>
	public static BotHabits Roll( WeaponCategory? category )
	{
		var habits = new BotHabits { Style = RollStyle( category ), LeftBias = R( 0.3f, 0.7f ) };
		switch ( habits.Style )
		{
			case BotStyle.Rusher:
				habits.Aggression = R( 0.8f, 0.95f );
				habits.Range = R( 0.45f, 0.65f );
				habits.CloseIn = 1.2f;
				habits.StrafeLeg = R( 0.25f, 0.5f );
				habits.StrafePace = R( 0.85f, 1f );
				habits.Plant = R( 0.15f, 0.35f );
				habits.CrouchPlant = R( 0.08f, 0.2f );
				(habits.StrafeWeight, habits.PlantWeight, habits.PushWeight) = (R( 0.5f, 0.6f ), R( 0.1f, 0.2f ), R( 0.3f, 0.4f ));
				habits.RelocateAfter = 99;
				habits.Patience = R( 0.2f, 0.6f );
				break;
			case BotStyle.Flanker:
				habits.Aggression = R( 0.6f, 0.8f );
				habits.Range = R( 0.8f, 1.1f );
				habits.CloseIn = 1.3f;
				habits.StrafeLeg = R( 0.35f, 0.7f );
				habits.StrafePace = R( 0.8f, 0.95f );
				habits.Plant = R( 0.25f, 0.5f );
				habits.CrouchPlant = R( 0.1f, 0.3f );
				(habits.StrafeWeight, habits.PlantWeight, habits.PushWeight) = (R( 0.4f, 0.5f ), R( 0.15f, 0.25f ), R( 0.1f, 0.2f ));
				habits.RelocateAfter = Game.Random.Int( 2, 3 );
				habits.Patience = R( 0.8f, 1.5f );
				break;
			case BotStyle.Anchor:
				habits.Aggression = R( 0.15f, 0.35f );
				habits.Range = R( 1.2f, 1.6f );
				habits.CloseIn = 2.5f;
				habits.StrafeLeg = R( 0.25f, 0.5f );
				habits.StrafePace = R( 0.6f, 0.8f );
				habits.Plant = R( 0.5f, 1f );
				habits.CrouchPlant = R( 0.55f, 0.85f );
				(habits.StrafeWeight, habits.PlantWeight, habits.PushWeight) = (R( 0.5f, 0.6f ), R( 0.4f, 0.5f ), 0f);
				habits.RelocateAfter = Game.Random.Int( 4, 7 );
				habits.Patience = R( 2.5f, 4.5f );
				habits.HoldAtSpot = R( 2f, 5f );
				break;
			case BotStyle.Marksman:
				habits.Aggression = R( 0.2f, 0.45f );
				habits.Range = R( 1.6f, 2.4f );
				habits.CloseIn = 2.2f;
				habits.StrafeLeg = R( 0.4f, 0.8f );
				habits.StrafePace = R( 0.6f, 0.8f );
				habits.Plant = R( 0.7f, 1.3f );
				habits.CrouchPlant = R( 0.6f, 0.9f );
				(habits.StrafeWeight, habits.PlantWeight, habits.PushWeight) = (R( 0.3f, 0.4f ), R( 0.6f, 0.7f ), 0f);
				habits.RelocateAfter = Game.Random.Int( 2, 3 );
				habits.Patience = R( 2f, 3.5f );
				habits.HoldAtSpot = R( 3f, 6f );
				break;
			default:
				habits.Aggression = R( 0.4f, 0.7f );
				habits.Range = R( 0.9f, 1.25f );
				habits.CloseIn = 1.4f;
				habits.StrafeLeg = R( 0.4f, 0.9f );
				habits.StrafePace = R( 0.7f, 0.9f );
				habits.Plant = R( 0.35f, 0.8f );
				habits.CrouchPlant = R( 0.25f, 0.45f );
				(habits.StrafeWeight, habits.PlantWeight, habits.PushWeight) = (R( 0.45f, 0.55f ), R( 0.25f, 0.35f ), R( 0.15f, 0.25f ));
				habits.RelocateAfter = Game.Random.Int( 3, 5 );
				habits.Patience = R( 1f, 2.5f );
				break;
		}

		return habits;
	}

	private static float R( float min, float max ) => Game.Random.Float( min, max );

	/// <summary>
	/// The style, weighted by the gun: players pick the gun that suits how they play. The shares are rifleman, rusher,
	/// flanker, anchor and marksman.
	/// </summary>
	private static BotStyle RollStyle( WeaponCategory? category )
	{
		var weights = category switch
		{
			WeaponCategory.SMG => new[] { 0.2f, 0.45f, 0.3f, 0.05f, 0f },
			WeaponCategory.LMG => new[] { 0.35f, 0.1f, 0f, 0.45f, 0.1f },
			WeaponCategory.Shotgun => new[] { 0.1f, 0.7f, 0.2f, 0f, 0f },
			WeaponCategory.Sniper or WeaponCategory.Marksman => new[] { 0.1f, 0f, 0.1f, 0.3f, 0.5f },
			_ => new[] { 0.35f, 0.15f, 0.2f, 0.15f, 0.15f },
		};

		var roll = Game.Random.Float( 0f, weights.Sum() );
		for ( var i = 0; i < weights.Length; i++ )
		{
			roll -= weights[i];
			if ( roll <= 0f && weights[i] > 0f )
				return (BotStyle)i;
		}

		return BotStyle.Rifleman;
	}
}

/// <summary>
/// How a bot moves in a fight. The user saw bots "often just stood still rather than moving and shooting": each second
/// or so a bot rolled a strafe or stood still, recruits standing three times in four, and it stood through every reload.
/// Now it always has a move on, and shoots through all of them: a strafe side to side (mostly back the other way, as a
/// player's A-D), a short plant for an aimed shot (often crouched), a push in, a step back, or a move to a new spot after
/// a few strings or a hit. Its <see cref="BotHabits"/> weigh them, so each bot moves in its own way.
/// </summary>
public sealed partial class LightweightCombatBot
{
	private BotHabits _habits;

	/// <summary> This soldier's habits in a fight. Rolled here if nothing set them (a bot placed in a scene, or a hotload). </summary>
	public BotHabits Habits
	{
		get
		{
			if ( !_habits.IsSet )
			{
				_habits = BotHabits.Roll( WeaponResource?.Category );
				Aggression = _habits.Aggression;
			}

			return _habits;
		}
		set => _habits = value;
	}

	/// <summary> What the bot's doing in its fight, for dev_bot_styles. </summary>
	public string CurrentMove => _move.ToString();

	private enum Move { None, Strafe, Plant, Push, BackOff, Relocate, Prone }

	private Move _move;
	private TimeUntil _moveEnds;
	/// <summary> Which way the last strafe went, -1 or 1 (0 before the first). </summary>
	private float _strafeSign;
	/// <summary> The spot the bot fights from: an anchor peeks either side of it, and a search hold shifts about it. </summary>
	private Vector3 _anchor;
	/// <summary> Strings of fire since the bot last moved spot (<see cref="BotHabits.RelocateAfter"/>). </summary>
	private int _stringsHere;
	/// <summary> Hit since the last move was picked: most get off the spot, a rusher goes at them. </summary>
	private bool _hurt;
	/// <summary> Which side a flanker comes round, -1 or 1. </summary>
	private float _flankSign;
	private TimeSince _timeSinceAcquired;
	/// <summary> A hunt's spot reached: an anchor or marksman holds it until this runs out (<see cref="BotHabits.HoldAtSpot"/>). </summary>
	private TimeUntil _huntHold;
	private bool _huntHeld;

	/// <summary> The distance this bot likes to fight at. </summary>
	private float FightRange => PreferredRange * Habits.Range;

	/// <summary>
	/// Seeing someone at a run, a player lets the sprint go almost at once and brings the gun up while they work out who
	/// it is. So does a bot, this long after it notices them: it used to run on at full tilt, gun down, until it had.
	/// </summary>
	private float SprintBreak => MathX.Lerp( 0.35f, 0.18f, Skill );

	/// <summary> A new fight: the next move is picked at once, from here. </summary>
	private void StartFight( bool sameEnemy )
	{
		StandFromProne();
		_move = Move.None;
		_moveEnds = 0f;
		_timeSinceAcquired = 0f;
		_huntHold = 0f;
		if ( sameEnemy )
			return;

		_hurt = false;
		_anchor = WorldPosition;
		_stringsHere = 0;
		_flankSign = Game.Random.Float() < 0.5f ? -1f : 1f;
	}

	/// <summary> In range of the enemy it's fighting: carry on with the move it's on, or pick the next. </summary>
	private void Manoeuvre( Vector3 toTarget, float distance, float wanted )
	{
		if ( ContinueProne( distance ) ) return;

		if ( _anchor.DistanceSquared( WorldPosition ) > 600f * 600f )
			_anchor = WorldPosition;

		var travelling = _move is Move.Push or Move.BackOff or Move.Relocate;
		var arrived = travelling && (!_moveTarget.HasValue || WorldPosition.DistanceSquared( _moveTarget.Value ) < 40f * 40f);
		if ( _moveEnds.Relative > 0f && !arrived && !_hurt )
			return;

		var away = distance > 1f ? -toTarget / distance : -WorldRotation.Forward.WithZ( 0f ).Normal;
		NextMove( away, distance, wanted );
	}

	private void NextMove( Vector3 away, float distance, float wanted )
	{
		StandFromProne();
		var habits = Habits;
		var hurt = _hurt;
		_hurt = false;
		if ( _move is Move.Push or Move.BackOff or Move.Relocate )
			_anchor = WorldPosition;

		// Rushed: back off, shooting (a rusher's where it wants to be).
		if ( distance < wanted * 0.5f && habits.Style != BotStyle.Rusher && Game.Random.Float() < 0.7f )
		{
			BackOff( away );
			return;
		}

		if ( hurt )
		{
			if ( habits.Style == BotStyle.Rusher )
				Push( away, distance, wanted );
			else if ( Game.Random.Float() < 1f - habits.Aggression * 0.6f )
				Relocate( away );
			else
				Strafe( away );
			return;
		}

		// A new magazine going in: off the line, not stood in the open.
		if ( IsReloading )
		{
			if ( habits.Style == BotStyle.Rusher || Game.Random.Float() < 0.4f )
				Strafe( away );
			else if ( Game.Random.Float() < 0.5f )
				BackOff( away );
			else
				Relocate( away );
			return;
		}

		if ( _stringsHere >= habits.RelocateAfter )
		{
			Relocate( away );
			return;
		}

		// A recruit freezes more often than a veteran. Never two plants in a row, and no push when it's close enough.
		var strafe = habits.StrafeWeight;
		var plant = _move is Move.Plant or Move.Prone ? 0f : habits.PlantWeight * MathX.Lerp( 1.4f, 0.8f, Skill );
		var push = distance > wanted * 0.8f ? habits.PushWeight : 0f;
		var roll = Game.Random.Float( 0f, strafe + plant + push );
		if ( roll < plant )
			Plant( distance );
		else if ( roll < plant + push )
			Push( away, distance, wanted );
		else
			Strafe( away );
	}

	/// <summary>
	/// Side to side across their aim at the gun's walk (a share of it), mostly back the other way each time, as a player
	/// strafes, and clear of a teammate beside it. A little forward for a pusher, a little back for a holder. An anchor
	/// swings either side of its spot, peeking one way then the other.
	/// </summary>
	private void Strafe( Vector3 away, float scale = 1f )
	{
		var habits = Habits;
		var side = Vector3.Cross( away, Vector3.Up );
		var mate = NearestTeammateSide( side, Interval * 1.5f );
		if ( mate != 0f )
			_strafeSign = -mate;
		else if ( _strafeSign == 0f )
			_strafeSign = Game.Random.Float() < habits.LeftBias ? -1f : 1f;
		else if ( Game.Random.Float() < 0.7f )
			_strafeSign = -_strafeSign;

		var time = habits.StrafeLeg * Game.Random.Float( 0.7f, 1.4f ) * scale;
		var speed = _walkSpeed * habits.StrafePace;
		var forward = Game.Random.Float( -0.25f, 0.25f ) + (Aggression - 0.5f) * 0.4f;
		var centre = habits.Style == BotStyle.Anchor ? _anchor : WorldPosition;
		var destination = centre + (side * _strafeSign - away * forward) * speed * time;

		IsCrouching = false;
		Step( destination, speed );
		_move = Move.Strafe;
		_moveEnds = MathF.Max( time, destination.WithZ( 0f ).Distance( WorldPosition.WithZ( 0f ) ) / MathF.Max( speed, 1f ) );
	}

	/// <summary>
	/// Stop for an aimed shot or two, only for a moment (<see cref="BotHabits.Plant"/>), or crouched for a steadier one.
	/// A soldier who gets down settles in for a few shots before getting up, and doesn't drop again straight after: every
	/// plant used to roll its own crouch and last 0.15-1.3 s, so bots bobbed down and up every second or two (the user:
	/// "bots crouch spam erratically").
	/// </summary>
	private void Plant( float distance )
	{
		var habits = Habits;
		HoldPosition();
		if ( TryPlantProne( distance ) ) return;
		var hold = habits.Plant * Game.Random.Float( 0.6f, 1.25f );
		IsCrouching = _proneBlend <= 0f && _timeSinceStood > _crouchRest && Game.Random.Float() < habits.CrouchPlant
			&& (distance > 350f || habits.Style != BotStyle.Rifleman);
		if ( IsCrouching )
		{
			// Down for at least this long: the drop itself takes a third of a second.
			hold = MathF.Max( hold, CrouchDownTime + habits.Style switch
			{
				BotStyle.Marksman or BotStyle.Anchor => Game.Random.Float( 1.8f, 3.2f ),
				BotStyle.Rusher => Game.Random.Float( 1f, 1.6f ),
				_ => Game.Random.Float( 1.3f, 2.4f )
			} );
			_crouchRest = Game.Random.Float( 3.5f, 7f );
		}

		_move = Move.Plant;
		_moveEnds = hold;
	}

	/// <summary> Since it last got up from a crouch, and how long it waits after that before crouching again. </summary>
	private TimeSince _timeSinceStood = 999f;
	private float _crouchRest;
	private bool _wasCrouching;

	/// <summary> Walk in on them at an angle, firing, stopping well short of them. </summary>
	private void Push( Vector3 away, float distance, float wanted )
	{
		var direction = Rotation.FromYaw( Game.Random.Float( 15f, 45f ) * (Game.Random.Float() < 0.5f ? -1f : 1f) ) * -away;
		var time = Game.Random.Float( 0.6f, 1.3f );
		var length = MathF.Min( _walkSpeed * time, distance - wanted * 0.35f );
		if ( length < 48f )
		{
			Strafe( away );
			return;
		}

		IsCrouching = false;
		Step( WorldPosition + direction * length, _walkSpeed );
		_move = Move.Push;
		_moveEnds = length / MathF.Max( _walkSpeed, 1f ) + 0.2f;
	}

	/// <summary> Step back from them, a little to one side, still facing them: slower than a walk forward. </summary>
	private void BackOff( Vector3 away )
	{
		var direction = Rotation.FromYaw( Game.Random.Float( -45f, 45f ) ) * away;
		var speed = _walkSpeed * 0.8f;
		var time = Game.Random.Float( 0.6f, 1.2f );
		var point = NavPoint( WorldPosition + direction * speed * time );
		// A wall behind: go sideways instead.
		if ( point.WithZ( 0f ).Distance( WorldPosition.WithZ( 0f ) ) < 48f )
		{
			Strafe( away );
			return;
		}

		IsCrouching = false;
		Step( point, speed );
		_move = Move.BackOff;
		_moveEnds = time + 0.2f;
	}

	/// <summary>
	/// Off to a new spot a few metres to the side, a little back for a holder and a little forward for a pusher, at a walk
	/// with the gun up, so it still shoots on the way. An anchor, marksman or flanker takes one out of the enemy's sight if
	/// it finds one (and comes back out from there); a rifleman one that still sees them.
	/// </summary>
	private void Relocate( Vector3 away )
	{
		var hide = Habits.Style is BotStyle.Anchor or BotStyle.Marksman or BotStyle.Flanker;
		var enemyEye = _target.IsValid() ? _target.WorldPosition + Vector3.Up * 60f : WorldPosition + -away * 500f;
		Vector3? chosen = null;
		for ( var i = 0; i < 4; i++ )
		{
			var sign = i % 2 == 0 ? (_strafeSign != 0f ? -_strafeSign : 1f) : (_strafeSign != 0f ? _strafeSign : -1f);
			var angle = (Game.Random.Float( 45f, 100f ) + Aggression * 35f) * sign;
			var direction = Rotation.FromYaw( angle ) * away;
			var spot = NavPoint( WorldPosition + direction * Game.Random.Float( 220f, 480f ) );
			if ( spot.WithZ( 0f ).Distance( WorldPosition.WithZ( 0f ) ) < 120f )
				continue;

			var seen = ClearLine( enemyEye, spot + Vector3.Up * 60f );
			if ( seen != hide )
			{
				chosen = spot;
				break;
			}

			chosen ??= spot;
		}

		if ( chosen is not { } destination || !GoTo( destination, _walkSpeed ) )
		{
			Strafe( away );
			return;
		}

		IsCrouching = false;
		_move = Move.Relocate;
		_moveEnds = MathF.Min( destination.Distance( WorldPosition ) / MathF.Max( _walkSpeed, 1f ) + 0.5f, 4f );
		_stringsHere = 0;
	}

	/// <summary> Nothing solid between two points: people and window glass don't count. </summary>
	private bool ClearLine( Vector3 from, Vector3 to ) => !Scene.Trace.Ray( from, to )
		.WithoutTags( "trigger", "playerclip", "movement", "player", LightweightBotManager.BotTag, BreakableGlass.Tag )
		.Run().Hit;

	/// <summary> A short move in a fight: a few metres at most, so it doesn't need the route checked first. </summary>
	private void Step( Vector3 position, float speed ) => GoTo( position, speed, checkPath: false );
}
