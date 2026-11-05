using Facepunch.Gunsmith;
using System.Text;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
const int maximum = 16384;
var json = "{\"Version\":1,\"Weapon\":\"weapons/rifle.equip\",\"Attachments\":{\"Optic\":\"parts/reflex.gnsmth\"}}";
var payload = Convert.ToBase64String( Encoding.UTF8.GetBytes( json ) ).TrimEnd( '=' ).Replace( '+', '-' ).Replace( '/', '_' );
var code = "HC1W1-" + payload;
var wrapped = string.Join( "\r\n\t", code.Chunk( 9 ).Select( chunk => new string( chunk ) ) );
foreach ( var text in new[]
{
	code, "  " + code + "  ", "`" + code + "`", "\"" + code + "\"", "'" + code + "'",
	"```\n" + code + "\n```", "```text\n" + code + "\n```", "```txt\r\n" + code + "\r\n```",
	"```HC1\n" + code + "\n```", "```" + code + "```", wrapped,
	"```text\n" + wrapped + "\n```", code.Insert( 3, "\t\u00a0\n" ),
	code.Insert( 20, "\u200b\ufeff\u2060" )
} )
{
	Check( WeaponBuildCodeText.TryNormalize( text, maximum, out var normalized ) && normalized == code,
		"Copied formatting must restore the exact original build code, including payload casing." );
}
Check( WeaponBuildCodeText.TryNormalize( payload, maximum, out var bare ) && bare == payload,
	"Legacy codes without the HC1 prefix must remain supported." );
var standardBase64 = Convert.ToBase64String( Encoding.UTF8.GetBytes( json ) );
Check( WeaponBuildCodeText.TryNormalize( standardBase64, maximum, out var standard ) && standard == standardBase64,
	"Standard Base64 symbols and padding must remain supported." );

foreach ( var invalid in new[]
{
	null, "", "  \t\n", "``", "```", "``````", "`unclosed", "\"unclosed", "```\n" + code,
	code + "```", "Here is the code: " + code, code + ";command", code.Insert( 20, "\0" ),
	new string( 'A', maximum + 1 )
} )
	Check( !WeaponBuildCodeText.TryNormalize( invalid, maximum, out var rejected ) && rejected is null,
		"Malformed wrappers, prose, invalid characters and oversized inputs must be rejected." );

Check( WeaponBuildCodeText.TryNormalize( new string( 'A', maximum ), maximum, out var boundary ) && boundary.Length == maximum,
	"The documented input-size boundary must remain usable." );
Check( !WeaponBuildCodeText.TryNormalize( new string( ' ', maximum ) + code, maximum, out _ ),
	"Whitespace must not bypass the raw clipboard input-size limit." );

Console.WriteLine( $"PASS: {checks} shared-build clipboard checks against production WeaponBuildCodeText." );
