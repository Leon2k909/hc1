
using Facepunch;

partial class BombSite : IMinimapLabel, IMinimapVolume, IMarkerObject
{
	Vector3 IMinimapElement.WorldPosition => WorldPosition;
	bool IMinimapElement.IsVisible( Pawn viewer ) => IsBombSiteMode();
	Color IMinimapVolume.Color => "rgba( #992d32, 0.25 )";
	Vector3 IMinimapVolume.Size => GetComponent<BoxCollider>().Scale;
	Color IMinimapVolume.LineColor => new Color32( 183, 85, 70 );
	string IMinimapLabel.Label => $"{(char)('A' + Index)}";
	Color IMinimapLabel.LabelColor => new Color32( 255, 199, 0 );
	Angles IMinimapVolume.Angles => Angles.Zero;

	// IMarkerObject implementation
	GameObject IMarkerObject.GameObject => GameObject;
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 64f;
	string IMarkerObject.MarkerIcon => "/c4.png"; // Fixed icon path
	int IMarkerObject.IconSize => 28;
	bool IMarkerObject.ShowChevron => true;
	bool IMarkerObject.LookOpacity => false;
	string IMarkerObject.DisplayText => $"{(char)('A' + Index)}";
	string IMarkerObject.MarkerStyles => "background-tint: #ffc700; color: #ffc700; font-weight: bold;";
	bool IMarkerObject.ShouldShow()
	{
		return IsBombSiteMode();
	}

	private static bool IsBombSiteMode()
	{
		var ident = GameMode.Instance?.Ident;
		return string.Equals( ident, "defuse", StringComparison.OrdinalIgnoreCase )
			|| string.Equals( ident, "retakes", StringComparison.OrdinalIgnoreCase );
	}
}
