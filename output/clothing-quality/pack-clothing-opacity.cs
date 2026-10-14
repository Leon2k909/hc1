// Package the generated RGB with the engine garment's exact UV opacity contract.
// The generated RGBA asset remains unchanged as the art source.
var original = Material.Load("models/citizen_clothes/gloves/fingerless_gloves/textures/fingerless_gloves.vmat").GetTexture("g_tColor");
var generated = Texture.Load("materials/operators/first_person/fp_fingerless_gloves_color.png");
using var originalBitmap = original.GetBitmap(0);
using var mask = originalBitmap.Resize(generated.Width,generated.Height,true);
using var generatedBitmap = generated.GetBitmap(0);
var originalPixels = mask.GetPixels32();
var generatedPixels = generatedBitmap.GetPixels32();
var data = new byte[generated.Width*generated.Height*4];
for(int p=0,j=0;p<generatedPixels.Length;p++,j+=4)
{
    var art=generatedPixels[p]; var source=originalPixels[p];
    var amount=art.a/255f;
    data[j]=(byte)(art.r*amount+source.r*(1f-amount)+.5f);
    data[j+1]=(byte)(art.g*amount+source.g*(1f-amount)+.5f);
    data[j+2]=(byte)(art.b*amount+source.b*(1f-amount)+.5f);
    data[j+3]=source.a;
}
using var packed = new Bitmap(generated.Width,generated.Height);
for(int y=0;y<generated.Height;y++)
{
    cancellationToken.ThrowIfCancellationRequested();
    for(int x=0;x<generated.Width;x++)
    {
        int j=(y*generated.Width+x)*4;
        packed.SetPixel(x,y,new Color(data[j]/255f,data[j+1]/255f,data[j+2]/255f,data[j+3]/255f));
    }
}
var destination = @"D:\Documents\s&box projects\hc1\forked-shooter-main\Assets\materials\operators\first_person\fp_fingerless_gloves_albedo.png";
if(System.IO.File.Exists(destination)) throw new Exception("Packed output already exists.");
System.IO.File.WriteAllBytes(destination,packed.ToPng());
Editor.AssetSystem.RegisterFile(destination);
return new { Path=destination, Width=packed.Width, Height=packed.Height, AlphaSourceWidth=original.Width };
