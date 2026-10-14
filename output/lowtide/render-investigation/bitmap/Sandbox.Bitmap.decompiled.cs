using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using Sandbox.Internal;
using Sandbox.UI;
using Sandbox.Utility;
using SkiaSharp;
using Svg;
using Svg.Skia;

namespace Sandbox;

[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 6)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 6)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 6)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.cs", 5)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 7)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Psd.cs", 5)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Svg.cs", 6)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tga.cs", 5)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 5)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 5)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 6)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Text.cs", 5)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Texture.cs", 3)]
[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Transforms.cs", 5)]
public sealed class Bitmap : IDisposable, IValid
{
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 75)]
	private class IES
	{
		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 77)]
		public int NumLamps;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 78)]
		public float LumensPerLamp;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 79)]
		public float CandelaMultiplier;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 81)]
		public int NumHorizontal;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 82)]
		public int NumVertical;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 84)]
		public int PhotometricType;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 85)]
		public int UnitsType;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 87)]
		public float Width;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 88)]
		public float Length;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 89)]
		public float Height;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 91)]
		public float BallastFactor;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 92)]
		public float Unused;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 93)]
		public float InputWatts;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 95)]
		public List<float> VerticalAngles;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 96)]
		public List<float> HorizontalAngles;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 97)]
		public List<float> Candelas;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 99)]
		public float CandelasMax;

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 101)]
		public void ParseIESInfo(Stream stream)
		{
			using StreamReader streamReader = new StreamReader(stream);
			streamReader.ReadLine();
			while (!streamReader.EndOfStream)
			{
				string text = streamReader.ReadLine();
				if (text.StartsWith("TILT="))
				{
					if (!(text.Substring(5) != "NONE"))
					{
						break;
					}
					throw new Exception("Tilted IES files are not supported");
				}
			}
			if (streamReader.EndOfStream)
			{
				throw new Exception("IES file is missing TILT information");
			}
			string[] array = streamReader.ReadToEnd().Split(new string[3] { " ", "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
			NumLamps = int.Parse(array[0]);
			LumensPerLamp = float.Parse(array[1]);
			CandelaMultiplier = float.Parse(array[2]);
			NumVertical = int.Parse(array[3]);
			NumHorizontal = int.Parse(array[4]);
			PhotometricType = int.Parse(array[5]);
			UnitsType = int.Parse(array[6]);
			Width = float.Parse(array[7]);
			Length = float.Parse(array[8]);
			Height = float.Parse(array[9]);
			BallastFactor = float.Parse(array[10]);
			Unused = float.Parse(array[11]);
			InputWatts = float.Parse(array[12]);
			VerticalAngles = new List<float>();
			HorizontalAngles = new List<float>();
			Candelas = new List<float>();
			int num = 13;
			int num2 = 0;
			while (num2 < NumVertical)
			{
				VerticalAngles.Add(float.Parse(array[num]));
				num2++;
				num++;
			}
			int num3 = 0;
			while (num3 < NumHorizontal)
			{
				HorizontalAngles.Add(float.Parse(array[num]));
				num3++;
				num++;
			}
			for (int i = 0; i < NumHorizontal; i++)
			{
				int num4 = 0;
				while (num4 < NumVertical)
				{
					Candelas.Add(float.Parse(array[num]));
					num4++;
					num++;
				}
			}
			CandelasMax = Candelas.Max();
		}

		[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 170)]
		public float Sample2D(float radius, float angleDeg)
		{
			if (radius > 1f)
			{
				return 0f;
			}
			angleDeg = (angleDeg % 360f + 360f) % 360f;
			if (angleDeg > 180f)
			{
				angleDeg = 360f - angleDeg;
			}
			int num = 0;
			int num2 = 0;
			float num3 = 0f;
			for (int i = 0; i < NumHorizontal - 1; i++)
			{
				if (angleDeg >= HorizontalAngles[i] && angleDeg <= HorizontalAngles[i + 1])
				{
					num = i;
					num2 = i + 1;
					num3 = (angleDeg - HorizontalAngles[i]) / (HorizontalAngles[i + 1] - HorizontalAngles[i]);
					break;
				}
			}
			float num4 = 90f * radius;
			int num5 = 0;
			int num6 = 0;
			float num7 = 0f;
			for (int j = 0; j < NumVertical - 1; j++)
			{
				if (num4 >= VerticalAngles[j] && num4 <= VerticalAngles[j + 1])
				{
					num5 = j;
					num6 = j + 1;
					num7 = (num4 - VerticalAngles[j]) / (VerticalAngles[j + 1] - VerticalAngles[j]);
					break;
				}
			}
			float num8 = Candelas[num * NumVertical + num5];
			float num9 = Candelas[num * NumVertical + num6];
			float num10 = Candelas[num2 * NumVertical + num5];
			float num11 = Candelas[num2 * NumVertical + num6];
			float num12 = num8 * (1f - num7) + num9 * num7;
			float num13 = num10 * (1f - num7) + num11 * num7;
			return (num12 * (1f - num3) + num13 * num3) * CandelaMultiplier;
		}
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 8)]
	private SKBitmap _bitmap;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 9)]
	private SKCanvas _canvas;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 31)]
	private const int MaxDimension = 16384;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 34)]
	private const ushort TiffBigEndian = 19789;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 35)]
	private const ushort TiffLittleEndian = 18761;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 36)]
	private const ushort TiffVersion = 42;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 7)]
	private SKPaint _pen;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 86)]
	private static readonly float[] gradientPoints = (from x in Enumerable.Range(0, 64)
		select (float)x / 64f).ToArray();

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 11)]
	public int Width => _bitmap.Width;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 12)]
	public int Height => _bitmap.Height;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 13)]
	public int BytesPerPixel => _bitmap.BytesPerPixel;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 14)]
	public int ByteCount => _bitmap.ByteCount;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 15)]
	public Rect Rect => new Rect(0f, 0f, (float)Width, (float)Height);

	/// <summary>
	/// The width and height of the bitmap
	/// </summary>
	[Description("The width and height of the bitmap")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 21)]
	public Vector2Int Size => new Vector2Int(Width, Height);

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 24)]
	public Vector2 Center => new Vector2(Width, Height) * 0.5f;

	/// <summary>Whether the backing pixels use half-float RGBA storage.</summary>
	[Description("Whether the backing pixels use half-float RGBA storage.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 27)]
	public bool IsFloatingPoint => GetColorType() == SKColorType.RgbaF16;

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 29)]
	public bool IsValid
	{
		get
		{
			if (_bitmap != null)
			{
				return _canvas != null;
			}
			return false;
		}
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Texture.cs", 5)]
	private ImageFormat ImageFormat
	{
		get
		{
			if (!IsFloatingPoint)
			{
				return ImageFormat.RGBA8888;
			}
			return ImageFormat.RGBA16161616F;
		}
	}

	public Bitmap(int width, int height, bool floatingPoint = false)
	{
		if (width <= 0 || height <= 0)
		{
			throw new ArgumentOutOfRangeException("Dimensions must be positive.");
		}
		if (width > 16384 || height > 16384)
		{
			throw new ArgumentOutOfRangeException($"Dimensions cannot exceed {16384}.");
		}
		checked
		{
			_ = width * height * (floatingPoint ? 8 : 4);
			_bitmap = new SKBitmap(new SKImageInfo(width, height, floatingPoint ? SKColorType.RgbaF16 : SKColorType.Rgba8888, SKAlphaType.Unpremul));
			InitializeCanvas();
		}
	}

	/// <summary>
	/// Used internally for resizing operations
	/// </summary>
	internal Bitmap(SKBitmap bitmap)
	{
		ArgumentNullException.ThrowIfNull(bitmap, "bitmap");
		_bitmap = bitmap;
		InitializeCanvas();
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 59)]
	private void InitializeCanvas()
	{
		try
		{
			GetBuffer();
			_canvas = new SKCanvas(_bitmap);
		}
		catch
		{
			Dispose();
			throw;
		}
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 73)]
	public void Dispose()
	{
		_canvas?.Dispose();
		_canvas = null;
		_bitmap?.Dispose();
		_bitmap = null;
	}

	/// <summary>
	/// Clears the bitmap to the specified color.
	/// </summary>
	/// <param name="color">The color to fill the bitmap with.</param>
	[Description("Clears the bitmap to the specified color.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 86)]
	public void Clear([Description("The color to fill the bitmap with.")] Color color)
	{
		_canvas.Clear(color.ToSkF());
	}

	/// <summary>Imports pixels in this bitmap's format, converting premultiplied input during the copy.</summary>
	[Description("Imports pixels in this bitmap's format, converting premultiplied input during the copy.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 92)]
	internal unsafe void SetPixelData(ReadOnlySpan<byte> pixels, bool premultiplied)
	{
		Span<byte> buffer = GetBuffer();
		if (pixels.Length != buffer.Length)
		{
			throw new ArgumentException("Pixel data must match the bitmap allocation.", "pixels");
		}
		if (!premultiplied)
		{
			pixels.CopyTo(buffer);
			return;
		}
		fixed (byte* addr = pixels)
		{
			using SKPixmap sKPixmap = new SKPixmap(_bitmap.Info.WithAlphaType(SKAlphaType.Premul), (nint)addr, _bitmap.RowBytes);
			if (!sKPixmap.ReadPixels(_bitmap.Info, _bitmap.GetPixels(), _bitmap.RowBytes))
			{
				throw new InvalidOperationException("Could not import premultiplied bitmap pixels.");
			}
		}
	}

	/// <summary>
	/// Retrieves the pixel data of the bitmap as an array of colors.
	/// </summary>
	[Description("Retrieves the pixel data of the bitmap as an array of colors.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 114)]
	public Color[] GetPixels()
	{
		Span<byte> buffer = GetBuffer();
		if (!IsFloatingPoint)
		{
			return _bitmap.Pixels.Select((SKColor p) => p.FromSk()).ToArray();
		}
		Span<Color.Rgba16> span = MemoryMarshal.Cast<byte, Color.Rgba16>(buffer);
		Color[] array = new Color[span.Length];
		for (int num = 0; num < span.Length; num++)
		{
			array[num] = span[num].ToColor();
		}
		return array;
	}

	/// <summary>Retrieves the pixel data as half-float colors.</summary>
	[Description("Retrieves the pixel data as half-float colors.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 126)]
	public Color.Rgba16[] GetPixels16()
	{
		Span<byte> buffer = GetBuffer();
		if (IsFloatingPoint)
		{
			return MemoryMarshal.Cast<byte, Color.Rgba16>(buffer).ToArray();
		}
		return ((IEnumerable<SKColor>)_bitmap.Pixels).Select((Func<SKColor, Color.Rgba16>)((SKColor p) => p.FromSk())).ToArray();
	}

	/// <summary>Retrieves the pixel data as 32-bit colors.</summary>
	[Description("Retrieves the pixel data as 32-bit colors.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 134)]
	public Color32[] GetPixels32()
	{
		Span<byte> buffer = GetBuffer();
		if (!IsFloatingPoint)
		{
			return ((IEnumerable<SKColor>)_bitmap.Pixels).Select((Func<SKColor, Color32>)((SKColor p) => p.FromSk())).ToArray();
		}
		Span<Color.Rgba16> span = MemoryMarshal.Cast<byte, Color.Rgba16>(buffer);
		Color32[] array = new Color32[span.Length];
		for (int num = 0; num < span.Length; num++)
		{
			array[num] = span[num].ToColor();
		}
		return array;
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 145)]
	public void SetPixels(Color[] colors)
	{
		Span<byte> buffer = GetBuffer();
		if (colors == null || colors.Length != checked(Width * Height))
		{
			throw new ArgumentException("Colors array must match the size of the bitmap.");
		}
		if (IsFloatingPoint)
		{
			Span<Color.Rgba16> span = MemoryMarshal.Cast<byte, Color.Rgba16>(buffer);
			for (int i = 0; i < span.Length; i++)
			{
				span[i] = new Color.Rgba16(colors[i]);
			}
			return;
		}
		SKColor[] array = new SKColor[colors.Length];
		for (int j = 0; j < colors.Length; j++)
		{
			array[j] = colors[j].ToSk();
		}
		_bitmap.Pixels = array;
	}

	/// <summary>
	/// Retrieves the color of a specific pixel in the bitmap.
	/// </summary>
	/// <param name="x">The x-coordinate of the pixel.</param>
	/// <param name="y">The y-coordinate of the pixel.</param>
	/// <returns>The color of the pixel at the specified coordinates.</returns>
	[Description("Retrieves the color of a specific pixel in the bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 170)]
	[return: Description("The color of the pixel at the specified coordinates.")]
	public Color GetPixel([Description("The x-coordinate of the pixel.")] int x, [Description("The y-coordinate of the pixel.")] int y)
	{
		AssertBounds(x, y, 1, 1);
		Span<byte> buffer = GetBuffer();
		if (IsFloatingPoint)
		{
			return MemoryMarshal.Cast<byte, Color.Rgba16>(buffer)[checked(y * Width + x)].ToColor();
		}
		return _bitmap.GetPixel(x, y).FromSk();
	}

	/// <summary>
	/// Sets the color of a specific pixel in the bitmap.
	/// </summary>
	/// <param name="x">The x-coordinate of the pixel.</param>
	/// <param name="y">The y-coordinate of the pixel.</param>
	/// <param name="color">The color to set the pixel to.</param>
	[Description("Sets the color of a specific pixel in the bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 185)]
	public void SetPixel([Description("The x-coordinate of the pixel.")] int x, [Description("The y-coordinate of the pixel.")] int y, [Description("The color to set the pixel to.")] Color color)
	{
		AssertBounds(x, y, 1, 1);
		Span<byte> buffer = GetBuffer();
		if (IsFloatingPoint)
		{
			MemoryMarshal.Cast<byte, Color.Rgba16>(buffer)[checked(y * Width + x)] = new Color.Rgba16(color);
		}
		else
		{
			_bitmap.SetPixel(x, y, color.ToSk());
		}
	}

	/// <summary>
	/// Low level, get a span of the bitmap data.
	/// </summary>
	[Description("Low level, get a span of the bitmap data.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 203)]
	internal Span<byte> GetBuffer()
	{
		int num = ((GetColorType() == SKColorType.RgbaF16) ? 8 : 4);
		checked
		{
			int num2 = Width * num;
			int num3 = num2 * Height;
			if (Width <= 0 || Height <= 0 || _bitmap.BytesPerPixel != num || _bitmap.RowBytes != num2 || num3 > _bitmap.ByteCount || _bitmap.GetPixels() == IntPtr.Zero)
			{
				throw new InvalidOperationException("Bitmap storage does not match its pixel format and dimensions.");
			}
			Span<byte> pixelSpan = _bitmap.GetPixelSpan();
			if (pixelSpan.Length < num3)
			{
				throw new InvalidOperationException("Bitmap pixel allocation is smaller than its dimensions.");
			}
			return pixelSpan.Slice(0, num3);
		}
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 219)]
	private SKColorType GetColorType()
	{
		ObjectDisposedException.ThrowIf(_bitmap == null, this);
		return _bitmap.ColorType switch
		{
			SKColorType.Rgba8888 => SKColorType.Rgba8888, 
			SKColorType.RgbaF16 => SKColorType.RgbaF16, 
			_ => throw new InvalidOperationException($"Unsupported bitmap pixel format: {_bitmap.ColorType}."), 
		};
	}

	/// <summary>Gets the pointer after validating the backing pixel allocation.</summary>
	[Description("Gets the pointer after validating the backing pixel allocation.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 231)]
	internal unsafe void* GetPointer()
	{
		GetBuffer();
		return (void*)_bitmap.GetPixels();
	}

	/// <summary>
	/// Asserts that the specified region is within the bounds of the bitmap.
	/// Throws an exception if the bounds are out of range.
	/// </summary>
	/// <param name="x">The x-coordinate of the starting point.</param>
	/// <param name="y">The y-coordinate of the starting point.</param>
	/// <param name="width">The width of the region to check.</param>
	/// <param name="height">The height of the region to check.</param>
	[Description("Asserts that the specified region is within the bounds of the bitmap. Throws an exception if the bounds are out of range.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 245)]
	private void AssertBounds([Description("The x-coordinate of the starting point.")] int x, [Description("The y-coordinate of the starting point.")] int y, [Description("The width of the region to check.")] int width, [Description("The height of the region to check.")] int height)
	{
		ObjectDisposedException.ThrowIf(!IsValid, this);
		if (x < 0 || y < 0 || width < 0 || height < 0 || width > Width || height > Height || x > Width - width || y > Height - height)
		{
			throw new ArgumentOutOfRangeException("x", "Specified region is out of bounds.");
		}
	}

	/// <summary>
	/// Copy the bitmap to a new one without any changes.
	/// </summary>
	[Description("Copy the bitmap to a new one without any changes.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 258)]
	public Bitmap Clone()
	{
		return new Bitmap(_bitmap.Copy());
	}

	/// <summary>
	/// Returns true if this bitmap is completely opaque (no alpha)
	/// This does a pixel by pixel search, so it's not the fastest.
	/// </summary>
	[Description("Returns true if this bitmap is completely opaque (no alpha) This does a pixel by pixel search, so it's not the fastest.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.cs", 269)]
	public bool IsOpaque()
	{
		Span<byte> buffer = GetBuffer();
		if (_bitmap.AlphaType == SKAlphaType.Opaque)
		{
			return true;
		}
		if (IsFloatingPoint)
		{
			Span<Color.Rgba16> span = MemoryMarshal.Cast<byte, Color.Rgba16>(buffer);
			for (int i = 0; i < span.Length; i++)
			{
				if ((float)span[i].a < 1f)
				{
					return false;
				}
			}
		}
		else
		{
			for (int j = 3; j < buffer.Length; j += 4)
			{
				if (buffer[j] != byte.MaxValue)
				{
					return false;
				}
			}
		}
		return true;
	}

	/// <summary>
	/// Draws a rectangle using the current pen settings.
	/// </summary>
	/// <param name="rect">The rectangle to draw.</param>
	[Description("Draws a rectangle using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 12)]
	public void DrawRect([Description("The rectangle to draw.")] Rect rect)
	{
		SKRect rect2 = rect.ToSk();
		_canvas.DrawRect(rect2, GetPen());
	}

	/// <summary>
	/// Draws a rectangle using the current pen settings.
	/// </summary>
	/// <param name="x">The x-coordinate of the top-left corner.</param>
	/// <param name="y">The y-coordinate of the top-left corner.</param>
	/// <param name="width">The width of the rectangle.</param>
	/// <param name="height">The height of the rectangle.</param>
	[Description("Draws a rectangle using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 25)]
	public void DrawRect([Description("The x-coordinate of the top-left corner.")] float x, [Description("The y-coordinate of the top-left corner.")] float y, [Description("The width of the rectangle.")] float width, [Description("The height of the rectangle.")] float height)
	{
		DrawRect(new Rect(in x, in y, x + width, y + height));
	}

	/// <summary>
	/// Draws a rectangle using the current pen settings.
	/// </summary>
	[Description("Draws a rectangle using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 33)]
	public void DrawRoundRect(Rect rect, Margin margins)
	{
		using SKRoundRect sKRoundRect = new SKRoundRect(rect.ToSk());
		sKRoundRect.SetRectRadii(rect.ToSk(), new SKPoint[4]
		{
			new SKPoint(margins.Left, margins.Left),
			new SKPoint(margins.Top, margins.Top),
			new SKPoint(margins.Right, margins.Right),
			new SKPoint(margins.Bottom, margins.Bottom)
		});
		rect.ToSk();
		_canvas.DrawRoundRect(sKRoundRect, GetPen());
	}

	/// <summary>
	/// Draws a circle using the current pen settings.
	/// </summary>
	/// <param name="center">The center of the circle.</param>
	/// <param name="radius">The radius of the circle.</param>
	[Description("Draws a circle using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 47)]
	public void DrawCircle([Description("The center of the circle.")] Vector2 center, [Description("The radius of the circle.")] float radius)
	{
		_canvas.DrawCircle(center.ToSk(), radius, GetPen());
	}

	/// <summary>
	/// Draws a circle using the current pen settings.
	/// </summary>
	/// <param name="x">The x-coordinate of the circle's center.</param>
	/// <param name="y">The y-coordinate of the circle's center.</param>
	/// <param name="radius">The radius of the circle.</param>
	[Description("Draws a circle using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 58)]
	public void DrawCircle([Description("The x-coordinate of the circle's center.")] float x, [Description("The y-coordinate of the circle's center.")] float y, [Description("The radius of the circle.")] float radius)
	{
		DrawCircle(new Vector2(x, y), radius);
	}

	/// <summary>
	/// Draws a polygon using the current pen settings.
	/// </summary>
	/// <param name="points">The points of the polygon.</param>
	[Description("Draws a polygon using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 67)]
	public void DrawPolygon([Description("The points of the polygon.")] Vector2[] points)
	{
		using SKPath sKPath = new SKPath();
		sKPath.MoveTo(points[0].ToSk());
		for (int i = 1; i < points.Length; i++)
		{
			sKPath.LineTo(points[i].ToSk());
		}
		sKPath.Close();
		_canvas.DrawPath(sKPath, GetPen());
	}

	/// <summary>
	/// Draws an arc using the current pen settings.
	/// </summary>
	/// <param name="rect">The bounding rectangle of the arc.</param>
	/// <param name="startAngle">The starting angle of the arc, in degrees.</param>
	/// <param name="sweepAngle">The sweep angle of the arc, in degrees.</param>
	[Description("Draws an arc using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 87)]
	public void DrawArc([Description("The bounding rectangle of the arc.")] Rect rect, [Description("The starting angle of the arc, in degrees.")] float startAngle, [Description("The sweep angle of the arc, in degrees.")] float sweepAngle)
	{
		_canvas.DrawArc(rect.ToSk(), startAngle, sweepAngle, useCenter: false, GetPen());
	}

	/// <summary>
	/// Draws an arc using the current pen settings, with an option to connect to the center.
	/// </summary>
	/// <param name="rect">The bounding rectangle of the arc.</param>
	/// <param name="startAngle">The starting angle of the arc, in degrees.</param>
	/// <param name="sweepAngle">The sweep angle of the arc, in degrees.</param>
	/// <param name="useCenter">If true, connects the arc endpoints to the center point, forming a pie shape.</param>
	[Description("Draws an arc using the current pen settings, with an option to connect to the center.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 99)]
	public void DrawArc([Description("The bounding rectangle of the arc.")] Rect rect, [Description("The starting angle of the arc, in degrees.")] float startAngle, [Description("The sweep angle of the arc, in degrees.")] float sweepAngle, [Description("If true, connects the arc endpoints to the center point, forming a pie shape.")] bool useCenter)
	{
		_canvas.DrawArc(rect.ToSk(), startAngle, sweepAngle, useCenter, GetPen());
	}

	/// <summary>
	/// Draws another bitmap onto this bitmap.
	/// </summary>
	/// <param name="bitmap">The bitmap to draw.</param>
	/// <param name="destRect">The destination rectangle for the drawn bitmap.</param>
	[Description("Draws another bitmap onto this bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 109)]
	public void DrawBitmap([Description("The bitmap to draw.")] Bitmap bitmap, [Description("The destination rectangle for the drawn bitmap.")] Rect destRect)
	{
		_canvas.DrawBitmap(bitmap._bitmap, destRect.ToSk(), GetPen());
	}

	/// <summary>
	/// Draws a line using the current pen settings.
	/// </summary>
	/// <param name="start">The starting point of the line.</param>
	/// <param name="end">The ending point of the line.</param>
	[Description("Draws a line using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 119)]
	public void DrawLine([Description("The starting point of the line.")] Vector2 start, [Description("The ending point of the line.")] Vector2 end)
	{
		_canvas.DrawLine(start.ToSk(), end.ToSk(), GetPen());
	}

	/// <summary>
	/// Draws connected lines through a series of points using the current pen settings.
	/// </summary>
	/// <param name="points">The points to connect with lines.</param>
	[Description("Draws connected lines through a series of points using the current pen settings.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Draw.cs", 128)]
	public void DrawLines([Description("The points to connect with lines.")] params Vector2[] points)
	{
		if (points == null || points.Length < 2)
		{
			throw new ArgumentException("At least two points are required to draw lines.", "points");
		}
		SKPaint pen = GetPen();
		using SKPath sKPath = new SKPath();
		sKPath.MoveTo(points[0].ToSk());
		for (int i = 1; i < points.Length; i++)
		{
			sKPath.LineTo(points[i].ToSk());
		}
		_canvas.DrawPath(sKPath, pen);
	}

	/// <summary>
	/// Applies a Gaussian blur effect to the current bitmap.
	/// </summary>
	/// <param name="radius">The radius of the blur, controlling its intensity. Must be non-negative.</param>
	/// <param name="tileClamp">Determines the behavior at the edges of the bitmap:
	/// <c>true</c> to clamp the edges (default), or <c>false</c> to repeat the edges.</param>
	[Description("Applies a Gaussian blur effect to the current bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 14)]
	public void Blur([Description("The radius of the blur, controlling its intensity. Must be non-negative.")] float radius, [Description("Determines the behavior at the edges of the bitmap: <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">true</code> to clamp the edges (default), or <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">false</code> to repeat the edges.")] bool tileClamp = true)
	{
		SKShaderTileMode sKShaderTileMode = ((!tileClamp) ? SKShaderTileMode.Repeat : SKShaderTileMode.Clamp);
		using SKPaint paint = new SKPaint
		{
			Shader = SKShader.CreateBitmap(_bitmap, sKShaderTileMode, sKShaderTileMode),
			ImageFilter = SKImageFilter.CreateBlur(radius, radius, SKShaderTileMode.Clamp)
		};
		_canvas.Clear(SKColors.Transparent);
		_canvas.DrawRect(new SKRect(-_bitmap.Width, -_bitmap.Height, _bitmap.Width * 2, _bitmap.Height * 2), paint);
	}

	/// <summary>
	/// Applies a Gaussian blur effect to the current bitmap.
	/// </summary>
	[Description("Applies a Gaussian blur effect to the current bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 31)]
	public void Sharpen(float amount, bool tileClamp = true)
	{
		SKShaderTileMode sKShaderTileMode = ((!tileClamp) ? SKShaderTileMode.Repeat : SKShaderTileMode.Clamp);
		float[] array = new float[9]
		{
			0f,
			0f - amount,
			0f,
			0f - amount,
			1f + 4f * amount,
			0f - amount,
			0f,
			0f - amount,
			0f
		};
		using SKPaint paint = new SKPaint
		{
			Shader = SKShader.CreateBitmap(_bitmap, sKShaderTileMode, sKShaderTileMode),
			ImageFilter = SKImageFilter.CreateMatrixConvolution(new SKSizeI(3, 3), array, 1f, 0f, new SKPointI(1, 1), (!tileClamp) ? SKShaderTileMode.Repeat : SKShaderTileMode.Clamp, convolveAlpha: false)
		};
		_canvas.Clear(SKColors.Transparent);
		_canvas.DrawRect(new SKRect(-_bitmap.Width, -_bitmap.Height, _bitmap.Width * 2, _bitmap.Height * 2), paint);
	}

	/// <summary>
	/// Adjusts brightness, contrast, and saturation in one pass.
	/// </summary>
	[Description("Adjusts brightness, contrast, and saturation in one pass.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 55)]
	public void Adjust(float brightness = 1f, float contrast = 1f, float saturation = 1f, float hueDegrees = 0f)
	{
		float num = brightness - 1f;
		float num2 = (1f - contrast) * 0.5f + num;
		float num3 = 0.2126f;
		float num4 = 0.7152f;
		float num5 = 0.0722f;
		float num6 = 1f - saturation;
		float[] matrix = new float[20]
		{
			contrast * (num6 * num3 + saturation),
			contrast * num6 * num4,
			contrast * num6 * num5,
			0f,
			num2,
			contrast * num6 * num3,
			contrast * (num6 * num4 + saturation),
			contrast * num6 * num5,
			0f,
			num2,
			contrast * num6 * num3,
			contrast * num6 * num4,
			contrast * (num6 * num5 + saturation),
			0f,
			num2,
			0f,
			0f,
			0f,
			1f,
			0f
		};
		float x = hueDegrees.DegreeToRadian();
		float num7 = MathF.Cos(x);
		float num8 = MathF.Sin(x);
		float[] matrix2 = new float[20]
		{
			num3 + num7 * (1f - num3) - num3 * num8,
			num4 - num4 * num7 - num4 * num8,
			num5 - num5 * num7 + (1f - num5) * num8,
			0f,
			0f,
			num3 - num3 * num7 + 0.143f * num8,
			num4 + num7 * (1f - num4) + 0.14f * num8,
			num5 - num5 * num7 - 0.283f * num8,
			0f,
			0f,
			num3 - num3 * num7 - (1f - num3) * num8,
			num4 - num4 * num7 + num4 * num8,
			num5 + num7 * (1f - num5) + num5 * num8,
			0f,
			0f,
			0f,
			0f,
			0f,
			1f,
			0f
		};
		using SKColorFilter outer = SKColorFilter.CreateColorMatrix(matrix);
		using SKColorFilter inner = SKColorFilter.CreateColorMatrix(matrix2);
		using SKColorFilter colorFilter = SKColorFilter.CreateCompose(outer, inner);
		using SKPaint paint = new SKPaint
		{
			Shader = SKShader.CreateBitmap(_bitmap),
			ColorFilter = colorFilter
		};
		_canvas.DrawRect(_bitmap.Info.Rect, paint);
	}

	/// <summary>
	/// Adjusts the hue of the bitmap.
	/// </summary>
	/// <param name="angle">The angle to rotate the hue, in degrees (0 to 360).</param>
	[Description("Adjusts the hue of the bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 108)]
	public void AdjustHue([Description("The angle to rotate the hue, in degrees (0 to 360).")] float angle)
	{
		angle %= 360f;
		float num = angle * (float)Math.PI / 180f;
		float num2 = (float)Math.Cos(num);
		float num3 = (float)Math.Sin(num);
		using SKColorFilter colorFilter = SKColorFilter.CreateColorMatrix(new float[20]
		{
			0.213f + num2 * 0.787f - num3 * 0.213f,
			0.213f - num2 * 0.213f + num3 * 0.143f,
			0.213f - num2 * 0.213f - num3 * 0.787f,
			0f,
			0f,
			0.715f - num2 * 0.715f - num3 * 0.715f,
			0.715f + num2 * 0.285f + num3 * 0.14f,
			0.715f - num2 * 0.715f + num3 * 0.715f,
			0f,
			0f,
			0.072f - num2 * 0.072f + num3 * 0.928f,
			0.072f - num2 * 0.072f - num3 * 0.283f,
			0.072f + num2 * 0.928f + num3 * 0.072f,
			0f,
			0f,
			0f,
			0f,
			0f,
			1f,
			0f
		});
		using SKPaint paint = new SKPaint
		{
			Shader = SKShader.CreateBitmap(_bitmap, SKShaderTileMode.Clamp, SKShaderTileMode.Clamp),
			ColorFilter = colorFilter
		};
		_canvas.DrawRect(new SKRect(0f, 0f, _bitmap.Width, _bitmap.Height), paint);
	}

	/// <summary>
	/// Color the bitmap using this color, respect alpha
	/// </summary>
	[Description("Color the bitmap using this color, respect alpha")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 137)]
	public void Colorize(Color color)
	{
		using SKPaint paint = new SKPaint
		{
			BlendMode = SKBlendMode.SrcATop,
			ColorF = color.ToSkF()
		};
		_canvas.DrawRect(new SKRect(0f, 0f, _bitmap.Width, _bitmap.Height), paint);
	}

	/// <summary>
	/// Tint the bitmap using this color, respect alpha
	/// </summary>
	/// <param name="color"></param>
	[Description("Tint the bitmap using this color, respect alpha")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 153)]
	public void Tint(Color color)
	{
		using SKPaint paint = new SKPaint
		{
			BlendMode = SKBlendMode.Modulate,
			ColorF = color.ToSkF()
		};
		_canvas.DrawRect(new SKRect(0f, 0f, _bitmap.Width, _bitmap.Height), paint);
	}

	/// <summary>
	/// Shrink the image by adding padding all around - without resizing the bitmap
	/// </summary>
	[Description("Shrink the image by adding padding all around - without resizing the bitmap")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 168)]
	public void InsertPadding(Margin margin)
	{
		SKRect dest = Rect.Shrink(in margin).ToSk();
		using SKBitmap bitmap = _bitmap.Copy();
		_canvas.Clear(SKColors.Transparent);
		_canvas.DrawBitmap(bitmap, dest);
	}

	/// <summary>
	/// Applies a posterize effect to the bitmap.
	/// </summary>
	/// <param name="levels">The number of color levels to reduce to (e.g., 2, 4, 8).</param>
	[Description("Applies a posterize effect to the bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 182)]
	internal void Posterize([Description("The number of color levels to reduce to (e.g., 2, 4, 8).")] int levels)
	{
		if (levels < 2)
		{
			levels = 2;
		}
		byte[] array = new byte[256];
		byte[] array2 = new byte[256];
		byte[] array3 = new byte[256];
		byte[] array4 = new byte[256];
		for (int i = 0; i < 256; i++)
		{
			array4[i] = (byte)i;
		}
		float num = 255f / (float)(levels - 1);
		for (int j = 0; j < 256; j++)
		{
			array3[j] = (array2[j] = (array[j] = (byte)MathF.Round((float)(int)MathF.Round((float)j / num) * num)));
		}
		using SKPaint paint = new SKPaint
		{
			Shader = SKShader.CreateBitmap(_bitmap, SKShaderTileMode.Clamp, SKShaderTileMode.Clamp),
			ColorFilter = SKColorFilter.CreateTable(array, array2, array3, array4)
		};
		_canvas.DrawRect(new SKRect(0f, 0f, _bitmap.Width, _bitmap.Height), paint);
	}

	/// <summary>
	/// Converts a heightmap to a normal map using parallel processing.
	/// </summary>
	/// <param name="strength">The strength of the normal map effect (default is 1.0).</param>
	/// <returns>The generated normal map as an SKBitmap.</returns>
	[Description("Converts a heightmap to a normal map using parallel processing.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 219)]
	[return: Description("The generated normal map as an SKBitmap.")]
	public Bitmap HeightmapToNormalMap([Description("The strength of the normal map effect (default is 1.0).")] float strength = 1f)
	{
		if (IsFloatingPoint)
		{
			return null;
		}
		int width = _bitmap.Width;
		int height = _bitmap.Height;
		Bitmap bitmap = Clone();
		SKColor[] heightmapPixels = _bitmap.Pixels;
		SKColor[] normalMapPixels = bitmap._bitmap.Pixels;
		System.Threading.Tasks.Parallel.For(0, height, (int y) =>
		{
			for (int i = 0; i < width; i++)
			{
				float height2 = GetHeight(heightmapPixels, width, height, i - 1, y);
				float height3 = GetHeight(heightmapPixels, width, height, i + 1, y);
				float height4 = GetHeight(heightmapPixels, width, height, i, y - 1);
				float height5 = GetHeight(heightmapPixels, width, height, i, y + 1);
				float num = (height3 - height2) * strength;
				float num2 = (height5 - height4) * strength;
				Vector3 normal = new Vector3(0f - num, 0f - num2, 1f).Normal;
				byte red = (byte)((normal.x * 0.5f + 0.5f) * 255f);
				byte green = (byte)((normal.y * 0.5f + 0.5f) * 255f);
				byte blue = (byte)((normal.z * 0.5f + 0.5f) * 255f);
				normalMapPixels[y * width + i] = new SKColor(red, green, blue, byte.MaxValue);
			}
		});
		bitmap._bitmap.Pixels = normalMapPixels;
		return bitmap;
	}

	/// <summary>
	/// Gets the height value from the pixel array, clamped to the edges.
	/// </summary>
	[Description("Gets the height value from the pixel array, clamped to the edges.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 269)]
	private static float GetHeight(SKColor[] pixels, int width, int height, int x, int y)
	{
		x = Math.Clamp(x, 0, width - 1);
		y = Math.Clamp(y, 0, height - 1);
		SKColor sKColor = pixels[y * width + x];
		return (float)(int)sKColor.Red / 255f;
	}

	/// <summary>
	/// Inverts the colors of the bitmap while preserving alpha.
	/// </summary>
	[Description("Inverts the colors of the bitmap while preserving alpha.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Filters.cs", 281)]
	public void InvertColor()
	{
		SKPaint sKPaint = new SKPaint();
		sKPaint.Shader = SKShader.CreateBitmap(_bitmap, SKShaderTileMode.Clamp, SKShaderTileMode.Clamp);
		sKPaint.ColorFilter = SKColorFilter.CreateColorMatrix((ReadOnlySpan<float>)new float[20]
		{
			-1f, 0f, 0f, 0f, 1f, 0f, -1f, 0f, 0f, 1f,
			0f, 0f, -1f, 0f, 1f, 0f, 0f, 0f, 1f, 0f
		});
		using SKPaint paint = sKPaint;
		_canvas.DrawRect(new SKRect(0f, 0f, _bitmap.Width, _bitmap.Height), paint);
	}

	/// <summary>
	/// Loads a bitmap from the specified byte array.
	/// </summary>
	/// <param name="data">The byte array containing the image data.</param>
	/// <returns>A new <see cref="T:Sandbox.Bitmap" /> instance.</returns>
	[Description("Loads a bitmap from the specified byte array.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.cs", 12)]
	[return: Description("A new <span style=\"color: #4EC9B0;\">Bitmap</span> instance.")]
	public static Bitmap CreateFromBytes([Description("The byte array containing the image data.")] byte[] data)
	{
		using (SKMemoryStream stream = new SKMemoryStream(data))
		{
			using SKCodec sKCodec = SKCodec.Create(stream);
			if (sKCodec != null)
			{
				_ = sKCodec.Info;
				SKImageInfo bitmapInfo = new SKImageInfo(sKCodec.Info.Width, sKCodec.Info.Height, SKColorType.Rgba8888, SKAlphaType.Unpremul);
				SKBitmap sKBitmap = SKBitmap.Decode(sKCodec, bitmapInfo);
				if (sKBitmap != null)
				{
					return new Bitmap(sKBitmap);
				}
			}
		}
		return CreateFromTgaBytes(data) ?? CreateFromPsdBytes(data) ?? CreateFromTifBytes(data) ?? CreateFromIesBytes(data);
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 9)]
	public unsafe static Bitmap CreateFromIesBytes(byte[] data)
	{
		if (!IsIes(data))
		{
			return null;
		}
		IES iES = new IES();
		try
		{
			using MemoryStream stream = new MemoryStream(data);
			iES.ParseIESInfo(stream);
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Warning($"Failed to parse IES file: {ex.Message}");
			return null;
		}
		if (iES.CandelasMax <= 0f)
		{
			GlobalSystemNamespace.Log.Warning("IES file has invalid maximum candela value.");
			return null;
		}
		float num = 1f / iES.CandelasMax;
		Half[] array = new Half[1048576];
		for (int i = 0; i < 512; i++)
		{
			for (int j = 0; j < 512; j++)
			{
				float num2 = (float)j / 512f * 2f - 1f;
				float num3 = (float)i / 512f * 2f - 1f;
				float radius = MathF.Sqrt(num2 * num2 + num3 * num3);
				float angleDeg = MathF.Atan2(num3, num2) * 180f / (float)Math.PI;
				float num4 = iES.Sample2D(radius, angleDeg);
				num4 = MathF.Max(0f, num4 * num);
				num4 = MathF.Pow(num4, 2.2f);
				int num5 = (i * 512 + j) * 4;
				array[num5] = (Half)num4;
				array[num5 + 1] = (Half)num4;
				array[num5 + 2] = (Half)num4;
				array[num5 + 3] = (Half)1f;
			}
		}
		SKBitmap sKBitmap = new SKBitmap(512, 512, SKColorType.RgbaF16, SKAlphaType.Unpremul);
		fixed (Half* pixels = array)
		{
			sKBitmap.SetPixels((nint)pixels);
		}
		return new Bitmap(sKBitmap);
	}

	/// <summary>
	/// Return true if this data is a Ies file
	/// </summary>
	[Description("Return true if this data is a Ies file")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Ies.cs", 236)]
	public static bool IsIes(byte[] data)
	{
		if (data == null || data.Length < 10)
		{
			return false;
		}
		return Encoding.ASCII.GetString(data, 0, Math.Min(20, data.Length)).Trim().StartsWith("IESNA");
	}

	/// <summary>
	/// Creates a Bitmap instance from PSD file data.
	/// </summary>
	/// <param name="data">Byte array containing the PSD file data.</param>
	/// <returns>A Bitmap instance if successful, or null if the data is not valid PSD.</returns>
	[Description("Creates a Bitmap instance from PSD file data.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Psd.cs", 12)]
	[return: Description("A Bitmap instance if successful, or null if the data is not valid PSD.")]
	public unsafe static Bitmap CreateFromPsdBytes([Description("Byte array containing the PSD file data.")] byte[] data)
	{
		if (!IsPsd(data))
		{
			return null;
		}
		FloatBitMap_t floatBitMap_t = FloatBitMap_t.Create();
		try
		{
			fixed (byte* pBuffer = data)
			{
				if (!floatBitMap_t.LoadFromInMemoryPSD((nint)pBuffer, data.Length))
				{
					return null;
				}
				SKBitmap sKBitmap = new SKBitmap(floatBitMap_t.Width(), floatBitMap_t.Height(), SKColorType.Rgba8888, SKAlphaType.Unpremul);
				floatBitMap_t.WriteToBuffer(sKBitmap.GetPixels(), sKBitmap.ByteCount, ImageFormat.RGBA8888, bLowQualityFastCompile: false, bIsSrgb: false, 0u);
				return new Bitmap(sKBitmap);
			}
		}
		finally
		{
			floatBitMap_t.Delete();
		}
	}

	/// <summary>
	/// Checks if the provided byte array is a valid PSD file.
	/// </summary>
	/// <param name="data">Byte array to check.</param>
	/// <returns>True if the data is a PSD file, otherwise false.</returns>
	[Description("Checks if the provided byte array is a valid PSD file.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Psd.cs", 44)]
	[return: Description("True if the data is a PSD file, otherwise false.")]
	public static bool IsPsd([Description("Byte array to check.")] byte[] data)
	{
		if (data == null || data.Length < 26)
		{
			return false;
		}
		if (data[0] == 56 && data[1] == 66 && data[2] == 80)
		{
			return data[3] == 83;
		}
		return false;
	}

	/// <summary>
	/// Create a bitmap from an SVG, with optional size
	/// </summary>
	[Description("Create a bitmap from an SVG, with optional size")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Svg.cs", 11)]
	public static Bitmap CreateFromSvgString(string svgContents, int? width, int? height, Vector2? scale = null, Vector2? offset = null, float? rotation = null)
	{
		SvgDocument svgDocument = SvgDocument.FromSvg<SvgDocument>(svgContents.Trim());
		int num = svgDocument.Width.Value.FloorToInt();
		int num2 = svgDocument.Height.Value.FloorToInt();
		int val = width ?? num;
		int val2 = height ?? num2;
		val = Math.Min(val, 4096);
		val2 = Math.Min(val2, 4096);
		if (width.HasValue && !height.HasValue)
		{
			val2 = width.Value * num2 / num;
		}
		if (height.HasValue && !width.HasValue)
		{
			val = height.Value * num / num2;
		}
		SKBitmap bitmap = new SKBitmap(val, val2, SKColorType.Rgba8888, SKAlphaType.Unpremul);
		using (SKSvg sKSvg = new SKSvg())
		{
			using SKCanvas sKCanvas = new SKCanvas(bitmap);
			sKSvg.FromSvgDocument(svgDocument);
			using SKPaint paint = new SKPaint();
			SKRect cullRect = sKSvg.Picture.CullRect;
			float s = Math.Min((float)val / cullRect.Width, (float)val2 / cullRect.Height);
			float num3 = cullRect.Left + cullRect.Width / 2f;
			float num4 = cullRect.Top + cullRect.Height / 2f;
			if (offset.HasValue)
			{
				sKCanvas.Translate(offset.Value.x, offset.Value.y);
			}
			sKCanvas.Translate(val / 2, val2 / 2);
			sKCanvas.Scale(s);
			if (scale.HasValue)
			{
				sKCanvas.Scale(scale.Value.x, scale.Value.y);
			}
			if (rotation.HasValue)
			{
				sKCanvas.RotateDegrees(rotation.Value);
			}
			sKCanvas.Translate(0f - num3, 0f - num4);
			sKCanvas.DrawPicture(sKSvg.Picture, paint);
		}
		return new Bitmap(bitmap);
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tga.cs", 7)]
	public unsafe static Bitmap CreateFromTgaBytes(byte[] data)
	{
		if (!IsTga(data))
		{
			return null;
		}
		FloatBitMap_t floatBitMap_t = FloatBitMap_t.Create();
		try
		{
			fixed (byte* pBuffer = data)
			{
				if (!floatBitMap_t.LoadFromInMemoryTGA((nint)pBuffer, data.Length))
				{
					return null;
				}
				SKBitmap sKBitmap = new SKBitmap(floatBitMap_t.Width(), floatBitMap_t.Height(), SKColorType.Rgba8888, SKAlphaType.Unpremul);
				floatBitMap_t.WriteToBuffer(sKBitmap.GetPixels(), sKBitmap.ByteCount, ImageFormat.RGBA8888, bLowQualityFastCompile: false, bIsSrgb: false, 0u);
				return new Bitmap(sKBitmap);
			}
		}
		finally
		{
			floatBitMap_t.Delete();
		}
	}

	/// <summary>
	/// Return true if this data is a Tga file
	/// </summary>
	[Description("Return true if this data is a Tga file")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tga.cs", 37)]
	public static bool IsTga(byte[] data)
	{
		if (data == null || data.Length < 18)
		{
			return false;
		}
		int num = data[2];
		if (num == 2 || num == 3 || num == 10)
		{
			int num2 = data[12] | (data[13] << 8);
			int num3 = data[14] | (data[15] << 8);
			if (num2 > 0)
			{
				return num3 > 0;
			}
			return false;
		}
		return false;
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 7)]
	public unsafe static Bitmap CreateFromTifBytes(byte[] data)
	{
		if (!IsTif(data))
		{
			return null;
		}
		FloatBitMap_t floatBitMap_t = FloatBitMap_t.Create();
		try
		{
			fixed (byte* pBuffer = data)
			{
				if (!floatBitMap_t.LoadFromInMemoryTIF((nint)pBuffer, data.Length))
				{
					return null;
				}
				SKBitmap sKBitmap = new SKBitmap(floatBitMap_t.Width(), floatBitMap_t.Height(), SKColorType.Rgba8888, SKAlphaType.Unpremul);
				floatBitMap_t.WriteToBuffer(sKBitmap.GetPixels(), sKBitmap.ByteCount, ImageFormat.RGBA8888, bLowQualityFastCompile: false, bIsSrgb: false, 0u);
				return new Bitmap(sKBitmap);
			}
		}
		finally
		{
			floatBitMap_t.Delete();
		}
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 38)]
	public static bool IsTif(ReadOnlySpan<byte> data)
	{
		if (data.Length < 8)
		{
			return false;
		}
		ushort num = ReadUInt16LittleEndian(data.Slice(0, 2));
		ushort num2 = ReadUInt16LittleEndian(data.Slice(2, 2));
		return num switch
		{
			19789 => SwapUInt16(num2) == 42, 
			18761 => num2 == 42, 
			_ => false, 
		};
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 54)]
	private static ushort ReadUInt16LittleEndian(ReadOnlySpan<byte> bytes)
	{
		return (ushort)(bytes[0] | (bytes[1] << 8));
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Loading.Tif.cs", 59)]
	private static ushort SwapUInt16(ushort value)
	{
		return (ushort)((value >> 8) | (value << 8));
	}

	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 9)]
	private SKPaint GetPen()
	{
		if (_pen != null)
		{
			return _pen;
		}
		_pen = new SKPaint();
		_pen.IsAntialias = true;
		return _pen;
	}

	/// <summary>
	/// Sets the pen for drawing with a solid color and stroke style.
	/// </summary>
	[Description("Sets the pen for drawing with a solid color and stroke style.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 22)]
	public void SetAntialias(bool on)
	{
		GetPen().IsAntialias = on;
	}

	/// <summary>
	/// Sets the pen to use a specific blend mode.
	/// </summary>
	/// <param name="blendMode">The blend mode to apply.</param>
	[Description("Sets the pen to use a specific blend mode.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 32)]
	public void SetBlendMode([Description("The blend mode to apply.")] BlendMode blendMode)
	{
		GetPen();
	}

	/// <summary>
	/// Sets the pen for drawing with a solid color and stroke style.
	/// </summary>
	/// <param name="color">The color of the pen.</param>
	/// <param name="width">The width of the pen in pixels.</param>
	[Description("Sets the pen for drawing with a solid color and stroke style.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 44)]
	public void SetPen([Description("The color of the pen.")] Color color, [Description("The width of the pen in pixels.")] float width)
	{
		SKPaint pen = GetPen();
		pen.Color = color.ToSk();
		pen.ColorF = color.ToSkF();
		pen.StrokeWidth = width;
		pen.Style = SKPaintStyle.Stroke;
		pen.PathEffect = null;
		pen.Shader = null;
	}

	/// <summary>
	/// Sets the pen for drawing dashed or dotted lines.
	/// </summary>
	/// <param name="color">The color of the pen.</param>
	/// <param name="width">The width of the pen in pixels.</param>
	/// <param name="dashPattern">An array defining the dash pattern (e.g., [10, 5] for 10px dash, 5px gap).</param>
	[Description("Sets the pen for drawing dashed or dotted lines.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 61)]
	public void SetDashedPen([Description("The color of the pen.")] Color color, [Description("The width of the pen in pixels.")] float width, [Description("An array defining the dash pattern (e.g., [10, 5] for 10px dash, 5px gap).")] float[] dashPattern)
	{
		SKPaint pen = GetPen();
		pen.Color = color.ToSk();
		pen.ColorF = color.ToSkF();
		pen.StrokeWidth = width;
		pen.Style = SKPaintStyle.Stroke;
		pen.PathEffect = SKPathEffect.CreateDash(dashPattern, 0f);
		pen.Shader = null;
	}

	/// <summary>
	/// Sets the pen for drawing filled shapes with a solid color.
	/// </summary>
	/// <param name="color">The color to fill the shapes with.</param>
	[Description("Sets the pen for drawing filled shapes with a solid color.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 76)]
	public void SetFill([Description("The color to fill the shapes with.")] Color color)
	{
		SKPaint pen = GetPen();
		pen.Color = color.ToSk();
		pen.ColorF = color.ToSkF();
		pen.Style = SKPaintStyle.Fill;
		pen.StrokeWidth = 0f;
		pen.Shader = null;
	}

	/// <summary>
	/// Sets the pen for drawing with a linear gradient.
	/// </summary>
	/// <param name="start">the gradient's start point.</param>
	/// <param name="end">the gradient's end point.</param>
	/// <param name="gradient">The color of the gradient.</param>
	[Description("Sets the pen for drawing with a linear gradient.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 94)]
	public void SetLinearGradient([Description("the gradient's start point.")] Vector2 start, [Description("the gradient's end point.")] Vector2 end, [Description("The color of the gradient.")] Gradient gradient)
	{
		SKPaint pen = GetPen();
		pen.StrokeWidth = 0f;
		using SKColorSpace colorspace = SKColorSpace.CreateSrgbLinear();
		pen.Shader = SKShader.CreateLinearGradient(new SKPoint(start.x, start.y), new SKPoint(end.x, end.y), gradientPoints.Select((float x) => gradient.Evaluate(x).ToSkF()).ToArray(), colorspace, gradientPoints, SKShaderTileMode.Clamp);
		pen.Style = SKPaintStyle.Fill;
	}

	/// <summary>
	/// Sets the pen for drawing with a radial gradient.
	/// </summary>
	/// <param name="center">The gradient's center.</param>
	/// <param name="radius">The radius of the gradient.</param>
	/// <param name="gradient">The color of the gradient.</param>
	[Description("Sets the pen for drawing with a radial gradient.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Pen.cs", 118)]
	public void SetRadialGradient([Description("The gradient's center.")] Vector2 center, [Description("The radius of the gradient.")] float radius, [Description("The color of the gradient.")] Gradient gradient)
	{
		SKPaint pen = GetPen();
		pen.StrokeWidth = 0f;
		using SKColorSpace colorspace = SKColorSpace.CreateSrgbLinear();
		pen.Shader = SKShader.CreateRadialGradient(new SKPoint(center.x, center.y), radius, gradientPoints.Select((float x) => gradient.Evaluate(x).ToSkF()).ToArray(), colorspace, gradientPoints, SKShaderTileMode.Clamp);
		pen.IsAntialias = true;
		pen.Style = SKPaintStyle.Fill;
	}

	/// <summary>
	/// Exports the bitmap as a JPEG byte array with the specified quality.
	/// </summary>
	/// <param name="quality">The quality of the JPEG, between 0 and 100.</param>
	/// <returns>A byte array containing the JPEG image data.</returns>
	[Description("Exports the bitmap as a JPEG byte array with the specified quality.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 13)]
	[return: Description("A byte array containing the JPEG image data.")]
	public byte[] ToJpg([Description("The quality of the JPEG, between 0 and 100.")] int quality = 100)
	{
		return Encode(SKEncodedImageFormat.Jpeg, quality);
	}

	/// <summary>
	/// Exports the bitmap as a PNG byte array.
	/// </summary>
	/// <returns>A byte array containing the PNG image data.</returns>
	[Description("Exports the bitmap as a PNG byte array.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 22)]
	[return: Description("A byte array containing the PNG image data.")]
	public byte[] ToPng()
	{
		return Encode(SKEncodedImageFormat.Png, 100);
	}

	/// <summary>
	/// Exports the bitmap as a BMP byte array.
	/// </summary>
	/// <returns>A byte array containing the BMP image data.</returns>
	[Description("Exports the bitmap as a BMP byte array.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 31)]
	[return: Description("A byte array containing the BMP image data.")]
	public byte[] ToBmp()
	{
		return Encode(SKEncodedImageFormat.Bmp, 100);
	}

	/// <summary>
	/// Exports the bitmap as an HDR WebP byte array with the specified quality.
	/// </summary>
	/// <param name="quality">The quality of the WebP image, between 0 and 100.</param>
	/// <returns>A byte array containing the WebP HDR image data.</returns>
	[Description("Exports the bitmap as an HDR WebP byte array with the specified quality.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 41)]
	[return: Description("A byte array containing the WebP HDR image data.")]
	public byte[] ToWebP([Description("The quality of the WebP image, between 0 and 100.")] int quality = 100)
	{
		return Encode(SKEncodedImageFormat.Webp, quality);
	}

	/// <summary>
	/// Exports the bitmap to the specified image format with optional quality.
	/// </summary>
	/// <param name="format">The image format (e.g., PNG, JPEG, BMP).</param>
	/// <param name="quality">The quality of the image, used for formats like JPEG.</param>
	/// <returns>A byte array containing the image data.</returns>
	[Description("Exports the bitmap to the specified image format with optional quality.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 52)]
	[return: Description("A byte array containing the image data.")]
	private byte[] Encode([Description("The image format (e.g., PNG, JPEG, BMP).")] SKEncodedImageFormat format, [Description("The quality of the image, used for formats like JPEG.")] int quality)
	{
		using SKImage sKImage = SKImage.FromBitmap(_bitmap);
		using SKData sKData = sKImage.Encode(format, quality);
		return sKData.ToArray();
	}

	/// <summary>
	/// Exports the bitmap to the specified engine format
	/// </summary>
	/// <param name="format">The target image format to encode to.</param>
	[Description("Exports the bitmap to the specified engine format")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Saving.cs", 63)]
	public byte[] ToFormat([Description("The target image format to encode to.")] ImageFormat format)
	{
		nint pixels = _bitmap.GetPixels();
		using FloatBitmap floatBitmap = new FloatBitmap(Width, Height, ImageFormat, pixels, ByteCount);
		return floatBitmap.EncodeTo(format);
	}

	/// <summary>
	/// Draws text onto this bitmap. The text is rendered on the GPU and read back.
	/// </summary>
	[Description("Draws text onto this bitmap. The text is rendered on the GPU and read back.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Text.cs", 10)]
	public void DrawText(TextRendering.Scope scope, Rect rect, TextFlag flags = TextFlag.Center)
	{
		TextRendering.TextBlock orCreateTextBlock = TextRendering.GetOrCreateTextBlock(in scope, flags, rect.Size);
		if (orCreateTextBlock == null || orCreateTextBlock.IsEmpty)
		{
			return;
		}
		orCreateTextBlock.MakeReady();
		if (orCreateTextBlock.Texture == null)
		{
			return;
		}
		using Bitmap bitmap = orCreateTextBlock.Texture.GetBitmap();
		if (bitmap != null)
		{
			Vector2 vector = rect.Align(new Vector2(orCreateTextBlock.Layout.MeasuredWidth, orCreateTextBlock.Layout.MeasuredHeight), flags).Position - orCreateTextBlock.BlockOrigin;
			_canvas.DrawBitmap(bitmap._bitmap, vector.x, vector.y);
		}
	}

	/// <summary>
	/// Try to create a texture from this bitmap
	/// </summary>
	[Description("Try to create a texture from this bitmap")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Texture.cs", 10)]
	public Texture ToTexture(bool mips = true)
	{
		Texture2DBuilder texture2DBuilder = Texture.Create(Width, Height).WithFormat(ImageFormat).WithData(_bitmap.GetPixels(), _bitmap.BytesPerPixel * Width * Height);
		if (mips)
		{
			texture2DBuilder = texture2DBuilder.WithMips();
		}
		return texture2DBuilder.Finish();
	}

	/// <summary>
	/// Rotates the bitmap by the specified angle.
	/// </summary>
	/// <param name="degrees">The angle in degrees to rotate the bitmap.</param>
	/// <returns>A new <see cref="T:Sandbox.Bitmap" /> instance with the rotated image.</returns>
	[Description("Rotates the bitmap by the specified angle.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Transforms.cs", 12)]
	[return: Description("A new <span style=\"color: #4EC9B0;\">Bitmap</span> instance with the rotated image.")]
	public Bitmap Rotate([Description("The angle in degrees to rotate the bitmap.")] float degrees)
	{
		float num = (float)Math.Abs(Math.Sin(degrees.DegreeToRadian()));
		float num2 = (float)Math.Abs(Math.Cos(degrees.DegreeToRadian()));
		int num3 = (int)(num2 * (float)Width + num * (float)Height);
		int num4 = (int)(num2 * (float)Height + num * (float)Width);
		SKBitmap bitmap = new SKBitmap(num3, num4, _bitmap.ColorType, _bitmap.AlphaType);
		using (SKCanvas sKCanvas = new SKCanvas(bitmap))
		{
			sKCanvas.Clear(SKColors.Transparent);
			sKCanvas.Translate((float)num3 / 2f, (float)num4 / 2f);
			sKCanvas.RotateDegrees(degrees);
			sKCanvas.Translate((float)(-Width) / 2f, (float)(-Height) / 2f);
			sKCanvas.DrawBitmap(_bitmap, 0f, 0f);
		}
		return new Bitmap(bitmap);
	}

	/// <summary>
	/// Resizes the bitmap to the specified dimensions and returns a new bitmap.
	/// </summary>
	/// <param name="newWidth">The new width of the bitmap.</param>
	/// <param name="newHeight">The new height of the bitmap.</param>
	/// <param name="smooth">Resample smoothly. If false this will be nearest neighbour.</param>
	/// <returns>A new <see cref="T:Sandbox.Bitmap" /> instance with the specified dimensions.</returns>
	[Description("Resizes the bitmap to the specified dimensions and returns a new bitmap.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Transforms.cs", 41)]
	[return: Description("A new <span style=\"color: #4EC9B0;\">Bitmap</span> instance with the specified dimensions.")]
	public Bitmap Resize([Description("The new width of the bitmap.")] int newWidth, [Description("The new height of the bitmap.")] int newHeight, [Description("Resample smoothly. If false this will be nearest neighbour.")] bool smooth = true)
	{
		if (newWidth <= 0 || newHeight <= 0)
		{
			throw new ArgumentOutOfRangeException("Width and height must be greater than zero.");
		}
		SKImageInfo info = new SKImageInfo(newWidth, newHeight, _bitmap.ColorType, _bitmap.AlphaType);
		SKSamplingOptions sampling = (smooth ? new SKSamplingOptions(SKFilterMode.Linear, SKMipmapMode.Linear) : SKSamplingOptions.Default);
		return new Bitmap(_bitmap.Resize(info, sampling));
	}

	/// <summary>
	/// Flips the bitmap vertically.
	/// </summary>
	/// <returns>A new <see cref="T:Sandbox.Bitmap" /> instance with the flipped image.</returns>
	[Description("Flips the bitmap vertically.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Transforms.cs", 58)]
	[return: Description("A new <span style=\"color: #4EC9B0;\">Bitmap</span> instance with the flipped image.")]
	public Bitmap FlipVertical()
	{
		SKBitmap bitmap = new SKBitmap(_bitmap.Width, _bitmap.Height, _bitmap.ColorType, _bitmap.AlphaType);
		using (SKCanvas sKCanvas = new SKCanvas(bitmap))
		{
			sKCanvas.Scale(1f, -1f);
			sKCanvas.Translate(0f, -_bitmap.Height);
			sKCanvas.DrawBitmap(_bitmap, 0f, 0f);
		}
		return new Bitmap(bitmap);
	}

	/// <summary>
	/// Flips the bitmap horizontally.
	/// </summary>
	/// <returns>A new <see cref="T:Sandbox.Bitmap" /> instance with the flipped image.</returns>
	[Description("Flips the bitmap horizontally.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Transforms.cs", 76)]
	[return: Description("A new <span style=\"color: #4EC9B0;\">Bitmap</span> instance with the flipped image.")]
	public Bitmap FlipHorizontal()
	{
		SKBitmap bitmap = new SKBitmap(_bitmap.Width, _bitmap.Height, _bitmap.ColorType, _bitmap.AlphaType);
		using (SKCanvas sKCanvas = new SKCanvas(bitmap))
		{
			sKCanvas.Scale(-1f, 1f);
			sKCanvas.Translate(-_bitmap.Width, 0f);
			sKCanvas.DrawBitmap(_bitmap, 0f, 0f);
		}
		return new Bitmap(bitmap);
	}

	/// <summary>
	/// Crops the bitmap to the specified rectangle.
	/// </summary>
	/// <param name="rect">The rectangle to crop to.</param>
	/// <returns>A new <see cref="T:Sandbox.Bitmap" /> instance with the cropped image.</returns>
	[Description("Crops the bitmap to the specified rectangle.")]
	[SourceLocation("Resources\\Textures\\Bitmap\\Bitmap.Transforms.cs", 95)]
	[return: Description("A new <span style=\"color: #4EC9B0;\">Bitmap</span> instance with the cropped image.")]
	public Bitmap Crop([Description("The rectangle to crop to.")] Rect rect)
	{
		SKBitmap bitmap = new SKBitmap((int)rect.Width, (int)rect.Height, _bitmap.ColorType, _bitmap.AlphaType);
		using (SKCanvas sKCanvas = new SKCanvas(bitmap))
		{
			SKRect source = rect.ToSk();
			sKCanvas.DrawBitmap(dest: new SKRect(0f, 0f, rect.Width, rect.Height), bitmap: _bitmap, source: source);
		}
		return new Bitmap(bitmap);
	}
}
