using Sandbox;
using Sandbox.Network;
using Sandbox.UI;
using Sandbox.UI.Navigation;
using Facepunch;
using Facepunch.UI;
using System;
using System.Collections.Generic;
using System.Linq;
using GameMode = Facepunch.GameMode;
using Label = Sandbox.UI.Label;

/// <summary>Exercises the custom game setup (CreateLobbyPage) through its actual controls, then checks the loaded session.</summary>
public static class Hc1PrivateMatchQa
{
    [ConCmd( "hc1_private_ui" )]
    public static async void Run( string action = "options" )
    {
        try
        {
            if ( action == "check" )
            {
                Require( GameMode.Instance.IsValid() && GameMode.Instance.Ident == "tdm", "selected TDM loaded" );
                Require( CustomGameSettings.Current is { PlayerLimit: 4, FillWithBots: false }, "selected settings survived scene load" );
                Require( Networking.IsActive && Networking.IsHost && Networking.MaxPlayers == 4, "custom game host has four player slots" );
                Require( Networking.ServerName?.EndsWith( "Custom Game" ) == true, "custom game lobby config was applied" );
                Require( !Game.ActiveScene.GetAllComponents<PregameLobbyManager>().Any(), "legacy pregame scene is bypassed" );
                Require( !Game.ActiveScene.GetAllComponents<LightweightCombatBot>().Any(), "bot fill off produced no bots" );
                Require( Client.Local.IsValid(), "local player connected successfully" );
                Log.Info( "PRIVATE_QA PASS: Start button loaded TDM, four slots, the custom game lobby and no bots; local client connected." );
                return;
            }

            var root = MainMenuRoot.Instance;
            Require( root.IsValid(), "main menu is open" );
            using var scope = Game.ActiveScene.Push();
            if ( action == "royale" )
            {
                root.Navigate( "/" );
                await GameTask.DelaySeconds( 0.2f );
                var rail = Descendants( root ).OfType<HubModeRail>().First();
                Descendants( rail ).First( p => p.HasClass( "rail-card" ) && p.HasClass( "battle-royale" ) ).CreateEvent( "onclick" );
                return;
            }
            if ( action == "start" )
            {
                var page = Descendants( root ).OfType<CreateLobbyPage>().First();
                Descendants( page ).First( p => p.HasClass( "cl-start" ) ).CreateEvent( "onclick" );
                return;
            }

            root.Navigate( "/new" );
            await GameTask.DelaySeconds( 0.2f );
            var setup = Descendants( root ).OfType<CreateLobbyPage>().First();
            var scene = Game.ActiveScene;
            Click( setup, "1V1 SKIRMISH" );
            await GameTask.DelaySeconds( 0.1f );
            Require( setup.PlayerLimit == 2, "1v1 limits the lobby to two players" );
            Click( setup, "TDM" );
            await GameTask.DelaySeconds( 0.1f );
            Click( setup, "4" );
            await GameTask.DelaySeconds( 0.1f );
            Click( setup, "OFF" );
            await GameTask.DelaySeconds( 0.1f );
            Click( setup, "FRIENDS" );
            await GameTask.DelaySeconds( 0.1f );
            Require( setup.Privacy == LobbyPrivacy.FriendsOnly, "friends option is selectable" );
            Click( setup, "PUBLIC" );
            await GameTask.DelaySeconds( 0.1f );
            Require( setup.Privacy == LobbyPrivacy.Public, "public option is selectable" );
            Click( setup, "INVITE ONLY" );
            await GameTask.DelaySeconds( 0.1f );
            Require( setup.SelectedMode?.Ident == "tdm" && setup.PlayerLimit == 4 && !setup.FillWithBots && setup.Privacy == LobbyPrivacy.Private, "summary reflects chosen settings" );
            Require( Game.ActiveScene == scene && CustomGameSettings.Current is null, "editing options did not start a match" );
            Log.Info( "PRIVATE_QA PASS: mode, mode capacity, four slots, bot fill, who can join (invite only, friends, public); setup stays in menu until Start." );
        }
        catch ( Exception e ) { Log.Warning( $"PRIVATE_QA FAIL: {e}" ); }
    }

    private static void Click( Panel page, string text ) => Descendants( page )
        .First( p => p.HasClass( "cl-option" ) && Descendants( p ).OfType<Label>().Any( label => label.Text == text ) )
        .CreateEvent( "onclick" );

    private static IEnumerable<Panel> Descendants( Panel panel )
    {
        yield return panel;
        foreach ( var child in panel.Children )
        foreach ( var descendant in Descendants( child ) ) yield return descendant;
    }

    private static void Require( bool value, string message )
    {
        if ( !value ) throw new Exception( message );
    }
}
