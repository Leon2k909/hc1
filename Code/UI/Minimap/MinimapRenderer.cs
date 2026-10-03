using System.IO;
using System.Linq;

namespace Facepunch;

public partial class MinimapRenderer : Component, Component.ExecuteInEditor
{
	[Property, Group( "Rendering" )] public Vector2 ExportResolution { get; set; } = new( 2048, 2048 );
	[Property, Group( "Rendering" )] public int Size { get; set; }

	private GameObject CameraGameObject;
	public CameraComponent Camera { get; set; }

	public Vector3 FromWorld( Vector3 worldPos )
	{
		// Define the center position and half size of the minimap area
		var origin = WorldPosition;
		var halfSize = Size * 0.5f;

		// Calculate the bounding box min and max coordinates
		var minX = origin.x - halfSize;
		var maxX = origin.x + halfSize;
		var minY = origin.y - halfSize;
		var maxY = origin.y + halfSize;

		// Normalize the world position within the bounding box
		var normalizedX = (worldPos.x - minX) / (maxX - minX);
		var normalizedY = (worldPos.y - minY) / (maxY - minY);

		// Map normalized coordinates to the minimap image resolution
		var minimapX = (1 - normalizedX).Clamp( 0, 1 );
		var minimapY = (1 - normalizedY).Clamp( 0, 1 ); // Invert Y to match top-left origin

		// Return the mapped coordinates
		return new Vector2(minimapY, minimapX);
	}

	/// <summary>
	/// Where <paramref name="worldPos"/> is on the radar, from its centre: 1 is its edge. Held to the edge unless
	/// <paramref name="clamp"/> is false (something drawn round a point, like the Skirmish arena's ring).
	/// </summary>
	public Vector3 FromWorldRadar( Vector3 worldPos, Vector3 playerPos, float yaw, float zoom, bool clamp = true )
	{
		// Get relative world position
		Vector3 dir = (playerPos - worldPos);

		// Scale to minimap space
		dir /= ( Size / 2 ) / zoom;

		// Apply look rotation
		float cosYaw = MathF.Cos( MathX.DegreeToRadian( -yaw ) );
		float sinYaw = MathF.Sin( MathX.DegreeToRadian( -yaw ) );
		Vector3 rotatedDirection = new Vector3(
			dir.x * cosYaw - dir.y * sinYaw,
			dir.x * sinYaw + dir.y * cosYaw
		);

		// Limit to radar bounds (so we stick to the edge)
		var position = new Vector3( rotatedDirection.y, rotatedDirection.x );
		return clamp ? position.ClampLength( 1 ) : position;
	}

	protected override void DrawGizmos()
	{
		if ( !Facepunch.Preferences.ShowVolumes )
			return;

		Gizmo.Draw.Color = Color.Blue.WithAlpha( 0.8f );
		Gizmo.Draw.LineBBox( BBox.FromPositionAndSize( Vector3.Zero, Size ) );

		if ( Gizmo.IsSelected )
		{
			Gizmo.Draw.Color = Color.Blue.WithAlpha( 0.3f );
			Gizmo.Draw.SolidBox( BBox.FromPositionAndSize( Vector3.Zero, Size ) );
		}
    }


	[Button( "Generate Minimap" )]
	public void GenerateMinimap()
	{
		if ( Game.IsPlaying )
		{
			Log.Warning( "Minimap generation is editor-only." );
			return;
		}

		GetOrCreateCamera();

		var width = Math.Max( 64, (int)ExportResolution.x );
		var height = Math.Max( 64, (int)ExportResolution.y );
		var renderTarget = Texture.CreateRenderTarget( $"minimap_{GameObject.Id}", ImageFormat.RGBA8888, new Vector2( width, height ) );
		Camera.RenderToTexture( renderTarget );

		var pixels = renderTarget.GetPixels();
		if ( pixels == null || pixels.Length != width * height )
		{
			Log.Error( $"Minimap generation failed: expected {width * height} pixels, got {pixels?.Length ?? 0}." );
			return;
		}

		var sceneName = SanitizeFileName( Game.ActiveScene?.Name ?? GameObject.Name ?? "scene" ).ToLowerInvariant();
		if ( string.IsNullOrWhiteSpace( sceneName ) )
			sceneName = "scene";

		var relativePath = $"ui/minimaps/minimap_{sceneName}.tga";
		FileSystem.Data.CreateDirectory( "ui/minimaps" );
		WriteTga( relativePath, pixels, width, height );
		CurrentMinimapPath = relativePath;

		Log.Info( $"Generated minimap: {CurrentMinimapPath}" );
	}

	private static string SanitizeFileName( string value )
	{
		return new string( value
			.Select( c => char.IsLetterOrDigit( c ) ? c : '_' )
			.ToArray() );
	}

	private static void WriteTga( string path, Color32[] pixels, int width, int height )
	{
		using var stream = FileSystem.Data.OpenWrite( path );

		// Uncompressed true-color TGA, top-left origin, 32bpp.
		stream.WriteByte( 0 );
		stream.WriteByte( 0 );
		stream.WriteByte( 2 );
		WriteUInt16LittleEndian( stream, 0 );
		WriteUInt16LittleEndian( stream, 0 );
		stream.WriteByte( 0 );
		WriteUInt16LittleEndian( stream, 0 );
		WriteUInt16LittleEndian( stream, 0 );
		WriteUInt16LittleEndian( stream, (ushort)width );
		WriteUInt16LittleEndian( stream, (ushort)height );
		stream.WriteByte( 32 );
		stream.WriteByte( 0x28 );

		for ( var y = 0; y < height; y++ )
		{
			var srcY = height - 1 - y;
			for ( var x = 0; x < width; x++ )
			{
				var c = pixels[srcY * width + x];
				stream.WriteByte( c.b );
				stream.WriteByte( c.g );
				stream.WriteByte( c.r );
				stream.WriteByte( c.a );
			}
		}
	}

	private static void WriteUInt16LittleEndian( Stream stream, ushort value )
	{
		stream.WriteByte( (byte)(value & 0xFF) );
		stream.WriteByte( (byte)(value >> 8) );
	}

	void GetOrCreateCamera()
	{
		if ( CameraGameObject.IsValid() )
			CameraGameObject.Destroy();

		if ( Camera.IsValid() )
		 Camera.Destroy();

        CameraGameObject = new GameObject();
		CameraGameObject.Parent = GameObject;
		CameraGameObject.Flags = GameObjectFlags.NotSaved | GameObjectFlags.Hidden;

		Camera = CameraGameObject.Components.Create<CameraComponent>();
		Camera.RenderExcludeTags.Add( "skybox" );
		Camera.Flags = ComponentFlags.NotSaved;
		// Only a capture camera: never the scene's main camera, which other components take for the view
		Camera.IsMainCamera = false;
		Camera.Orthographic = true;
		Camera.OrthographicHeight = Size;
		Camera.BackgroundColor = Color.Transparent;
    }

	protected override void OnUpdate()
	{
        if ( Game.IsPlaying )
		{
			CameraGameObject?.Destroy();
			return;
		}

		if ( !CameraGameObject.IsValid() )
		{
			GetOrCreateCamera();
        }

        Camera.WorldPosition = WorldPosition + Vector3.Up * Size;
        Camera.WorldRotation = Rotation.From( 90, 0, 0 );
        Camera.OrthographicHeight = Size;
	}
}
