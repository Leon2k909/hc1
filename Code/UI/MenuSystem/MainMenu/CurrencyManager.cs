using Sandbox;

namespace Facepunch;

public static class CurrencyManager
{
    private const string CurrencyCookieKey = "hc1.currency";

    public static int GetBalance()
    {
        return Game.Cookies.Get<int>( CurrencyCookieKey, 0 );
    }

    public static void Add( int amount )
    {
        if ( amount <= 0 ) return;
        var current = GetBalance();
        Game.Cookies.Set( CurrencyCookieKey, current + amount );
    }

    public static bool Spend( int amount )
    {
        if ( amount <= 0 ) return true;
        var current = GetBalance();
        if ( current < amount ) return false;
        
        Game.Cookies.Set( CurrencyCookieKey, current - amount );
        return true;
    }
}
