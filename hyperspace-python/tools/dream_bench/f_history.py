"""Question F — history depth: texture memory and the composite cost.

    uv run python tools/dream_bench/f_history.py

Memory per stored frame is arithmetic (printed for RGBA8, RGBA16F and
RGB32F at the candidate dream resolutions, the 1280x820 window and its 2x
retina framebuffer). The composite cost is measured: a fullscreen pass
over a 1280x820 target sampling N layers of a 2D-array texture with a
per-layer age weight (darker and fainter with age), N = 1/4/8/16/32, at
the dream resolutions and at full resolution, plus the same pass on a
2x retina-sized target. Each number is render + finish, so it is the GPU
cost the renderer's frame would absorb.
"""

from __future__ import annotations

import moderngl
import numpy as np
from common import bench, machine_info, make_ctx, md_table

VS = """
#version 410
const vec2 P[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
out vec2 v_uv;
void main() { gl_Position = vec4(P[gl_VertexID], 0.0, 1.0); v_uv = P[gl_VertexID] * 0.5 + 0.5; }
"""

FS = """
#version 410
uniform sampler2DArray u_hist;
uniform int u_n;
uniform int u_head;
uniform float u_alpha;
uniform float u_fade;
in vec2 v_uv;
out vec4 f;
void main() {
    vec3 acc = vec3(0.0);
    float w = u_alpha;
    for (int i = 0; i < u_n; i++) {
        int layer = (u_head - i + u_n) % u_n;      // newest first
        acc += texture(u_hist, vec3(v_uv, float(layer))).rgb * w;
        w *= u_fade;                                // older = darker, fainter
    }
    f = vec4(acc, 1.0);
}
"""


def main() -> None:
    print(machine_info())
    print("\n### F. memory per stored frame\n")
    rows = []
    for label, (w, h) in [("128 short side", (200, 128)), ("192", (296, 192)), ("256", (400, 256)),
                          ("384", (600, 384)), ("512", (800, 512)),
                          ("1280x820 window", (1280, 820)), ("2560x1640 retina", (2560, 1640))]:
        px = w * h
        rows.append([label, f"{w}x{h}", px * 4 / 2**20, px * 8 / 2**20, px * 12 / 2**20,
                     f"{px * 4 * 32 / 2**20:.1f} / {px * 8 * 32 / 2**20:.1f}"])
    print(md_table(["buffer", "size", "RGBA8 MiB", "RGBA16F MiB", "RGB32F MiB",
                    "32 frames RGBA8 / RGBA16F MiB"], rows))

    ctx = make_ctx()
    prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
    vao = ctx.vertex_array(prog, [])
    prog["u_alpha"].value = 0.4
    prog["u_fade"].value = 0.85
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
    rows = []
    rng = np.random.default_rng(0)
    for target in [(1280, 820), (2560, 1640)]:
        fbo = ctx.framebuffer(color_attachments=[ctx.texture(target, 4)])
        for hist in [(400, 256), (800, 512), (1280, 820)]:
            for n in (1, 4, 8, 16, 32):
                data = rng.integers(0, 255, (n, hist[1], hist[0], 4), dtype=np.uint8)
                tex = ctx.texture_array((hist[0], hist[1], n), 4, data.tobytes())
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                tex.use(0)
                prog["u_hist"].value = 0
                prog["u_n"].value = n
                prog["u_head"].value = n - 1
                fbo.use()
                ctx.viewport = (0, 0, *target)

                def draw(fbo=fbo):
                    fbo.clear(0.0, 0.0, 0.0, 1.0)
                    vao.render(moderngl.TRIANGLES, vertices=3)

                st = bench(draw, n=40, sync=ctx.finish)
                rows.append([f"{target[0]}x{target[1]}", f"{hist[0]}x{hist[1]}", n, st["p50"],
                             st["p99"]])
                tex.release()
            print(rows[-1], flush=True)
        fbo.release()
    print("\n### F. composite cost: fullscreen pass sampling N history layers (ms, render+finish)\n")
    print(md_table(["target", "history res", "N layers", "p50", "p99"], rows))


if __name__ == "__main__":
    main()
