HEADER
{
    Description = "Cerro Blanco honed stone: independently cut slabs, fine joints and close-range relief";
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
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    CreateInputTexture2D( TextureHeight, Linear, 8, "", "_height", "Stone", Default( 1 ) );
    Texture2D g_tHeight < Channel( R, Box( TextureHeight ), Linear ); OutputFormat( ATI1N ); SrgbRead( false ); >;
    float g_flTilesPerUv < Default( 8 ); UiGroup( "Stone" ); >;
    float g_flSlabSize < Default( 30 ); UiGroup( "Stone" ); >;
    float g_flHasJoints < Default( 1 ); UiGroup( "Stone" ); >;
    float g_flStoneScale < Default( .39 ); UiGroup( "Stone" ); >;
    float g_flJointWidth < Default( .16 ); UiGroup( "Stone" ); >;
    float g_flBevelWidth < Default( .12 ); UiGroup( "Stone" ); >;
    float g_flReliefDepth < Default( .14 ); UiGroup( "Stone" ); >;
    float g_flNormalStrength < Default( .55 ); UiGroup( "Stone" ); >;
    float g_flStoneRoughness < Default( .65 ); UiGroup( "Stone" ); >;
    float3 g_vStoneTint < Default3( 1, 1, 1 ); UiGroup( "Stone" ); >;
    // How much each slab's stone differs from the next (a share of its brightness either way), and the share of slabs cut
    // from a denser, warmer bed of the block.
    float g_flSlabVariation < Default( .033 ); UiGroup( "Stone" ); >;
    float g_flOddSlabs < Default( 0 ); UiGroup( "Stone" ); >;

    float StoneHash( float2 p ) { return frac( sin( dot( p, float2( 127.1, 311.7 ) ) ) * 43758.5453 ); }
    float StoneNoise( float2 p )
    {
        float2 i = floor( p ), f = frac( p );
        float2 u = f * f * ( 3 - 2 * f );
        return lerp( lerp( StoneHash( i ), StoneHash( i + float2( 1, 0 ) ), u.x ),
                     lerp( StoneHash( i + float2( 0, 1 ) ), StoneHash( i + 1 ), u.x ), u.y );
    }
    float2 RotateStone( float2 p, float turn )
    {
        if (turn < 1) return p;
        if (turn < 2) return float2( -p.y, p.x );
        if (turn < 3) return -p;
        return float2( p.y, -p.x );
    }
    float2 StoneUv( float2 grid, out float turn, out float variation )
    {
        float2 cell = floor( grid );
        turn = floor( StoneHash( cell + 5.3 ) * 4 );
        variation = StoneHash( cell + 19.7 );
        float2 offset = float2( StoneHash( cell + 43.1 ), StoneHash( cell + 91.7 ) );
        if (g_flHasJoints < .5) { turn = 0; variation = .5; return grid * g_flStoneScale; }
        return RotateStone( frac( grid ) - .5, turn ) * g_flStoneScale + offset;
    }
    float EdgeDistance( float2 grid )
    {
        float2 local = frac( grid );
        float2 edge = min( local, 1-local ) * g_flSlabSize;
        return min( edge.x, edge.y );
    }
    float StoneDepth( float2 grid, float2 dx, float2 dy )
    {
        float turn, variation;
        float2 uv = StoneUv( grid, turn, variation );
        float height = g_tHeight.SampleGrad( TextureFiltering, uv,
            RotateStone(dx,turn)*g_flStoneScale, RotateStone(dy,turn)*g_flStoneScale ).r;
        float edge = EdgeDistance( grid );
        float interior = smoothstep( g_flJointWidth*.5, g_flJointWidth*.5+g_flBevelWidth, edge );
        return 1 - lerp( height, height * interior, g_flHasJoints );
    }
    float2 StoneRelief( float2 grid, float2 dx, float2 dy, float2 ray, float facing )
    {
        int steps = (int)lerp( 20.0, 8.0, saturate( facing ) );
        float layer = 1.0 / steps;
        float2 delta = ray * layer;
        float2 at = grid;
        float depth = 0, surface = StoneDepth( at,dx,dy ), previous = surface;
        [loop] for(int k=0;k<steps && depth<surface;k++)
        {
            previous = surface-depth;
            at -= delta;
            depth += layer;
            surface = StoneDepth(at,dx,dy);
        }
        float after = surface-depth;
        float weight = saturate(after/min(after-previous,-.00001));
        return lerp(at,at+delta,weight);
    }
    float4 MainPs( PixelInput input ) : SV_Target0
    {
        Material material = Material::Init( input );
        #if !S_MODE_DEPTH
        float2 grid = input.vTextureCoords.xy * g_flTilesPerUv;
        float2 dx = ddx(grid), dy = ddy(grid);
        float3 n = normalize(input.vNormalWs);
        float3 toCamera = g_vCameraPositionWs-material.WorldPosition;
        float distance = length(toCamera);
        float3 view = toCamera/max(distance,.001);
        float facing = dot(view,n);
        float fade = 1-smoothstep(280,850,distance);
        float3 px = ddx(material.WorldPosition), py = ddy(material.WorldPosition);
        float3 a = cross(py,n), b = cross(n,px);
        float determinant = dot(px,a);
        [branch] if(fade>.001 && g_flReliefDepth>0 && facing>.01 && abs(determinant)>1e-10)
        {
            float3 gu = (dx.x*a+dy.x*b)/determinant;
            float3 gv = (dx.y*a+dy.y*b)/determinant;
            float2 ray = float2(dot(view,gu),dot(view,gv))*g_flReliefDepth*fade/max(facing,.18);
            float resolved = smoothstep(.35,1.2,length(ray/max(abs(dx)+abs(dy),.00001)));
            [branch] if(resolved>.001) grid=StoneRelief(grid,dx,dy,ray*resolved,facing);
        }
        float turn,variation;
        float2 uv = StoneUv(grid,turn,variation);
        float2 sx=RotateStone(dx,turn)*g_flStoneScale, sy=RotateStone(dy,turn)*g_flStoneScale;
        float3 color = g_tColor.SampleGrad(TextureFiltering,uv,sx,sy).rgb;
        float4 normal = g_tNormal.SampleGrad(TextureFiltering,uv,sx,sy);
        float4 rma = g_tRma.SampleGrad(TextureFiltering,uv,sx,sy);
        float edge = EdgeDistance(grid);
        float2 local0 = frac(grid);
        float aa = max(length(float2(length(dx),length(dy)))*g_flSlabSize*.35,.008);
        // The joint box-filtered over the pixel's footprint across it, as the panels' are: from afar, where the joint is
        // narrower than a pixel, it darkens the pixel only by the share it covers, a fine grid rather than dotted lines
        // of grout.
        float2 edgeInches = min( local0, 1 - local0 ) * g_flSlabSize;
        float2 footprint = max( float2( length( float2( dx.x, dy.x ) ), length( float2( dx.y, dy.y ) ) ) * g_flSlabSize, .004 );
        float halfJoint = g_flJointWidth * .5;
        float2 cover = saturate( ( min( edgeInches + footprint * .5, halfJoint ) - max( edgeInches - footprint * .5, -halfJoint ) ) / footprint );
        float joint = ( 1 - ( 1 - cover.x ) * ( 1 - cover.y ) ) * g_flHasJoints;
        float bevel = saturate((edge-g_flJointWidth*.5)/max(g_flBevelWidth,.001));
        float slope = 6*bevel*(1-bevel)*g_flReliefDepth/max(g_flBevelWidth,.001)*g_flHasJoints;
        // An analytic bevel cannot rely on texture mipmaps. Attenuate its
        // normal once the bevel is smaller than the projected pixel footprint.
        slope *= saturate(g_flBevelWidth/max(aa*2,.001));
        float2 local = local0, nearest = min(local,1-local);
        float2 gradient = nearest.x<nearest.y ? float2(local.x<.5?1:-1,0) : float2(0,local.y<.5?1:-1);
        float3 tangentNormal = DecodeNormal(normal.xyz);
        tangentNormal.xy = RotateStone(tangentNormal.xy, fmod(4-turn,4))*g_flNormalStrength;
        tangentNormal.xy -= gradient*slope;
        tangentNormal = normalize(tangentNormal);
        // Broad, slow differences over the field, in world space (a sine here banded it).
        float2 wp = material.WorldPosition.xy;
        float broad = StoneNoise( wp / 610 ) * .65 + StoneNoise( wp / 233 + 17.3 ) * .35;
        color *= lerp( 1 - g_flSlabVariation, 1 + g_flSlabVariation, variation ) * lerp( .976, 1.012, broad );
        // A few slabs from a denser, warmer bed.
        float odd = step( StoneHash( floor( grid ) + 71.9 ), g_flOddSlabs ) * g_flHasJoints;
        color = lerp( color, color * float3( .9, .86, .8 ), odd );
        float3 grout = float3(.315,.286,.239);
        float3 albedo = lerp(color*g_vStoneTint,grout,joint);
        material.Albedo = albedo*g_flTintColor*input.vVertexColor.rgb;
        material.Normal = TransformNormal(tangentNormal,input.vNormalWs,input.vTangentUWs,input.vTangentVWs);
        material.Roughness = lerp(clamp(g_flStoneRoughness+(rma.r-.65)*.55,.35,.9),.91,joint);
        // The joint's occlusion by its share of the reflected light, not its area: the albedo already darkens a
        // part-covered pixel by its share (as in the panel shader).
        float3 luma = float3( .2126, .7152, .0722 );
        float occluded = joint * dot( grout, luma ) / max( dot( albedo, luma ), .001 );
        material.AmbientOcclusion = lerp(rma.b,.72,occluded);
        material.TintMask = normal.a;
        material.TextureCoords = uv;
        #endif
        material.Metalness = 0;
        material.Transmission = 0;
        material.Opacity = 1;
        return ShadingModelStandard::Shade(input,material);
    }
}
