namespace Facepunch;

public partial class Shootable
{
	/// <summary>The real load's muzzle velocity from this gun's barrel, in m/s. 0 shoots dead straight.</summary>
	[Property, Group( "Ballistics" )] public float MuzzleVelocity { get; set; }

	/// <summary>The standard projectile the bullet's <see cref="BallisticCoefficient"/> is published against.</summary>
	[Property, Group( "Ballistics" )] public Ballistics.DragFunction DragFunction { get; set; }

	/// <summary>The bullet's published ballistic coefficient for <see cref="DragFunction"/>, in lb/in².</summary>
	[Property, Group( "Ballistics" )] public float BallisticCoefficient { get; set; }

	/// <summary>How far the sights' line sits above the bore, in inches.</summary>
	[Property, Group( "Ballistics" )] public float SightHeight { get; set; }

	/// <summary>The gun's standard zero, in metres: where the path comes back down through the line of sight.</summary>
	[Property, Group( "Ballistics" )] public float ZeroRange { get; set; }

	/// <summary>The bullet's diameter, in mm. With <see cref="BulletLength"/>, it sets how loud its supersonic crack is and how long it lasts (<see cref="BulletFlyby"/>).</summary>
	[Property, Group( "Ballistics" )] public float BulletDiameter { get; set; }

	/// <summary>The bullet's length, in mm (a buckshot ball's is its diameter).</summary>
	[Property, Group( "Ballistics" )] public float BulletLength { get; set; }

	/// <summary>How far along the real path the last shot's trace starts, in units, for its damage falloff.</summary>
	private float _pathTravelled;

	/// <summary>
	/// In a game mode with <see cref="BulletDrop"/> (Warzone), moves a shot along the line of sight onto the bullet's
	/// real path. It still hits instantly, but it leaves the muzzle (<see cref="SightHeight"/> below the sights), climbs
	/// through the line of sight and falls back through it at <see cref="ZeroRange"/>. The path is followed in straight
	/// segments until one meets something, and the shot is traced from the start of that segment. Gravity only bends the
	/// path across the line of sight by its component across it, so steep shots up or down fall less (the rifleman's rule).
	/// </summary>
	private void ApplyBallistics( ref Vector3 start, ref Vector3 forward, Rotation aim )
	{
		_pathTravelled = 0f;
		if ( MuzzleVelocity <= 0f || BallisticCoefficient <= 0f || ZeroRange <= 0f || !BulletDrop.IsActive ) return;

		var path = Ballistics.Get( DragFunction, MuzzleVelocity, BallisticCoefficient );
		var sightHeight = SightHeight / Ballistics.UnitsPerMeter;
		// The bore's angle above the line of sight, zeroed on level ground, at the optic's tuned zero if it has one.
		var zero = Equipment.IsValid() ? Equipment.GetSightZero( ZeroRange ) : ZeroRange;
		var elevation = (sightHeight + path.DropAt( zero )) / zero;

		var sights = start;
		var line = forward;
		var across = Vector3.Up - line * line.z;
		var cosine = across.Length;
		across = cosine > 0.001f ? across / cosine : aim.Up;

		// The point on the path at a range along the line of sight, in units.
		Vector3 PointAt( float range )
		{
			var metres = range / Ballistics.UnitsPerMeter;
			return sights + line * range
				+ aim.Up * ((elevation * metres - sightHeight) * Ballistics.UnitsPerMeter)
				- across * (cosine * path.DropAt( metres ) * Ballistics.UnitsPerMeter);
		}

		// 25 m segments stay within millimetres of a rifle bullet's arc; past 300 m only pistols are still going.
		var reach = MathF.Min( MaxRange, Ballistics.SolvedRange * Ballistics.UnitsPerMeter );
		var from = PointAt( 0f );
		for ( var range = 0f; ; )
		{
			var next = MathF.Min( range + (range < 300f * Ballistics.UnitsPerMeter ? 25f : 100f) * Ballistics.UnitsPerMeter, reach );
			var to = PointAt( next );
			start = from;
			forward = (to - from).Normal;
			if ( next >= reach || DoTraceBulletOne( from, to, BulletSize ).Hit ) return;

			_pathTravelled += from.Distance( to );
			from = to;
			range = next;
		}
	}
}
