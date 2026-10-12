# IoT Challenge 3 — Node-RED + LoRaWAN

**Authors:** Alice Berta (10889590, leader), Marco Abbadessa (10854816)
**Course:** IoT Systems — Academic Year 2025–2026

## Overview

Design and implementation of a **Node-RED** flow that integrates **MQTT** messaging with **ZigBee** packet processing (from `challenge3.csv`), real-time dashboard charting and publishing to a public **ThingSpeak** channel. A second part covers a theoretical exercise on **LoRaWAN** capacity.

The challenge is split into two parts:

| Part | Content | Deliverable |
|------|---------|-------------|
| Part 1 | Node-RED flow, tasks 1–3 | `Challenge.pdf`, `nodered.txt`, CSV files, ThingSpeak channel |
| Part 2 | LoRaWAN exercise, questions EQ1–EQ2 | `Exercise.pdf` |

Task-to-output mapping for Part 1:

| Task | Points | Content | Output |
|------|--------|---------|--------|
| Task 1 | 1 | Periodic MQTT publisher | `id_log.csv` |
| Task 2 | 2 | Subscriber, ZBEE_ZCL publishing, attribute filtering, charts | `filtered_elems.csv`, dashboard |
| Task 3 | 2 | Link Status costs, ThingSpeak upload | `outgoing_cost.csv`, ThingSpeak channel |

## Flow Overview

A single Node-RED tab with two branches sharing the same local Mosquitto broker (`localhost:1884`):

| Branch | Role |
|--------|------|
| Publisher | Generates a random `id` and a UNIX timestamp every second, publishes them on `challenge3/id_generator` and logs them to `id_log.csv` |
| Subscriber | Subscribes to `challenge3/id_generator`, computes `N = id mod 5218`, fetches row `N` from `challenge3.csv` and routes it to the ZigBee ZCL path, the Link Status path, or discards it |

The subscriber stops after exactly **200** received messages; ignored messages still count toward the limit.

## How Each Task Was Solved

### Task 1 — Publisher flow

1. An **Inject** node (`1s Trigger`) fires every second.
2. A **Function** node (`Generate ID + Timestamp`) builds `{"id": <0–30000>, "timestamp": <UNIX time>}` and serialises it to a JSON string.
3. An **MQTT Out** node publishes the payload to `challenge3/id_generator` on `localhost:1884`.
4. In parallel, a **Function** node (`Format CSV row`) keeps an incremental counter in node context and formats the row `No.,ID,TIMESTAMP`, adding the header on the first row only.
5. A **File** node appends each row to `id_log.csv` (automatic newline disabled, since line breaks are already in the payload).

### Task 2 — Subscriber branch with ZigBee processing

1. **MQTT In** subscribes to `challenge3/id_generator`.
2. **Counter + ID** keeps a flow-scoped message counter, drops everything after 200, computes `N = id mod 5218` and, at message 200, emits a `save` trigger on its second output (used by Task 3).
3. **Read challenge3.csv** (File In) loads the whole CSV as a UTF-8 string; the path comes from `msg.filename`.
4. **Find Row N** uses a custom quote-aware parser (the `Command String` column contains commas inside quoted substrings, so the built-in CSV node cannot be used) and stores the matching row in `msg.row`.
5. **Contains ZBEE_ZCL?** (Switch) forwards only rows whose `Command String` contains `ZBEE_ZCL`.
6. **Rate Limit — 10 msg/min** (Delay node, rate-limit mode) queues messages without dropping them.
7. **Build MQTT Payload** assembles the required JSON and sets the dynamic topic `ZigBee/<Device Name ZigBee Source>` (the device name is sanitised for MQTT); an **MQTT Out** node publishes it.
8. **Extract RMS / Active Power Attrs** converts the Python-style dictionary in `Command String` to JSON, keeps only Read Attributes Responses (packets with a `Status` key), and matches `Attribute`, `Status`, `Data Type` and value **by position**, consuming `Int16` or `Uint16` values according to the data type.
9. **Format filtered_elems.csv** writes rows `No.,Timestamp,Sequence Number,Attribute,Status,Data Type,Data Value` (header written once), appended by a File node.
10. **Chart Split** (two outputs) sends RMS Current and RMS Voltage to two line charts on the dashboard (`@flowfuse/node-red-dashboard`, page *ZigBee Monitor*, group *Electrical Measurements*).

Published payload format:

```json
{
  "timestamp": CURRENT_TIMESTAMP,
  "id": SUB_ID,
  "wpan.src": "SRC_ADDR",
  "wpan.dst": "DST_ADDR",
  "zbee.src": "ZB_SRC_ADDR",
  "zbee.dst": "ZB_DST_ADDR",
  "topic": "ZigBee/ZB_SRC_DEV_NAME",
  "payload": CMD_STR
}
```

### Task 3 — Link Status handling and ThingSpeak publishing

1. **Process Link Status** handles rows whose `Packet Type` is `Link Status (0x08)`: a regex extracts every `{Address, Incoming Cost, Outgoing Cost}` entry, and the outgoing costs are stored in `flow.costTable[source][destination]`. A later packet from the same source overwrites the stored values.
2. When the 200-message limit is reached, **Generate outgoing_cost.csv** serialises the table as `No.,Source,Destination,Cost`, and a File node overwrites `outgoing_cost.csv`.
3. **Prepare ThingSpeak Messages** selects the source with the smallest address (parsed as hexadecimal), sorts its destinations in ascending hexadecimal order and stores the ordered list in flow context.
4. **Format HTTP ThingSpeak** builds `https://api.thingspeak.com/update?api_key=<KEY>&field1=<cost>`; an **HTTP Request** node sends it.
5. **Next ThingSpeak Msg** advances the index and, through a **Delay 20s** node, loops back to the formatter, enforcing one update every 20 seconds until all destinations are sent.

## Results

| Output | Content |
|--------|---------|
| `id_log.csv` | One row per published ID (`No.,ID,TIMESTAMP`) |
| `filtered_elems.csv` | RMS Current, RMS Voltage and Active Power attributes extracted from ZBEE_ZCL packets |
| `outgoing_cost.csv` | Last known outgoing cost for every (source, destination) link |
| Dashboard | Real-time RMS Current and RMS Voltage charts at `http://localhost:1880/ui` |
| ThingSpeak | Public channel [3378810](https://thingspeak.mathworks.com/channels/3378810), costs in `field1` |

Full explanations, code listings and screenshots are in `Challenge.pdf`.

## Part 2 — Exercise

A European LoRaWAN network (868 MHz, 125 kHz bandwidth) with one gateway and 40 nodes, each sending 20-byte packets as a Poisson process with λ = 2 packets/minute.

- **EQ1:** largest spreading factor guaranteeing a packet success rate of at least 75%, under an unslotted-ALOHA collision model with all nodes on the same SF, using the TTN airtime calculator for the time on air.
- **EQ2:** given a measured success rate much lower than expected and very uneven across nodes, choose the most appropriate action (fewer nodes, nodes closer to the gateway, higher SF) and justify it.

The full solution is in `Exercise.pdf`.

## Repository Structure

```
node-red/
├── challenge3.csv                  # Input ZigBee packet dataset
├── nodered.txt                     # Node-RED flow export (JSON)
├── output/
│   ├── id_log.csv
│   ├── filtered_elems.csv
│   └── outgoing_cost.csv
├── image/                          # Flow, dashboard and ThingSpeak screenshots
├── Challenge.tex                   # Part 1 report
├── Exercise.tex                    # Part 2 report
└── compile.sh                      # Script to compile the reports
```

## Running the Flow

1. Start Mosquitto on port 1884:
   ```
   mosquitto -p 1884
   ```
2. Install the dashboard package from the Node-RED palette manager (or via npm in `~/.node-red`):
   ```
   npm install @flowfuse/node-red-dashboard
   ```
3. Import `nodered.txt` in Node-RED (*Menu → Import*) and deploy.
4. Update the file paths (`csvPath` and the File nodes) to match your local folder, and set your ThingSpeak Write API Key in the *Format HTTP ThingSpeak* node.
5. Reset the flow context (`msgCount`, `filteredCount`, `filteredHeader`, `costTable`) before a new run, otherwise the 200-message limit and the CSV headers carry over from the previous execution.
6. Open the dashboard at `http://localhost:1880/ui`.

## Report

To compile the reports:

```
bash compile.sh
```

Requires a LaTeX distribution with `pdflatex` (e.g., TeX Live or MiKTeX).

## Delivery

The ZIP file `10889590_10854816.zip` (leader first) contains `Challenge.pdf`, `Exercise.pdf`, `nodered.txt`, `id_log.csv`, `filtered_elems.csv` and `outgoing_cost.csv`. The ThingSpeak channel is public, and the CSV values and channel ID are also submitted through the course MS Form.