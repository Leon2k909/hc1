// Checks PadNavMath (Code/UI/Navigation): where the D-pad goes on a settings page laid out as it is at 1920x1080, and
// how a slider steps. `dotnet run --project Tools/PadNavChecks`.
using Facepunch.UI;
using Sandbox;

var failures = 0;

void Check( bool ok, string what )
{
	Console.WriteLine( (ok ? "ok    " : "FAIL  ") + what );
	if ( !ok ) failures++;
}

var up = new Vector2( 0, -1 );
var down = new Vector2( 0, 1 );
var left = new Vector2( -1, 0 );
var right = new Vector2( 1, 0 );

// The settings page: the back button, eight categories on the left, ten rows on the right, two footer buttons.
var rects = new List<Rect>();
var back = rects.Count; rects.Add( new Rect( 48, 80, 110, 32 ) );
var firstCategory = rects.Count;
for ( var i = 0; i < 8; i++ ) rects.Add( new Rect( 48, 210 + i * 46, 280, 40 ) );
var firstRow = rects.Count;
for ( var i = 0; i < 10; i++ ) rects.Add( new Rect( 352, 190 + i * 64, 1520, 58 ) );
var report = rects.Count; rects.Add( new Rect( 1480, 1000, 190, 44 ) );
var save = rects.Count; rects.Add( new Rect( 1690, 1000, 180, 44 ) );

int Pick( int from, Vector2 direction ) => PadNavMath.Pick( rects[from], rects, direction, from );

Check( Pick( firstRow, down ) == firstRow + 1, "down a row goes to the next row" );
Check( Pick( firstRow + 5, up ) == firstRow + 4, "up a row goes to the row above" );
Check( Pick( firstCategory + 2, down ) == firstCategory + 3, "down the categories stays in them" );
Check( Pick( firstCategory + 2, up ) == firstCategory + 1, "up the categories stays in them" );
Check( Pick( firstCategory, up ) == back, "up from the first category goes to the back button" );
var fromCategory = Pick( firstCategory + 3, right );
Check( fromCategory >= firstRow && fromCategory < firstRow + 10, $"right from a category goes into the rows ({fromCategory - firstRow})" );
Check( Pick( firstRow + 3, left ) >= firstCategory && Pick( firstRow + 3, left ) < firstRow, "left from a row goes to the categories" );
Check( Pick( firstRow + 9, down ) == report || Pick( firstRow + 9, down ) == save, "down from the last row goes to the footer" );
Check( Pick( save, left ) == report, "left from Save goes to Report a Bug" );
Check( Pick( report, right ) == save, "right from Report a Bug goes to Save" );
Check( Pick( save, right ) == -1, "nothing right of Save" );
Check( Pick( back, up ) == -1, "nothing over the back button" );

// The crosshair settings' chips: rows of buttons of different widths.
var chips = new List<Rect>
{
	new( 352, 200, 90, 36 ), new( 450, 200, 70, 36 ), new( 528, 200, 110, 36 ), new( 646, 200, 120, 36 ),
	new( 352, 260, 60, 36 ), new( 420, 260, 60, 36 ),
	new( 352, 320, 60, 36 ), new( 420, 320, 60, 36 ),
};
Check( PadNavMath.Pick( chips[0], chips, right, 0 ) == 1, "right along a row of chips" );
Check( PadNavMath.Pick( chips[3], chips, right, 3 ) == -1, "nothing right of the row's last chip" );
Check( PadNavMath.Pick( chips[1], chips, down, 1 ) == 5, "down from a chip goes to the one under it" );
Check( PadNavMath.Pick( chips[3], chips, down, 3 ) == 5, "down from a wide row's end goes to the next row's nearest chip" );
Check( PadNavMath.Pick( chips[4], chips, up, 4 ) == 0, "up from a chip goes to the one over it" );

// The control nearest one that went away: a gunsmith slot (top of the right column) swapped for that slot's parts.
var muzzleSlot = new Rect( 1480, 260, 400, 72 );
var afterSwap = new List<Rect>
{
	new( 40, 250, 360, 110 ),    // the primary weapon card, on the left at about the same height
	new( 1480, 180, 40, 40 ),    // the parts list's back arrow
	new( 1480, 262, 400, 72 ),   // the first part
	new( 1480, 342, 400, 72 ),   // the second part
};
int Nearest( Rect lost, List<Rect> rects ) => rects.IndexOf( rects.OrderBy( x => PadNavMath.Distance( x, lost ) ).First() );
Check( Nearest( muzzleSlot, afterSwap ) == 2, "a slot swapped for its parts goes to the part in its place, not the left column" );
Check( Nearest( new Rect( 1480, 420, 400, 72 ), afterSwap ) == 3, "a lower slot goes to the nearest part" );
Check( PadNavMath.Distance( muzzleSlot, muzzleSlot ) < PadNavMath.Distance( muzzleSlot, afterSwap[3] ), "overlapping is nearer than touching" );

// Sliders.
void Step( float value, float min, float max, float step, int direction, float held, float expected, string what )
{
	var got = PadNavMath.SliderStep( value, min, max, step, direction, held );
	Check( MathF.Abs( got - expected ) < 0.0001f, $"{what}: {value} -> {got} (expected {expected})" );
}

Step( 1f, 0.1f, 5f, 0.01f, 1, 0f, 1.1f, "mouse sensitivity steps 0.1" );
Step( 1f, 0.1f, 5f, 0.01f, 1, 1.5f, 1.4f, "held, four times as far" );
Step( 4.95f, 0.1f, 5f, 0.01f, 1, 0f, 5f, "stops at the top" );
Step( 0.15f, 0.1f, 5f, 0.01f, -1, 0f, 0.1f, "stops at the bottom" );
Step( 85f, 60f, 120f, 1f, 1, 0f, 86f, "field of view steps 1" );
Step( 85f, 60f, 120f, 1f, -1, 0f, 84f, "field of view steps back 1" );
Step( 50f, 0f, 100f, 5f, 1, 0f, 55f, "volume steps 5" );
Step( 15f, -5f, 50f, 0.1f, 1, 0f, 16.1f, "crosshair distance steps 1.1" );
Step( 1f, 0.1f, 2f, 0.01f, -1, 0f, 0.96f, "ADS sensitivity steps 0.04" );
Step( 1.037f, 0.1f, 5f, 0.01f, 1, 0f, 1.14f, "an off-grid value lands on the grid" );

Console.WriteLine( failures == 0 ? "All checks passed." : $"{failures} check(s) failed." );
return failures == 0 ? 0 : 1;
