namespace Tec.AI;

public class FootstepsAiStims : Component
{
	[Property] public SkinnedModelRenderer Renderer { get; set; }
	[Property] public Facepunch.Pawn Player { get; set; }

	protected override void OnStart()
	{
		base.OnStart();
		
		// Renderer.SceneModel.OnAnimTagEvent += @event => PrintOverlay.Print(@event.ToString());
		// Renderer.OnAnimTagEvent += @event => PrintOverlay.Print(@event.ToString());
		
		// Renderer.OnFootstepEvent += @event => PrintOverlay.Print(@event.ToString());
		Renderer.OnFootstepEvent += @event => new AudioStim( Player.Team.ToFaction(), @event.Transform.Position, 264f * @event.Volume, AudioStim.AudioStimType.Footstep );
	}
}
