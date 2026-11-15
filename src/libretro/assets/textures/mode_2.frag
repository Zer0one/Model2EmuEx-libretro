// ElSemi mode_2.ps: conversion-table lighting for textured faces.
void main()
{
    vec4 color = texture2D(Texture, TexCoord0);
    float light = LightMap.r;
    if (LightMap.b != 0.0)
        light = texture2D(Luma, vec2(LightMap.r, LightMap.g)).r;
    gl_FragColor = vec4(color.rgb * (2.0 * light), color.a);
}
