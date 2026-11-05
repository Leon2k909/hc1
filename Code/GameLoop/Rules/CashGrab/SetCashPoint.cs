using Sandbox.Events;

namespace Facepunch;

public partial class SetCashPoint : Component, IGameEventHandler<EnterStateEvent>
{
	[Late]
	public void OnGameEvent( EnterStateEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		var tracker = GameMode.Instance.Get<CashPointTracker>();
		var cashPoints = tracker.All.Where( x => x.IsValid() ).ToList();
		if ( cashPoints.Count == 0 ) return;

		// Move away from the current point whenever another is available. Single-point maps can reuse theirs.
		var alternatives = cashPoints.Where( x => tracker.Current != x ).ToList();
		var selected = Game.Random.FromList( alternatives.Count > 0 ? alternatives : cashPoints );

		// Turn off all the cash points
		foreach ( var item in cashPoints )
		{
			if ( item == selected )
			{
				item.SetSpawning();
			}
			else
			{
				item.Deactivate();
			}
		}

		// Turn on our selected cash point
		{
			tracker.Last = tracker.Current;
			tracker.Current = selected;
		}
	}
}
