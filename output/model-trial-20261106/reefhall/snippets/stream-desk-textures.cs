var s = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( s == null ) return "reefhall is not open";
var names = new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "g_tMetalness", "g_tTintMask", "g_tSelfIllumMask" };
var renderers = s.Scene.GetAllComponents<ModelRenderer>().Where( r => r.Model != null && r.Model.ResourcePath == "models/props/reefhall/reception_desk_v1/reception_desk.vmdl" ).ToArray();
var textures = renderers.SelectMany( r => r.Model.Materials ).SelectMany( m => names.Select( n => m.GetTexture( n ) ).Append( m.FirstTexture ) ).Where( t => t != null ).Distinct().ToArray();
foreach ( var t in textures ) t.MarkUsed( 2048 );
return new { Renderers = renderers.Length, Textures = textures.Length, Sizes = textures.Select( t => t.Width + "x" + t.Height ).Distinct().ToArray() };
