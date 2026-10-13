using Sandbox.Rendering;
using System.Runtime.InteropServices;

namespace Facepunch;

/// <summary>
/// Draws all grenade smoke together after world transparency and before viewmodels. Each puff integrates its visible
/// volume up to scene depth, so refraction/glass cannot repaint a clear background over smoke, and nearby walls still
/// occlude it. This runs on every game camera, including scopes, spectators and recon feeds.
/// </summary>
[Hide]
public sealed class SmokeRendering : Component, Component.DontExecuteOnServer
{
	[StructLayout( LayoutKind.Sequential )]
	private struct Puff
	{
		public Vector4 CentreRadius;
		public Vector4 ColourOpacity;
		public readonly Vector3 Position => new( CentreRadius.x, CentreRadius.y, CentreRadius.z );
	}

	private sealed class View : IDisposable
	{
		public readonly CameraComponent Camera;
		public readonly CommandList Commands = new( "Grenade smoke" );
		public readonly RenderAttributes Attributes = new();
		public readonly List<Puff> Puffs = new();
		public readonly GpuBuffer<GpuBuffer.IndirectDrawIndexedArguments> DrawArguments = new( 1, GpuBuffer.UsageFlags.IndirectDrawArguments );
		public GpuBuffer<Puff> Buffer;
		public int Capacity;

		public View( CameraComponent camera )
		{
			Camera = camera;
			camera.AddCommandList( Commands, Stage.AfterTransparent, -100 );
		}

		public void Dispose()
		{
			if ( Camera.IsValid() ) Camera.RemoveCommandList( Commands );
			Commands.Reset();
			Buffer?.Dispose();
			DrawArguments.Dispose();
			Buffer = null;
			Puffs.Clear();
		}
	}

	private readonly Dictionary<CameraComponent, View> Views = new();
	private readonly HashSet<CameraComponent> LiveCameras = new();
	private Material Material;
	private GpuBuffer<int> Indices;
	private GpuBuffer<Vertex> Vertices;

	internal static void Ensure( Scene scene )
	{
		if ( scene.GetAllComponents<SmokeRendering>().Any( x => x.Enabled ) ) return;
		var go = new GameObject( scene, true, "Grenade smoke rendering" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.AddComponent<SmokeRendering>();
	}

	protected override void OnPreRender()
	{
		var smoke = Scene.GetAllComponents<SmokeSimulation>()
			.Where( x => x.Enabled && x.ParticleEffect.IsValid() && x.ParticleEffect.Enabled ).ToArray();
		if ( smoke.Length == 0 )
		{
			GameObject.Destroy();
			return;
		}

		Material ??= Material.FromShader( "shaders/hc1_smoke.shader" );
		if ( Indices is null )
		{
			Indices = new GpuBuffer<int>( 6, GpuBuffer.UsageFlags.Index );
			Indices.SetData( new int[] { 0, 1, 2, 2, 3, 0 } );
			Vertices = new GpuBuffer<Vertex>( 4, GpuBuffer.UsageFlags.Vertex );
			Vertices.SetData( new Vertex[]
			{
				new( new Vector3( -1f, -1f, 0f ) ), new( new Vector3( 1f, -1f, 0f ) ),
				new( new Vector3( 1f, 1f, 0f ) ), new( new Vector3( -1f, 1f, 0f ) )
			} );
		}

		LiveCameras.Clear();
		foreach ( var camera in Scene.GetAllComponents<CameraComponent>() )
		{
			if ( !camera.Enabled || !camera.GameObject.Active ) continue;
			LiveCameras.Add( camera );
			if ( !Views.TryGetValue( camera, out var view ) )
			{
				view = new View( camera );
				Views.Add( camera, view );
			}
			Record( view, smoke );
		}

		foreach ( var camera in Views.Keys.Where( x => !LiveCameras.Contains( x ) ).ToArray() )
		{
			Views[camera].Dispose();
			Views.Remove( camera );
		}
	}

	private void Record( View view, SmokeSimulation[] smoke )
	{
		view.Commands.Reset();
		view.Puffs.Clear();
		foreach ( var effect in smoke )
		{
			if ( effect.Tags.HasAny( (ITagSet)view.Camera.RenderExcludeTags ) ) continue;
			if ( view.Camera.RenderTags.Any() && !effect.Tags.HasAny( (ITagSet)view.Camera.RenderTags ) ) continue;
			foreach ( var particle in effect.ParticleEffect.Particles )
			{
				var alpha = Math.Clamp( particle.Alpha * particle.Color.a, 0f, 0.995f );
				var radius = MathF.Max( particle.Size.x, particle.Size.y ) * SmokeMath.PuffReach;
				if ( alpha <= 0.001f || radius <= 0.01f ) continue;
				view.Puffs.Add( new Puff
				{
					CentreRadius = new Vector4( particle.Position, radius ),
					ColourOpacity = new Vector4( particle.Color.r, particle.Color.g, particle.Color.b, alpha )
				} );
			}
		}
		if ( view.Puffs.Count == 0 ) return;

		// Merge every grenade into one camera-depth order, rather than sorting each cloud as a separate scene object.
		var cameraPosition = view.Camera.WorldPosition;
		var forward = view.Camera.WorldRotation.Forward;
		view.Puffs.Sort( (a, b) => Vector3.Dot( b.Position - cameraPosition, forward )
			.CompareTo( Vector3.Dot( a.Position - cameraPosition, forward ) ) );

		if ( view.Capacity < view.Puffs.Count )
		{
			view.Buffer?.Dispose();
			view.Capacity = Math.Max( 64, (int)Math.Pow( 2, Math.Ceiling( Math.Log2( view.Puffs.Count ) ) ) );
			view.Buffer = new GpuBuffer<Puff>( view.Capacity );
			view.Attributes.Set( "SmokePuffs", view.Buffer );
		}
		view.Buffer.SetData( view.Puffs );
		view.DrawArguments.SetData( new GpuBuffer.IndirectDrawIndexedArguments[]
		{
			new() { IndexCount = 6, InstanceCount = (uint)view.Puffs.Count }
		} );
		view.Commands.DrawIndexedInstancedIndirect( Vertices, Indices, Material, view.DrawArguments, 0, view.Attributes );
	}

	protected override void OnDisabled()
	{
		foreach ( var view in Views.Values ) view.Dispose();
		Views.Clear();
		LiveCameras.Clear();
		Indices?.Dispose();
		Indices = null;
		Vertices?.Dispose();
		Vertices = null;
	}
}
