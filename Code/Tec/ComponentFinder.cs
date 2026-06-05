using Facepunch;

namespace Tec;

/// <summary>
/// Just a stupid component to use its property to find a component in the hierarchy.
/// </summary>
public class ComponentFinder : Component
{
	[Property] public CombatBehavior componentToFind;
}
