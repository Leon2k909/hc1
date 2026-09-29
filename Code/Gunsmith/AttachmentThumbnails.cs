namespace Facepunch.Gunsmith;

/// <summary>
/// Pictures of the attachments for the gunsmith's parts list, like CoD's: each part is drawn once from the gun's right
/// side (muzzle to the right) in a scene of its own, cut out of its background, turned light grey and kept for the
/// session. Nothing is written to disk. A part with a prefab is drawn from the prefab's meshes, turned the way its mount
/// turns it on the gun; a bodygroup part (the Kastovs' stocks, grips and magazines) from the gun's own model with only
/// that part's bodygroup choices showing. Set up like the editor's asset previews (AssetPreview.cs).
/// </summary>
public static class AttachmentThumbnails
{
	public const int Width = 256;
	public const int Height = 160;

	/// <summary> Drawn at twice the size and scaled down, for smooth edges. </summary>
	private const int Supersample = 2;

	/// <summary> The first look, which finds where the part is in a frame around its bounds. </summary>
	private const int ProbeWidth = 256;
	private const int ProbeHeight = 160;

	/// <summary> The share of the picture left empty on each side of the part. </summary>
	private const float Padding = 0.05f;

	/// <summary> The camera: on the gun's right, a little above and in front of the part. </summary>
	private static readonly Rotation View = Rotation.From( 12f, 100f, 0f );

	/// <summary> The first look's background, a colour no part is. </summary>
	private static readonly Color ProbeBackground = new( 1f, 0f, 1f );

	private static readonly Dictionary<string, Texture> _pictures = new( StringComparer.OrdinalIgnoreCase );
	private static readonly Queue<(string Key, GunsmithPart Part, Model Weapon)> _queue = new();
	private static readonly HashSet<string> _queued = new( StringComparer.OrdinalIgnoreCase );

	private static Scene _studio;
	private static CameraComponent _camera;

	/// <summary> Goes up whenever a picture is finished, for panels to rebuild with it. </summary>
	public static int Version { get; private set; }

	/// <summary>
	/// The picture of <paramref name="part"/> as fitted to the gun with <paramref name="weapon"/> for its model, or null
	/// while it's still to be drawn (see <see cref="Pump"/>) or when there's nothing to show.
	/// </summary>
	public static Texture Get( GunsmithPart part, Model weapon )
	{
		if ( !part.IsValid() || !AttachmentUnlocks.IsAttachment( part.Category ) )
			return null;

		var key = $"{part.ResourcePath}|{weapon?.Name}";
		if ( _pictures.TryGetValue( key, out var texture ) )
			return texture;

		if ( _queued.Add( key ) )
			_queue.Enqueue( (key, part, weapon) );
		return null;
	}

	/// <summary> Draws up to <paramref name="count"/> of the pictures asked for. The panels showing them call it each frame. </summary>
	public static void Pump( int count = 1 )
	{
		for ( var i = 0; i < count && _queue.Count > 0; i++ )
		{
			var (key, part, weapon) = _queue.Dequeue();
			_queued.Remove( key );

			Texture texture = null;
			Bitmap bitmap = null;
			try
			{
				bitmap = Render( part, weapon );
				texture = bitmap?.ToTexture( true );
			}
			catch ( Exception e )
			{
				Log.Warning( $"AttachmentThumbnails: couldn't draw {part?.ResourcePath}: {e.Message}" );
			}
			finally
			{
				bitmap?.Dispose();
			}

			_pictures[key] = texture;
			Version++;
		}
	}

	/// <summary> Draws <paramref name="part"/> now: a picture with a transparent background, or null if nothing shows. </summary>
	public static Bitmap Render( GunsmithPart part, Model weapon )
	{
		if ( !part.IsValid() || !EnsureStudio() )
			return null;

		using var _ = _studio.Push();
		GameObject subject = null;
		try
		{
			subject = BuildSubject( part, weapon, out var bounds );
			if ( !subject.IsValid() )
				return null;

			// Find the part in a frame around its bounds: a bodygroup part fills only a little of its gun's.
			var center = bounds.Center;
			var depth = bounds.Size.Length + 64f;
			var height = FrameHeight( bounds.Corners, center ) * 1.2f + 1f;
			Rect? found = null;
			for ( var attempt = 0; attempt < 3; attempt++ )
			{
				found = FindSubject( center, height, depth );
				if ( found is not { } seen || !TouchesEdge( seen ) )
					break;
				height *= 2f;
			}

			if ( found is not { } rect )
				return null;

			// Then frame it tightly for the picture.
			var perPixel = height / ProbeHeight;
			center += View.Right * ((rect.Left + rect.Width * 0.5f - ProbeWidth * 0.5f) * perPixel)
				+ View.Up * ((ProbeHeight * 0.5f - rect.Top - rect.Height * 0.5f) * perPixel);
			var width = (rect.Width + 2f) * perPixel;
			height = MathF.Max( (rect.Height + 2f) * perPixel, width * Height / Width ) / (1f - 2f * Padding);

			const int shotWidth = Width * Supersample;
			const int shotHeight = Height * Supersample;
			var shot = Shoot( shotWidth, shotHeight, center, height, depth, Color.Transparent );
			var cleared = shot[0].a == 0 && shot[^1].a == 0;
			if ( _probeDump is not null )
				SavePixels( shot, shotWidth, shotHeight, $"{_probeDump}_shot.png" );

			// If the render left no alpha, cut the part out by how it differs on black and on white instead.
			var white = cleared ? null : Shoot( shotWidth, shotHeight, center, height, depth, Color.White );
			var picture = Compose( shot, white, shotWidth, shotHeight );
			if ( picture is null )
				return null;

			var scaled = picture.Resize( Width, Height, true );
			picture.Dispose();
			return scaled;
		}
		finally
		{
			// Destroyed alone (the studio is never ticked), a part's meshes could stay and show in the next part's first
			// look, which then framed the two together. Hiding them takes them out at once.
			if ( subject.IsValid() )
			{
				foreach ( var renderer in subject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				{
					if ( renderer.SceneObject is { } sceneObject )
						sceneObject.RenderingEnabled = false;
				}

				subject.DestroyImmediate();
			}
		}
	}

	private static bool EnsureStudio()
	{
		if ( _studio.IsValid() && _camera.IsValid() )
			return true;

		if ( _studio.IsValid() )
			_studio.Destroy();

		_studio = new Scene();
		using ( _studio.Push() )
		{
			_camera = new GameObject( true, "Thumbnail Camera" ).Components.Create<CameraComponent>();
			_camera.IsMainCamera = false;
			_camera.Orthographic = true;
			_camera.EnablePostProcessing = false;

			// A key light from the camera's upper left, a dim fill from its lower right, some ambient and a cubemap for
			// the metal to reflect.
			AddLight( View.Forward * 0.55f - View.Up * 0.65f + View.Right * 0.5f, new Color( 1.7f, 1.66f, 1.6f ) );
			AddLight( View.Forward * 0.6f + View.Up * 0.35f - View.Right * 0.6f, new Color( 0.42f, 0.44f, 0.48f ) );
			new GameObject( true, "Thumbnail Ambient" ).Components.Create<AmbientLight>().Color = new Color( 0.28f, 0.28f, 0.3f );

			var envmap = new GameObject( true, "Thumbnail Envmap" ).Components.Create<EnvmapProbe>();
			envmap.Mode = EnvmapProbe.EnvmapProbeMode.CustomTexture;
			envmap.Texture = Texture.Load( "textures/cubemaps/default2.vtex" );
			envmap.Bounds = BBox.FromPositionAndSize( Vector3.Zero, 100000f );
		}

		return _studio.IsValid() && _camera.IsValid();
	}

	private static void AddLight( Vector3 direction, Color color )
	{
		var go = new GameObject( true, "Thumbnail Light" );
		go.WorldRotation = Rotation.LookAt( direction.Normal );
		var light = go.Components.Create<DirectionalLight>();
		light.LightColor = color;
		light.SkyColor = Color.Black;
		light.Shadows = false;
	}

	/// <summary> Copies the part's meshes into the studio, placed as on the gun, with their bounds. Null if it has none. </summary>
	private static GameObject BuildSubject( GunsmithPart part, Model weapon, out BBox bounds )
	{
		bounds = default;
		var corners = new List<Vector3>();
		var subject = new GameObject( true, "Thumbnail Subject" );

		if ( part.MainPrefab.IsValid() )
		{
			// Only the meshes: the attachment components follow a live gun's bones and would do nothing useful here.
			var root = part.MainPrefab;
			var mount = MountTransform( root, weapon );
			var variant = ModelVariant( root, weapon );
			foreach ( var source in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( !IsShown( source, root ) || source.Model is null || source.Model.IsError )
					continue;

				var go = new GameObject( subject, true, source.GameObject.Name );
				go.WorldTransform = mount.ToWorld( root.WorldTransform.ToLocal( source.WorldTransform ) );
				var renderer = go.Components.Create<ModelRenderer>();
				renderer.CopyFrom( source );
				var model = source.GameObject == root && variant is not null ? variant : source.Model;
				renderer.Model = model;
				if ( model == source.Model )
					renderer.BodyGroups = source.BodyGroups;
				if ( source.GameObject == root && root.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf ) is { } mw22 )
				{
					foreach ( var choice in mw22.BodygroupChoices ?? new() )
						renderer.SetBodyGroup( choice.Key, choice.Value );
				}

				Dress( renderer );
				corners.AddRange( model.Bounds.Corners.Select( c => go.WorldTransform.PointToWorld( c ) ) );
			}
		}
		else if ( part.ModifyBodygroups && weapon is not null && !weapon.IsError )
		{
			var mask = ChoiceMask( part, weapon );
			if ( mask != 0 )
			{
				var go = new GameObject( subject, true, "Thumbnail Bodygroups" );
				var renderer = go.Components.Create<ModelRenderer>();
				renderer.Model = weapon;
				renderer.BodyGroups = mask;
				Dress( renderer );
				corners.AddRange( weapon.Bounds.Corners );
			}
		}

		if ( corners.Count == 0 )
		{
			subject.DestroyImmediate();
			return null;
		}

		bounds = BBox.FromPoints( corners );
		return subject;
	}

	private static void Dress( ModelRenderer renderer )
	{
		renderer.RenderType = ModelRenderer.ShadowRenderType.Off;
		renderer.RenderOptions.Game = true;
		renderer.RenderOptions.Overlay = false;
		if ( renderer.SceneObject is not null )
			renderer.SceneObject.Transform = renderer.WorldTransform;
	}

	/// <summary> Whether a prefab's mesh shows: it and every object above it up to the prefab's root are enabled. </summary>
	private static bool IsShown( Component component, GameObject root )
	{
		if ( !component.Enabled )
			return false;

		for ( var go = component.GameObject; go.IsValid(); go = go.Parent )
		{
			if ( !go.Enabled )
				return false;
			if ( go == root )
				break;
		}

		return true;
	}

	/// <summary>
	/// How the part's mount turns it on the gun, at the gun's bind pose. Most mounts don't; the MW22 parts carry their
	/// own angles (the lasers are rolled), and the M4's stock follows its stock bone turned round.
	/// </summary>
	private static Transform MountTransform( GameObject root, Model weapon )
	{
		if ( root.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf ) is { } mw22 )
			return new Transform( Vector3.Zero, Rotation.From( mw22.PartAngles ), mw22.PartScale );

		if ( root.Components.Get<GunsmithStockAttachment>( FindMode.EverythingInSelf ).IsValid() && BoneBind( weapon, "stock" ) is { } stock )
			return new Transform( Vector3.Zero, stock.Rotation * Rotation.FromYaw( 180f ) );

		return Transform.Zero;
	}

	/// <summary> The part's model for this gun, for mounts with a variant per gun model. </summary>
	private static Model ModelVariant( GameObject root, Model weapon )
	{
		if ( weapon is null )
			return null;

		var variants = root.Components.Get<GunsmithBoneAttachment>( FindMode.EverythingInSelf )?.ModelVariants
			?? root.Components.Get<GunsmithSocketAttachment>( FindMode.EverythingInSelf )?.ModelVariants;
		return variants is not null && variants.TryGetValue( weapon.Name, out var variant ) && variant is not null && !variant.IsError
			? variant : null;
	}

	private static Transform? BoneBind( Model model, string bone )
	{
		if ( model is null )
			return null;

		for ( var i = 0; i < model.BoneCount; i++ )
		{
			if ( model.GetBoneName( i ) == bone )
				return model.GetBoneTransform( i );
		}

		return null;
	}

	/// <summary> The mesh-group bits of the bodygroup choices <paramref name="part"/> picks on <paramref name="model"/>. </summary>
	private static ulong ChoiceMask( GunsmithPart part, Model model )
	{
		ulong mask = 0;
		foreach ( var (group, choice) in part.GetBodygroups( model ) ?? new() )
		{
			var body = int.TryParse( group, out var index )
				? model.Parts.All.FirstOrDefault( p => p.Index == index )
				: model.Parts.Get( group );
			if ( body?.Choices is null || choice < 0 || choice >= body.Choices.Count )
				continue;

			mask |= body.Choices[choice].Mask;
		}

		return mask;
	}

	/// <summary> The frame height that takes in all of <paramref name="points"/> around <paramref name="center"/>. </summary>
	private static float FrameHeight( IEnumerable<Vector3> points, Vector3 center )
	{
		var right = 0f;
		var up = 0f;
		foreach ( var point in points )
		{
			var relative = point - center;
			right = MathF.Max( right, MathF.Abs( Vector3.Dot( relative, View.Right ) ) );
			up = MathF.Max( up, MathF.Abs( Vector3.Dot( relative, View.Up ) ) );
		}

		return MathF.Max( up * 2f, right * 2f * ProbeHeight / ProbeWidth );
	}

	/// <summary> Where the part shows in the first look, in its pixels, or null if nothing does. </summary>
	private static Rect? FindSubject( Vector3 center, float height, float depth )
	{
		var pixels = Shoot( ProbeWidth, ProbeHeight, center, height, depth, ProbeBackground );
		if ( pixels.Length < ProbeWidth * ProbeHeight )
			return null;

		if ( _probeDump is not null )
			SavePixels( pixels, ProbeWidth, ProbeHeight, $"{_probeDump}_probe{_probeCount++}.png" );

		var mask = new bool[ProbeWidth * ProbeHeight];
		for ( var i = 0; i < mask.Length; i++ )
		{
			var c = pixels[i];
			mask[i] = 255 - c.r + c.g + 255 - c.b >= 24;
		}

		DropLooseBits( mask, ProbeWidth, ProbeHeight );

		int x0 = ProbeWidth, y0 = ProbeHeight, x1 = -1, y1 = -1;
		for ( var y = 0; y < ProbeHeight; y++ )
		{
			for ( var x = 0; x < ProbeWidth; x++ )
			{
				if ( !mask[y * ProbeWidth + x] )
					continue;

				x0 = Math.Min( x0, x );
				x1 = Math.Max( x1, x );
				y0 = Math.Min( y0, y );
				y1 = Math.Max( y1, y );
			}
		}

		return x1 < 0 ? null : new Rect( x0, y0, x1 - x0 + 1, y1 - y0 + 1 );
	}

	private static bool TouchesEdge( Rect rect ) =>
		rect.Left <= 0 || rect.Top <= 0 || rect.Left + rect.Width >= ProbeWidth || rect.Top + rect.Height >= ProbeHeight;

	/// <summary>
	/// Takes out of <paramref name="mask"/> the small loose bits away from the part's main piece. A bodygroup part can
	/// carry pieces the gun's animations put in place, like the RPK magazines' top round, which the bind pose leaves
	/// floating off to one side, where it shrank the part to fit it in. Pieces of a fair size, and any close to what's
	/// kept (a thin wire stock can break up into bits at this size), stay.
	/// </summary>
	private static void DropLooseBits( bool[] mask, int width, int height )
	{
		var label = new int[mask.Length];
		var sizes = new List<int> { 0 };
		var boxes = new List<(int X0, int Y0, int X1, int Y1)> { default };
		var stack = new Stack<int>();
		for ( var start = 0; start < mask.Length; start++ )
		{
			if ( !mask[start] || label[start] != 0 )
				continue;

			var id = sizes.Count;
			int size = 0, x0 = width, y0 = height, x1 = -1, y1 = -1;
			label[start] = id;
			stack.Push( start );
			while ( stack.Count > 0 )
			{
				var i = stack.Pop();
				var x = i % width;
				var y = i / width;
				size++;
				x0 = Math.Min( x0, x );
				x1 = Math.Max( x1, x );
				y0 = Math.Min( y0, y );
				y1 = Math.Max( y1, y );

				for ( var ny = Math.Max( 0, y - 1 ); ny <= Math.Min( height - 1, y + 1 ); ny++ )
				{
					for ( var nx = Math.Max( 0, x - 1 ); nx <= Math.Min( width - 1, x + 1 ); nx++ )
					{
						var n = ny * width + nx;
						if ( !mask[n] || label[n] != 0 )
							continue;

						label[n] = id;
						stack.Push( n );
					}
				}
			}

			sizes.Add( size );
			boxes.Add( (x0, y0, x1, y1) );
		}

		if ( sizes.Count <= 2 )
			return;

		var main = 1;
		for ( var id = 2; id < sizes.Count; id++ )
		{
			if ( sizes[id] > sizes[main] )
				main = id;
		}

		var keep = new bool[sizes.Count];
		var kept = boxes[main];
		void Keep( int id )
		{
			keep[id] = true;
			var box = boxes[id];
			kept = (Math.Min( kept.X0, box.X0 ), Math.Min( kept.Y0, box.Y0 ), Math.Max( kept.X1, box.X1 ), Math.Max( kept.Y1, box.Y1 ));
		}

		Keep( main );
		for ( var id = 1; id < sizes.Count; id++ )
		{
			if ( sizes[id] * 10 >= sizes[main] )
				Keep( id );
		}

		// Near means within a share of the main piece's size, so the first look and the picture agree at their scales.
		var gap = Math.Max( 3, Math.Max( kept.X1 - kept.X0, kept.Y1 - kept.Y0 ) / 16 );
		bool grew;
		do
		{
			grew = false;
			for ( var id = 1; id < sizes.Count; id++ )
			{
				var box = boxes[id];
				if ( keep[id] || box.X0 > kept.X1 + gap || box.X1 < kept.X0 - gap || box.Y0 > kept.Y1 + gap || box.Y1 < kept.Y0 - gap )
					continue;

				Keep( id );
				grew = true;
			}
		}
		while ( grew );

		for ( var i = 0; i < mask.Length; i++ )
		{
			if ( mask[i] && !keep[label[i]] )
				mask[i] = false;
		}
	}

	private static Color32[] Shoot( int width, int height, Vector3 center, float frameHeight, float depth, Color background )
	{
		_camera.WorldRotation = View;
		_camera.WorldPosition = center - View.Forward * depth;
		_camera.OrthographicHeight = frameHeight;
		_camera.ZNear = 1f;
		_camera.ZFar = depth * 2f;
		_camera.BackgroundColor = background;

		using var bitmap = new Bitmap( width, height );
		_camera.RenderToBitmap( bitmap );
		return bitmap.GetPixels32();
	}

	/// <summary>
	/// The picture: coverage from the shot's alpha (or, when <paramref name="white"/> is given, from how the shot on black
	/// differs on white), and the shading stretched over a light grey range so black and tan parts read alike on the
	/// dark list.
	/// </summary>
	private static Bitmap Compose( Color32[] shot, Color32[] white, int width, int height )
	{
		var count = width * height;
		if ( shot is null || shot.Length < count || (white is not null && white.Length < count) )
			return null;

		var alpha = new float[count];
		var shown = new bool[count];
		for ( var i = 0; i < count; i++ )
		{
			var c = shot[i];
			float coverage;
			if ( white is null )
			{
				coverage = c.a / 255f;
			}
			else
			{
				var w = white[i];
				coverage = 1f - ((w.r - c.r) + (w.g - c.g) + (w.b - c.b)) / (3f * 255f);
			}

			alpha[i] = coverage.Clamp( 0f, 1f );
			shown[i] = alpha[i] >= 0.02f;
		}

		DropLooseBits( shown, width, height );

		var shade = new float[count];
		var solid = new List<float>();
		for ( var i = 0; i < count; i++ )
		{
			if ( !shown[i] )
				continue;

			// On black the pixel is the part's colour times its coverage; with alpha it's the colour itself.
			var c = shot[i];
			var light = (0.2126f * c.r + 0.7152f * c.g + 0.0722f * c.b) / 255f;
			shade[i] = white is null ? light : light / alpha[i];
			if ( alpha[i] > 0.5f )
				solid.Add( shade[i] );
		}

		if ( solid.Count < 16 )
			return null;

		solid.Sort();
		var low = solid[(int)(solid.Count * 0.02f)];
		var high = solid[Math.Min( solid.Count - 1, (int)(solid.Count * 0.98f) )];
		var range = MathF.Max( high - low, 0.04f );

		// Clear pixels keep the grey too, so scaling down doesn't darken the edges.
		var colors = new Color[count];
		for ( var i = 0; i < count; i++ )
		{
			if ( !shown[i] )
			{
				colors[i] = new Color( 0.62f, 0.63f, 0.65f, 0f );
				continue;
			}

			var t = MathF.Pow( ((shade[i] - low) / range).Clamp( 0f, 1f ), 0.8f );
			var grey = 0.4f + 0.55f * t;
			colors[i] = new Color( grey * 0.97f, grey * 0.985f, grey, alpha[i] );
		}

		var bitmap = new Bitmap( width, height );
		bitmap.SetPixels( colors );
		return bitmap;
	}

	/// <summary> While dev_thumbnails runs with probes on: where each first look is written, with a counter. </summary>
	private static string _probeDump;
	private static int _probeCount;

	private static void SavePixels( Color32[] pixels, int width, int height, string path )
	{
		using var bitmap = new Bitmap( width, height );
		bitmap.SetPixels( pixels.Select( c => new Color( c.r / 255f, c.g / 255f, c.b / 255f, c.a / 255f ) ).ToArray() );
		FileSystem.Data.WriteAllBytes( path, bitmap.ToPng() );
	}

	/// <summary>
	/// Writes a weapon's attachment pictures to the game's data folder (thumbnails/&lt;weapon&gt;/), for checking them,
	/// e.g. dev_thumbnails kastov74u. An optional filter keeps the parts whose path contains it; "probes" also writes the
	/// first looks that frame each part.
	/// </summary>
	[ConCmd( "dev_thumbnails" )]
	public static void DumpThumbnails( string weapon, string filter = "", string probes = "" )
	{
		var resource = ResourceLibrary.GetAll<EquipmentResource>()
			.FirstOrDefault( r => r.ResourceName.Equals( weapon, StringComparison.OrdinalIgnoreCase ) );
		if ( resource is null )
		{
			Log.Warning( $"dev_thumbnails: no equipment named {weapon}" );
			return;
		}

		var model = resource.ViewModelPrefab?.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants )?.Model;
		var folder = $"thumbnails/{resource.ResourceName}";
		FileSystem.Data.CreateDirectory( folder );
		var written = 0;
		foreach ( var part in AttachmentUnlocks.GetWeaponParts( resource ).Where( p => string.IsNullOrEmpty( filter )
			|| p.ResourcePath.Contains( filter, StringComparison.OrdinalIgnoreCase ) ) )
		{
			Bitmap bitmap = null;
			try
			{
				_probeDump = probes == "probes" ? $"{folder}/{part.Category}_{part.ResourceName}" : null;
				_probeCount = 0;
				bitmap = Render( part, model );
				if ( bitmap is null )
				{
					Log.Info( $"dev_thumbnails: nothing to draw for {part.ResourcePath}" );
					continue;
				}

				FileSystem.Data.WriteAllBytes( $"{folder}/{part.Category}_{part.ResourceName}.png", bitmap.ToPng() );
				written++;
			}
			catch ( Exception e )
			{
				Log.Warning( $"dev_thumbnails: {part.ResourcePath}: {e}" );
			}
			finally
			{
				_probeDump = null;
				bitmap?.Dispose();
			}
		}

		Log.Info( $"dev_thumbnails: wrote {written} pictures for {resource.ResourceName} (model {model?.Name}) to data/{folder}" );
	}
}
