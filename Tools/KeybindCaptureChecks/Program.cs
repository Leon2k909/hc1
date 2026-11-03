using Facepunch.UI;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}

foreach ( var modifier in new[] { "ctrl", "control", "leftcontrol", "rightcontrol", "shift", "leftshift", "rightshift", "alt", "leftalt", "rightalt" } )
{
	var capture = new KeybindCapture();
	Check( !capture.ShouldCapture( modifier, true ), "A modifier press must wait for a possible main key." );
	Check( !capture.ShouldCapture( modifier, true ), "Modifier auto-repeat must not finish capture." );
	Check( capture.ShouldCapture( modifier, false ), "A modifier pressed alone must be bindable on release." );
	Check( !capture.ShouldCapture( modifier, false ), "A repeated release must not produce another binding." );
}

foreach ( var mainKey in new[] { "r", "space", "mouseleft", "mouseright", "mousemiddle" } )
{
	var capture = new KeybindCapture();
	Check( !capture.ShouldCapture( "leftcontrol", true ), "Ctrl must not terminate a chord before its main key." );
	Check( capture.ShouldCapture( mainKey, true ), "The chord's keyboard or mouse main key must finish capture." );
	Check( !capture.ShouldCapture( "leftcontrol", false ), "Modifier release after a completed chord must be ignored." );
}

var combined = new KeybindCapture();
Check( !combined.ShouldCapture( "ctrl", true ) && !combined.ShouldCapture( "shift", true )
	&& combined.ShouldCapture( "r", true ), "Multiple modifiers must leave capture open until the main key." );

var standalone = new KeybindCapture();
Check( standalone.ShouldCapture( "e", true ) && !standalone.ShouldCapture( "e", false ), "Ordinary single-key binds must keep working on key-down." );
var reset = new KeybindCapture();
reset.ShouldCapture( "alt", true );
reset.Reset();
Check( !reset.ShouldCapture( "alt", false ), "Cancelling or switching the binding row must discard a pending modifier." );
var mismatched = new KeybindCapture();
mismatched.ShouldCapture( "ctrl", true );
Check( !mismatched.ShouldCapture( "shift", false ) && mismatched.ShouldCapture( "ctrl", false ),
	"An unrelated modifier release must not complete the pending modifier's binding." );
var aliases = new KeybindCapture();
Check( !aliases.ShouldCapture( "  LEFTCONTROL ", true ) && aliases.ShouldCapture( "ctrl", false ),
	"Modifier aliases and casing must resolve consistently." );
Check( !new KeybindCapture().ShouldCapture( null, true ) && !new KeybindCapture().ShouldCapture( " ", true ),
	"Empty button events must not end capture." );

Console.WriteLine( $"PASS: {checks} modifier and chord capture checks against production KeybindCapture." );
