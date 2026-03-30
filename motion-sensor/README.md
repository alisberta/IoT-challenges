# IoT Challenge 1 — ESP32 Motion Sensor Node

**Authors:** Marco Abbadessa (10854816), Alice Berta (10889590)
**Course:** IoT Systems — Academic Year 2025–2026

---

## Overview

Design and emulation of a battery-powered IoT motion sensor node for a smart-home scenario. The node is based on an ESP32 board and follows a duty-cycled strategy to minimize energy consumption: sense → transmit → deep sleep → repeat.

The transmitted message follows one of two formats:

```
MOTION_DETECTED-LUMINOSITY:<value>
MOTION_NOT_DETECTED-LUMINOSITY:<value>
```

---

## Hardware

Simulated in [Wokwi](https://wokwi.com/):

| Component | Pin |
|---|---|
| ESP32 dev board | — |
| PIR motion sensor | GPIO 13 (digital) |
| Photoresistor (LDR) | GPIO 34 (analog, 12-bit ADC) |

The LDR is wired in a voltage-divider configuration with a 10 kΩ resistor to map light intensity to a 0–4095 ADC reading.

---

## Communication

- **Protocol:** ESP-NOW (IEEE 802.11 Wi-Fi layer)
- **Addressing:** broadcast (`FF:FF:FF:FF:FF:FF`)
- **Assumption:** sink node is always reachable

---

## Execution Cycle

Each wake-up cycle goes through these phases:

1. **Boot** — serial init, boot counter increment
2. **Sensing** — PIR read + LDR ADC read (~430 µs)
3. **WiFi + ESP-NOW init** — mode set, peer registration (~196 ms)
4. **TX** — send message via ESP-NOW, wait for callback
5. **Deep Sleep** — timer-based wake-up after X seconds

---

## Challenge Parameters

Parameters are derived from the leader code (`10889590`):

| Parameter | Formula | Value |
|---|---|---|
| Deep sleep duration (X) | `(AB % 50 + 5) / 10` | **4.5 s** |
| Battery energy (Y) | `ABCD % 5000 + 15000` | **9590 J** |

where `AB = leader_code % 100` and `ABCD = leader_code % 10000`.

---

## Repository Structure

```
motion-sensor/
├── esp32-motion-sensor/          # Baseline firmware (PlatformIO)
│   ├── src/esp32.ino
│   ├── platformio.ini
│   └── wokwi.toml
├── esp32-motion-sensor-best/     # Optimized firmware (PlatformIO)
│   ├── src/esp32.ino
│   ├── platformio.ini
│   └── wokwi.toml
├── data/                         # Power profiling CSVs from Wokwi
│   ├── deep_sleep.csv
│   ├── sender.csv
│   └── sensor-read.csv
├── image/                        # Figures used in the report
│   ├── circuit.png
│   ├── plot1.png
│   └── plot2.png
├── main.py                       # Baseline energy analysis script
├── main-best.py                  # Optimized energy analysis script
├── report.tex                    # Full LaTeX report
└── compile.sh                    # Script to compile the report
```

---

## Energy Analysis

The Python scripts compute the energy consumed per duty cycle and estimate the total battery lifetime.

**Run the baseline analysis:**
```bash
cd motion-sensor
python main.py
```

**Run the optimized analysis:**
```bash
python main-best.py
```

Both scripts load power measurements from the CSV files, compute mean power per phase, and generate a step-plot of the power profile over one full cycle.

**Dependencies:**
```bash
pip install pandas matplotlib
```

---

## Optimizations (Best Version)

Four improvements were applied to reduce energy per cycle:

| # | Improvement | Effect |
|---|---|---|
| 1 | Replace `delay(100)` with a `volatile bool` callback flag | t_tx: 99.3 ms → 1.26 ms |
| 2 | Increase deep sleep duration | More time in low-power state |
| 3 | Reduce TX power from 19.5 dBm to 2 dBm | Lower p_tx |
| 4 | Reduce boot `delay` from 1 s to 10 ms | t_boot: 1 s → 10 ms |

---

## Build & Flash (PlatformIO)

```bash
cd esp32-motion-sensor        # or esp32-motion-sensor-best
pio run                       # compile
pio run --target upload       # flash to device
```

Alternatively, open the project in VS Code with the PlatformIO extension.

---

## Report

The full analysis is written in `report.tex`. To compile:

```bash
cd motion-sensor
bash compile.sh
```

Requires a LaTeX distribution with `pdflatex` (e.g., TeX Live or MiKTeX).
