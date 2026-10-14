global using Sandbox;
using Facepunch;
using Sandbox.Events;

var checks = 0;
void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
    checks++;
}

var mode = new GameMode { UsesStandardHealth = true, Hardcore = true, ArmorEnabled = true, HelmetsEnabled = true };
GameMode.Instance = mode;
GameMode.ActiveHardcore = true;
Check(!GameMode.IsHardcore, "Tactical health must override a client's stale hardcore preference.");
mode.UsesStandardHealth = false;
Check(GameMode.IsHardcore, "Ordinary hardcore modes must retain trauma.");
mode.UsesStandardHealth = true;
var economy = new TacticalEconomy();
mode.Set(economy);
var buyRule = new EnableBuyMenu { BuyMenuMode = BuyMenuMode.EnabledEverywhere };
mode.Set(buyRule);

PlayerPawn Player(Team team = Team.Terrorist, int balance = 800)
{
    var client = new Client { Balance = balance };
    var player = new PlayerPawn { Client = client, Team = team };
    client.PlayerPawn = player;
    return player;
}

EquipmentResource Weapon(string path, int price = 300)
{
    var resource = new EquipmentResource { ResourcePath = path, Name = path, Price = price };
    EquipmentResource.All.Add(resource);
    ResourceLibrary.Items[path] = resource;
    return resource;
}

var armor = new TestArmor { Armor = 100, HasHelmet = true };
mode.ArmorEnabled = false;
var hit = new ModifyDamageTakenEvent { DamageInfo = new(DamageFlags.Armor | DamageFlags.Helmet) };
((IGameEventHandler<ModifyDamageTakenEvent>)armor).OnGameEvent(hit);
Check(hit.DamageInfo.Flags == DamageFlags.None, "Disabled protection must remove stale damage flags.");
armor.TickForTest();
Check(armor.Armor == 0 && !armor.HasHelmet, "Disabling protection must clear existing armour and helmets.");
mode.ArmorEnabled = true;
mode.HelmetsEnabled = false;
armor.Armor = 100;
armor.HasHelmet = true;
hit.DamageInfo = new(DamageFlags.Helmet);
((IGameEventHandler<ModifyDamageTakenEvent>)armor).OnGameEvent(hit);
Check(hit.DamageInfo.Flags == DamageFlags.Armor, "Body-only modes must not grant head protection.");
mode.HelmetsEnabled = true;
armor.Armor = 0;
hit.DamageInfo = new(DamageFlags.None);
((IGameEventHandler<ModifyDamageTakenEvent>)armor).OnGameEvent(hit);
Check(hit.DamageInfo.Flags == DamageFlags.None, "An exhausted vest must not protect the body or head.");

var pistol = Weapon("pistol");
var rifle = Weapon("rifle", 2900);
var hidden = Weapon("hidden"); hidden.IsPurchasable = false;
var unfinished = Weapon("unfinished"); unfinished.IsWip = true;
var free = Weapon("free", 0);
var bomb = Weapon("bomb"); bomb.Slot = EquipmentSlot.Special;
var otherTeam = Weapon("defender-rifle"); otherTeam.Team = Team.CounterTerrorist;
var badPrefab = Weapon("unsupported"); badPrefab.MainPrefab.HasEquipment = false;
var catalog = TacticalEconomy.Catalog(Team.Terrorist).ToArray();
Check(catalog.Length == 2 && catalog.Contains(pistol) && catalog.Contains(rifle), "The catalog must exclude free, restricted, special, unfinished and unsupported equipment.");

var player = Player();
Check(economy.TryBuyEquipment(player, pistol) && player.Client.Balance == 500 && player.Inventory.Has(pistol), "A successful purchase must grant equipment and charge its server price.");
Check(!player.Inventory.LastAppliedSavedAttachments, "Purchased weapons must not receive free saved attachments.");
Check(!economy.TryBuyEquipment(player, pistol) && player.Client.Balance == 500, "Repeated requests for an owned weapon must not charge again.");
Check(!economy.TryBuyEquipment(player, rifle) && player.Client.Balance == 500, "Unaffordable purchases must leave balance unchanged.");
Check(!economy.TryBuyEquipment(player, otherTeam), "Team-restricted purchases must be rejected on the host.");
var failedGrant = Weapon("failed-grant");
player.Inventory.FailNextGrant = true;
Check(!economy.TryBuyEquipment(player, failedGrant) && player.Client.Balance == 500, "A failed grant must not deduct money.");
buyRule.BuyMenuMode = BuyMenuMode.Disabled;
Check(!economy.TryBuyEquipment(player, failedGrant) && player.Client.Balance == 500, "Late requests after the buy phase must be rejected.");
buyRule.BuyMenuMode = BuyMenuMode.EnabledEverywhere;
mode.Remove<EnableBuyMenu>();
Check(!TacticalEconomy.CanBuy(player), "Without an active buy rule, stale client state must not permit buying.");
mode.Set(buyRule);

player = Player();
Check(economy.TryBuyGear(player, TacticalGear.Armor) && player.Client.Balance == 150 && player.ArmorComponent.Armor == 100, "Armour must cost $650 and fill protection.");
Check(!economy.TryBuyGear(player, TacticalGear.ArmorAndHelmet), "Helmet upgrades must not bypass affordability checks.");
player.Client.Balance = 1000;
Check(TacticalEconomy.GearPrice(player, TacticalGear.ArmorAndHelmet) == 350, "A full vest must reduce the helmet upgrade price to $350.");
Check(economy.TryBuyGear(player, TacticalGear.ArmorAndHelmet) && player.Client.Balance == 650 && player.ArmorComponent.HasHelmet, "Helmet upgrades must grant and charge exactly once.");
Check(!economy.TryBuyGear(player, TacticalGear.ArmorAndHelmet) && player.Client.Balance == 650, "Owned gear must not be charged again.");
player.ArmorComponent.Armor = 50;
Check(TacticalEconomy.GearPrice(player, TacticalGear.ArmorAndHelmet) == 650, "A retained helmet must not be charged again when repairing armour.");
Check(!economy.TryBuyGear(player, TacticalGear.DefuseKit), "Attackers must not buy defuse kits.");
player.Team = Team.CounterTerrorist;
Check(economy.TryBuyGear(player, TacticalGear.DefuseKit) && player.Client.Balance == 250 && player.Inventory.HasDefuseKit, "Defenders must be able to buy a $400 kit.");
Check(!economy.TryBuyGear(player, TacticalGear.DefuseKit) && player.Client.Balance == 250, "Kit purchases must reject duplicates.");
Check(!economy.TryBuyGear(player, (TacticalGear)99), "Malformed gear requests must be rejected.");
player.HealthComponent.State = LifeState.Dead;
Check(!TacticalEconomy.CanBuy(player), "Dead players must not buy.");
player.HealthComponent.State = LifeState.Alive;
Networking.IsHost = false;
Check(!economy.TryBuyEquipment(player, failedGrant), "Only the host may mutate purchases.");
Networking.IsHost = true;

player = Player();
Rpc.Caller = new Connection(Guid.NewGuid());
player.Client.BuyTacticalEquipment("pistol");
Check(player.Client.Balance == 800 && !player.Inventory.Has(pistol), "An RPC from another client must not purchase on this player's behalf.");
Rpc.Caller = player.Client.Connection;
player.Client.BuyTacticalEquipment("pistol");
Check(player.Client.Balance == 500 && player.Inventory.Has(pistol), "An authenticated owner RPC must reach the host economy.");
player.Client.BuyTacticalEquipment("missing-resource");
Check(player.Client.Balance == 500, "Unknown resources must not deduct money.");

var rewards = new KillRewards();
var killWeapon = new Equipment { Resource = pistol };
var npc = new LightweightCombatBot { Team = Team.CounterTerrorist };
((IGameEventHandler<KillEvent>)rewards).OnGameEvent(new(new(DamageFlags.None) { Attacker = player, Victim = npc, Inflictor = killWeapon }));
Check(player.Client.Balance == 800, "Killing an opposing lightweight bot must earn the weapon's reward in Tactical Defuse.");
npc.Team = player.Team;
((IGameEventHandler<KillEvent>)rewards).OnGameEvent(new(new(DamageFlags.None) { Attacker = player, Victim = npc, Inflictor = killWeapon }));
Check(player.Client.Balance == 500, "Friendly bot kills must apply the same cash penalty as friendly player kills.");
var victim = Player(Team.CounterTerrorist);
((IGameEventHandler<KillEvent>)rewards).OnGameEvent(new(new(DamageFlags.None) { Attacker = player, Victim = victim, Inflictor = killWeapon }));
Check(player.Client.Balance == 800, "Normal player kill rewards must still work.");
mode.Remove<TacticalEconomy>();
npc.Team = Team.CounterTerrorist;
((IGameEventHandler<KillEvent>)rewards).OnGameEvent(new(new(DamageFlags.None) { Attacker = player, Victim = npc, Inflictor = killWeapon }));
Check(player.Client.Balance == 800, "The new NPC economy must not change ordinary mode rewards.");
mode.Set(economy);

Console.WriteLine($"PASS: {checks} checks against the production economy, RPC handlers, armour and health-mode settings.");

// Minimal engine substitutes let the production rules run without booting a map.
namespace Sandbox
{
    public class Component
    {
        public bool IsValid { get; set; } = true;
        public GameObject GameObject { get; } = new();
        protected virtual void OnUpdate() { }
        protected T GetGlobal<T>() where T : new() => new();
    }
    public class GameObject
    {
        public bool HasEquipment { get; set; } = true;
        public GameObject Root => this;
        public void Dispatch(object value) { }
        public T GetComponentInChildren<T>(bool includeDisabled = false) where T : class => HasEquipment ? new Facepunch.Equipment() as T : null;
    }
    public static class Validity
    {
        public static bool IsValid(this object value) => value is Component { IsValid: true } or GameObject or Facepunch.EquipmentResource { IsValid: true };
    }
    public static class Networking { public static bool IsHost { get; set; } = true; }
    public sealed record Connection(Guid Id);
    public enum NetFlags { HostOnly }
    public static class Rpc
    {
        public static Connection Caller { get; set; }
        public sealed class HostAttribute : Attribute { }
        public sealed class OwnerAttribute(NetFlags flags) : Attribute { }
    }
    public static class ResourceLibrary
    {
        public static Dictionary<string, object> Items { get; } = new();
        public static T Get<T>(string path) where T : class => path is not null && Items.TryGetValue(path, out var item) ? item as T : null;
    }
    public enum SyncFlags { FromHost }
    public sealed class PropertyAttribute : Attribute { }
    public sealed class ReadOnlyAttribute : Attribute { }
    public sealed class SyncAttribute(SyncFlags flags) : Attribute { }
    public sealed class ChangeAttribute(string method) : Attribute { }
    public sealed class DeveloperCommandAttribute(string name, string category) : Attribute { }
    public sealed class ShowIfAttribute(string name, bool value) : Attribute { }
}
namespace Sandbox.Events
{
    public interface IGameEvent;
    public interface IGameEventHandler<T> { void OnGameEvent(T eventArgs); }
    public sealed class EarlyAttribute : Attribute { }
}
namespace Facepunch
{
    public enum Team { Unassigned, Terrorist, CounterTerrorist }
    public enum EquipmentSlot { Undefined, Primary, Secondary, Melee, Utility, Special, Tactical, Lethal }
    public enum BuyMenuMode { Disabled, EnabledInBuyZone, EnabledEverywhere }
    public enum LifeState { Alive, Dead }
    [Flags] public enum DamageFlags { None, Armor = 1, Helmet = 2 }
    public record DamageInfo(DamageFlags Flags)
    {
        public Component Attacker { get; init; }
        public Component Victim { get; init; }
        public Component Inflictor { get; init; }
    }
    public record KillEvent(DamageInfo DamageInfo);
    public record BombPlantedEvent(PlayerPawn Planter);
    public record BombDefusedEvent(PlayerPawn Defuser);
    public class ModifyDamageTakenEvent
    {
        public DamageInfo DamageInfo { get; set; }
        public void AddFlag(DamageFlags flag) => DamageInfo = DamageInfo with { Flags = DamageInfo.Flags | flag };
    }
    public class PlayerGlobals { public float MaxArmor => 100; }
    public partial class GameMode : Component
    {
        public static GameMode Instance { get; set; }
        public static bool ActiveHardcore { get; set; }
        private readonly Dictionary<Type, Component> _rules = new();
        public T Get<T>() where T : class => _rules.TryGetValue(typeof(T), out var rule) ? rule as T : null;
        public void Set<T>(T component) where T : Component => _rules[typeof(T)] = component;
        public void Remove<T>() => _rules.Remove(typeof(T));
    }
    public class EnableBuyMenu : Component { public BuyMenuMode BuyMenuMode { get; set; } }
    public partial class Client : Component
    {
        public static Client Local { get; set; }
        public Connection Connection { get; set; } = new(Guid.NewGuid());
        public PlayerPawn PlayerPawn { get; set; }
        public int Balance { get; set; }
        public void GiveCash(int amount) => Balance += amount;
    }
    public class PlayerPawn : Component
    {
        public Client Client { get; set; }
        public Team Team { get; set; }
        public TestArmor ArmorComponent { get; } = new();
        public HealthComponent HealthComponent { get; } = new();
        public PlayerInventory Inventory { get; } = new();
        public bool IsFriendly(PlayerPawn other) => Team != Team.Unassigned && Team == other.Team;
    }
    public class LightweightCombatBot : Component { public Team Team { get; set; } }
    public static class GameUtils
    {
        public static PlayerPawn GetPlayerFromComponent(Component component) => component as PlayerPawn;
        public static LightweightCombatBot GetLightweightBotFromComponent(Component component) => component as LightweightCombatBot;
        public static IEnumerable<Client> GetPlayers(Team team) => Array.Empty<Client>();
    }
    public class TestArmor : ArmorComponent { public void TickForTest() => base.OnUpdate(); }
    public class HealthComponent { public LifeState State { get; set; } }
    public class EquipmentResource
    {
        public static HashSet<EquipmentResource> All { get; } = new();
        public bool IsValid { get; set; } = true;
        public bool IsPurchasable { get; set; } = true;
        public bool IsWip { get; set; }
        public int Price { get; set; }
        public int KillReward { get; set; } = 300;
        public Team Team { get; set; }
        public string ResourcePath { get; set; }
        public string Name { get; set; }
        public EquipmentSlot Slot { get; set; } = EquipmentSlot.Secondary;
        public GameObject MainPrefab { get; set; } = new();
        public bool IsPurchasableForTeam(Team team) => Team == Team.Unassigned || Team == team;
    }
    public class Equipment : Component { public EquipmentResource Resource { get; set; } }
    public class PlayerInventory
    {
        private readonly List<Equipment> _held = new();
        public bool HasDefuseKit { get; set; }
        public bool FailNextGrant { get; set; }
        public bool LastAppliedSavedAttachments { get; private set; }
        public bool Has(EquipmentResource resource) => _held.Any(x => x.Resource == resource);
        public Equipment Give(EquipmentResource resource, bool makeActive, bool applySavedAttachments)
        {
            LastAppliedSavedAttachments = applySavedAttachments;
            if (FailNextGrant) { FailNextGrant = false; return null; }
            _held.RemoveAll(x => x.Resource.Slot == resource.Slot);
            var equipment = new Equipment { Resource = resource };
            _held.Add(equipment);
            return equipment;
        }
    }
}
namespace Facepunch.UI
{
    public class TacticalBuyMenu
    {
        public static TacticalBuyMenu Instance { get; } = new();
        public static string GearName(TacticalGear gear) => gear.ToString();
        public void PurchaseFinished(bool success, string item) { }
    }
}
