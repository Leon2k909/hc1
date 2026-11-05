global using System.Numerics;
using Facepunch;

var checks = 0;
void Check( bool valid, string message )
{
	if ( !valid ) throw new Exception( message );
	checks++;
}
var eye = new Vector3( 0, 0, 64 );
var forward = Vector3.UnitX;
var gun = new Shootable { SightHeight = 2.6f, MaxRange = 10000f };
var up = new Rotation( Vector3.UnitZ );

// A ledge below the sight line must catch a round while preserving the firearm's direction.
gun.Hits = [new( true, false )];
Check( gun.FireOrigin( eye, forward, up ) == eye - Vector3.UnitZ * 2.6f, "Close cover must move the shot to the bore." );
Check( gun.TraceStart.Z == 61.4f && gun.TraceEnd.X == 48f, "Probe must follow the bore for four feet." );
Check( gun.TraceEnd.Z == gun.TraceStart.Z, "Clearance must not tilt the shot." );

gun.Hits = [];
Check( gun.FireOrigin( eye, forward, up ) == eye, "Clear shots must retain existing sight alignment." );
gun.Hits = [new( true, true )];
Check( gun.FireOrigin( eye, forward, up ) == eye, "Bodies must not displace the shot as if they were solid cover." );
gun.Hits = [new( true, true ), new( true, false )];
Check( gun.FireOrigin( eye, forward, up ) != eye, "A body before a ledge must not hide the cover." );
gun.Hits = [new( false, false )];
Check( gun.FireOrigin( eye, forward, up ) == eye, "A trace miss must not count as cover." );

gun.Hits = [new( true, false )];
gun.MaxRange = 12f;
gun.FireOrigin( eye, forward, up );
Check( gun.TraceEnd.X == 12f, "Probe must not extend beyond weapon range." );
// Rotated/steep aiming must use the sight's up axis, rather than world vertical.
Check( gun.FireOrigin( eye, Vector3.UnitZ, new( Vector3.UnitY ) ) == eye - Vector3.UnitY * 2.6f,
	"Bore offset must rotate with the sight." );

BulletDrop.IsActive = true;
var calls = gun.TraceCalls;
Check( gun.FireOrigin( eye, forward, up ) == eye && gun.TraceCalls == calls, "Ballistics must not receive a second bore offset." );
BulletDrop.IsActive = false;
foreach ( var height in new[] { 0f, -2f, float.NaN, float.PositiveInfinity } )
{
	gun.SightHeight = height;
	Check( gun.FireOrigin( eye, forward, up ) == eye && gun.TraceCalls == calls, "Invalid/unconfigured height must skip the probe." );
}
gun.SightHeight = 2.6f;
foreach ( var range in new[] { 0f, -1f, float.NaN, float.PositiveInfinity } )
{
	gun.MaxRange = range;
	Check( gun.FireOrigin( eye, forward, up ) == eye && gun.TraceCalls == calls, "Invalid range must skip the probe." );
}
Console.WriteLine( $"PASS: {checks} close-cover clearance checks against production code." );

// Engine seams only; the clearance method above is linked directly from production.
namespace Facepunch
{
	public record struct Rotation( Vector3 Up );
	public record struct TraceHit( bool Hit, bool Body );
	public static class BulletDrop { public static bool IsActive; }
	public partial class Shootable
	{
		public float SightHeight, MaxRange;
		public TraceHit[] Hits = [];
		public Vector3 TraceStart, TraceEnd;
		public int TraceCalls;
		public Vector3 FireOrigin( Vector3 start, Vector3 forward, Rotation aim )
		{
			ApplyCloseCoverClearance( ref start, forward, aim );
			return start;
		}
		private Shootable BulletTrace( Vector3 start, Vector3 end )
		{
			TraceStart = start;
			TraceEnd = end;
			TraceCalls++;
			return this;
		}
		public TraceHit[] RunAll() => Hits;
		private static bool IsBody( TraceHit hit ) => hit.Body;
	}
}
