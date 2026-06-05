using Facepunch.UI;

namespace Facepunch;

public partial class PlayerPawn
{
	/// <summary>
	/// Development: should bots follow the player's input?
	/// </summary>
	[ConVar( "hc1_bot_follow" )] public static bool BotFollowHostInput { get; set; }

	[DeveloperCommand( "-10 HP (head)", "Player" )]
	private static void Command_HurtTenHead()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;
		player.HealthComponent.TakeDamage( new DamageInfo( player as Component, 10, Hitbox: HitboxTags.Head ) );
	}


	[DeveloperCommand( "Toggle God", "Player" )]
	private static void Command_Add_Bot()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;

		player.HealthComponent.IsGodMode = !player.HealthComponent.IsGodMode;
	}


	[DeveloperCommand( "-10 HP (chest)", "Player" )]
	private static void Command_HurtTenChest()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;
		player.HealthComponent.TakeDamage( new DamageInfo( player as Component, 10, Hitbox: HitboxTags.Chest ) );
	}

	[DeveloperCommand( "Heal", "Player" )]
	private static void Command_Heal()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;
		player.HealthComponent.Health = player.HealthComponent.MaxHealth;
	}

	[DeveloperCommand( "Suicide", "Player" ), ConCmd( "kill" )]
	private static void Command_Suicide()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;
		Host_Suicide( player );
	}

	[DeveloperCommand( "Give $1k", "Player" )]
	private static void Command_GiveGrand()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;
		player.Client.GiveCash( 1000 );
	}


	[DeveloperCommand( "Give Scores", "Player" )]
	private static void Command_Scores()
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;
		player.Client.GetComponent<PlayerScore>().AddScore( 25, "Killed a player" );
	}

	[Rpc.Owner]
	private static void Host_Suicide( PlayerPawn pawn )
	{
		if ( !pawn.IsValid() )
			return;

		pawn.HealthComponent.TakeDamage( new( pawn, float.MaxValue ) );
	}

	[DeveloperCommand( "Switch Team", "Player" ), ConCmd( "switchteam" )]
	private static void Command_SwitchTeam()
	{
		var localClient = Client.Local;
		if ( !localClient.IsValid() ) return;

		var currentTeam = localClient.Team;
		var newTeam = currentTeam == Team.Terrorist ? Team.CounterTerrorist : Team.Terrorist;

		using ( Sandbox.Rpc.FilterInclude( Sandbox.Connection.Host ) )
		{
			AskToSwitchTeam( localClient.Id, (int)newTeam );
		}
	}

	[Rpc.Broadcast]
	private static void AskToSwitchTeam( Guid clientId, int teamVal )
	{
		var client = GameUtils.AllPlayers.FirstOrDefault( x => x.Id == clientId );
		if ( !client.IsValid() ) return;

		var team = (Team)teamVal;
		client.AssignTeam( team );

		if ( client.PlayerPawn.IsValid() )
		{
			client.PlayerPawn.HealthComponent.TakeDamage( new( client.PlayerPawn, float.MaxValue ) );
		}
	}
}
