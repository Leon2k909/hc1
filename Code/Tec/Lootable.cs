using System.Runtime.Intrinsics.X86;
using System.Runtime.Serialization;
using Facepunch;
using Sandbox.Events;
using Sandbox.UI;

namespace Tec;

public enum Loot
{
	ExtractionToken,
	Something,
	SomethingElse,
}

public class Lootable: PanelComponent, IUse
{
	public Loot Loot { get; set; }
	private TextPanel textPanel;
	private bool _looted = false;
	private bool _canUse = true;

	private bool showingPanel = false;
	
	private Prop Prop => field ??= GetComponent<Prop>();
	public PrefabFile LootPrefab {get; set;}

	protected override void OnStart()
	{
		Prop?.OnPropBreak += () =>
		{
			if ( _looted )
				return;
			
			var spawnedObject = GameObject.Clone( LootPrefab, new Transform(WorldPosition, WorldRotation) );
			if (!spawnedObject.IsValid())
				return;
			spawnedObject.Enabled = true;
			spawnedObject.NetworkSpawn(true, (Connection) null);
		};
	}

	public UseResult CanUse( PlayerPawn player )
	{
		return _canUse && !showingPanel;
	}

	public void OnUse( PlayerPawn player )
	{
		string lootText = "Already looted.";

		if ( !_looted )
		{
			// Log.Info("Loot stuff----------------------------------------------");
			switch ( Loot )
			{
				case Loot.ExtractionToken:
					lootText = "The gnome!";
					// GameObject.Scene.Dispatch( new ExtractionTokenObtainedEvent( player.Team ) );
					break;
				case Loot.Something:
					lootText = "Something";
					break;
				case Loot.SomethingElse:
					lootText = "Something Else";
					break;
				default:
					return;
			}
			PrintOverlay.Print($"Looted: {lootText}");
		}
		
		_looted = true;
		
		textPanel?.Delete();
		textPanel = new TextPanel( lootText );
		Panel.AddChild( textPanel );
		showingPanel = true;
		
		PrintOverlay.Print($"Looted: {lootText}");
		
		Invoke(2f,DisableText);
	}

	private void DisableText()
	{
		showingPanel = false;
		textPanel.Delete();
	}
}
