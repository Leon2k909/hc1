using Sandbox.UI;
using Sandbox.UI.Construct;

namespace Tec;

public class TextPanel : Panel
{
	public string Text { get; private set; }
	public TextPanel(string text)
	{
		StyleSheet.Load( "/Tec/UI/TextPanel.cs.scss" );
		Text = text;
		Add.Label( text, "text" );
	}
}
