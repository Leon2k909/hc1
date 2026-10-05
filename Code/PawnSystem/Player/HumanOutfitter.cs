using Sandbox.Events;

namespace Facepunch;

public sealed class HumanOutfitter : Component,
	IGameEventHandler<TeamChangedEvent>
{
	public struct TeamModelEntry 
	{
		[KeyProperty] public List<Model> Models { get; set; }
	}

	[Property] public PlayerPawn PlayerPawn { get; set; }
	[Property] public SkinnedModelRenderer Renderer { get; set; }
	[Property, InlineEditor] public Dictionary<Team, TeamModelEntry> TeamBaseModels { get; set; } = new();

	void IGameEventHandler<TeamChangedEvent>.OnGameEvent( TeamChangedEvent eventArgs )
	{
		UpdateFromTeam( eventArgs.After );
	}

	/// <summary>
	/// Called to wear an outfit based off a team: the one the player equipped for it (<see cref="OperatorOutfits"/>).
	/// The host picks it and every machine wears it. On a client it does nothing, as when this was itself the host-only
	/// broadcast.
	/// </summary>
	public void UpdateFromTeam( Team team )
	{
		if ( !Networking.IsHost )
			return;

		Wear( team, OutfitFor( team ).Style );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void Wear( Team team, MilitaryUniformStyle style )
	{
		if ( !TeamBaseModels.TryGetValue( team, out var model ) )
		{
			model = TeamBaseModels[Team.Terrorist];
		}

		MilitaryUniform.SetModel( Renderer, Game.Random.FromList( model.Models ), style );
		// A dead pawn's body has left it as a ragdoll.
		if ( PlayerPawn.Body.IsValid() )
			PlayerPawn.Body.Refresh();
	}

	/// <summary>
	/// The player's equipped outfit for <paramref name="team"/>. The body and the first-person body each have an
	/// outfitter, so this mustn't be random: a bot (a player-pawn one) gets one by its id.
	/// </summary>
	private OperatorOutfit OutfitFor( Team team )
	{
		var client = PlayerPawn.IsValid() ? PlayerPawn.Client : null;
		if ( !client.IsValid() )
			return OperatorOutfits.ForTeam( team )[0];

		if ( client.IsBot )
		{
			var outfits = OperatorOutfits.ForTeam( team );
			return outfits[(int)((uint)client.BotId % (uint)outfits.Count)];
		}

		// The host's own picks are its cookies: they need no syncing, and offline there's nothing to sync them over.
		var own = client.Connection is null || client.Connection == Connection.Local;
		return OperatorOutfits.Resolve( team, own ? OperatorOutfits.LocalPicks : client.OperatorPicks );
	}
}
