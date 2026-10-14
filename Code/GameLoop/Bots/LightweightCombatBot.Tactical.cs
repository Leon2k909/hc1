using Sandbox.Events;

namespace Facepunch;

public sealed partial class LightweightBotManager :
	IGameEventHandler<KillEvent>,
	IGameEventHandler<TeamsSwappedEvent>,
	IGameEventHandler<BombDefusedEvent>
{
	private static bool HasTacticalEconomy => Networking.IsHost && TacticalEconomy.Current.IsValid();

	/// <summary>The bot's bank survives its pawn, just as a player's Client does.</summary>
	public int GetTacticalCash( LightweightCombatBot bot ) =>
		_roster.FirstOrDefault( x => x.Name == bot.BotName )?.TacticalCash ?? 0;

	private void PrepareTacticalLoadout( LightweightCombatBot bot, BotIdentity identity )
	{
		var mode = GameMode.Instance;
		identity.Weapon ??= mode.Get<DefaultEquipment>()?.GetLoadout( identity.Team )?.Equipment
			.FirstOrDefault( x => x.Slot == EquipmentSlot.Secondary )
			?? ResourceLibrary.Get<EquipmentResource>( identity.Team == Team.CounterTerrorist
				? "weapons/usp_sd/usp_sd.equip" : "weapons/usp/usp.equip" );
		// Tactical weapons have their factory parts; the ordinary bot roll must not grant a free suppressor.
		identity.Muzzle = null;

		var armor = bot.Components.GetOrCreate<ArmorComponent>();
		if ( mode.Get<EnableBuyMenu>()?.BuyMenuMode == BuyMenuMode.EnabledEverywhere )
		{
			// Keep a surviving primary. A bot that died starts with its team's pistol and buys within its bank.
			if ( identity.Weapon?.Slot != EquipmentSlot.Primary )
			{
				var automaticWeapons = LightweightCombatBot.WeaponPool().ToHashSet();
				var affordable = TacticalEconomy.Catalog( identity.Team )
					.Where( x => automaticWeapons.Contains( x ) && x.Price <= identity.TacticalCash ).ToList();
				if ( affordable.Count > 0 )
				{
					identity.Weapon = Game.Random.FromList( affordable );
					identity.TacticalCash -= identity.Weapon.Price;
				}
			}

			if ( armor.ArmorEnabled && identity.TacticalArmor < armor.MaxArmor
				&& identity.TacticalCash >= TacticalEconomy.ArmorPrice )
			{
				identity.TacticalArmor = armor.MaxArmor;
				identity.TacticalCash -= TacticalEconomy.ArmorPrice;
			}
			if ( armor.HelmetsEnabled && identity.TacticalArmor > 0f && !identity.TacticalHelmet
				&& identity.TacticalCash >= TacticalEconomy.HelmetPrice )
			{
				identity.TacticalHelmet = true;
				identity.TacticalCash -= TacticalEconomy.HelmetPrice;
			}
		}

		bot.WeaponResource = identity.Weapon;
		bot.MuzzlePart = null;
		armor.Armor = identity.TacticalArmor;
		armor.HasHelmet = identity.TacticalHelmet;
		identity.TacticalEquipmentCleared = false;
	}

	/// <summary>Move survivors back to their spawns without granting back equipment lost on death.</summary>
	internal void SaveTacticalLoadouts()
	{
		if ( !HasTacticalEconomy ) return;
		foreach ( var bot in Bots )
		{
			var identity = _roster.FirstOrDefault( x => x.Name == bot.BotName );
			if ( identity is null || identity.TacticalEquipmentCleared ) continue;
			if ( !bot.IsAlive )
			{
				ClearTacticalLoadout( identity, true );
				continue;
			}
			var armor = bot.Components.Get<ArmorComponent>();
			identity.Weapon = bot.WeaponResource;
			identity.TacticalArmor = armor?.Armor ?? 0f;
			identity.TacticalHelmet = armor?.HasHelmet ?? false;
		}
	}

	internal void ResetTacticalCash( int value )
	{
		if ( !HasTacticalEconomy ) return;
		foreach ( var identity in _roster )
			identity.TacticalCash = Math.Clamp( value, 0, GameMode.Instance.MaxBalance );
	}

	internal void GiveTacticalTeamIncome( Team team, int value )
	{
		if ( !HasTacticalEconomy ) return;
		foreach ( var identity in _roster.Where( x => x.Team == team ) )
			GiveTacticalCash( identity, value );
	}

	private static void GiveTacticalCash( BotIdentity identity, int value ) =>
		identity.TacticalCash = Math.Clamp( identity.TacticalCash + value, 0, GameMode.Instance.MaxBalance );

	internal void ClearTacticalEquipment( bool clearProtection )
	{
		if ( !HasTacticalEconomy ) return;
		foreach ( var identity in _roster )
			ClearTacticalLoadout( identity, clearProtection );
	}

	private static void ClearTacticalLoadout( BotIdentity identity, bool clearProtection )
	{
		identity.Weapon = null;
		identity.Muzzle = null;
		identity.TacticalEquipmentCleared = true;
		if ( clearProtection )
		{
			identity.TacticalArmor = 0f;
			identity.TacticalHelmet = false;
		}
	}

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs ) => RecordTacticalKill( eventArgs );

	private void RecordTacticalKill( KillEvent eventArgs )
	{
		if ( !HasTacticalEconomy ) return;
		var damage = eventArgs.DamageInfo;
		var victimBot = GameUtils.GetLightweightBotFromComponent( damage.Victim );
		if ( victimBot.IsValid() && _roster.FirstOrDefault( x => x.Name == victimBot.BotName ) is { } victim )
			ClearTacticalLoadout( victim, true );

		var killerBot = GameUtils.GetLightweightBotFromComponent( damage.Attacker );
		if ( !killerBot.IsValid() || killerBot == victimBot
			|| (!victimBot.IsValid() && !GameUtils.GetPlayerFromComponent( damage.Victim ).IsValid()) ) return;
		var killer = _roster.FirstOrDefault( x => x.Name == killerBot.BotName );
		var rewards = GameMode.Instance.Get<KillRewards>();
		if ( killer is null || !rewards.IsValid() ) return;
		var friendly = killer.Team != Team.Unassigned && killer.Team == GameUtils.GetTeamFromComponent( damage.Victim );
		GiveTacticalCash( killer, friendly && !rewards.AllowFriendlyFire
			? -rewards.FriendlyFirePenalty : killerBot.WeaponResource?.KillReward ?? 0 );
	}

	void IGameEventHandler<TeamsSwappedEvent>.OnGameEvent( TeamsSwappedEvent eventArgs ) => SwapTacticalTeams();

	private void SwapTacticalTeams()
	{
		if ( !HasTacticalEconomy ) return;
		foreach ( var identity in _roster )
		{
			identity.Team = identity.Team == Team.Terrorist ? Team.CounterTerrorist : Team.Terrorist;
			identity.Outfit = null;
		}
	}

	void IGameEventHandler<BombDefusedEvent>.OnGameEvent( BombDefusedEvent eventArgs )
	{
		if ( GameMode.Instance?.Get<DefuseObjectiveRewards>() is { } rewards )
			GiveTacticalTeamIncome( Team.Terrorist, rewards.BombPlantTeamReward );
	}
}
