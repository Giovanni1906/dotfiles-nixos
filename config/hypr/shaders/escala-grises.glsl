precision mediump float;
varying vec2 v_texcoord;
uniform sampler2D tex;

void main() {
    vec4 c = texture2D(tex, v_texcoord);
    // Luminancia BT.709 (estándar de monitores — más fiel que promediar RGB)
    float l = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
    gl_FragColor = vec4(l, l, l, c.a);
}
