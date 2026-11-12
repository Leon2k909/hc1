using System.Text.Json;
using Sandbox.ContentBuild;

// Builds a project's content with the engine's own content builder and out-of-process contentworkers, a chunk of
// folders at a time, with fresh workers per chunk. Writes the same records the editor's startup build reads.
//
//   contentbuild <projectDir> [sboxDir] [--max-sources N] [--only <relative folder>]...

var argList = args.ToList();
string Take( string flag )
{
	var i = argList.IndexOf( flag );
	if ( i < 0 || i + 1 >= argList.Count ) return null;
	var v = argList[i + 1];
	argList.RemoveRange( i, 2 );
	return v;
}

var only = new List<string>();
while ( Take( "--only" ) is { } o ) only.Add( o );
var maxSources = int.Parse( Take( "--max-sources" ) ?? "2000" );

var projectDir = Path.GetFullPath( argList[0] );
var sboxDir = Path.GetFullPath( argList.Count > 1 ? argList[1] : @"C:\Program Files (x86)\Steam\steamapps\common\sbox" );

static string FullIdent( string sbproj )
{
	using var doc = JsonDocument.Parse( File.ReadAllText( sbproj ) );
	var org = doc.RootElement.TryGetProperty( "Org", out var o ) ? o.GetString() : "local";
	var ident = doc.RootElement.GetProperty( "Ident" ).GetString();
	return $"{org}.{ident}";
}

// Libraries with assets, then the project, as the editor mounts them
var projects = new List<(string Ident, string AssetsPath, string ProjectDirectory)>();
var libraries = Path.Combine( projectDir, "Libraries" );
if ( Directory.Exists( libraries ) )
{
	foreach ( var lib in Directory.GetDirectories( libraries ).OrderBy( x => x, StringComparer.OrdinalIgnoreCase ) )
	{
		var proj = Directory.GetFiles( lib, "*.sbproj" ).FirstOrDefault();
		var assets = Path.Combine( lib, "Assets" );
		if ( proj is not null && Directory.Exists( assets ) ) projects.Add( (FullIdent( proj ), assets, lib) );
	}
}
var mainProj = Directory.GetFiles( projectDir, "*.sbproj" ).First();
var projectAssets = Path.Combine( projectDir, "Assets" );
projects.Add( (FullIdent( mainProj ), projectAssets, projectDir) );

var roots = ContentRoots.WithProjects( [], projects );
var readOnly = ContentRoots.Engine( sboxDir )
	.Where( x => !roots.Any( r => string.Equals( r.Path, x.Path, StringComparison.OrdinalIgnoreCase ) ) )
	.Select( x => (x.Mod, x.Path) ).ToList();

foreach ( var r in roots ) Console.WriteLine( $"root {r.Mod}: {r.Path}" );

static bool IsSource( string f )
{
	var n = Path.GetFileName( f );
	return !n.EndsWith( "_c", StringComparison.OrdinalIgnoreCase ) && !n.EndsWith( ".meta", StringComparison.OrdinalIgnoreCase )
		&& !n.EndsWith( "_d", StringComparison.OrdinalIgnoreCase ) && !n.Contains( ".generated.", StringComparison.OrdinalIgnoreCase );
}

static int CountSources( string dir ) => Directory.EnumerateFiles( dir, "*", SearchOption.AllDirectories ).Count( IsSource );

// Units: folders small enough to build in one go (big ones split by subfolder) and a big folder's own files in
// batches. The engine's compilers break after a few thousand compiles in one process, so no chunk may exceed the cap.
var units = new List<(List<string> Paths, int Size)>();
void Split( string dir )
{
	var size = CountSources( dir );
	if ( size == 0 ) return;
	if ( size <= maxSources ) { units.Add( ([dir], size) ); return; }
	AddLoose( dir );
	foreach ( var sub in Directory.GetDirectories( dir ).OrderBy( x => x, StringComparer.OrdinalIgnoreCase ) ) Split( sub );
}

void AddLoose( string dir )
{
	var loose = Directory.GetFiles( dir ).Where( IsSource ).OrderBy( x => x, StringComparer.OrdinalIgnoreCase ).ToList();
	for ( var i = 0; i < loose.Count; i += maxSources )
	{
		var batch = loose.Skip( i ).Take( maxSources ).ToList();
		units.Add( (batch, batch.Count) );
	}
}

if ( only.Count > 0 )
{
	foreach ( var o in only ) Split( Path.GetFullPath( Path.Combine( projectAssets, o ) ) );
}
else
{
	foreach ( var r in roots.Where( r => r.Path != Path.GetFullPath( projectAssets ) ) ) Split( r.Path );
	AddLoose( projectAssets );
	foreach ( var sub in Directory.GetDirectories( projectAssets ).OrderBy( x => x, StringComparer.OrdinalIgnoreCase ) ) Split( sub );
}

// Neighbouring small units share a chunk (each chunk pays a worker start-up)
var chunks = new List<List<string>>();
var labels = new List<string>();
var current = new List<string>();
int currentSize = 0, currentUnits = 0;
string currentLabel = null;
void Flush()
{
	if ( current.Count == 0 ) return;
	chunks.Add( current );
	labels.Add( currentUnits > 1 ? $"{currentLabel} (+{currentUnits - 1} more)" : currentLabel );
	current = []; currentSize = 0; currentUnits = 0;
}
foreach ( var (paths, size) in units )
{
	if ( currentSize + size > maxSources ) Flush();
	if ( current.Count == 0 )
		currentLabel = paths.Count == 1 && Directory.Exists( paths[0] ) ? Path.GetRelativePath( projectDir, paths[0] ) : $"{paths.Count} files in {Path.GetRelativePath( projectDir, Path.GetDirectoryName( paths[0] ) )}";
	current.AddRange( paths ); currentSize += size; currentUnits++;
}
Flush();

Console.WriteLine( $"{chunks.Count} chunks, max {maxSources} source files each" );

var types = new AssetTypeTable( Path.Combine( sboxDir, "bin", "assettypes.txt" ) );
var logDir = Directory.CreateDirectory( Path.Combine( projectDir, ".sbox", "build", "contentbuild-logs" ) ).FullName;

int totalJobs = 0, totalFailed = 0, totalBlocked = 0;
for ( var c = 0; c < chunks.Count; c++ )
{
	var select = chunks[c];
	var label = labels[c];
	var done = 0;
	var request = new BuildRequest
	{
		Roots = roots,
		ReadOnlyMounts = readOnly,
		OutputRoots = new Dictionary<string, string> { ["transient"] = Path.Combine( projectDir, ".sbox", "transient" ) },
		OutputFallbacks = new Dictionary<string, string> { ["transient"] = Path.Combine( sboxDir, "addons", "menu", "Transients" ) },
		Select = select,
		MaxJobs = ResourceCompiler.DefaultMaxJobs,
		LockTimeout = TimeSpan.FromSeconds( 15 ),
		Waiting = root => Console.WriteLine( $"  waiting for another build of {root} (close the editor)" ),
		JobFinished = _ => { var n = Interlocked.Increment( ref done ); if ( n % 250 == 0 ) Console.WriteLine( $"  {n} jobs" ); },
	};

	// Fresh workers for every chunk
	var compiler = new ResourceCompiler( Path.Combine( sboxDir, "bin", "managed", "contentworker.exe" ), types, request.Mounts, null ) { RenderDevice = true };
	var started = DateTime.Now;
	Console.WriteLine( $"[{c + 1}/{chunks.Count}] {label}" );
	BuildReport report;
	try { report = await ContentBuilder.BuildAsync( request, compiler ); }
	finally { compiler.Finished(); }

	totalJobs += report.Jobs.Count; totalFailed += report.Failed.Count; totalBlocked += report.Blocked.Count;
	Console.WriteLine( $"  {report.Jobs.Count} compiles, {report.Failed.Count} failed, {report.Blocked.Count} blocked, {report.Adopted.Count} adopted, {report.Unsupported.Count} unsupported, {(DateTime.Now - started).TotalSeconds:F0}s, workers {compiler.Launches}" );
	if ( report.Error is not null ) { Console.WriteLine( $"  ERROR: {report.Error}" ); return 1; }
	if ( report.Failed.Count > 0 || report.Blocked.Count > 0 ) File.WriteAllText( Path.Combine( logDir, $"chunk-{c + 1:0000}.log" ), $"{label}\n{report.Log}" );
}

Console.WriteLine( $"done: {totalJobs} compiles, {totalFailed} failed, {totalBlocked} blocked; failure logs in {logDir}" );
return 0;
