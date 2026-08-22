# **Real-Time 4D Visualizer Architecture Specification**

**Target System:** Custom ZGameEditor Visualizer (FL Studio) \+ Pro DJ Link \+ IMU UDP Bridge

**Purpose:** High-performance, multi-parameter, 4D shape visualizer driven by live DJ performance metadata, transient audio processing, and handheld IMU sensors.

## **1\. System Overview & Core Data Flow**

The system orchestrates three primary external data pipelines (IMU orientation, Pro DJ Link metadata, and uncompressed live master audio) into FL Studio to drive a custom 4D (![][image1]) GLSL raymarcher/projection engine running inside ZGameEditor Visualizer (ZGEV).

┌────────────────────────────────────────────────────────────────────────────────────────┐  
│                                     DJ BOOTH                                           │  
│                                                                                        │  
│  \[ CDJ-3000s / XDJ-AZ \+ DJM Mixer \]                                                    │  
│    ├── Pro DJ Link (Ethernet UDP) ────────┐                                            │  
│    └── Master 2 / Booth Out (Analog) ─────┼─────────┐                                  │  
│                                           │         │                                  │  
│  \[ ESP32 IMU Sensors \]                    │         │                                  │  
│    └── Motion Data (UDP Broadcast) ───────┼──┐      │                                  │  
└───────────────────────────────────────────┼──┼──────┼──────────────────────────────────┘  
                                            │  │      │  
                                            │  │      │  CAT6 / Network Runs  
                                            ▼  ▼      ▼  
┌────────────────────────────────────────────────────────────────────────────────────────┐  
│                                VISUALIZER ENGINE (PC)                                  │  
│                                                                                        │  
│  ┌─────────────────────────────┐  ┌─────────────────────────┐  ┌────────────────────┐  │  
│  │    Beat-Link-Trigger        │  │   Python UDP Bridge     │  │ Audio Interface In │  │  
│  │   (Pro DJ Link Parser)      │  │  (IMU Socket Listener)  │  │   (ASIO Buffer)    │  │  
│  └──────────────┬──────────────┘  └────────────┬────────────┘  └─────────┬──────────┘  │  
│                 │                              │                         │             │  
│                 │ Virtual MIDI                 │ Virtual MIDI            │ ASIO Audio  │  
│                 │ (loopMIDI Port 1\)            │ (loopMIDI Port 2\)       │ Stream      │  
│                 ▼                              ▼                         ▼             │  
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │  
│  │                                 FL STUDIO DAW                                    │  │  
│  │                                                                                  │  │  
│  │  \[ Internal Routing & Processing \]                                               │  │  
│  │  ├── MIDI CC Beat Phase & Dynamic Tempo ───────────────────────┐                 │  │  
│  │  ├── MIDI CC 14-bit IMU Plane Steering ────────────────────────┼────────┐        │  │  
│  │  └── Fruity Peak Controller (Sub-Bass Transients) ─────────────┼───┐    │        │  │  
│  │                                                                ▼   ▼    ▼        │  │  
│  │  \[ ZGameEditor Visualizer Plugin \]                                               │  │  
│  │   └── Custom 4D Shader (.zgeproj) ──────────────────────────────────────────────┘  │  │  
│  └──────────────────────────────────────────────────────────────────────────────────┘  │  
└────────────────────────────────────────────────────────────────────────────────────────┘

## **2\. Subsystem Specifications**

### **2.1 Subsystem A: 4D Custom Renderer (ZGameEditor / GLSL)**

* **Framework:** ZGameEditor Visualizer (ZGEV) using .zgeproj XML container structure.  
* **Math Model:** Stereographic / Perspective 4D-to-3D projection of hypergeometries (![][image1] rotation group across 6 orthogonal planar pairs: ![][image2]).  
* **Uniform Inputs:**  
  * uniform float u\_RotSpeedXY, u\_RotSpeedXZ, u\_RotSpeedXW, u\_RotSpeedYZ, u\_RotSpeedYW, u\_RotSpeedZW (Range: \-1.0 to 1.0 mapped from 0.0 to 1.0 normalized FL Studio parameters).  
  * uniform float u\_BeatPhase (0.0–1.0 continuous normalized bar phase from Pro DJ Link).  
  * uniform float u\_AudioTransient (Sub-bass peak intensity for 4D hyper-surface displacement).  
  * uniform float u\_SliceW (Hyperplane slicing depth ![][image3]\-offset).

### **2.2 Subsystem B: Pro DJ Link Metadata Integration**

* **Protocol:** Pro DJ Link UDP broadcast packet sniffing over Local Network / Ethernet.  
* **Parsing Software:** Beat-Link-Trigger running headless or minimized on the Visualizer PC.  
* **Extracted Attributes:**  
  * Master Deck BPM and Playhead Position.  
  * Beat Grid Phase (Quarter-note beat triggers & bar boundaries).  
  * Channel On-Air status and Fader positions.  
* **Output Path:** Virtual MIDI Port (loopMIDI / macOS IAC Driver) emitting MIDI CC phase envelopes and tempo sync.

### **2.3 Subsystem C: IMU Sensor Network**

* **Hardware:** ESP32 microcontrollers paired with BNO055 / MPU6050 IMUs.  
* **Transmission Protocol:** Low-latency Wi-Fi / Ethernet UDP broadcast containing 3-axis Euler angles or Quaternions (struct { float roll, pitch, yaw; }).  
* **Bridge Component:** Standalone Python daemon using socket and mido / python-rtmidi.  
* **Processing:** Unpacks UDP payloads, normalizes values, and outputs 14-bit high-resolution MIDI CC pairs (MSB/LSB) to prevent parameter stepping during 4D steering.

### **2.4 Subsystem D: Audio Pipeline**

* **Source:** DJM Mixer / XDJ-AZ **Booth Out** (Balanced 1/4" TRS / XLR) or **Master 2** (RCA).  
* **Transport:** \* *Primary Recommendation:* Passive RJ45-to-XLR Audio Snake over CAT6 cable (0.0 ms latency).  
  * *Alternative:* 5.8 GHz uncompressed RF stereo transceiver (3–5 ms latency).  
* **Host Input:** Multi-channel ASIO Audio Interface (e.g., Focusrite / Universal Audio) or FL Studio ASIO at 128 samples / 48kHz.  
* **FL Studio Processing:**  
  1. Audio routed to Mixer Track 1\.  
  2. Fruity Parametric EQ 2 isolates Sub-Bass (![][image4]).  
  3. Fruity Peak Controller maps envelope peaks to internal parameter automation nodes.

## **3\. Clock & Latency Synchronization Architecture**

To eliminate the "early visual trigger" defect caused by network metadata arriving faster than the buffered audio path, the system applies **Delay Compensation** at the ingress point.

Metadata Path:  \[CDJ Beat Event\] ──► (UDP \~1ms) ──► \[Beat-Link-Trigger\] ──► \[Artificial Delay Δt\] ──┐  
                                                                                                      ▼  
Audio Path:     \[CDJ Audio Out\]  ──► (Analog 0ms) ──► \[ASIO Input Buffer\] ──► \[Peak Controller\] ───► \[Phase-Locked Render Event\]

### **3.1 Latency Equation**

![][image5]Where:

* ![][image6]  
* ![][image7] (depending on RF or hardware converters)  
* ![][image8]  
* **Target Compensation Delay (![][image9]):** ![][image10] (Configured inside Beat-Link-Trigger output buffer delay settings).

## **4\. GLSL Boilerplate Engine**

Below is the complete single-pass shader code required for ZGameEditor Visualizer to render a 4D Hypercube (Tesseract) frame with 6-plane parameters, IMU controls, and audio transient deformation.

// Name: 4D Hypercube Matrix Visualizer  
// Author: Implementation Agent Blueprint  
// Category: Custom 4D

\#version 120

uniform vec2 a\_resolution;  // Screen dimensions  
uniform float a\_time;       // Global application time

// Exposed Automatable Parameters (Automated via FL Studio)  
uniform float u\_RotSpeedXY; // CC Parameter 1 (IMU / Beat)  
uniform float u\_RotSpeedXZ; // CC Parameter 2  
uniform float u\_RotSpeedXW; // CC Parameter 3  
uniform float u\_RotSpeedYZ; // CC Parameter 4  
uniform float u\_RotSpeedYW; // CC Parameter 5  
uniform float u\_RotSpeedZW; // CC Parameter 6

uniform float u\_BeatPhase;     // Dynamic phase from Pro DJ Link (0.0 to 1.0)  
uniform float u\_AudioTransient;// Peak Controller intensity input (0.0 to 1.0)  
uniform float u\_SliceW;        // Hyperplane depth W-slice offset

// 4D Rotation Matrix Generators  
mat4 rotateXY(float t) {  
    float c \= cos(t), s \= sin(t);  
    return mat4(  c,  s, 0.0, 0.0,  
                 \-s,  c, 0.0, 0.0,  
                0.0, 0.0, 1.0, 0.0,  
                0.0, 0.0, 0.0, 1.0);  
}

mat4 rotateXW(float t) {  
    float c \= cos(t), s \= sin(t);  
    return mat4(  c, 0.0, 0.0,  s,  
                0.0, 1.0, 0.0, 0.0,  
                0.0, 0.0, 1.0, 0.0,  
                 \-s, 0.0, 0.0,  c);  
}

mat4 rotateYZ(float t) {  
    float c \= cos(t), s \= sin(t);  
    return mat4(1.0, 0.0, 0.0, 0.0,  
                0.0,   c,  s, 0.0,  
                0.0,  \-s,  c, 0.0,  
                0.0, 0.0, 0.0, 1.0);  
}

mat4 rotateZW(float t) {  
    float c \= cos(t), s \= sin(t);  
    return mat4(1.0, 0.0, 0.0, 0.0,  
                0.0, 1.0, 0.0, 0.0,  
                0.0, 0.0,   c,  s,  
                0.0, 0.0,  \-s,  c);  
}

// 4D Distance Estimator for a Tesseract  
float sdHypercube(vec4 p, vec4 b) {  
    vec4 d \= abs(p) \- b;  
    return min(max(d.x, max(d.y, max(d.z, d.w))), 0.0) \+ length(max(d, 0.0));  
}

void main() {  
    // Normalize aspect ratio coordinates (-1.0 to 1.0)  
    vec2 uv \= (gl\_FragCoord.xy \- 0.5 \* a\_resolution.xy) / a\_resolution.y;

    // Raymarching setup in projected 3D space  
    vec3 ro \= vec3(0.0, 0.0, \-3.5);  
    vec3 rd \= normalize(vec3(uv, 1.0));

    // Convert parameter ranges from \[0, 1\] to \[-2.0, 2.0\] speeds  
    float tXY \= a\_time \* (u\_RotSpeedXY \- 0.5) \* 4.0;  
    float tXW \= a\_time \* (u\_RotSpeedXW \- 0.5) \* 4.0 \+ (u\_BeatPhase \* 6.28318);  
    float tYZ \= a\_time \* (u\_RotSpeedYZ \- 0.5) \* 4.0;  
    float tZW \= a\_time \* (u\_RotSpeedZW \- 0.5) \* 4.0;

    // Composite 4D Rotation Transformation Matrix  
    mat4 rot4D \= rotateXY(tXY) \* rotateXW(tXW) \* rotateYZ(tYZ) \* rotateZW(tZW);

    // Audio-reactive scale modification  
    float hyperScale \= 0.8 \+ (u\_AudioTransient \* 0.35);

    float totalDist \= 0.0;  
    vec3 col \= vec3(0.0);

    // Raymarching loop  
    for (int i \= 0; i \< 64; i++) {  
        vec3 p3D \= ro \+ rd \* totalDist;  
          
        // Embed 3D point into 4D space with dynamic W-slicing  
        vec4 p4D \= vec4(p3D, (u\_SliceW \- 0.5) \* 2.0);

        // Apply 4D Rotations  
        p4D \= rot4D \* p4D;

        // Compute Distance in 4D  
        float d \= sdHypercube(p4D, vec4(hyperScale)) \- 0.02;

        if (d \< 0.001 || totalDist \> 10.0) break;  
        totalDist \+= d \* 0.5; // Step relaxation for smooth convergence  
    }

    // Shading & Glow pass  
    if (totalDist \< 10.0) {  
        float glow \= 1.0 / (1.0 \+ totalDist \* totalDist \* 0.5);  
        vec3 baseColor \= 0.5 \+ 0.5 \* cos(u\_BeatPhase \* 6.28318 \+ vec3(0.0, 2.0, 4.0));  
        col \= baseColor \* glow \* (1.0 \+ u\_AudioTransient \* 1.5);  
    }

    gl\_FragColor \= vec4(col, 1.0);  
}

## **5\. Python IMU UDP-to-MIDI Bridge Implementation**

Run this daemon on the Visualizer PC to bridge ESP32 wireless packets into 14-bit MIDI CC messages.

import socket  
import struct  
import mido  
import sys

\# Configuration  
UDP\_IP \= "0.0.0.0"  
UDP\_PORT \= 8888  
MIDI\_PORT\_NAME \= "IMU\_Bridge\_Port"  \# Must match virtual MIDI setup in loopMIDI

def main():  
    \# Initialize MIDI Output  
    try:  
        outport \= mido.open\_output(MIDI\_PORT\_NAME)  
        print(f"\[+\] MIDI Bridge active on port: '{MIDI\_PORT\_NAME}'")  
    except IOError:  
        print(f"\[-\] Error: Could not open MIDI port '{MIDI\_PORT\_NAME}'. Ensure loopMIDI is running.")  
        sys.exit(1)

    \# Initialize UDP Socket  
    sock \= socket.socket(socket.AF\_INET, socket.SOCK\_DGRAM)  
    sock.bind((UDP\_IP, UDP\_PORT))  
    print(f"\[+\] Listening for IMU UDP packets on port {UDP\_PORT}...")

    while True:  
        try:  
            data, addr \= sock.recvfrom(1024)  
            \# Expecting 3 binary floats (12 bytes): Roll, Pitch, Yaw  
            if len(data) \>= 12:  
                roll, pitch, yaw \= struct.unpack("fff", data\[:12\])

                \# Map values (-180.0 to 180.0) to 14-bit MIDI range (0 to 16383\)  
                norm\_r \= int(max(0.0, min(1.0, (roll \+ 180.0) / 360.0)) \* 16383\)  
                norm\_p \= int(max(0.0, min(1.0, (pitch \+ 180.0) / 360.0)) \* 16383\)  
                norm\_y \= int(max(0.0, min(1.0, (yaw \+ 180.0) / 360.0)) \* 16383\)

                \# Send 14-bit MIDI CC (MSB \+ LSB pairs)  
                \# Roll \-\> CC 20 (MSB) / CC 52 (LSB)  
                outport.send(mido.Message('control\_change', control=20, value=(norm\_r \>\> 7\) & 0x7F))  
                outport.send(mido.Message('control\_change', control=52, value=norm\_r & 0x7F))

                \# Pitch \-\> CC 21 (MSB) / CC 53 (LSB)  
                outport.send(mido.Message('control\_change', control=21, value=(norm\_p \>\> 7\) & 0x7F))  
                outport.send(mido.Message('control\_change', control=53, value=norm\_p & 0x7F))

                \# Yaw \-\> CC 22 (MSB) / CC 54 (LSB)  
                outport.send(mido.Message('control\_change', control=22, value=(norm\_y \>\> 7\) & 0x7F))  
                outport.send(mido.Message('control\_change', control=54, value=norm\_y & 0x7F))

        except KeyboardInterrupt:  
            print("\\n\[\*\] Shutting down IMU Bridge.")  
            break  
        except Exception as e:  
            \# Prevent dropped packet crashes during performance  
            continue

if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

## **6\. Implementation Checklist & Commissioning Steps**

1. **Virtual MIDI Bus Setup:**  
   * Install loopMIDI (Windows) or enable IAC Driver (macOS).  
   * Create two ports: ProDJLink\_MIDI and IMU\_Bridge\_Port.  
2. **Network Switch Ingress:**  
   * Connect CDJ-3000s / XDJ-AZ, Visualizer PC, and IMU access point to a dedicated Gigabit Switch.  
   * Verify Beat-Link-Trigger connects to the Pro DJ Link broadcast address.  
3. **FL Studio MIDI Mapping:**  
   * Enable both virtual ports in FL Studio MIDI Settings.  
   * Open ZGE Visualizer with the compiled .zgeproj shader.  
   * Right-click u\_RotSpeedXW ![][image11] **Link to Controller** ![][image11] select ProDJLink\_MIDI (Beat Phase CC).  
   * Right-click u\_RotSpeedYZ ![][image11] **Link to Controller** ![][image11] assign IMU Roll CC.  
   * Right-click u\_AudioTransient ![][image11] **Link to Controller** ![][image11] assign Fruity Peak Controller (Mixer Track 1).  
4. **Calibration Phase Alignment:**  
   * Route a metronome track through the DJ mixer.  
   * Adjust **Output Delay Buffer** in Beat-Link-Trigger until the visual color pulse and audio kick drum transient hit the screen at the exact same millisecond boundary.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAAAaCAYAAAAT6cSuAAAC+0lEQVR4Xu2WO2gUURSGN1FB8F0sK7K7M7usroWgsIKNWomdFtoIPlCCVuIDtFB8IGIlFnaKTTRoFws7wc5Cm0CCIGIhoqImTQQR4yPqf7Lnypl/78zNpskW88FlZv7z33NfM3duoZCTMyfq9fo61rKI43gfa10jjSLR7Wq1ustpURSdsR4G8T0od1DnBMd8wPuXtRDIXUe9MdZnRavVWoTKf6STjUZjea1W2y6dQLmA8pX9oA/6F5RRTEYsAjpwTOrg8SZ5/4P4OPIXWbfoZHVMgOSViWc9iCRD57b6dJTzpA3oINZbXYC2WGOnOIb8hxCbYJ3RNjsGJ6TpqaDRwbRKosuqmuf9omFlN1qfBfEfvnw66NWsW+D5HBjcUNTN6xlIltDV+8ZqDOJPuF6lUlnDGiPfOQZ/Oqs/2BNWpMW8uGQoNzhmQXxCfM1mcxnHLPCMiQ8d3WS0eyg/rY9BfEqvqYMTJCb7AuteYL7uErqCWbzl8WU26nA+DG6l0aZR7lufBbG3uCzU+8x2NPc51lORbdwlNZ17beIHRcP1sa3nw9c51a5azYFXdhvyXnbPvvoW7dtd1mcFGtrBDeD+pWoD1stgo9mpvkmra4eOWM2B2C96Dg3uO8pz1juAaS9rQtTelezgZjYJdHCL9THwTImP/2Va97DVVH8hvw/SQoP7hjLCegK8Drt9/yMBlc/aBrCaR+UZ1wPWZ0G+zTqIRxxT/YpHf+opM4PT++OeOhJ7yHoCGEbSTNCnaVNZIEmhvTOapV8b/cgBQWNDrPtQb9bKSTxxsOjAJSkWi0tJH448Ry5oF8WPFdpgdaxIrLmydsMHkW71IVy/WHdIDJO8ivUEMH0otGdczoiScFIrDrLXId+ceuXbeqb3owj1s9fiJoB1S9Q+2XxCea9lPKJ/b6lUWhLKMy/oxGXPeAD5VJBnmPV5Bx07KSvCejf05Ko50LnfoeNbGpicS6h/jfWeYi6zj8NBCfVesd6L9JXL5bUsZiHHQ9ZycnJ6g3/7VhVMU2WemAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAaCAYAAACzdqxAAAABOElEQVR4Xu2RvUoDURCFA6a1iE0S3N9q8xCKTSobewsV0ljZ+ASCYNpAHsEUwdJnsAxYiIWNCJY2CooY/PkG5pqbYbNZLKz2g2HnnnPn7N27tVrFf7ASx/Ez9e3VkxhJknToX30P7c4Nsn40c7uz2NmmNzGtLrhBqwu86BDv2Oq/YF4vGi4KRp9abQ42XGhA29ejKNpD+8oLRhsGQbBm9TkIOJPhMAw3fR3tnbrS4Lrxbv11LmzqyTB3duBpoyzLVnmei5emaeZ5N64vhMAtGaZOnUY/Ue9EvW1Z83UN+qHbVwh3ta4nHsua/sF5aPviEXik3ofzSqGnmhDUovpOJ3BDXzqg7/Lc8eeWosEv1KfR2+pdWq8UOiyf3F3k8QOb1luKDufen3r3Vi+FnrZhdUE8q1VUVPyRH5EpaU3H9jWQAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIgAAAAZCAYAAADqgGa0AAAEsklEQVR4Xu2ZSYgeVRDHJ3GJGhUTMg7OVt8sYWA8RJhIDlE86CEJqOBBEDwEvGjiEtGcQvSgB0GFBE28GHMIxIMevAlZQARBxUMU0YMXMUaN2TSLE7Ppv7rrhZp/V/cscb4M+H5QfP3+Vf1evdfVb7p7OjoymUwmk8lkriL9/f33iMhR2D+wzyHN5xgFvs2wk7C/YE+wn0HMMesz2VnY9+Y7AjtH/qPcx1wBub3YarWeYj0B/5s2n2O6nuxXent7h+H7wua6j/0MYvZLudZ+jY6rb2BgoAvHJ8h3Gjlu5X6uCHT6Fmy7axcJYSKDFPcdbK9rfwv7zMfUkSbAutLku9ogr/dlYhGv4xgF+p+wV117HBfqNR+D9n1+nmjfNdV5I+6wxnZ2dt7Mvr6+vrvVh/4+Zd9/gnW+gjWf/PDw8K3RZOzc21hnuD9Pk28uYXlWCgQ30v2cP3aKxazZWk3YgaQsPt2xGxErEJx/A/tmtUC6uroWRheINRwf4BjTNe5d1hnuz9Pkm0tYnpUCEdthAl134cf1eGho6HZt66+PwUXdE53LiBUIDq9l36wWiILOX8FEVpI24aJxezKdaYqLfLgDl0JbE5mPayeWZ1Qgqp+PdFy0b/QY6/sSz9H0nZHOyAwKxK+Zt8HBwX4fNyNs0peoXZlInc6kONjqwCp9oP2eapj0w/pgB+uxuBM+rp3Y+HUFcrJGH9djFMJHPEeL2RbpjFiBoJ8HhdYP2nPqCwpEx9+Hh9llPT09vVI+8Oou1ufjpo1WvXbU3d19U9JssMpE6nQmxcFeCKzSB9qf6FO6axcPzj6m3Vie62v04s0i0Iuc9eJF+UPfqrreAOzziBUIbKPQ+qGPLeoLCuRiOkYRjWoMft/xMdMGg6zQjvBQ2ul1S64ywTqdaYqLfGj/6I6Lu0wn6UJCsN0un6rxuZNhOTwT6bA/avRiF8bvbp6j6W+bXvnT4ZEZ/InRXSsdWy5nvH/aoMNF2hGKYwH7bIBogqHONMU1+WxrVP9u9kVgsR6aqvG5k6F5YI2ejXTY3zX6D3pc9wwCbUekMzKDAkmIfYtifbrM507Q3uWOT7HfdF2E4sNXExZXOV+Zgu+ca1ceBtuF5oKLsCHSo/xVS1u6vgRo+0rfYkZHR69nX1OBYNyX1acx2h4bG7sO7W0cNyniHkgjDQM9Gk3EFmGMdaZuEZU6H7SDps9zWiWuXejYuAjPB/r2IK95qukFSYLN8xEfhPZpCZ5fGLEC8c+FiboCSd9iYB8nDTGPtRq+BodI9XP3ZaM4TeJJ136dYyJGRkZuifpLON81TntaNRTfA07bVNfHbIMLs8TyfIN9iuV6Z2pjnb4UerOx3eKCk4oigt5yWojYJ3U8uAv7cPoqy+2A103zN37xVwIFda/TmnGvj5EVr2gu9kbVbfJfw852uLs7QspP0L9IuRv8LOWd8Kv5tDB/M139GnfKfOPmvyiU18QRZheM94GU/zNKOaY5XP6zp+iFs/z2o1B+wu8h709IuW5nYB9qvL8BIhDzlY2Xxj8k9qqP3ztgx01Luf0O24FrtFbK/3udh10St356w/I4mUwmk8lkMplMJpPJZDL/d/4FPntMK9fwN2oAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABBCAYAAABsOPjkAAAPCklEQVR4Xu2dfbBuVV3Hz71Q0buUxHjhPmtfLnr12qhENQKJSFGSKDqaZmqREsbYqy+JYzVNSjXm4JgmaS8mjMwk42gkppn9UWQU2YyGkqWpSSEjEmAginD7fvf+rXN+d539nOd5zrnn3Jf5fGbWXb/1Wy977/W2f3utdZ67tAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHhFLKJyeTyUWtHgAAAAAOAbquu0QG2z67Nm6MnTt3Pq7VwdZDO2wd+ph5XauDA4/moDe1Ojh8YdwAHGDCWHul/VNPPfXr2viMjLufVbp3tnrYWmiH9aE6u7TVzUJ1/fB5P2ZgQPX1pFY3i+jT1PMRAuMGYBOoL7Ew3D7ZxmcUf7vcKa0ethbaYX2ozq5tdbOYTCbv5sWzGKqvl7W6WUSfpp6PEBg3AAcYDahPV3nHjh0P9gDTQHtmTmOkP1fuRyP+yZbbNLD50A4bYxGDTWkfUeta7l+o6/kpCxhs6sc/kOr5Cur58IZxA7A5HKXB9OWsiEG26qtIuhdrYv2DiH+xXZsGNh/aYWOUBQy2rusulntF1PWrqOv5KQsYbPTpIwvGDcAmoIF044knnnhCo7s3Btq5WR9x73Rcq4fZ7Nmz51tVd1eOuCs0ub1NL6y3Sv5juT8sM87/zGoHxb2o1cFAWcBgM2qXn1+rrsXRraKye/funa1uLXbu3Lmj1R1I1M+6Kp988snflqIOOGUBg83M6tNweDHHuAGAedGAOk8D6k9avfFAGxtsoX9Xqz9c0bNc14T9fC/JukORWe3g+PW+kHO7j/WBtVg0/XrQB8ZDW900op7mcm3eSsR/sdVXFHfHrl27fnhEf1+SP5Xk0+VeXcPKe7yvIVvqmFAdPet+qqwx/JNrpU1sV7q7lP59us758v/RSum+2iZcD1FH87j727yViF/Vp60f0d1pX8+xdyx+veSyDmS5Jp7vVy3v2LHjmxyWgb67TbcoLsfltfoN4v7i+53lbmgzViJ+1biR7jrHjeg9Bs5q9RmleWOrWwuVd4HcP7X6zEknnTRpdbPQfdzVPoPCN+fwVtHeBxyhrNXQZVj5aeO3xaB6TKM/bBl5xsOBWe3g+Pvk/qKNmIeN1MlG8s6DXtBnyD2y1S9CWXCFLer6l1p9RfF/VJoXk17E31eSkebV1RynZ/j1Gnb5Nrxq2Cj8ZLnnZl2lrePI/1tZ16JrPsXGWg23ZWwGZfEVttE+Hc+3/PuQNnA36+dsNrNe4jl+JYU/UdYwYOfF5W6CwbZhpo2bMmyRup6PSronRfqzVlKuRmmubnVr4XE0y2BTma9sdbNQnrtU7sXy31J1s67juavVHQg2s8/CIYQ62DtaXSYG0J+n8M/lziH5vVVWZzxH7uU1bJT3hUrzEzWsSfa7FX5CxD0r1EdJ/vGUZrfKeZ7EbdI/teqNf25E+S+tHV/xD/eLKOTzc1pN6o/yNeQujvhjlPdFyvuDNc3u3bu/y8/jLyz/sYVXpBQ+W2V+b03je/agr2HFn1LvXfLTq34eVM4jlecrc7rXtvkrZY12MLrO63SPF+Q0xs9S61Rp9kY9L6Pwj9XVHoddH9blNF3Tpi3NfZ2r/Mced9xx39L+VIyuUxR3qvwz5f+2dW37GoXPdjl+5gj7pXfOer6KK2UdBpu87Zb1/H+V46LfrVoRO+GEE76z1VX83CVWWsy0dHPqe+Nd7iG+pvu35NNUP9+ue3u83I8ozdHSXyT9B9werjvnyXVYUr27byj8NMsq88SaZlHKOgy2JC/3aclXNXEfrrLvtfbpiMv9ZZviz1M//gbHKd0TPeZDXjUfRP7Rvu+6qm4ptsBdx6439eE9DnveUPg5voe2vxuXnetE8t2l+Yv8XF6ZMdco7jEeWy43G2y+h1pGPEf/B2Rliw/+R12uGjdlMNj+siTjS/Knnb5LBludD1IaG3XX5jbQc36/dL9Z01RcLyrr2W7/LhlSrk+lvzCn9XVT2+Z0u3K6jOLuCt/z0bEhX9+k+bUSdd6+a6Tadvzxx3+zx6zD/qBz2PNv3hnpmvlW8Y9W+BT77n/WuVz7LsdlKP9xNT0cIagjXOOGnselCeQGh0P+Si2r6kx9+Up3xVj8GvJoeZZ1r49dGgy4X7bOg7EOribt1+zrHi73QA7dPdkPefRaEX5LST9xkvRfrC8v6238tGm2ijKlHVJ8v63kNHLPb+L+Ncn3hmij+YVJP62NRts006T/T7n/DvmDci8YSXNbiKvaV3E3SfegSNdvNzjv5CCssNn3xNytbFvWuC+E/0CunxS/r7qk+56yQYPNHyq6l/Mlf7ZLqxiT4RzkGyLdSyaxqib5aXJ/n8sIsTf4LMTLvx9D1tmYKQtuQWXKOg22OnbbOLnTl4atulUv3PBH+4tfiiF/KeYSyzPngywnXW9g+cVa4id1usEorvH7/PKV7oKqy3FyH5G72vLevXu/vsZFef31XJ7k/6h52rnGZ45LtFPV22Bbqwy/yHM/2QrqvbTjpsRxgBqv+35UDXdhsEm+vov5QPJX03y/bOTF89b55bYSiwEupxrpki/swmCT/De1req1WznCo+kyJQy2WudhkH2oxnf7L3Q8J/z2OjdOYuW4jQvd6HxbYt4uTT2Wke1nOEJwIy/g8lmcL1u3lA5al8ZosGGjjnhOinf6/ktL8r8lfS53dABJvl7uY3IvkLtZ7nN2Yx1d8t32PUFYL3ePJrfvqPHd8LXyoWnXivDvlWG14blNuqvTy29q/q2ijLSD8VZRGX4W4Y1yt5ZUx6aMGGylebGOPd9abZrJeVXf/97F6qn010q+pE0j+e/CX9W+cmc4rdytS7F94vBBMNi+EPex3/kq9a1vLIMh6rr2TxdM7QuK+2yVJwd2ha0Py91oWXX85rJisPkvL9c02MpQ787f13vSj157EcriBlvfp+VeMxL3Ybnb9XxvG4nr73Vaf0kGm7exeoPNzJoPshzh/iUdso+M1Dr7nAyKh4V+ar3FvfV1UldcUpzL88r61HZIumtru1Z9nImbWcZWUqaMm0ls30v/kfD7seG03YrB5nx1Prgnzff7bYnaEC3DR/Z9kzhWkJ+3a86wycA6U/HvzWmyXIl0Hx+LM2X/vtCvAJcYX94lKsOz13a4KtK1/WlXiS3xMpwl9cdIb9ytNd/W8nKc3GV19RhgTUr62jP+yzh1tmek+OUl+zJiMNQ0U+QPaMB9VO5ZY0u9Tdrlrx77uodfqPH2p6zK9XJ9Ech/fRkMtuc16d5T4gtqLP+hgu7nlirHFm87SXw8yb2hrWf+naVkfI0931ptmmny3lRiK0fXuKZbMdjeJXdnWVldc/yq9pWus690r63lyn/A2wE53aKUBQ22aej2/iyHfY9drCTU5674w6E+n7fOJs0ZttL8ALLKOWsy5b/0yXVslPZvU/3YeOz/ayf5L1UZ7w/ZBtvyCkBN73pvy8vxG6EsaLCthesu6qlfUcmkZ+kinPtLv/oR8v/JnVb1a80HI/Jr6rVVp+fJXV7jMjlPi+Mm+59hW95Oc3kKf2wl9UqaVi7DR+xfZ70Nl3nKOBTohvmmtunTJ7Et7ft0v69yOx+Evjf+lOdnJL+srGxN/rPy/lTIy8/bDUdD+j+MkP+1Wv85TZVT/xlNl6nXTeF9JQw2v38mzVGSSPOA/S59dDhfzK1+3/gXAvo/pllrvpX+T6s+x027V4D9KMPqQv9VXOLnJNx51DGPiXMIL7XOh60l39YNZ8983qM/ZFyGLaJ99mveeo5M8u3pOu6YD67nQ1K+fk+/DAPNqxdXyX9rpOkHidPJO1rp9kSef0h6+1d6q6EbXn7vCd11HjSx7P350Pkv/Jz/dKV9rOU6yRxsYsL+ku63OFzvT+5cT+jWlfjNPaV9puPcJqHvt/bi69B5nhBbL94Sr9vLq9q04tWmWN1zXm9dOf3/yv2+8jxI/id0zXdHXd4i93m5Tynup2sZztu07/8oz0VxPa+a+Jn8206XdSNbTluJrv9436/7m8PR72wQ3B0T9jNK9L2I/y/73v5R3t8owxmevr8byXd08cKR/+z6vC1xHbfJmW6XsrJC1K8o+ctc+T8q0Vudn5G7J85avUHuZm/XxTjcV8JIlP/BWu/Ke0m9huQn5msfbEqaCyr1WaKvjvWX17uvW5buToXfEasyq+aDKnvuafq+6/KGyHdr+vi83/0+nYs7K8p6RL2/ilfgHOcx0MUfVkT4ffVe5d9Sy5sMq4VT5xrL/ghwG0WaOv96bD2/lhHjzc/0uLFzdVtN1NG97r8Olxgjk+F8r5/j1ZL3Lg113s8HyvPmmr8M29rHdMN/eXXFZOWvnW+aDL/jd5ncm0ps5cu/vwx/gOUf8u3/KtfbpZa7OB+ofO/3EYPJyjujTyf/0pyuovBTrZ80fyhUmhVsxZ8UwW3+R/leEXFX1nTdYFB+JvTLH3w5nOfbbugHN3TRh+pYlf9D8n838ixv0QNMY5snvKzwJKXO02XdPLjT2fck08Z5Mq1bHNOo2xMedFlfhq/r7e3E1abLeHDHIdEjhngJebDvrWc9TK1vxT86/1VjZr1tmlE73OEXk8TtuofLVdw1NS63rydx++3vBE67t0OJEi/tbjhn9qqlke3jFj3vsXIvr4eJN4LLUl3uqGNhFvOMq4PNrJ9zmdZfPN7DYDot/y7etPlgEXTNM8ZWmudF93BhjIWeRcqr85aNH5XzkKr3+Ji3jEMd98tWl40asX1XnIHr4vyi8flA561jIH0E7sqH+ittn3G6HF4Pfh/uio/nyti7po739v0ZcRuebwE2DQ8+G2wlrT7AkYXbtxrBkt+ul9QvtmkAAAAA4BBAxtrZrQ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALaW/wf9O1hRfWtEwAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQgAAAAaCAYAAABLn8LbAAAI50lEQVR4Xu1bB6gdRRRNYu+ixISUvS9Fol8sybf33lBBsRcsEbFgryhKwF6xRERNUKyIIvYuWLFgLFhiI4klamKJLbEnnrN757377pt97/+fn09+Mgcub+bcO3dmZ6fcnd3Xp09CQkJCQkJCQkJCQkJCQkJCQkITZFl2lojMhcxD+navbwaUOR/yK2QOZKzXL+rANb/lOQvoJ2i/fjl8+PDM68swZMiQkSjzBstCnvP6Xg0Olkql8qbnExY+4F59MnTo0K1MfjYHpbUpA+w+gjxr8h9AXrU2iyLMxM3F6wOgmzts2LCdTX4e5sWu1iYG2Gxj/SK/QbN6eh20I07xfMLCBz/IMfhPVu5ea+cxcuTIlWODVu/9qp5fFIFrPS3WBwT4C70OfbuH52LQPjzOcX9DXrdcrwRWzPW1E/p5XUL3YPDgwYhAh6zpeY/+/fuv6DkPXQxmhzwG8dnKXW3tPKB/NzbYtewEzy+KkOYLBPvhoxg/YsSIoZ4PgG4NtVnD8lgwnimrq1cAA2tLXMDukGd5Icjvyby3S+g6sCgsJ3pWAPlZf0snMnRneK4VUOYXHYh9vc5C624YsGV8AAb6ERgbl8DmAeaRXgfpWzlegg02mVHgboFcXCtZA3yM4zM9z0tgMwa/+3qbnoC0XiAazg6Uv97zAbiWC2I+wd8W4wP4mAj96eibmzWC64f8WKSvZbQX7MAdD7kH/La10gVQx3DonoR8CP2x0p0RixSddYZ2wI+aP83bJXQd6M8Z+FnScripN7HP8dtueXBTBg0atLzlWgFlrqAvLETrep2H3ueGAVvGB0B3UbCBTBs1atRKoPtq/itcx4sYnNvQlmnvi3ktE/KzfDjeU5AWCwTa9UiMhzzp+QBc80Mxn+BujPEBKHco9G+r/+0ht5DHwrGXtmUgfqeSw4LRX+2qm0tWPP5MNvm2ZvV1GXQK5yd63gI2J3guoTVwky/3HNHe3r4U+vQ3vem54B6c5O3KwHCWOw3KvQz5Go8wq3sbj1BPR3kL1kEb1Lls4JA+Vcse5WznIaJYz+adfvRCuEBw9+a1POgVyn/m+QBcy0sxn+CvI4/Fe7DXWaj/LyKc77e/LIf09+LOnXyZ+QZ3HnXaMjz1XGeAzrqZPsIOifxayP/r7ZoB9jewI7XzbvX63grsDst4rjMQ3eExKbf2Ogvtt4b7WMZbQD/N23CSe44gVzHhcPDPnda+fSlDW1vb0rDbsCPio7BWkPIFIm8n2xjjIS97PgC6e2I+wY1Xvi6C9ND+Otxz4s5DpPYomQNtvVTtZkHOZL9Z+24BHD8QuzgL6K+mDUMir+sM6CMsEAMGDFgB+ce9TStkxfv/pu3tbrCtqHcdz3cUuPlH6o2klA40AvVc4LkOIIT7TfulzKaMt4D+c2+D/NGeU57+tg/5cIhnpdlhLPubYXZHJDPnIB2BtF4gno7x0mRD4j2L+QQ3McZ7aL37e67iPjsA94P3x/aGPlU/DQvcfEEd/+R5C+j/lOIg5C+v6wxYV2efsT1Ez0w8vyCB+p7o6gKBm3yZmDAQ+XHa5+daO9VtAn6M5y2g34zlES1s7Hj6bNovoo80EZ5lq8+yMUD/mS+L/FjPKU9/1QXCRkjoxx1V/3PgehLSYoGQkrcYuDcHeD4A17QFbbr6FkPr3cdz8PuG42Zaf7Y+1LUsdO9oW7vvlbU2rnpyjvQrVg/0ZeTASv3FgjtQy7/PvKb9IPoOcqfoDhQWCG8LXwOz4pSbr+xm1jzUA7rTbbngB3Il5C5xix3ykyD306em87Kopx3pj7PipDl/7tSd7tVK8Wz9n5b/Q/3nYn13BFLy1R7qeFh9XoP0rmjHU2JeXZYBNu9ruRcc39A+5M+zee5S3oYgx/7wvIVEHjGkSQQBfzuY/Cyn3ztWricgzRcIfkRWp+NC7DlELhuJW8hpI42T/HdpsfkS2l91b3XIVRojCJ451I19LgzOhu3Y3HLzBTrkJ6KabogQ0IDrQlorrzuQgv5w0QUi2Jj0r7jwNquzEYS/2JDWV4PRHUYiN5j58PyF9POinw9zQmQaMuJ3J/A/aJE8JNc0y/zNT2rxOzmsvrQ3et7ALkUQLSbeElKcq0xBveO8MgbYjoH847g72Eb42CVwSJ9CToq3KNaWdseaPBfW6ISxEDc4lTuXHA9cA8dHB62juuMyb78Bge4cafGotaAg+taHbwW8Dm1cTdtenXRSRF2TrB1tfF9UimjBnqnlYwx8xXANYF1q5z+yYh2fO67ui1m1mepsWt7LTgEOr9KK/uwTOUxRHV/X8MBlhrjBiQs7SMoXCD+gogtEVrzuabC1+QBxEYRyts7HOQCZht+TkJ+m/G6ig1I0NIZ8pTIHtsdkGipSMnMWoPkuLRALAmjLftpO7lD/aXo7bwduCmRty+nim+9O+H1Pivve6oCar8D5FoN9NSMrHhM4caYr961OkI8h3yhH3Rwt/1ymrwIpsL3P17GgIcVXjYxmw3Xwl4vendZOr41tZITHw7/XrJ6QYj7cGOHZn5zE+bkefXkbC70H32p72F+z9d5ynoU25hGIFOcPoe0zNYqZBxmtv5S5HfkYrzvBVz+HhEzsU11c0L5intus3tsyzwMor4ePw2K2Nh8gkTMIm0enPxIWCNXxIzCG5dUwF/oDvA/lK/q7KfT/ZBomS/F9/vpMI9JYxRRJSFh8gYkxMcLVhahZEbpX3xHbiSfFDjfa6uwEc7bVNFdBqT0O1IGT309u5+cx0QNAfQ12WM2yBi2Tf1rOQ7RK8eea6Ua/HeRgTU+Hr600+mm62yYkLBaQIoRkWPOb4fihxk9ShJwMTQM/qVKEmI9y4unkC7qpUuzi+efcFH5VJzX/+cEcJ5/mJ0OuDOUtpAgTQ/2/KMfPl3M/UtRPPeU8nkuI1hnEhGD90OZPpQiLx6uv6Vnxrz+eY7wT6q0UB7R8DKk7VU5ISOjFELOIKfKv5RyXkJCwOAI7/+VYEK4IeaTvRhRwsrVJSEhYzMFv4bFYDPR8QkJCQkJCQkJCQkJCQkJCj+B/RRKF/5rq9+wAAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG8AAAAaCAYAAAC5KgISAAAD5klEQVR4Xu2Y24tNcRTHD4PCgwdlNLdzZuZtotQUcnsQuT148wcgLyhRYkQuhUKS5H5NcskQRpTLgyi3kHsjGozGfTDMTDF81rF+Y/nNHmaKc8b4fevbXuu71m/t32+v/dtn7xOLBQQEBAT8KcTj8fqcnJyuvh7QxkHjSuBXWOnHAto4tHFJFhUVdfHjUdD8sb4ekEIkEokZNGEJnK8Neejn+ODx2ldyMTv6sYAUQpvQaKufYVKagJxDdlxAGkADJsEVzmcXLtcG3rZ5DsRHExurOXVwXG5u7lA/LyAFiNo9Zvc1AfrMvLy82ZqzR/0Rfl7AXwYXfQIXf52vo62V5hC/6McE5veugx8LSBGa212C3+y+g83F/iek7RrIbxfc6esO7Lrt2sBTfkz1177ensF6x0Ro53wtJWjJXdPc7hNNPi98vT2DNVf5WlrARAbBg77ug5xSbWBjLm+WfbShye877OH2hQX/E1wBHxUWFvYSjUYPhJfQFsNrJldqCyV/N/yCnMHxBiyn7lIdP1fzjsKX8DK87uqATvif4ay4PhEYu0HHTIW34E20HW4A/hXqzuF4AT5VbRpcBbfABya3QWslqVqt2MXFxZ1N3hNqLuR4W66TaskxBQUFPTj/CewPHIe4Ma2GnUhLacaO8/y3xq6Tlxm1y1jI+KysrG42Pz8/v799EZKY+0cH+7TUsDFnM2YB/lkTuyoXw+Qlv0vRluFvVn0bbDBj7LyfGds17wxzHqV2KfYikxP5BHLNw66gYYU2FtM5iQ0PaKhDVK0WgTsgT4u1ilyU1a4Gfrnq9u5vboFyF5/3NHsRrV0G50XFZPfBI8aX7023C2QuT5RVcW0Mx02yA90Y71wfddzzmPlDgptrGNpxjW8z+VFrs837KY7/Una2i2H3NrEmtdKOqEmhbYW3PC2yedIct+CI2BzbPJoy2MWjzisgZz2xtc738jrKjkdbaep8ZsxstVfKS5tLdjnMIWG1XzSvxj32JZadnd3TxCLnm1YwqfdwkvGPxb7/HtlmTYybtzQvdgyWRMWkefhXTawCba7aj7AHmNz9qm+VBpoxtt4+X/fmcp2cnRw/mlgG9UaaHNu8+/afJs1PfgeLzY7O9GJtD0zsDHwN7xotH9bDChY/xejV8JVcoPj3l5E3ynnwg8beS640j7En8V/ASjjZ1dFa8niWenc0f6Optw7WaL13Gl+D/VB07IGiUX86/hfJy8zM7M6xgVg/jRXj13Hcq+eT9cg6q80cdhF/zPFF7McLnct7Ky9wkq9+rRvX7sFiSxLmsRnwj0DuWO7owzTwHg1M+PGAgICAgICA9oVvB4+feyCKUc4AAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,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>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAAAcklEQVR4XmNgGAWjYOCBvLz8XnQxigHQ0H/oYhQDOTk5GyAuQxenGABde05BQcEcXRwOZGVlTcjBQENvAQ3fh24eRQBo4F8gxYguTjYAGvgfXYwiAPT2BBUVFXZ0cYoA0JW/0cUoBkCXGqCLjYJRQEMAAMSsFY9fiDqtAAAAAElFTkSuQmCC>