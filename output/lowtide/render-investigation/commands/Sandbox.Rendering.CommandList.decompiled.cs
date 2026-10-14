using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using NativeEngine;
using Sandbox.Diagnostics;
using Sandbox.Internal;

namespace Sandbox.Rendering;

[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 5)]
[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 8)]
[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 5)]
[SourceLocation("Systems\\Render\\CommandList\\CommandList.Render.cs", 4)]
[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 6)]
[SourceLocation("Systems\\Render\\Painting\\CommandList.Compatibility.cs", 3)]
public sealed class CommandList
{
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 51)]
	public class AttributeAccess
	{
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 56)]
		private readonly Dictionary<string, RenderTarget> _renderTargets = new Dictionary<string, RenderTarget>();

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 58)]
		internal Func<RenderAttributes> _get;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 59)]
		internal CommandList list;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 61)]
		private RenderAttributes attributes => _get();

		internal AttributeAccess(CommandList cmdlist, Func<RenderAttributes> _getter)
		{
			list = cmdlist;
			_get = _getter;
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 69)]
		public unsafe void Clear()
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object1 = this
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object1).attributes.Clear();
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 79)]
		public unsafe void Set(StringToken token, float f)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(f, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, entry.Data1.x);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 89)]
		public void Set(StringToken token, double f)
		{
			Set(token, (float)f);
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 91)]
		public unsafe void Set(StringToken token, Vector2 vector2)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(vector2.x, vector2.y, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, new Vector2(entry.Data1.x, entry.Data1.y));
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 101)]
		public unsafe void Set(StringToken token, Vector3 vector3)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(vector3.x, vector3.y, vector3.z, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, new Vector3(entry.Data1.x, entry.Data1.y, entry.Data1.z));
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 111)]
		public unsafe void Set(StringToken token, Vector4 vector4)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = vector4
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, in entry.Data1);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 121)]
		public unsafe void Set(StringToken token, int i)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(i, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, (int)entry.Data1.x);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 131)]
		public unsafe void Set(StringToken token, bool b)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(b ? 1 : 0, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, (int)entry.Data1.x != 0);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 141)]
		public unsafe void Set(StringToken token, Matrix matrix)
		{
			Entry data = new Entry
			{
				Token = token,
				Object4 = this
			};
			Unsafe.As<Vector4, Matrix>(ref data.Data1) = matrix;
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), data);
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, in Unsafe.As<Vector4, Matrix>(ref entry.Data1));
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 153)]
		public unsafe void Set(StringToken token, GpuBuffer buffer)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object2 = buffer,
				Object4 = this
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, (GpuBuffer)entry.Object2);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 163)]
		public unsafe void Set(StringToken token, Texture texture, int mip = -1)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object2 = texture,
				Object4 = this,
				Data1 = new Vector4(mip, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, (Texture)entry.Object2, (int)entry.Data1.x);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 173)]
		public unsafe void Set(StringToken token, SamplerState samplerState)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object2 = samplerState,
				Object4 = this
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, (SamplerState)entry.Object2);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 183)]
		public unsafe void SetCombo(StringToken token, int value)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(value, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.SetCombo(in entry.Token, (int)entry.Data1.x);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 193)]
		public unsafe void SetCombo(StringToken token, bool value)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(value ? 1 : 0, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.SetCombo(in entry.Token, (int)entry.Data1.x != 0);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 203)]
		public unsafe void SetCombo<T>(StringToken token, T t) where T : unmanaged, Enum
		{
			int num = Unsafe.SizeOf<T>() switch
			{
				1 => Unsafe.As<T, byte>(ref t), 
				2 => Unsafe.As<T, short>(ref t), 
				8 => (int)Unsafe.As<T, long>(ref t), 
				_ => Unsafe.As<T, int>(ref t), 
			};
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object4 = this,
				Data1 = new Vector4(num, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.SetCombo(in entry.Token, (int)entry.Data1.x);
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 223)]
		public unsafe void SetData<T>(StringToken token, T data) where T : unmanaged
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object2 = data,
				Object4 = this
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.SetData(in entry.Token, (T)entry.Object2);
			}
		}

		/// <summary>
		/// Set a special value
		/// </summary>
		[Description("Set a special value")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 236)]
		public unsafe void SetValue(StringToken token, RenderValue value)
		{
			switch (value)
			{
			case RenderValue.ColorTarget:
				list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute3), new Entry
				{
					Token = token,
					Object4 = this
				});
				break;
			case RenderValue.DepthTarget:
				list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute2), new Entry
				{
					Token = token,
					Object4 = this
				});
				break;
			case RenderValue.MsaaCombo:
				list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
				{
					Token = token,
					Object4 = this
				});
				break;
			}
			static void Execute(ref Entry entry, CommandList commandList)
			{
				((AttributeAccess)entry.Object4).attributes.SetCombo(in entry.Token, (Graphics.IdealMsaaLevel != MultisampleAmount.MultisampleNone) ? 1 : 0);
			}
			static void Execute2(ref Entry entry, CommandList commandList)
			{
				AttributeAccess attributeAccess = (AttributeAccess)entry.Object4;
				ITexture value2 = Graphics.GetDepthTarget(out var owned);
				attributeAccess.attributes.Set(in entry.Token, in value2, -1);
				if (owned && !value2.IsNull)
				{
					value2.DestroyStrongHandle();
				}
			}
			static void Execute3(ref Entry entry, CommandList commandList)
			{
				AttributeAccess attributeAccess = (AttributeAccess)entry.Object4;
				ITexture value2 = Graphics.GetColorTarget(out var owned);
				attributeAccess.attributes.Set(in entry.Token, in value2, -1);
				if (owned && !value2.IsNull)
				{
					value2.DestroyStrongHandle();
				}
			}
		}

		/// <summary>
		/// Set the color texture from this named render target to this attribute
		/// </summary>
		[Description("Set the color texture from this named render target to this attribute")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 284)]
		public unsafe void Set(StringToken token, RenderTargetHandle.ColorTextureRef buffer, int mip = -1)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object5 = buffer.Name,
				Object4 = this,
				Data1 = new Vector4(mip, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
				if (renderTarget == null)
				{
					GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
				}
				else
				{
					((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, renderTarget.ColorTarget, (int)entry.Data1.x);
				}
			}
		}

		/// <summary>
		/// Set the depth texture from this named render target to this attribute
		/// </summary>
		[Description("Set the depth texture from this named render target to this attribute")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 304)]
		public unsafe void Set(StringToken token, RenderTargetHandle.DepthTextureRef buffer, int mip = -1)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object5 = buffer.Name,
				Object4 = this,
				Data1 = new Vector4(mip, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
				if (renderTarget == null)
				{
					GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
				}
				else
				{
					((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, renderTarget.DepthTarget, (int)entry.Data1.x);
				}
			}
		}

		/// <summary>
		/// Set the color texture from this named render target to this attribute
		/// </summary>
		[Description("Set the color texture from this named render target to this attribute")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 324)]
		public unsafe void Set(StringToken token, RenderTargetHandle.ColorIndexRef buffer)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object5 = buffer.Name,
				Object4 = this
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
				if (renderTarget == null)
				{
					GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
				}
				else
				{
					((AttributeAccess)entry.Object4).attributes.Set(in entry.Token, renderTarget.ColorTarget.Index);
				}
			}
		}

		/// <summary>
		/// Set the size of this named render target to this float2 attribute
		/// </summary>
		[Description("Set the size of this named render target to this float2 attribute")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 344)]
		public unsafe void Set(StringToken token, RenderTargetHandle.SizeHandle size, bool inverse = false)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Token = token,
				Object5 = size.Name,
				Object4 = this,
				Data1 = new Vector4(inverse ? 1 : 0, 0f, 0f, 0f)
			});
			static void Execute(ref Entry entry, CommandList commandList)
			{
				RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
				if (renderTarget == null)
				{
					GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
				}
				else
				{
					Vector2 value = renderTarget.ColorTarget.Size;
					AttributeAccess attributeAccess = (AttributeAccess)entry.Object4;
					if ((int)entry.Data1.x != 0)
					{
						attributeAccess.attributes.Set(in entry.Token, new Vector2(1f / value.x, 1f / value.y));
					}
					else
					{
						attributeAccess.attributes.Set(in entry.Token, in value);
					}
				}
			}
		}

		/// <summary>
		/// Takes a copy of the current viewport's color texture and stores it in targetName on renderAttributes.
		/// </summary>
		[Description("Takes a copy of the current viewport's color texture and stores it in targetName on renderAttributes.")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 367)]
		public RenderTargetHandle GrabFrameTexture(string token = "FrameTexture", bool withMips = false)
		{
			return GrabFrameTexture(token, withMips ? Graphics.DownsampleMethod.GaussianBlur : Graphics.DownsampleMethod.None);
		}

		/// <summary>
		/// Takes a copy of the current viewport's color texture and stores it in targetName on renderAttributes.
		/// </summary>
		[Description("Takes a copy of the current viewport's color texture and stores it in targetName on renderAttributes.")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 375)]
		public unsafe RenderTargetHandle GrabFrameTexture(string token, Graphics.DownsampleMethod downsampleMethod, int maxMips = 0)
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object5 = token,
				Object2 = this,
				Data1 = new Vector4((float)downsampleMethod, maxMips, 0f, 0f)
			});
			return new RenderTargetHandle
			{
				Name = token
			};
			static void Execute(ref Entry entry, CommandList commandList)
			{
				AttributeAccess attributeAccess = (AttributeAccess)entry.Object2;
				RenderTarget value = Graphics.GrabFrameTexture((string)entry.Object5, attributeAccess.attributes, (Graphics.DownsampleMethod)entry.Data1.x, (int)entry.Data1.y);
				commandList.state.renderTargets[(string)entry.Object5] = value;
				attributeAccess._renderTargets[(string)entry.Object5] = value;
			}
		}

		/// <summary>
		/// Takes a copy of the current viewport's depth texture and stores it in targetName on renderAttributes.
		/// </summary>
		[Description("Takes a copy of the current viewport's depth texture and stores it in targetName on renderAttributes.")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 393)]
		public unsafe RenderTargetHandle GrabDepthTexture(string token = "DepthTexture")
		{
			list.AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object5 = token,
				Object2 = this
			});
			return new RenderTargetHandle
			{
				Name = token
			};
			static void Execute(ref Entry entry, CommandList commandList)
			{
				AttributeAccess attributeAccess = (AttributeAccess)entry.Object2;
				RenderTarget value = Graphics.GrabDepthTexture((string)entry.Object5, attributeAccess.attributes);
				commandList.state.renderTargets[(string)entry.Object5] = value;
				attributeAccess._renderTargets[(string)entry.Object5] = value;
			}
		}

		/// <summary>
		/// Get the actual render target by name. Useful for externals that need to access the render target directly.
		/// </summary>
		[Description("Get the actual render target by name. Useful for externals that need to access the render target directly.")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 411)]
		public RenderTarget GetRenderTarget(string name)
		{
			using (list._lock.EnterScope())
			{
				if (_renderTargets.TryGetValue(name, out var value))
				{
					return value;
				}
				return null;
			}
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 422)]
		internal void ClearRenderTargets()
		{
			_renderTargets.Clear();
		}
	}

	/// <summary>
	/// Holds the function and state data for a single command. 
	/// Target: fit within 2 cache lines (128 bytes).
	/// </summary>
	[Description("Holds the function and state data for a single command. Target: fit within 2 cache lines (128 bytes).")]
	private struct Entry
	{
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 52)]
		public unsafe delegate*<ref Entry, CommandList, void> Execute;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 56)]
		public object Object1;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 57)]
		public object Object2;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 58)]
		public object Object3;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 59)]
		public object Object4;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 60)]
		public object Object5;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 62)]
		public StringToken Token;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 65)]
		public int Count;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 67)]
		public Vector4 Data1;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 68)]
		public Vector4 Data2;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 69)]
		public Vector4 Data3;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 72)]
		public Vector4 Data4;
	}

	/// <summary>
	/// This lives for the lifetime of the command list and is 
	/// used to store temporary render targets and other state.
	/// </summary>
	[Description("This lives for the lifetime of the command list and is used to store temporary render targets and other state.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 103)]
	private class State
	{
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 105)]
		public Dictionary<string, RenderTarget> renderTargets = new Dictionary<string, RenderTarget>();

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 106)]
		public Stack<(RenderTarget Target, RenderViewport Viewport)> renderTargetStack = new Stack<(RenderTarget, RenderViewport)>();

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 107)]
		public Stack<OpenScope> openScopes = new Stack<OpenScope>();

		/// <summary>
		/// Should be called at the end of usage
		/// </summary>
		[Description("Should be called at the end of usage")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 112)]
		public void Reset()
		{
			renderTargets.Clear();
			renderTargetStack.Clear();
			openScopes.Clear();
		}

		/// <summary>
		/// Sneaky way for externals to get render target
		/// </summary>
		[Description("Sneaky way for externals to get render target")]
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 126)]
		public RenderTarget GetRenderTarget(string name)
		{
			if (renderTargets.TryGetValue(name, out var value))
			{
				return value;
			}
			return null;
		}
	}

	/// <summary>
	/// Command buffer flags allow us to skip command buffers if the camera 
	/// doesn't want a particular thing. Like post processing.
	/// </summary>
	[Description("Command buffer flags allow us to skip command buffers if the camera doesn't want a particular thing. Like post processing.")]
	public enum Flag
	{
		None = 0,
		PostProcess = 2,
		Hud = 4
	}

	/// <summary>
	/// A GPU timing section in a command list. Closes at the end of its <c>using</c> block.
	/// </summary>
	[Description("A GPU timing section in a command list. Closes at the end of its <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">using</code> block.")]
	public ref struct ProfilingScope
	{
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 26)]
		private CommandList _list;

		internal ProfilingScope(CommandList list)
		{
			_list = list;
		}

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 33)]
		public unsafe void Dispose()
		{
			if (_list != null)
			{
				_list.AddEntry((delegate*<ref Entry, CommandList, void>)(&ExecuteEndScope), default(Entry));
				_list = null;
			}
		}
	}

	/// <summary>
	/// A scope open during this execution. Carries what was actually begun, since the profiler or a debugger
	/// can be toggled between a scope opening and closing.
	/// </summary>
	[Description("A scope open during this execution. Carries what was actually begun, since the profiler or a debugger can be toggled between a scope opening and closing.")]
	internal struct OpenScope
	{
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 49)]
		public nint Marker;

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 50)]
		public bool Pix;
	}

	/// <summary>
	/// Owns reusable command data referenced by this list. Reset releases recorded data for reuse.
	/// </summary>
	[Description("Owns reusable command data referenced by this list. Reset releases recorded data for reuse.")]
	internal interface IResource
	{
		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 13)]
		void Reset();

		[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 14)]
		void BeginExecute();
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 7)]
	private RenderAttributes drawAttributes;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 8)]
	private AttributeAccess drawAttributeAccess;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 10)]
	private readonly Lock _lock = new Lock();

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 12)]
	private string _debugName;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 13)]
	private ProfilingSampler _sampler = DefaultSampler;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 15)]
	private static readonly ProfilingSampler DefaultSampler = new ProfilingSampler("CommandList");

	/// <summary>
	/// An ordered list of entries that will execute on the render thread. All access (record and
	/// execute) is serialized by <see cref="F:Sandbox.Rendering.CommandList._lock" /> - recording and executing the same list from
	/// two threads at once is caller misuse, but the lock guarantees it can't crash or corrupt state.
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 81)]
	private readonly List<Entry> _entries = new List<Entry>(8);

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 135)]
	private State state;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 53)]
	private static bool _debugMarkers;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 54)]
	private static bool _debugMarkersQueried;

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 17)]
	private List<IResource> _resources;

	/// <summary>
	/// These are the attributes for the current view. Setting a variable here will let you pass it down to
	/// other places in the render pipeline.
	/// </summary>
	[Obsolete("Global/frame attributes are deprecated. Use a local Attributes set or pipeline texture slots instead.")]
	[Description("These are the attributes for the current view. Setting a variable here will let you pass it down to other places in the render pipeline.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 433)]
	public AttributeAccess GlobalAttributes => Attributes;

	/// <summary>
	/// Access to the local attributes. What these are depends on where the command list is being called.
	/// If we're calling from a renderable, these are the attributes for that renderable.
	/// </summary>
	[Description("Access to the local attributes. What these are depends on where the command list is being called. If we're calling from a renderable, these are the attributes for that renderable.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 440)]
	public AttributeAccess Attributes { get; private set; }

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 17)]
	public string DebugName
	{
		get
		{
			return _debugName;
		}
		set
		{
			if (!(_debugName == value))
			{
				_debugName = value;
				_sampler = (string.IsNullOrEmpty(value) ? DefaultSampler : new ProfilingSampler(value));
			}
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 31)]
	public bool Enabled { get; set; }

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 32)]
	public Flag Flags { get; set; }

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 96)]
	private RenderAttributes attributes => Graphics.Attributes;

	/// <summary>
	/// A handle to the viewport size
	/// </summary>
	[Description("A handle to the viewport size")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1103)]
	public RenderTargetHandle.SizeHandle ViewportSize => new RenderTargetHandle.SizeHandle
	{
		Name = "$vp"
	};

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 56)]
	private static bool DebugMarkersEnabled
	{
		get
		{
			if (!_debugMarkersQueried)
			{
				_debugMarkers = g_pRenderDevice.AreDebugMarkersEnabled();
				_debugMarkersQueried = true;
			}
			return _debugMarkers;
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 19)]
	internal Lock SyncRoot => _lock;

	/// <summary>
	/// Access to simple 2D painting functions to draw shapes and text.
	/// </summary>
	[Obsolete("Use Painter.Begin( commandList ) instead. Dispose the painter to submit its drawing.")]
	[Description("Access to simple 2D painting functions to draw shapes and text.")]
	[SourceLocation("Systems\\Render\\Painting\\CommandList.Compatibility.cs", 8)]
	public HudPainter Paint => new HudPainter(this);

	/// <summary>Starts a private attribute set for one draw, inheriting the caller's attributes at playback.</summary>
	[Description("Starts a private attribute set for one draw, inheriting the caller's attributes at playback.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 11)]
	internal unsafe AttributeAccess BeginDrawAttributes()
	{
		if (drawAttributes == null)
		{
			drawAttributes = new RenderAttributes();
		}
		if (drawAttributeAccess == null)
		{
			drawAttributeAccess = new AttributeAccess(this, () => drawAttributes);
		}
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), default(Entry));
		return drawAttributeAccess;
		static void Execute(ref Entry entry, CommandList list)
		{
			list.drawAttributes.Clear(freeMemory: false);
			Graphics.Attributes.MergeTo(list.drawAttributes);
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 24)]
	internal unsafe void DrawQuad(Rect rect, Material material, Color color, AttributeAccess attributes)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Data1 = new Vector4(rect.Left, rect.Top, rect.Width, rect.Height),
			Data2 = new Vector4(color.r, color.g, color.b, color.a),
			Object1 = material,
			Object2 = attributes
		});
		static void Execute(ref Entry entry, CommandList list)
		{
			Graphics.DrawQuad(new Rect(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w), (Material)entry.Object1, new Color(entry.Data2.x, entry.Data2.y, entry.Data2.z, entry.Data2.w), ((AttributeAccess)entry.Object2)._get());
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 41)]
	internal unsafe void DrawIndexedInstanced(GpuBuffer indices, Material material, int count, AttributeAccess attributes)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = indices,
			Object2 = material,
			Object3 = attributes,
			Count = count
		});
		static void Execute(ref Entry entry, CommandList list)
		{
			Graphics.DrawIndexedInstanced((GpuBuffer)entry.Object1, (Material)entry.Object2, entry.Count, ((AttributeAccess)entry.Object3)._get());
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Attributes.cs", 442)]
	private RenderAttributes GetLocalAttributes()
	{
		return Graphics.Attributes;
	}

	public CommandList()
	{
		Enabled = true;
		Attributes = new AttributeAccess(this, GetLocalAttributes);
	}

	public CommandList(string debugName)
		: this()
	{
		DebugName = debugName;
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 85)]
	private unsafe void AddEntry(delegate*<ref Entry, CommandList, void> execute, Entry data)
	{
		data.Execute = execute;
		using (_lock.EnterScope())
		{
			_entries.Add(data);
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 137)]
	public void Reset()
	{
		using (_lock.EnterScope())
		{
			if (_resources != null)
			{
				foreach (IResource resource in _resources)
				{
					resource.Reset();
				}
			}
			Attributes.ClearRenderTargets();
			drawAttributeAccess?.ClearRenderTargets();
			drawAttributes?.Clear(freeMemory: false);
			_entries.Clear();
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 156)]
	public unsafe void Blit(Material material, RenderAttributes attributes = null)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = material,
			Object2 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Blit((Material)entry.Object1, (RenderAttributes)entry.Object2);
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 166)]
	public unsafe void DrawQuad(Rect rect, Material material, Color color)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Data1 = new Vector4(rect.Left, rect.Top, rect.Width, rect.Height),
			Object1 = material,
			Data2 = new Vector4(color.r, color.g, color.b, color.a)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawQuad(new Rect(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w), (Material)entry.Object1, new Color(entry.Data2.x, entry.Data2.y, entry.Data2.z, entry.Data2.w));
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 176)]
	public unsafe void DrawScreenQuad(Material material, Color color)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = material,
			Data1 = new Vector4(color.r, color.g, color.b, color.a)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawQuad(Graphics.Viewport, (Material)entry.Object1, new Color(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 186)]
	public unsafe void Set(StringToken token, float f)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(f, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, entry.Data1.x);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 196)]
	public void Set(StringToken token, double f)
	{
		Set(token, (float)f);
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 198)]
	public unsafe void Set(StringToken token, Vector2 vector2)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(vector2.x, vector2.y, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, new Vector2(entry.Data1.x, entry.Data1.y));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 208)]
	public unsafe void Set(StringToken token, Vector3 vector3)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(vector3.x, vector3.y, vector3.z, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, new Vector3(entry.Data1.x, entry.Data1.y, entry.Data1.z));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 218)]
	public unsafe void Set(StringToken token, Vector4 vector4)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = vector4
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, in entry.Data1);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 228)]
	public unsafe void Set(StringToken token, int i)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(i, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, (int)entry.Data1.x);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 238)]
	public unsafe void Set(StringToken token, bool b)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(b ? 1 : 0, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, (int)entry.Data1.x != 0);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 248)]
	public unsafe void Set(StringToken token, Matrix matrix)
	{
		Entry data = new Entry
		{
			Token = token
		};
		Unsafe.As<Vector4, Matrix>(ref data.Data1) = matrix;
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), data);
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, in Unsafe.As<Vector4, Matrix>(ref entry.Data1));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 260)]
	public unsafe void Set(StringToken token, GpuBuffer buffer)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Object2 = buffer
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, (GpuBuffer)entry.Object2);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 270)]
	public unsafe void Set(StringToken token, Texture texture)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Object2 = texture
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.Set(in entry.Token, (Texture)entry.Object2, -1);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 280)]
	public unsafe void SetCombo(StringToken token, int value)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(value, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.SetCombo(in entry.Token, (int)entry.Data1.x);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 290)]
	public unsafe void SetCombo(StringToken token, bool value)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(value ? 1 : 0, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.SetCombo(in entry.Token, (int)entry.Data1.x != 0);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 300)]
	public unsafe void SetCombo<T>(StringToken token, T t) where T : unmanaged, Enum
	{
		int num = Unsafe.SizeOf<T>() switch
		{
			1 => Unsafe.As<T, byte>(ref t), 
			2 => Unsafe.As<T, short>(ref t), 
			8 => (int)Unsafe.As<T, long>(ref t), 
			_ => Unsafe.As<T, int>(ref t), 
		};
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(num, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.SetCombo(in entry.Token, (int)entry.Data1.x);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 317)]
	public unsafe void SetConstantBuffer<T>(StringToken token, T data) where T : unmanaged
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Object2 = data
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Attributes.SetData(in entry.Token, (T)entry.Object2);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 327)]
	public unsafe void SetGlobal(StringToken token, GpuBuffer buffer)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Object2 = buffer
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, (GpuBuffer)entry.Object2);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 337)]
	public unsafe void SetGlobal(StringToken token, int i)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(i, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, (int)entry.Data1.x);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 347)]
	public unsafe void SetGlobal(StringToken token, bool b)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(b ? 1 : 0, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, (int)entry.Data1.x != 0);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 357)]
	public unsafe void SetGlobal(StringToken token, float f)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(f, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, entry.Data1.x);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 367)]
	public void SetGlobal(StringToken token, double f)
	{
		SetGlobal(token, (float)f);
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 369)]
	public unsafe void SetGlobal(StringToken token, Vector2 vector2)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(vector2.x, vector2.y, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, new Vector2(entry.Data1.x, entry.Data1.y));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 379)]
	public unsafe void SetGlobal(StringToken token, Vector3 vector3)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = new Vector4(vector3.x, vector3.y, vector3.z, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, new Vector3(entry.Data1.x, entry.Data1.y, entry.Data1.z));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 389)]
	public unsafe void SetGlobal(StringToken token, Vector4 vector4)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Data1 = vector4
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, in entry.Data1);
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 399)]
	public unsafe void SetGlobal(StringToken token, Matrix matrix)
	{
		Entry data = new Entry
		{
			Token = token
		};
		Unsafe.As<Vector4, Matrix>(ref data.Data1) = matrix;
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), data);
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, in Unsafe.As<Vector4, Matrix>(ref entry.Data1));
		}
	}

	[Obsolete]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 411)]
	public unsafe void SetGlobal(StringToken token, Texture texture)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Token = token,
			Object2 = texture
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.FrameAttributes.Set(in entry.Token, (Texture)entry.Object2, -1);
		}
	}

	/// <summary>
	/// Takes a copy of the framebuffer and returns a handle to it
	/// </summary>
	/// <param name="token"></param>
	/// <param name="withMips">Generates mipmaps on the grabbed texture filtered with gaussian blur for each mip</param>
	/// <returns></returns>
	[Obsolete]
	[Description("Takes a copy of the framebuffer and returns a handle to it")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 427)]
	public RenderTargetHandle GrabFrameTexture(string token, [Description("Generates mipmaps on the grabbed texture filtered with gaussian blur for each mip")] bool withMips = false)
	{
		return Attributes.GrabFrameTexture(token, withMips);
	}

	/// <summary>
	/// Takes a copy of the depthbuffer and returns a handle to it
	/// </summary>
	/// <param name="token"></param>
	/// <returns></returns>
	[Obsolete]
	[Description("Takes a copy of the depthbuffer and returns a handle to it")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 435)]
	public RenderTargetHandle GrabDepthTexture(string token)
	{
		return Attributes.GrabDepthTexture(token);
	}

	/// <summary>
	/// Run this CommandList here
	/// </summary>
	[Description("Run this CommandList here")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 441)]
	public unsafe void InsertList(CommandList otherBuffer)
	{
		if (otherBuffer != this)
		{
			AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object1 = otherBuffer
			});
		}
		unsafe static void Execute(ref Entry entry, CommandList commandList)
		{
			CommandList commandList2 = (CommandList)entry.Object1;
			if (commandList2.Enabled)
			{
				State state = commandList2.state;
				commandList2.state = commandList.state;
				using (commandList2._lock.EnterScope())
				{
					if (commandList2._resources != null)
					{
						foreach (IResource resource in commandList2._resources)
						{
							resource.BeginExecute();
						}
					}
					for (int i = 0; i < commandList2._entries.Count; i++)
					{
						Entry entry2 = commandList2._entries[i];
						entry2.Execute(ref entry2, commandList2);
					}
				}
				commandList2.state = state;
			}
		}
	}

	/// <summary>
	/// Run this command list
	/// </summary>
	[Description("Run this command list")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 485)]
	internal void ExecuteOnRenderThread()
	{
		if (!Enabled)
		{
			return;
		}
		using (_lock.EnterScope())
		{
			OpenScope open = OpenScopeFor(_sampler);
			try
			{
				ExecuteEntries();
			}
			catch (Exception exception)
			{
				GlobalSystemNamespace.Log.Warning(exception, $"Error when executing CommandList {_debugName}");
			}
			finally
			{
				CloseScope(Graphics.Context, open);
			}
		}
	}

	/// <summary>
	/// Draws a single model at the given Transform immediately.
	/// </summary>
	/// <param name="model">The model to draw</param>
	/// <param name="transform">Transform to draw the model at</param>
	/// <param name="attributes">Optional attributes to apply only for this draw call</param>
	[Description("Draws a single model at the given Transform immediately.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 527)]
	public unsafe void DrawModel([Description("The model to draw")] Model model, [Description("Transform to draw the model at")] Transform transform, [Description("Optional attributes to apply only for this draw call")] RenderAttributes attributes = null)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = model,
			Object2 = attributes,
			Data1 = new Vector4(transform.Position.x, transform.Position.y, transform.Position.z, transform.Scale.x),
			Data2 = new Vector4(transform.Scale.y, transform.Scale.z, transform.Rotation.x, transform.Rotation.y),
			Data3 = new Vector4(transform.Rotation.z, transform.Rotation.w, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Vector3 position = new Vector3(entry.Data1.x, entry.Data1.y, entry.Data1.z);
			Vector3 scale = new Vector3(entry.Data1.w, entry.Data2.x, entry.Data2.y);
			Rotation rotation = new Rotation(entry.Data2.z, entry.Data2.w, entry.Data3.x, entry.Data3.y);
			Transform transform2 = new Transform
			{
				Position = position,
				Scale = scale,
				Rotation = rotation
			};
			Graphics.DrawModel((Model)entry.Object1, transform2, (RenderAttributes)entry.Object2);
		}
	}

	/// <summary>
	/// Draws multiple instances of a model using GPU instancing at a specific LOD level.
	///
	/// Use `GetTransformMatrix( int instance )` in shaders to access the instance transform.
	///
	/// There is a limit of 1,048,576 transform slots per frame when using this method.
	/// </summary>
	/// <param name="model">The model to draw</param>
	/// <param name="transforms">Instance transform data to draw</param>
	/// <param name="lodLevel">LOD level to render (0 = highest detail)</param>
	/// <param name="attributes">Optional attributes to apply only for this draw call</param>
	[Description("Draws multiple instances of a model using GPU instancing at a specific LOD level. Use `GetTransformMatrix( int instance )` in shaders to access the instance transform. There is a limit of 1,048,576 transform slots per frame when using this method.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 560)]
	public unsafe void DrawModelInstanced([Description("The model to draw")] Model model, [Description("Instance transform data to draw")] Span<Transform> transforms, [Description("LOD level to render (0 = highest detail)")] int lodLevel, [Description("Optional attributes to apply only for this draw call")] RenderAttributes attributes = null)
	{
		Transform[] @object = transforms.ToArray();
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = model,
			Object5 = @object,
			Data1 = new Vector4(lodLevel, 0f, 0f, 0f),
			Object2 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawModelInstanced((Model)entry.Object1, ((Transform[])entry.Object5).AsSpan(), (int)entry.Data1.x, (RenderAttributes)entry.Object2);
		}
	}

	/// <summary>
	/// Draws multiple instances of a model using GPU instancing, assuming standard implemented shaders.
	///
	/// Use `GetTransformMatrix( int instance )` in shaders to access the instance transform.
	///
	/// There is a limit of 1,048,576 transform slots per frame when using this method.
	/// </summary>
	/// <param name="model">The model to draw</param>
	/// <param name="transforms">Instance transform data to draw</param>
	/// <param name="attributes">Optional attributes to apply only for this draw call</param>
	[Description("Draws multiple instances of a model using GPU instancing, assuming standard implemented shaders. Use `GetTransformMatrix( int instance )` in shaders to access the instance transform. There is a limit of 1,048,576 transform slots per frame when using this method.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 581)]
	public unsafe void DrawModelInstanced([Description("The model to draw")] Model model, [Description("Instance transform data to draw")] Span<Transform> transforms, [Description("Optional attributes to apply only for this draw call")] RenderAttributes attributes = null)
	{
		Transform[] @object = transforms.ToArray();
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = model,
			Object5 = @object,
			Object2 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawModelInstanced((Model)entry.Object1, ((Transform[])entry.Object5).AsSpan(), (RenderAttributes)entry.Object2);
		}
	}

	/// <summary>
	/// Draws multiple instances of a model using GPU instancing with the number of instances being provided by indirect draw arguments.
	/// Use `SV_InstanceID` semantic in shaders to access the rendered instance.
	/// </summary>
	/// <param name="model">The model to draw</param>
	/// <param name="buffer">The GPU buffer containing the DrawIndirectArguments</param>
	/// <param name="bufferOffset">Optional offset in the GPU buffer</param>
	/// <param name="attributes">Optional attributes to apply only for this draw call</param>
	[Description("Draws multiple instances of a model using GPU instancing with the number of instances being provided by indirect draw arguments. Use `SV_InstanceID` semantic in shaders to access the rendered instance.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 602)]
	public unsafe void DrawModelInstancedIndirect([Description("The model to draw")] Model model, [Description("The GPU buffer containing the DrawIndirectArguments")] GpuBuffer buffer, [Description("Optional offset in the GPU buffer")] int bufferOffset = 0, [Description("Optional attributes to apply only for this draw call")] RenderAttributes attributes = null)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = model,
			Object2 = buffer,
			Data1 = new Vector4(bufferOffset, 0f, 0f, 0f),
			Object3 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawModelInstancedIndirect((Model)entry.Object1, (GpuBuffer)entry.Object2, (int)entry.Data1.x, (RenderAttributes)entry.Object3);
		}
	}

	/// <summary>
	/// Draws instances of a model using GPU instancing, with per-instance transforms read from
	/// <paramref name="transformBuffer" /> and the instance count provided by indirect draw arguments.
	/// Feeds the standard `GetTransformMatrix()` path, so normal/custom material shaders render unchanged.
	/// </summary>
	/// <param name="model">The model to draw</param>
	/// <param name="transformBuffer">Per-instance transforms, indexed 0..count-1</param>
	/// <param name="indirectArgs">Buffer containing the DrawIndexedInstancedArguments</param>
	/// <param name="argsOffset">Optional byte offset into the indirect args buffer</param>
	/// <param name="lodLevel">LOD level to render (0 = highest detail)</param>
	/// <param name="attributes">Optional attributes to apply only for this draw call</param>
	[Description("Draws instances of a model using GPU instancing, with per-instance transforms read from <span style=\"color: #9CDCFE;\">transformBuffer</span> and the instance count provided by indirect draw arguments. Feeds the standard `GetTransformMatrix()` path, so normal/custom material shaders render unchanged.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 623)]
	public unsafe void DrawModelInstancedIndirect([Description("The model to draw")] Model model, [Description("Per-instance transforms, indexed 0..count-1")] GpuBuffer transformBuffer, [Description("Buffer containing the DrawIndexedInstancedArguments")] GpuBuffer indirectArgs, [Description("Optional byte offset into the indirect args buffer")] int argsOffset = 0, [Description("LOD level to render (0 = highest detail)")] int lodLevel = 0, [Description("Optional attributes to apply only for this draw call")] RenderAttributes attributes = null)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = model,
			Object2 = transformBuffer,
			Object3 = indirectArgs,
			Data1 = new Vector4(argsOffset, lodLevel, 0f, 0f),
			Object4 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawModelInstancedIndirect((Model)entry.Object1, (GpuBuffer)entry.Object2, (GpuBuffer)entry.Object3, (int)entry.Data1.x, (int)entry.Data1.y, (RenderAttributes)entry.Object4);
		}
	}

	/// <summary>
	/// Draws multiple instances of a model using GPU instancing.
	/// This is similar to <see cref="M:Sandbox.Rendering.CommandList.DrawModelInstancedIndirect(Sandbox.Model,Sandbox.GpuBuffer,System.Int32,Sandbox.RenderAttributes)" />,
	/// except the count is provided from the CPU rather than via a GPU buffer.
	///
	/// Use `SV_InstanceID` semantic in shaders to access the rendered instance.
	/// </summary>
	/// <param name="model">The model to draw</param>
	/// <param name="count">The number of instances to draw</param>
	/// <param name="attributes">Optional attributes to apply only for this draw call</param>
	[Description("Draws multiple instances of a model using GPU instancing. This is similar to <span style=\"color: #4EC9B0;\">CommandList</span>.<span style=\"color: #DCDCAA;\">DrawModelInstancedIndirect</span>(<span style=\"color: #4EC9B0;\">Model</span>,<span style=\"color: #4EC9B0;\">GpuBuffer</span>,<span style=\"color: #86C691;\">int</span>,<span style=\"color: #4EC9B0;\">RenderAttributes</span>), except the count is provided from the CPU rather than via a GPU buffer. Use `SV_InstanceID` semantic in shaders to access the rendered instance.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 643)]
	public unsafe void DrawModelInstanced([Description("The model to draw")] Model model, [Description("The number of instances to draw")] int count, [Description("Optional attributes to apply only for this draw call")] RenderAttributes attributes = null)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = model,
			Data1 = new Vector4(count, 0f, 0f, 0f),
			Object2 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawModelInstanced((Model)entry.Object1, (int)entry.Data1.x, (RenderAttributes)entry.Object2);
		}
	}

	/// <summary>
	/// Draws geometry using a vertex buffer and material.
	/// </summary>
	/// <typeparam name="T">The vertex type used for vertex layout.</typeparam>
	/// <param name="vertexBuffer">The GPU buffer containing vertex data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="startVertex">The starting vertex index for rendering.</param>
	/// <param name="vertexCount">The number of vertices to render. If 0, uses all vertices in the buffer.</param>
	/// <param name="attributes">Optional render attributes to apply only for this draw call.</param>
	/// <param name="primitiveType">The type of primitives to render. Defaults to triangles.</param>
	[Description("Draws geometry using a vertex buffer and material.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 663)]
	public unsafe void Draw<T>([Description("The GPU buffer containing vertex data.")] GpuBuffer<T> vertexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The starting vertex index for rendering.")] int startVertex = 0, [Description("The number of vertices to render. If 0, uses all vertices in the buffer.")] int vertexCount = 0, [Description("Optional render attributes to apply only for this draw call.")] RenderAttributes attributes = null, [Description("The type of primitives to render. Defaults to triangles.")] Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles) where T : unmanaged
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = vertexBuffer,
			Object2 = material,
			Data1 = new Vector4(startVertex, vertexCount, (float)primitiveType, 0f),
			Object3 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Draw((GpuBuffer<T>)entry.Object1, (Material)entry.Object2, (int)entry.Data1.x, (int)entry.Data1.y, (RenderAttributes)entry.Object3, (Graphics.PrimitiveType)entry.Data1.z);
		}
	}

	/// <summary>
	/// Draws indexed geometry using vertex and index buffers.
	/// </summary>
	/// <typeparam name="T">The vertex type used for vertex layout.</typeparam>
	/// <param name="vertexBuffer">The GPU buffer containing vertex data.</param>
	/// <param name="indexBuffer">The GPU buffer containing index data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="startIndex">The starting index for rendering.</param>
	/// <param name="indexCount">The number of indices to render. If 0, uses all indices in the buffer.</param>
	/// <param name="attributes">Optional render attributes to apply only for this draw call.</param>
	/// <param name="primitiveType">The type of primitives to render. Defaults to triangles.</param>
	[Description("Draws indexed geometry using vertex and index buffers.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 684)]
	public unsafe void DrawIndexed<T>([Description("The GPU buffer containing vertex data.")] GpuBuffer<T> vertexBuffer, [Description("The GPU buffer containing index data.")] GpuBuffer indexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The starting index for rendering.")] int startIndex = 0, [Description("The number of indices to render. If 0, uses all indices in the buffer.")] int indexCount = 0, [Description("Optional render attributes to apply only for this draw call.")] RenderAttributes attributes = null, [Description("The type of primitives to render. Defaults to triangles.")] Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles) where T : unmanaged
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = vertexBuffer,
			Object2 = indexBuffer,
			Object3 = material,
			Data1 = new Vector4(startIndex, indexCount, (float)primitiveType, 0f),
			Object4 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Draw((GpuBuffer<T>)entry.Object1, (GpuBuffer)entry.Object2, (Material)entry.Object3, (int)entry.Data1.x, (int)entry.Data1.y, (RenderAttributes)entry.Object4, (Graphics.PrimitiveType)entry.Data1.z);
		}
	}

	/// <summary>
	/// Draws instanced geometry using a vertex buffer and indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <typeparam name="T">The vertex type used for vertex layout.</typeparam>
	/// <param name="vertexBuffer">The GPU buffer containing vertex data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Optional element offset into the indirect buffer.</param>
	/// <param name="attributes">Optional render attributes to apply only for this draw call.</param>
	/// <param name="primitiveType">The type of primitives to render. Defaults to triangles.</param>
	[Description("Draws instanced geometry using a vertex buffer and indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 704)]
	public void DrawInstancedIndirect<T>([Description("The GPU buffer containing vertex data.")] GpuBuffer<T> vertexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Optional element offset into the indirect buffer.")] uint bufferOffset = 0u, [Description("Optional render attributes to apply only for this draw call.")] RenderAttributes attributes = null, [Description("The type of primitives to render. Defaults to triangles.")] Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles) where T : unmanaged
	{
		DrawInstancedIndirect(vertexBuffer, material, indirectBuffer, bufferOffset, attributes, primitiveType, 1u);
	}

	/// <summary>
	/// Draws instanced geometry using a vertex buffer, executing one or more indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <typeparam name="T">The vertex type used for vertex layout.</typeparam>
	/// <param name="vertexBuffer">The GPU buffer containing vertex data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Element offset into the indirect buffer.</param>
	/// <param name="attributes">Render attributes to apply only for this draw call, or null.</param>
	/// <param name="primitiveType">The type of primitives to render.</param>
	/// <param name="drawCount">Number of draw argument structs to read and execute.</param>
	/// <param name="stride">Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.</param>
	[Description("Draws instanced geometry using a vertex buffer, executing one or more indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 719)]
	public unsafe void DrawInstancedIndirect<T>([Description("The GPU buffer containing vertex data.")] GpuBuffer<T> vertexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Element offset into the indirect buffer.")] uint bufferOffset, [Description("Render attributes to apply only for this draw call, or null.")] RenderAttributes attributes, [Description("The type of primitives to render.")] Graphics.PrimitiveType primitiveType, [Description("Number of draw argument structs to read and execute.")] uint drawCount, [Description("Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.")] uint stride = 0u) where T : unmanaged
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = vertexBuffer,
			Object2 = material,
			Object3 = indirectBuffer,
			Data1 = new Vector4(bufferOffset, (float)primitiveType, drawCount, stride),
			Object4 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawInstancedIndirect((GpuBuffer<T>)entry.Object1, (Material)entry.Object2, (GpuBuffer)entry.Object3, (uint)entry.Data1.x, (RenderAttributes)entry.Object4, (Graphics.PrimitiveType)entry.Data1.y, (uint)entry.Data1.z, (uint)entry.Data1.w);
		}
	}

	/// <summary>
	/// Draws instanced geometry using indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <remarks>
	/// Vertex data is accessed in shader through buffer attribute and SV_VertexID.
	/// </remarks>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Optional element offset into the indirect buffer.</param>
	/// <param name="attributes">Optional render attributes to apply only for this draw call.</param>
	/// <param name="primitiveType">The type of primitives to render. Defaults to triangles.</param>
	[Description("Draws instanced geometry using indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 740)]
	public void DrawInstancedIndirect([Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Optional element offset into the indirect buffer.")] uint bufferOffset = 0u, [Description("Optional render attributes to apply only for this draw call.")] RenderAttributes attributes = null, [Description("The type of primitives to render. Defaults to triangles.")] Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles)
	{
		DrawInstancedIndirect(material, indirectBuffer, bufferOffset, attributes, primitiveType, 1u);
	}

	/// <summary>
	/// Draws instanced geometry, executing one or more indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <remarks>
	/// Vertex data is accessed in shader through buffer attribute and SV_VertexID.
	/// </remarks>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Element offset into the indirect buffer.</param>
	/// <param name="attributes">Render attributes to apply only for this draw call, or null.</param>
	/// <param name="primitiveType">The type of primitives to render.</param>
	/// <param name="drawCount">Number of draw argument structs to read and execute.</param>
	/// <param name="stride">Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.</param>
	[Description("Draws instanced geometry, executing one or more indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 756)]
	public unsafe void DrawInstancedIndirect([Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Element offset into the indirect buffer.")] uint bufferOffset, [Description("Render attributes to apply only for this draw call, or null.")] RenderAttributes attributes, [Description("The type of primitives to render.")] Graphics.PrimitiveType primitiveType, [Description("Number of draw argument structs to read and execute.")] uint drawCount, [Description("Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.")] uint stride = 0u)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = material,
			Object2 = indirectBuffer,
			Data1 = new Vector4(bufferOffset, (float)primitiveType, drawCount, stride),
			Object3 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawInstancedIndirect((Material)entry.Object1, (GpuBuffer)entry.Object2, (uint)entry.Data1.x, (RenderAttributes)entry.Object3, (Graphics.PrimitiveType)entry.Data1.y, (uint)entry.Data1.z, (uint)entry.Data1.w);
		}
	}

	/// <summary>
	/// Draws instanced indexed geometry using indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <typeparam name="T">The vertex type used for vertex layout.</typeparam>
	/// <param name="vertexBuffer">The GPU buffer containing vertex data.</param>
	/// <param name="indexBuffer">The GPU buffer containing index data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Optional element offset into the indirect buffer.</param>
	/// <param name="attributes">Optional render attributes to apply only for this draw call.</param>
	/// <param name="primitiveType">The type of primitives to render. Defaults to triangles.</param>
	[Description("Draws instanced indexed geometry using indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 777)]
	public void DrawIndexedInstancedIndirect<T>([Description("The GPU buffer containing vertex data.")] GpuBuffer<T> vertexBuffer, [Description("The GPU buffer containing index data.")] GpuBuffer indexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Optional element offset into the indirect buffer.")] uint bufferOffset = 0u, [Description("Optional render attributes to apply only for this draw call.")] RenderAttributes attributes = null, [Description("The type of primitives to render. Defaults to triangles.")] Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles) where T : unmanaged
	{
		DrawIndexedInstancedIndirect(vertexBuffer, indexBuffer, material, indirectBuffer, bufferOffset, attributes, primitiveType, 1u);
	}

	/// <summary>
	/// Draws instanced indexed geometry, executing one or more indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <typeparam name="T">The vertex type used for vertex layout.</typeparam>
	/// <param name="vertexBuffer">The GPU buffer containing vertex data.</param>
	/// <param name="indexBuffer">The GPU buffer containing index data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Element offset into the indirect buffer.</param>
	/// <param name="attributes">Render attributes to apply only for this draw call, or null.</param>
	/// <param name="primitiveType">The type of primitives to render.</param>
	/// <param name="drawCount">Number of draw argument structs to read and execute.</param>
	/// <param name="stride">Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.</param>
	[Description("Draws instanced indexed geometry, executing one or more indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 793)]
	public unsafe void DrawIndexedInstancedIndirect<T>([Description("The GPU buffer containing vertex data.")] GpuBuffer<T> vertexBuffer, [Description("The GPU buffer containing index data.")] GpuBuffer indexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Element offset into the indirect buffer.")] uint bufferOffset, [Description("Render attributes to apply only for this draw call, or null.")] RenderAttributes attributes, [Description("The type of primitives to render.")] Graphics.PrimitiveType primitiveType, [Description("Number of draw argument structs to read and execute.")] uint drawCount, [Description("Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.")] uint stride = 0u) where T : unmanaged
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = vertexBuffer,
			Object2 = indexBuffer,
			Object3 = material,
			Object4 = indirectBuffer,
			Data1 = new Vector4(bufferOffset, (float)primitiveType, drawCount, stride),
			Object5 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawIndexedInstancedIndirect((GpuBuffer<T>)entry.Object1, (GpuBuffer)entry.Object2, (Material)entry.Object3, (GpuBuffer)entry.Object4, (uint)entry.Data1.x, (RenderAttributes)entry.Object5, (Graphics.PrimitiveType)entry.Data1.y, (uint)entry.Data1.z, (uint)entry.Data1.w);
		}
	}

	/// <summary>
	/// Draws instanced indexed geometry using indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <remarks>
	/// Vertex data is accessed in shader through buffer attribute and SV_VertexID.
	/// </remarks>
	/// <param name="indexBuffer">The GPU buffer containing index data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Optional element offset into the indirect buffer.</param>
	/// <param name="attributes">Optional render attributes to apply only for this draw call.</param>
	/// <param name="primitiveType">The type of primitives to render. Defaults to triangles.</param>
	[Description("Draws instanced indexed geometry using indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 815)]
	public void DrawIndexedInstancedIndirect([Description("The GPU buffer containing index data.")] GpuBuffer indexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Optional element offset into the indirect buffer.")] uint bufferOffset = 0u, [Description("Optional render attributes to apply only for this draw call.")] RenderAttributes attributes = null, [Description("The type of primitives to render. Defaults to triangles.")] Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles)
	{
		DrawIndexedInstancedIndirect(indexBuffer, material, indirectBuffer, bufferOffset, attributes, primitiveType, 1u);
	}

	/// <summary>
	/// Draws instanced indexed geometry, executing one or more indirect draw arguments stored in a GPU buffer.
	/// </summary>
	/// <remarks>
	/// Vertex data is accessed in shader through buffer attribute and SV_VertexID.
	/// </remarks>
	/// <param name="indexBuffer">The GPU buffer containing index data.</param>
	/// <param name="material">The material to use for rendering.</param>
	/// <param name="indirectBuffer">The GPU buffer containing indirect draw arguments.</param>
	/// <param name="bufferOffset">Element offset into the indirect buffer.</param>
	/// <param name="attributes">Render attributes to apply only for this draw call, or null.</param>
	/// <param name="primitiveType">The type of primitives to render.</param>
	/// <param name="drawCount">Number of draw argument structs to read and execute.</param>
	/// <param name="stride">Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.</param>
	[Description("Draws instanced indexed geometry, executing one or more indirect draw arguments stored in a GPU buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 832)]
	public unsafe void DrawIndexedInstancedIndirect([Description("The GPU buffer containing index data.")] GpuBuffer indexBuffer, [Description("The material to use for rendering.")] Material material, [Description("The GPU buffer containing indirect draw arguments.")] GpuBuffer indirectBuffer, [Description("Element offset into the indirect buffer.")] uint bufferOffset, [Description("Render attributes to apply only for this draw call, or null.")] RenderAttributes attributes, [Description("The type of primitives to render.")] Graphics.PrimitiveType primitiveType, [Description("Number of draw argument structs to read and execute.")] uint drawCount, [Description("Byte stride between draw argument structs. Use this when your indirect buffer packs extra per-draw userdata. Must be a multiple of 4 and at least the size of the draw argument struct. 0 uses the natural size.")] uint stride = 0u)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = indexBuffer,
			Object2 = material,
			Object3 = indirectBuffer,
			Data1 = new Vector4(bufferOffset, (float)primitiveType, drawCount, stride),
			Object4 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawIndexedInstancedIndirect((GpuBuffer)entry.Object1, (Material)entry.Object2, (GpuBuffer)entry.Object3, (uint)entry.Data1.x, (RenderAttributes)entry.Object4, (Graphics.PrimitiveType)entry.Data1.y, (uint)entry.Data1.z, (uint)entry.Data1.w);
		}
	}

	/// <summary>
	/// Draws indexed geometry with instancing. Each instance shares the same index buffer.
	/// </summary>
	[Description("Draws indexed geometry with instancing. Each instance shares the same index buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 845)]
	public unsafe void DrawIndexedInstanced(GpuBuffer indexBuffer, Material material, int instanceCount, RenderAttributes attributes = null, Graphics.PrimitiveType primitiveType = Graphics.PrimitiveType.Triangles)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = indexBuffer,
			Object2 = material,
			Data1 = new Vector4(instanceCount, (float)primitiveType, 0f, 0f),
			Object3 = attributes
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.DrawIndexedInstanced((GpuBuffer)entry.Object1, (Material)entry.Object2, (int)entry.Data1.x, (RenderAttributes)entry.Object3, (Graphics.PrimitiveType)entry.Data1.y);
		}
	}

	/// <summary>
	/// Get a screen sized temporary render target. You should release the returned handle when you're done to return the textures to the pool.
	/// </summary>
	/// <param name="name">The name of the render target handle.</param>
	/// <param name="sizeFactor">Divide the screen size by this factor. 2 would be half screen sized. 1 for full screen sized.</param>
	/// <param name="format">The format for the color buffer. If set to default we'll use whatever the current pipeline is using.</param>
	/// <param name="numMips">Number of mips you want in this texture. You probably don't want this unless you want to generate mips in a second pass.</param>
	/// <returns>A RenderTarget that is ready to render to.</returns>
	[Description("Get a screen sized temporary render target. You should release the returned handle when you're done to return the textures to the pool.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 863)]
	[return: Description("A RenderTarget that is ready to render to.")]
	public unsafe RenderTargetHandle GetRenderTarget([Description("The name of the render target handle.")] string name, [Description("The format for the color buffer. If set to default we'll use whatever the current pipeline is using.")] ImageFormat format, [Description("Number of mips you want in this texture. You probably don't want this unless you want to generate mips in a second pass.")] int numMips = 1, [Description("Divide the screen size by this factor. 2 would be half screen sized. 1 for full screen sized.")] int sizeFactor = 1)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = name,
			Data1 = new Vector4((float)format, sizeFactor, numMips, 0f)
		});
		return new RenderTargetHandle
		{
			Name = name
		};
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget temporary = RenderTarget.GetTemporary((int)entry.Data1.y, (ImageFormat)entry.Data1.x, ImageFormat.None, MultisampleAmount.MultisampleNone, (int)entry.Data1.z);
			commandList.state.renderTargets[(string)entry.Object5] = temporary;
		}
	}

	/// <summary>
	/// Get a screen sized temporary render target. You should release the returned handle when you're done to return the textures to the pool.
	/// </summary>
	/// <param name="name">The name of the render target handle.</param>
	/// <param name="sizeFactor">Divide the screen size by this factor. 2 would be half screen sized. 1 for full screen sized.</param>
	/// <param name="colorFormat">The format for the color buffer. If set to default we'll use whatever the current pipeline is using.</param>
	/// <param name="depthFormat">The format for the depth buffer.</param>
	/// <param name="msaa">The number of msaa samples you'd like. Msaa render textures are a pain in the ass so you're probably gonna regret trying to use this.</param>
	/// <param name="numMips">Number of mips you want in this texture. You probably don't want this unless you want to generate mips in a second pass.</param>
	/// <returns>A RenderTarget that is ready to render to.</returns>
	[Description("Get a screen sized temporary render target. You should release the returned handle when you're done to return the textures to the pool.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 888)]
	[return: Description("A RenderTarget that is ready to render to.")]
	public unsafe RenderTargetHandle GetRenderTarget([Description("The name of the render target handle.")] string name, [Description("Divide the screen size by this factor. 2 would be half screen sized. 1 for full screen sized.")] int sizeFactor = 1, [Description("The format for the color buffer. If set to default we'll use whatever the current pipeline is using.")] ImageFormat colorFormat = ImageFormat.Default, [Description("The format for the depth buffer.")] ImageFormat depthFormat = ImageFormat.Default, [Description("The number of msaa samples you'd like. Msaa render textures are a pain in the ass so you're probably gonna regret trying to use this.")] MultisampleAmount msaa = MultisampleAmount.MultisampleNone, [Description("Number of mips you want in this texture. You probably don't want this unless you want to generate mips in a second pass.")] int numMips = 1)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = name,
			Data1 = new Vector4(sizeFactor, (float)colorFormat, (float)depthFormat, (float)msaa),
			Data2 = new Vector4(numMips, 0f, 0f, 0f)
		});
		return new RenderTargetHandle
		{
			Name = name
		};
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget temporary = RenderTarget.GetTemporary((int)entry.Data1.x, (ImageFormat)entry.Data1.y, (ImageFormat)entry.Data1.z, (MultisampleAmount)entry.Data1.w, (int)entry.Data2.x, (string)entry.Object5);
			commandList.state.renderTargets[(string)entry.Object5] = temporary;
		}
	}

	/// <summary>
	/// Get a temporary render target. You should release the returned handle when you're done to return the textures to the pool.
	/// </summary>
	/// <param name="name">The name of the render target handle.</param>
	/// <param name="width">Width of the render target you want.</param>
	/// <param name="height">Height of the render target you want.</param>
	/// <param name="colorFormat">The format for the color buffer. If set to default we'll use whatever the current pipeline is using.</param>
	/// <param name="depthFormat">The format for the depth buffer.</param>
	/// <param name="msaa">The number of msaa samples you'd like. Msaa render textures are a pain in the ass so you're probably gonna regret trying to use this.</param>
	/// <param name="numMips">Number of mips you want in this texture. You probably don't want this unless you want to generate mips in a second pass.</param>
	/// <returns>A RenderTarget that is ready to render to.</returns>
	[Description("Get a temporary render target. You should release the returned handle when you're done to return the textures to the pool.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 911)]
	[return: Description("A RenderTarget that is ready to render to.")]
	public unsafe RenderTargetHandle GetRenderTarget([Description("The name of the render target handle.")] string name, [Description("Width of the render target you want.")] int width, [Description("Height of the render target you want.")] int height, [Description("The format for the color buffer. If set to default we'll use whatever the current pipeline is using.")] ImageFormat colorFormat = ImageFormat.Default, [Description("The format for the depth buffer.")] ImageFormat depthFormat = ImageFormat.Default, [Description("The number of msaa samples you'd like. Msaa render textures are a pain in the ass so you're probably gonna regret trying to use this.")] MultisampleAmount msaa = MultisampleAmount.MultisampleNone, [Description("Number of mips you want in this texture. You probably don't want this unless you want to generate mips in a second pass.")] int numMips = 1)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = name,
			Data1 = new Vector4(width, height, (float)colorFormat, (float)depthFormat),
			Data2 = new Vector4((float)msaa, numMips, 0f, 0f)
		});
		return new RenderTargetHandle
		{
			Name = name
		};
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget temporary = RenderTarget.GetTemporary((int)entry.Data1.x, (int)entry.Data1.y, (ImageFormat)entry.Data1.z, (ImageFormat)entry.Data1.w, (MultisampleAmount)entry.Data2.x, (int)entry.Data2.y, (string)entry.Object5);
			commandList.state.renderTargets[(string)entry.Object5] = temporary;
		}
	}

	/// <summary>
	/// We're no longer using this RT, return it to the pool
	/// </summary>
	[Description("We're no longer using this RT, return it to the pool")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 926)]
	public unsafe void ReleaseRenderTarget(RenderTargetHandle handle)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = handle.Name
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			if (commandList.state.renderTargets.Remove((string)entry.Object5, out var value))
			{
				value.Dispose();
			}
		}
	}

	/// <summary>
	/// Set the current render target. Setting this will bind the render target and change the viewport to match it.
	/// </summary>
	[Description("Set the current render target. Setting this will bind the render target and change the viewport to match it.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 942)]
	public unsafe void SetRenderTarget(RenderTargetHandle handle)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = handle.Name
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			if (!commandList.state.renderTargets.TryGetValue((string)entry.Object5, out var value))
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				Graphics.RenderTarget = value;
			}
		}
	}

	/// <summary>
	/// Set the current render target. Setting this will bind the render target and change the viewport to match it.
	/// </summary>
	[Description("Set the current render target. Setting this will bind the render target and change the viewport to match it.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 961)]
	public unsafe void SetRenderTarget(RenderTarget target)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = target
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.RenderTarget = (RenderTarget)entry.Object1;
		}
	}

	/// <summary>
	/// Save the render target and viewport active when this command executes.
	/// </summary>
	[Description("Save the render target and viewport active when this command executes.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 974)]
	internal unsafe void PushRenderTarget()
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), default(Entry));
		static void Execute(ref Entry entry, CommandList commandList)
		{
			commandList.state.renderTargetStack.Push((Graphics.RenderTarget, Graphics.Context.GetViewport()));
		}
	}

	/// <summary>
	/// Restore the most recently saved render target and viewport.
	/// </summary>
	[Description("Restore the most recently saved render target and viewport.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 987)]
	internal unsafe void PopRenderTarget()
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), default(Entry));
		static void Execute(ref Entry entry, CommandList commandList)
		{
			(RenderTarget, RenderViewport) tuple = commandList.state.renderTargetStack.Pop();
			(Graphics.RenderTarget, _) = tuple;
			Graphics.Context.SetViewport(tuple.Item2);
		}
	}

	/// <summary>
	/// Set the current render target. Setting this will bind the render target and change the viewport to match it.
	/// </summary>
	[Description("Set the current render target. Setting this will bind the render target and change the viewport to match it.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1002)]
	public unsafe void ClearRenderTarget()
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), default(Entry));
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.RenderTarget = null;
		}
	}

	/// <summary>
	/// Set the color texture from this named render target to this attribute
	/// </summary>
	[Obsolete]
	[Description("Set the color texture from this named render target to this attribute")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1015)]
	public void Set(StringToken token, RenderTargetHandle.ColorTextureRef buffer, int mip = -1)
	{
		Attributes.Set(token, buffer, mip);
	}

	/// <summary>
	/// Set the color texture from this named render target to this attribute
	/// </summary>
	[Obsolete]
	[Description("Set the color texture from this named render target to this attribute")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1021)]
	public void SetGlobal(StringToken token, RenderTargetHandle.ColorIndexRef buffer)
	{
		GlobalAttributes.Set(token, buffer);
	}

	/// <summary>
	/// Binds the given render target's color texture to a stable, pipeline-level bindless slot
	/// for this frame. This is how full-screen pipeline resources (ambient occlusion, screen-space
	/// reflections) are published to the rest of the pipeline: consumers read a fixed descriptor
	/// binding rather than a per-view render attribute. Because procedural layers build their
	/// command lists on threaded jobs, writing the result index into the shared frame attributes
	/// would race - this fixed slot is resolved single-threaded at submit, so it doesn't.
	/// </summary>
	[Description("Binds the given render target's color texture to a stable, pipeline-level bindless slot for this frame. This is how full-screen pipeline resources (ambient occlusion, screen-space reflections) are published to the rest of the pipeline: consumers read a fixed descriptor binding rather than a per-view render attribute. Because procedural layers build their command lists on threaded jobs, writing the result index into the shared frame attributes would race - this fixed slot is resolved single-threaded at submit, so it doesn't.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1032)]
	internal unsafe void SetPipelineTexture(PipelineTextureSlot slot, RenderTargetHandle.ColorTextureRef buffer)
	{
		if (slot < PipelineTextureSlot.AmbientOcclusion || slot >= PipelineTextureSlot.Count)
		{
			GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Invalid pipeline texture slot: {1}", DebugName ?? "CommandList", (int)slot));
		}
		else
		{
			AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object5 = buffer.Name,
				Data1 = new Vector4((float)slot, 0f, 0f, 0f)
			});
		}
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
			if (renderTarget == null)
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				CSceneSystem.SetPipelineTextureIndex((int)entry.Data1.x, renderTarget.ColorTarget.Index);
			}
		}
	}

	/// <inheritdoc cref="M:Sandbox.ComputeShader.Dispatch(System.Int32,System.Int32,System.Int32)" />
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1057)]
	public unsafe void DispatchCompute(ComputeShader compute, int threadsX, int threadsY, int threadsZ)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = compute,
			Data1 = new Vector4(threadsX, threadsY, threadsZ, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((ComputeShader)entry.Object1).DispatchWithAttributes(Graphics.Attributes, (int)entry.Data1.x, (int)entry.Data1.y, (int)entry.Data1.z);
		}
	}

	/// <inheritdoc cref="M:Sandbox.ComputeShader.DispatchIndirect(Sandbox.GpuBuffer,System.UInt32)" />
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1068)]
	public unsafe void DispatchComputeIndirect(ComputeShader compute, GpuBuffer indirectBuffer, uint indirectElementOffset = 0u)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = compute,
			Object2 = indirectBuffer,
			Data1 = new Vector4(indirectElementOffset, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((ComputeShader)entry.Object1).DispatchIndirectWithAttributes(Graphics.Attributes, (GpuBuffer)entry.Object2, (uint)entry.Data1.x);
		}
	}

	/// <inheritdoc cref="M:Sandbox.RayTracingShader.DispatchRaysWithAttributes(Sandbox.RenderAttributes,System.Int32,System.Int32,System.Int32)" />
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1079)]
	internal unsafe void DispatchRays(RayTracingShader raytracing, int threadsX, int threadsY, int threadsZ)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = raytracing,
			Data1 = new Vector4(threadsX, threadsY, threadsZ, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((RayTracingShader)entry.Object1).DispatchRaysWithAttributes(Graphics.Attributes, (int)entry.Data1.x, (int)entry.Data1.y, (int)entry.Data1.z);
		}
	}

	/// <inheritdoc cref="M:Sandbox.RayTracingShader.DispatchRaysIndirect(Sandbox.GpuBuffer,System.UInt32)" />
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1090)]
	internal unsafe void DispatchRaysIndirect(RayTracingShader raytracing, GpuBuffer indirectBuffer, uint indirectElementOffset = 0u)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = raytracing,
			Object2 = indirectBuffer,
			Data1 = new Vector4(indirectElementOffset, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((RayTracingShader)entry.Object1).DispatchRaysIndirectWithAttributes(Graphics.Attributes, (GpuBuffer)entry.Object2, (uint)entry.Data1.x);
		}
	}

	/// <summary>
	/// A handle to the viewport size divided by a factor. Useful for dispatching at half or quarter resolution.
	/// </summary>
	[Description("A handle to the viewport size divided by a factor. Useful for dispatching at half or quarter resolution.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1108)]
	public RenderTargetHandle.SizeHandle ViewportSizeScaled(int divisor)
	{
		return new RenderTargetHandle.SizeHandle
		{
			Name = "$vp",
			Divisor = Math.Max(1, divisor)
		};
	}

	/// <summary>
	/// Dispatch a compute shader
	/// </summary>
	[Description("Dispatch a compute shader")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1113)]
	public unsafe void DispatchCompute(ComputeShader compute, RenderTargetHandle.SizeHandle dimension)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = compute,
			Object5 = dimension.Name,
			Data1 = new Vector4(dimension.Divisor, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Vector3Int? dimension2 = commandList.GetDimension((string)entry.Object5, (int)entry.Data1.x);
			if (dimension2.HasValue)
			{
				((ComputeShader)entry.Object1).DispatchWithAttributes(Graphics.Attributes, dimension2.Value.x, dimension2.Value.y, dimension2.Value.z);
			}
		}
	}

	/// <summary>
	/// Dispatch a ray tracing shader
	/// </summary>
	[Description("Dispatch a ray tracing shader")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1129)]
	internal unsafe void DispatchRays(RayTracingShader raytracing, RenderTargetHandle.SizeHandle dimension)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = raytracing,
			Object5 = dimension.Name,
			Data1 = new Vector4(dimension.Divisor, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Vector3Int? dimension2 = commandList.GetDimension((string)entry.Object5, (int)entry.Data1.x);
			if (dimension2.HasValue)
			{
				((RayTracingShader)entry.Object1).DispatchRaysWithAttributes(Graphics.Attributes, dimension2.Value.x, dimension2.Value.y, dimension2.Value.z);
			}
		}
	}

	/// <summary>
	/// Called during rendering, convert RenderTargetHandle.SizeHandle to a dimension
	/// </summary>
	[Description("Called during rendering, convert RenderTargetHandle.SizeHandle to a dimension")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1145)]
	private Vector3Int? GetDimension(string name, int divisor = 0)
	{
		Vector3Int value;
		if (name == "$vp")
		{
			value = new Vector3Int(Graphics.Viewport.Width.CeilToInt(), Graphics.Viewport.Height.CeilToInt(), 1);
		}
		else
		{
			RenderTarget valueOrDefault = state.renderTargets.GetValueOrDefault(name);
			if (valueOrDefault == null)
			{
				return null;
			}
			value = new Vector3Int(valueOrDefault.Width, valueOrDefault.Height, 1);
		}
		if (divisor > 1)
		{
			value.x = Math.Max(1, value.x / divisor);
			value.y = Math.Max(1, value.y / divisor);
		}
		return value;
	}

	/// <summary>
	/// Clear the current drawing context to given color.
	/// </summary>
	/// <param name="color">Color to clear to.</param>
	/// <param name="clearColor">Whether to clear the color buffer at all.</param>
	/// <param name="clearDepth">Whether to clear the depth buffer.</param>
	/// <param name="clearStencil">Whether to clear the stencil buffer.</param>
	[Description("Clear the current drawing context to given color.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1177)]
	public unsafe void Clear([Description("Color to clear to.")] Color color, [Description("Whether to clear the color buffer at all.")] bool clearColor = true, [Description("Whether to clear the depth buffer.")] bool clearDepth = true, [Description("Whether to clear the stencil buffer.")] bool clearStencil = true)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Data1 = new Vector4(color.r, color.g, color.b, color.a),
			Data2 = new Vector4(clearColor ? 1 : 0, clearDepth ? 1 : 0, clearStencil ? 1 : 0, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Color color2 = new Color(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w);
			bool clearColor2 = (int)entry.Data2.x != 0;
			bool clearDepth2 = (int)entry.Data2.y != 0;
			bool clearStencil2 = (int)entry.Data2.z != 0;
			Graphics.Clear(color2, clearColor2, clearDepth2, clearStencil2);
		}
	}

	/// <summary>
	/// Clears the given texture to a solid color.
	/// </summary>
	/// <param name="texture">The texture to clear.</param>
	/// <param name="color">The color to clear to. Defaults to transparent black.</param>
	[Description("Clears the given texture to a solid color.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1197)]
	public unsafe void Clear([Description("The texture to clear.")] Texture texture, [Description("The color to clear to. Defaults to transparent black.")] Color color = default(Color))
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = texture,
			Data1 = new Vector4(color.r, color.g, color.b, color.a)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.Context.ClearTexture(((Texture)entry.Object1).native, new Color(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w));
		}
	}

	/// <summary>
	/// Clears the color texture of the given render target handle to a solid color.
	/// </summary>
	/// <param name="handle">The render target handle whose color texture to clear.</param>
	/// <param name="color">The color to clear to. Defaults to transparent black.</param>
	[Description("Clears the color texture of the given render target handle to a solid color.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1212)]
	public unsafe void Clear([Description("The render target handle whose color texture to clear.")] RenderTargetHandle handle, [Description("The color to clear to. Defaults to transparent black.")] Color color = default(Color))
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = handle.ColorTexture.Name,
			Data1 = new Vector4(color.r, color.g, color.b, color.a)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
			if (renderTarget == null)
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				Graphics.Context.ClearTexture(renderTarget.ColorTarget.native, new Color(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w));
			}
		}
	}

	/// <summary>
	/// Fills the given GPU buffer with a repeated uint32 value.
	/// </summary>
	/// <param name="buffer">The buffer to clear.</param>
	/// <param name="value">The uint32 value to fill with. Defaults to zero.</param>
	[Description("Fills the given GPU buffer with a repeated uint32 value.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1233)]
	public unsafe void Clear([Description("The buffer to clear.")] GpuBuffer buffer, [Description("The uint32 value to fill with. Defaults to zero.")] uint value = 0u)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer,
			Data1 = new Vector4(value, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((GpuBuffer)entry.Object1).Clear((uint)entry.Data1.x);
		}
	}

	/// <summary>
	/// Resets the hidden append/structured-buffer counter of <paramref name="buffer" /> to <paramref name="value" />.
	/// </summary>
	/// <param name="buffer">An <see cref="F:Sandbox.GpuBuffer.UsageFlags.Append" /> or structured buffer.</param>
	/// <param name="value">The counter value to set. Defaults to zero.</param>
	[Description("Resets the hidden append/structured-buffer counter of <span style=\"color: #9CDCFE;\">buffer</span> to <span style=\"color: #9CDCFE;\">value</span>.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1248)]
	public unsafe void SetCounterValue([Description("An Sandbox.GpuBuffer.UsageFlags.Append or structured buffer.")] GpuBuffer buffer, [Description("The counter value to set. Defaults to zero.")] uint value = 0u)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer,
			Data1 = new Vector4(value, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((GpuBuffer)entry.Object1).SetCounterValue((uint)entry.Data1.x);
		}
	}

	/// <summary>
	/// Copies the hidden append-buffer counter of <paramref name="buffer" /> into <paramref name="destBuffer" />.
	/// Useful for feeding a survivor count into an indirect draw/dispatch argument buffer.
	/// </summary>
	/// <param name="buffer">The <see cref="F:Sandbox.GpuBuffer.UsageFlags.Append" /> buffer to read the counter from.</param>
	/// <param name="destBuffer">The buffer to write the counter into.</param>
	/// <param name="destBufferOffset">Byte offset into <paramref name="destBuffer" /> to write at.</param>
	[Description("Copies the hidden append-buffer counter of <span style=\"color: #9CDCFE;\">buffer</span> into <span style=\"color: #9CDCFE;\">destBuffer</span>. Useful for feeding a survivor count into an indirect draw/dispatch argument buffer.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1265)]
	public unsafe void CopyStructureCount([Description("The Sandbox.GpuBuffer.UsageFlags.Append buffer to read the counter from.")] GpuBuffer buffer, [Description("The buffer to write the counter into.")] GpuBuffer destBuffer, [Description("Byte offset into <span style=\"color: #9CDCFE;\">destBuffer</span> to write at.")] int destBufferOffset = 0)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer,
			Object2 = destBuffer,
			Data1 = new Vector4(destBufferOffset, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((GpuBuffer)entry.Object1).CopyStructureCount((GpuBuffer)entry.Object2, (int)entry.Data1.x);
		}
	}

	/// <summary>
	/// Executes a barrier transition for the given GPU Texture Resource.
	/// Transitions the texture resource to a new pipeline stage and access state.
	/// </summary>
	/// <param name="texture">The texture to transition.</param>
	/// <param name="state">The new resource state for the texture.</param>
	/// <param name="mip">The mip level to transition (-1 for all mips).</param>
	[Description("Executes a barrier transition for the given GPU Texture Resource. Transitions the texture resource to a new pipeline stage and access state.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1282)]
	public unsafe void ResourceBarrierTransition([Description("The texture to transition.")] Texture texture, [Description("The new resource state for the texture.")] ResourceState state, [Description("The mip level to transition (-1 for all mips).")] int mip = -1)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = texture,
			Data1 = new Vector4((float)state, mip, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.ResourceBarrierTransition((Texture)entry.Object1, (ResourceState)entry.Data1.x, (int)entry.Data1.y);
		}
	}

	/// <summary>
	/// Executes a barrier transition for the color texture of the given render target handle.
	/// </summary>
	/// <param name="texture">The render target color handle.</param>
	/// <param name="state">The new resource state for the texture.</param>
	/// <param name="mip">The mip level to transition (-1 for all mips).</param>
	[Description("Executes a barrier transition for the color texture of the given render target handle.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1298)]
	public unsafe void ResourceBarrierTransition([Description("The render target color handle.")] RenderTargetHandle.ColorTextureRef texture, [Description("The new resource state for the texture.")] ResourceState state, [Description("The mip level to transition (-1 for all mips).")] int mip = -1)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = texture.Name,
			Data1 = new Vector4((float)state, mip, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
			if (renderTarget == null)
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				Graphics.ResourceBarrierTransition(renderTarget.ColorTarget, (ResourceState)entry.Data1.x, (int)entry.Data1.y);
			}
		}
	}

	/// <summary>
	/// Executes a barrier transition for the depth texture of the given render target handle.
	/// </summary>
	/// <param name="texture">The render target depth handle.</param>
	/// <param name="state">The new resource state for the texture.</param>
	/// <param name="mip">The mip level to transition (-1 for all mips).</param>
	[Description("Executes a barrier transition for the depth texture of the given render target handle.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1320)]
	public unsafe void ResourceBarrierTransition([Description("The render target depth handle.")] RenderTargetHandle.DepthTextureRef texture, [Description("The new resource state for the texture.")] ResourceState state, [Description("The mip level to transition (-1 for all mips).")] int mip = -1)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = texture.Name,
			Data1 = new Vector4((float)state, mip, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
			if (renderTarget == null)
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				Graphics.ResourceBarrierTransition(renderTarget.DepthTarget, (ResourceState)entry.Data1.x, (int)entry.Data1.y);
			}
		}
	}

	/// <summary>
	/// Executes a barrier transition for the color texture of the given render target handle.
	/// </summary>
	/// <param name="handle">The render target handle.</param>
	/// <param name="state">The new resource state for the texture.</param>
	/// <param name="mip">The mip level to transition (-1 for all mips).</param>
	[Description("Executes a barrier transition for the color texture of the given render target handle.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1342)]
	public void ResourceBarrierTransition([Description("The render target handle.")] RenderTargetHandle handle, [Description("The new resource state for the texture.")] ResourceState state, [Description("The mip level to transition (-1 for all mips).")] int mip = -1)
	{
		ResourceBarrierTransition(handle.ColorTexture, state, mip);
	}

	/// <summary>
	/// Executes a barrier transition for the given GPU Buffer Resource.
	/// Transitions the buffer resource to a new pipeline stage and access state.
	/// </summary>
	/// <param name="buffer">The GPU buffer to transition.</param>
	/// <param name="state">The new resource state for the buffer.</param>
	[Description("Executes a barrier transition for the given GPU Buffer Resource. Transitions the buffer resource to a new pipeline stage and access state.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1353)]
	public unsafe void ResourceBarrierTransition([Description("The GPU buffer to transition.")] GpuBuffer buffer, [Description("The new resource state for the buffer.")] ResourceState state)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer,
			Data1 = new Vector4((float)state, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.ResourceBarrierTransition((GpuBuffer)entry.Object1, (ResourceState)entry.Data1.x);
		}
	}

	/// <summary>
	/// Executes a barrier transition for the given GPU Buffer Resource.
	/// Transitions the buffer resource from a known source state to a specified destination state.
	/// </summary>
	/// <param name="buffer">The GPU buffer to transition.</param>
	/// <param name="before">The current resource state of the buffer.</param>
	/// <param name="after">The desired resource state of the buffer after the transition.</param>
	[Description("Executes a barrier transition for the given GPU Buffer Resource. Transitions the buffer resource from a known source state to a specified destination state.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1370)]
	public unsafe void ResourceBarrierTransition([Description("The GPU buffer to transition.")] GpuBuffer buffer, [Description("The current resource state of the buffer.")] ResourceState before, [Description("The desired resource state of the buffer after the transition.")] ResourceState after)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer,
			Data1 = new Vector4((float)before, (float)after, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.ResourceBarrierTransition((GpuBuffer)entry.Object1, (ResourceState)entry.Data1.x, (ResourceState)entry.Data1.y);
		}
	}

	/// <summary>
	/// Issues a UAV barrier for the given texture, ensuring writes from prior shader invocations
	/// are visible to subsequent ones without changing the resource layout.
	/// </summary>
	/// <param name="texture">The texture to barrier.</param>
	[Description("Issues a UAV barrier for the given texture, ensuring writes from prior shader invocations are visible to subsequent ones without changing the resource layout.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1385)]
	public unsafe void UavBarrier([Description("The texture to barrier.")] Texture texture)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = texture
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.UavBarrier((Texture)entry.Object1);
		}
	}

	/// <summary>
	/// Issues a UAV barrier for the color texture of the given render target handle, ensuring writes
	/// from prior shader invocations are visible to subsequent ones without changing the resource layout.
	/// Use this for a UAV (RWTexture) that is written in one pass and read back as a UAV in a later pass,
	/// where the layout doesn't change and a plain transition wouldn't emit a barrier.
	/// </summary>
	/// <param name="texture">The render target color handle.</param>
	[Description("Issues a UAV barrier for the color texture of the given render target handle, ensuring writes from prior shader invocations are visible to subsequent ones without changing the resource layout. Use this for a UAV (RWTexture) that is written in one pass and read back as a UAV in a later pass, where the layout doesn't change and a plain transition wouldn't emit a barrier.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1402)]
	public unsafe void UavBarrier([Description("The render target color handle.")] RenderTargetHandle.ColorTextureRef texture)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = texture.Name
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			RenderTarget renderTarget = commandList.state.GetRenderTarget((string)entry.Object5);
			if (renderTarget == null)
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				Graphics.UavBarrier(renderTarget.ColorTarget);
			}
		}
	}

	/// <summary>
	/// Issues a UAV barrier for the color texture of the given render target handle.
	/// </summary>
	/// <param name="handle">The render target handle.</param>
	[Description("Issues a UAV barrier for the color texture of the given render target handle.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1422)]
	public void UavBarrier([Description("The render target handle.")] RenderTargetHandle handle)
	{
		UavBarrier(handle.ColorTexture);
	}

	/// <summary>
	/// Issues a UAV barrier for the given GPU buffer, ensuring writes from prior shader invocations
	/// are visible to subsequent ones.
	/// </summary>
	/// <param name="buffer">The buffer to barrier.</param>
	[Description("Issues a UAV barrier for the given GPU buffer, ensuring writes from prior shader invocations are visible to subsequent ones.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1429)]
	public unsafe void UavBarrier([Description("The buffer to barrier.")] GpuBuffer buffer)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.UavBarrier((GpuBuffer)entry.Object1);
		}
	}

	/// <summary>
	/// Sets up per-object lighting for the given scene object. Writes lighting state
	/// into <see cref="P:Sandbox.Graphics.Attributes" /> at execution time.
	/// </summary>
	[Description("Sets up per-object lighting for the given scene object. Writes lighting state into <span style=\"color: #4EC9B0;\">Graphics</span>.<span style=\"color: #DCDCDC;\">Attributes</span> at execution time.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1443)]
	internal unsafe void SetupLighting(SceneObject obj, RenderAttributes attr = null)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = obj,
			Object2 = attr
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.SetupLighting((SceneObject)entry.Object1, (RenderAttributes)entry.Object2);
		}
	}

	/// <summary>
	/// Uploads data from an array to a GPU buffer at execution time.
	/// Zero-copy: the array reference is stored directly without copying.
	/// The caller must ensure the array contents remain stable until the command list
	/// has finished executing (i.e. until the next <see cref="M:Sandbox.Rendering.CommandList.Reset" /> call).
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1459)]
	internal unsafe void SetBufferData<T>(GpuBuffer<T> buffer, T[] data, int sourceOffset = 0, int count = -1, int elementOffset = 0) where T : unmanaged
	{
		if (count < 0)
		{
			count = data.Length - sourceOffset;
		}
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = buffer,
			Object2 = data,
			Data1 = new Vector4(elementOffset, count, sourceOffset, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			GpuBuffer<T> gpuBuffer = (GpuBuffer<T>)entry.Object1;
			T[] array = (T[])entry.Object2;
			int start = (int)entry.Data1.z;
			int length = (int)entry.Data1.y;
			gpuBuffer.SetData(array.AsSpan(start, length), (int)entry.Data1.x);
		}
	}

	/// <summary>
	/// Records an action to execute on the render thread. Cache the delegate to avoid allocations when recording.
	/// </summary>
	[Description("Records an action to execute on the render thread. Cache the delegate to avoid allocations when recording.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1478)]
	internal unsafe void AddAction(Action a)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = a
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			((Action)entry.Object1)?.Invoke();
		}
	}

	/// <summary>
	/// Sneaky way for externals to get render target
	/// </summary>
	[Description("Sneaky way for externals to get render target")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1491)]
	internal RenderTarget GetRenderTarget(string name)
	{
		if (state.renderTargets != null && state.renderTargets.TryGetValue(name, out var value))
		{
			return value;
		}
		return null;
	}

	/// <summary>
	/// Generates a mip-map chain for the specified render target.
	/// This will generate mipmaps for the color texture of the render target.
	/// </summary>
	[Description("Generates a mip-map chain for the specified render target. This will generate mipmaps for the color texture of the render target.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1503)]
	public unsafe void GenerateMipMaps(RenderTargetHandle handle, Graphics.DownsampleMethod method = Graphics.DownsampleMethod.GaussianBlur)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object5 = handle.Name,
			Data1 = new Vector4((float)method, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			if (!commandList.state.renderTargets.TryGetValue((string)entry.Object5, out var value))
			{
				GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("[{0}] Unknown rt: {1}", commandList.DebugName ?? "CommandList", (string)entry.Object5));
			}
			else
			{
				Graphics.GenerateMipMaps(value.ColorTarget, (Graphics.DownsampleMethod)entry.Data1.x);
			}
		}
	}

	/// <summary>
	/// Generates a mip-map chain for the specified render target.
	/// This will generate mipmaps for the color texture of the render target.
	/// </summary>
	[Description("Generates a mip-map chain for the specified render target. This will generate mipmaps for the color texture of the render target.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1523)]
	public unsafe void GenerateMipMaps(RenderTarget target, Graphics.DownsampleMethod method = Graphics.DownsampleMethod.GaussianBlur)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = target,
			Data1 = new Vector4((float)method, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.GenerateMipMaps(((RenderTarget)entry.Object1).ColorTarget, (Graphics.DownsampleMethod)entry.Data1.x);
		}
	}

	/// <summary>
	/// Generates a mip-map chain for the specified texture.
	/// This will generate mipmaps for the color texture of the texture.
	/// </summary>
	[Description("Generates a mip-map chain for the specified texture. This will generate mipmaps for the color texture of the texture.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1537)]
	public unsafe void GenerateMipMaps(Texture texture, Graphics.DownsampleMethod method = Graphics.DownsampleMethod.GaussianBlur)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = texture,
			Data1 = new Vector4((float)method, 0f, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Graphics.GenerateMipMaps((Texture)entry.Object1, (Graphics.DownsampleMethod)entry.Data1.x);
		}
	}

	/// <summary>
	/// Draws text within a rectangle using a prepared <see cref="T:Sandbox.TextRendering.Scope" />.
	/// </summary>
	/// <param name="scope">The text rendering scope.</param>
	/// <param name="rect">The rectangle to draw the text in.</param>
	/// <param name="flags">Text alignment flags (optional).</param>
	/// <param name="angleDegrees">Rotation angle in degrees (optional).</param>
	[Description("Draws text within a rectangle using a prepared Sandbox.TextRendering.Scope.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1554)]
	public void DrawText([Description("The text rendering scope.")] TextRendering.Scope scope, [Description("The rectangle to draw the text in.")] Rect rect, [Description("Text alignment flags (optional).")] TextFlag flags = TextFlag.LeftTop, [Description("Rotation angle in degrees (optional).")] float angleDegrees = 0f)
	{
		TextRendering.TextBlock orCreateTextBlock = TextRendering.GetOrCreateTextBlock(in scope, flags);
		if (orCreateTextBlock != null)
		{
			DrawText(orCreateTextBlock, rect, flags, angleDegrees);
		}
	}

	/// <summary>Draws an already resolved text block, for callers that measured it first.</summary>
	[Description("Draws an already resolved text block, for callers that measured it first.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.cs", 1563)]
	internal unsafe void DrawText(TextRendering.TextBlock block, Rect rect, TextFlag flags, float angleDegrees = 0f)
	{
		AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
		{
			Object1 = block,
			Data1 = new Vector4(rect.Left, rect.Top, rect.Width, rect.Height),
			Data2 = new Vector4((float)flags, angleDegrees, 0f, 0f)
		});
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Rect position = new Rect(entry.Data1.x, entry.Data1.y, entry.Data1.z, entry.Data1.w);
			Graphics.DrawText((TextRendering.TextBlock)entry.Object1, in position, (TextFlag)entry.Data2.x, entry.Data2.y);
		}
	}

	/// <summary>
	/// Times a section of this command list on the GPU. Shows up as a PIX/RenderDoc event and as a row in
	/// the GPU profiler overlay. Bound with a <c>using</c> block, which is what decides where the section ends.
	/// </summary>
	[Description("Times a section of this command list on the GPU. Shows up as a PIX/RenderDoc event and as a row in the GPU profiler overlay. Bound with a <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">using</code> block, which is what decides where the section ends.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 11)]
	public unsafe ProfilingScope ProfileScope(ProfilingSampler sampler)
	{
		if (sampler == null)
		{
			return default;
		}
		AddEntry((delegate*<ref Entry, CommandList, void>)(&ExecuteBeginScope), new Entry
		{
			Object1 = sampler
		});
		return new ProfilingScope(this);
	}

	/// <summary>
	/// Begin a scope on the render thread. Checked here rather than at record time so toggling the profiler takes effect immediately
	/// </summary>
	[Description("Begin a scope on the render thread. Checked here rather than at record time so toggling the profiler takes effect immediately")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 73)]
	internal static OpenScope OpenScopeFor(ProfilingSampler sampler)
	{
		IRenderContext context = Graphics.Context;
		bool debugMarkersEnabled = DebugMarkersEnabled;
		if (debugMarkersEnabled)
		{
			context.BeginPixEvent(sampler.NamePtr);
		}
		nint marker = ((GpuProfilerStats.Enabled && !Graphics.OnComputeQueue) ? CSceneSystem.BeginManagedPerfMarker(context, sampler.NamePtr) : IntPtr.Zero);
		GC.KeepAlive(sampler);
		return new OpenScope
		{
			Marker = marker,
			Pix = debugMarkersEnabled
		};
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 91)]
	private static void ExecuteBeginScope(ref Entry entry, CommandList commandList)
	{
		ProfilingSampler sampler = (ProfilingSampler)entry.Object1;
		commandList.state.openScopes.Push(OpenScopeFor(sampler));
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 98)]
	private static void ExecuteEndScope(ref Entry entry, CommandList commandList)
	{
		if (commandList.state.openScopes.TryPop(out var result))
		{
			CloseScope(Graphics.Context, result);
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 106)]
	private static void CloseScope(IRenderContext context, OpenScope open)
	{
		if (open.Marker != IntPtr.Zero)
		{
			CSceneSystem.EndManagedPerfMarker(context, open.Marker);
		}
		if (open.Pix)
		{
			context.EndPixEvent();
		}
	}

	/// <summary>
	/// Close anything left open by a missing Dispose, so a recording mistake can't leak a timestamp query for the rest of the frame
	/// </summary>
	[Description("Close anything left open by a missing Dispose, so a recording mistake can't leak a timestamp query for the rest of the frame")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Profiling.cs", 119)]
	private void CloseLeakedScopes()
	{
		IRenderContext context = Graphics.Context;
		OpenScope result;
		while (state.openScopes.TryPop(out result))
		{
			CloseScope(context, result);
		}
	}

	/// <summary>
	/// Render a <see cref="T:Sandbox.Renderer" /> with the specified overrides.
	/// </summary>
	[Description("Render a <span style=\"color: #4EC9B0;\">Renderer</span> with the specified overrides.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Render.cs", 9)]
	public unsafe void DrawRenderer(Renderer renderer, RendererSetup rendererSetup = default(RendererSetup))
	{
		if (renderer.IsValid())
		{
			AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object1 = renderer,
				Object2 = rendererSetup
			});
		}
		static void Execute(ref Entry entry, CommandList commandList)
		{
			Renderer renderer2 = (Renderer)entry.Object1;
			if (renderer2.IsValid())
			{
				renderer2.RenderSceneObject((RendererSetup)entry.Object2);
			}
		}
	}

	/// <summary>
	/// Renders the view from a camera to the specified render target.
	/// </summary>
	[Description("Renders the view from a camera to the specified render target.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Render.cs", 29)]
	public unsafe void DrawView(CameraComponent camera, RenderTargetHandle target, ViewSetup viewSetup = default(ViewSetup))
	{
		if (camera.IsValid())
		{
			AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object1 = camera,
				Object5 = target.Name,
				Object2 = viewSetup
			});
		}
		static void Execute(ref Entry entry, CommandList commandList)
		{
			CameraComponent cameraComponent = (CameraComponent)entry.Object1;
			if (cameraComponent.IsValid())
			{
				RenderTarget renderTarget = commandList.GetRenderTarget((string)entry.Object5);
				if (renderTarget != null && !Graphics.IsChildView)
				{
					cameraComponent.RenderToTexture(renderTarget.ColorTarget, (ViewSetup)entry.Object2);
				}
			}
		}
	}

	/// <summary>
	/// Render a planar reflection using the specified camera and the specified plane.
	/// </summary>
	[Description("Render a planar reflection using the specified camera and the specified plane.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Render.cs", 54)]
	public unsafe void DrawReflection(CameraComponent camera, Plane plane, in RenderTargetHandle target, ReflectionSetup reflectionSetup = default(ReflectionSetup))
	{
		if (camera.IsValid())
		{
			AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object1 = camera,
				Object2 = reflectionSetup,
				Object5 = target.Name,
				Data1 = new Vector4(plane.Normal.x, plane.Normal.y, plane.Normal.z, 0f),
				Data2 = new Vector4(plane.Distance, 0f, 0f, 0f)
			});
		}
		static void Execute(ref Entry entry, CommandList commandList)
		{
			CameraComponent cameraComponent = (CameraComponent)entry.Object1;
			if (cameraComponent.IsValid())
			{
				ReflectionSetup reflectionSetup2 = (ReflectionSetup)entry.Object2;
				Plane plane2 = new Plane(new Vector3(entry.Data1.x, entry.Data1.y, entry.Data1.z), entry.Data2.x);
				RenderTarget renderTarget = commandList.GetRenderTarget((string)entry.Object5);
				if (renderTarget != null && (plane2.IsInFront(Graphics.CameraTransform.Position) || reflectionSetup2.RenderBehind))
				{
					if (Graphics.IsChildView)
					{
						Color? fallbackColor = reflectionSetup2.FallbackColor;
						if (fallbackColor.HasValue)
						{
							Color valueOrDefault = fallbackColor.GetValueOrDefault();
							Graphics.RenderTarget = renderTarget;
							Graphics.Clear(valueOrDefault);
							Graphics.RenderTarget = null;
						}
					}
					else
					{
						Transform cameraTransform = Graphics.CameraTransform.Mirror(in plane2);
						Matrix projectionMatrix = Matrix.CreateProjection(cameraComponent.ZNear, cameraComponent.ZFar, Graphics.FieldOfView, Graphics.Viewport.Width / Graphics.Viewport.Height, reflectionSetup2.ViewSetup.ClipSpaceBounds ?? new Vector4(-1f, -1f, 1f, 1f));
						plane2.GetDistance(in cameraTransform.Position);
						float clipOffset = reflectionSetup2.ClipOffset;
						Matrix matrix = Matrix.CreateObliqueProjection(in cameraTransform, new Plane(plane2.Position - clipOffset * plane2.Normal, in plane2.Normal), in projectionMatrix);
						ref Transform? transform = ref reflectionSetup2.ViewSetup.Transform;
						Transform valueOrDefault2 = transform.GetValueOrDefault();
						if (!transform.HasValue)
						{
							valueOrDefault2 = cameraTransform;
							transform = valueOrDefault2;
						}
						ref float? fieldOfView = ref reflectionSetup2.ViewSetup.FieldOfView;
						float valueOrDefault3 = fieldOfView.GetValueOrDefault();
						if (!fieldOfView.HasValue)
						{
							valueOrDefault3 = Graphics.FieldOfView;
							fieldOfView = valueOrDefault3;
						}
						ref Matrix? projectionMatrix2 = ref reflectionSetup2.ViewSetup.ProjectionMatrix;
						Matrix valueOrDefault4 = projectionMatrix2.GetValueOrDefault();
						if (!projectionMatrix2.HasValue)
						{
							valueOrDefault4 = matrix;
							projectionMatrix2 = valueOrDefault4;
						}
						ref bool? flipX = ref reflectionSetup2.ViewSetup.FlipX;
						bool valueOrDefault5 = flipX == true;
						if (!flipX.HasValue)
						{
							valueOrDefault5 = true;
							flipX = valueOrDefault5;
						}
						cameraComponent.RenderToTexture(renderTarget.ColorTarget, in reflectionSetup2.ViewSetup);
					}
				}
			}
		}
	}

	/// <summary>
	/// Render a planar refraction using the specified camera and the specified plane. This is for all intents and purposes a
	/// regular view with a plane clipping it. Usually used for rendering under water.
	/// </summary>
	[Description("Render a planar refraction using the specified camera and the specified plane. This is for all intents and purposes a regular view with a plane clipping it. Usually used for rendering under water.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Render.cs", 110)]
	public unsafe void DrawRefraction(CameraComponent camera, Plane plane, in RenderTargetHandle target, RefractionSetup refractionSetup = default(RefractionSetup))
	{
		if (camera.IsValid())
		{
			AddEntry((delegate*<ref Entry, CommandList, void>)(&Execute), new Entry
			{
				Object1 = camera,
				Object2 = refractionSetup,
				Object5 = target.Name,
				Data1 = new Vector4(plane.Normal.x, plane.Normal.y, plane.Normal.z, 0f),
				Data2 = new Vector4(plane.Distance, 0f, 0f, 0f)
			});
		}
		static void Execute(ref Entry entry, CommandList commandList)
		{
			CameraComponent cameraComponent = (CameraComponent)entry.Object1;
			if (cameraComponent.IsValid())
			{
				RefractionSetup refractionSetup2 = (RefractionSetup)entry.Object2;
				Plane plane2 = new Plane(new Vector3(entry.Data1.x, entry.Data1.y, entry.Data1.z), entry.Data2.x);
				RenderTarget renderTarget = commandList.GetRenderTarget((string)entry.Object5);
				if (renderTarget != null && (plane2.IsInFront(Graphics.CameraTransform.Position) || refractionSetup2.RenderBehind))
				{
					if (Graphics.IsChildView)
					{
						Color? fallbackColor = refractionSetup2.FallbackColor;
						if (fallbackColor.HasValue)
						{
							Color valueOrDefault = fallbackColor.GetValueOrDefault();
							Graphics.RenderTarget = renderTarget;
							Graphics.Clear(valueOrDefault);
							Graphics.RenderTarget = null;
						}
					}
					else
					{
						Transform cameraTransform = Graphics.CameraTransform;
						Matrix projectionMatrix = Matrix.CreateProjection(cameraComponent.ZNear, cameraComponent.ZFar, Graphics.FieldOfView, Graphics.Viewport.Width / Graphics.Viewport.Height, refractionSetup2.ViewSetup.ClipSpaceBounds ?? new Vector4(-1f, -1f, 1f, 1f));
						plane2.GetDistance(in cameraTransform.Position);
						float clipOffset = refractionSetup2.ClipOffset;
						Matrix matrix = Matrix.CreateObliqueProjection(in cameraTransform, new Plane(plane2.Position + clipOffset * plane2.Normal, in plane2.Normal), in projectionMatrix);
						ref Transform? transform = ref refractionSetup2.ViewSetup.Transform;
						Transform valueOrDefault2 = transform.GetValueOrDefault();
						if (!transform.HasValue)
						{
							valueOrDefault2 = cameraTransform;
							transform = valueOrDefault2;
						}
						ref float? fieldOfView = ref refractionSetup2.ViewSetup.FieldOfView;
						float valueOrDefault3 = fieldOfView.GetValueOrDefault();
						if (!fieldOfView.HasValue)
						{
							valueOrDefault3 = Graphics.FieldOfView;
							fieldOfView = valueOrDefault3;
						}
						ref Matrix? projectionMatrix2 = ref refractionSetup2.ViewSetup.ProjectionMatrix;
						Matrix valueOrDefault4 = projectionMatrix2.GetValueOrDefault();
						if (!projectionMatrix2.HasValue)
						{
							valueOrDefault4 = matrix;
							projectionMatrix2 = valueOrDefault4;
						}
						cameraComponent.RenderToTexture(renderTarget.ColorTarget, in refractionSetup2.ViewSetup);
					}
				}
			}
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 21)]
	internal int GetCheckpoint()
	{
		using (_lock.EnterScope())
		{
			return _entries.Count;
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 27)]
	internal void Rewind(int checkpoint)
	{
		using (_lock.EnterScope())
		{
			_entries.RemoveRange(checkpoint, _entries.Count - checkpoint);
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 33)]
	internal T FindResource<T>() where T : class, IResource
	{
		using (_lock.EnterScope())
		{
			if (_resources != null)
			{
				foreach (IResource resource in _resources)
				{
					if (resource is T result)
					{
						return result;
					}
				}
			}
			return null;
		}
	}

	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 50)]
	internal void RegisterResource(IResource resource)
	{
		using (_lock.EnterScope())
		{
			if (_resources == null)
			{
				_resources = new List<IResource>();
			}
			_resources.Add(resource);
		}
	}

	/// <summary>
	/// Executes commands on the current graphics context without requiring a scene view.
	/// </summary>
	[Description("Executes commands on the current graphics context without requiring a scene view.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 62)]
	internal void Execute()
	{
		using (_lock.EnterScope())
		{
			ExecuteEntries();
		}
	}

	/// <summary>
	/// Runs every recorded entry against a fresh state. The caller holds the lock.
	/// </summary>
	[Description("Runs every recorded entry against a fresh state. The caller holds the lock.")]
	[SourceLocation("Systems\\Render\\CommandList\\CommandList.Resources.cs", 71)]
	private unsafe void ExecuteEntries()
	{
		State state = this.state;
		this.state = ObjectPool<State>.Get();
		try
		{
			if (_resources != null)
			{
				foreach (IResource resource in _resources)
				{
					resource.BeginExecute();
				}
			}
			Span<Entry> span = CollectionsMarshal.AsSpan(_entries);
			for (int i = 0; i < span.Length; i++)
			{
				span[i].Execute(ref span[i], this);
			}
		}
		finally
		{
			CloseLeakedScopes();
			this.state.Reset();
			ObjectPool<State>.Return(this.state);
			this.state = state;
		}
	}
}
