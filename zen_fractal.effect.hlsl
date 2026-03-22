// Zen Fractal Shader for OBS Shadertastic
// Procedural animated Julia/Mandelbrot fractal
//
// Install: Copy to obs-shadertastic/effects/
// Usage: Add as filter on a Color Source in OBS

// ─── Parameters ─────────────────────────────────────────────

uniform float speed <
    string label = "Animation Speed";
    string widget_type = "slider";
    float minimum = 0.0;
    float maximum = 2.0;
    float step = 0.01;
> = 0.3;

uniform float zoom <
    string label = "Zoom Level";
    string widget_type = "slider";
    float minimum = 0.5;
    float maximum = 10.0;
    float step = 0.1;
> = 1.0;

uniform float color_shift <
    string label = "Color Shift";
    string widget_type = "slider";
    float minimum = 0.0;
    float maximum = 1.0;
    float step = 0.01;
> = 0.0;

uniform float complexity <
    string label = "Complexity";
    string widget_type = "slider";
    float minimum = 0.1;
    float maximum = 1.0;
    float step = 0.01;
> = 0.7;

uniform int fractal_type <
    string label = "Fractal Type";
    string widget_type = "combo";
    string options = "Julia|Mandelbrot|Plasma";
> = 0;

uniform int palette <
    string label = "Color Palette";
    string widget_type = "combo";
    string options = "Zen|Aurora|Ember|Ocean";
> = 0;

// ─── Color Palettes ─────────────────────────────────────────

float3 palette_zen(float t) {
    float3 c0 = float3(0.06, 0.10, 0.18);
    float3 c1 = float3(0.12, 0.24, 0.35);
    float3 c2 = float3(0.24, 0.47, 0.55);
    float3 c3 = float3(0.39, 0.67, 0.63);
    float3 c4 = float3(0.59, 0.78, 0.71);
    float3 c5 = float3(0.78, 0.86, 0.78);
    float3 c6 = float3(0.94, 0.94, 0.90);
    
    if (t < 0.166) return lerp(c0, c1, t * 6.0);
    if (t < 0.333) return lerp(c1, c2, (t - 0.166) * 6.0);
    if (t < 0.5)   return lerp(c2, c3, (t - 0.333) * 6.0);
    if (t < 0.666) return lerp(c3, c4, (t - 0.5) * 6.0);
    if (t < 0.833) return lerp(c4, c5, (t - 0.666) * 6.0);
    return lerp(c5, c6, (t - 0.833) * 6.0);
}

float3 palette_aurora(float t) {
    float3 c0 = float3(0.04, 0.02, 0.12);
    float3 c1 = float3(0.16, 0.04, 0.31);
    float3 c2 = float3(0.31, 0.08, 0.47);
    float3 c3 = float3(0.47, 0.20, 0.59);
    float3 c4 = float3(0.24, 0.47, 0.71);
    float3 c5 = float3(0.16, 0.71, 0.59);
    float3 c6 = float3(0.39, 0.86, 0.39);
    float3 c7 = float3(0.78, 0.94, 0.59);
    
    float idx = t * 7.0;
    int i = int(idx);
    float f = frac(idx);
    if (i == 0) return lerp(c0, c1, f);
    if (i == 1) return lerp(c1, c2, f);
    if (i == 2) return lerp(c2, c3, f);
    if (i == 3) return lerp(c3, c4, f);
    if (i == 4) return lerp(c4, c5, f);
    if (i == 5) return lerp(c5, c6, f);
    return lerp(c6, c7, f);
}

float3 palette_ember(float t) {
    float3 c0 = float3(0.08, 0.02, 0.02);
    float3 c1 = float3(0.24, 0.06, 0.04);
    float3 c2 = float3(0.47, 0.12, 0.06);
    float3 c3 = float3(0.71, 0.24, 0.08);
    float3 c4 = float3(0.86, 0.47, 0.12);
    float3 c5 = float3(0.94, 0.71, 0.24);
    float3 c6 = float3(0.98, 0.86, 0.47);
    
    if (t < 0.166) return lerp(c0, c1, t * 6.0);
    if (t < 0.333) return lerp(c1, c2, (t - 0.166) * 6.0);
    if (t < 0.5)   return lerp(c2, c3, (t - 0.333) * 6.0);
    if (t < 0.666) return lerp(c3, c4, (t - 0.5) * 6.0);
    if (t < 0.833) return lerp(c4, c5, (t - 0.666) * 6.0);
    return lerp(c5, c6, (t - 0.833) * 6.0);
}

float3 palette_ocean(float t) {
    float3 c0 = float3(0.02, 0.04, 0.12);
    float3 c1 = float3(0.04, 0.12, 0.27);
    float3 c2 = float3(0.08, 0.24, 0.47);
    float3 c3 = float3(0.16, 0.39, 0.63);
    float3 c4 = float3(0.24, 0.59, 0.75);
    float3 c5 = float3(0.39, 0.75, 0.82);
    float3 c6 = float3(0.63, 0.86, 0.92);
    float3 c7 = float3(0.86, 0.94, 0.98);
    
    float idx = t * 7.0;
    int i = int(idx);
    float f = frac(idx);
    if (i == 0) return lerp(c0, c1, f);
    if (i == 1) return lerp(c1, c2, f);
    if (i == 2) return lerp(c2, c3, f);
    if (i == 3) return lerp(c3, c4, f);
    if (i == 4) return lerp(c4, c5, f);
    if (i == 5) return lerp(c5, c6, f);
    return lerp(c6, c7, f);
}

float3 get_color(float t) {
    t = frac(t + color_shift);
    if (palette == 0) return palette_zen(t);
    if (palette == 1) return palette_aurora(t);
    if (palette == 2) return palette_ember(t);
    return palette_ocean(t);
}

// ─── Fractal Computation ────────────────────────────────────

float julia(float2 uv, float time) {
    float angle = time * speed * 0.5;
    float r = 0.7885 * (1.0 + 0.5 * cos(5.0 * angle));
    float2 c = float2(r * cos(angle), r * sin(angle));
    
    float2 z = uv / zoom;
    int max_iter = int(50.0 + complexity * 150.0);
    
    for (int i = 0; i < 200; i++) {
        if (i >= max_iter) break;
        if (dot(z, z) > 4.0) {
            float log_zn = log(dot(z, z)) / 2.0;
            float nu = log(log_zn / log(2.0)) / log(2.0);
            return (float(i) + 1.0 - nu) / float(max_iter);
        }
        z = float2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
    }
    return 0.0;
}

float mandelbrot(float2 uv, float time) {
    float2 center = float2(-0.75 + 0.1 * sin(time * speed * 0.1),
                            0.1 * cos(time * speed * 0.07));
    float2 z = float2(0.0, 0.0);
    float2 c = uv / zoom + center;
    int max_iter = int(50.0 + complexity * 150.0);
    
    for (int i = 0; i < 200; i++) {
        if (i >= max_iter) break;
        if (dot(z, z) > 4.0) {
            float log_zn = log(dot(z, z)) / 2.0;
            float nu = log(log_zn / log(2.0)) / log(2.0);
            return (float(i) + 1.0 - nu) / float(max_iter);
        }
        z = float2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
    }
    return 0.0;
}

float plasma(float2 uv, float time) {
    float t = time * speed;
    float x = uv.x;
    float y = uv.y;
    
    float v1 = sin(x * 10.0 + t);
    float v2 = sin(10.0 * (x * sin(t / 2.0) + y * cos(t / 3.0)) + t);
    float cx = x + 0.5 * sin(t / 5.0);
    float cy = y + 0.5 * cos(t / 3.0);
    float v3 = sin(sqrt(100.0 * (cx * cx + cy * cy) + 1.0) + t);
    float v4 = sin(sqrt(100.0 * ((x - 0.5) * (x - 0.5) + (y - 0.5) * (y - 0.5)) + 1.0) - t);
    
    return (v1 + v2 + v3 + v4) * 0.25 * 0.5 + 0.5;
}

// ─── Main ───────────────────────────────────────────────────

float4 main_image(float2 uv, float2 resolution, float time) : COLOR {
    // Center UV around origin, aspect-corrected
    float aspect = resolution.x / resolution.y;
    float2 p = (uv - 0.5) * 2.0;
    p.x *= aspect;
    
    float value;
    if (fractal_type == 0) {
        value = julia(p, time);
    } else if (fractal_type == 1) {
        value = mandelbrot(p, time);
    } else {
        value = plasma(uv, time);
    }
    
    float3 color = get_color(value);
    
    // Subtle vignette
    float vignette = 1.0 - 0.3 * dot(uv - 0.5, uv - 0.5) * 2.0;
    color *= vignette;
    
    return float4(color, 1.0);
}
