// ElSemi mode_1.ps: linear lighting of the replacement's RGB.
void main()
{
    vec4 color = texture2D(Texture, TexCoord0);
    gl_FragColor = vec4(color.rgb * LightMap.r, color.a);
}
