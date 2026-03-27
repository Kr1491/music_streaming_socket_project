# 🎵 Secure Multi-Client Music Streaming Server (Socket Programming)

## 📌 Overview

This project implements a **secure multi-client music streaming system** using **low-level TCP socket programming**. A central server streams audio files to multiple clients concurrently over a network, with communication secured using **SSL/TLS**.

The system demonstrates key networking concepts such as client-server architecture, concurrency, protocol design, secure communication, and performance evaluation.

---

## 🚀 Features

* 📡 TCP socket-based communication
* 🔐 SSL/TLS secure data transfer
* 👥 Supports multiple concurrent clients (multithreading)
* 🎧 Chunk-based audio streaming
* ⚡ Performance measurement (response time & throughput)
* ⚠️ Handles failure scenarios (invalid request, disconnects)

---

## 🏗️ Architecture

Client devices connect to a central server over a network.

```
Client 1 ----\
Client 2 ----- > Secure TCP/SSL Server ----> songs/
Client 3 ----/
```

---

## 🔄 Workflow

1. Client connects to server using TCP + SSL
2. Client sends request:

   ```
   REQUEST:song1.mp3
   ```
3. Server responds:

   * `OK:<filesize>` → if file exists
   * `ERROR:File not found` → if invalid
4. Server streams file in chunks
5. Client receives and stores the file

---

## 🧠 Technologies Used

* Python
* socket
* ssl
* threading
* OS/networking concepts

---

## 📁 Project Structure

### Server (Laptop A)

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

### Client (Laptop B)

```
music_streaming_client/
│
├── client.py
└── received/
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```
git clone <your-repo-link>
cd <repo-name>
```

---

### 2. Generate SSL Certificates (Server only)

Run inside server folder:

```
openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem
```

---

### 3. Start Server (Mac/Linux)

```
python3 server.py
```

---

### 4. Find Server IP

```
ifconfig
```

Example:

```
192.168.1.7
```

---

### 5. Configure Client

Update in `client.py`:

```python
SERVER_HOST = '192.168.1.7'
```

---

### 6. Run Client (Windows/Mac/Linux)

```
python client.py
```

Enter:

```
song1.mp3
```

---

## 📊 Performance Evaluation

| Clients | File Size | Avg Time | Throughput |
| ------- | --------- | -------- | ---------- |
| 1       | 5 MB      | ~1.2 s   | ~4 MB/s    |
| 3       | 5 MB      | ~2.4 s   | ~2 MB/s    |
| 5       | 5 MB      | ~4 s     | ~1 MB/s    |

### Observations

* Increasing clients increases latency
* Throughput per client decreases
* Server remains stable under load

---

## ⚠️ Failure Scenarios Handled

* ❌ Invalid file request → error response
* 🔌 Client disconnect → handled gracefully
* 🔐 SSL errors → caught and handled
* 📉 High load → increased latency but stable

---

## ⚡ Optimizations

* Chunk-based file transfer (4096 bytes)
* Multithreading for concurrency
* Socket reuse (`SO_REUSEADDR`)
* Efficient memory usage

---

## 📚 Key Concepts Demonstrated

* TCP Socket Programming
* Client-Server Architecture
* SSL/TLS Secure Communication
* Concurrency using Threads
* Performance & Scalability Analysis

---

## 🔮 Future Improvements

* Real-time audio playback
* GUI-based client
* Song search & playlists
* Authentication system
* Adaptive bitrate streaming

---

## 👨‍💻 Contributors

* Team Member 1
* Team Member 2
* Team Member 3

---

## 📌 Note

SSL certificates (`cert.pem`, `key.pem`) are **not included in the repository** for security reasons. Generate them locally before running the server.

---
