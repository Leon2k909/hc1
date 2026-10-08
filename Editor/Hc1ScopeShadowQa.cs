using Editor;
using Sandbox;
using Facepunch;
using Facepunch.UI;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

/// <summary>Render the production scope shadow through the native UI painter without changing a match.</summary>
public static class Hc1ScopeShadowQa
{
	[ConCmd( "hc1_scope_shadow_qa" )]
	public static void Render()
	{
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/scope-shadow" );
		Directory.CreateDirectory( folder );
		var states = new (string Name, Vector2 Eye, float Relief)[]
		{
			("aligned", Vector2.Zero, 0f),
			("turn-right", new( .3f, 0f ), 0f),
			("turn-left", new( -.3f, 0f ), 0f),
			("recoil", new( .05f, -.24f ), .12f),
			("eye-relief", Vector2.Zero, .7f),
			("off-axis", new( 1.25f, .2f ), 0f)
		};
		using var target = Texture.CreateRenderTarget( "scope_shadow_qa", ImageFormat.RGBA8888, new Vector2( 1536, 1024 ) );
		var background = OpticZoom.LensTexture ?? Texture.Load( "materials/railhead/rw_sandstone_color.png" );
		var report = new List<string>();
		using ( var painter = Painter.Begin( target ) )
		{
			painter.Clear( new Color( .035f, .04f, .045f ) );
			for ( int i = 0; i < states.Length; i++ )
			{
				var state = states[i];
				var box = new Rect( (i % 3) * 512f + 32f, (i / 3) * 512f + 32f, 448f, 448f );
				var eyeBox = ScopeEyeBox.Calculate( state.Eye, state.Relief, 6f );
				using ( painter.Scope() )
				{
					painter.Clip( box, 224f );
					painter.Texture( background, box );
					painter.Fill = new Color( 1f, .08f, .015f );
					painter.Circle( box.Center, 3f );
					ScopeShadow.Paint( painter, box, eyeBox );
				}
				report.Add( $"{state.Name}: offset={eyeBox.Offset}, aperture={eyeBox.Radius:F3}, blackout={eyeBox.Blackout:F3}" );
			}
		}
		using ( var bitmap = target.GetBitmap() )
			File.WriteAllBytes( Path.Combine( folder, "native-preview.png" ), bitmap.ToPng() );

		// White behind the production shadow makes black occlusion measurable, including over a bright reticle.
		using var samples = Texture.CreateRenderTarget( "scope_shadow_samples", ImageFormat.RGBA8888, new Vector2( 1024, 256 ) );
		using ( var painter = Painter.Begin( samples ) )
		{
			painter.Clear( Color.White );
			for ( int i = 0; i < 4; i++ )
			{
				var state = states[i == 3 ? 5 : i];
				var box = new Rect( i * 256f, 0f, 256f, 256f );
				ScopeShadow.Paint( painter, box, ScopeEyeBox.Calculate( state.Eye, state.Relief, 6f ) );
			}
		}
		using ( var bitmap = samples.GetBitmap() )
		{
			float Bright( int x, int y ) { var c = bitmap.GetPixel( x, y ); return (c.r + c.g + c.b) / 3f; }
			Require( Bright( 128, 128 ) > .98f, "aligned centre stays clear" );
			Require( Bright( 294, 128 ) < .02f && Bright( 474, 128 ) > .9f, "turn right produces an opaque left crescent" );
			Require( Bright( 730, 128 ) < .02f && Bright( 550, 128 ) > .9f, "turn left produces an opaque right crescent" );
			Require( Bright( 896, 128 ) < .02f, "leaving the exit pupil blacks out the centre and reticle" );
			File.WriteAllBytes( Path.Combine( folder, "native-samples.png" ), bitmap.ToPng() );
		}
		Require( ScopeEyeBox.Calculate( new( .3f, 0f ), 0f, 6f ).Offset.Length > ScopeEyeBox.Calculate( new( .3f, 0f ), 0f, 2f ).Offset.Length,
			"higher magnification has a smaller eye box" );
		File.WriteAllLines( Path.Combine( folder, "validation.txt" ), report );
		Log.Info( "Scope shadow native QA passed" );

		void Require( bool ok, string message )
		{
			report.Add( $"{(ok ? "PASS" : "FAIL")}: {message}" );
			if ( !ok ) throw new Exception( "Scope shadow QA: " + message );
		}
	}
}
