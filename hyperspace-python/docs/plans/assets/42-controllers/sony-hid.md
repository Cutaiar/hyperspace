# Sony DualSense / DualSense Edge: HID spec for the hidapi driver

Research note, 2026-11-01. Covers what a Python driver that uses the cython
`hidapi` package (`import hid`) needs in order to read and drive a DualSense (054C:0CE6)
and a DualSense Edge (054C:0DF2) over USB and Bluetooth on macOS. Nothing in it
has been checked against real hardware yet; §9 lists what only a controller can settle.

Confidence: **H** = two or more independent sources agree, or the source is the
device's own descriptor. **M** = one solid source, or sources that agree only partly.
**L** = a single community source, or an inference.

## 0. Sources (pinned)

| key | source | pin |
|---|---|---|
| K | Linux `drivers/hid/hid-playstation.c` | torvalds/linux `cbbddb6b08cc9900a87cccaa9b22bbe06aa4f50a` |
| Kids | Linux `drivers/hid/hid-ids.h` | same commit |
| Kp | proposed patch "HID: playstation: ignore DualSense Bluetooth microphone reports" (Du Yijie, 2026-10-26; reviewed, **not** in K) | https://ratatoskr.run/linux-input/2026/10/17805266 |
| KT | Linux `tools/testing/selftests/hid/tests/test_sony.py` | same commit as K |
| S | SDL `src/joystick/hidapi/SDL_hidapi_ps5.c` | libsdl-org/SDL `bd9f6ca9ff0e9509f49980fc1b70837f54b6f244` |
| Sr / St / Sc / Su | SDL `src/joystick/hidapi/SDL_hidapi_rumble.c` / `test/testcontroller.c` / `src/stdlib/SDL_crc32.c` / `src/joystick/usb_ids.h` | same commit |
| HT | hid-tools `hidtools/device/sony_gamepad.py` (descriptors and feature dumps of a real DualSense) | gitlab.freedesktop.org/libevdev/hid-tools `f4a32530ea548df2ae5efd2ebfd16d4c3e658875` |
| ER | DualSense **Edge** USB + BT report descriptors (`/sys/kernel/debug/hid/*/rdesc`), attached to a linux-input bug report, 2026-05-27 | https://ratatoskr.run/linux-input/2026/05/17034585 (`/attachment/0` USB, `/attachment/1` BT) |
| F | controllers.fandom wiki `Sony_DualSense/Data_Structures`; line numbers are lines of the page's wikitext | revid 602 (2026-07-07) |
| N | Nielk1, DualSense trigger-effect generator gist, "Revision 6" | gist `6d54cc2c00d2201ccb8c2720ad7538db` @ `f73a299fdc52f43be84d39e62734192ad82bb393` |
| D | dualsensectl `main.c` (uses hidapi) | nowrep/dualsensectl `d3ae2fa272e1bf9a5c08a0ded3f374b40f7c73ac` |
| CY | cython-hidapi 0.15.0, the latest release on PyPI (uploaded 2025-12-09): `hid.pyx`, `chid.pxd`, and the macOS arm64 cp313 wheel | trezor/cython-hidapi tag `0.15.0` = `0b5671548f20d4e2cb4bbb95b7821839da5de146` |
| H | hidapi 0.15.0 `mac/hid.c` as vendored in the CY sdist (`hidapi-0.15.0.tar.gz`) | (upstream libusb/hidapi `852cc68b` behaves the same: line 476) |

## 1. Identification

| fact | source | conf |
|---|---|---|
| VID 0x054C; PID 0x0CE6 = DualSense, 0x0DF2 = Edge | Kids:1368-1369; Su:180-181 | H |
| Edge is told apart **by PID only** (K sets `is_edge` and vibration v2; S checks the PID) | K:1804-1809; S:443, 562, 983 | H |
| Bus: `hid.enumerate()` dicts carry `bus_type` (1 = USB, 2 = BT) | CY hid.pyx:71, chid.pxd (`hid_bus_type`) | H |
| SDL also infers USB when the first input read is 64 bytes, and "BT, enhanced" when it is report 0x31 | S:405-423 | H |

## 2. Input reports

### 2.1 Framing

| mode | ID | bytes incl. ID | payload `p0` at | trailer | source | conf |
|---|---|---|---|---|---|---|
| USB | 0x01 | 64 | byte 1 | none | K:81-82, 1453-1455; S:1608-1614 | H |
| BT simple | 0x01 | 10 | byte 1 (own layout, §2.3) | none | HT:1684-1730 (descriptor); ER BT; S:72-81, 1609 | H |
| BT full | 0x31 | 78 | byte 2 | bytes 74-77 = CRC32 LE of `0xA1 ‖ bytes[0:74]` | K:77, 83-84, 743-751, 1456-1466; S:1530-1543, 1619-1625; HT:1915 | H |

- **BT byte 1:** the low nibble is a tag (1 = HID input data, 2 = microphone data) and the high nibble is a sequence number (Kp; F:1323-1327 calls them `HasHID` = bit 0, `HasMic` = bit 1, `SeqNo` = high nibble). K master does not check this byte yet; Kp adds the check. Drop any report whose tag is not 1. **M**
- SDL also parses a report 0x01 that is 78 bytes long with the simple layout (S:1609-1610). **M**
- The Edge declares exactly the same input report 1 as the DualSense on both buses. Its BT descriptor ends in one stray `0x00` byte after End Collection (ER message; ER attachment 1, line 1). **H**

### 2.2 Full report payload (USB absolute byte = p+1; BT absolute byte = p+2)

| p | field | encoding | source | conf |
|---|---|---|---|---|
| 0-3 | LX, LY, RX, RY | u8, centre ≈ 0x80; 0 = left/up | K:246-248; S:85-90; F:1217-1220 | H |
| 4, 5 | L2, R2 analog | u8 0-255 (K names them `z`, `rz`) | K:248; S:89-90; F:1221-1222 | H |
| 6 | counter | u8 (K `seq_number`; F "always 0x01 on BT") | K:249; F:1223 | M |
| 7 | hat + face | bits 0-3 hat: 0 N, 1 NE, 2 E, 3 SE, 4 S, 5 SW, 6 W, 7 NW, ≥ 8 released · 0x10 □ · 0x20 × · 0x40 ○ · 0x80 △ | K:98-102, 579-582; S:1260-1300; F:1224-1228 | H |
| 8 | 0x01 L1 · 0x02 R1 · 0x04 L2 digital · 0x08 R2 digital · 0x10 Create · 0x20 Options · 0x40 L3 · 0x80 R3 | | K:103-110; S:1306-1315; F:1229-1236 | H |
| 9 | 0x01 PS · 0x02 touchpad click · 0x04 mic mute · 0x08 unused · **Edge:** 0x10 left Fn · 0x20 right Fn · 0x40 left back button · 0x80 right back button | Edge bits 3-7 fall inside vendor field `ff00:0021` (bit offset 75, 13 bits) in the Edge USB descriptor | K:111-119, 1499-1508; S:1317-1326; F:1237-1244; ER USB | H |
| 10 | unknown ("appears unused") | | F:1245 | L |
| 11-14 | u32 LE packet sequence/counter (K: reserved) | | S:93; F:1246 | M |
| 15-20 | gyro, 3 × s16 LE, raw (calibrate with §4.2) | K and S name them x, y, z = pitch, yaw, roll; **F names them X, Z, Y** | K:254, 1555-1562; S:94-96, 640-647; F:1247-1249 | H layout / **M** axis names |
| 21-26 | accel X, Y, Z, 3 × s16 LE, raw | | K:255, 1564-1572; S:97-99; F:1250-1252 | H |
| 27-30 | sensor timestamp, u32 LE, in units of 0.33 µs | | K:256, 1574-1588; S:121, 1384; F:1253 | H |
| 31 | temperature s8 (K: reserved) | | S:122; F:1254 | M |
| 32-35 | touch point 0 | byte 0: bit 7 = 1 means **inactive**, bits 0-6 = contact id · x = b1 \| (b2 & 0x0F) << 8 · y = (b2 >> 4) \| b3 << 4 (12 bits each) | K:139-147, 236-242, 260, 1592-1606; S:123-126, 1405-1416; F:1178-1189; HT:1544-1557 | H |
| 36-39 | touch point 1 | same encoding | same | H |
| 40 | touch timestamp/counter u8 (HT comment: one count = 682.7 µs) | **conflict:** F and HT's comment place it at +8 from the touch block (p40); HT's code writes it at +16 (HT:1414); K and S leave it unnamed | F:1185-1189; HT:1551 | L |
| 41 / 42 | right / left trigger: bits 0-3 stop location, bits 4-7 status | | F:1256-1259 only | L |
| 43-46 | host timestamp echoed back from the output report | | F:1266 only | L |
| 47 | bits 0-3 right, bits 4-7 left active trigger effect | | F:1267-1268 only | L |
| 48-51 | device timestamp u32 | | S:128; F:1272 | M |
| 52 | battery | bits 0-3 level 0-10 (K reports min(n×10+5, 100) %) · bits 4-7 state: 0 discharging, 1 charging, 2 full, 0xA voltage/temperature out of range, 0xB temperature error, 0xF charging error | K:122-123, 263, 1610-1641; S:129; HT:1505-1530; F:16-23, 1273-1274 | H |
| 53 | 0x01 headphones plugged · 0x02 mic plugged · 0x04 mic muted · 0x08 USB data · 0x10 USB power · 0x20 USB power while on BT | K has bits 0-2; S: "0x08 = USB, 0x01 = headphone" | K:124-127; S:130; F:1275-1282 | H bits 0-2 / M rest |
| 54 | 0x01 external mic active · 0x02 haptic low-pass filter active | | F:1283-1285 | L |
| 55-62 | K reserved; F: AES-CMAC | | F:1286 | L |
| 63-71 | BT only: reserved | | Kp `reserved[9]`; F:1291-1297 | L |

SDL quirk: when an analog trigger reads 0 but its digital bit is set, SDL reports the trigger fully pressed (S:1329-1340). Its purpose isn't documented; it may be a fix for third-party pads. **L**

### 2.3 BT simple report 0x01 (10 bytes, absolute offsets)

`[0]=0x01 [1]LX [2]LY [3]RX [4]RY [5]` hat + face (as p7) `[6]` same as p8 `[7]` 0x01 PS, 0x02 touchpad click, bits 2-7 = counter (F) / constant (descriptor) `[8]L2 [9]R2`.
There is no mic button, no Edge Fn/back bits, no touch and no motion data.
Sources: HT:1684-1730; ER BT (identical on the Edge); S:72-81, 1163-1240; F:1190-1214. **H**
F labels the PS and touchpad bits "6.1/6.2". The descriptor and S put them at bits 6.0/6.1.

### 2.4 Mode switch, rates

- BT starts in simple mode. It switches to 0x31 **for the rest of the connection** after any of: a feature read of 0x05 (F:1491), of 0x09 or 0x20 (S:425-439), or any 0x31 output report (S:826, 871-883). S: "enhanced mode is a one-way ticket" (S:890). USB always sends the full 0x01 report. **H**
- Rates SDL assumes for the sensors: 250 Hz on USB (DualSense), about 1000 Hz on BT, 1000 Hz on USB for the Edge (S:846-855). **M**

### 2.5 Touchpad range

K uses 1920 × 1080 (K:177-178). S scales x by 1/1920 and **y by 1/1070** (S:1402-1403). They disagree on Y; clamp, and measure on the device (§9). **M**

## 3. Read path on macOS (cython hidapi 0.15.0)

| fact | source | conf |
|---|---|---|
| `read(n, timeout_ms)` returns one report as delivered by IOKit, report-ID byte first; it is truncated to `n` bytes, so use n ≥ 78 | H:1195-1206; S relies on `data[0]` being the ID (S:1606-1619) | H |
| hidapi buffers at most **30** input reports and drops the oldest past that; at 250-1000 Hz, drain with non-blocking reads every frame and keep the last report | H:908-911 | H |
| `hid_init()` runs at `import hid` and makes opens **exclusive** (`kIOHIDOptionsTypeSeizeDevice`) | CY hid.pyx:11; H:473 | H |
| CY 0.15.0 wraps no `hid_darwin_*` function (none in `hid.pyx` or `chid.pxd`), but the macOS arm64 wheel's `hid.cpython-313-darwin.so` exports `_hid_darwin_set_open_exclusive` as a global (`llvm-nm`: `T`). So `ctypes.CDLL(hid.__file__).hid_darwin_set_open_exclusive(0)` after import and before `open()` should work | CY; H:1535-1538 | M (not tried on a Mac) |
| An exclusive open starves GLFW and the GameController framework of that pad. Any BT read/write that flips the pad to 0x31 also freezes GLFW's raw joystick values for it | H:1059; earlier report | M |

## 4. Feature reports

Read with `get_feature_report(id, 64)`. It sets `buf[0] = id` and returns the bytes **including** the ID (CY hid.pyx:351-380; H:1143-1186). SDL also reads into a 64-byte buffer (S:289-293).
**Over BT the last 4 bytes are a CRC32 LE of `0xA3 ‖ bytes[0:n-4]`. USB has no CRC** (K:79, 799-832; HT:1831-1840, 1918-1926). **H**

### 4.1 0x05 calibration: 41 bytes (40 on the wire + ID), all fields s16 LE

| off | field | off | field |
|---|---|---|---|
| 1 | gyro pitch bias | 19 | gyro speed + |
| 3 | gyro yaw bias | 21 | gyro speed − |
| 5 | gyro roll bias | 23 / 25 | accel X + / X − |
| 7 / 9 | pitch + / pitch − | 27 / 29 | accel Y + / Y − |
| 11 / 13 | yaw + / yaw − | 31 / 33 | accel Z + / Z − |
| 15 / 17 | roll + / roll − | 35 | unknown (F) · 37-40 = BT CRC |

Sources: K:1050-1066; S:618-634; F:1538-1560. **H**

| quantity | formula | source | conf |
|---|---|---|---|
| gyro deg/s | `(raw − b) × (speed+ + speed−) / D` | K:1068-1089, 1555-1562; S:639-647, 682-694 | H formula |
| — SDL | b = bias, D = plus − minus | S:639-647 | |
| — Linux | **b = 0** (bias explicitly zeroed), D = \|plus − bias\| + \|minus − bias\| (equals plus − minus whenever minus < bias < plus) | K:1074, 1080, 1086 (bias = 0); K:1076-1089 (denominators) | **disagreement on subtracting the bias** (≤ 0.9 deg/s for the §8 sample) |
| accel g | `(raw − b) × 2 / R`, R = plus − minus, b = plus − R/2 (C integer division) | K:1107-1127, 1564-1572; S:649-659 | H |
| what 1024 / 8192 are | K's **output** units (values normalised to 1/1024 deg/s and 1/8192 g, K:173-176), also S's intermediate constants (S:42-43). They are **not** the raw resolution. The §8 sample gives about 16.4 raw LSB per deg/s and about 8190 LSB per g | K; S; §8 | H |
| no calibration | S falls back to gyro deg/s = raw × 64 / 1024 and accel g = raw / 8192. S rejects a calibration whose \|bias\| > 1024 or whose sensitivity is more than 50 % off 64 (gyro) / 1 (accel). K replaces a zero denominator | S:662-690; K:1096-1105, 1134-1143 | H |

### 4.2 0x09 pairing info (20 bytes)

Bytes 1-6 are the controller MAC, **little-endian** (reverse it to display). F adds: bytes 7-9 constant `08 25 00`, bytes 10-15 the host MAC. BT CRC at 16-19.
Sources: K:1183-1205; S:427-431; F:1580-1589; HT:1926. **H** for the controller MAC, **L** for the host MAC.

### 4.3 0x20 firmware info (64 bytes)

| bytes | field |
|---|---|
| 1-11 | build date (ASCII) |
| 12-19 | build time (ASCII) |
| 20 | u16 firmware type |
| 22 | u16 software series |
| 24 | u32 hardware version |
| 28 | u32 firmware version |
| 32-43 | device info |
| 44 | u16 update ("feature") version |
| 60-63 | BT CRC |

Sources: K:1150-1180; S:433-439; F:1604-1625. **H** for offsets 24, 28 and 44; **M** for the rest.

K's comment: the update version "is different between DualSense and DualSense Edge" (K:1168-1175).

Which rumble mode to use (key off offset 44):
- K uses v2 if the PID is 0x0DF2 or the update version is ≥ `0x0215` ("2.21") (K:1800-1809).
- S uses v2 if the PID is 0x0DF2, the version is 0 (BT, unknown), or the version is ≥ **`0x0224`** (S:441-447).
- **The thresholds disagree.** Both always use v2 on an Edge. **H** for the Edge.

### 4.4 Other feature IDs: leave them alone

- 0x03 capabilities: S uses it only for third-party pads (S:301-317).
- 0x08 BT control and 0x0A set-pairing are documented in F; avoid them.
- The Edge USB descriptor adds undocumented features 0x0B, 0x0C, 0x60-0x7B, 0xF4 and 0xF5, and 0xF2 is 52 bytes (15 on the DualSense) (ER USB line 1).

## 5. Output report

### 5.1 Framing

| | layout | source | conf |
|---|---|---|---|
| USB | `[0]=0x02`, then the 47-byte common block at byte 1 | K:85, 311-316; S:1096-1100 | H |
| USB length | **S sends 48. K and D send 63.** The DualSense descriptor declares 47 data bytes (48 total); the **Edge descriptor declares 63 (64 total)** | S:1099; K:86; D:41; HT USB descriptor ("Report ID (2) … Report Count (47)"); ER USB (`85 02 09 23 95 3f 91 02`) | M (§9) |
| BT | 78 bytes: `[0]=0x31`, `[1]` = seq << 4 \| tag(0), `[2]=0x10`, `[3..49]` common block, `[50..73]` = 0, `[74..77]` = CRC32 LE of `0xA2 ‖ bytes[0:74]` | K:78, 150-152, 301-309, 1251-1320; S:1089-1111; D:204-214, 285-333 | H |
| BT byte 2 | `0x10`: K "Tag must be set. Exact meaning is unclear."; S "Magic value". **F's `ReportOut31` drops this byte and starts the block at byte 2**, which contradicts K, S and D | K:1261; S:1092; F:1471-1485 | H (K, S, D) |
| BT sequence | K and D increment the high nibble of byte 1 (0-15) on every report; **S always sends 0x00**. Both ship, so the firmware apparently doesn't enforce it | K:1263-1270; D:297-299; S:1091 | M |
| CRC in Python | `zlib.crc32(b"\xa2" + buf[:74]) & 0xFFFFFFFF`, packed `<I`. This equals K's `~crc32_le(crc32_le(~0, seed), …)` and SDL_crc32 (equality checked with a local script; Sc:39-56). S's comment: the CRC is needed "at least on Linux"; send it on every OS | K:1308-1317; HT:1831-1840; S:1106 | H |
| write call | `dev.write(buf)` with the ID in byte 0 → `hid_write` → `IOHIDDeviceSetReport(Output, reportID = buf[0], whole buffer including ID)`. S and D use `hid_write` on both buses. **Not** `send_feature_report` | H:1101-1140, 1189-1192; Sr:84; D:333 | H |

### 5.2 The 47-byte common block (offset c; USB absolute = c+1, BT absolute = c+3)

| c | field | values | source | conf |
|---|---|---|---|---|
| 0 | flags0 | 0x01 rumble emulation v1 · 0x02 haptics select ("disable audio haptics"; set whenever sending rumble) · 0x04 right-trigger effect · 0x08 left-trigger effect · 0x10 headphone volume · 0x20 speaker volume · 0x40 mic volume · 0x80 audio control | K:154-158, 1332-1338; S:724, 730; D:62-69; St:491, 535; F:1339-1349 | H |
| 1 | flags1 | 0x01 mic-mute LED · 0x02 power-save/mute byte · 0x04 lightbar RGB · 0x08 release/reset LEDs (K defines it but never uses it; S uses it) · 0x10 player LEDs · 0x20 haptic low-pass filter · 0x40 motor power reduction · 0x80 audio control 2 | K:159-164; S:744-771; D:71-78; F:1350-1364 | H bits 0-4, 7 / M bits 5-6 |
| 2 | rumble "right" = **high-frequency / weak** motor | u8 | K:275, 1660; S:1019, 720; F:1366 | H |
| 3 | rumble "left" = **low-frequency / strong** motor | u8. In v1 mode S halves it ("to match Xbox"); F: "suggest halving" | K:276, 1659; S:1018, 721-727; F:1367 | H |
| 4 | headphone volume | 0-0x7F | K:279; D:170; F:1369 | M |
| 5 | speaker volume | K: 0-0xFF, "accepted range seems to be [0x3d..0x64]" | K:280, 1387-1389 | M |
| 6 | mic volume | 0-0x40 | K:281; D:172 | M |
| 7 | audio control | bits 0-1 mic select · 0x04 echo cancel · 0x08 noise cancel · bits 4-5 output path (0 L-R-X = headphones, 1 L-L-X, 2 L-L-R, 3 X-X-R = speaker) · bits 6-7 input path | K:167, 1366-1384; D:95-100; F:1374-1388; St:494-510 | M |
| 8 | mic-mute LED | 0 off, 1 on, 2 breathing/pulse (K only writes 0/1) | F:25-35; S:773; K:283, 1414 | M |
| 9 | power-save/mute | 0x01 touch · 0x02 motion · 0x04 haptics · 0x08 audio power-save · 0x10 mic mute · 0x20 speaker mute · 0x40 headphone mute · 0x80 haptics mute | D:83-90; F:1392-1399; K:169 (bit 4) | M. Don't set 0x02 (it presumably stops the IMU; inference, L) |
| 10-20 | **right**-trigger effect (11 bytes) | §6 | S:176; St:468, 536; D:179-180; F:1401 | H |
| 21-31 | **left**-trigger effect (11 bytes) | §6 | S:177; St:469, 537; D:183-184; F:1402 | H |
| 32-35 | host timestamp (K: reserved) | | D:186; F:1403 | L |
| 36 | motor power reduction | low part rumble, high part triggers. **F: 4 bits each (0-F / 0-A); D masks 3 bits each** | F:1406-1407; D:788 | L |
| 37 | audio control 2 | bits 0-2 speaker pre-gain (K sets 2 = +6 dB) | K:168, 287, 1396-1398; F:1410 | M |
| 38 | flags2 | 0x01 LED brightness · 0x02 lightbar setup · 0x04 **vibration v2 / "improved rumble"** (use it instead of flags0 0x01; needs §4.3) · 0x08 F "UseRumbleNotHaptics2" (L) | K:165-166, 290, 1335-1336; S:179, 719; D:80-82; F:1414-1419 | H bits 1-2 / M bit 0 |
| 39 | 0x01 haptic low-pass filter | | D:193; F:1422 | L |
| 41 | lightbar setup | 0x01 light on (fade in), 0x02 light out (fade out) | K:170, 292; D:91-92; F:48-52, 1427 | H |
| 42 | LED brightness | 0 bright, 1 mid, 2 dim (K never sets it) | F:37-46, 1428; K:293 | L |
| 43 | player LEDs | bits 0-4 LEDs left to right; **0x20 = change instantly** (otherwise fade) | S:365-370; F:1445-1450; K:294 | H |
| 44-46 | lightbar R, G, B | u8 | K:295-297; S:184-186 | H |

- **Player LED patterns:** P1 0x04, **P2 0x0A** (S and K; F says 0x06, which contradicts F's own diagram), P3 0x15, P4 0x1B, P5 0x1F (S:356-364; K:1722-1728; F:1438-1442). F also says hardware generation 0x04 mirrors the LEDs (F:1430-1436).
- **No Edge-specific output bits** were found in K, S, D or F. The Edge differs only by always using vibration v2 (K:1807-1809; S:443) and by the USB report length above.

### 5.3 Connect and take-over sequence

1. **K, on both buses:** at probe, send one report with flags2 = 0x02 and c41 = 0x02 (fade out), "before we can do any programming later on". Then lightbar (0, 0, 128) and the player LEDs (K:1677-1700, 1870-1896). **H** (for Linux)
2. **S, on BT:** hold back LED and player-LED writes until the sensor timestamp (p27) ≥ 10 200 000 (× 0.33 µs ≈ 3.4 s after connect), then send flags1 0x08 (reset LEDs), then LED + player LEDs (S:705-712, 779-806). F: reset "cannot be applied during the BT pair animation" (F:1355-1360). **M**
3. **Rumble:** flags0 0x02, plus flags2 0x04 (v2) or flags0 0x01 (v1), plus c2/c3 (K:1332-1340; S:715-731). **H**

K and S use two different take-over mechanisms (steps 1 and 2) and both ship. Plan: do step 1; if the LEDs ignore later writes over BT, add step 2 (§9).

## 6. Adaptive-trigger effects (11 bytes: `[0]` mode, `[1..10]` parameters; zero-fill unused bytes)

| mode | name | packing | ranges | status / source |
|---|---|---|---|---|
| 0x05 | Off | all parameters 0 | — | official, "100% safe" (N:36-41, 139-155; D:835-838; St:525) |
| 0x21 | Feedback (zoned resistance) | `[1..2]` u16 LE active-zone mask (bit i = zone i of 10) · `[3..6]` u32 LE 3 bits per zone = strength − 1 | single form: position 0-9, strength 1-8, zones position..9 | official (N:165-200; D:840-883) |
| 0x25 | Weapon | `[1..2]` u16 LE = (1 << start) \| (1 << end) · `[3]` = strength − 1 | start 2-7, end start+1..8, strength 1-8 | official (N:210-240; D:885-906) |
| 0x26 | Vibration | `[1..2]` zone mask as 0x21 · `[3..6]` amplitude − 1, 3 bits per zone · `[9]` frequency in Hz | position 0-9, amplitude 1-8, frequency > 0 | official (N:250-285; D:1006-1026) |
| 0x22 / 0x23 / 0x27 | Bow / Galloping / Machine | see N:427-560 | — | unofficial, "might be removed" (N:43-48). Don't use |
| 0x01 | Simple_Feedback | `[1]` position, `[2]` strength (raw bytes, no documented range) | — | legacy, "should not be used" (N:50-53, 560-588). **SDL's own test sends `01 00 6E`** (St:527) |
| 0x02 | Simple_Weapon | `[1]` start, `[2]` end, `[3]` strength | — | legacy (N:602-616) |
| 0x06 | Simple_Vibration | `[1]` frequency, `[2]` amplitude, `[3]` position | — | legacy (N:631-650). **SDL's test sends `06 0F 3F 80`** (St:529) |
| 0x11 / 0x12 | Limited Feedback / Weapon | as the simple forms, with range checks | — | "should not be used" (N:55-58, 665-725) |
| **0xFC / 0xFD / 0xFE** | debug / calibration | — | — | **Never send:** "will corrupt the trigger state until the reset button is pressed" (N:60-64) |

- Rule from N: a strength or amplitude of 0 → send Off instead (N:122-127). Set flags0 0x04 / 0x08 for the side(s) you write.
- No source found claims any mode can physically damage the controller. The only explicit warning is the 0xFC-0xFE one.
- No Edge-specific trigger encodings were found.

## 7. Write cadence and BT behaviour

| fact | source | conf |
|---|---|---|
| S serialises all output writes on one thread and sleeps **10 ms after each `hid_write`** (so ≤ ~100 writes/s). A queued request for the same device, size and report ID is overwritten in place | Sr:64-93, 263-266; S:1118-1131 | H |
| K writes from a workqueue and coalesces updates; there is no explicit rate limit | K:1290-1296, 1322-1434 | H |
| Any 0x31 output switches BT input to 0x31 ("We can't even send an invalid effects packet, or it will put the controller in enhanced mode") | S:826 | M |
| S keepalive: after 500 ms with no input on BT, it sends a dummy 0x31 with `[1]=0x02` and **no CRC** to "tickle" the link | S:44, 809-829, 1641-1647 | M |
| Plan: send only on change, coalesce to ≤ 100 Hz, and keep the sequence nibble incrementing (K/D behaviour) | derived | — |

## 8. Test vectors

**Real bytes from hardware dumps** (taken from HT):

- **0x05 calibration** (HT:1605-1610, 41 bytes):
  `05 ff ff f2 ff 04 00 9d 22 5e dd 92 22 52 dd ba 22 51 dd 1c 02 1c 02 fb 1f 05 e0 83 1f 99 df 07 20 fc df 05 00 00 00 00 00`
  - Expected under K's decode, as asserted by KT:306-315 and HT:1450-1459:
    - gyro numerator 1 105 920 (= 1080 × 1024) on all axes; denominators 17727 / 17728 / 17769.
    - accel bias 0 / −114 / 2; numerator 16384; denominators 16374 / 16362 / 16395.
  - Recomputed locally from the bytes: matches.
  - Raw fields: biases −1 / −14 / 4; pitch ± 8861 / −8866; speed ± 540.
  - So the gyro is 0.060924 / 0.060921 / 0.060780 deg/s per LSB.
  - The bytes at 37-40 are zero, so this dump is the USB (no-CRC) form.
- **0x20 firmware info** (HT:1629-1636, 64 bytes):
  `20 41 75 67 20 31 38 20 32 30 32 30 30 36 3a 32 30 3a 32 39 03 00 04 00 13 03 00 00 1e 00 00 01 41 0a 00 00 00 00 00 00 00 00 00 00 04 02 00 00 2a 00 01 00 06 00 01 00 06 00 00 00 98 d8 b3 b7`
  - Bytes 60-63 `98 d8 b3 b7` = CRC32(`0xA3 ‖ bytes[0:60]`), recomputed locally: a **real BT feature-report CRC vector**.
  - Decodes to "Aug 18 2020" "06:20:29", hw 0x00000313, fw 0x0100001E, update version 0x0204 (below both rumble-v2 thresholds).
- HT's 0x09 report uses a random MAC; it is not a vector.

**No public real input-report capture was found.** HT and KT build input reports from the descriptor (HT:1842-1917), and SDL ships no DualSense packet data. The vectors below were **computed from this spec** with zlib; they only test framing and CRC code:

| vector | bytes (hex) | CRC32 |
|---|---|---|
| BT 0x31 input: sticks centred, hat released, both touch points inactive, **Edge right back button held**, `[1]=0x01` | `31 01 80 80 80 80 00 00 00 08 00 80` + 22×`00` + `80 00 00 00 80` + 35×`00` + `43 70 11 35` | 0x35117043 (seed 0xA1) |
| USB 0x01, same payload | `01 80 80 80 80 00 00 00 08 00 80` + 22×`00` + `80 00 00 00 80` + 26×`00` (64 bytes) | none |
| BT 0x31 output, K's reset-LEDs step, seq 0 | `31 00 10`, byte 41 = `02` (flags2), byte 44 = `02` (setup), all else 0, then `43 e6 31 36` | 0x3631E643 (seed 0xA2) |
| BT 0x31 output, lightbar (0, 0, 128), seq 1 | `31 10 10`, byte 4 = `04` (flags1), byte 49 = `80` (blue), all else 0, then `42 23 ea 4c` | 0x4CEA2342 (seed 0xA2) |

## 9. Open: needs a real controller

1. Which USB output length macOS IOKit accepts for an **Edge** (descriptor 64 vs SDL's 48), and whether a 63-byte write (K/D) is rejected.
2. Touchpad Y maximum (1070 vs 1080), the gyro axis order (F vs K/S), and where the touch timestamp sits (p40?).
3. Whether `hid_darwin_set_open_exclusive(0)` via ctypes on the CY wheel takes effect, and whether macOS's GameController framework also writes LEDs and fights ours.
4. On BT, which LED take-over (K's 0x02 setup or S's flags1 0x08 after ~3.4 s) is needed on macOS.
5. Whether the stray trailing 0x00 in the Edge BT descriptor upsets IOKit.
6. The meaning of the BT input tag values other than 1 and 2, and whether microphone (tag 2) reports ever appear without our asking.
7. Edge firmware's update version (§4.3) and whether it matters for anything beyond rumble.

## 10. Answered by the hardware (2026-11-02)

An Edge, update version 0x0217, on macOS, through `tools/hid_probe.py
--check` over USB and Bluetooth ([`edge-usb.json`](edge-usb.json),
[`edge-bt.json`](edge-bt.json)): §9 1 — 64 bytes, at once; §9 2 — Y max
1079 (1080 high), the axes as K/S name them; §9 3 — opened exclusively,
nothing fought it; §9 4 — K's take-over is enough over Bluetooth; §9 5 —
IOKit took the BT descriptor; §9 6 — only tag 1 seen (20 162 reports);
§9 7 — 0x0217. Bluetooth paces input at about 64 reports a second, evenly,
where §2.4 assumed far more. Fn held hides the face buttons.

