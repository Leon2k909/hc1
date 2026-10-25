namespace Sandbox.Events
{
    public interface IGameEventHandler<T> { void OnGameEvent(T value); }
    public record EquipmentDeployedEvent(Facepunch.Equipment Equipment);
}

namespace Facepunch
{
    public class PropertyAttribute : Attribute { }
    public class CategoryAttribute(string name) : Attribute { }
    public static class Validity { public static bool IsValid(this object value) => value is not null; }
    public class PlayerPawn { public bool IsLocallyControlled = true; public bool IsPipeClimbing; }
    public class TagSet
    {
        readonly HashSet<string> tags = new();
        public bool Has(string tag) => tags.Contains(tag);
        public void Set(string tag, bool state) { if (state) tags.Add(tag); else tags.Remove(tag); }
    }
    public class Equipment
    {
        public PlayerPawn Owner = new();
        public bool IsDeployed = true;
        public TagSet Tags = new();
        public bool HasTag(string tag) => Tags.Has(tag);
        public void SetTag(string tag, bool value) => Tags.Set(tag, value);
    }
    public abstract class EquipmentComponent
    {
        protected Equipment Equipment { get; set; }
        protected TagSet Tags => Equipment.Tags;
        protected virtual void OnFixedUpdate() { }
    }
    public static class GameUtils
    {
        public static bool GunsmithOpen;
        public static bool IsGunsmithStudioOpen() => GunsmithOpen;
    }
    public static class Input
    {
        public static bool Held, Press;
        public static bool Down(string action) => action.Equals("attack1", StringComparison.OrdinalIgnoreCase) && Held;
        public static bool Pressed(string action) => action.Equals("attack1", StringComparison.OrdinalIgnoreCase) && Press;
    }
    public enum FireMode { Semi, Automatic, Burst }
    public class Ammo { public bool HasAmmo = true; }
    public partial class Shootable : WeaponInputAction
    {
        public FireMode CurrentFireMode;
        public bool IsBurstFiring;
        public int BurstCount, BurstAmount = 3, Shots, Released, Pressed;
        public float TimeSinceBurstFinished = 100, TimeSinceShoot = 100, DryShootDelay = .2f, BurstEndDelay = .1f;
        public Ammo AmmoComponent = new();
        public Shootable(FireMode mode) { Equipment = new(); CurrentFireMode = mode; }
        public void Tick(bool held = false, bool press = false)
        {
            Input.Held = held; Input.Press = press;
            TimeSinceBurstFinished += .02f; TimeSinceShoot += .02f;
            OnFixedUpdate();
        }
        public void Deploy() => ResetInputState();
        public void QueueBurst() { IsBurstFiring = true; BurstCount = 1; }
        public bool CanShoot() => AmmoComponent.HasAmmo;
        public void CycleFireMode() { }
        public void DryShoot() { }
        public void Shoot() { Shots++; TimeSinceShoot = 0; if (CurrentFireMode == FireMode.Burst) IsBurstFiring = true; }
        protected override void OnInputDown() => Pressed++;
        protected override void OnInputUp() => Released++;
    }
}

namespace Facepunch.UI
{
    public static class ClassSelect { public static bool IsAnyOpen; }
    public static class TacticalBuyMenu { public static bool IsAnyOpen; }
    public static class ZombiesWorkbenchPanel { public static bool IsAnyOpen; }
}
