// Numerical architectural mask baked by Tools/lowtide_shed_weathering.py.
CreateInputTexture2D( TextureShedWear, Linear, 8, "", "_mask", "Weathering", Default3( 0, 0, 0 ) );
Texture2D g_tShedWear < Channel( RGB, Box( TextureShedWear ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
SamplerState ShedWearSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
float g_flShedWear < Default( 0 ); Range( 0, 1 ); >;

float3 ShedWear( float3 world, float3 normal )
{
    float n=world.x, e=-world.y, a=abs(e);
    if( world.z<0 || world.z>512 || abs(normal.z)>.3 ) return 0;
    float4 bounds;
    float row;
    if( a>1292 && a<1958 && n>-1058 && n<-592 )
    { bounds=float4(1300,1950,-1050,-600); row=0; }
    else if( a>292 && a<628 && n>-988 && n<-692 )
    { bounds=float4(300,620,-980,-700); row=2; }
    else return 0;
    float column=-1, along=0;
    if( abs(a-bounds.x)<8 && normal.y*sign(e)>.8 )
    { column=0; along=(n-bounds.z)/(bounds.w-bounds.z); }
    else if( abs(a-bounds.y)<8 && normal.y*sign(e)<-.8 )
    { column=1; along=(n-bounds.z)/(bounds.w-bounds.z); }
    else if( abs(n-bounds.z)<8 && normal.x<-.8 )
    { column=2; along=(a-bounds.x)/(bounds.y-bounds.x); }
    else if( abs(n-bounds.w)<8 && normal.x>.8 )
    { column=3; along=(a-bounds.x)/(bounds.y-bounds.x); }
    if( column<0 || along<0 || along>1 ) return 0;
    row += e<0 ? 1 : 0;
    float2 local=float2(along,1-world.z/512);
    float2 uv=(float2(column,row)+(8.5+local*495)/512)/4;
    return g_tShedWear.Sample(ShedWearSampler,uv).rgb;
}
