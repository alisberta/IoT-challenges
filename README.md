# IoT Challenges — Internet of Things Course

**Authors:** Marco Abbadessa (10854816), Alice Berta (10889590)
**Course:** Internet of Things — Politecnico di Milano
**Academic Year:** 2025–2026

## About

This repository collects the challenges developed for the Internet of Things course in the academic year 2025–2026. The work was carried out as a team of two.

Each challenge is split into two parts:

- a **practical challenge** on real IoT protocols and tools
- a **theoretical exercise** on the networking concepts covered in class

Each part has its own report.

## Challenges

| Challenge | Topic | Technologies | Folder |
|-----------|-------|--------------|--------|
| Challenge 2 | Packet sniffing and energy analysis | Wireshark, CoAP, MQTT, MQTT-SN, Python | [`packet-sniffing/`](packet-sniffing/) |
| Challenge 3 | Node-RED flow and LoRaWAN capacity | Node-RED, MQTT, ZigBee, ThingSpeak, LoRaWAN | [`node-red/`](node-red/) |

Each folder contains its own README describing the following:

- the tasks
- the approach followed
- the results obtained
- how to run the code

## Repository Structure

```
IoT-challenges/
├── packet-sniffing/     # Challenge 2: Wireshark analysis of CoAP / MQTT / MQTT-SN traffic
├── node-red/            # Challenge 3: Node-RED flow + LoRaWAN exercise
└── README.md
```

## Tools

| Tool | Used for |
|------|----------|
| Wireshark / tshark | Capture inspection and protocol filtering |
| Python (`pyshark`, `matplotlib`) | Automated packet analysis and plots |
| Mosquitto | Local MQTT broker |
| Node-RED + `@flowfuse/node-red-dashboard` | Flow design and real-time charts |
| ThingSpeak | Public cloud data channel |
| LaTeX | Reports |

## Delivery

Each challenge was submitted on WeBeep as a ZIP archive named `<leader_personcode>_<other_personcode>.zip`. The answers were also entered in the course MS Form.

## Disclaimer

This repository contains coursework produced for academic purposes. If you are taking the same course, use it as a reference only, in accordance with the course rules on academic integrity.
