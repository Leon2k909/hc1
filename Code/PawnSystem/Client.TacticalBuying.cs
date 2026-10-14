namespace Facepunch;

public partial class Client
{
	[Rpc.Host]
	public void BuyTacticalEquipment( string resourcePath )
	{
		if ( Rpc.Caller != Connection || !TacticalEconomy.Current.IsValid() ) return;
		var resource = ResourceLibrary.Get<EquipmentResource>( resourcePath );
		var bought = TacticalEconomy.Current.TryBuyEquipment( PlayerPawn, resource );
		TacticalPurchaseFinished( bought, resource?.Name ?? "" );
	}

	[Rpc.Host]
	public void BuyTacticalGear( TacticalGear gear )
	{
		if ( Rpc.Caller != Connection || !TacticalEconomy.Current.IsValid() ) return;
		var bought = TacticalEconomy.Current.TryBuyGear( PlayerPawn, gear );
		TacticalPurchaseFinished( bought, UI.TacticalBuyMenu.GearName( gear ) );
	}

	[Rpc.Owner( NetFlags.HostOnly )]
	private void TacticalPurchaseFinished( bool success, string item )
	{
		UI.TacticalBuyMenu.Instance?.PurchaseFinished( success, item );
	}
}
