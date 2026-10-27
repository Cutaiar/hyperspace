import time, numpy as np, torch, torchvision
from torchvision.models.segmentation import lraspp_mobilenet_v3_large, LRASPP_MobileNet_V3_Large_Weights
dev = torch.device("mps")
print("torch", torch.__version__, "torchvision", torchvision.__version__)
w = LRASPP_MobileNet_V3_Large_Weights.DEFAULT
net = lraspp_mobilenet_v3_large(weights=w).eval().to(dev)
mean = torch.tensor([0.485,0.456,0.406], device=dev).view(1,3,1,1)
std = torch.tensor([0.229,0.224,0.225], device=dev).view(1,3,1,1)
for dtype in (torch.float32, torch.float16):
    n = net.to(dtype)
    for (h, w_) in ((240,320),(360,640),(480,640)):
        frame = (np.random.rand(h, w_, 3)*255).astype(np.uint8)
        def step():
            x = torch.from_numpy(frame).to(dev)                     # upload uint8
            x = x.permute(2,0,1).unsqueeze(0).to(dtype)/255.0
            x = (x-mean.to(dtype))/std.to(dtype)
            with torch.no_grad():
                out = n(x)["out"]                                  # 1x21xHxW
            person = out.softmax(1)[:,15]                           # class 15 = person
            m = (person*255).to(torch.uint8)[0].cpu().numpy()       # readback
            return m
        for _ in range(5): step()
        torch.mps.synchronize()
        t=time.perf_counter(); N=30
        for _ in range(N): m=step()
        torch.mps.synchronize()
        dt=(time.perf_counter()-t)/N*1000
        print(f"lraspp {str(dtype)[6:]} {w_}x{h}: {dt:.1f} ms/frame (upload+infer+softmax+readback), mask {m.shape} {m.dtype}")
