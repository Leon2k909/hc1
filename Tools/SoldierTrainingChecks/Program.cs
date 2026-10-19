using Facepunch;
using static Facepunch.SoldierTrainingRules;

var scenarios = 0;
void Check( bool condition, string description )
{
    if ( !condition ) throw new Exception( description );
}
void Near( float actual, float expected, float tolerance, string description )
    => Check( float.IsFinite( actual ) && Math.Abs( actual - expected ) <= tolerance,
        $"{description}: expected {expected}, got {actual}" );
void Scenario( string description, Action run )
{
    run();
    scenarios++;
    Console.WriteLine( $"PASS: {description}" );
}

Scenario( "Fresh, capped and corrupt XP inputs", () =>
{
    Check( LevelForXP( 0 ) == 1 && LevelForXP( int.MinValue ) == 1, "Fresh/corrupt low XP starts at level 1" );
    Check( XPForLevel( 2 ) == 100 && XPForLevel( 3 ) == 240 && XPForLevel( 50 ) == 51940, "Training pacing" );
    Check( XPForLevel( int.MinValue ) == 0 && XPForLevel( int.MaxValue ) == 51940, "Level bounds" );
    Check( ClampXP( int.MaxValue ) == 51940 && LevelForXP( int.MaxValue ) == 50, "XP cap" );
    Check( XPToNextLevel( int.MaxValue ) == 0 && LevelProgress( int.MaxValue ) == 1f, "Maximum progress display" );
    Check( AddXP( 100, -50 ) == 100 && AddXP( -50, 25 ) == 25, "Awards cannot remove XP" );
    Check( AddXP( 51939, int.MaxValue ) == 51940 && AddXP( int.MaxValue, int.MaxValue ) == 51940, "No addition overflow" );
    Check( LevelForXP( AddXP( 90, 400 ) ) == 4 && XPIntoLevel( 490 ) == 70, "Awards can cross several levels" );
} );

Scenario( "Every level boundary and continuous capped bonuses", () =>
{
    for ( var level = 2; level <= 50; level++ )
    {
        var threshold = XPForLevel( level );
        Check( LevelForXP( threshold - 1 ) == level - 1 && LevelForXP( threshold ) == level, $"Boundary {level}" );
        Check( XPToNextLevel( threshold - 1 ) == 1 && XPIntoLevel( threshold ) == 0, $"Boundary display {level}" );
        Check( Mastery( threshold ) >= Mastery( threshold - 1 )
            && Mastery( threshold ) - Mastery( threshold - 1 ) < 0.001f, $"Continuous benefit at level {level}" );
    }
    var previous = -1f;
    for ( var xp = 0; xp <= 51940; xp++ )
    {
        var mastery = Mastery( xp );
        Check( mastery >= previous && mastery is >= 0f and <= 1f, $"Monotonic mastery at {xp} XP" );
        previous = mastery;
    }
    Near( SprintCapacityScale( 0 ), 1f, 0.00001f, "Base sprint" );
    Near( SprintCapacityScale( int.MaxValue ), 1.2f, 0.00001f, "Sprint cap" );
    Near( RecoveryScale( int.MaxValue ), 1.15f, 0.00001f, "Recovery cap" );
    Near( RecoilScale( int.MaxValue ), 0.88f, 0.00001f, "Recoil cap" );
    Near( SwayScale( int.MaxValue ), 0.85f, 0.00001f, "Sway cap" );
    Near( AimTimeScale( int.MaxValue ), 0.9f, 0.00001f, "Aim duration cap" );
    Near( ReloadTimeScale( int.MaxValue ), 0.9f, 0.00001f, "Reload duration cap" );
} );

float SprintUntilEmpty( int xp, float step )
{
    var state = new SprintState( 1f, false, 0f );
    var ticks = 0;
    while ( !state.Exhausted && ticks < 10000 )
    {
        state = StepStamina( state, true, step, xp );
        ticks++;
    }
    Check( state.Exhausted && state.Stamina == 0f, "Sprinting must exhaust" );
    return ticks * step;
}

Scenario( "12 second base sprint and 14.4 second trained sprint across tick rates", () =>
{
    foreach ( var step in new[] { 0.01f, 0.02f, 0.05f } )
    {
        Near( SprintUntilEmpty( 0, step ), 12f, step * 1.1f, "Base sprint time" );
        Near( SprintUntilEmpty( 51940, step ), 14.4f, step * 1.1f, "Trained sprint time" );
    }
} );

Scenario( "Recovery delay, partial ticks and exhaustion hysteresis", () =>
{
    var state = new SprintState( 0f, true, 1.25f );
    for ( var i = 0; i < 5; i++ ) state = StepStamina( state, true, 0.25f, 0 );
    Check( state.Stamina == 0f && state.Exhausted, "Holding sprint cannot bypass the recovery delay" );
    for ( var i = 0; i < 5; i++ ) state = StepStamina( state, true, 0.25f, 0 );
    Check( state.Stamina < 0.25f && state.Exhausted, "Stay locked below 25%" );
    state = StepStamina( state, true, 0.25f, 0 );
    Near( state.Stamina, 0.25f, 0.00001f, "Recovery threshold" );
    Check( !state.Exhausted, "Release the lock at 25%" );
    var partial = StepStamina( new( 0.5f, false, 0.1f ), false, 0.25f, 0 );
    Near( partial.Stamina, 0.525f, 0.00001f, "Only the 0.15 s after the delay recovers" );
    Check( partial.RecoveryWait == 0f, "Recovery delay ends cleanly" );
} );

Scenario( "Six second base recovery and faster trained recovery", () =>
{
    float Recover( int xp )
    {
        var state = new SprintState( 0f, true, 1.25f );
        var ticks = 0;
        while ( state.Stamina < 0.99999f && ticks < 10000 )
        {
            state = StepStamina( state, false, 0.01f, xp );
            ticks++;
        }
        Check( !state.Exhausted, "Recovered soldier can sprint" );
        return ticks * 0.01f;
    }
    Near( Recover( 0 ), 7.25f, 0.02f, "Base recovery including delay" );
    Near( Recover( 51940 ), 6.4674f, 0.02f, "Trained recovery including delay" );
} );

Scenario( "Stamina survives skill changes without a refill and sanitizes invalid time", () =>
{
    var state = new SprintState( 0.37f, false, 0.5f );
    var trained = StepStamina( state, false, 0f, 51940 );
    Check( trained.Stamina == state.Stamina && trained.RecoveryWait == state.RecoveryWait, "Skill increases preserve current stamina" );
    var stationary = StepStamina( new( 1f, false, 0f ), false, 0.25f, 0 );
    Check( stationary.Stamina == 1f, "Non-running movement does not drain" );
    var invalid = StepStamina( new( float.NaN, true, float.PositiveInfinity ), false, float.NaN, -999 );
    Check( invalid.Stamina == 1f && !invalid.Exhausted && invalid.RecoveryWait == 0f, "Invalid state stays finite" );
    var stalled = StepStamina( new( 1f, false, 0f ), true, 10f, 0 );
    Near( stalled.Stamina, 1f - 0.25f / 12f, 0.00001f, "A stalled update cannot consume seconds of stamina" );
    Near( StepStamina( state, false, -1f, 0 ).Stamina, state.Stamina, 0.00001f, "Negative time does nothing" );
} );

Scenario( "Real ground distance counts in metres; walls, teleports and stale samples do not", () =>
{
    Near( RunningMetres( 62.5f, 0.25f, 250f, 250f, true ), 1.5875f, 0.00001f, "Engine inches to metres" );
    Near( RunningMetres( 393.7008f, 1f, 394f, 400f, true ), 10f, 0.0001f, "Ten metres earns one endurance XP" );
    Check( RunningMetres( 0f, 0.25f, 250f, 250f, true ) == 0f, "Pushing a wall" );
    Check( RunningMetres( 62.5f, 0.25f, 250f, 250f, false ) == 0f, "Airborne or otherwise ineligible sample" );
    Check( RunningMetres( 2000f, 0.25f, 250f, 250f, true ) == 0f, "Teleport" );
    Check( RunningMetres( 62.5f, 1.01f, 250f, 250f, true ) == 0f, "Stale sample" );
    Check( RunningMetres( 62.5f, 0f, 250f, 250f, true ) == 0f, "Zero time" );
    Check( RunningMetres( 62.5f, 0.25f, 0f, 250f, true ) == 0f, "Carried without running velocity" );
    Check( RunningMetres( 100f, 0.25f, 40f, 400f, true ) == 0f, "Displacement inconsistent with velocity" );
    Check( RunningMetres( float.NaN, 0.25f, 250f, 250f, true ) == 0f, "Non-finite distance" );
    Check( RunningMetres( 62.5f, 0.25f, float.PositiveInfinity, 250f, true ) == 0f, "Non-finite velocity" );
} );

Scenario( "Fresh profiles are level one and repeated reads do not write cookies", () =>
{
    Game.SteamId = 101;
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 0 && SoldierTraining.GetLevel( SoldierSkill.Handling ) == 1, "Fresh account" );
    var writes = Game.Cookies.Writes;
    for ( var i = 0; i < 100; i++ ) SoldierTraining.GetXP( SoldierSkill.Endurance );
    SoldierTraining.FlushIfDue();
    Check( Game.Cookies.Writes == writes, "Reading UI cannot cause saves" );
} );

Scenario( "Newer host snapshots merge, stale snapshots never roll back saved progress", () =>
{
    SoldierTraining.Receive( 150, 250, false );
    var revision = SoldierTraining.Revision;
    SoldierTraining.Receive( 100, 200, false );
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 150 && SoldierTraining.GetXP( SoldierSkill.Handling ) == 250, "Ignore older host snapshot" );
    Check( SoldierTraining.Revision == revision, "Ignored snapshot does not rebuild UI" );
    SoldierTraining.Receive( 180, 240, false );
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 180 && SoldierTraining.GetXP( SoldierSkill.Handling ) == 250, "Merge independently per skill" );
    Check( SoldierTraining.LevelUpRevision == 0, "Importing existing progress is silent" );
    SoldierTraining.Flush();
} );

Scenario( "Progress saves every five seconds, with immediate saves on skill improvement", () =>
{
    var writes = Game.Cookies.Writes;
    SoldierTraining.Receive( 181, 251, true );
    TestClock.Now += 4.99;
    SoldierTraining.FlushIfDue();
    Check( Game.Cookies.Writes == writes, "Do not save every earned point" );
    TestClock.Now += 0.02;
    SoldierTraining.FlushIfDue();
    Check( Game.Cookies.Writes == writes + 2, "Save both skills when due" );
    SoldierTraining.Receive( 240, 251, true );
    Check( Game.Cookies.Writes == writes + 4 && SoldierTraining.LevelUpRevision == 1, "Level improvement is saved immediately" );
    Check( SoldierTraining.LastImprovedSkill == SoldierSkill.Endurance && SoldierTraining.TimeSinceLevelUp < 0.01f, "Notice identifies the improved skill" );
    TestClock.Now += 4.01;
    Check( SoldierTraining.TimeSinceLevelUp > 4f, "The notice timer expires" );
} );

Scenario( "Saved training reloads and stays isolated between accounts", () =>
{
    Game.SteamId = 202;
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 0, "A different account starts fresh" );
    SoldierTraining.Receive( 12, 34, false );
    Game.SteamId = 101;
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 240 && SoldierTraining.GetXP( SoldierSkill.Handling ) == 251, "Reload original account from cookies" );
    Check( Game.Cookies.Get( "hc1.training.v1.202.Endurance", -1 ) == 12
        && Game.Cookies.Get( "hc1.training.v1.202.Handling", -1 ) == 34, "Account switch flushes the pending old profile to its own keys" );
    Game.SteamId = 202;
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 12 && SoldierTraining.GetXP( SoldierSkill.Handling ) == 34, "Second profile persists independently" );
    Check( SoldierTraining.TimeSinceLevelUp > 4f, "Account switch does not replay another account's notice" );
} );

Scenario( "Corrupt saved values and repeated maximum awards stay bounded", () =>
{
    Game.SteamId = 303;
    Game.Cookies.Set( "hc1.training.v1.303.Endurance", -900 );
    Game.Cookies.Set( "hc1.training.v1.303.Handling", int.MaxValue );
    Check( SoldierTraining.GetXP( SoldierSkill.Endurance ) == 0 && SoldierTraining.GetXP( SoldierSkill.Handling ) == 51940, "Clamp loaded values" );
    SoldierTraining.Receive( int.MaxValue, int.MaxValue, false );
    SoldierTraining.Flush();
    var revision = SoldierTraining.Revision;
    var writes = Game.Cookies.Writes;
    SoldierTraining.Receive( int.MaxValue, int.MinValue, true );
    SoldierTraining.Flush();
    Check( SoldierTraining.GetLevel( SoldierSkill.Endurance ) == 50 && SoldierTraining.GetLevel( SoldierSkill.Handling ) == 50, "Max level remains permanent" );
    Check( SoldierTraining.Revision == revision && Game.Cookies.Writes == writes, "No redundant cap notification or save" );
} );

Console.WriteLine( $"PASS: {scenarios} training scenarios using the production rules and profile code." );

// Only the engine's account, clock and cookie boundary are replaced. Rules and save/merge behavior are production code.
namespace Facepunch
{
    internal static class Game
    {
        internal static ulong SteamId { get; set; }
        internal static readonly CookieStore Cookies = new();
    }
    internal sealed class CookieStore
    {
        private readonly Dictionary<string, object> values = new();
        public int Writes { get; private set; }
        public T Get<T>( string key, T fallback ) => values.TryGetValue( key, out var value ) ? (T)value : fallback;
        public void Set<T>( string key, T value ) { values[key] = value; Writes++; }
    }
    internal static class TestClock { internal static double Now = 1000; }
    public readonly struct RealTimeSince
    {
        private readonly double timestamp;
        private RealTimeSince( double value ) => timestamp = value;
        public static implicit operator RealTimeSince( float age ) => new( TestClock.Now - age );
        public static implicit operator float( RealTimeSince value ) => (float)(TestClock.Now - value.timestamp);
    }
}
