using Sandbox.UI;
using SWB.Base.UI;

namespace SWB.Base;

public partial class Weapon
{
	public ScreenPanel ScreenPanel { get; set; }
	public PanelComponent RootPanel { get; set; }

	private CustomizationMenu customizationMenu;

	public virtual void CreateUI()
	{
		// Nuclear option: Weapon HUD completely disabled
	}

	public virtual void DestroyUI()
	{
		RootPanel?.Destroy();
	}

	void BroadcastUIEvent( string name, object value )
	{
		if ( RootPanel?.Panel?.Children is null ) return;

		foreach ( var panel in RootPanel.Panel.Children )
		{
			panel.CreateEvent( name, value );
		}
	}

	void OpenCustomizationMenu()
	{
		customizationMenu = new CustomizationMenu( this );
		RootPanel.Panel.AddChild( customizationMenu );
	}

	void CloseCustomizationMenu()
	{
		customizationMenu?.Delete( true );
	}

	/// <summary>Override to use a custom crosshair</summary>
	public virtual Panel CreateCrosshair( Panel parent )
	{
		return parent.AddChild( new Crosshair( this ) );
	}
}
