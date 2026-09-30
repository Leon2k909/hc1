using System;
using System.Collections.Generic;
using System.Linq;
using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public sealed class HardpointZone : Component, 
	Component.ITriggerListener, 
	IMarkerObject, 
	ICustomMinimapIcon
{
	[Property, Sync( SyncFlags.FromHost )]
	public string ZoneName { get; set; } = "Hot Zone";

	[Property, Sync( SyncFlags.FromHost ), Change( nameof( OnControllingTeamChanged ) )]
	public Team ControllingTeam { get; set; } = Team.Unassigned;

	[Property, Sync( SyncFlags.FromHost )]
	public bool IsContested { get; set; } = false;

	[Property] public ModelRenderer FlagModel { get; set; }

	private readonly HashSet<Component> _occupants = new();

	// IMarkerObject implementation
	GameObject IMarkerObject.GameObject => GameObject;
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 100f;
	string IMarkerObject.MarkerIcon => "/ui/minimaps/cashgrab/cashpoint.png";
	int IMarkerObject.IconSize => 28;
	bool IMarkerObject.ShowChevron => true;
	bool IMarkerObject.LookOpacity => false;

	string IMarkerObject.DisplayText
	{
		get
		{
			if ( IsContested )
			{
				return $"{Tr( "Hot Zone" )} - {Tr( "CONTESTED" )}";
			}

			if ( ControllingTeam != Team.Unassigned )
			{
				var teamName = Tr( ControllingTeam.GetName() );
				return $"{Tr( "Hot Zone" )} - {teamName}";
			}

			return $"{Tr( "Hot Zone" )} - {Tr( "Neutral" )}";
		}
	}

	string IMarkerObject.MarkerStyles
	{
		get
		{
			if ( IsContested )
			{
				return "background-tint: #ffaa00; color: #ffaa00; font-weight: bold;";
			}

			var color = GetColorForTeam( ControllingTeam );
			return $"background-tint: {color.Hex}; color: {color.Hex}; font-weight: bold;";
		}
	}

	bool IMarkerObject.ShouldShow() => true;

	// ICustomMinimapIcon implementation
	string IMinimapIcon.IconPath => "/ui/minimaps/cashgrab/cashpoint.png";
	Vector3 IMinimapElement.WorldPosition => WorldPosition;
	bool IMinimapElement.IsVisible( Pawn viewer ) => true;

	string ICustomMinimapIcon.CustomStyle
	{
		get
		{
			if ( IsContested )
			{
				return "background-tint: #ffaa00;";
			}

			var color = GetColorForTeam( ControllingTeam );
			return $"background-tint: {color.Hex};";
		}
	}

	private Color GetColorForTeam( Team team )
	{
		return team switch
		{
			Team.Terrorist => team.GetColor(),
			Team.CounterTerrorist => team.GetColor(),
			_ => Color.White
		};
	}

	protected override void OnStart()
	{
		if ( !FlagModel.IsValid() )
		{
			FlagModel = Components.Get<ModelRenderer>( FindMode.EverythingInSelfAndDescendants );
		}
		UpdateVisuals();
	}

	private void OnControllingTeamChanged( Team before, Team after )
	{
		UpdateVisuals();
	}

	public void UpdateVisuals()
	{
		if ( !FlagModel.IsValid() )
			return;

		if ( IsContested )
		{
			FlagModel.Tint = Color.Orange;
		}
		else
		{
			FlagModel.Tint = GetColorForTeam( ControllingTeam );
		}
	}

	public void ClearPlayers()
	{
		_occupants.Clear();
	}

	void ITriggerListener.OnTriggerEnter( Collider other )
	{
		var player = other.GameObject.Root.GetComponentInChildren<PlayerPawn>();
		if ( player.IsValid() )
		{
			_occupants.Add( player );
			return;
		}

		var bot = other.GameObject.Root.GetComponentInChildren<LightweightCombatBot>();
		if ( bot.IsValid() )
		{
			_occupants.Add( bot );
		}
	}

	void ITriggerListener.OnTriggerExit( Collider other )
	{
		var player = other.GameObject.Root.GetComponentInChildren<PlayerPawn>();
		if ( player.IsValid() )
		{
			_occupants.Remove( player );
			return;
		}

		var bot = other.GameObject.Root.GetComponentInChildren<LightweightCombatBot>();
		if ( bot.IsValid() )
		{
			_occupants.Remove( bot );
		}
	}

	protected override void OnUpdate()
	{
		// Clean up dead/destroyed players, or players that are too far (teleportation cleanup safeguard)
		_occupants.RemoveWhere( x => !x.IsValid() || (x is PlayerPawn p && (p.HealthComponent is null || p.HealthComponent.State != LifeState.Alive)) || (x is LightweightCombatBot b && !b.IsAlive) || x.WorldPosition.Distance( WorldPosition ) > 350f );

		// Draw capture circle for players to see the radius
		DrawCaptureRadius();

		if ( !Networking.IsHost )
			return;

		var pawns = _occupants.ToList();
		var tCount = pawns.Count( x => GameUtils.GetTeamFromComponent( x ) == Team.Terrorist );
		var ctCount = pawns.Count( x => GameUtils.GetTeamFromComponent( x ) == Team.CounterTerrorist );

		var wasContested = IsContested;
		var oldTeam = ControllingTeam;

		if ( tCount > 0 && ctCount > 0 )
		{
			IsContested = true;
		}
		else if ( tCount > 0 )
		{
			IsContested = false;
			if ( ControllingTeam != Team.Terrorist )
			{
				ControllingTeam = Team.Terrorist;
				BroadcastNotification( "Zone secured by {0}!", "captured", Team.Terrorist );
				Sound.Play( "sounds/ui/menu/ui_nav_tab.sound" );
			}
		}
		else if ( ctCount > 0 )
		{
			IsContested = false;
			if ( ControllingTeam != Team.CounterTerrorist )
			{
				ControllingTeam = Team.CounterTerrorist;
				BroadcastNotification( "Zone secured by {0}!", "captured", Team.CounterTerrorist );
				Sound.Play( "sounds/ui/menu/ui_nav_tab.sound" );
			}
		}
		else
		{
			IsContested = false;
		}

		if ( wasContested != IsContested || oldTeam != ControllingTeam )
		{
			UpdateVisuals();
		}
	}

	private void DrawCaptureRadius()
	{
		Color zoneColor;
		if ( IsContested )
		{
			float pulse = (MathF.Sin( Time.Now * 8f ) + 1f) * 0.5f;
			zoneColor = Color.Lerp( Color.Orange, Color.Yellow, pulse );
		}
		else
		{
			zoneColor = ControllingTeam == Team.Unassigned ? Color.White : ControllingTeam.GetColor();
		}

		DrawCircle( WorldPosition, 300f, zoneColor );
	}

	private void DrawCircle( Vector3 center, float radius, Color color )
	{
		int segments = 36;
		Vector3 lastPoint = Vector3.Zero;

		for ( int i = 0; i <= segments; i++ )
		{
			float angle = (i / (float)segments) * MathF.PI * 2f;
			Vector3 offset = new Vector3( MathF.Cos( angle ) * radius, MathF.Sin( angle ) * radius, 5f );
			Vector3 point = center + offset;

			// Trace to ground to conform to terrain
			var tr = Scene.Trace.Ray( point + Vector3.Up * 50f, point + Vector3.Down * 100f )
				.IgnoreGameObjectHierarchy( GameObject )
				.WithoutTags( "trigger", "playerclip", "movement" )
				.Run();

			if ( tr.Hit )
			{
				point = tr.HitPosition + Vector3.Up * 2f;
			}

			if ( i > 0 )
			{
				DebugOverlay.Line( new Line( lastPoint, point ), color, 0f );
			}

			lastPoint = point;
		}
	}

	// The message goes to the toast in English with its values apart, and the toast puts it in the player's language
	// (a team shows as its translated name).
	private void BroadcastNotification( string message, string type, params object[] args )
	{
		Facepunch.UI.Toast.Instance?.Show( message, Facepunch.UI.ToastType.Generic, 5f, args );
	}
}
