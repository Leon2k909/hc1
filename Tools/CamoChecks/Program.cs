using Facepunch.Gunsmith;
using System.Text.RegularExpressions;
using Surface = Facepunch.Gunsmith.CamoMaterialRules.Surface;

var checks = 0;
void Check( bool passed, string reason )
{
	checks++;
	if ( !passed ) throw new Exception( reason );
}

var cases = new (string Material, string Shader, bool Optic, bool Transparent, Surface Expected)[]
{
	("attachments/swb/sight/reflex/textures/reflex_dot_shader.vmat", "shaders/swb_sam_red_dot.shader", true, false, Surface.Reticle),
	("reflex_dot_shader_scarh.vmat", "shaders/swb_sam_red_dot.shader", true, false, Surface.Reticle),
	("reflex_dot_shader_remington.vmat", "shaders/swb_sam_red_dot.shader", true, false, Surface.Reticle),
	("attachments/swb/sight/scope_hunter/textures/scope.vmat", "shaders/swb_render_scope.shader", true, false, Surface.Lens),
	("weapons/m700/3d_scope.vmat", "shaders/3dscope.shader", false, false, Surface.Lens),
	("weapons/m700/scope.vmat", "shaders/scope.shader", false, false, Surface.Lens),
	("generated/m_123.vmat", "shaders/m4_optic_lens.shader", true, false, Surface.Reticle),
	("generated/m_124.vmat", "shaders/swb_render_scope.shader", true, false, Surface.Lens),
	("ATTACHMENTS\\SIGHT\\GLASS.VMAT_C", "SHADERS\\COMPLEX.VFX_C", true, false, Surface.Lens),
	("ATTACHMENTS\\M_125.VMAT_C", "SHADERS\\M4_OPTIC_LENS.VFX_C", true, false, Surface.Reticle),
	("v_rmr_red_dot.vmat", "complex", true, false, Surface.Reticle),
	("v_holo_hologram.vmat", "complex", true, false, Surface.Reticle),
	("scope_crosshair.vmat", "complex", false, false, Surface.Reticle),
	("att_vm_scope_mike14_baffle.vmat", "shaders/complex.shader", true, false, Surface.Mask),
	("scout_lens_baffle.vmat", "shaders/complex.shader", true, false, Surface.Mask),
	("reticle_ui_stencil.vmat", "shaders/complex.shader", true, true, Surface.Mask),
	("reticle_ui_stencil_no_weap_cull.vmat", "shaders/complex.shader", true, true, Surface.Mask),
	("stencil_outline.vmat", "shaders/complex.shader", true, true, Surface.Mask),
	("vm_depth_mask_start.vmat", "shaders/complex.shader", true, true, Surface.Mask),
	("vm_depth_mask_end.vmat", "shaders/complex.shader", true, true, Surface.Mask),
	("hidden.vmat", "shaders/complex.shader", false, true, Surface.Mask),
	("materials/black_matte.vmat", "shaders/complex.shader", true, false, Surface.Mask),
	("imported/anonymous.vmat", "shaders/complex.shader", true, true, Surface.Lens),
	// Folder names describe the attachment, not the surface: each of these is an exterior housing.
	("attachments/reddot_rmr/v_rmr.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("attachments/swb/sight/reflex/textures/reflex.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("attachments/swb/sight/scope_hunter/textures/hunter.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("attachments/m4a1/optics/reflex_housing.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("attachment_vm_4x_west_body.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("weapon_vm_sn_mike14_scope_alt.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("red_dot_housing.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("materials/reticle/body.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("weapons/swb/l96a1/textures/v_l96a1_scope.vmat", "shaders/complex.shader", true, false, Surface.Paintable),
	("materials/black_matte.vmat", "shaders/complex.shader", false, false, Surface.Paintable),
	("weapons/receiver.vmat", "shaders/complex.shader", false, false, Surface.Paintable),
	("weapons/magazine.vmat", "shaders/complex.shader", false, true, Surface.Paintable),
};
foreach ( var c in cases )
{
	var result = CamoMaterialRules.Classify( c.Material, c.Shader, c.Optic, c.Transparent );
	Check( result == c.Expected, $"{c.Material}: expected {c.Expected}, got {result}" );
}

var project = Path.GetFullPath( args.FirstOrDefault() ?? "." );
var assets = Path.Combine( project, "Assets" );
var shaderPattern = new Regex( "\"?shader\"?\\s+\"([^\"]+)\"", RegexOptions.IgnoreCase );
string Shader( string text ) => shaderPattern.Match( text ).Groups[1].Value;
bool Feature( string text, string name ) => Regex.IsMatch( text, $"\"?{name}\"?\\s+\"?1\"?", RegexOptions.IgnoreCase );

// Asset fixtures, not just inferred names: these are the materials that the models really bind to the view surface.
var fixtures = new (string Path, Surface Expected)[]
{
	("attachments/swb/sight/reflex/textures/reflex_dot_shader.vmat", Surface.Reticle),
	("attachments/swb/sight/reflex/textures/reflex_dot_shader_remington.vmat", Surface.Reticle),
	("attachments/swb/sight/reflex/textures/reflex_dot_shader_scarh.vmat", Surface.Reticle),
	("attachments/swb/sight/scope_hunter/textures/scope.vmat", Surface.Lens),
	("Weapons/M700/3d_scope.vmat", Surface.Lens),
	("Weapons/M700/scope.vmat", Surface.Lens),
	("attachments/m4a1/optics/reflex_reticle.vmat", Surface.Reticle),
	("attachments/m4a1/optics/scout_reticle.vmat", Surface.Reticle),
	("attachments/m4a1/optics/scout_lens_baffle.vmat", Surface.Mask),
	("attachments/mw2022/models/att_vm_scope_mike14/att_vm_scope_mike14_baffle.vmat", Surface.Mask),
	("attachments/mw2022/materials/viper/mw/attachments/vm_depth_mask_start.vmat", Surface.Mask),
	("attachments/mw2022/materials/viper/mw/attachments/vm_depth_mask_end.vmat", Surface.Mask),
	("attachments/mw2022/materials/viper/mw/attachments/stencil_outline.vmat", Surface.Mask),
	("attachments/mw2022/materials/viper/mw/attachments/reticle_ui_stencil.vmat", Surface.Mask),
	("attachments/mw2022/materials/reticle_ui_stencil_no_weap_cull.vmat", Surface.Mask),
	("attachments/mw2022/materials/viper/mw/attachments/attachment_vm_holo_west_lens.vmat", Surface.Lens),
	("attachments/mw2022/models/att_vm_holo_west01/att_vm_holo_west01_reticle.vmat", Surface.Reticle),
	("attachments/m4a1/optics/scout_housing.vmat", Surface.Paintable),
	("attachments/m4a1/optics/reflex_housing.vmat", Surface.Paintable),
	("attachments/swb/sight/reflex/textures/reflex.vmat", Surface.Paintable),
	("attachments/swb/sight/scope_hunter/textures/hunter.vmat", Surface.Paintable),
	("attachments/mw2022/materials/viper/mw/attachments/attachment_vm_4x_west_body.vmat", Surface.Paintable),
	("attachments/mw2022/materials/viper/mw/attachments/weapon_vm_sn_mike14_scope_alt.vmat", Surface.Paintable),
};
foreach ( var fixture in fixtures )
{
	var text = File.ReadAllText( Path.Combine( assets, fixture.Path ) );
	var result = CamoMaterialRules.Classify( fixture.Path, Shader( text ), true,
		Feature( text, "F_TRANSLUCENT" ) || Feature( text, "F_ALPHA_TEST" ) );
	Check( result == fixture.Expected, $"Actual asset {fixture.Path}: expected {fixture.Expected}, got {result}" );
}

// Cover every optical shader, lens and mask in the weapon/attachment assets, and print the legacy misses.
var protectedCount = 0;
var oldMisses = new List<string>();
var opticalShaders = new HashSet<string>( StringComparer.OrdinalIgnoreCase )
{
	"shaders/m4_optic_lens.shader", "shaders/swb_sam_red_dot.shader", "shaders/swb_render_scope.shader",
	"shaders/scope.shader", "shaders/3dscope.shader",
};
foreach ( var directory in new[] { "attachments", "Weapons" } )
foreach ( var material in Directory.EnumerateFiles( Path.Combine( assets, directory ), "*.vmat", SearchOption.AllDirectories ) )
{
	var text = File.ReadAllText( material );
	var name = Path.GetFileName( material ).ToLowerInvariant();
	var isOptical = opticalShaders.Contains( Shader( text ) ) || name.Contains( "lens" ) || name.Contains( "glass" )
		|| name.Contains( "baffle" ) || name.Contains( "stencil" ) || name.Contains( "depth_mask" );
	if ( !isOptical ) continue;
	var result = CamoMaterialRules.Classify( material, Shader( text ), true,
		Feature( text, "F_TRANSLUCENT" ) || Feature( text, "F_ALPHA_TEST" ) );
	Check( result != Surface.Paintable, $"Optical asset is camo eligible: {material}" );
	protectedCount++;
	var previouslyProtected = name.Contains( "lens" ) || name.Contains( "glass" ) || name.Contains( "reticle" )
		|| name.Contains( "hologram" ) || name.Contains( "_dot." ) || name.Contains( "_reddot." )
		|| name.StartsWith( "dot." ) || name.StartsWith( "red_dot." );
	if ( !previouslyProtected ) oldMisses.Add( Path.GetRelativePath( project, material ).Replace( '\\', '/' ) );
}
Check( protectedCount >= 70, "The complete weapon/attachment optical asset inventory was audited" );
Console.WriteLine( $"PASS: {checks} checks; {protectedCount} optical materials protected; {oldMisses.Count} previously missed surfaces." );
foreach ( var miss in oldMisses ) Console.WriteLine( $"  Fixed: {miss}" );
