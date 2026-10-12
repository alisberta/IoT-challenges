#!/usr/bin/env python3
"""
IoT Challenge #2 - Analisi di B.pcapng
Risponde alle domande CQ5, CQ6a, CQ6b, CQ7

CQ5:  Quanti subscriber MQTT ricevono un last will message derivato da una
      subscription che include almeno un wildcard?

CQ6a: Quanti client MQTT DIVERSI hanno inviato almeno un messaggio per
      cancellare un valore retained su un topic del broker pubblico HiveMQ?

CQ6b: Quanti dei client trovati in CQ6a si sono connessi a HiveMQ con un
      client identifier strettamente più lungo di 7 byte (>7)?

CQ7:  Quante SUBSCRIBE request dirette al broker LOCALE specificano un topic
      con almeno DUE wildcard?
"""

import ipaddress
from collections import defaultdict
from scapy.all import rdpcap, TCP, IP
from scapy.contrib.mqtt import (
    MQTT, MQTTConnect, MQTTPublish, MQTTSubscribe, MQTTDisconnect, MQTTTopicQOS
)

# ─── Configurazione ────────────────────────────────────────────────────────────
PCAP_FILE = "coap-mqtt/B.pcapng"
MQTT_PORT = 1883

# Identificati dai DNS nel pcap:
#   broker.hivemq.com  → 18.192.151.104 e 35.158.43.69  (HiveMQ pubblico)
#   test.mosquitto.org → 5.196.78.28                     (broker "locale" del lab)
HIVEMQ_IPS    = {'18.192.151.104', '35.158.43.69'}
LOCAL_BROKER  = {'5.196.78.28'}

# ─── Utility ───────────────────────────────────────────────────────────────────

def is_hivemq(ip_str):
    """Restituisce True se l'IP appartiene al cluster HiveMQ pubblico."""
    return ip_str in HIVEMQ_IPS

def is_local_broker(ip_str):
    """Restituisce True se l'IP è il broker locale del lab (test.mosquitto.org)."""
    return ip_str in LOCAL_BROKER

def mqtt_topic_matches(filter_str, topic_str):
    """
    Verifica se topic_str corrisponde al filter MQTT.
    Regole wildcard:
      '+' corrisponde esattamente a un livello del topic
      '#' corrisponde a tutto il resto (deve essere l'ultimo livello)
    """
    f_parts = filter_str.split('/')
    t_parts = topic_str.split('/')

    fi, ti = 0, 0
    while fi < len(f_parts):
        fp = f_parts[fi]
        if fp == '#':
            return True          # corrisponde a qualsiasi resto
        if ti >= len(t_parts):
            return False         # topic più corto del filtro
        if fp != '+' and fp != t_parts[ti]:
            return False         # livello non corrisponde
        fi += 1
        ti += 1

    return ti == len(t_parts)   # filtro e topic devono terminare insieme

def count_wildcards(topic_str):
    """Conta il numero di wildcard ('+' e '#') in un topic/filtro."""
    return topic_str.count('+') + topic_str.count('#')

def decode_str(raw):
    """Decodifica bytes in stringa UTF-8, gestisce sia bytes che str."""
    if isinstance(raw, bytes):
        return raw.decode('utf-8', errors='replace')
    return str(raw)

def parse_mqtt_from_tcp(pkt):
    """
    Estrae tutti i messaggi MQTT da un segmento TCP.
    Un segmento può contenere più messaggi MQTT concatenati.
    Restituisce una lista di oggetti MQTT.
    """
    if not pkt[TCP].payload:
        return []

    raw = bytes(pkt[TCP].payload)
    messages = []
    offset = 0

    while offset < len(raw):
        try:
            msg = MQTT(raw[offset:])
            messages.append(msg)
            # La lunghezza totale del messaggio è: 1 (byte tipo/flags) +
            # dimensione del campo len variabile + remaining length
            # scapy calcola il campo 'len' come remaining_length
            # Lunghezza totale = header fisso + remaining_length
            remaining = msg.len  # remaining length dichiarata
            # stima del numero di byte per il campo len (variabile, 1-4 byte)
            tmp = remaining
            len_field_bytes = 1
            while tmp > 127:
                tmp >>= 7
                len_field_bytes += 1
            total_len = 1 + len_field_bytes + remaining
            offset += total_len
        except Exception:
            break

    return messages


# ─── Caricamento PCAP ──────────────────────────────────────────────────────────
print(f"Carico {PCAP_FILE}...")
packets = rdpcap(PCAP_FILE)
print(f"Pacchetti totali nel file: {len(packets)}\n")
print(f"Broker HiveMQ (pubblico) : {HIVEMQ_IPS}")
print(f"Broker locale lab        : {LOCAL_BROKER}\n")

# ─── Strutture dati principali ─────────────────────────────────────────────────

# Chiave connessione: (client_ip, client_port)  →  lato client di ogni sessione TCP su porta 1883
conn_to_broker   = {}                   # c_key → broker_ip
client_ids       = {}                   # c_key → client_id (str)
will_info        = {}                   # c_key → {'topic': str, 'broker': str}  (solo se willflag==1)
subscriptions    = defaultdict(list)    # c_key → [topic_filter, ...]  (include broker_ip nella chiave)
graceful_disc    = set()                # c_key dei client che hanno inviato MQTT DISCONNECT
tcp_closed       = set()               # c_key dei client con TCP FIN/RST

# ─── Seconda passata: analisi MQTT ─────────────────────────────────────────────
for pkt in packets:
    if IP not in pkt or TCP not in pkt:
        continue

    tcp = pkt[TCP]
    ip  = pkt[IP]

    # Rileva chiusure TCP (FIN o RST)
    if (tcp.flags & 0x01) or (tcp.flags & 0x04):   # FIN | RST
        if tcp.dport == MQTT_PORT:
            tcp_closed.add((ip.src, tcp.sport))
        elif tcp.sport == MQTT_PORT:
            tcp_closed.add((ip.dst, tcp.dport))

    # Solo pacchetti su porta MQTT con payload
    if MQTT_PORT not in (tcp.dport, tcp.sport) or not tcp.payload:
        continue

    # Direzione: client→broker se dport==1883, broker→client altrimenti
    client_to_broker_dir = (tcp.dport == MQTT_PORT)

    if client_to_broker_dir:
        c_ip, c_port = ip.src, tcp.sport
        b_ip, b_port = ip.dst, tcp.dport
    else:
        c_ip, c_port = ip.dst, tcp.dport
        b_ip, b_port = ip.src, tcp.sport

    c_key = (c_ip, c_port)
    conn_to_broker[c_key] = (b_ip, b_port)

    # Parsa tutti i messaggi MQTT nel payload TCP
    msgs = parse_mqtt_from_tcp(pkt)

    for msg in msgs:
        if MQTT not in msg:
            continue

        ptype = msg[MQTT].type

        # ── CONNECT (type=1) ──────────────────────────────────────────────────
        if ptype == 1 and MQTTConnect in msg:
            conn = msg[MQTTConnect]

            # Salva client ID
            try:
                cid = decode_str(conn.clientId)
                client_ids[c_key] = cid
            except Exception:
                client_ids[c_key] = ""

            # Salva will se presente
            if conn.willflag == 1:
                try:
                    wtopic = decode_str(conn.willtopic)
                    will_info[c_key] = {'topic': wtopic, 'broker': b_ip}
                except Exception:
                    pass

        # ── SUBSCRIBE (type=8) ────────────────────────────────────────────────
        elif ptype == 8 and MQTTSubscribe in msg and client_to_broker_dir:
            sub = msg[MQTTSubscribe]
            if hasattr(sub, 'topics') and sub.topics:
                for tq in sub.topics:
                    try:
                        tf = decode_str(tq.topic)
                        # La chiave include l'IP del broker per distinguere
                        subscriptions[c_key].append((tf, b_ip))
                    except Exception:
                        pass

        # ── PUBLISH (type=3) ──────────────────────────────────────────────────
        elif ptype == 3 and MQTTPublish in msg:
            pub = msg[MQTTPublish]
            try:
                pub_topic   = decode_str(pub.topic)
                pub_payload = pub.value if isinstance(pub.value, bytes) else pub.value.encode()
                retain_flag = msg[MQTT].RETAIN
            except Exception:
                continue

            # Memorizza i PUBLISH per uso in CQ6 (li processiamo sotto)
            # Salviamo una tupla (c_key, b_ip, pub_topic, payload_len, retain)
            # direttamente nel dizionario publish_events
            if client_to_broker_dir:
                if not hasattr(parse_mqtt_from_tcp, '_publish_events'):
                    parse_mqtt_from_tcp._publish_events = []
                parse_mqtt_from_tcp._publish_events.append(
                    (c_key, b_ip, pub_topic, len(pub_payload), retain_flag)
                )
                conn_to_broker[c_key] = b_ip

        # ── DISCONNECT (type=14) ──────────────────────────────────────────────
        elif ptype == 14 and client_to_broker_dir:
            graceful_disc.add(c_key)

# Recupera publish events (trick per evitare una terza passata)
publish_events = getattr(parse_mqtt_from_tcp, '_publish_events', [])


# ══════════════════════════════════════════════════════════════════════════════
# CQ7: SUBSCRIBE al broker locale (test.mosquitto.org) con almeno 2 wildcard
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("CQ7 — SUBSCRIBE al broker LOCALE (test.mosquitto.org) con ≥ 2 wildcard")
print("=" * 60)

cq7_count = 0
for c_key, topic_broker_pairs in subscriptions.items():
    for (tf, b_ip) in topic_broker_pairs:
        if not is_local_broker(b_ip):
            continue
        wc = count_wildcards(tf)
        if wc >= 2:
            cq7_count += 1
            print(f"  Client {c_key[0]}:{c_key[1]}  topic: '{tf}'  (wildcards: {wc})")

print(f"\n>>> CQ7 RISPOSTA: {cq7_count}\n")


# ══════════════════════════════════════════════════════════════════════════════
# CQ6a: Client che cancellano un valore retained su HiveMQ (broker.hivemq.com)
# Cancellare un retained = PUBLISH con retain=1 e payload vuoto (0 byte)
# DNS: broker.hivemq.com → 18.192.151.104 e 35.158.43.69
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("CQ6a — Client che cancellano retained value sul broker HiveMQ PUBBLICO")
print("=" * 60)

# Raccoglie i client unici che hanno inviato almeno un retain-clear a HiveMQ
retain_clear_clients = set()   # c_key dei client

for (c_key, b_ip, pub_topic, payload_len, retain_flag) in publish_events:
    if not is_hivemq(b_ip):          # filtra solo il broker HiveMQ
        continue
    # Retain=1 + payload vuoto = cancellazione del retained value
    if retain_flag == 1 and payload_len == 0:
        retain_clear_clients.add(c_key)
        print(f"  Client {c_key[0]}:{c_key[1]} ({b_ip})  topic: '{pub_topic}'  "
              f"clientId: '{client_ids.get(c_key, '?')}'")

print(f"\n>>> CQ6a RISPOSTA: {len(retain_clear_clients)}\n")


# ══════════════════════════════════════════════════════════════════════════════
# CQ6b: Quanti dei client in CQ6a hanno clientId > 7 byte?
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("CQ6b — Client in CQ6a con clientId strettamente > 7 byte")
print("=" * 60)

cq6b_count = 0
for c_key in retain_clear_clients:
    cid = client_ids.get(c_key, "")
    cid_len = len(cid.encode('utf-8'))   # lunghezza in byte
    status = "OK (>7)" if cid_len > 7 else f"NO ({cid_len}B)"
    print(f"  Client {c_key[0]}:{c_key[1]}  clientId: '{cid}'  "
          f"len={cid_len}B  {status}")
    if cid_len > 7:
        cq6b_count += 1

print(f"\n>>> CQ6b RISPOSTA: {cq6b_count}\n")


# ══════════════════════════════════════════════════════════════════════════════
# CQ5: Subscriber che ricevono un last will message tramite wildcard subscription
#
# Logica:
#   1. Identifica i client con will (CONNECT willflag=1) che si disconnettono
#      in modo INATTESO (TCP chiuso senza MQTT DISCONNECT precedente).
#   2. Il broker dove era connesso il client pubblica il will_topic.
#   3. Trova i subscriber sullo STESSO broker con wildcard che corrispondono
#      al will_topic.
#   4. Conta i subscriber UNICI che ricevono il messaggio.
#
# Nota: Il will è su test.mosquitto.org (5.196.78.28).
#       I subscriber sono identificati in base alle loro SUBSCRIBE request.
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("CQ5 — Subscriber che ricevono last will via wildcard subscription")
print("=" * 60)

# Disconnessioni inattese = TCP chiuso SENZA MQTT DISCONNECT
unexpected_disc = tcp_closed - graceful_disc

print(f"Client con will         : {len(will_info)}")
print(f"Client con MQTT DISC    : {len(graceful_disc)}")
print(f"Disconnessioni TCP      : {len(tcp_closed)}")
print(f"Disconnessioni inattese : {len(unexpected_disc)}")

# Raccoglie i (will_topic, broker_ip) effettivamente "scattati"
triggered_wills = []
for c_key in unexpected_disc:
    if c_key in will_info:
        wt     = will_info[c_key]['topic']
        broker = will_info[c_key]['broker']
        triggered_wills.append((wt, broker))
        print(f"  Will scattato: client {c_key}  broker={broker}  topic='{wt}'")

if not triggered_wills:
    print("  (nessuna disconnessione inattesa con will rilevata)")

# Per ogni will scattato, trova i subscriber con wildcard sullo STESSO broker
cq5_subscribers = set()   # c_key dei subscriber che ricevono il will

for (will_topic, will_broker) in triggered_wills:
    print(f"\n  Ricerca subscriber su broker={will_broker} per topic='{will_topic}':")
    for sub_key, topic_broker_pairs in subscriptions.items():
        for (filt, b_ip) in topic_broker_pairs:
            # Stesso broker + wildcard + topic matching
            if b_ip == will_broker and count_wildcards(filt) >= 1 \
               and mqtt_topic_matches(filt, will_topic):
                cq5_subscribers.add(sub_key)
                print(f"    Subscriber {sub_key[0]}:{sub_key[1]}  filter='{filt}'  MATCH")

if not cq5_subscribers:
    print("  (nessun subscriber con wildcard corrisponde al will topic)")

print(f"\n>>> CQ5 RISPOSTA: {len(cq5_subscribers)}\n")

# ─── Riepilogo finale ──────────────────────────────────────────────────────────
print("=" * 60)
print("RIEPILOGO")
print("=" * 60)
print(f"CQ5  : {len(cq5_subscribers)}")
print(f"CQ6a : {len(retain_clear_clients)}")
print(f"CQ6b : {cq6b_count}")
print(f"CQ7  : {cq7_count}")
