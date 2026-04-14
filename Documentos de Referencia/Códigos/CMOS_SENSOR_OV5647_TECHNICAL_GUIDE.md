# Technical Guide: OV5647 CMOS Sensor Control for Lensless Microscopy
## Image Sensor Microscopy System - INTISAT Payload

**Document ID**: INTISAT-ISM-SEN-001
**Version**: 1.0
**Date**: 2025-12-05
**Sensor**: OmniVision OV5647 (Raspberry Pi Camera Module v1)
**Application**: Lensless Fourier Ptychographic Microscopy

---

## Table of Contents

1. [OV5647 Sensor Specifications](#1-ov5647-sensor-specifications)
2. [Sensor Physics and Architecture](#2-sensor-physics-and-architecture)
3. [Camera Control Parameters](#3-camera-control-parameters)
4. [Code Implementation](#4-code-implementation)
5. [Parameter Optimization for Microscopy](#5-parameter-optimization-for-microscopy)
6. [Calibration Procedures](#6-calibration-procedures)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. OV5647 Sensor Specifications

### 1.1 Physical Characteristics

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Manufacturer** | OmniVision Technologies | Silicon Valley, CA |
| **Part Number** | OV5647 | Raspberry Pi Camera Module v1 |
| **Sensor Type** | CMOS (Back-illuminated) | Improved quantum efficiency |
| **Format** | 1/4" optical format | 3.67mm diagonal |
| **Active Pixels** | 2592 (H) × 1944 (V) | 5.04 Megapixels |
| **Pixel Size** | 1.4 μm × 1.4 μm | Physical pixel pitch |
| **Pixel Array** | 2.71mm × 3.63mm | Active sensor area |
| **Optical Center** | (1296, 972) pixels | Centered on array |

### 1.2 Optical Specifications

```
Sensor Geometry (OV5647):
┌─────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────┐  │
│  │                                           │  │
│  │        Active Pixel Array                 │  │
│  │        2592 × 1944 pixels                 │  │
│  │        2.71mm × 3.63mm                    │  │
│  │                                           │  │
│  │           Center: (1296, 972)             │  │
│  │              ↓                            │  │
│  │           ┌──┴──┐                         │  │
│  │           │  ●  │  ← Optical axis        │  │
│  │           └─────┘                         │  │
│  │                                           │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Pixel pitch: 1.4μm × 1.4μm                    │
│  Fill factor: ~65% (photodiode area)           │
└─────────────────────────────────────────────────┘

Bayer Color Filter Array (BGGR pattern):
┌─────┬─────┬─────┬─────┐
│  B  │  G  │  B  │  G  │  ← Row 0 (even)
├─────┼─────┼─────┼─────┤
│  G  │  R  │  G  │  R  │  ← Row 1 (odd)
├─────┼─────┼─────┼─────┤
│  B  │  G  │  B  │  G  │  ← Row 2 (even)
├─────┼─────┼─────┼─────┤
│  G  │  R  │  G  │  R  │  ← Row 3 (odd)
└─────┴─────┴─────┴─────┘

For microscopy (grayscale):
  We extract luminance from Bayer pattern
  or use direct RAW readout
```

### 1.3 Performance Specifications

| Parameter | Min | Typ | Max | Unit | Condition |
|-----------|-----|-----|-----|------|-----------|
| **Sensitivity** | - | 680 | - | mV/lux-s | @ 550nm |
| **Dynamic Range** | - | 67 | - | dB | Linear mode |
| **SNR** | - | 36 | - | dB | @ 1200mV signal |
| **Dark Current** | - | 15 | 30 | mV/s | @ 60°C |
| **Fixed Pattern Noise** | - | 0.2 | - | % | of saturation |
| **Quantum Efficiency** | - | 65 | - | % | @ 550nm (green) |
| **Full Well Capacity** | - | 4300 | - | e⁻ | per pixel |
| **Read Noise** | - | 3.2 | - | e⁻ rms | Low gain |

### 1.4 Timing Specifications

| Parameter | Min | Max | Unit | Notes |
|-----------|-----|-----|------|-------|
| **Frame Rate (full res)** | - | 30 | fps | 2592×1944 @ 30fps |
| **Frame Rate (1080p)** | - | 60 | fps | 1920×1080 @ 60fps |
| **Exposure Time** | 1 | ~6000 | ms | Software configurable |
| **Line Time** | 21.5 | - | μs | @ 30fps full resolution |
| **Pixel Clock** | - | 84 | MHz | MIPI CSI-2 interface |

---

## 2. Sensor Physics and Architecture

### 2.1 CMOS Photodiode Architecture

```
Single OV5647 Pixel Cross-Section:
─────────────────────────────────────────────────
                   ↓ Light (photons)
                   │
    ┌──────────────┴──────────────┐
    │   Micro-lens (focusing)     │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │   Color Filter (Bayer)      │ ← B, G, or R
    └──────────────┬──────────────┘
                   │
    ╔══════════════╧══════════════╗
    ║   Photodiode (Si p-n junction) ║
    ║   - Photon → electron-hole pair║
    ║   - Charge accumulation        ║
    ║   - Integration time = exposure║
    ╚══════════════╤══════════════╝
                   │
    ┌──────────────┴──────────────┐
    │  Transfer Gate               │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │  Floating Diffusion (FD)     │ ← Charge-to-voltage
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │  Source Follower (SF)        │ ← Amplification
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │  Column Amplifier            │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │  ADC (10-bit)                │ ← Digital conversion
    └──────────────┬──────────────┘
                   │
                  Output (0-1023)
─────────────────────────────────────────────────
```

**Photoelectric Effect**:
```
Incident photon energy: E = hν = hc/λ

For λ = 550nm (green light):
  E = (6.626×10⁻³⁴ J·s)(3×10⁸ m/s) / (550×10⁻⁹ m)
    = 3.61×10⁻¹⁹ J
    = 2.26 eV

Silicon bandgap: Eg = 1.12 eV @ 300K
  → Photon absorbed if E > Eg ✓

Quantum Efficiency:
  QE = (# electrons generated) / (# incident photons)
  QE(550nm) ≈ 65% for OV5647
```

### 2.2 Analog Gain Implementation

**OV5647 Gain Architecture**:
```
                Photodiode Signal
                       ↓
    ┌──────────────────┴──────────────────┐
    │   Pixel Source Follower (SF)        │
    │   Gain: Fixed (unity)               │
    └──────────────────┬──────────────────┘
                       ↓
    ┌──────────────────┴──────────────────┐
    │   Column Amplifier                   │
    │   Gain: 1× to 16× (programmable)    │ ← ANALOG_GAIN control
    │   Implementation: PGA (Programmable  │
    │   Gain Amplifier)                    │
    └──────────────────┬──────────────────┘
                       ↓
    ┌──────────────────┴──────────────────┐
    │   10-bit ADC                         │
    │   Range: 0 - 1023 (digital values)   │
    └──────────────────┬──────────────────┘
                       ↓
               Digital Output

Gain Formula:
  V_out = V_photodiode × AnalogGain × DigitalGain

  Where:
    AnalogGain: 1.0 to ~16.0 (hardware amplification)
    DigitalGain: 1.0 to 16.0 (software multiplication)

  Total Gain = AnalogGain × DigitalGain
  Max combined: ~256× (not recommended for microscopy)
```

### 2.3 Exposure Time Control

**Rolling Shutter Architecture**:
```
OV5647 uses ROLLING SHUTTER (not global shutter)

Frame Readout Sequence:
─────────────────────────────────────────────────
Row 0:    │───[Expose]───│[Read]│
Row 1:      │───[Expose]───│[Read]│
Row 2:        │───[Expose]───│[Read]│
  ...           ...
Row 1943:                        │───[Expose]───│[Read]│
─────────────────────────────────────────────────
          ← Exposure Time →

Timeline:
  t=0:     Row 0 starts exposure
  t=T_exp: Row 0 stops exposure, readout begins
  t=T_exp + T_line: Row 1 stops exposure
  ...
  t=T_exp + 1943×T_line: Last row readout

Where:
  T_exp = ExposureTime (user controlled)
  T_line = Line readout time (~21.5μs)

Frame Period = T_exp + (Rows × T_line)
             = T_exp + (1944 × 21.5μs)
             = T_exp + 41.8ms

Maximum exposure:
  T_exp_max ≈ 6 seconds (limited by buffer/timing)
```

**Charge Integration**:
```
Signal Charge Accumulation:
  Q(t) = ∫₀ᵗ I_photo dt
       = (QE × Φ × A × t) electrons

Where:
  QE = Quantum efficiency (0.65 @ 550nm)
  Φ = Photon flux (photons/cm²/s)
  A = Pixel area (1.4μm × 1.4μm = 1.96μm²)
  t = Exposure time (ExposureTime)

Saturation:
  Q_sat = Full well capacity = 4300 e⁻

If Q(t) > Q_sat → Pixel saturates (value = 255 in 8-bit)
```

---

## 3. Camera Control Parameters

### 3.1 Picamera2 API Control Structure

**Camera Initialization** (from `capturaclaude.py`):
```python
from picamera2 import Picamera2

# Initialize camera object
cam = Picamera2()

# Create configurations for different modes
cfg_preview = cam.create_preview_configuration(
    main={"format": "XRGB8888", "size": (1280, 720)}
)

cfg_capture = cam.create_still_configuration(
    main={"format": "XRGB8888", "size": (2592, 1944)}
)

# Apply configuration
cam.configure(cfg_preview)  # or cfg_capture

# Start camera
cam.start()
```

**Configuration Dictionary Structure**:
```python
configuration = {
    "main": {
        "format": "XRGB8888",      # Pixel format (RGB8, YUV420, etc.)
        "size": (width, height),   # Resolution in pixels
    },
    "lores": None,                 # Optional low-res stream
    "raw": None,                   # Optional RAW Bayer stream
    "controls": {                  # Optional default controls
        "ExposureTime": value_us,
        "AnalogueGain": value_float,
        ...
    }
}
```

### 3.2 Core Control Parameters

#### **ExposureTime** (Exposure Duration)

**Definition**: Time duration for charge integration in each pixel.

```python
# Units: microseconds (μs)
# Range: 10,000 μs (10ms) to ~6,000,000 μs (6s)

ExposureTime = 150000  # 150ms (150,000 μs)

cam.set_controls({
    "ExposureTime": ExposureTime
})
```

**Physical Effect**:
```
Longer exposure → More photons collected → Higher signal
BUT:
  - Increased dark current noise
  - Potential motion blur
  - Slower frame rate

Signal-to-Noise Ratio:
  SNR ∝ √(N_photons)

  Where N_photons ∝ ExposureTime × Illumination

Optimal for microscopy:
  Balance between:
    - Sufficient signal (avoid underexposure)
    - Limited noise (avoid long exposures)
    - No saturation (avoid overexposure)
```

**Code Implementation** (`capturaclaude.py`, line 14, 102-107):
```python
# Default configuration
EXPOSURE_US = 150000  # 150ms default

# Runtime adjustment (lines 102-107, 379-386)
cam.set_controls({
    "ExposureTime": EXPOSURE_US,
    "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)
})

# Interactive control (lines 379-386)
if key == '[':  # Decrease
    EXPOSURE_US = max(10000, EXPOSURE_US - 10000)
    cam.set_controls({"ExposureTime": EXPOSURE_US})

if key == ']':  # Increase
    EXPOSURE_US = min(500000, EXPOSURE_US + 10000)
    cam.set_controls({"ExposureTime": EXPOSURE_US})
```

#### **AnalogueGain** (Analog Amplification)

**Definition**: Hardware amplification applied to photodiode signal before ADC.

```python
# Units: Linear gain factor (unitless)
# Range: 1.0 (unity) to ~16.0 (OV5647 hardware limit)

AnalogueGain = 1.0  # Unity gain (no amplification)

cam.set_controls({
    "AnalogueGain": AnalogueGain
})
```

**Physical Effect**:
```
Signal Amplification:
  V_adc = V_photodiode × AnalogGain

Noise Amplification:
  - Signal noise: √(N_signal) × AnalogGain
  - Read noise: N_read × AnalogGain
  - Fixed pattern noise: FPN × AnalogGain

SNR Degradation:
  SNR_gain = SNR_unity × √(1/AnalogGain)

Why avoid high gain:
  - Amplifies noise equally with signal
  - Does NOT improve SNR
  - Reduces dynamic range
  - Increases fixed pattern noise

Preferred approach for low light:
  1. Increase ExposureTime (improves SNR)
  2. Increase illumination
  3. Only then increase AnalogGain
```

**Code Implementation** (`capturaclaude.py`, line 15, 104, 389-396):
```python
# Default configuration
ANALOG_GAIN = 1.0  # Unity gain

# Runtime adjustment
cam.set_controls({
    "AnalogueGain": ANALOG_GAIN
})

# Interactive control (lines 389-396)
if key == '{':  # Decrease
    ANALOG_GAIN = max(1.0, ANALOG_GAIN - 0.2)
    cam.set_controls({"AnalogueGain": ANALOG_GAIN})

if key == '}':  # Increase
    ANALOG_GAIN = min(8.0, ANALOG_GAIN + 0.2)
    cam.set_controls({"AnalogueGain": ANALOG_GAIN})
```

#### **AwbEnable** / **AeEnable** (Auto White Balance / Auto Exposure)

**Definition**: Automatic camera control algorithms.

```python
# Boolean: True (enable auto) or False (manual control)

AWB = False  # Disable auto white balance
AE = False   # Disable auto exposure

cam.set_controls({
    "AwbEnable": AWB,
    "AeEnable": AE
})
```

**Why Disable for Microscopy**:
```
Auto White Balance (AWB):
  - Adjusts color gains (R, G, B) for "neutral" white
  - Varies between frames based on scene content
  - Introduces inconsistency in FPM reconstruction
  - Not needed for grayscale scientific imaging

Auto Exposure (AE):
  - Adjusts ExposureTime/Gain for "correct" brightness
  - Target: Mean pixel value ≈ 128 (mid-gray)
  - Defeats FPM angular variation
  - Creates non-uniform illumination response

For FPM:
  REQUIRE fixed, manual exposure across all angles
  → AWB=False, AE=False is MANDATORY
```

**Code Implementation** (`capturaclaude.py`, lines 16, 106, 120, 300):
```python
# Configuration
AWB, AE = False, False

# Apply to camera (multiple locations)
cam.set_controls({
    "AwbEnable": AWB,
    "AeEnable": AE
})
```

#### **FrameDurationLimits** (Frame Timing)

**Definition**: Minimum and maximum time between frame starts.

```python
# Units: microseconds (μs)
# Tuple: (min_duration, max_duration)

FrameDurationLimits = (EXPOSURE_US, EXPOSURE_US)

cam.set_controls({
    "FrameDurationLimits": FrameDurationLimits
})
```

**Purpose**:
```
Frame Rate Control:
  Frame Period = max(ExposureTime, MinFrameDuration)

  If ExposureTime = 150ms and FrameDuration = (150ms, 150ms):
    → Fixed frame period = 150ms
    → Frame rate = 1 / 0.150s = 6.67 fps

Why Set Equal to ExposureTime:
  - Prevents automatic frame rate adjustment
  - Ensures consistent timing
  - Avoids "black frames" (exposure < frame period)

For continuous preview:
  Set FrameDurationLimits = (ExposureTime, ExposureTime)
  → Framerate locked to exposure duration
```

**Code Implementation** (`capturaclaude.py`, lines 107, 121, 301, 381, 385):
```python
# Always set together with ExposureTime
cam.set_controls({
    "ExposureTime": EXPOSURE_US,
    "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)
})

# When changing exposure:
EXPOSURE_US = new_value
cam.set_controls({
    "ExposureTime": EXPOSURE_US,
    "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)
})
```

---

## 4. Code Implementation

### 4.1 Camera Configuration Modes

**Two-Configuration System** (`capturaclaude.py`, lines 291-292):

```python
# ====== Preview Configuration ======
# Purpose: Real-time display for focusing/alignment
# Resolution: Reduced for speed
cfg_prev = cam.create_preview_configuration(
    main={
        "format": "XRGB8888",    # RGB with padding (fast)
        "size": (1280, 720)      # 720p (downscaled from 2592×1944)
    }
)

# Memory: 1280 × 720 × 4 bytes = 3.7 MB per frame
# Frame rate: Limited by ExposureTime
# Use case: Continuous loop, user interaction


# ====== Capture Configuration ======
# Purpose: Full-resolution scientific acquisition
# Resolution: Native sensor size
cfg_cap = cam.create_still_configuration(
    main={
        "format": "XRGB8888",    # RGB with padding
        "size": (2592, 1944)     # Full OV5647 resolution
    }
)

# Memory: 2592 × 1944 × 4 bytes = 20.2 MB per frame
# Frame rate: Slower (full sensor readout)
# Use case: Single capture or scan loop
```

**Why Two Configurations**:
```
Problem: Can't change resolution on-the-fly
Solution: Stop → Reconfigure → Restart

Preview Mode (Interactive):
  - Lower resolution → Faster refresh
  - User adjusts: exposure, gain, position
  - Real-time histogram/stats display

Capture Mode (Acquisition):
  - Full resolution → Maximum detail
  - Fixed settings from preview
  - Save as TIFF (lossless, 16-bit capable)
```

### 4.2 Image Capture Function

**Full Implementation** (`capturaclaude.py`, lines 98-126):

```python
def capturar_imagen(cam, cfg_prev, cfg_cap):
    """
    Capture full-resolution image with sensor parameter control

    Workflow:
      1. Stop preview stream
      2. Switch to capture configuration
      3. Apply manual exposure/gain settings
      4. Wait for sensor stabilization
      5. Capture frame
      6. Switch back to preview
      7. Convert to grayscale

    Parameters:
        cam: Picamera2 object
        cfg_prev: Preview configuration (1280×720)
        cfg_cap: Capture configuration (2592×1944)

    Returns:
        gray_cap: numpy array (2592, 1944) dtype=uint8
                 Grayscale image (0-255)
    """

    # STEP 1: Stop preview stream
    cam.stop()

    # STEP 2: Reconfigure for full resolution
    cam.configure(cfg_cap)

    # STEP 3: Start capture stream
    cam.start()

    # STEP 4: Apply manual controls
    # (CRITICAL: Ensures consistent exposure across all captures)
    cam.set_controls({
        "ExposureTime": EXPOSURE_US,     # Fixed exposure (μs)
        "AnalogueGain": ANALOG_GAIN,     # Fixed gain (linear)
        "AwbEnable": AWB,                # Disabled (False)
        "AeEnable": AE,                  # Disabled (False)
        "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)  # Lock timing
    })

    # STEP 5: Wait for sensor stabilization
    # Allow time for:
    #   - Exposure integration
    #   - AGC to stabilize (even though disabled)
    #   - Frame buffer to fill
    time.sleep(0.15)  # 150ms (≥ 1 frame period)

    # STEP 6: Capture array
    # Returns: numpy array shape (1944, 2592, 4)
    #          Format: XRGB8888 (R, G, B, X channels)
    img = cam.capture_array()

    # STEP 7: Return to preview mode
    cam.stop()
    cam.configure(cfg_prev)
    cam.start()
    cam.set_controls({
        "ExposureTime": EXPOSURE_US,
        "AnalogueGain": ANALOG_GAIN,
        "AwbEnable": AWB,
        "AeEnable": AE,
        "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)
    })

    # STEP 8: Color space conversion
    # Extract RGB channels (discard X padding)
    bgr_cap = img[..., :3][:, :, ::-1]  # XRGB → BGR

    # Convert to grayscale (luminance)
    # Formula: Y = 0.299R + 0.587G + 0.114B (Rec. 601)
    gray_cap = cv2.cvtColor(bgr_cap, cv2.COLOR_BGR2GRAY)

    # Return: (1944, 2592) uint8 grayscale
    return gray_cap
```

**Timing Diagram**:
```
Capture Sequence Timeline:
─────────────────────────────────────────────────
Preview Mode:
  |──[Frame]──[Frame]──[Frame]──|
                                ↓
                            cam.stop()
                                ↓
                        cam.configure(cfg_cap)
                                ↓
                            cam.start()
                                ↓
                     cam.set_controls(...)
                                ↓
                         time.sleep(0.15s)
                                ↓
Capture Mode:
  |────[Integration 150ms]────|[Readout 42ms]|
                                ↓
                      img = cam.capture_array()
                                ↓
                            cam.stop()
                                ↓
                        cam.configure(cfg_prev)
                                ↓
Preview Mode:
  |──[Frame]──[Frame]──[Frame]──|
─────────────────────────────────────────────────
Total capture time: ~400-500ms per image
```

### 4.3 Automated Scan Implementation

**Grid Scan Function** (`capturaclaude.py`, lines 129-252):

```python
def barrido_automatico(cam, oled, cfg_prev, cfg_cap,
                       circ_r, grid_size, overlap,
                       center_cx, center_cy):
    """
    Automated grid scan for FPM acquisition

    Captures images at multiple illumination angles by varying
    OLED circle position while keeping camera settings fixed.

    Parameters:
        cam: Picamera2 object (OV5647)
        oled: OLEDController object (illumination source)
        cfg_prev: Preview configuration
        cfg_cap: Capture configuration
        circ_r: Circle radius (pixels on OLED)
        grid_size: N×N grid (e.g., 7 → 49 images)
        overlap: Fractional overlap (0.65 = 65%)
        center_cx, center_cy: Grid center position

    Camera Parameters Used:
        EXPOSURE_US: Fixed for all captures
        ANALOG_GAIN: Fixed for all captures
        AWB: False (manual)
        AE: False (manual)

    Returns:
        scan_dir: Path to output directory
    """

    W, H = oled.width, oled.height  # 128 × 64 pixels

    # Calculate step size between illumination positions
    step_x = int(circ_r * 2 * (1 - overlap))
    step_y = int(circ_r * 2 * (1 - overlap))

    # Center grid on user-specified position
    start_x = center_cx - (grid_size - 1) * step_x // 2
    start_y = center_cy - (grid_size - 1) * step_y // 2

    # Create output directory
    scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_dir = os.path.join(RAW_DIR, f"scan_oled_{scan_id}")
    os.makedirs(scan_dir, exist_ok=True)

    print(f"📁 Carpeta: {scan_dir}")
    print(f"⚙️  Sensor: OV5647 @ 2592×1944")
    print(f"⚙️  Exposure: {EXPOSURE_US/1000:.1f}ms")
    print(f"⚙️  Gain: {ANALOG_GAIN:.1f}×")
    print(f"🎯 Centro grilla: ({center_cx}, {center_cy})")

    scan_meta = []
    total = grid_size * grid_size

    # ===== GRID SCAN LOOP =====
    for iy in range(grid_size):
        for ix in range(grid_size):

            # --- Illumination Control ---
            # Calculate OLED position for this grid point
            pos_x = start_x + ix * step_x
            pos_y = start_y + iy * step_y

            # Clamp to valid OLED area
            circ_cx = max(circ_r, min(W - circ_r, pos_x))
            circ_cy = max(circ_r, min(H - circ_r, pos_y))

            # Update OLED display (illumination angle)
            oled.show_circle(circ_cx, circ_cy, circ_r, fill=True)
            time.sleep(DELAY_MS / 1000.0)  # 200ms settling

            # --- Image Acquisition ---
            # Camera settings remain FIXED throughout scan
            # (ExposureTime, AnalogGain set in capturar_imagen)
            gray_cap = capturar_imagen(cam, cfg_prev, cfg_cap)

            # --- Quality Metrics ---
            # Real-time validation of capture quality
            met = quick_stats(gray_cap)
            # met = {
            #     "min": pixel_min,
            #     "max": pixel_max,
            #     "mean": pixel_mean,
            #     "std": pixel_std,
            #     "pct_sat_255": saturation_percent,
            #     "pct_black_0": black_percent
            # }

            # --- File Naming Convention ---
            # Encode grid position AND illumination position
            fname = f"img_{iy:02d}_{ix:02d}_cx{circ_cx:03d}_cy{circ_cy:03d}.tiff"
            fpath = os.path.join(scan_dir, fname)

            # --- Save Full-Resolution TIFF ---
            # Lossless, preserves full 8-bit dynamic range
            cv2.imwrite(fpath, gray_cap)

            # --- Save Preview PNG ---
            # Downscaled for quick inspection
            png_small = cv2.resize(gray_cap, (648, 486))
            cv2.imwrite(fpath.replace('.tiff', '_preview.png'), png_small)

            # --- Individual Metadata ---
            json_path = fpath.replace('.tiff', '.json')
            with open(json_path, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "sample_tag": SAMPLE_TAG,

                    # ===== SENSOR PARAMETERS =====
                    "sensor": {
                        "model": "OV5647",
                        "manufacturer": "OmniVision",
                        "pixel_size_um": 1.4,
                        "array_size_px": [2592, 1944]
                    },

                    # ===== CAPTURE SETTINGS =====
                    "capture": {
                        "size_px": list(CAPTURE_SIZE),  # [2592, 1944]
                        "exposure_us": EXPOSURE_US,     # Microseconds
                        "analog_gain": ANALOG_GAIN,     # Linear factor
                        "awb_enable": AWB,              # False
                        "ae_enable": AE,                # False
                        "color_mode": "grayscale"
                    },

                    # ===== IMAGE QUALITY =====
                    "metrics": met,

                    # ===== ILLUMINATION =====
                    "oled": {
                        "address": f"0x{OLED_ADDR:02X}",
                        "contrast": OLED_CONTRAST,
                        "pattern": "circle",
                        "circle": {
                            "radius_px": int(circ_r),
                            "cx_px": int(circ_cx),
                            "cy_px": int(circ_cy)
                        }
                    }
                }, f, indent=2)

            # --- Scan Metadata Accumulation ---
            scan_meta.append({
                "filename": fname,
                "grid_pos": [ix, iy],
                "circle_pos_px": [int(circ_cx), int(circ_cy)],
                "circle_radius_px": int(circ_r),
                "metrics": met
            })

            # --- Progress Logging ---
            idx = iy * grid_size + ix + 1
            status = "⚠️SAT" if met['pct_sat_255'] > 1.0 else "✓"
            print(f"  {status} [{idx:2d}/{total}] "
                  f"grid({ix},{iy}) → OLED({circ_cx},{circ_cy}) | "
                  f"mean={met['mean']:.1f} sat={met['pct_sat_255']:.2f}%")

    # ===== CONSOLIDATED METADATA =====
    with open(os.path.join(scan_dir, "scan_metadata.json"), "w") as f:
        json.dump({
            "scan_id": scan_id,
            "datetime_utc": datetime.utcnow().isoformat() + "Z",

            # ===== SENSOR INFORMATION =====
            "sensor": {
                "model": "OV5647",
                "manufacturer": "OmniVision Technologies",
                "format": "1/4 inch",
                "pixel_array": [2592, 1944],
                "pixel_size_um": 1.4,
                "active_area_mm": [3.63, 2.71]
            },

            # ===== ACQUISITION PARAMETERS =====
            "acquisition": {
                "exposure_time_us": EXPOSURE_US,
                "analog_gain": ANALOG_GAIN,
                "awb_enable": AWB,
                "ae_enable": AE,
                "capture_size_px": list(CAPTURE_SIZE),
                "color_mode": "grayscale"
            },

            # ===== ILLUMINATION SOURCE =====
            "illumination": {
                "type": "OLED_white",
                "model": "SSD1306",
                "size_px": [W, H],
                "contrast": OLED_CONTRAST,
                "i2c_address": f"0x{OLED_ADDR:02X}"
            },

            # ===== SCAN PATTERN =====
            "scan_pattern": {
                "type": "centered_grid",
                "grid_size": [grid_size, grid_size],
                "total_images": total,
                "overlap_fraction": overlap,
                "circle_radius_px": int(circ_r),
                "step_px": [step_x, step_y],
                "center_px": [center_cx, center_cy],
                "start_px": [start_x, start_y]
            },

            # ===== INDIVIDUAL CAPTURES =====
            "captures": scan_meta

        }, f, indent=2)

    # Clear illumination
    oled.clear()

    print(f"\n✅ SCAN COMPLETADO")
    print(f"📊 {len(scan_meta)} imágenes @ 2592×1944")
    print(f"📁 {scan_dir}")

    return scan_dir
```

---

## 5. Parameter Optimization for Microscopy

### 5.1 Exposure Time Selection

**Optimization Goal**: Maximize SNR without saturation

```python
def optimize_exposure(cam, target_mean=100, target_sat_pct=0.1):
    """
    Automatically determine optimal exposure time

    Target:
        - Mean pixel value: ~100/255 (40% of range)
        - Saturation: <0.1% of pixels
        - Avoid underexposure (mean < 30)

    Algorithm:
        1. Start with conservative estimate (50ms)
        2. Capture test frame
        3. Measure mean intensity and saturation
        4. Adjust exposure proportionally
        5. Repeat until targets met
    """

    EXPOSURE_US = 50000  # Start: 50ms

    for iteration in range(10):  # Max 10 iterations
        # Set exposure
        cam.set_controls({
            "ExposureTime": EXPOSURE_US,
            "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)
        })
        time.sleep(0.2)  # Stabilize

        # Capture test frame
        img = cam.capture_array()
        gray = cv2.cvtColor(img[..., :3][:, :, ::-1], cv2.COLOR_BGR2GRAY)

        # Measure
        mean = gray.mean()
        sat_pct = 100 * (gray == 255).sum() / gray.size

        print(f"  Iter {iteration}: Exp={EXPOSURE_US/1000:.1f}ms "
              f"Mean={mean:.1f} Sat={sat_pct:.2f}%")

        # Check convergence
        if abs(mean - target_mean) < 10 and sat_pct < target_sat_pct:
            print(f"✓ Optimal exposure: {EXPOSURE_US/1000:.1f}ms")
            return EXPOSURE_US

        # Adjust exposure
        if sat_pct > target_sat_pct:
            # Overexposure: reduce aggressively
            EXPOSURE_US = int(EXPOSURE_US * 0.7)
        elif mean < target_mean:
            # Underexposure: increase proportionally
            factor = target_mean / (mean + 1)
            EXPOSURE_US = int(EXPOSURE_US * min(factor, 2.0))
        else:
            # Slight overexposure: reduce gently
            EXPOSURE_US = int(EXPOSURE_US * 0.9)

        # Clamp to valid range
        EXPOSURE_US = max(10000, min(500000, EXPOSURE_US))

    print(f"⚠️ Did not converge, using: {EXPOSURE_US/1000:.1f}ms")
    return EXPOSURE_US


# Usage in main():
EXPOSURE_US = optimize_exposure(cam, target_mean=100, target_sat_pct=0.1)
```

**Exposure Guidelines**:

| Illumination Condition | Suggested Exposure | Expected Mean | Notes |
|------------------------|-------------------|---------------|-------|
| **Bright (OLED 100%)** | 20-50ms | 120-150 | Risk of saturation |
| **Normal (OLED 80%)** | 100-150ms | 80-100 | Balanced |
| **Dim (OLED 60%)** | 200-400ms | 50-80 | Increased noise |
| **Very Dim** | 500ms+ | 30-50 | Avoid if possible |

### 5.2 Analog Gain Selection

**Rule of Thumb**: Keep gain as low as possible

```python
def select_analog_gain(illumination_level, exposure_us):
    """
    Choose analog gain based on conditions

    Priority:
        1. Increase exposure time (up to ~400ms)
        2. Increase illumination
        3. Only then increase gain

    Rationale:
        AnalogGain DOES NOT improve SNR
        It only amplifies existing signal + noise
    """

    if exposure_us < 400000:  # < 400ms
        # Prefer longer exposure over gain
        recommended_gain = 1.0
        recommendation = "Increase exposure time first"

    elif illumination_level < 80:  # OLED contrast < 80%
        # Prefer brighter illumination
        recommended_gain = 1.0
        recommendation = "Increase OLED contrast"

    else:
        # Last resort: increase gain
        # Limit to 2-4× to minimize noise amplification
        recommended_gain = 2.0
        recommendation = "Use minimal gain (2-4×)"

    return recommended_gain, recommendation


# Example usage
gain, advice = select_analog_gain(
    illumination_level=OLED_CONTRAST,
    exposure_us=EXPOSURE_US
)

print(f"Recommended gain: {gain}× ({advice})")
```

**Gain Impact on SNR**:
```
Scenario: Low-light sample

Option A: Exposure = 50ms, Gain = 4×
  Signal: 100 e⁻ × 4 = 400 e⁻ equivalent
  Noise: √(100) × 4 + ReadNoise × 4 = 40 + 12.8 = 52.8 e⁻
  SNR = 400 / 52.8 = 7.6

Option B: Exposure = 200ms, Gain = 1×
  Signal: 400 e⁻
  Noise: √(400) + ReadNoise = 20 + 3.2 = 23.2 e⁻
  SNR = 400 / 23.2 = 17.2

Option B has 2.3× better SNR! ✓
```

### 5.3 Resolution Selection

**Full Resolution vs. Binning/Cropping**:

```python
# Full resolution (maximum detail)
cfg_full = cam.create_still_configuration(
    main={"format": "XRGB8888", "size": (2592, 1944)}
)
# Use for: FPM reconstruction, final images

# 2×2 binning (4× faster, 2× less noise)
cfg_binned = cam.create_still_configuration(
    main={"format": "XRGB8888", "size": (1296, 972)}
)
# Use for: Quick scans, high SNR needed

# Center crop (region of interest)
cfg_crop = cam.create_still_configuration(
    main={"format": "XRGB8888", "size": (1920, 1080)}
)
# Use for: Small samples, faster acquisition
```

**Binning Benefits**:
```
2×2 Binning:
  - Combines 4 pixels → 1 "superpixel"
  - Signal: 4× (4 photodiodes combined)
  - Noise: 2× (√4 = 2)
  - SNR improvement: 4/2 = 2×
  - Frame rate: ~4× faster

Tradeoff:
  - Resolution: 2592×1944 → 1296×972
  - Spatial detail lost

When to use:
  - Low light conditions
  - Motion blur concerns
  - Quick preview scans
```

---

## 6. Calibration Procedures

### 6.1 Dark Frame Calibration

**Purpose**: Measure sensor dark current and fixed pattern noise

```python
def capture_dark_frame(cam, exposure_us, num_averages=10):
    """
    Capture dark frame with lens cap on

    Dark frame contains:
        - Thermal noise (dark current)
        - Fixed pattern noise (FPN)
        - Readout noise
        - Hot pixels

    Subtract from science images to improve quality
    """

    print(f"📷 Dark frame calibration")
    print(f"   Exposure: {exposure_us/1000:.1f}ms")
    print(f"   Averages: {num_averages}")
    print("   ⚠️  COVER LENS/SENSOR NOW")
    input("   Press Enter when covered...")

    # Configure camera
    cam.set_controls({
        "ExposureTime": exposure_us,
        "AnalogueGain": 1.0,  # Unity gain for dark frame
        "AwbEnable": False,
        "AeEnable": False
    })

    # Capture multiple frames
    darks = []
    for i in range(num_averages):
        time.sleep(0.2)
        img = cam.capture_array()
        gray = cv2.cvtColor(img[..., :3][:, :, ::-1], cv2.COLOR_BGR2GRAY)
        darks.append(gray.astype(np.float32))
        print(f"   [{i+1}/{num_averages}] Mean: {gray.mean():.2f}")

    # Average dark frames
    dark_master = np.mean(darks, axis=0).astype(np.float32)

    # Statistics
    print(f"\n✅ Dark frame captured")
    print(f"   Mean dark level: {dark_master.mean():.2f} ADU")
    print(f"   Std deviation: {dark_master.std():.2f} ADU")
    print(f"   Min/Max: {dark_master.min():.1f} / {dark_master.max():.1f}")

    # Save calibration
    dark_fname = f"dark_{exposure_us}us_gain1.0.npy"
    np.save(dark_fname, dark_master)
    print(f"💾 Saved: {dark_fname}")

    return dark_master


# Apply dark frame correction
def apply_dark_correction(science_image, dark_frame):
    """Subtract dark frame from science image"""
    corrected = science_image.astype(np.float32) - dark_frame
    corrected = np.clip(corrected, 0, 255).astype(np.uint8)
    return corrected


# Usage
dark = capture_dark_frame(cam, EXPOSURE_US, num_averages=10)
science = capture_image(cam, ...)
corrected = apply_dark_correction(science, dark)
```

### 6.2 Flat Field Calibration

**Purpose**: Correct for illumination non-uniformity and pixel response variation

```python
def capture_flat_field(cam, exposure_us, num_averages=10):
    """
    Capture flat field with uniform illumination

    Flat field contains:
        - OLED intensity variation
        - Lens vignetting (if using lens)
        - Pixel-to-pixel sensitivity variation
        - Dust/debris shadows

    Divide science images by normalized flat to correct
    """

    print(f"📷 Flat field calibration")
    print(f"   Exposure: {exposure_us/1000:.1f}ms")
    print(f"   ⚠️  ILLUMINATE UNIFORMLY")
    print(f"   (Use diffuse white OLED screen)")
    input("   Press Enter when ready...")

    # Configure camera
    cam.set_controls({
        "ExposureTime": exposure_us,
        "AnalogueGain": 1.0,
        "AwbEnable": False,
        "AeEnable": False
    })

    # Capture multiple frames
    flats = []
    for i in range(num_averages):
        time.sleep(0.2)
        img = cam.capture_array()
        gray = cv2.cvtColor(img[..., :3][:, :, ::-1], cv2.COLOR_BGR2GRAY)
        flats.append(gray.astype(np.float32))
        print(f"   [{i+1}/{num_averages}] Mean: {gray.mean():.2f}")

    # Average flat frames
    flat_master = np.mean(flats, axis=0).astype(np.float32)

    # Normalize to mean = 1.0
    flat_norm = flat_master / flat_master.mean()

    # Statistics
    print(f"\n✅ Flat field captured")
    print(f"   Mean: {flat_norm.mean():.3f} (should be 1.000)")
    print(f"   Variation: {flat_norm.std():.3f}")
    print(f"   Min/Max: {flat_norm.min():.3f} / {flat_norm.max():.3f}")

    # Save calibration
    flat_fname = f"flat_{exposure_us}us_gain1.0.npy"
    np.save(flat_fname, flat_norm)
    print(f"💾 Saved: {flat_fname}")

    return flat_norm


def apply_flat_correction(science_image, flat_field):
    """Divide science image by flat field"""
    corrected = science_image.astype(np.float32) / (flat_field + 1e-6)
    corrected = np.clip(corrected, 0, 255).astype(np.uint8)
    return corrected


# Usage
flat = capture_flat_field(cam, EXPOSURE_US, num_averages=10)
science = capture_image(cam, ...)
corrected = apply_flat_correction(science, flat)
```

### 6.3 Complete Calibration Workflow

```python
def full_calibration_correction(science, dark, flat):
    """
    Apply complete calibration pipeline

    Order of operations:
        1. Subtract dark frame
        2. Divide by flat field
        3. Clip to valid range

    Formula:
        Corrected = (Science - Dark) / Flat
    """

    # Step 1: Dark subtraction
    science_float = science.astype(np.float32)
    dark_corrected = science_float - dark

    # Step 2: Flat fielding
    flat_corrected = dark_corrected / (flat + 1e-6)

    # Step 3: Clip and convert
    final = np.clip(flat_corrected, 0, 255).astype(np.uint8)

    return final


# Complete workflow
# (Run once per exposure/gain setting)
print("=== CALIBRATION ===")
dark = capture_dark_frame(cam, EXPOSURE_US, 10)
flat = capture_flat_field(cam, EXPOSURE_US, 10)

print("\n=== SCIENCE ACQUISITION ===")
for i in range(49):  # FPM scan
    science_raw = capture_image(cam, ...)
    science_calibrated = full_calibration_correction(science_raw, dark, flat)
    save_image(science_calibrated, f"img_{i:03d}.tiff")
```

---

## 7. Troubleshooting

### 7.1 Common Issues

#### **Issue: Images too dark**

**Symptoms**:
- Mean pixel value < 30
- Histogram bunched at low end
- High noise, low SNR

**Diagnosis**:
```python
if gray.mean() < 30:
    print("⚠️ UNDEREXPOSURE")
```

**Solutions** (in priority order):
1. **Increase exposure time**:
   ```python
   EXPOSURE_US = min(500000, EXPOSURE_US * 2)  # Double exposure
   ```

2. **Increase OLED brightness**:
   ```python
   OLED_CONTRAST = min(255, OLED_CONTRAST + 20)
   ```

3. **Increase analog gain** (last resort):
   ```python
   ANALOG_GAIN = min(4.0, ANALOG_GAIN + 0.5)
   ```

#### **Issue: Images saturated**

**Symptoms**:
- Many pixels at 255
- Loss of detail in bright areas
- Saturation % > 1%

**Diagnosis**:
```python
sat_pct = 100 * (gray == 255).sum() / gray.size
if sat_pct > 1.0:
    print(f"⚠️ SATURATION: {sat_pct:.1f}% pixels clipped")
```

**Solutions**:
1. **Reduce exposure time**:
   ```python
   EXPOSURE_US = max(10000, EXPOSURE_US // 2)  # Halve exposure
   ```

2. **Reduce OLED brightness**:
   ```python
   OLED_CONTRAST = max(40, OLED_CONTRAST - 20)
   ```

3. **Verify not using gain** (should be 1.0):
   ```python
   ANALOG_GAIN = 1.0
   ```

#### **Issue: Inconsistent brightness between frames**

**Symptoms**:
- Mean intensity varies frame-to-frame
- FPM reconstruction fails
- Random brightness fluctuations

**Diagnosis**:
```python
means = [capture().mean() for _ in range(10)]
variation = np.std(means)
if variation > 5.0:
    print(f"⚠️ UNSTABLE: σ={variation:.1f}")
```

**Solutions**:
1. **Disable auto-exposure/white balance**:
   ```python
   AWB, AE = False, False  # CRITICAL
   ```

2. **Lock frame duration**:
   ```python
   cam.set_controls({
       "FrameDurationLimits": (EXPOSURE_US, EXPOSURE_US)
   })
   ```

3. **Allow settling time**:
   ```python
   time.sleep(0.15)  # Before capture
   ```

#### **Issue: Fixed pattern noise**

**Symptoms**:
- Persistent vertical/horizontal stripes
- "Jail bars" in flat areas
- Pattern doesn't change between frames

**Diagnosis**:
```python
# Capture flat field, check for patterns
flat = capture_uniform_illumination()
cv2.imwrite("diagnostic_flat.png", flat)
# Inspect for stripes/patterns
```

**Solutions**:
1. **Dark frame subtraction**:
   ```python
   corrected = image - dark_frame
   ```

2. **Flat field correction**:
   ```python
   corrected = (image - dark) / flat
   ```

3. **If persistent, check**:
   - EMI/electrical noise (shielding)
   - Bad sensor (RMA)

#### **Issue: Hot pixels / dead pixels**

**Symptoms**:
- Bright spots (hot pixels: always 255)
- Dark spots (dead pixels: always 0)
- Same locations across frames

**Diagnosis**:
```python
# Capture dark frame
dark = capture_with_lens_cap()

# Find hot pixels
hot_pixels = np.where(dark > 200)
print(f"Hot pixels: {len(hot_pixels[0])}")

# Find dead pixels
dead_pixels = np.where(dark == 0)
print(f"Dead pixels: {len(dead_pixels[0])}")
```

**Solutions**:
1. **Median filter** (for few bad pixels):
   ```python
   corrected = cv2.medianBlur(image, 3)
   ```

2. **Interpolation** (for known locations):
   ```python
   def fix_bad_pixels(img, bad_pixel_map):
       for (y, x) in bad_pixel_map:
           # Replace with median of neighbors
           neighbors = img[max(0,y-1):y+2, max(0,x-1):x+2]
           img[y, x] = np.median(neighbors)
       return img
   ```

3. **Cooling** (reduces dark current):
   - Add heatsink to sensor
   - Improve airflow
   - Reduce ambient temperature

---

## Appendix A: OV5647 Register Map (Relevant Subset)

**Note**: Raspberry Pi API abstracts registers, but for reference:

| Register | Function | Picamera2 Equivalent |
|----------|----------|----------------------|
| `0x3500-0x3502` | Exposure Value | `ExposureTime` |
| `0x350A-0x350B` | Analog Gain | `AnalogueGain` |
| `0x5001` | AWB Enable | `AwbEnable` |
| `0x3503` | AE/AG Manual | `AeEnable` |
| `0x3808-0x380A` | Horizontal Size | Config `size[0]` |
| `0x380C-0x380E` | Vertical Size | Config `size[1]` |

---

## Appendix B: Code Cross-Reference

| Concept | File | Lines | Description |
|---------|------|-------|-------------|
| **Camera init** | capturaclaude.py | 290-303 | Picamera2 setup |
| **Config creation** | capturaclaude.py | 291-292 | Preview/capture configs |
| **Parameter setting** | capturaclaude.py | 102-107 | set_controls() usage |
| **Exposure control** | capturaclaude.py | 379-386 | Interactive adjustment |
| **Gain control** | capturaclaude.py | 389-396 | Interactive adjustment |
| **Capture function** | capturaclaude.py | 98-126 | capturar_imagen() |
| **Scan loop** | capturaclaude.py | 160-221 | Grid iteration |
| **Metadata save** | capturaclaude.py | 188-206 | JSON format |

---

## Appendix C: Quick Reference

**Optimal Settings for FPM** (OV5647):
```python
# Camera parameters
CAPTURE_SIZE = (2592, 1944)    # Full resolution
EXPOSURE_US = 150000           # 150ms (adjust per sample)
ANALOG_GAIN = 1.0              # Unity gain (no amplification)
AWB = False                    # CRITICAL: disable auto WB
AE = False                     # CRITICAL: disable auto exposure

# Target metrics
TARGET_MEAN = 80-120           # ADU (40-50% of range)
MAX_SATURATION = 1.0           # % of pixels at 255
MIN_SNR = 20                   # Signal-to-noise ratio

# Quality checks
assert gray.mean() > 30, "Underexposure"
assert (gray == 255).sum() / gray.size < 0.01, "Saturation"
assert AWB == False and AE == False, "Auto modes enabled!"
```

---

**END OF DOCUMENT**

**Document prepared for**: INTISAT Mission - Payload Development
**Sensor**: OmniVision OV5647 CMOS Image Sensor
**Application**: Lensless Fourier Ptychographic Microscopy
**Last Updated**: 2025-12-05
