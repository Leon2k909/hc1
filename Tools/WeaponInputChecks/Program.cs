global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
void Button( bool down, bool pressed = false )
{
	Input.Held = down;
	Input.NewPress = pressed;
}
void Reset()
{
	Button( false );
	GameUtils.StudioOpen = false;
	Facepunch.UI.ClassSelect.IsAnyOpen = false;
	Facepunch.UI.TacticalBuyMenu.IsAnyOpen = false;
	Facepunch.UI.ZombiesWorkbenchPanel.IsAnyOpen = false;
}

// Test the real dispatcher with an update callback that reads raw input, as semi/burst fire does.
foreach ( var blocker in new[] { "class", "buy", "workbench", "gunsmith", "climbing" } )
{
	Reset();
	var action = new ProbeAction();
	void Block( bool blocked )
	{
		switch ( blocker )
		{
			case "class": Facepunch.UI.ClassSelect.IsAnyOpen = blocked; break;
			case "buy": Facepunch.UI.TacticalBuyMenu.IsAnyOpen = blocked; break;
			case "workbench": Facepunch.UI.ZombiesWorkbenchPanel.IsAnyOpen = blocked; break;
			case "gunsmith": GameUtils.StudioOpen = blocked; break;
			case "climbing": action.Weapon.Owner.IsPipeClimbing = blocked; break;
		}
	}

	action.Tick(); // Establish the deployment's released input.
	Button( true, true );
	action.Tick();
	Check( action.RawShots == 1 && action.IsTakingInput, $"{blocker}: normal firing must work before suppression." );
	action.QueuedBurst = true;
	var updates = action.Updates;
	var callbacks = action.Callbacks;
	Block( true );
	action.Tick();
	Check( action.RawShots == 1 && action.Updates == updates, $"{blocker}: menu clicks must never reach raw semi/burst input." );
	Check( !action.QueuedBurst && action.Suppressions == 1, $"{blocker}: pending burst actions must be cancelled through the suppression hook." );
	Check( !action.IsTakingInput && action.Releases == 1, $"{blocker}: opening a menu must release an active trigger and stop blocking sprint." );
	Check( action.Callbacks == callbacks, $"{blocker}: suppressed input must not invoke ActionGraph actions." );
	action.Tick();
	Check( action.Releases == 1, $"{blocker}: the release callback must run only once." );
	Block( false );
	action.Tick();
	Check( action.Updates == updates && !action.IsTakingInput, $"{blocker}: holding a menu click through closing must not resume fire." );
	Button( false );
	action.Tick();
	Button( true, true );
	action.Tick();
	Check( action.RawShots == 2 && action.IsTakingInput, $"{blocker}: a fresh press after release must fire normally." );

	// UI code may consume the button while open, then expose it again on closing.
	Block( true );
	Button( false );
	action.Tick();
	updates = action.Updates;
	Block( false );
	Button( true, true );
	action.Tick();
	Check( action.Updates == updates && action.RawShots == 2, $"{blocker}: a UI-consumed click must remain blocked when the menu closes." );
	Button( false );
	action.Tick();
	Button( true, true );
	action.Tick();
	Check( action.RawShots == 3, $"{blocker}: input must recover after a UI-consumed click is released." );
}

Reset();
var deployedHeld = new ProbeAction();
Button( true, true );
deployedHeld.Tick();
Check( deployedHeld.RawShots == 0 && !deployedHeld.IsTakingInput, "Fire held before deployment/respawn must still require release." );
Button( false );
deployedHeld.Tick();
Button( true, true );
deployedHeld.Tick();
Check( deployedHeld.RawShots == 1, "A fresh press after deployment must still work." );

Reset();
var aim = new ProbeAction { AllowHeldThroughDeploy = true };
Button( true );
aim.Tick();
Check( aim.IsTakingInput, "Actions allowing held input through deployment must retain that behavior." );
Facepunch.UI.ClassSelect.IsAnyOpen = true;
aim.Tick();
Facepunch.UI.ClassSelect.IsAnyOpen = false;
aim.Tick();
Check( !aim.IsTakingInput, "Held-through-deploy exceptions must not bypass the menu release latch." );

Reset();
var remote = new ProbeAction();
remote.Weapon.Owner.IsLocallyControlled = false;
remote.Tick();
Check( remote.Updates == 0 && remote.Suppressions == 0, "Remote owners must not run weapon input." );
var holstered = new ProbeAction();
holstered.Weapon.IsDeployed = false;
holstered.Tick();
Check( holstered.Updates == 0 && holstered.Suppressions == 0, "Holstered weapons must not run weapon input." );

Console.WriteLine( $"PASS: {checks} weapon input checks against the production dispatcher." );

// Engine seams only: the input/deploy/menu dispatch logic is linked from game code.
namespace Sandbox
{
	public class Component { public bool Valid { get; set; } = true; }
	public static class Validity { public static bool IsValid( this Component component ) => component?.Valid == true; }
	public sealed class PropertyAttribute : Attribute;
	public sealed class CategoryAttribute( string name ) : Attribute { public string Name { get; } = name; }
	public static class Input
	{
		public static bool Suppressed, MouseCursorVisible;
		public static bool Held { get; set; }
		public static bool NewPress { get; set; }
		public static bool Down( string action ) => Held;
		public static bool Pressed( string action ) => NewPress;
	}
}
namespace Sandbox.Events
{
	public interface IGameEventHandler<T> { void OnGameEvent( T eventArgs ); }
}
namespace Facepunch
{
	public class PlayerPawn : Component
	{
		public bool IsLocallyControlled { get; set; } = true;
		public bool IsPipeClimbing { get; set; }
	}
	public class Equipment : Component
	{
		public PlayerPawn Owner { get; set; } = new();
		public bool IsDeployed { get; set; } = true;
	}
	public abstract class EquipmentComponent : Component
	{
		protected Equipment Equipment { get; set; } = new();
		protected virtual void OnFixedUpdate() { }
	}
	public record EquipmentDeployedEvent( Equipment Equipment );
	public static class GameUtils
	{
		public static bool StudioOpen { get; set; }
		public static bool IsGunsmithStudioOpen() => StudioOpen;
	}
	public class ProbeAction : WeaponInputAction
	{
		public Equipment Weapon => Equipment;
		public int Updates { get; private set; }
		public int RawShots { get; private set; }
		public int Releases { get; private set; }
		public int Suppressions { get; private set; }
		public int Callbacks { get; private set; }
		public bool QueuedBurst { get; set; }
		public bool AllowHeldThroughDeploy { get; set; }
		public ProbeAction() { OnInputAction = _ => Callbacks++; }
		protected override bool TakesInputHeldThroughDeploy => AllowHeldThroughDeploy;
		public void Tick() => OnFixedUpdate();
		protected override void OnInputUpdate()
		{
			Updates++;
			if ( Input.Pressed( "Attack1" ) || QueuedBurst ) RawShots++;
		}
		protected override void OnInputUp() => Releases++;
		protected override void OnInputSuppressed() { Suppressions++; QueuedBurst = false; }
	}
}
namespace Facepunch.UI
{
	public static class ClassSelect { public static bool IsAnyOpen { get; set; } }
	public static class TacticalBuyMenu { public static bool IsAnyOpen { get; set; } }
	public static class ZombiesWorkbenchPanel { public static bool IsAnyOpen { get; set; } }
}
