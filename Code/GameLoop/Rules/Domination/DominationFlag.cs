using System;
using System.Collections.Generic;
using System.Linq;
using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public sealed class DominationFlag : Component, 
	Component.ITriggerListener, 
	IMarkerObject, 
	ICustomMinimapIcon
{
	[Property, Sync( SyncFlags.FromHost )]
	public string FlagName { get; set; }

	[Property, Sync( SyncFlags.FromHost ), Change( nameof( OnControllingTeamChanged ) )]
	public Team ControllingTeam { get; set; } = Team.Unassigned;

	[Property, Sync( SyncFlags.FromHost )]
	public float CaptureProgress { get; set; } = 0f;

	[Property, Sync( SyncFlags.FromHost )]
	public Team CapturingTeam { get; set; } = Team.Unassigned;

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
			if ( CapturingTeam != Team.Unassigned )
			{
				var capturingName = Tr( CapturingTeam.GetName() );
				return Tr( "Capturing {0} ({1}% by {2})", FlagName, MathF.Round( CaptureProgress * 100 ), capturingName );
			}

			if ( ControllingTeam != Team.Unassigned )
			{
				var teamName = Tr( ControllingTeam.GetName() );
				return $"[{FlagName}] - {teamName}";
			}

			return $"[{FlagName}] - {Tr( "Neutral" )}";
		}
	}

	string IMarkerObject.MarkerStyles
	{
		get
		{
			var color = GetColorForTeam( ControllingTeam );
			if ( CapturingTeam != Team.Unassigned )
			{
				color = GetColorForTeam( CapturingTeam );
			}
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
			var color = GetColorForTeam( ControllingTeam );
			if ( CapturingTeam != Team.Unassigned )
			{
				color = GetColorForTeam( CapturingTeam );
			}
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

		FlagModel.Tint = GetColorForTeam( ControllingTeam );
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
		// Clean up dead/destroyed players
		_occupants.RemoveWhere( x => !x.IsValid() || (x is PlayerPawn p && (p.HealthComponent is null || p.HealthComponent.State != LifeState.Alive)) || (x is LightweightCombatBot b && !b.IsAlive) );

		// Draw capture circle for players to see the radius
		DrawCaptureRadius();

		if ( !Networking.IsHost )
			return;

		var pawns = _occupants.ToList();
		var tCount = pawns.Count( x => GameUtils.GetTeamFromComponent( x ) == Team.Terrorist );
		var ctCount = pawns.Count( x => GameUtils.GetTeamFromComponent( x ) == Team.CounterTerrorist );

		if ( tCount > 0 && ctCount > 0 )
		{
			// Contested - capture progress doesn't change
			return;
		}

		float baseCaptureRate = 0.1f; // 10 seconds to capture solo
		float extraPlayerBonus = 0.05f; // extra speed per player

		if ( tCount > 0 )
		{
			var rate = baseCaptureRate + (tCount - 1) * extraPlayerBonus;
			HandleTeamProgress( Team.Terrorist, rate );
		}
		else if ( ctCount > 0 )
		{
			var rate = baseCaptureRate + (ctCount - 1) * extraPlayerBonus;
			HandleTeamProgress( Team.CounterTerrorist, rate );
		}
		else
		{
			// No one in zone, slowly decay progress
			if ( CapturingTeam != Team.Unassigned )
			{
				CaptureProgress -= Time.Delta * 0.1f;
				if ( CaptureProgress <= 0f )
				{
					CaptureProgress = 0f;
					CapturingTeam = Team.Unassigned;
				}
			}
		}
	}

	private void DrawCaptureRadius()
	{
		var teamColor = ControllingTeam == Team.Unassigned ? Color.White : ControllingTeam.GetColor();
		if ( CapturingTeam != Team.Unassigned )
		{
			// Pulse color if capturing
			float pulse = (MathF.Sin( Time.Now * 6f ) + 1f) * 0.5f;
			teamColor = Color.Lerp( teamColor, CapturingTeam.GetColor(), pulse );
		}

		// Radius of capture zone is 300 units (collider scale 600)
		DrawCircle( WorldPosition, 300f, teamColor );
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

	private void HandleTeamProgress( Team team, float rate )
	{
		if ( ControllingTeam == team )
		{
			// Already controls this flag
			CaptureProgress = 0f;
			CapturingTeam = Team.Unassigned;
			return;
		}

		if ( CapturingTeam != team )
		{
			CaptureProgress = 0f;
			CapturingTeam = team;
		}

		CaptureProgress += Time.Delta * rate;

		if ( CaptureProgress >= 1f )
		{
			CaptureProgress = 0f;
			var oldTeam = ControllingTeam;

			if ( ControllingTeam != Team.Unassigned )
			{
				// If controlled by enemy, neutralize it first!
				ControllingTeam = Team.Unassigned;
				CapturingTeam = Team.Unassigned;
				BroadcastNotification( "{0} Neutralized!", "neutralized", FlagName );
				Sound.Play( "sounds/ui/buttons/ui_press.sound" );
			}
			else
			{
				// Neutral flag captured!
				ControllingTeam = team;
				CapturingTeam = Team.Unassigned;
				BroadcastNotification( "{0} Captured {1}!", "captured", team, FlagName );
				Sound.Play( "sounds/ui/buttons/ui_action.sound" );
			}

			UpdateVisuals();
		}
	}

	// The message goes to the toast in English with its values apart, and the toast puts it in the player's language
	// (a team shows as its translated name).
	private void BroadcastNotification( string message, string type, params object[] args )
	{
		Facepunch.UI.Toast.Instance?.Show( message, Facepunch.UI.ToastType.Generic, 5f, args );
	}
}
