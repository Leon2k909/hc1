using Facepunch;
using Sandbox.Events;

namespace TerrorTown;

/// <summary>
/// Shared logic for the TTT gamemode's map movers (<see cref="FuncDoorRotating"/>, <see cref="FuncMoveLinear"/>).
/// Maps built for TTT (thieves.innocent_hotel, thieves.aesthetic) serialize their doors as these types, so the
/// type and [Property] names must match TTT's or the doors load as MissingComponents and can't be used.
/// </summary>
/// <remarks>
/// Map objects aren't network objects (NetworkMode.Snapshot), so [Sync] and instance RPCs don't reach clients.
/// Moves are sent through a static RPC keyed by the GameObject id and every client animates locally.
/// </remarks>
public abstract class MapMover : Component, IUse,
	IGameEventHandler<BetweenRoundCleanupEvent>
{
	/// <summary>
	/// Tag on movers players (and NPCs) can open. They're left out of the navmesh so NPCs path through the doorway
	/// and open the door on the way, see <see cref="FindDoorAhead"/>.
	/// </summary>
	public const string DoorTag = "door";

	/// <summary>
	/// How far open a door has to be for an NPC to walk through it.
	/// </summary>
	public const float OpenEnough = 0.65f;

	/// <summary>
	/// Can players use this directly? Traitor-room doors are false, they were opened by TTT's role buttons.
	/// </summary>
	[Property] public bool AllowDirectUse { get; set; } = true;

	[Property] public bool StartsOpen { get; set; }
	[Property] public bool StartsLocked { get; set; }

	/// <summary>
	/// Close again <see cref="ResetTime"/> seconds after fully opening.
	/// </summary>
	[Property] public bool AutoReset { get; set; }
	[Property] public float ResetTime { get; set; } = 1f;

	[Property] public float OpenDuration { get; set; } = 1f;
	[Property] public float CloseDuration { get; set; } = 1f;

	/// <summary>
	/// X is the time between 0-1, Y is how far towards the target the mover is from 0-1.
	/// </summary>
	[Property] public Curve OpenMovementCurve { get; set; } = new Curve( new Curve.Frame( 0f, 0f ), new Curve.Frame( 1f, 1f ) );
	[Property] public Curve CloseMovementCurve { get; set; } = new Curve( new Curve.Frame( 0f, 0f ), new Curve.Frame( 1f, 1f ) );

	/// <summary>
	/// The other half of a double door, moved along with this one.
	/// </summary>
	[Property] public GameObject PartnerObject { get; set; }
	[Property] public string PartnerName { get; set; }

	[Property, Group( "Sound" )] public SoundEvent OpenSound { get; set; }
	[Property, Group( "Sound" )] public SoundEvent OpenFinishedSound { get; set; }
	[Property, Group( "Sound" )] public SoundEvent CloseSound { get; set; }
	[Property, Group( "Sound" )] public SoundEvent CloseFinishedSound { get; set; }

	public enum MoveState
	{
		Closed,
		Opening,
		Open,
		Closing
	}

	public MoveState MovementState { get; private set; } = MoveState.Closed;
	public bool IsLocked { get; set; }

	/// <summary>
	/// How far open this is, 0 closed to 1 open.
	/// </summary>
	public float OpenAmount { get; private set; }

	protected Transform StartTransform { get; private set; }

	/// <summary>
	/// Which way the current (or last) open went, see <see cref="ShouldReverse"/>.
	/// </summary>
	protected bool Reversed { get; private set; }

	TimeSince _sinceMoveStarted;
	TimeSince _sinceOpened;
	bool _navMeshUpdated;

	/// <summary>
	/// The local transform when this is <paramref name="amount"/> open (0 closed, 1 open).
	/// </summary>
	protected abstract Transform GetTransform( float amount, bool reverse );

	/// <summary>
	/// Should this open the other way, given who's opening it?
	/// </summary>
	protected virtual bool ShouldReverse( Vector3 activatorPosition ) => false;

	protected override void OnStart()
	{
		StartTransform = LocalTransform;
		ResetToStart();

		if ( AllowDirectUse && !StartsLocked )
		{
			Tags.Add( DoorTag );
			Scene.NavMesh.ExcludedBodies.Add( DoorTag );
		}
	}

	void ResetToStart()
	{
		IsLocked = StartsLocked;
		Reversed = false;
		MovementState = StartsOpen ? MoveState.Open : MoveState.Closed;
		SetOpenAmount( StartsOpen ? 1f : 0f );
		_sinceOpened = 0f;
	}

	void SetOpenAmount( float amount )
	{
		OpenAmount = amount;
		LocalTransform = GetTransform( amount, Reversed );
	}

	/// <summary>
	/// The navmesh can finish building before the door is tagged, with the closed door walling off the doorway.
	/// Rebuild the tiles around it once it's done.
	/// </summary>
	void UpdateNavMesh()
	{
		if ( _navMeshUpdated || !Tags.Has( DoorTag ) )
			return;

		var navMesh = Scene.NavMesh;
		if ( !navMesh.IsEnabled || navMesh.IsGenerating )
			return;

		_navMeshUpdated = true;
		var bounds = GetComponent<ModelRenderer>()?.Bounds ?? BBox.FromPositionAndSize( WorldPosition, 64f );
		navMesh.RequestTilesGeneration( bounds.Grow( 32f ) );
	}

	void IGameEventHandler<BetweenRoundCleanupEvent>.OnGameEvent( BetweenRoundCleanupEvent eventArgs )
	{
		ResetToStart();
	}

	GrabAction IUse.GetGrabAction()
	{
		return MovementState == MoveState.Open ? GrabAction.SweepRight : GrabAction.SweepLeft;
	}

	public UseResult CanUse( PlayerPawn player )
	{
		if ( !AllowDirectUse ) return false;
		if ( IsLocked ) return "Locked";

		// Don't use movers that are already moving
		return MovementState is MoveState.Open or MoveState.Closed;
	}

	public void OnUse( PlayerPawn player )
	{
		Toggle( player.IsValid() ? player.WorldPosition : null );
	}

	/// <summary>
	/// Open if closed, close if open, along with the partner door. Host only.
	/// </summary>
	public void Toggle( Vector3? activatorPosition = null )
	{
		if ( MovementState is not (MoveState.Open or MoveState.Closed) )
			return;

		var open = MovementState == MoveState.Closed;
		StartMove( open, activatorPosition );

		var partner = FindPartner();
		if ( partner.IsValid() && partner.MovementState == MovementStateBefore( open ) )
			partner.StartMove( open, activatorPosition );
	}

	static MoveState MovementStateBefore( bool open ) => open ? MoveState.Closed : MoveState.Open;

	/// <summary>
	/// The door an NPC at <paramref name="position"/> moving at <paramref name="velocity"/> is about to walk into,
	/// if it isn't open enough to get through. Doors aren't in the navmesh, so NPCs walk through them otherwise.
	/// </summary>
	public static MapMover FindDoorAhead( Scene scene, Vector3 position, Vector3 velocity )
	{
		velocity = velocity.WithZ( 0f );
		if ( velocity.Length < 30f )
			return null;

		var heading = velocity.Normal;
		// This frame's doors (BotSystem): every bot and zombie went through every mover in the scene ten times a second.
		var doors = scene.GetSystem<BotSystem>()?.Doors ?? scene.GetAllComponents<MapMover>().ToList();
		foreach ( var door in doors )
		{
			if ( !door.IsValid() || door.OpenAmount >= OpenEnough || !door.Tags.Has( DoorTag ) )
				continue;

			// The door's middle stays the same distance from its origin as it swings or slides, so one further than that
			// past the reach below can't be it: skip it before asking the engine for its bounds.
			if ( door._centreReach >= 0f )
			{
				var origin = door.WorldPosition;
				var slack = door._centreReach + 1f;
				if ( MathF.Abs( origin.z - position.z - 56f ) > 48f + slack
					|| (origin - position).WithZ( 0f ).LengthSquared > (80f + slack) * (80f + slack) )
					continue;
			}

			var center = door.BoundsCentre();
			if ( MathF.Abs( center.z - position.z - 56f ) > 48f )
				continue;

			var toDoor = (center - position).WithZ( 0f );
			if ( toDoor.Length < 80f && Vector3.Dot( heading, toDoor.Normal ) > 0.6f )
				return door;
		}

		return null;
	}

	private ModelRenderer _boundsRenderer;
	/// <summary> How far the middle of this door's bounds is from its origin, once measured (-1 until then). </summary>
	private float _centreReach = -1f;

	/// <summary> The middle of this door's model as it is now, or its origin with no model (<see cref="FindDoorAhead"/>). </summary>
	private Vector3 BoundsCentre()
	{
		if ( !_boundsRenderer.IsValid() )
			_boundsRenderer = GetComponent<ModelRenderer>();
		if ( !_boundsRenderer.IsValid() )
			return WorldPosition;

		var centre = _boundsRenderer.Bounds.Center;
		_centreReach = MathF.Max( _centreReach, centre.Distance( WorldPosition ) );
		return centre;
	}

	/// <summary>
	/// An NPC at <paramref name="position"/> is walking into this door: open it if it's shut (again, if someone
	/// closed it on them). False if it can't be opened, so there's no point waiting. Host only.
	/// </summary>
	public bool OpenForNpc( Vector3 position )
	{
		if ( MovementState == MoveState.Closed )
		{
			if ( !CanUse( null ).CanUse )
				return false;

			Toggle( position );
		}

		return true;
	}

	MapMover FindPartner()
	{
		if ( PartnerObject.IsValid() )
			return PartnerObject.GetComponent<MapMover>();

		if ( string.IsNullOrEmpty( PartnerName ) )
			return null;

		return Scene.Directory.FindByName( PartnerName )
			.Select( x => x.GetComponent<MapMover>() )
			.FirstOrDefault( x => x.IsValid() && x != this );
	}

	void StartMove( bool open, Vector3? activatorPosition )
	{
		// Close back the way we opened
		var reverse = open ? activatorPosition is { } position && ShouldReverse( position ) : Reversed;
		BroadcastMove( GameObject.Id, open, reverse );
	}

	[Rpc.Broadcast]
	static void BroadcastMove( Guid objectId, bool open, bool reverse )
	{
		var mover = Game.ActiveScene?.Directory.FindByGuid( objectId )?.GetComponent<MapMover>();
		if ( !mover.IsValid() ) return;

		mover.Reversed = reverse;
		mover.MovementState = open ? MoveState.Opening : MoveState.Closing;
		mover._sinceMoveStarted = 0f;
		mover.PlaySound( open ? mover.OpenSound : mover.CloseSound );
	}

	void PlaySound( SoundEvent resource )
	{
		if ( resource is null ) return;
		Sound.Play( resource, WorldPosition );
	}

	protected override void OnFixedUpdate()
	{
		UpdateNavMesh();

		if ( MovementState == MoveState.Open )
		{
			if ( AutoReset && Networking.IsHost && _sinceOpened > ResetTime )
				Toggle();

			return;
		}

		// Don't do anything if we're not opening or closing
		if ( MovementState != MoveState.Opening && MovementState != MoveState.Closing )
			return;

		var opening = MovementState == MoveState.Opening;
		var duration = opening ? OpenDuration : CloseDuration;
		var time = duration > 0f ? (_sinceMoveStarted / duration).Clamp( 0f, 1f ) : 1f;
		var amount = (opening ? OpenMovementCurve : CloseMovementCurve).Evaluate( time );

		// Move backwards if we're closing
		if ( !opening ) amount = 1f - amount;

		SetOpenAmount( amount );

		// If we're done finalize the state and play the sound
		if ( time < 1f ) return;

		MovementState = opening ? MoveState.Open : MoveState.Closed;
		_sinceOpened = 0f;
		PlaySound( opening ? OpenFinishedSound : CloseFinishedSound );
	}
}
