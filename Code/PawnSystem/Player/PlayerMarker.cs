namespace Facepunch;

/// <summary>
/// A component that handles the state of the player's marker on the minimap and the HUD.
/// </summary>
public partial class PlayerMarker : Component, IMarkerObject, IDirectionalMinimapIcon
{
	/// <summary>
	/// The player.
	/// </summary>
	[RequireComponent] PlayerPawn Player { get; set; }

	/// <summary>
	/// An accessor to see if the player is alive or not.
	/// </summary>
	private bool IsAlive => Player.HealthComponent.State == LifeState.Alive;
	private bool IsBot => Player.Client.IsValid() && Player.Client.IsBot;

	/// <summary>
	/// Defines a custom marker panel type to instantiate. Might remove this later.
	/// </summary>
	Type IMarkerObject.MarkerPanelTypeOverride => typeof( UI.PlayerMarkerPanel );

	private Vector3 DistOffset
	{
		get
		{
			if ( !Scene.Camera.IsValid() ) return 0f;

			var dist = Scene.Camera.WorldPosition.DistanceSquared( WorldPosition );
			dist *= 0.00000225f;
			return Vector3.Up * dist;
		}
	}

	/// <summary>
	/// Where is the marker?
	/// </summary>
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 70f + DistOffset;

	bool IMarkerObject.ShouldShow()
	{
		if ( IsBot )
			return false;

		return IsAlive && !Player.IsPossessed && Player.Team != Team.Unassigned;
	}

	/// <summary>
	/// What type of icon are we using on the minimap?
	/// </summary>
	string IMinimapIcon.IconPath
	{
		get
		{
			if ( IsEnemy ) return IsMissing ? "ui/minimaps/enemy_missing.png" : "ui/minimaps/enemy_icon.png";
			if ( !IsAlive ) return "ui/minimaps/icon-map_skull.png";
			return "ui/minimaps/player_icon.png";
		}
	}


	/// <summary>
	/// Is this a directional icon?
	/// </summary>
	bool IDirectionalMinimapIcon.EnableDirectional => IsAlive;

	/// <summary>
	/// What direction should we be facing? Surely this could be a float?
	/// </summary>
	Angles IDirectionalMinimapIcon.Direction => !IsAlive ? Angles.Zero : Player.EyeAngles;

	/// <summary>
	/// Defines a custom css style for this minimap icon.
	/// </summary>
	string ICustomMinimapIcon.CustomStyle
	{
		get
		{
			// The enemy's team colour, not a generic red (TeamExtensions.GetColor).
			if ( IsEnemy ) return $"background-image-tint: {Player.Team.GetColor().Hex}";
			return $"background-image-tint: {Player.Client.PlayerColor.Hex}";
		}
	}

	/// <summary>
	/// The minimap element's position in the world.
	/// </summary>
	Vector3 IMinimapElement.WorldPosition => IsEnemy && IsMissing ? Player.Spottable.LastSeenPosition : WorldPosition;

	/// <summary>
	/// Is this player an enemy of the viewer?
	/// </summary>
	bool IsEnemy => Client.Viewer.Team != Player.Team;

	/// <summary>
	/// How long an unsuppressed shot keeps an enemy lit up on the minimap (seconds).
	/// </summary>
	private const float GunfireRevealTime = 2f;

	/// <summary>
	/// Has this player fired an unsuppressed weapon recently? (CoD-style gunfire radar.)
	/// </summary>
	private bool FiredRecently => Player.IsValid() && Player.TimeSinceUnsuppressedShot < GunfireRevealTime;

	/// <summary>
	/// Is this player revealed by a friendly UAV?
	/// </summary>
	private bool RevealedByUav
	{
		get
		{
			if ( Client.Viewer == null ) return false;
			var uavActive = ScorestreakManager.Instance?.IsUavActiveForTeam( Client.Viewer.Team ) == true
				|| ReconDroneFlight.Reveals( Player.GameObject, Client.Viewer.PlayerPawn );
			if ( !uavActive ) return false;

			var hasGhost = Player.Components.TryGet<PlayerPerks>( out var perks, FindMode.EnabledInSelf ) && perks.HasPerk( "ghost" );
			return !hasGhost;
		}
	}

	/// <summary>
	/// Did we spot this player recently? Live gunfire overrides the faded "last seen" state.
	/// </summary>
	bool IsMissing => Player.Spottable.WasSpotted && !FiredRecently && !RevealedByUav;

	/// <summary>
	/// Should we render this element at all?
	/// </summary>
	/// <param name="viewer"></param>
	/// <returns></returns>
	bool IMinimapElement.IsVisible( Pawn viewer )
	{
		// NOTE: bots are intentionally NOT excluded here — they show on the minimap
		// like real players (teammates always, enemies when spotted or firing unsuppressed).

		if ( Player.HealthComponent.State != LifeState.Alive )
			return false;

		if ( IsAlive )
		{
			// Are we possessing this player?
			if ( Player.IsPossessed )
				return false;

			// seen by enemy team, or revealed by firing an unsuppressed weapon, or UAV
			if ( Player.Spottable.IsSpotted || Player.Spottable.WasSpotted || FiredRecently || RevealedByUav )
				return true;
		}

		if ( Player.Team == Team.Unassigned )
			return false;

		return viewer.Team == Player.Team;
	}
}
