using Facepunch;
using System.Text.Json;

var checks = 0;
void Check( bool passed, string message )
{
	checks++;
	if ( !passed ) throw new Exception( message );
}

// A constant air target has a known exponential solution, independent of puff age or display frame rate.
var wind = new Vector3( 15f, -22f, 0f );
foreach ( var fps in new[] { 20, 30, 60, 144, 240 } )
{
	foreach ( var age in new[] { 0f, 0.01f, 3f, 8f, 12.99f } )
	{
		var velocity = Vector3.Zero;
		for ( var step = 0; step < fps * 3; step++ )
			velocity = SmokeMath.Advect( velocity, Vector3.Zero, Vector3.Zero, wind, 0f, age, 0f, 0f, 0f, 1.4f, 1f / fps );
		var expected = wind * (1f - MathF.Exp( -3f * 1.4f ));
		Check( velocity.Distance( expected ) < 0.0003f, $"Air response changed at {fps} FPS / age {age}: {velocity} vs {expected}" );
	}
}

// In calm air warm puffs rise and cool continuously; even maximum turbulence never reverses their vertical travel.
Vector3 Track( int fps, float phase )
{
	var position = Vector3.Zero;
	var velocity = new Vector3( 4f, -3f, 26f );
	var dt = 1f / fps;
	for ( var frame = 0; frame < 13 * fps; frame++ )
	{
		var time = (frame + 1) * dt;
		velocity = SmokeMath.Advect( velocity, position, Vector3.Zero, Vector3.Zero, time, time, phase, 40f, 18f, 1.4f, dt );
		Check( velocity.z >= 0f && float.IsFinite( velocity.Length ), $"Puff reversed or became invalid at {fps} FPS / {time}s" );
		position += velocity * dt;
	}
	return position;
}

var maximumFrameRateDrift = 0f;
for ( var seed = 0; seed < 16; seed++ )
{
	var phase = seed * 4.067f;
	var low = Track( 30, phase );
	var medium = Track( 60, phase );
	var high = Track( 144, phase );
	maximumFrameRateDrift = MathF.Max( maximumFrameRateDrift, MathF.Max( low.Distance( high ), medium.Distance( high ) ) );
	Check( MathF.Abs( low.z - high.z ) < 0.6f, $"Vertical transport depends on frame rate: {low.z} vs {high.z}" );
}
Check( SmokeMath.Advect( wind, Vector3.Zero, Vector3.Zero, Vector3.Zero, 4f, 4f, 1f, 40f, 18f, 1.4f, 0f ) == wind,
	"Paused smoke changed its velocity" );

// Motion parallel to a surface must not cause the previous shrink/reprobe/grow sawtooth.
var floor = new SmokeMath.Surface( Vector3.Zero, Vector3.Up, 32f );
var wall = new SmokeMath.Surface( new Vector3( 100f, 0f, 0f ), -Vector3.Forward, 0f );
for ( var i = -200; i <= 200; i++ )
{
	Check( MathF.Abs( floor.Clearance( new Vector3( i, i * 0.5f, 10f ) ) - 42f ) < 0.001f, "Puff changes size along a flat floor" );
	Check( MathF.Abs( wall.Clearance( new Vector3( 70f, i, i * 0.5f ) ) - 30f ) < 0.001f, "Puff changes size along a flat wall" );
}
Check( wall.Clearance( new Vector3( 90f, 0f, 0f ) ) == 10f, "Moving toward a wall did not reduce clearance" );
Check( wall.Clearance( new Vector3( 50f, 0f, 0f ) ) == 50f, "Moving away from a wall did not increase clearance" );

// Exact visibility at the front, middle and back of a puff, including a camera inside it.
var centre = new Vector3( 100f, 0f, 0f );
var radius = 20f;
var alpha = 0.6f;
float Depth( float distance ) => SmokeMath.OpticalDepth( Vector3.Zero, Vector3.Forward, centre, radius, distance, alpha );
var full = -MathF.Log( 1f - alpha );
Check( Depth( 75f ) == 0f && Depth( 80f ) == 0f, "Smoke covered an object in front" );
Check( MathF.Abs( Depth( 100f ) - full * 0.5f ) < 0.00001f, "Object inside the puff got the wrong amount of smoke" );
Check( MathF.Abs( Depth( 120f ) - full ) < 0.00001f, "Full smoke did not cover an object behind it" );
Check( MathF.Abs( Depth( 120f ) - Depth( 500f ) ) < 0.00001f, "Background depth changed complete puff opacity" );
Check( MathF.Abs( SmokeMath.OpticalDepth( centre, Vector3.Forward, centre, radius, 500f, alpha ) - full * 0.5f ) < 0.00001f,
	"Smoke disappeared when the camera entered the puff" );
Check( SmokeMath.OpticalDepth( Vector3.Zero, -Vector3.Forward, centre, radius, 500f, alpha ) == 0f, "Smoke behind the camera rendered" );
Check( SmokeMath.OpticalDepth( Vector3.Zero, Vector3.Forward, new Vector3( 100f, radius, 0f ), radius, 500f, alpha ) == 0f,
	"The puff's tangent edge did not fade to zero" );
Check( MathF.Exp( -Depth( 500f ) * 5f ) < 0.011f, "Overlapping smoke failed to hide the background" );

// Compare arbitrary clipped chords against independently sampled density along the visible ray.
var random = new Random( 4126 );
for ( var sample = 0; sample < 256; sample++ )
{
	var y = (float)random.NextDouble() * 46f - 23f;
	var surface = 60f + (float)random.NextDouble() * 90f;
	var shifted = centre + new Vector3( 0f, y, 0f );
	var actual = SmokeMath.OpticalDepth( Vector3.Zero, Vector3.Forward, shifted, radius, surface, alpha );
	const int subdivisions = 1200;
	var sum = 0f;
	var ds = surface / subdivisions;
	for ( var i = 0; i < subdivisions; i++ )
	{
		var at = (i + 0.5f) * ds;
		var kernel = MathF.Max( 0f, 1f - ((at - centre.x) * (at - centre.x) + y * y) / (radius * radius) );
		sum += kernel * kernel * ds;
	}
	var expected = full * sum / (radius * (16f / 15f));
	Check( MathF.Abs( actual - expected ) < 0.00005f, $"Clipped volume integral disagrees with density samples: {actual} vs {expected}" );
}

var repo = Path.GetFullPath( Path.Combine( AppContext.BaseDirectory, "../../../../../" ) );
using var prefab = JsonDocument.Parse( File.ReadAllText( Path.Combine( repo, "Assets/weapons/Throwable/M18_Smoke_Grenade/smoke_particles.prefab" ) ) );
var components = prefab.RootElement.GetProperty( "RootObject" ).GetProperty( "Components" ).EnumerateArray().ToArray();
var effect = components.Single( x => x.GetProperty( "__type" ).GetString() == "Sandbox.ParticleEffect" );
var sprite = components.Single( x => x.GetProperty( "__type" ).GetString() == "Sandbox.ParticleSpriteRenderer" );
var emitter = components.Single( x => x.GetProperty( "__type" ).GetString() == "Sandbox.ParticleSphereEmitter" );
Check( effect.GetProperty( "Damping" ).GetSingle() == 0f && effect.GetProperty( "Friction" ).GetSingle() == 0f,
	"Native damping/friction competes with the airflow" );
Check( effect.GetProperty( "Collision" ).GetBoolean() && effect.GetProperty( "Bounce" ).GetSingle() == 0f, "Smoke lost non-bouncing world collisions" );
Check( !sprite.GetProperty( "__enabled" ).GetBoolean(), "The old sprite pass would double-render smoke" );
var lifetime = effect.GetProperty( "Lifetime" ).GetProperty( "Constants" ).GetString().Split( ',' ).Select( float.Parse ).Max();
var rate = emitter.GetProperty( "Rate" ).GetProperty( "CurveA" ).EnumerateArray().Max( x => x.GetProperty( "y" ).GetSingle() );
Check( effect.GetProperty( "MaxParticles" ).GetInt32() >= lifetime * rate, "Particle cap interrupts sustained smoke emission" );

Console.WriteLine( $"{checks:N0} smoke transport, surface and depth checks passed. Maximum 30–144 FPS trajectory difference: {maximumFrameRateDrift:F3} units." );
