namespace Tec;

public class LootManager : Component
{
	[Property]
	private PrefabFile extractionToken;
	
	[Property]
	private List<Lootable> _lootables;
	
	protected override void OnAwake()
	{
		int tokenIdx = Random.Shared.Next( 0, _lootables.Count );

		for ( int i = 0; i < _lootables.Count; i++ )
		{
			if ( i == tokenIdx )
			{
				_lootables[i].Loot = Loot.ExtractionToken;
				_lootables[i].LootPrefab = extractionToken;
			}
			else
				_lootables[i].Loot = (Loot) Random.Shared.Next( 1, Enum.GetNames(typeof(Loot)).Length );
		}
	}
}
