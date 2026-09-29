"""Question B.1 — zero-copy GL <-> Metal <-> torch/MLX on macOS from Python.

    uv run python tools/dream_bench/b_iosurface.py [--res 256]

What it prototypes, in order, stopping at the first thing that fails:

  1. An IOSurface (Quartz's IOSurface class) bound to an OpenGL
     GL_TEXTURE_RECTANGLE via CGLTexImageIOSurface2D (ctypes on the OpenGL
     framework) in moderngl's own CGL context, wrapped as a moderngl
     Framebuffer with ctx.detect_framebuffer(). The real Renderer draws into
     it.
  2. The same IOSurface as an MTLTexture (newTextureWithDescriptor:
     iosurface:plane:) — verified by a Metal blit into an MTLBuffer and a
     pixel compare against glReadPixels.
  3. The IOSurface's host-visible memory wrapped as an MTLBuffer
     (newBufferWithBytesNoCopy) and handed to torch and MLX through a
     hand-built DLPack capsule (device kDLMetal) — a torch MPS tensor / MLX
     array that *is* the GL render target. Verified by pixel compare.
  4. Timings: the GL render into the IOSurface, and a dream-style read of it
     from torch with no copy at all, versus the glReadPixels path.

torch has no public "MPS tensor from MTLBuffer" API (checked: torch.mps and
torch._C._mps_* expose only the host alias, events, shaders, capture). The
DLPack import path is public and accepts kDLMetal, and the data pointer of a
kDLMetal DLTensor is an id<MTLBuffer> — that is the hook this uses.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import time

import numpy as np
from common import Scene, bench, machine_info, make_ctx, md_table

GL_TEXTURE_RECTANGLE = 0x84F5
GL_RGBA = 0x1908
GL_BGRA = 0x80E1
GL_UNSIGNED_INT_8_8_8_8_REV = 0x8367
GL_FRAMEBUFFER = 0x8D40
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
MTLPixelFormatBGRA8Unorm = 80
MTLResourceStorageModeShared = 0


# ---- DLPack structs (v0.x ABI, what torch/mlx consume) -------------------


class DLDevice(ctypes.Structure):
    _fields_ = [("device_type", ctypes.c_int), ("device_id", ctypes.c_int)]


class DLDataType(ctypes.Structure):
    _fields_ = [("code", ctypes.c_uint8), ("bits", ctypes.c_uint8), ("lanes", ctypes.c_uint16)]


class DLTensor(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_void_p),
        ("device", DLDevice),
        ("ndim", ctypes.c_int),
        ("dtype", DLDataType),
        ("shape", ctypes.POINTER(ctypes.c_int64)),
        ("strides", ctypes.POINTER(ctypes.c_int64)),
        ("byte_offset", ctypes.c_uint64),
    ]


class DLManagedTensor(ctypes.Structure):
    pass


DELETER = ctypes.CFUNCTYPE(None, ctypes.POINTER(DLManagedTensor))
DLManagedTensor._fields_ = [
    ("dl_tensor", DLTensor),
    ("manager_ctx", ctypes.c_void_p),
    ("deleter", DELETER),
]

kDLMetal = 8
kDLUInt = 1

_keep = []  # everything the capsule points at must outlive it


def dlpack_capsule(mtl_buffer_id: int, shape, strides_elems, byte_offset: int = 0):
    """A 'dltensor' capsule describing uint8 data in an MTLBuffer."""
    n = len(shape)
    shp = (ctypes.c_int64 * n)(*shape)
    strd = (ctypes.c_int64 * n)(*strides_elems)

    @DELETER
    def deleter(_p):
        pass

    mt = DLManagedTensor()
    mt.dl_tensor.data = mtl_buffer_id
    mt.dl_tensor.device = DLDevice(kDLMetal, 0)
    mt.dl_tensor.ndim = n
    mt.dl_tensor.dtype = DLDataType(kDLUInt, 8, 1)
    mt.dl_tensor.shape = shp
    mt.dl_tensor.strides = strd
    mt.dl_tensor.byte_offset = byte_offset
    mt.manager_ctx = None
    mt.deleter = deleter
    _keep.extend([shp, strd, deleter, mt])
    PyCapsule_New = ctypes.pythonapi.PyCapsule_New
    PyCapsule_New.restype = ctypes.py_object
    PyCapsule_New.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]
    return PyCapsule_New(ctypes.addressof(mt), b"dltensor", None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=256)
    args = ap.parse_args()
    W = H = args.res
    print(machine_info())

    import Metal
    import objc
    import Quartz
    from OpenGL import GL

    ctx = make_ctx()
    gl = ctypes.CDLL("/System/Library/Frameworks/OpenGL.framework/OpenGL")
    gl.CGLGetCurrentContext.restype = ctypes.c_void_p
    gl.CGLTexImageIOSurface2D.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                                          ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
    iosf = ctypes.CDLL("/System/Library/Frameworks/IOSurface.framework/IOSurface")
    iosf.IOSurfaceGetBaseAddress.restype = ctypes.c_void_p
    iosf.IOSurfaceGetBaseAddress.argtypes = [ctypes.c_void_p]
    iosf.IOSurfaceGetBytesPerRow.restype = ctypes.c_size_t
    iosf.IOSurfaceGetBytesPerRow.argtypes = [ctypes.c_void_p]
    iosf.IOSurfaceGetAllocSize.restype = ctypes.c_size_t
    iosf.IOSurfaceGetAllocSize.argtypes = [ctypes.c_void_p]
    cgl = gl.CGLGetCurrentContext()
    print(f"CGL context: {cgl:#x}")

    # ---- 1. IOSurface + GL texture + moderngl framebuffer ------------------
    surf = Quartz.IOSurface.alloc().initWithProperties_({
        "IOSurfaceWidth": W, "IOSurfaceHeight": H, "IOSurfaceBytesPerElement": 4,
        "IOSurfacePixelFormat": 0x42475241,  # 'BGRA'
    })
    surf_ptr = objc.pyobjc_id(surf)
    bpr = iosf.IOSurfaceGetBytesPerRow(surf_ptr)
    alloc = iosf.IOSurfaceGetAllocSize(surf_ptr)
    base = iosf.IOSurfaceGetBaseAddress(surf_ptr)
    print(f"IOSurface {W}x{H}: bytesPerRow {bpr}, allocSize {alloc}, base {base:#x}")

    tex = GL.glGenTextures(1)
    GL.glBindTexture(GL_TEXTURE_RECTANGLE, tex)
    err = gl.CGLTexImageIOSurface2D(cgl, GL_TEXTURE_RECTANGLE, GL_RGBA, W, H, GL_BGRA,
                                    GL_UNSIGNED_INT_8_8_8_8_REV, surf_ptr, 0)
    print("CGLTexImageIOSurface2D ->", err, "(0 = kCGLNoError)")
    assert err == 0
    fbo_id = GL.glGenFramebuffers(1)
    GL.glBindFramebuffer(GL_FRAMEBUFFER, fbo_id)
    GL.glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_RECTANGLE, tex, 0)
    status = GL.glCheckFramebufferStatus(GL_FRAMEBUFFER)
    print("framebuffer status", hex(status), "(0x8cd5 = complete)")
    assert status == GL_FRAMEBUFFER_COMPLETE
    fbo = ctx.detect_framebuffer(int(fbo_id))
    print("detect_framebuffer size:", fbo.size, "(rectangle attachments report 0 — pass viewport)")
    VP = (0, 0, W, H)

    sc = Scene(ctx, W, H)
    sc.fbo = fbo  # the Renderer now draws straight into the IOSurface
    sc.step()
    ctx.finish()
    ref = np.frombuffer(fbo.read(viewport=VP, components=4), dtype=np.uint8).reshape(H, W, 4)
    print("glReadPixels from the IOSurface FBO: max", ref.max(), "nonzero frac",
          f"{(ref[..., :3].max(-1) > 0).mean():.3f}")

    # ---- 2. Metal texture on the same IOSurface ----------------------------
    dev = Metal.MTLCreateSystemDefaultDevice()
    desc = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
        MTLPixelFormatBGRA8Unorm, W, H, False)
    mtex = dev.newTextureWithDescriptor_iosurface_plane_(desc, surf, 0)
    print("MTLTexture:", mtex.width(), "x", mtex.height(), "pixelFormat", mtex.pixelFormat())
    queue = dev.newCommandQueue()
    mbuf = dev.newBufferWithLength_options_(bpr * H, MTLResourceStorageModeShared)
    cb = queue.commandBuffer()
    blit = cb.blitCommandEncoder()
    blit.copyFromTexture_sourceSlice_sourceLevel_sourceOrigin_sourceSize_toBuffer_destinationOffset_destinationBytesPerRow_destinationBytesPerImage_(
        mtex, 0, 0, Metal.MTLOrigin(0, 0, 0), Metal.MTLSize(W, H, 1), mbuf, 0, bpr, bpr * H)
    blit.endEncoding()
    cb.commit()
    cb.waitUntilCompleted()
    got = np.frombuffer(mbuf.contents().as_buffer(bpr * H), dtype=np.uint8).reshape(
        H, bpr // 4, 4)[:, :W]
    # the surface holds rows in GL order (same as glReadPixels); BGRA vs RGBA
    got_rgba = got[..., [2, 1, 0, 3]]
    print("Metal blit == glReadPixels:", np.array_equal(got_rgba, ref))

    # ---- 3. MTLBuffer over the IOSurface memory -> torch / MLX via DLPack --
    import torch

    view = (ctypes.c_char * alloc).from_address(base)
    nocopy = dev.newBufferWithBytesNoCopy_length_options_deallocator_(
        view, alloc, MTLResourceStorageModeShared, None)
    print("newBufferWithBytesNoCopy:", nocopy, "length", nocopy.length() if nocopy else None)
    same_ptr = nocopy is not None and ctypes.addressof(
        ctypes.c_char.from_buffer(nocopy.contents().as_buffer(1))) == base
    print("MTLBuffer.contents() == IOSurface base:", same_ptr)
    assert nocopy is not None
    buf_id = objc.pyobjc_id(nocopy)

    cap = dlpack_capsule(buf_id, (H, bpr // 4, 4), (bpr, 4, 1))
    t = torch.from_dlpack(cap)
    print("torch.from_dlpack(kDLMetal MTLBuffer):", t.shape, t.dtype, t.device)
    torch.mps.synchronize()
    t_rgba = t[:, :W][..., [2, 1, 0, 3]].cpu().numpy()
    print("torch view == glReadPixels:", np.array_equal(t_rgba, ref))
    # re-render, re-check: the tensor follows the GL output with no copy
    sc.step()
    ctx.finish()
    ref2 = np.frombuffer(fbo.read(viewport=VP, components=4), dtype=np.uint8).reshape(H, W, 4)
    t_rgba2 = t[:, :W][..., [2, 1, 0, 3]].cpu().numpy()
    print("after a second render, torch view tracks GL:", np.array_equal(t_rgba2, ref2),
          "(and differs from frame 1:", not np.array_equal(ref, ref2), ")")

    try:
        import mlx.core as mx

        cap2 = dlpack_capsule(buf_id, (H, bpr // 4, 4), (bpr, 4, 1))
        m = mx.from_dlpack(cap2)
        mx.eval(m)
        m_rgba = np.asarray(m)[:, :W][..., [2, 1, 0, 3]]
        print("mlx.from_dlpack(kDLMetal MTLBuffer):", m.shape, m.dtype,
              "== glReadPixels:", np.array_equal(m_rgba, ref2))
    except Exception as e:  # noqa: BLE001
        print("MLX from_dlpack failed:", repr(e))

    # ---- 4. timings ---------------------------------------------------------
    rows = []
    st = bench(sc.step, sync=ctx.finish)
    rows.append(["render into IOSurface FBO (+finish)", st["p50"], st["p99"]])
    sc2 = Scene(ctx, W, H)
    st = bench(sc2.step, sync=ctx.finish)
    rows.append(["render into ordinary texture FBO (+finish)", st["p50"], st["p99"]])

    def gl_to_torch_zero_copy():
        # what the dream worker would do each frame: GL done -> touch tensor on GPU
        ctx.finish()
        f = t[:, :W, :3].permute(2, 0, 1).unsqueeze(0).float().div_(255.0).contiguous()
        torch.mps.synchronize()
        return f

    st = bench(gl_to_torch_zero_copy)
    rows.append(["finish + u8->f32 straight from the IOSurface tensor", st["p50"], st["p99"]])

    def gl_to_torch_copy():
        raw = np.frombuffer(sc2.fbo.read(viewport=VP, components=4), dtype=np.uint8).reshape(H, W, 4)
        g = torch.from_numpy(raw).to("mps")
        f = g[:, :, :3].permute(2, 0, 1).unsqueeze(0).float().div_(255.0).contiguous()
        torch.mps.synchronize()
        return f

    st = bench(gl_to_torch_copy)
    rows.append(["glReadPixels + np->MPS + u8->f32 (copy path)", st["p50"], st["p99"]])

    # write-back: torch result -> IOSurface tensor (GPU copy) -> GL samples it
    src = torch.rand((H, W, 4), device="mps").mul(255).to(torch.uint8)

    def torch_to_gl_zero_copy():
        t[:, :W].copy_(src)
        torch.mps.synchronize()

    st = bench(torch_to_gl_zero_copy)
    rows.append(["torch -> IOSurface tensor (GPU copy_) + sync", st["p50"], st["p99"]])
    torch.mps.synchronize()
    chk = np.frombuffer(fbo.read(viewport=VP, components=4), dtype=np.uint8).reshape(H, W, 4)
    exp = src.cpu().numpy()[..., [2, 1, 0, 3]]
    print("GL sees the torch write:", np.array_equal(chk, exp))
    print()
    print(md_table(["op", "p50 ms", "p99 ms"], rows))
    _ = time


if __name__ == "__main__":
    main()
