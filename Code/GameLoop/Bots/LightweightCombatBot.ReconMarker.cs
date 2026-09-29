namespace Facepunch;

public sealed partial class LightweightCombatBot : ICustomMinimapIcon
{
	bool IMinimapElement.IsVisible( Pawn viewer ) => IsAlive && viewer.IsValid()
		&& ((Team != Team.Unassigned && viewer.Team == Team && !GameUtils.IsFreeForAllMode)
			|| ReconDroneFlight.Reveals( GameObject, viewer ));
	Vector3 IMinimapElement.WorldPosition => WorldPosition;
	string IMinimapIcon.IconPath => Client.Viewer?.Team == Team && !GameUtils.IsFreeForAllMode
		? "ui/minimaps/player_icon.png" : "ui/minimaps/enemy_icon.png";
	string ICustomMinimapIcon.CustomStyle => $"background-image-tint: {Team.GetColor().Hex}";
}
