namespace Facepunch;

/// <summary>
/// Manages party state: membership, invites, and leader.
/// Attach to a persistent networked GameObject in the scene.
/// Adapted from fps project — uses Client instead of PlayerData.
/// </summary>
public sealed class PartySystem : Component, Component.INetworkListener
{
	public static PartySystem Current { get; private set; }

	/// <summary>All party member connection GUIDs. Synced to all clients.</summary>
	[Sync( SyncFlags.FromHost )]
	public NetList<Guid> MemberIds { get; private set; } = new();

	/// <summary>The party leader's connection GUID. Synced to all clients.</summary>
	[Sync( SyncFlags.FromHost )]
	public Guid LeaderId { get; private set; }

	// Host-only: who has a pending invite
	private readonly HashSet<Guid> _pendingInvites = new();

	protected override void OnStart()  => Current = this;
	protected override void OnDestroy() { if ( Current == this ) Current = null; }

	// ── Internal lookup ──────────────────────────────────────────────────

	private static Guid LocalConnectionId => Connection.Local?.Id ?? Guid.Empty;

	private static Client FindClient( Guid id ) =>
		GameUtils.AllPlayers.FirstOrDefault( c => c.Connection?.Id == id );

	// ── Read helpers (safe on any client) ────────────────────────────────

	public bool IsInParty( Guid id )  => MemberIds.Contains( id );
	public bool IsLeader( Guid id )   => LeaderId == id;
	public bool LocalIsLeader         => LocalConnectionId != Guid.Empty && LeaderId == LocalConnectionId;
	public bool LocalIsInParty        => LocalConnectionId != Guid.Empty && MemberIds.Contains( LocalConnectionId );

	public IEnumerable<Client> Members =>
		MemberIds.Select( FindClient ).Where( c => c.IsValid() );

	// ── Invite ────────────────────────────────────────────────────────────

	/// <summary>Leader calls this to invite a player by their connection GUID.</summary>
	public void Invite( Guid targetId )
	{
		if ( !Networking.IsHost ) { HostInvite( targetId ); return; }

		var localId = LocalConnectionId;
		if ( localId == Guid.Empty ) return;

		ProcessInvite( localId, targetId );
	}

	[Rpc.Host]
	private void HostInvite( Guid targetId ) => ProcessInvite( Rpc.Caller.Id, targetId );

	private void ProcessInvite( Guid callerId, Guid targetId )
	{
		// First invite: caller becomes leader and joins their own party
		if ( MemberIds.Count == 0 )
		{
			LeaderId = callerId;
			MemberIds.Add( callerId );
		}

		// Only the leader can invite
		if ( callerId != LeaderId ) return;
		if ( MemberIds.Contains( targetId ) ) return;
		if ( _pendingInvites.Contains( targetId ) ) return;

		_pendingInvites.Add( targetId );

		var fromClient = FindClient( callerId );
		var fromName = fromClient.IsValid() ? fromClient.DisplayName : "Someone";

		// Broadcast — each client checks if it's the target
		ReceiveInvite( targetId, fromName, callerId );
	}

	/// <summary>Broadcast to all; only the target reacts.</summary>
	[Rpc.Broadcast]
	private void ReceiveInvite( Guid targetId, string fromName, Guid fromId )
	{
		if ( LocalConnectionId != targetId ) return;
		Facepunch.UI.PartyPanel.ShowInvite( fromName, fromId );
	}

	// ── Accept / Decline ─────────────────────────────────────────────────

	public void AcceptInvite( Guid fromId )
	{
		if ( !Networking.IsHost ) { HostAcceptInvite( fromId ); return; }

		var localId = LocalConnectionId;
		if ( localId == Guid.Empty ) return;

		ProcessAccept( localId );
	}

	[Rpc.Host]
	private void HostAcceptInvite( Guid fromId ) => ProcessAccept( Rpc.Caller.Id );

	private void ProcessAccept( Guid callerId )
	{
		if ( !_pendingInvites.Remove( callerId ) ) return;
		if ( !MemberIds.Contains( callerId ) )
			MemberIds.Add( callerId );
	}

	public void DeclineInvite( Guid fromId )
	{
		if ( !Networking.IsHost ) { HostDeclineInvite( fromId ); return; }

		var localId = LocalConnectionId;
		if ( localId == Guid.Empty ) return;

		_pendingInvites.Remove( localId );
	}

	[Rpc.Host]
	private void HostDeclineInvite( Guid fromId ) => _pendingInvites.Remove( Rpc.Caller.Id );

	// ── Leave / Kick ─────────────────────────────────────────────────────

	public void LeaveParty()
	{
		if ( !Networking.IsHost ) { HostLeaveParty(); return; }

		var localId = LocalConnectionId;
		if ( localId == Guid.Empty ) return;

		ProcessLeave( localId );
	}

	[Rpc.Host]
	private void HostLeaveParty() => ProcessLeave( Rpc.Caller.Id );

	private void ProcessLeave( Guid callerId )
	{
		MemberIds.Remove( callerId );
		if ( LeaderId == callerId && MemberIds.Count > 0 )
			LeaderId = MemberIds[0];
		if ( MemberIds.Count <= 1 )
			Disband();
	}

	public void KickMember( Guid targetId )
	{
		if ( !Networking.IsHost ) { HostKickMember( targetId ); return; }
		ProcessKick( Connection.Local.Id, targetId );
	}

	[Rpc.Host]
	private void HostKickMember( Guid targetId ) => ProcessKick( Rpc.Caller.Id, targetId );

	private void ProcessKick( Guid callerId, Guid targetId )
	{
		if ( callerId != LeaderId ) return;
		MemberIds.Remove( targetId );
		if ( MemberIds.Count <= 1 ) Disband();
	}

	private void Disband()
	{
		MemberIds.Clear();
		LeaderId = Guid.Empty;
		_pendingInvites.Clear();
	}

	//  Pull Party 

	public void PullParty()
	{
		if ( !Networking.IsHost ) { HostPullParty(); return; }
		ProcessPullParty( LocalConnectionId );
	}

	[Rpc.Host]
	private void HostPullParty() => ProcessPullParty( Rpc.Caller.Id );

	private void ProcessPullParty( Guid callerId )
	{
		if ( callerId != LeaderId ) return;

		foreach ( var memberId in MemberIds )
		{
			var client = FindClient( memberId );
			if ( client.IsValid() && client.Connection != null )
			{
				using ( Rpc.FilterInclude( client.Connection ) )
				{
					RpcPullToMenu();
				}
			}
		}
	}

	[Rpc.Broadcast]
	private void RpcPullToMenu()
	{
		GameUtils.ReturnToMainMenu();
	}

	//  Disconnect cleanup ────────────────────────────────────────────────

	void Component.INetworkListener.OnDisconnected( Connection channel )
	{
		if ( !Networking.IsHost ) return;
		ProcessLeave( channel.Id );
		_pendingInvites.Remove( channel.Id );
	}
}
