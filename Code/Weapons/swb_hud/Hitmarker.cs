using Sandbox.UI;

namespace SWB.HUD;

/*
 * Base your custom hitmarker on HitmarkerPanel and simply add to the weapon
 */

public class Hitmarker : Panel
{
	private Marker activeMarker;

	public Hitmarker()
	{
		StyleSheet.Load( "/swb_hud/Hitmarker.cs.scss" );
		Style.PointerEvents = PointerEvents.None;
	}

	public void Create( bool isKill )
	{
		activeMarker?.Delete( true );
		activeMarker = new Marker( this, isKill );
	}

	public class Marker : Panel
	{
		public Marker( Panel parent, bool isKill )
		{
			Parent = parent;
			Style.PointerEvents = PointerEvents.None;

			var leftTopBar = Add.Panel( "leftTopBar" );
			leftTopBar.Style.PointerEvents = PointerEvents.None;

			var lefBottomBar = Add.Panel( "leftBottomBar" );
			lefBottomBar.Style.PointerEvents = PointerEvents.None;

			var rightTopBar = Add.Panel( "rightTopBar" );
			rightTopBar.Style.PointerEvents = PointerEvents.None;

			var rightBottomBar = Add.Panel( "rightBottomBar" );
			rightBottomBar.Style.PointerEvents = PointerEvents.None;

			string sharedStyling = isKill ? "sharedBarStylingKill" : "sharedBarStyling";
			leftTopBar.AddClass( sharedStyling );
			lefBottomBar.AddClass( sharedStyling );
			rightTopBar.AddClass( sharedStyling );
			rightBottomBar.AddClass( sharedStyling );

			Lifetime();
		}

		async void Lifetime()
		{
			await GameTask.Delay( 100 );
			AddClass( "fadeOut" );
			await GameTask.Delay( 300 );
			Delete();
		}
	}
}
