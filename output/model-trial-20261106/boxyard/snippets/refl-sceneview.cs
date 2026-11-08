
var f = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.DeclaredOnly;
string Sig( System.Reflection.MemberInfo m ) => m.MemberType + " " + m.Name + ( m is System.Reflection.MethodBase mb ? "(" + string.Join( ",", mb.GetParameters().Select( p => p.ParameterType.Name + " " + p.Name ) ) + ")" : m is System.Reflection.PropertyInfo pi ? ":" + pi.PropertyType.Name : m is System.Reflection.FieldInfo fi ? ":" + fi.FieldType.Name : "" );
var all = AppDomain.CurrentDomain.GetAssemblies().SelectMany( a => { try { return a.GetTypes(); } catch { return new Type[0]; } } ).ToList();
var iface = all.First( t => t.FullName == "Editor.EditorEvent+ISceneView" );
var impl = all.Where( t => iface.IsAssignableFrom( t ) && t != iface ).Select( t => t.FullName ).ToList();
var ifaceMembers = iface.GetMembers( f ).Select( Sig ).ToList();
var cand = all.Where( t => t.FullName != null && ( t.FullName.Contains( "SceneViewWidget" ) || t.FullName.Contains( "SceneViewportWidget" ) || t.FullName.Contains( "EditorCamera" ) || t.FullName.Contains( "SceneViewCamera" ) || t.FullName.Contains( "ViewportCamera" ) ) ).Select( t => t.FullName ).Take( 30 ).ToList();
return new { impl, ifaceMembers, cand };
