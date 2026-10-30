// RODALISO_SHADER_VERSAO=3
// RodaLiso_CAS.fx - nitidez adaptativa ao contraste (algoritmo AMD FidelityFX CAS, licença MIT).
// Reescrito para o ReShade pelo projeto Roda Liso. Não precisa de outros arquivos.

uniform float Sharpening <
    ui_type = "slider";
    ui_label = "Nitidez";
    ui_min = 0.0; ui_max = 1.0;
> = 0.5;

uniform float Boost <
    ui_type = "slider";
    ui_label = "Reforço de detalhe";
    ui_tooltip = "Realce extra de micro-contraste (mais 'pop'). 0 = desligado.";
    ui_min = 0.0; ui_max = 2.0;
> = 0.0;

texture RL_BackBufferTex : COLOR;
sampler RL_BackBuffer { Texture = RL_BackBufferTex; };

float3 RL_Load(int2 p)
{
    p = clamp(p, int2(0, 0), int2(BUFFER_WIDTH - 1, BUFFER_HEIGHT - 1));
    return tex2Dfetch(RL_BackBuffer, p).rgb;
}

void RL_VS(in uint id : SV_VertexID, out float4 position : SV_Position, out float2 texcoord : TEXCOORD)
{
    texcoord.x = (id == 2) ? 2.0 : 0.0;
    texcoord.y = (id == 1) ? 2.0 : 0.0;
    position = float4(texcoord * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
}

float3 RL_PS(float4 vpos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    int2 p = int2(vpos.xy);
    //  a b c
    //  d e f
    //  g h i
    float3 a = RL_Load(p + int2(-1, -1));
    float3 b = RL_Load(p + int2( 0, -1));
    float3 c = RL_Load(p + int2( 1, -1));
    float3 d = RL_Load(p + int2(-1,  0));
    float3 e = RL_Load(p);
    float3 f = RL_Load(p + int2( 1,  0));
    float3 g = RL_Load(p + int2(-1,  1));
    float3 h = RL_Load(p + int2( 0,  1));
    float3 i = RL_Load(p + int2( 1,  1));

    // Mínimo e máximo suaves da vizinhança (cruz + cantos)
    float3 mn4 = min(min(b, d), min(e, min(f, h)));
    float3 mn  = mn4 + min(min(mn4, min(a, c)), min(g, i));
    float3 mx4 = max(max(b, d), max(e, max(f, h)));
    float3 mx  = mx4 + max(max(mx4, max(a, c)), max(g, i));

    // Quanto de nitidez cabe neste pixel sem estourar (áreas de alto contraste recebem menos)
    float3 amp = saturate(min(mn, 2.0 - mx) / max(mx, 0.0001));
    amp = sqrt(amp);

    // Filtro em cruz: 0 w 0 / w 1 w / 0 w 0
    float peak = -1.0 / lerp(8.0, 5.0, Sharpening);
    float3 w = amp * peak;
    float3 rcpW = 1.0 / (1.0 + 4.0 * w);
    float3 cas = saturate(((b + d + f + h) * w + e) * rcpW);

    // Reforço de detalhe: realça o que o pixel central tem de diferente da média da vizinhança (unsharp mask 3x3)
    float3 desfoque = (a + c + g + i + 2.0 * (b + d + f + h) + 4.0 * e) / 16.0;
    return saturate(cas + Boost * (e - desfoque));
}

technique RodaLiso_CAS
{
    pass
    {
        VertexShader = RL_VS;
        PixelShader = RL_PS;
    }
}
