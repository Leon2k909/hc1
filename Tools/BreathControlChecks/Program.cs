using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
BreathControlRules.Sample Simulate( BreathControlRules.State state, int frames, float delta,
	bool eligible = true, bool held = true, float stamina = 1f )
{
	BreathControlRules.Sample sample = default;
	for ( var i = 0; i < frames; i++ )
	{
		sample = BreathControlRules.Step( state, delta, eligible, held, stamina );
		state = sample.State;
	}
	return sample;
}

foreach ( var hz in new[] { 30, 60, 120, 144 } )
{
	var dt = 1f / hz;
	var steady = Simulate( default, hz, dt );
	Check( steady.Holding && MathF.Abs( steady.State.Spent - 1f ) < 0.001f, $"{hz}Hz: holding must consume reserve in real seconds." );
	Check( steady.SwayScale >= 0.3f && steady.SwayScale < 0.301f, $"{hz}Hz: steady aim must retain residual sway." );
	var exhausted = Simulate( default, hz * 4 + 1, dt );
	Check( !exhausted.Holding && exhausted.State.NeedsRelease, $"{hz}Hz: four seconds must exhaust the hold." );
	var stillHeld = Simulate( exhausted.State, hz * 12, dt );
	Check( !stillHeld.Holding && stillHeld.State.NeedsRelease && stillHeld.State.Spent == 0f,
		$"{hz}Hz: holding the button must never auto-restart after recovery." );
	var released = Simulate( stillHeld.State, 1, dt, held: false );
	Check( !released.State.NeedsRelease, $"{hz}Hz: release after recovery must rearm." );
	Check( Simulate( released.State, 1, dt ).Holding, $"{hz}Hz: a fresh hold must work." );
	var partialRecovery = Simulate( exhausted.State, hz * 2, dt, held: false );
	Check( !Simulate( partialRecovery.State, 1, dt ).Holding, $"{hz}Hz: releasing alone must not bypass exhaustion." );
	var recovered = Simulate( exhausted.State, hz * 8 + 1, dt, held: false );
	Check( recovered.State.Spent < 0.001f && Simulate( recovered.State, 1, dt ).Holding, $"{hz}Hz: eight seconds must refill reserve." );
	var earlyRelease = Simulate( steady.State, hz / 2, dt, held: false );
	Check( earlyRelease.SwayScale > 0.99f && earlyRelease.State.Spent < steady.State.Spent,
		$"{hz}Hz: voluntary release must fade smoothly and start recovery." );
	var cancelled = Simulate( steady.State, 1, dt, eligible: false );
	Check( !cancelled.Holding && cancelled.State.NeedsRelease, $"{hz}Hz: movement/reload/menu must cancel and latch." );
	Check( !Simulate( cancelled.State, hz, dt ).Holding, $"{hz}Hz: becoming eligible again with Run held must not resume." );
}

foreach ( var stamina in new[] { 0f, 0.34f, float.NaN, float.NegativeInfinity } )
	Check( !Simulate( default, 1, 0.02f, stamina: stamina ).Holding, "Exertion or invalid stamina must prevent holding." );
Check( Simulate( default, 1, 0.02f, stamina: 0.35f ).Holding, "The minimum rested threshold must permit holding." );
var active = Simulate( default, 60, 1f / 60f );
Check( !Simulate( active.State, 1, 0.02f, stamina: 0.2f ).Holding, "Exertion during a hold must stop it." );
foreach ( var delta in new[] { float.NaN, float.PositiveInfinity, -1f, 0f } )
{
	var result = Simulate( active.State, 1, delta );
	Check( result.State.Spent == active.State.Spent && result.State.Weight == active.State.Weight,
		"Invalid/zero time must not consume reserve or change the smoothing weight." );
}
var invalid = Simulate( new( float.NaN, float.NaN, false ), 1, 0.02f );
Check( !invalid.Holding && float.IsFinite( invalid.SwayScale ), "Invalid saved state must fail closed without NaN aim." );
Check( Simulate( default, 1, 60f ).State.Spent <= 0.25f, "A long frame must be capped." );
Console.WriteLine( $"PASS: {checks} breath-control checks against production rules." );
