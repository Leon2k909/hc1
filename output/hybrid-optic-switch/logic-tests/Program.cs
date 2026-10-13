using Facepunch;
using Facepunch.Gunsmith;
using System.Text.Json;

// Run the production Equipment.Optics.cs with stand-ins for the engine's input,
// ownership and attachment APIs. This does not exercise native rendering/networking.
var checks = 0;
void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
    checks++;
}
bool Near(float a, float b) => MathF.Abs(a-b) < .0001f;
Vector3 Vector(JsonElement data, string key)
{
    var v = data.GetProperty(key).GetString().Split(',').Select(float.Parse).ToArray();
    return new(v[0], v[1], v[2]);
}

var root = new DirectoryInfo(AppContext.BaseDirectory);
while (!File.Exists(Path.Combine(root.FullName, "ProjectSettings/Input.config")))
    root = root.Parent ?? throw new Exception("Cannot locate project root");
var assets = Path.Combine(root.FullName, "Assets/gunsmith");
foreach (var path in Directory.EnumerateFiles(assets, "*.gnsmth", SearchOption.AllDirectories))
{
    using var data = JsonDocument.Parse(File.ReadAllText(path));
    var j = data.RootElement;
    if (!j.TryGetProperty("HasAlternateSight", out var alternate) || !alternate.GetBoolean()) continue;
    var part = new GunsmithPart {
        OverrideAimOffset = true, HasAlternateSight = true,
        OpticMagnification = j.GetProperty("OpticMagnification").GetSingle(),
        OpticAimOffset = Vector(j, "OpticAimOffset"),
        AlternateSightAimOffset = Vector(j, "AlternateSightAimOffset"),
        AlternateSightMagnification = j.GetProperty("AlternateSightMagnification").GetSingle()
    };
    var gun = Equipment.Make(part);
    Require(!gun.UsingAlternateSight && Near(gun.GetOpticMagnification(part), 3), "scope defaults to 3x");
    var scopeFov = gun.GetAimFovOffset(85);
    Input.Press = true;
    gun.Tick();
    Require(gun.UsingAlternateSight && Near(gun.GetOpticMagnification(part), 1), "T selects the unmagnified sight");
    var aim = gun.GetOpticAimOffset(part);
    Require(aim == part.OpticAimOffset + part.AlternateSightAimOffset, "ADS moves to the second glass");
    Require(Near(gun.GetAimFovOffset(85), -5) && gun.GetAimFovOffset(85) > scopeFov, "reflex removes scope camera zoom");
    Input.Press = false;
    gun.Tick();
    Require(gun.UsingAlternateSight, "holding/no new press does not repeat the toggle");
    Input.Press = true;
    gun.Tick();
    Require(!gun.UsingAlternateSight && Near(gun.GetAimFovOffset(85), scopeFov), "second T restores scope and FOV");
    gun.Tick();
    Require(gun.UsingAlternateSight, "third T returns to reflex");
    Input.Press = false;
    gun.IsDeployed = false;
    gun.Tick();
    gun.IsDeployed = true;
    gun.Tick();
    Require(gun.UsingAlternateSight, "selection stays with the weapon across holstering");

    // Input is ignored for every menu/ownership/death/reload state independently.
    Action[] block = [() => GameUtils.MenuOpen = true, () => GameUtils.StudioOpen = true,
        () => Input.Suppressed = true, () => Input.EscapePressed = true,
        () => gun.Owner.IsFrozen = true, () => gun.Owner.IsLocallyControlled = false,
        () => gun.Owner.HealthComponent.State = LifeState.Dead, () => gun.IsDeployed = false,
        () => gun.Owner.CurrentEquipment = null, () => gun.Tags.Add("reloading"),
        () => gun.ViewModel.IsInspecting = true];
    foreach (var apply in block)
    {
        Input.Reset(); GameUtils.Reset(); gun.Owner.IsFrozen = false; gun.Owner.IsLocallyControlled = true;
        gun.Owner.HealthComponent.State = LifeState.Alive; gun.IsDeployed = true;
        gun.Owner.CurrentEquipment = gun; gun.Tags.Clear(); gun.ViewModel.IsInspecting = false;
        apply(); Input.Press = true; gun.Tick();
        Require(gun.UsingAlternateSight, "blocked input does not change sights");
    }
    Input.Reset(); GameUtils.Reset(); gun.ViewModel.IsInspecting = false;
    gun.Point.CurrentPart = new GunsmithPart { OverrideAimOffset=true, OpticMagnification=6 };
    gun.Tick();
    Require(!gun.UsingAlternateSight, "changing the fitted optic clears alternate mode");
    Require(!gun.SwitchOpticSight(), "normal scopes cannot select a phantom reflex");
    Console.WriteLine($"PASS {Path.GetFileName(path)}");
}
Input.Reset(); GameUtils.Reset();
var bare = Equipment.Make(null);
Input.Press = true; bare.Tick();
Require(!bare.SwitchOpticSight() && !bare.UsingAlternateSight, "no optic safely ignores the switch");
Console.WriteLine($"PASS: {checks} production sight-selection checks (engine APIs stubbed; native rendering not tested)");

namespace Facepunch
{
    public sealed class SyncAttribute : Attribute { }
    public enum FindMode { EverythingInSelfAndDescendants }
    public enum LifeState { Alive, Dead }
    public readonly record struct Vector3(float x, float y, float z)
    {
        public static Vector3 Zero => default;
        public static Vector3 operator +(Vector3 a, Vector3 b) => new(a.x+b.x,a.y+b.y,a.z+b.z);
    }
    public readonly record struct Angles(float Pitch, float Yaw, float Roll)
    {
        public static Angles Zero => default;
        public static Angles operator +(Angles a, Angles b) => new(a.Pitch+b.Pitch,a.Yaw+b.Yaw,a.Roll+b.Roll);
    }
    public static class Extensions
    {
        public static bool IsValid(this object o) => o is not null;
        public static float Clamp(this float value, float lo, float hi) => Math.Clamp(value,lo,hi);
    }
    public static class Input
    {
        public static bool Press, Suppressed, EscapePressed;
        public static bool Pressed(string action) => action == "SwitchOptic" && Press;
        public static void Reset() { Press=Suppressed=EscapePressed=false; }
    }
    public static class GameUtils
    {
        public static bool MenuOpen, StudioOpen;
        public static bool IsInteractiveMouseUiOpen() => MenuOpen;
        public static bool IsGunsmithStudioOpen() => StudioOpen;
        public static void Reset() { MenuOpen=StudioOpen=false; }
    }
    public sealed class Components
    {
        public readonly List<object> Items = [];
        public IEnumerable<T> GetAll<T>(FindMode mode) => Items.OfType<T>();
    }
    public sealed class ViewModel
    {
        public Components Components { get; } = new();
        public bool IsInspecting;
    }
    public sealed class GameObject { public Components Components { get; } = new(); }
    public sealed class EquipmentResource { public GameObject ViewModelPrefab; }
    public sealed class Health { public LifeState State; }
    public sealed class Player
    {
        public bool IsLocallyControlled=true, IsFrozen;
        public Health HealthComponent = new();
        public Equipment CurrentEquipment;
    }
    public sealed partial class Equipment
    {
        public bool IsDeployed=true, ApplySavedAttachments;
        public EquipmentResource Resource;
        public ViewModel ViewModel = new();
        public Player Owner = new();
        public readonly HashSet<string> Tags = [];
        public GunsmithAttachmentPoint Point;
        public float AimFovOffset = -5;
        public bool HasTag(string tag) => Tags.Contains(tag);
        public void Tick() => UpdateOpticInput();
        public static Equipment Make(GunsmithPart optic)
        {
            var gun = new Equipment(); gun.Owner.CurrentEquipment = gun;
            gun.Point = new() { Category=GunsmithPartType.Optic, CurrentPart=optic };
            gun.ViewModel.Components.Items.Add(gun.Point); return gun;
        }
    }
    public static class OpticZoom { public const float ViewMagnification=1.2f; }
    public sealed class Settings { public bool IndependentAdsFov; }
    public static class GameSettingsSystem { public static Settings Current = new(); }
}
namespace Facepunch.Gunsmith
{
    public enum GunsmithPartType { Optic }
    public sealed class GunsmithPart
    {
        public bool OverrideAimOffset, HasAlternateSight;
        public Vector3 OpticAimOffset, AlternateSightAimOffset;
        public Angles OpticAimAngles, AlternateSightAimAngles;
        public float OpticMagnification=1, AlternateSightMagnification=1;
    }
    public sealed class GunsmithAttachmentPoint { public GunsmithPartType Category; public GunsmithPart CurrentPart; }
    public static class GunsmithLoadoutManager
    {
        public static bool TryGetAttachment(EquipmentResource resource,GunsmithPartType kind,out GunsmithPart optic) { optic=null; return false; }
        public static float GetOpticZero(EquipmentResource resource,GunsmithPart part) => 0;
    }
    public static class OpticTuning { public static bool IsTunable(GunsmithPart part) => false; }
}
