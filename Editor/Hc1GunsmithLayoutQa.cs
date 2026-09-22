using Editor;
using Sandbox;
using Sandbox.UI;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Threading.Tasks;
using Label = Sandbox.UI.Label;

public static class Hc1GunsmithLayoutQa
{
    [ConCmd( "hc1_gunsmith_restore_part" )]
    public static void RestorePart( string weaponPath, string partPath )
    {
        var weapon = ResourceLibrary.GetAll<EquipmentResource>().Single( r => r.ResourcePath == weaponPath );
        var part = ResourceLibrary.GetAll<GunsmithPart>().Single( r => r.ResourcePath == partPath );
        GunsmithLoadoutManager.SetAttachment( weapon, part.Category, part );
        var scene = Game.ActiveScene;
        if ( scene.IsValid() )
        {
            using var scope = scene.Push();
            foreach ( var system in scene.GetAllComponents<GunsmithSystem>().Where( s => s.Equipment == weapon ) )
                system.ApplyPreviewAttachments( weapon );
        }
        if ( !GunsmithLoadoutManager.HasAttachment( weapon, part ) ) throw new Exception( "Could not restore attachment" );
        Log.Info( $"GUNSMITH_LAYOUT restored {weapon.Name}: {part.Name}" );
    }

    [ConCmd( "hc1_gunsmith_layout" )]
    public static void Run( string action = "capture", int width = 1920, int height = 1080 )
    {
        var scene = Game.ActiveScene;
        if ( !scene.IsValid() ) return;
        using var scope = scene.Push();
        var root = scene.GetAllComponents<GunsmithPanel>().FirstOrDefault();
        if ( !root.IsValid() ) { Log.Warning( "Gunsmith is not open" ); return; }
        var browser = Descendants( root.Panel ).OfType<GunsmithAttachmentBrowser>().FirstOrDefault();
        var folder = Path.Combine( Project.Current.GetRootPath(), "Sources/UI/qa/gunsmith-layout" );
        Directory.CreateDirectory( folder );
        if ( action.StartsWith( "slot-" ) )
        {
            var category = action.Substring( 5 ).ToUpperInvariant();
            var slot = Descendants( root.Panel ).FirstOrDefault( p => p.HasClass( "attachment-slot" ) && Descendants( p ).OfType<Label>().Any( l => l.Text == category ) );
            if ( slot is null ) throw new Exception( $"Slot missing: {category}" );
            slot.CreateEvent( "onclick" );
        }
        if ( action == "done" ) Descendants( root.Panel ).First( p => p.HasClass( "drawer-close" ) ).CreateEvent( "onclick" );
        if ( action == "loadout" ) Descendants( root.Panel ).First( p => p.HasClass( "gs-armory-tab" ) ).CreateEvent( "onclick" );
        if ( action == "tuning" ) Descendants( root.Panel ).First( p => p.HasClass( "gs-tuning-btn" ) ).CreateEvent( "onclick" );
        if ( action == "tuning-done" ) Descendants( root.Panel ).First( p => p.HasClass( "gs-tuning-heading" ) ).Children.Last().CreateEvent( "onclick" );
        if ( action.StartsWith( "option-" ) )
            Descendants( root.Panel ).First( p => p.HasClass( "attachment-option" ) && Descendants( p ).OfType<Label>().Any( l => l.HasClass( "option-name" ) && l.Text == action.Substring( 7 ) ) ).CreateEvent( "onclick" );
        if ( action is "customize" or "build" )
        {
            var text = action == "build" ? "BUILD" : "CUSTOM";
            Descendants( root.Panel ).First( p => p.HasClass( "gs-mode-tab" ) && Descendants( p ).OfType<Label>().Any( l => l.Text.StartsWith( text ) ) ).CreateEvent( "onclick" );
        }
        if ( action == "check" ) { _ = Check( browser, folder ); return; }
        var lines = Descendants( root.Panel )
            .Where( p => p.HasClass( "attachment-slot" ) || p.HasClass( "attachment-option" ) || p.HasClass( "attachment-drawer" ) || p.HasClass( "weapon-browser" ) || p.HasClass( "gs-bottom" ) )
            .Select( p => $"{p.Classes}: {p.Box.Rect}; {string.Join( " / ", Descendants( p ).OfType<Label>().Select( l => l.Text ) )}" );
        File.WriteAllLines( Path.Combine( folder, $"{action}.txt" ), lines );
        using var bitmap = new Bitmap( width.Clamp( 640, 3840 ), height.Clamp( 480, 2160 ) );
        scene.Camera.RenderToBitmap( bitmap, true );
        File.WriteAllBytes( Path.Combine( folder, $"{action}.png" ), bitmap.ToPng() );
        Log.Info( $"GUNSMITH_LAYOUT {action} captured" );
    }

    private static async Task Check( GunsmithAttachmentBrowser browser, string folder )
    {
        var scene = browser.Weapon.Scene;
        var point = browser.SelectedPoint;
        if ( !point.IsValid() ) throw new Exception( "Open a slot before checking the tray" );
        var original = point.CurrentPart;
        try
        {
            string name;
            using ( scene.Push() )
            {
                var option = Descendants( browser ).Where( p => p.HasClass( "attachment-option" ) ).Skip( 1 ).First( p => !p.HasClass( "locked" ) );
                name = Descendants( option ).OfType<Label>().First( l => l.HasClass( "option-name" ) ).Text;
                option.CreateEvent( "onclick" );
            }
            await Task.Delay( 250 );
            using ( scene.Push() )
            {
                var found = GunsmithLoadoutManager.TryGetAttachment( browser.Weapon.Resource, point.Category, out var saved );
                if ( point.CurrentPart?.Name != name || !found || saved != point.CurrentPart )
                    throw new Exception( $"Equip failed: wanted {name}, preview={point.CurrentPart?.Name}, saved={saved?.Name}" );
                Descendants( browser ).First( p => p.HasClass( "attachment-option" ) ).CreateEvent( "onclick" );
            }
            await Task.Delay( 250 );
            using ( scene.Push() )
            {
                GunsmithLoadoutManager.TryGetAttachment( browser.Weapon.Resource, point.Category, out var saved );
                if ( point.CurrentPart is not null || saved is not null ) throw new Exception( "Standard did not remove the attachment" );
                var slots = Descendants( browser ).Where( p => p.HasClass( "attachment-slot" ) ).ToList();
                if ( slots.Any( p => p.Box.Rect.Height * p.ScaleFromScreen < 90f || p.Box.Rect.Width * p.ScaleFromScreen < 150f ) )
                    throw new Exception( "Attachment hit targets too small" );
            }
            File.WriteAllText( Path.Combine( folder, "checks.txt" ), "PASS: visible card clicks equip and save; Standard removes and saves; original attachment restored; attachment targets at least 150 x 90 panel units." );
        }
        catch ( Exception ex )
        {
            File.WriteAllText( Path.Combine( folder, "checks.txt" ), $"FAIL: {ex.Message}" );
        }
        finally
        {
            using ( scene.Push() )
            {
                GunsmithLoadoutManager.SetAttachment( browser.Weapon.Resource, point.Category, original );
                GunsmithLoadoutManager.ApplyAttachments( browser.Weapon.Resource, browser.Weapon.GameObject );
            }
        }
    }

    private static IEnumerable<Panel> Descendants( Panel panel )
    {
        yield return panel;
        foreach ( var child in panel.Children )
        foreach ( var descendant in Descendants( child ) ) yield return descendant;
    }
}
