# IoT Challenge 2 — Packet Sniffing

**Authors:** Marco Abbadessa (10854816, leader), Alice Berta (10889590)
**Course:** IoT Systems — Academic Year 2025–2026

## Overview

Analysis of two network captures (`A.pcapng` and `B.pcapng`) containing IoT traffic over **CoAP**, **MQTT** and **MQTT-SN**. The goal is to answer eight protocol-level questions (CQ1–CQ8) by inspecting the traffic with Wireshark and, where useful, with Python scripts. Malformed packets are ignored, as required by the challenge.

The challenge is split into two parts:

| Part | Content | Deliverable |
|------|---------|-------------|
| Part 1 | Packet analysis, questions CQ1–CQ8 | `Challenge.pdf` |
| Part 2 | Energy exercise on a smart-building scenario, questions EQ1–EQ2 | `Exercise.pdf` |

Question-to-file mapping for Part 1:

| Questions | Capture file | Protocols |
|-----------|--------------|-----------|
| CQ1–CQ4 | `A.pcapng` | CoAP, MQTT-SN |
| CQ5–CQ7 | `B.pcapng` | MQTT |
| CQ8 | both | MQTT (local broker) |

## Preliminary Network Analysis

Before answering the questions, the main endpoints in each capture were identified.

**A.pcapng**

| Entity | Address | How it was found |
|--------|---------|------------------|
| `coap.me` public server | `134.102.218.18` | `dns.qry.name contains "coap.me"` |
| Local CoAP server | `127.0.0.1` | loopback destination |
| Local MQTT-SN broker | UDP port `1885` | given by the challenge |

**B.pcapng**

| Entity | Address | How it was found |
|--------|---------|------------------|
| Local MQTT broker | `::1` (IPv6 loopback) | destination of `mqtt.msgtype == 1` frames |
| Public HiveMQ broker | `18.192.151.104`, `35.158.43.69` | `dns.qry.name contains "hivemq"`, cross-checked against MQTT traffic |
| Other public broker | `5.196.78.28` | carries MQTT traffic, not resolved from HiveMQ |

DNS resolved `broker.hivemq.com` to a third address (`35.158.34.213`), but it never appears in MQTT frames.

## How Each Question Was Solved

### CQ1 — NON DELETE requests to coap.me (A.pcapng)

1. Isolated Non-Confirmable DELETE requests to `coap.me`:
   `ip.dst == 134.102.218.18 and coap.type == 1 and coap.code == 4`
2. Since NON requests get no ACK, each response was matched to its request through the **CoAP Token** (`coap.token == <token>`).
3. A response was considered successful if its code was `2.02 Deleted`.
4. For CQ1b, the payload of the successful response was inspected to check that a resource was actually removed (`DELETE OK`).

### CQ2 — Equal unsuccessful CON POST/PUT per resource (A.pcapng)

1. Filtered CON POST and CON PUT requests to the local server:
   `ip.dst == 127.0.0.1 and coap.type == 0 and coap.code == 2` (POST)
   `ip.dst == 127.0.0.1 and coap.type == 0 and coap.code == 3` (PUT)
2. Duplicate MIDs (retransmissions) were discarded to keep only unique requests.
3. A request counted as unsuccessful only when the server replied with a `4.xx` or `5.xx` code.
4. Counts X (POST) and Y (PUT) were tallied per `Uri-Path`, and resources with X = Y > 0 were counted.

### CQ3 — Observe notifications for `/dining_room/temperature` (A.pcapng)

1. Found the observe registration: `coap.opt.uri_path contains "temperature" and coap.opt.observe == 0` (MID 10588, Token `89b9`).
2. Followed all notifications sharing that token: `coap.token == 89:b9`.
3. Excluded the piggybacked first response (carried in the ACK) since only *separate* notifications count, and ignored retransmissions by keeping unique MIDs only.
4. For CQ3b, a notification was considered useless if it carried an unchanged value or was sent to a client that was no longer listening (followed by an ICMP Port Unreachable).

### CQ4 — MQTT-SN messages from the broker on port 1885 (A.pcapng)

1. Configured Wireshark to decode UDP port 1885 as MQTT-SN (*Edit → Preferences → Protocols → MQTT-SN*).
2. Filtered broker-to-client traffic: `udp.srcport == 1885 and mqttsn`.
3. No packets matched: port 1885 only appears as a destination, and every client packet is answered by an ICMP Port Unreachable, showing that the broker was not listening.

### CQ5 — Last Will received through wildcard subscriptions (B.pcapng)

1. Found clients declaring a Last Will: `mqtt.msgtype == 1 and mqtt.conflag.willflag == 1`.
2. The three wills on broker `5.196.78.28` were discarded because that broker has no subscribers (`mqtt.msgtype == 8 and ip.dst == 5.196.78.28` returns nothing).
3. For the will on the local broker, checked for the absence of a DISCONNECT and confirmed the will was published on `university/department12/room1/temperature`.
4. Matched that topic against wildcard subscriptions to `::1` (`mqtt.topic contains "#"` / `"+"`).

### CQ6 — Clients erasing retained messages on HiveMQ (B.pcapng)

1. A retained message is erased by a PUBLISH with `retain = 1` and an empty payload:
   `mqtt.msgtype == 3 and mqtt.retain == 1 and (ip.dst == 18.192.151.104 or ip.dst == 35.158.43.69)`
2. Kept only frames with empty payload and grouped them by `tcp.stream` (one stream = one client connection).
3. For CQ6b, the CONNECT frame of each stream was inspected to read the Client ID length.

### CQ7 — Local subscriptions with at least two wildcards (B.pcapng)

1. Filtered wildcard subscriptions to the local broker:
   `mqtt.msgtype == 8 and ipv6.dst == ::1 and (mqtt.topic contains "+" or mqtt.topic contains "#")`
2. Counted the wildcard symbols in each topic and kept those with two or more.

### CQ8 — Topic depth of PUBLISH messages to the local broker (both files)

A Python script based on `pyshark` and `matplotlib`:

1. Reads each capture with the display filter `mqtt.msgtype == 3`.
2. Keeps only packets whose destination is the loopback address (`127.0.0.1` or `::1`).
3. Computes the number of topic layers by splitting the topic on `/`.
4. Counts messages per depth and plots a grouped histogram comparing A and B.

## Results

| Question | Answer |
|----------|--------|
| CQ1a | 1 |
| CQ1b | 1 |
| CQ2 | 1 |
| CQ3a | 10 |
| CQ3b | 5 |
| CQ4 | 0 |
| CQ5 | 1 |
| CQ6a | 5 |
| CQ6b | 2 |
| CQ7 | 9 |
| CQ8a | 706 |
| CQ8b | 1177 |

Full motivations, filters and screenshots are in `Challenge.pdf`.

## Part 2 — Exercise

A smart-building system with a battery-powered temperature sensor (one measurement every 2 minutes), a battery-powered fan actuator and a mains-powered MQTT-only gateway. Sensor and actuator can talk either directly over CoAP (CON messages) or through the gateway over MQTT (QoS 1).

- **EQ1:** total communication energy of sensor and actuator over 1 hour, for (a) CoAP and (b) MQTT, using the given message sizes and E_TX = 50 nJ/bit, E_RX = 58 nJ/bit.
- **EQ2:** protocol choice when the actuator wakes up only every 30 minutes, stating the protocol parameters used and the metric optimized.

The full solution is in `Exercise.pdf`.

## Repository Structure

```
packet-sniffing/
├── captures/
│   ├── A.pcapng
│   └── B.pcapng
├── scripts/
│   └── cq8_topic_depth.py          # CQ8 analysis and histogram
├── image/
│   └── mqtt_topic_depth_comparison.png
├── Challenge.tex                   # Part 1 report (CQ1–CQ8)
├── Exercise.tex                    # Part 2 report (EQ1–EQ2)
└── compile.sh                      # Script to compile the reports
```

## Running the CQ8 Script

Install the dependencies (`pyshark` also requires `tshark`, which ships with Wireshark):

```
pip install pyshark matplotlib numpy
```

Run from the folder containing the captures:

```
python scripts/cq8_topic_depth.py
```

The script prints the CQ8a and CQ8b totals and saves the plot as `mqtt_topic_depth_comparison.png`.

## Report

To compile the reports:

```
bash compile.sh
```

Requires a LaTeX distribution with `pdflatex` (e.g., TeX Live or MiKTeX).

## Delivery

The ZIP file `10854816_10889590.zip` contains `Challenge.pdf` and `Exercise.pdf`, and the answers for both parts are also submitted through the course MS Form.