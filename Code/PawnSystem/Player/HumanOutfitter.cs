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
	// Retained for existing prefabs; playable character models now come from OperatorOutfits.
	[Property, InlineEditor] public Dictionary<Team, TeamModelEntry> TeamBaseModels { get; set; } = new();

	/// <summary>The host's selected character, retained in snapshots for players joining after the spawn.</summary>
	[Sync( SyncFlags.FromHost ), Change( nameof( OnOutfitIdChanged ) )]
	public string OutfitId { get; set; } = "";

	protected override void OnStart() => ApplyOutfit();
	protected override void OnEnabled() => ApplyOutfit();
	private void OnOutfitIdChanged( string before, string after ) => ApplyOutfit();

	void IGameEventHandler<TeamChangedEvent>.OnGameEvent( TeamChangedEvent eventArgs )
	{
		UpdateFromTeam( eventArgs.After );
	}

	/// <summary>
	/// Called to wear an outfit based off a team: the one the player equipped for it (<see cref="OperatorOutfits"/>).
		/// The host picks it and every machine wears the same model and uniform, including late joiners.
	/// </summary>
	public void UpdateFromTeam( Team team )
	{
		if ( !Networking.IsHost )
			return;

		OutfitId = OutfitFor( team ).Id;
		// Respawning can reset the body without changing the equipped id.
		ApplyOutfit();
	}

	private void ApplyOutfit()
	{
		if ( !Renderer.IsValid() ) return;
		var outfit = OperatorOutfits.All.FirstOrDefault( x => x.Id == OutfitId );
		if ( outfit is null ) return;
		var model = Model.Load( outfit.ModelPath );
		if ( model is null || model.IsError ) return;

		MilitaryUniform.SetModel( Renderer, model, outfit.Style );
		// A dead pawn's body has left it as a ragdoll.
		if ( PlayerPawn.IsValid() && PlayerPawn.Body.IsValid() && PlayerPawn.Body.Player.IsValid() )
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
