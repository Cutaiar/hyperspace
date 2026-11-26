# Dream layers · compile · Apple M3 Max · mps · torch 2.14.0

## googlenet · fp16 · step: ms p50 (p99) per step

| layer | mode | 456×256 | 960×540 | 1920×1080 | compile s |
|---|---|---|---|---|---|
| conv1 | eager | 1.7 (1.9) | 3.7 (4.8) | 11.8 (12.4) |  |
| conv1 | fold | 1.8 (4.2) | 3.6 (4.3) | 11.1 (11.5) |  |
| conv1 | fold+cl | 1.7 (2.3) | 3.8 (4.0) | 12.1 (12.8) |  |
| conv1 | inductor | 1.9 (3.5) | 3.9 (6.0) | 11.3 (12.1) | 0.2 |
| conv1 | fold+inductor | 1.8 (2.5) | 4.3 (4.9) | 11.4 (12.0) | 0.2 |
| conv1 | fold+cl+inductor | 2.0 (4.4) | 4.6 (4.9) | 15.4 (15.6) | 0.2 |
| conv1 | fold+cl+step | 1.3 (1.5) | 3.7 (3.8) | 13.3 (13.5) | 0.4 |
| conv2 | eager | 2.0 (2.6) | 4.8 (5.1) | 16.2 (16.7) |  |
| conv2 | fold | 2.0 (2.3) | 4.7 (4.9) | 15.3 (15.9) |  |
| conv2 | fold+cl | 2.1 (2.8) | 5.3 (5.7) | 22.8 (24.0) |  |
| conv2 | inductor | 2.1 (3.6) | 4.5 (6.6) | 14.1 (14.5) | 0.5 |
| conv2 | fold+inductor | 2.1 (2.7) | 5.5 (6.4) | 13.6 (14.0) | 0.4 |
| conv2 | fold+cl+inductor | 2.3 (3.2) | 5.8 (6.0) | 19.8 (22.3) | 0.4 |
| conv2 | fold+cl+step | 1.8 (2.4) | 5.2 (5.4) | 18.9 (19.1) | 0.5 |
| conv3 | eager | 2.4 (2.6) | 6.1 (6.6) | 21.4 (22.0) |  |
| conv3 | fold | 2.3 (2.6) | 5.8 (6.0) | 20.1 (20.8) |  |
| conv3 | fold+cl | 2.4 (3.5) | 6.5 (6.8) | 28.0 (28.8) |  |
| conv3 | inductor | 2.7 (4.6) | 7.5 (7.8) | 26.7 (27.0) | 0.8 |
| conv3 | fold+inductor | 2.6 (3.3) | 7.4 (7.8) | 26.3 (26.9) | 0.4 |
| conv3 | fold+cl+inductor | 2.6 (3.7) | 7.3 (7.6) | 25.3 (25.7) | 0.4 |
| conv3 | fold+cl+step | 2.0 (2.6) | 6.3 (6.4) | 23.0 (23.2) | 0.6 |
| inception3a | eager | 3.6 (3.9) | 7.9 (8.3) | 27.7 (28.2) |  |
| inception3a | fold | 2.9 (3.4) | 7.5 (7.8) | 25.9 (26.4) |  |
| inception3a | fold+cl | 3.1 (4.7) | 8.9 (9.4) | 36.1 (37.6) |  |
| inception3a | inductor | 3.3 (5.0) | 9.3 (9.8) | 33.4 (33.7) | 1.5 |
| inception3a | fold+inductor | 3.1 (3.4) | 9.1 (9.5) | 32.7 (33.0) | 1.0 |
| inception3a | fold+cl+inductor | 3.1 (3.3) | 9.0 (9.4) | 32.3 (32.7) | 0.9 |
| inception3a | fold+cl+step | 2.7 (3.3) | 8.3 (8.5) | 30.7 (31.0) | 1.0 |
| inception3b | eager | 4.5 (5.2) | 9.8 (10.2) | 33.9 (34.5) |  |
| inception3b | fold | 3.3 (4.3) | 9.1 (9.6) | 31.5 (31.9) |  |
| inception3b | fold+cl | 3.8 (4.5) | 10.9 (11.2) | 43.9 (45.2) |  |
| inception3b | inductor | 4.0 (4.6) | 11.6 (12.0) | 41.1 (41.7) | 2.0 |
| inception3b | fold+inductor | 3.9 (4.1) | 11.6 (14.6) | 40.9 (42.2) | 1.4 |
| inception3b | fold+cl+inductor | 3.8 (4.0) | 11.1 (11.3) | 39.4 (39.8) | 1.2 |
| inception3b | fold+cl+step | 3.3 (4.2) | 10.3 (10.8) | 37.2 (37.7) | 1.4 |
| inception4a | eager | 5.9 (6.9) | 11.0 (11.5) | 37.7 (38.3) |  |
| inception4a | fold | 4.0 (5.0) | 10.3 (10.8) | 35.0 (35.5) |  |
| inception4a | fold+cl | 4.3 (5.2) | 12.5 (13.3) | 48.8 (49.5) |  |
| inception4a | inductor | 4.4 (4.9) | 12.8 (13.2) | 45.0 (45.5) | 2.8 |
| inception4a | fold+inductor | 4.5 (4.7) | 12.8 (13.0) | 44.8 (45.2) | 1.9 |
| inception4a | fold+cl+inductor | 4.3 (4.5) | 12.4 (12.7) | 43.7 (44.0) | 1.6 |
| inception4a | fold+cl+step | 3.9 (4.0) | 12.0 (12.4) | 43.3 (43.6) | 1.8 |
| inception4b | eager | 7.5 (9.0) | 11.9 (12.3) | 40.1 (40.6) |  |
| inception4b | fold | 4.4 (5.1) | 11.1 (11.6) | 37.3 (37.8) |  |
| inception4b | fold+cl | 4.9 (5.7) | 13.5 (13.8) | 51.9 (52.7) |  |
| inception4b | inductor | 4.9 (5.3) | 13.9 (14.2) | 48.2 (48.7) | 3.8 |
| inception4b | fold+inductor | 4.9 (5.3) | 13.9 (14.1) | 48.0 (48.4) | 2.3 |
| inception4b | fold+cl+inductor | 4.7 (4.9) | 13.5 (13.7) | 46.6 (47.0) | 2.0 |
| inception4b | fold+cl+step | 4.3 (5.1) | 12.9 (13.6) | 46.2 (46.7) | 2.2 |
| inception4c | eager | 8.4 (9.4) | 12.7 (13.3) | 42.6 (42.9) |  |
| inception4c | fold | 5.0 (5.9) | 11.8 (13.2) | 39.6 (40.0) |  |
| inception4c | fold+cl | 5.5 (6.3) | 14.4 (15.0) | 54.8 (55.6) |  |
| inception4c | inductor | 6.2 (7.9) | 14.8 (15.0) | 51.0 (51.3) | 4.3 |
| inception4c | fold+inductor | 5.3 (5.9) | 15.0 (15.4) | 51.2 (51.9) | 2.5 |
| inception4c | fold+cl+inductor | 5.2 (5.5) | 14.5 (15.1) | 49.8 (50.2) | 2.2 |
| inception4c | fold+cl+step | 4.8 (4.8) | 14.0 (14.2) | 49.3 (49.6) | 2.4 |
| inception4d | eager | 9.7 (10.4) | 13.7 (14.5) | 45.4 (45.9) |  |
| inception4d | fold | 5.8 (7.1) | 12.7 (13.0) | 42.1 (42.7) |  |
| inception4d | fold+cl | 6.4 (7.1) | 15.5 (16.0) | 58.1 (58.9) |  |
| inception4d | inductor | 5.8 (6.9) | 16.0 (16.3) | 54.4 (55.4) | 4.8 |
| inception4d | fold+inductor | 5.8 (6.0) | 16.1 (16.5) | 54.7 (55.1) | 2.9 |
| inception4d | fold+cl+inductor | 5.7 (6.1) | 15.6 (15.8) | 52.9 (53.3) | 2.5 |
| inception4d | fold+cl+step | 5.2 (5.6) | 15.2 (15.8) | 52.5 (53.0) | 2.7 |
| inception4e | eager | 10.8 (11.4) | 14.8 (15.3) | 49.0 (49.3) |  |
| inception4e | fold | 6.3 (6.7) | 13.8 (14.2) | 45.4 (46.0) |  |
| inception4e | fold+cl | 7.1 (7.5) | 16.9 (17.3) | 62.4 (63.3) |  |
| inception4e | inductor | 6.9 (8.1) | 17.3 (17.5) | 58.6 (60.4) | 5.5 |
| inception4e | fold+inductor | 6.4 (6.6) | 17.6 (17.8) | 59.3 (59.7) | 3.4 |
| inception4e | fold+cl+inductor | 6.2 (6.6) | 17.0 (17.3) | 57.4 (57.9) | 2.9 |
| inception4e | fold+cl+step | 5.6 (5.8) | 16.5 (17.9) | 56.6 (57.0) | 3.0 |
| inception5a | eager | 11.8 (12.4) | 16.0 (16.8) | 50.9 (51.5) |  |
| inception5a | fold | 6.8 (7.3) | 14.6 (15.1) | 47.3 (47.7) |  |
| inception5a | fold+cl | 8.1 (9.4) | 17.8 (18.3) | 65.2 (66.2) |  |
| inception5a | inductor | 7.5 (8.0) | 18.2 (18.4) | 60.8 (62.0) | 6.2 |
| inception5a | fold+inductor | 6.9 (7.1) | 18.6 (18.8) | 61.8 (62.2) | 3.7 |
| inception5a | fold+cl+inductor | 6.6 (7.1) | 17.9 (18.1) | 59.8 (60.2) | 3.3 |
| inception5a | fold+cl+step | 6.2 (6.3) | 17.5 (17.7) | 59.6 (59.8) | 3.5 |
| inception5b | eager | 13.3 (14.3) | 17.4 (18.6) | 52.7 (53.1) |  |
| inception5b | fold | 7.5 (8.4) | 15.2 (15.5) | 48.8 (49.2) |  |
| inception5b | fold+cl | 8.5 (9.5) | 18.6 (19.4) | 67.4 (86.0) |  |
| inception5b | inductor | 7.6 (9.8) | 19.4 (22.9) | 62.7 (64.4) | 7.5 |
| inception5b | fold+inductor | 7.4 (8.0) | 19.4 (19.8) | 63.9 (64.3) | 4.2 |
| inception5b | fold+cl+inductor | 7.2 (7.5) | 18.6 (19.0) | 61.6 (61.9) | 3.5 |
| inception5b | fold+cl+step | 6.7 (7.1) | 18.3 (18.6) | 61.5 (61.8) | 3.8 |

## googlenet · fp32 · step: ms p50 (p99) per step

| layer | mode | 456×256 | 960×540 | 1920×1080 | compile s |
|---|---|---|---|---|---|
| conv1 | eager | 2.0 (5.2) | 4.7 (4.9) | 15.9 (18.3) |  |
| conv1 | fold | 1.8 (1.9) | 4.5 (4.8) | 14.4 (16.0) |  |
| conv1 | fold+cl | 2.0 (2.8) | 5.4 (5.7) | 18.4 (19.9) |  |
| conv1 | inductor | 1.8 (3.0) | 4.5 (4.9) | 14.1 (14.8) | 0.7 |
| conv1 | fold+inductor | 1.9 (2.2) | 4.5 (4.7) | 14.1 (14.8) | 0.1 |
| conv1 | fold+cl+inductor | 3.2 (3.7) | 6.3 (6.7) | 21.7 (22.4) | 0.2 |
| conv1 | fold+cl+step | 1.8 (2.3) | 5.0 (5.5) | 18.9 (19.2) | 0.5 |
| conv2 | eager | 2.1 (2.3) | 5.9 (6.3) | 20.7 (22.0) |  |
| conv2 | fold | 2.1 (3.0) | 5.5 (5.9) | 18.7 (20.3) |  |
| conv2 | fold+cl | 2.3 (4.5) | 6.9 (7.3) | 30.6 (31.6) |  |
| conv2 | inductor | 2.1 (2.6) | 5.4 (5.7) | 17.4 (18.1) | 0.4 |
| conv2 | fold+inductor | 2.4 (4.9) | 5.3 (5.6) | 17.2 (17.7) | 0.3 |
| conv2 | fold+cl+inductor | 2.5 (3.3) | 7.5 (7.7) | 26.7 (27.0) | 0.4 |
| conv2 | fold+cl+step | 1.9 (2.8) | 6.7 (6.9) | 24.9 (26.0) | 0.5 |
| conv3 | eager | 2.6 (2.7) | 7.5 (8.1) | 27.7 (29.6) |  |
| conv3 | fold | 2.4 (2.7) | 7.0 (7.6) | 24.8 (25.6) |  |
| conv3 | fold+cl | 2.7 (2.8) | 8.4 (8.7) | 37.0 (38.2) |  |
| conv3 | inductor | 3.0 (3.9) | 9.3 (9.9) | 33.9 (34.3) | 0.5 |
| conv3 | fold+inductor | 3.1 (4.0) | 9.2 (9.5) | 33.5 (34.2) | 0.4 |
| conv3 | fold+cl+inductor | 3.1 (4.0) | 9.2 (9.9) | 33.3 (33.9) | 0.4 |
| conv3 | fold+cl+step | 2.3 (2.9) | 7.9 (8.4) | 30.0 (30.7) | 0.6 |
| inception3a | eager | 3.6 (4.2) | 9.4 (9.8) | 34.8 (36.9) |  |
| inception3a | fold | 3.1 (3.2) | 8.6 (8.9) | 31.4 (31.9) |  |
| inception3a | fold+cl | 3.6 (4.0) | 11.0 (11.4) | 46.5 (48.4) |  |
| inception3a | inductor | 3.6 (4.1) | 11.2 (11.9) | 41.0 (41.8) | 1.3 |
| inception3a | fold+inductor | 3.5 (3.8) | 11.2 (11.7) | 40.8 (41.3) | 0.9 |
| inception3a | fold+cl+inductor | 3.4 (3.9) | 11.1 (11.8) | 40.5 (41.0) | 0.8 |
| inception3a | fold+cl+step | 3.2 (5.1) | 10.1 (10.5) | 38.2 (38.7) | 1.0 |
| inception3b | eager | 4.6 (5.1) | 11.8 (12.2) | 42.8 (43.4) |  |
| inception3b | fold | 3.6 (4.1) | 10.5 (11.2) | 38.5 (39.1) |  |
| inception3b | fold+cl | 4.2 (4.8) | 13.4 (14.0) | 56.1 (57.6) |  |
| inception3b | inductor | 4.3 (5.6) | 13.6 (14.2) | 49.3 (49.7) | 1.8 |
| inception3b | fold+inductor | 4.3 (5.1) | 13.6 (14.0) | 49.1 (50.2) | 1.3 |
| inception3b | fold+cl+inductor | 4.2 (4.5) | 13.5 (15.2) | 48.8 (49.3) | 1.2 |
| inception3b | fold+cl+step | 3.7 (5.7) | 12.2 (12.5) | 45.7 (46.9) | 1.3 |
| inception4a | eager | 5.8 (6.8) | 13.1 (13.5) | 46.9 (47.3) |  |
| inception4a | fold | 4.1 (4.9) | 11.8 (12.4) | 42.5 (43.0) |  |
| inception4a | fold+cl | 4.9 (5.1) | 15.1 (15.7) | 61.6 (62.7) |  |
| inception4a | inductor | 4.8 (5.1) | 14.8 (15.2) | 53.4 (53.9) | 2.6 |
| inception4a | fold+inductor | 4.9 (5.0) | 15.1 (15.8) | 53.9 (54.8) | 1.8 |
| inception4a | fold+cl+inductor | 4.7 (4.9) | 14.8 (15.3) | 53.1 (53.8) | 1.6 |
| inception4a | fold+cl+step | 4.3 (5.1) | 14.0 (14.4) | 51.3 (51.9) | 1.9 |
| inception4b | eager | 7.2 (10.0) | 14.1 (14.6) | 50.1 (50.6) |  |
| inception4b | fold | 4.5 (5.2) | 12.7 (13.1) | 45.1 (45.6) |  |
| inception4b | fold+cl | 5.3 (5.8) | 16.3 (18.8) | 65.2 (65.8) |  |
| inception4b | inductor | 5.3 (5.7) | 16.2 (16.7) | 56.7 (57.2) | 3.3 |
| inception4b | fold+inductor | 5.4 (5.6) | 16.3 (16.7) | 57.3 (57.9) | 2.3 |
| inception4b | fold+cl+inductor | 5.1 (5.3) | 15.9 (16.7) | 56.3 (56.7) | 2.0 |
| inception4b | fold+cl+step | 4.8 (5.1) | 15.1 (15.5) | 54.6 (55.0) | 2.2 |
| inception4c | eager | 8.2 (8.7) | 15.1 (15.6) | 53.2 (55.3) |  |
| inception4c | fold | 5.1 (5.6) | 13.5 (14.0) | 47.9 (48.4) |  |
| inception4c | fold+cl | 5.8 (6.4) | 17.3 (17.9) | 68.7 (69.4) |  |
| inception4c | inductor | 5.8 (8.1) | 17.3 (17.7) | 60.0 (60.5) | 3.7 |
| inception4c | fold+inductor | 5.9 (6.3) | 17.5 (18.0) | 60.7 (61.3) | 2.5 |
| inception4c | fold+cl+inductor | 5.6 (6.0) | 17.0 (17.7) | 59.7 (60.3) | 2.2 |
| inception4c | fold+cl+step | 5.2 (5.8) | 16.3 (16.8) | 58.0 (58.6) | 2.5 |
| inception4d | eager | 9.4 (10.2) | 16.1 (16.5) | 56.2 (56.7) |  |
| inception4d | fold | 5.7 (6.4) | 14.5 (15.0) | 50.8 (51.4) |  |
| inception4d | fold+cl | 6.5 (8.5) | 18.6 (19.1) | 72.5 (74.3) |  |
| inception4d | inductor | 6.2 (7.0) | 18.5 (19.0) | 63.5 (64.1) | 4.4 |
| inception4d | fold+inductor | 6.4 (6.7) | 18.9 (19.4) | 64.4 (65.0) | 2.9 |
| inception4d | fold+cl+inductor | 6.0 (7.0) | 18.2 (18.9) | 63.3 (64.2) | 2.6 |
| inception4d | fold+cl+step | 5.6 (6.0) | 17.4 (21.1) | 61.4 (62.2) | 2.8 |
| inception4e | eager | 10.7 (11.5) | 17.4 (18.0) | 61.3 (63.8) |  |
| inception4e | fold | 6.4 (7.1) | 15.8 (16.1) | 54.8 (55.3) |  |
| inception4e | fold+cl | 7.3 (8.2) | 20.0 (20.4) | 77.3 (78.0) |  |
| inception4e | inductor | 6.8 (7.2) | 19.8 (20.4) | 68.0 (68.5) | 5.1 |
| inception4e | fold+inductor | 7.0 (7.5) | 20.5 (21.2) | 69.3 (71.2) | 3.4 |
| inception4e | fold+cl+inductor | 6.7 (7.5) | 19.6 (20.2) | 67.4 (68.8) | 2.9 |
| inception4e | fold+cl+step | 6.2 (6.9) | 18.9 (19.4) | 65.5 (67.4) | 3.1 |
| inception5a | eager | 12.1 (14.9) | 18.4 (19.2) | 62.6 (63.2) |  |
| inception5a | fold | 7.0 (7.7) | 16.6 (16.9) | 56.7 (57.2) |  |
| inception5a | fold+cl | 8.1 (9.1) | 21.0 (22.4) | 80.4 (81.2) |  |
| inception5a | inductor | 7.3 (8.2) | 20.9 (21.4) | 70.3 (70.8) | 5.6 |
| inception5a | fold+inductor | 7.5 (7.8) | 21.3 (21.8) | 71.8 (72.2) | 3.8 |
| inception5a | fold+cl+inductor | 7.1 (7.6) | 20.6 (20.7) | 69.9 (70.8) | 3.4 |
| inception5a | fold+cl+step | 6.7 (7.2) | 19.9 (20.5) | 68.4 (68.8) | 3.6 |
| inception5b | eager | 13.3 (14.1) | 19.1 (19.9) | 64.6 (65.0) |  |
| inception5b | fold | 7.5 (8.2) | 17.4 (17.7) | 58.6 (59.1) |  |
| inception5b | fold+cl | 9.1 (9.8) | 21.9 (22.3) | 82.6 (83.3) |  |
| inception5b | inductor | 7.9 (8.4) | 21.6 (21.9) | 72.6 (73.4) | 6.3 |
| inception5b | fold+inductor | 8.0 (8.8) | 22.2 (22.6) | 74.0 (75.2) | 4.3 |
| inception5b | fold+cl+inductor | 7.7 (8.7) | 21.4 (21.9) | 71.7 (72.5) | 3.7 |
| inception5b | fold+cl+step | 7.2 (7.7) | 20.8 (21.3) | 70.5 (72.3) | 3.9 |

## The fit: ms ≈ fixed + o × convs + p × megapixels + c × GMAC

fixed is per call; o per conv (launches: what folding and compiling should remove); p per megapixel whatever the layer (elementwise work and memory traffic: the floor at high resolution); c per billion multiply-adds.

| net | mode | precision | pass | fixed ms | o ms/conv | p ms/Mpx | c ms/GMAC | GMAC/s | worst miss ms | points |
|---|---|---|---|---|---|---|---|---|---|---|
| googlenet | eager | fp16 | step | 0.83 | 0.130 | 5.11 | 0.562 | 1781 | 2.48 | 36 |
| googlenet | eager | fp32 | step | 0.69 | 0.116 | 6.83 | 0.719 | 1391 | 2.83 | 36 |
| googlenet | fold | fp16 | step | 0.97 | 0.061 | 4.43 | 0.581 | 1722 | 1.95 | 36 |
| googlenet | fold | fp32 | step | 0.81 | 0.054 | 5.79 | 0.703 | 1422 | 2.11 | 36 |
| googlenet | fold+cl | fp16 | step | 0.27 | 0.060 | 6.31 | 0.833 | 1200 | 5.40 | 36 |
| googlenet | fold+cl | fp32 | step | 0.09 | 0.049 | 9.45 | 0.996 | 1004 | 6.17 | 36 |
| googlenet | fold+cl+inductor | fp16 | step | 0.89 | 0.056 | 5.87 | 0.741 | 1350 | 2.59 | 36 |
| googlenet | fold+cl+inductor | fp32 | step | 0.99 | 0.052 | 8.96 | 0.812 | 1231 | 2.58 | 36 |
| googlenet | fold+cl+step | fp16 | step | 0.29 | 0.061 | 5.21 | 0.764 | 1308 | 3.50 | 36 |
| googlenet | fold+cl+step | fp32 | step | 0.29 | 0.062 | 8.00 | 0.822 | 1217 | 3.45 | 36 |
| googlenet | fold+inductor | fp16 | step | 1.45 | 0.041 | 3.67 | 0.871 | 1149 | 1.96 | 36 |
| googlenet | fold+inductor | fp32 | step | 1.50 | 0.038 | 5.39 | 0.994 | 1006 | 3.43 | 36 |
| googlenet | inductor | fp16 | step | 1.37 | 0.046 | 4.06 | 0.844 | 1184 | 2.60 | 36 |
| googlenet | inductor | fp32 | step | 1.54 | 0.034 | 5.64 | 0.969 | 1032 | 3.86 | 36 |
