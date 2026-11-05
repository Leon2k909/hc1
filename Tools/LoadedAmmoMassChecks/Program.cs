using Facepunch;
using System.Text.Json;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
float Scale( float mass, float round, int capacity, long rounds, bool chamber = true )
	=> LoadedAmmoMassRules.RecoilScale( mass, round, capacity, rounds, chamber );

foreach ( var load in new[] { (Mass: 3.4f, Round: 0.0123f, Capacity: 30), (Mass: 6.8f, Round: 0.0163f, Capacity: 75),
	(Mass: 5.0f, Round: 0.0254f, Capacity: 20), (Mass: 0.95f, Round: 0.0115f, Capacity: 17),
	(Mass: 5.5f, Round: 0.04f, Capacity: 25) } )
{
	Check( Scale( load.Mass, load.Round, load.Capacity, load.Capacity ) == 1f, "Full magazine must preserve authored recoil." );
	var previous = 1f;
	for ( var remaining = load.Capacity - 1; remaining >= 0; remaining-- )
	{
		var scale = Scale( load.Mass, load.Round, load.Capacity, remaining );
		Check( scale >= previous && scale <= 2f, "Recoil must increase monotonically as cartridges leave the gun." );
		previous = scale;
	}
	Check( Scale( load.Mass, load.Round, load.Capacity, load.Capacity ) < previous, "Reloading must restore full-load response." );
	Check( Scale( load.Mass, load.Round, load.Capacity, load.Capacity + 1 ) < 1f, "A tactical reload's extra chambered round must add its mass." );
	Check( Scale( load.Mass, load.Round, load.Capacity, load.Capacity + 1, false ) == 1f, "Open-bolt guns must not gain an extra chambered round." );
	Check( Scale( load.Mass, load.Round, load.Capacity, long.MaxValue ) == Scale( load.Mass, load.Round, load.Capacity, load.Capacity + 1 ), "Corrupt ammo must be clamped to physical capacity." );
}
Check( MathF.Abs( Scale( 3.4f, 0.0123f, 30, 1 ) - 3.4f / (3.4f - 29f * 0.0123f) ) < 0.00001f,
	"The last live round must use the pre-discharge mass, not the now-empty gun's mass." );
Check( Scale( 4f, 0.0123f, 60, 1 ) > Scale( 3.4f, 0.0123f, 30, 1 ), "A larger loaded magazine must account for its additional expended rounds." );
foreach ( var invalid in new[] { 0f, -1f, float.NaN, float.PositiveInfinity } )
{
	Check( Scale( invalid, 0.0123f, 30, 1 ) == 1f, "Invalid gun mass must disable the adjustment." );
	Check( Scale( 3.4f, invalid, 30, 1 ) == 1f, "Unknown or invalid cartridge mass must disable the adjustment." );
}
Check( Scale( 3.4f, 0.0123f, 0, 1 ) == 1f && Scale( 3.4f, 0.0123f, int.MaxValue, 1 ) == 1f,
	"Invalid magazine capacity must disable the adjustment." );
Check( LoadedAmmoMassRules.CartridgeKg( null ) == 0f && LoadedAmmoMassRules.CartridgeKg( "weapons/unknown/unknown.equip" ) == 0f,
	"Unlisted cartridges must retain existing behavior." );
Check( LoadedAmmoMassRules.CartridgeKg( "WEAPONS\\M4A1\\M4A1.EQUIP" ) == 0.0123f, "Resource paths must ignore case and slash style." );

// Validate each configured cartridge against an actual firearm resource in this checkout.
var assets = Path.Combine( args[0], "Assets" );
var supported = 0;
foreach ( var path in Directory.EnumerateFiles( Path.Combine( assets, "Weapons" ), "*.equip", SearchOption.AllDirectories ) )
{
	var relative = Path.GetRelativePath( assets, path ).Replace( '\\', '/' );
	if ( LoadedAmmoMassRules.CartridgeKg( relative ) <= 0f ) continue;
	using var resource = JsonDocument.Parse( File.ReadAllText( path ) );
	Check( resource.RootElement.GetProperty( "Name" ).GetString()?.Length > 0, "Mapped cartridge must refer to a real equipment resource." );
	supported++;
}
Check( supported == 23, $"Expected 23 mapped firearm resources; found {supported}." );
Console.WriteLine( $"PASS: {checks} loaded-ammunition mass checks; {supported} firearms mapped." );
