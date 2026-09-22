using System;
using System.Reflection;
using Sandbox;

public class Test {
    public static void Run() {
        Console.WriteLine(""Checking Sandbox.Mouse properties:"");
        foreach(var prop in typeof(Sandbox.Mouse).GetProperties(BindingFlags.Static | BindingFlags.Public)) {
            Console.WriteLine(prop.Name);
        }
    }
}
