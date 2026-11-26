# Dream layers · forward · Apple M3 Max · mps · torch 2.14.0

## googlenet · fp16 · forward: ms p50 (p99) per forward

| layer | mode | 960×540 | 1280×720 | 1920×1080 | compile s |
|---|---|---|---|---|---|
| conv1 | fold | 1.3 (1.4) | 1.7 (1.9) | 2.9 (3.2) |  |
| conv2 | fold | 1.9 (3.0) | 2.7 (3.0) | 5.1 (5.3) |  |
| conv3 | fold | 2.4 (2.7) | 3.6 (4.9) | 7.0 (7.3) |  |
| inception3a | fold | 3.1 (3.5) | 4.8 (9.7) | 9.5 (9.8) |  |
| inception3b | fold | 3.8 (10.8) | 5.7 (6.4) | 11.5 (12.2) |  |
| inception4a | fold | 4.2 (4.6) | 6.5 (6.7) | 12.9 (13.4) |  |
| inception4b | fold | 4.5 (5.5) | 6.9 (7.2) | 13.7 (14.1) |  |
| inception4c | fold | 4.9 (5.5) | 7.4 (7.6) | 14.6 (15.0) |  |
| inception4d | fold | 5.2 (5.8) | 7.8 (8.0) | 15.5 (16.1) |  |
| inception4e | fold | 5.6 (5.9) | 8.6 (9.0) | 16.8 (17.1) |  |
| inception5a | fold | 6.0 (6.3) | 9.0 (9.4) | 17.6 (18.1) |  |
| inception5b | fold | 6.4 (6.7) | 9.5 (10.1) | 18.2 (18.6) |  |

## googlenet · fp32 · forward: ms p50 (p99) per forward

| layer | mode | 960×540 | 1280×720 | 1920×1080 | compile s |
|---|---|---|---|---|---|
| conv1 | fold | 1.6 (1.8) | 2.3 (2.8) | 4.3 (4.8) |  |
| conv2 | fold | 2.3 (2.9) | 3.4 (3.8) | 6.7 (7.3) |  |
| conv3 | fold | 2.9 (3.2) | 4.5 (4.7) | 9.0 (9.5) |  |
| inception3a | fold | 3.7 (3.9) | 5.7 (6.1) | 11.8 (12.2) |  |
| inception3b | fold | 4.4 (4.6) | 6.8 (7.6) | 14.4 (15.1) |  |
| inception4a | fold | 4.9 (5.1) | 7.6 (8.0) | 16.0 (16.5) |  |
| inception4b | fold | 5.2 (5.6) | 8.1 (8.3) | 16.9 (17.2) |  |
| inception4c | fold | 5.7 (6.6) | 8.6 (8.8) | 17.9 (18.4) |  |
| inception4d | fold | 6.0 (6.2) | 9.1 (9.5) | 19.0 (20.6) |  |
| inception4e | fold | 6.5 (6.6) | 9.9 (10.4) | 20.4 (20.9) |  |
| inception5a | fold | 6.8 (7.2) | 10.5 (11.0) | 21.4 (21.8) |  |
| inception5b | fold | 7.0 (7.7) | 10.9 (11.2) | 22.1 (22.7) |  |

## vgg16 · fp16 · forward: ms p50 (p99) per forward

| layer | mode | 960×540 | 1280×720 | 1920×1080 | compile s |
|---|---|---|---|---|---|
| conv1_1 | fold | 1.4 (2.7) | 2.1 (2.1) | 3.7 (3.9) |  |
| conv1_2 | fold | 4.1 (4.3) | 6.9 (7.6) | 14.4 (14.9) |  |
| conv2_1 | fold | 7.3 (7.7) | 12.6 (13.0) | 27.8 (28.5) |  |
| conv2_2 | fold | 9.7 (10.0) | 16.9 (17.3) | 37.5 (38.1) |  |
| conv3_1 | fold | 11.8 (12.2) | 20.6 (21.1) | 46.1 (46.6) |  |
| conv3_2 | fold | 14.2 (14.5) | 24.7 (25.1) | 55.2 (55.8) |  |
| conv3_3 | fold | 16.4 (17.1) | 28.7 (29.1) | 64.2 (64.9) |  |
| conv4_1 | fold | 18.0 (18.4) | 31.5 (32.0) | 70.6 (71.1) |  |
| conv4_2 | fold | 20.3 (20.8) | 35.6 (36.2) | 79.5 (80.0) |  |
| conv4_3 | fold | 22.6 (23.3) | 39.5 (40.1) | 88.5 (88.8) |  |
| conv5_1 | fold | 23.4 (24.0) | 40.9 (41.5) | 91.6 (92.3) |  |
| conv5_2 | fold | 24.2 (24.8) | 42.1 (42.6) | 94.0 (94.8) |  |
| conv5_3 | fold | 24.7 (25.2) | 43.2 (43.8) | 96.2 (99.5) |  |

## vgg16 · fp32 · forward: ms p50 (p99) per forward

| layer | mode | 960×540 | 1280×720 | 1920×1080 | compile s |
|---|---|---|---|---|---|
| conv1_1 | fold | 2.5 (3.9) | 3.0 (3.2) | 6.0 (6.5) |  |
| conv1_2 | fold | 5.3 (5.6) | 8.8 (9.3) | 19.2 (19.7) |  |
| conv2_1 | fold | 8.8 (9.1) | 15.2 (15.6) | 33.8 (34.3) |  |
| conv2_2 | fold | 11.5 (12.0) | 20.1 (20.7) | 44.9 (45.4) |  |
| conv3_1 | fold | 13.8 (14.2) | 24.1 (24.6) | 54.3 (54.8) |  |
| conv3_2 | fold | 16.4 (16.9) | 28.7 (29.3) | 64.6 (65.2) |  |
| conv3_3 | fold | 18.9 (19.5) | 33.3 (33.8) | 75.0 (76.5) |  |
| conv4_1 | fold | 20.7 (21.2) | 36.3 (36.8) | 82.0 (82.3) |  |
| conv4_2 | fold | 23.3 (24.0) | 40.9 (41.4) | 92.0 (92.6) |  |
| conv4_3 | fold | 25.9 (26.4) | 45.5 (46.1) | 102.2 (105.3) |  |
| conv5_1 | fold | 26.8 (27.5) | 47.2 (55.0) | 105.6 (105.8) |  |
| conv5_2 | fold | 27.6 (28.0) | 48.3 (48.8) | 108.2 (108.4) |  |
| conv5_3 | fold | 28.3 (29.1) | 49.6 (50.0) | 110.7 (111.0) |  |

## The fit: ms ≈ fixed + o × convs + p × megapixels + c × GMAC

fixed is per call; o per conv (launches: what folding and compiling should remove); p per megapixel whatever the layer (elementwise work and memory traffic: the floor at high resolution); c per billion multiply-adds.

| net | mode | precision | pass | fixed ms | o ms/conv | p ms/Mpx | c ms/GMAC | GMAC/s | worst miss ms | points |
|---|---|---|---|---|---|---|---|---|---|---|
| googlenet | fold | fp16 | forward | 0.86 | 0.023 | 0.97 | 0.233 | 4294 | 1.16 | 36 |
| googlenet | fold | fp32 | forward | 0.83 | 0.018 | 1.57 | 0.281 | 3563 | 1.18 | 36 |
| vgg16 | fold | fp16 | forward | 0.56 | 0.000 | 3.61 | 0.142 | 7029 | 5.00 | 39 |
| vgg16 | fold | fp32 | forward | 0.46 | 0.000 | 5.33 | 0.160 | 6241 | 6.12 | 39 |
