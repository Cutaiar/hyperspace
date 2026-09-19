"""Question B.3 — one VGG conv layer as a moderngl fragment shader.

    uv run --extra dream python tools/dream_bench/b_glsl_conv.py [--res 256]

macOS is OpenGL 4.1: no compute shaders, no SSBOs, so a conv layer is a
fullscreen pass that reads the activation tensor as a 2D-array texture
(C/4 RGBA32F layers) and writes output channels through MRT. Weights ride
in std140 uniform blocks (64 KB max: one output RGBA slice of a 64-in 3x3
conv is 9*16 mat4 = 36 KB, so one block per output slice, up to 8 output
slices — 32 channels — per pass with 8 MRT attachments and 8 blocks).

It times the 64 -> 64 channel 3x3 conv + ReLU at `res` px for 1, 2, 4 and 8
output slices per pass, checks the result against torch, and times the same
conv in torch on MPS (forward, and forward+backward-to-input) for the
comparison. The trunk estimate at the end scales by MAC count: the layer is
2.4 GMAC; VGG conv1_1..conv3_3 forward is 12.1 GMAC, and backward to the
input (frozen weights) costs about one more forward per layer.
"""

from __future__ import annotations

import argparse

import moderngl
import numpy as np
import torch
from common import bench, machine_info, make_ctx, md_table, mps_sync

VS = """
#version 410
const vec2 P[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
void main() { gl_Position = vec4(P[gl_VertexID], 0.0, 1.0); }
"""


def fs_source(n_out: int, c_in_slices: int = 16) -> str:
    blocks = "\n".join(
        f"layout(std140) uniform W{k} {{ mat4 w{k}[{9 * c_in_slices}]; }};" for k in range(n_out))
    outs = "\n".join(f"layout(location = {k}) out vec4 f{k};" for k in range(n_out))
    accs = "\n".join(f"    vec4 a{k} = bias[{k}];" for k in range(n_out))
    macs = "\n".join(f"            a{k} += w{k}[t * {c_in_slices} + s] * v;" for k in range(n_out))
    writes = "\n".join(f"    f{k} = max(a{k}, 0.0);" for k in range(n_out))
    return f"""
#version 410
uniform sampler2DArray u_in;
uniform vec4 bias[{n_out}];
uniform ivec2 u_size;
{blocks}
{outs}
void main() {{
    ivec2 p = ivec2(gl_FragCoord.xy);
{accs}
    for (int t = 0; t < 9; t++) {{
        ivec2 q = p + ivec2(t % 3 - 1, t / 3 - 1);
        if (q.x < 0 || q.y < 0 || q.x >= u_size.x || q.y >= u_size.y) continue;  // zero pad
        for (int s = 0; s < {c_in_slices}; s++) {{
            vec4 v = texelFetch(u_in, ivec3(q, s), 0);
{macs}
        }}
    }}
{writes}
}}
"""


class GLConv:
    """3x3 conv C_in -> C_out (multiples of 4) + ReLU as fullscreen passes."""

    def __init__(self, ctx: moderngl.Context, res: int, weight: np.ndarray, bias: np.ndarray,
                 per_pass: int):
        self.ctx, self.res, self.per_pass = ctx, res, per_pass
        c_out, c_in = weight.shape[:2]
        self.si, self.so = c_in // 4, c_out // 4
        self.prog = ctx.program(vertex_shader=VS, fragment_shader=fs_source(per_pass, self.si))
        self.vao = ctx.vertex_array(self.prog, [])
        self.prog["u_size"].value = (res, res)
        # std140 mat4 per (tap, in-slice): column-major mat4 M with M*v = out
        # over v = 4 input channels -> 4 output channels of the slice
        self.ubos = []
        for o in range(self.so):
            arr = np.zeros((9, self.si, 4, 4), dtype=np.float32)  # [tap, s, col=in, row=out]
            for t in range(9):
                ky, kx = divmod(t, 3)
                for s in range(self.si):
                    # column j of M is the outputs for input channel j
                    arr[t, s] = weight[o * 4:o * 4 + 4, s * 4:s * 4 + 4, ky, kx].T
            self.ubos.append(ctx.buffer(arr.tobytes()))
        self.bias = bias.astype(np.float32)
        self.out = ctx.texture_array((res, res, self.so), 4, dtype="f4")
        # one framebuffer per pass over `per_pass` layers of the output array;
        # moderngl cannot attach array layers (and detect_framebuffer() trips
        # on layered attachments), so raw GL builds and binds the FBOs
        from OpenGL import GL

        self.GL = GL
        self.fbos = []
        for p in range(0, self.so, per_pass):
            fid = int(GL.glGenFramebuffers(1))
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fid)
            n = min(per_pass, self.so - p)
            for k in range(n):
                GL.glFramebufferTextureLayer(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0 + k,
                                             self.out.glo, 0, p + k)
            GL.glDrawBuffers(n, [GL.GL_COLOR_ATTACHMENT0 + k for k in range(n)])
            assert GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE
            self.fbos.append(fid)
        for k in range(per_pass):
            self.prog[f"W{k}"].binding = k

    def forward(self, inp: moderngl.TextureArray) -> None:
        inp.use(location=0)
        self.prog["u_in"].value = 0
        for i, fbo in enumerate(self.fbos):
            base = i * self.per_pass
            for k in range(self.per_pass):
                self.ubos[base + k].bind_to_uniform_block(k)
            self.prog["bias"].write(self.bias[base * 4:(base + self.per_pass) * 4].tobytes())
            self.GL.glBindFramebuffer(self.GL.GL_FRAMEBUFFER, fbo)
            self.GL.glViewport(0, 0, self.res, self.res)
            self.vao.render(moderngl.TRIANGLES, vertices=3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=256)
    args = ap.parse_args()
    res = args.res
    print(machine_info())
    ctx = make_ctx()
    rng = np.random.default_rng(0)
    w = (rng.standard_normal((64, 64, 3, 3)) * 0.05).astype(np.float32)
    b = (rng.standard_normal(64) * 0.1).astype(np.float32)
    x = rng.random((64, res, res), dtype=np.float32)

    # input as a 16-layer RGBA32F array: layer s holds channels 4s..4s+3
    x_layers = np.ascontiguousarray(x.reshape(16, 4, res, res).transpose(0, 2, 3, 1))
    inp = ctx.texture_array((res, res, 16), 4, x_layers.tobytes(), dtype="f4")

    # torch reference
    xt = torch.from_numpy(x)[None]
    ref = torch.relu(torch.nn.functional.conv2d(xt, torch.from_numpy(w), torch.from_numpy(b),
                                                padding=1))[0].numpy()

    rows = []
    for per_pass in (1, 2, 4, 8):
        conv = GLConv(ctx, res, w, b, per_pass)
        conv.forward(inp)
        ctx.finish()
        got = np.frombuffer(conv.out.read(), dtype=np.float32).reshape(16, res, res, 4)
        got = got.transpose(0, 3, 1, 2).reshape(64, res, res)
        err = np.abs(got - ref).max()
        st = bench(lambda c=conv: c.forward(inp), n=30, sync=ctx.finish)
        rows.append([f"GLSL {per_pass} slice/pass ({16 // per_pass} passes)", st["p50"], st["p99"],
                     f"{err:.2e}"])
        print(rows[-1])

    # torch MPS, same layer
    wt, bt = torch.from_numpy(w).to("mps"), torch.from_numpy(b).to("mps")
    xm = xt.to("mps")

    def fwd():
        return torch.relu(torch.nn.functional.conv2d(xm, wt, bt, padding=1))

    st = bench(fwd, n=30, sync=mps_sync)
    rows.append(["torch MPS forward", st["p50"], st["p99"], "-"])
    xg = xm.clone().requires_grad_(True)

    def fb():
        y = torch.relu(torch.nn.functional.conv2d(xg, wt, bt, padding=1))
        (g,) = torch.autograd.grad(y.mean(), xg)
        return g

    st = bench(fb, n=30, sync=mps_sync)
    rows.append(["torch MPS forward + backward(input)", st["p50"], st["p99"], "-"])
    xh, wh, bh = xm.half(), wt.half(), bt.half()

    def fwd16():
        return torch.relu(torch.nn.functional.conv2d(xh, wh, bh, padding=1))

    st = bench(fwd16, n=30, sync=mps_sync)
    rows.append(["torch MPS forward fp16", st["p50"], st["p99"], "-"])

    print(f"\n### B.3 one 3x3 conv 64->64 + ReLU at {res} px (2.4 GMAC), ms\n")
    print(md_table(["path", "p50", "p99", "max |err| vs torch"], rows))
    best = min(r[1] for r in rows if str(r[0]).startswith("GLSL"))
    gmac = 64 * 64 * 9 * res * res / 1e9
    print(f"\nbest GLSL: {best:.2f} ms -> {gmac / best * 1e3:.0f} GMAC/s")
    trunk_fwd = 12.1 * (res / 256) ** 2
    print(f"estimate, VGG conv1_1..conv3_3 at {res} px: forward {trunk_fwd:.1f} GMAC -> "
          f"{trunk_fwd / gmac * best:.1f} ms; forward+backward ~x2 -> "
          f"{2 * trunk_fwd / gmac * best:.1f} ms per gradient step "
          f"(torch MPS measures ~6 ms for the same step at 256 px, b_mlx.py)")


if __name__ == "__main__":
    main()
