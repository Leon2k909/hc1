HEADER
{
    Description = "Lowtide warehouse floor: scanned pine boards laid across the existing joists";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
    ToolsShadingComplexity( "tools_shading_complexity.shader" );
}
COMMON
{
    #include "common/shared.hlsl"
}
struct VertexInput
{
    #include "common/vertexinput.hlsl"
};
struct PixelInput
{
    #include "common/pixelinput.hlsl"
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    // This floor is opaque. Ordinary RGB mips also support the source scan's
    // non-power-of-two dimensions, which the alpha-weighted filter rejects.
    #define AlphaWeighted( color, opacity ) Box( color )
    #include "common/utils/Material.CommonInputs.hlsl"
    #undef AlphaWeighted
    #include "common/pixel.hlsl"
    #include "hc1_lowtide_floor_atlas.hlsl"
    float3 g_vFloorTint < Default3( .62, .60, .56 ); UiType( Color ); >;

    uint FloorHash( int row, int block, uint salt )
    {
        uint h = uint( row ) * 0x9e3779b9u ^ uint( block ) * 0x85ebca6bu ^ salt;
        h ^= h >> 16;
        h *= 0x7feb352du;
        h ^= h >> 15;
        h *= 0x846ca68bu;
        return h ^ ( h >> 16 );
    }

    float FloorGap( float distance, float footprint, float average )
    {
        float aa = max( footprint * .5, .0001 );
        float coverage = 1 - smoothstep( .00125 - aa, .00125 + aa, distance );
        // Once a board is unresolved, use area coverage rather than a flashing line.
        return lerp( average, coverage, 1 - smoothstep( .032, .127, footprint ) );
    }

    float FloorEdgeSlope( float distance, float footprint )
    {
        float t = saturate( ( distance - .00125 ) / .00175 );
        return .0005 * 6 * t * ( 1 - t ) / .00175 * saturate( .00175 / max( footprint, .0001 ) );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        Material material = Material::Init( input );
        #if !S_MODE_DEPTH
        // Engine X is north. Joists run east/west at n = 440 + 110*k inches.
        // The same layout is mirrored about the Fleet; no model UV rewrite is needed.
        float2 plane = float2( material.WorldPosition.x, abs( material.WorldPosition.y ) );
        float2 px = ddx( plane ), py = ddy( plane );
        float2 footprint = ( abs( px ) + abs( py ) ) * .0254;
        float across = ( plane.y - 260 ) / 10;
        int row = int( floor( across ) );
        float phase = float( FloorHash( row, 0, 107u ) % 3u );
        float q = ( plane.x - 440 ) / 110 + phase;
        int block = int( floor( q / 3 ) );
        float at = q - float( block ) * 3;
        float split = 1 + float( FloorHash( row, block, 701u ) & 1u );
        bool second = at >= split;
        float spans = second ? 3 - split : split;
        float along = ( at - ( second ? split : 0 ) ) / spans;
        uint variation = FloorHash( row, block * 2 + int( second ), 419u );
        uint choice = variation & 3u;
        // The longer scans have restrained grain; knotty scans go on short boards.
        uint scan = spans < 1.5 ? ( choice == 0 ? 0u : choice == 1 ? 3u : choice == 2 ? 5u : 7u )
                               : ( choice == 0 ? 1u : choice == 1 ? 2u : choice == 2 ? 4u : 6u );
        float2 direction = float2( ( variation & 16u ) != 0 ? -1 : 1,
                                   ( variation & 32u ) != 0 ? -1 : 1 );
        float2 local = float2( along, frac( across ) );
        float2 sampleLocal = .5 + ( local - .5 ) * direction;
        float4 rect = FloorAtlasRect( scan );
        float2 uv = rect.xy + sampleLocal * rect.zw;
        // Derivatives come from the continuous world coordinates before floor/frac.
        float2 derivativeScale = rect.zw * direction / float2( 110 * spans, 10 );
        float2 dx = px * derivativeScale, dy = py * derivativeScale;
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );

        float2 distance = min( local, 1 - local ) * float2( 2.794 * spans, .254 );
        float gapU = FloorGap( distance.x, footprint.x, .0025 / ( 2.794 * spans ) );
        float gapV = FloorGap( distance.y, footprint.y, .0025 / .254 );
        float gap = 1 - ( 1 - gapU ) * ( 1 - gapV );
        float side = material.WorldPosition.y < 0 ? -1 : 1;
        float3 scanned = DecodeNormal( normal.xyz );
        // Atlas V runs down the image; +Y in the OpenGL normal points up it.
        float3 surface = float3( scanned.x * direction.x, -scanned.y * direction.y * side, scanned.z );
        float2 slope = float2( FloorEdgeSlope( distance.x, footprint.x ), FloorEdgeSlope( distance.y, footprint.y ) );
        slope *= float2( local.x < .5 ? 1 : -1, ( local.y < .5 ? 1 : -1 ) * side );
        surface.xy -= slope;

        // Recessed square nail heads occur at the joists, not on an arbitrary tile grid.
        float nearJoist = abs( frac( ( plane.x - 440 ) / 110 + .5 ) - .5 ) * 2.794;
        float alongNail = abs( nearJoist - .018 );
        float acrossNail = min( abs( local.y * .254 - .045 ), abs( local.y * .254 - .209 ) );
        float nailAa = max( max( footprint.x, footprint.y ) * .5, .0001 );
        float nail = 1 - smoothstep( .0018 - nailAa, .0018 + nailAa, max( alongNail, acrossNail ) );
        nail *= 1 - smoothstep( .003, .012, max( footprint.x, footprint.y ) );
        float tone = .97 + float( ( variation >> 8 ) & 255u ) / 255 * .05;
        material.Albedo = color.rgb * g_vFloorTint * tone * g_flTintColor * input.vVertexColor.rgb;
        material.Albedo *= lerp( 1, .27, gap ) * lerp( 1, .30, nail );
        material.Normal = normalize( lerp( surface, float3( 0, 0, 1 ), nail * .65 ) );
        material.Roughness = lerp( lerp( rma.r, .96, gap ), .60, nail );
        material.AmbientOcclusion = lerp( rma.b, .86, gap );
        material.TintMask = normal.a;
        material.TextureCoords = uv;
        #endif
        material.Metalness = 0;
        material.Transmission = 0;
        material.Opacity = 1;
        return ShadingModelStandard::Shade( input, material );
    }
}
