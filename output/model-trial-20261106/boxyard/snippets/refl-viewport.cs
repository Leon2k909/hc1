
var f = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.DeclaredOnly;
string Sig( System.Reflection.MemberInfo m ) => m.MemberType + " " + ( m is System.Reflection.MethodBase mb && mb.IsStatic ? "static " : m is System.Reflection.PropertyInfo p0 && ( p0.GetMethod?.IsStatic ?? false ) ? "static " : m is System.Reflection.FieldInfo f0 && f0.IsStatic ? "static " : "" ) + m.Name + ( m is System.Reflection.MethodBase mb2 ? "(" + string.Join( ",", mb2.GetParameters().Select( p => p.ParameterType.Name + " " + p.Name ) ) + ")" : m is System.Reflection.PropertyInfo pi ? ":" + pi.PropertyType.Name : m is System.Reflection.FieldInfo fi ? ":" + fi.FieldType.Name : "" );
var all = AppDomain.CurrentDomain.GetAssemblies().SelectMany( a => { try { return a.GetTypes(); } catch { return new Type[0]; } } ).ToList();
object Dump( string name ) {
    var t = all.First( x => x.FullName == name );
    return t.GetMembers( f ).Where( m => !m.Name.StartsWith( "<" ) && !m.Name.StartsWith( "get_" ) && !m.Name.StartsWith( "set_" ) && !m.Name.StartsWith( "add_" ) && !m.Name.StartsWith( "remove_" ) ).Select( Sig ).ToList();
}
return new { SceneViewWidget = Dump( "Editor.SceneViewWidget" ), Viewport = Dump( "Editor.SceneViewportWidget" ), State = Dump( "Editor.SceneViewportWidget+ViewportState" ) };
