using Facepunch;

var count = 0;
void Check( bool passed, string name )
{
    if ( !passed ) throw new Exception( name );
    count++;
}
void Simulate( LpgCanisterState state, float seconds, float heat = 0f, bool ignition = false )
{
    for ( var t = 0f; t < seconds; t += 0.1f ) state.Step( 0.1f, heat, ignition );
}

var bottle = new LpgCanisterState();
Simulate( bottle, 300f );
Check( bottle.Phase == LpgCanisterPhase.Intact && bottle.Fuel == 1f, "Undamaged bottle retains fuel" );
bottle.Ignite();
Check( bottle.Phase == LpgCanisterPhase.Intact, "An intact, cold cylinder cannot catch a gas jet fire" );
bottle.Puncture();
Check( bottle.Phase == LpgCanisterPhase.Leaking, "A gunshot punctures without automatic ignition" );
Simulate( bottle, 30f );
Check( bottle.Phase == LpgCanisterPhase.Leaking && bottle.Fuel is > 0f and < 1f, "An unlit leak loses fuel without exploding" );
Simulate( bottle, 300f );
Check( bottle.Phase == LpgCanisterPhase.Empty && bottle.Fuel == 0f, "An unlit bottle eventually empties" );
bottle.Ignite();
Simulate( bottle, 100f, 3f, true );
Check( bottle.Phase == LpgCanisterPhase.Empty, "An empty cylinder does not explode in fire" );

bottle.Reset();
bottle.Puncture();
bottle.Ignite();
Simulate( bottle, 5f );
Check( bottle.Phase == LpgCanisterPhase.Burning, "Ignition produces sustained fire before pressure failure" );
Simulate( bottle, 70f );
Check( bottle.Phase == LpgCanisterPhase.Ruptured, "Sustained heating ruptures a cylinder while fuel remains" );
var fuel = bottle.Fuel;
bottle.Puncture();
Simulate( bottle, 100f, 3f, true );
Check( bottle.Phase == LpgCanisterPhase.Ruptured && bottle.Fuel == fuel, "Rupture is terminal and cannot retrigger" );

bottle.Reset();
bottle.Puncture( 12 );
bottle.Ignite();
Simulate( bottle, 30f );
Check( bottle.Phase == LpgCanisterPhase.Empty, "A heavily perforated bottle loses pressure before heat can rupture it" );
bottle.Reset();
Simulate( bottle, 15f, 1f, true );
Check( bottle.Phase == LpgCanisterPhase.Burning && bottle.Holes == 1, "An externally heated cylinder vents and the escaping gas ignites" );
bottle.Reset();
Simulate( bottle, 5f, 1f );
Simulate( bottle, 20f );
Check( bottle.Phase == LpgCanisterPhase.Intact && bottle.Heat == 0f, "Removing heat lets an intact bottle cool" );
bottle.Step( float.NaN, float.PositiveInfinity, true );
Check( bottle.Fuel == 1f && bottle.Heat == 0f, "Invalid timesteps cannot corrupt state" );
bottle.Reset();
Check( bottle.Phase == LpgCanisterPhase.Intact && bottle.Fuel == 1f && bottle.Heat == 0f && bottle.Holes == 0,
    "Between-round cleanup restores the whole bottle" );
Console.WriteLine( $"PASS: {count} LPG canister behaviour checks" );
