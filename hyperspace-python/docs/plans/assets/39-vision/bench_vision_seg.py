import time, numpy as np
import objc, Quartz, Vision
from Foundation import NSData
# a CGImage from a numpy RGBA frame
def cgimage(frame):
    h, w, _ = frame.shape
    data = NSData.dataWithBytes_length_(frame.tobytes(), frame.nbytes)
    prov = Quartz.CGDataProviderCreateWithCFData(data)
    cs = Quartz.CGColorSpaceCreateDeviceRGB()
    return Quartz.CGImageCreate(w, h, 8, 32, w*4, cs, Quartz.kCGImageAlphaNoneSkipLast, prov, None, False, Quartz.kCGRenderingIntentDefault)
def pixels(pb):
    Quartz.CVPixelBufferLockBaseAddress(pb, 1)
    w = Quartz.CVPixelBufferGetWidth(pb); h = Quartz.CVPixelBufferGetHeight(pb)
    bpr = Quartz.CVPixelBufferGetBytesPerRow(pb); fmt = Quartz.CVPixelBufferGetPixelFormatType(pb)
    base = Quartz.CVPixelBufferGetBaseAddress(pb)
    buf = base.as_buffer(bpr*h)
    Quartz.CVPixelBufferUnlockBaseAddress(pb, 1)
    return w, h, bpr, fmt, np.frombuffer(buf, dtype=np.uint8).copy()
for (h, w) in ((360,640),(720,1280)):
    frame = (np.random.rand(h, w, 4)*255).astype(np.uint8)
    img = cgimage(frame)
    for name, mk in (("person", lambda: Vision.VNGeneratePersonSegmentationRequest.alloc().initWithCompletionHandler_(None)),
                     ("subject", lambda: Vision.VNGenerateForegroundInstanceMaskRequest.alloc().initWithCompletionHandler_(None))):
        for q in (0, 1, 2) if name=="person" else (None,):
            def run():
                req = mk()
                if q is not None: req.setQualityLevel_(q)   # 0 accurate 1 balanced 2 fast
                hd = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, {})
                ok, err = hd.performRequests_error_([req], None)
                return req, ok, err
            try:
                req, ok, err = run()
                if not ok: print(name, q, "err", err); continue
                res = req.results()
                if not res: print(f"{name} q={q} {w}x{h}: no result (synthetic noise has no subject)"); 
                for _ in range(3): run()
                t=time.perf_counter(); N=20
                for _ in range(N): req, ok, err = run()
                dt=(time.perf_counter()-t)/N*1000
                res = req.results()
                desc=""
                if res and name=="person":
                    pb = res[0].pixelBuffer(); pw,ph,bpr,fmt,_ = pixels(pb); desc=f"mask {pw}x{ph} fmt={fmt:#x} bpr={bpr}"
                elif res:
                    desc=f"instances={res[0].allInstances().count()}"
                print(f"vision {name} q={q} {w}x{h}: {dt:.1f} ms/call (CGImage in, mask out) {desc}")
            except Exception as e:
                print(name, q, "exception", repr(e)[:200])
