# 🎵 Secure Multi-Client Music Streaming Server (Socket Programming)

## 📌 Overview

This project implements a **secure multi-client music streaming system** using **low-level TCP socket programming**. A central server streams audio files to multiple clients concurrently over a network, with communication secured using **SSL/TLS**.

The system demonstrates key networking concepts such as client-server architecture, concurrency, protocol design, secure communication, buffer management, adaptive streaming, packet integrity verification, and Quality of Service (QoS) evaluation.

---

## 🚀 Features

- 📡 TCP socket-based communication
- 🔐 SSL/TLS secure data transfer
- 👥 Supports multiple concurrent clients (multithreading)
- 🎧 Chunk-based audio streaming
- 🗄️ **Buffer management** — producer/consumer queue decouples receiving from disk writes
- 📦 **Packet loss handling** — MD5 checksum verification with automatic retry (up to 3 attempts)
- 📶 **Adaptive streaming** — chunk size adjusts dynamically based on measured throughput
- 📊 **QoS evaluation** — per-transfer report: throughput, jitter, buffer stalls, and transfer completeness
- ⚠️ Handles failure scenarios (invalid request, disconnects, corrupt transfers)

---

## 🏗️ Architecture

```
Client 1 ----\
Client 2 ----- > Secure TCP/SSL Server ----> songs/
Client 3 ----/
```

Each client connection is handled in its own thread. The client uses a two-thread pipeline (receiver + writer) with a bounded in-memory queue as the buffer.

---

## 🔄 Workflow

1. Client connects to server using TCP + SSL
2. Client sends request:
   ```
   REQUEST:song1.mp3
   ```
3. Server responds with file metadata:
   - `OK:<filesize>:<md5checksum>` → if file exists
   - `ERROR:File not found` → if invalid
4. Client negotiates chunk size:
   ```
   CHUNK:8192
   ```
5. Server acknowledges:
   ```
   CHUNK_ACK:8192
   ```
6. Server streams file in negotiated chunk sizes
7. Client buffers chunks in a queue and writes them to disk concurrently
8. Client verifies MD5 checksum; retries on mismatch
9. Client prints a full QoS report

---

## 🧠 Technologies Used

- Python
- `socket`
- `ssl`
- `threading`
- `queue`
- `hashlib` (MD5)
- OS/networking concepts

---

## 📁 Project Structure

### Server

```
music_streaming_server/
│
├── server.py
├── cert.pem          # (Generated locally, not uploaded)
├── key.pem           # (Generated locally, not uploaded)
└── songs/
    ├── song1.mp3
    ├── song2.mp3
```

### Client

```
music_streaming_client/
│
├── client.py
└── received/
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-link>
cd <repo-name>
```

### 2. Generate SSL Certificates (server only)

Run inside the server folder:

```bash
openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem
```

### 3. Start the server

```bash
python3 server.py
```

### 4. Find server IP

```bash
ifconfig        # Mac/Linux
ipconfig        # Windows
```

Example: `192.168.1.7`

### 5. Configure the client

Update in `client.py`:

```python
SERVER_HOST = '192.168.1.7'
```

### 6. Run the client

```bash
python3 client.py
```

Enter the song filename when prompted:

```
Enter song filename (e.g., song1.mp3): song1.mp3
```

---

## 🗄️ Buffer Management

The client uses a **producer/consumer** model with a bounded `queue.Queue` (capacity: 20 chunks):

- **Producer thread** — receives data over SSL and puts chunks into the queue
- **Consumer thread** — drains the queue and writes chunks to disk

This decouples network I/O from disk I/O. If the disk is slow, the buffer absorbs the difference. If the buffer fills up, the receiver pauses automatically (**backpressure**), preventing memory overflow.

The number of buffer stall events (times the buffer was full) is reported in the QoS summary.

---

## 📦 Packet Loss Handling

After a complete file transfer, the client computes the **MD5 checksum** of the received file and compares it with the checksum sent by the server.

- ✅ Match → transfer accepted, file saved
- ❌ Mismatch → corrupted file deleted, transfer retried (up to **3 attempts**)

This detects corruption caused by network errors, partial disconnects, or dropped data.

---

## 📶 Adaptive Streaming Logic

The client starts with a default chunk size of **4096 bytes**. Every 10 chunks, it measures the instantaneous throughput and adjusts:

| Condition | Action |
|---|---|
| Throughput > 500 KB/s | Double chunk size (up to 65536 bytes) |
| Throughput < 100 KB/s | Halve chunk size (down to 1024 bytes) |

Before streaming begins, the client sends its preferred chunk size to the server, which clamps it within safe limits and confirms the agreed size. This reduces protocol overhead on fast networks and keeps memory usage low on slow ones.

---

## 📊 QoS Evaluation

Both server and client log quality metrics after each transfer.

### Client QoS report (example output)

```
[QoS REPORT] ---- song1.mp3 ----
  Total bytes received : 5242880 / 5242880
  Time taken           : 1.43 sec
  Avg throughput       : 3.49 MB/s
  Jitter               : 0.82 ms
  Final chunk size     : 32768 bytes (adaptive)
  Buffer stall events  : 0
  Transfer complete    : YES
  File saved to        : received/song1.mp3
```

### Server QoS log (example output)

```
[QoS][('192.168.1.5', 51234)] File: song1.mp3
[QoS][('192.168.1.5', 51234)] Bytes sent: 5242880 | Time: 1.41s
[QoS][('192.168.1.5', 51234)] Throughput: 3.54 MB/s
[QoS][('192.168.1.5', 51234)] Chunk size used: 32768 | Jitter: 0.74 ms
```

**Metrics explained:**

- **Throughput** — average MB/s for the complete transfer
- **Jitter** — mean absolute deviation of per-chunk delivery times; higher jitter = less consistent network
- **Buffer stall events** — how often the receive buffer was full, indicating the disk write was slower than the network receive
- **Final chunk size** — the chunk size the adaptive algorithm settled on

---

## 📈 Performance Evaluation

| Clients | File Size | Avg Time | Throughput |
|---|---|---|---|
| 1 | 5 MB | ~1.2 s | ~4 MB/s |
| 3 | 5 MB | ~2.4 s | ~2 MB/s |
| 5 | 5 MB | ~4 s | ~1 MB/s |

### Observations

- Increasing clients increases latency and reduces per-client throughput
- Adaptive chunk sizing improves throughput on stable connections
- Buffer management prevents disk I/O from becoming a bottleneck
- Server remains stable under load; MD5 verification ensures data integrity

---

## ⚠️ Failure Scenarios Handled

- ❌ Invalid file request → error response
- 🔌 Client disconnect → handled gracefully
- 🔐 SSL errors → caught and handled
- 📉 High load → increased latency but stable
- 💾 Corrupt/incomplete transfer → MD5 mismatch triggers retry

---

## ⚡ Optimizations

- Chunk-based file transfer (adaptive: 1024–65536 bytes)
- Multithreading for concurrency
- Socket reuse (`SO_REUSEADDR`)
- Producer/consumer buffer (bounded queue)
- MD5 integrity check with retry
- Adaptive chunk sizing based on live throughput measurement

---

## 📚 Key Concepts Demonstrated

- TCP Socket Programming
- Client-Server Architecture
- SSL/TLS Secure Communication
- Concurrency using Threads
- Buffer Management (producer/consumer)
- Packet Integrity Verification (MD5)
- Adaptive Bitrate / Chunk-Size Streaming
- QoS Measurement (throughput, jitter, stall events)
- Performance & Scalability Analysis

---

## 🔮 Future Improvements

- Real-time audio playback (pipe received data to an audio player)
- GUI-based client
- Song search & playlists
- Authentication system
- True adaptive bitrate streaming (multiple quality tiers)
- QUIC/UDP transport for lower latency

---

## 👨‍💻 Contributors

- Krrish Aryan
- Kaushik Biradar
- Krishna Jha

---

## 📌 Note

SSL certificates (`cert.pem`, `key.pem`) are **not included** in the repository for security reasons. Generate them locally before running the server (see Setup Instructions above).
