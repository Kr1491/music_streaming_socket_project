import socket
import ssl
import threading
import os
import time
import hashlib

HOST = '0.0.0.0'
PORT = 5001
SONG_FOLDER = 'songs'
DEFAULT_CHUNK_SIZE = 4096
MAX_CHUNK_SIZE = 65536
MIN_CHUNK_SIZE = 1024

active_clients = 0
lock = threading.Lock()


def compute_md5(filepath):
    """Compute MD5 checksum of a file for integrity verification."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def handle_client(connstream, addr):
    global active_clients
    start_time = time.time()

    with lock:
        active_clients += 1
    print(f"[+] Client connected: {addr} | Active clients: {active_clients}")

    # QoS tracking
    qos = {
        'chunk_sizes': [],
        'chunk_times': [],
        'bytes_sent': 0,
    }

    try:
        request = connstream.recv(1024).decode().strip()
        print(f"[{addr}] Request: {request}")

        if not request.startswith("REQUEST:"):
            connstream.sendall(b"ERROR:Invalid request format")
            return

        filename = os.path.basename(request.split(":", 1)[1])  # prevent path traversal
        filepath = os.path.join(SONG_FOLDER, filename)

        if not os.path.exists(filepath):
            connstream.sendall(b"ERROR:File not found")
            return

        filesize = os.path.getsize(filepath)
        checksum = compute_md5(filepath)

        # --- Adaptive Streaming: negotiate chunk size with client ---
        # Send file metadata; client replies with its preferred chunk size
        connstream.sendall(f"OK:{filesize}:{checksum}".encode())
        chunk_resp = connstream.recv(64).decode().strip()
        if chunk_resp.startswith("CHUNK:"):
            try:
                requested = int(chunk_resp.split(":")[1])
                chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, requested))
            except ValueError:
                chunk_size = DEFAULT_CHUNK_SIZE
        else:
            chunk_size = DEFAULT_CHUNK_SIZE
        print(f"[{addr}] Using chunk size: {chunk_size} bytes")
        connstream.sendall(f"CHUNK_ACK:{chunk_size}".encode())

        # --- Stream file in chunks ---
        total_sent = 0
        with open(filepath, "rb") as f:
            while True:
                t0 = time.time()
                data = f.read(chunk_size)
                if not data:
                    break
                connstream.sendall(data)
                total_sent += len(data)
                elapsed_chunk = time.time() - t0

                # QoS: record per-chunk stats
                qos['chunk_sizes'].append(len(data))
                qos['chunk_times'].append(elapsed_chunk)
        qos['bytes_sent'] = total_sent

        # --- QoS Report ---
        elapsed = time.time() - start_time
        throughput = total_sent / elapsed / 1024 / 1024 if elapsed > 0 else 0
        if len(qos['chunk_times']) > 1:
            avg_t = sum(qos['chunk_times']) / len(qos['chunk_times'])
            jitter = sum(abs(t - avg_t) for t in qos['chunk_times']) / len(qos['chunk_times'])
        else:
            jitter = 0

        print(f"[QoS][{addr}] File: {filename}")
        print(f"[QoS][{addr}] Bytes sent: {total_sent} | Time: {elapsed:.2f}s")
        print(f"[QoS][{addr}] Throughput: {throughput:.2f} MB/s")
        print(f"[QoS][{addr}] Chunk size used: {chunk_size} | Jitter: {jitter*1000:.2f} ms")

    except Exception as e:
        print(f"[!] Error with client {addr}: {e}")
    finally:
        try:
            connstream.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        connstream.close()
        with lock:
            active_clients -= 1
        print(f"[-] Client disconnected: {addr} | Active clients: {active_clients}")


def start_server():
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        print("[ERROR] SSL certificate files not found!")
        print("Generate them with:")
        print("  openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem")
        return

    if not os.path.exists(SONG_FOLDER):
        os.makedirs(SONG_FOLDER)
        print(f"[INFO] Created '{SONG_FOLDER}' folder. Add songs and restart.")
        return

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    bindsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bindsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bindsocket.bind((HOST, PORT))
    bindsocket.listen(10)
    print(f"[SERVER] Secure Music Streaming Server on {HOST}:{PORT}")
    print(f"[SERVER] Features: buffer management, MD5 integrity, adaptive chunks, QoS logging")
    print(f"[SERVER] Waiting for clients...\n")

    while True:
        newsocket, fromaddr = bindsocket.accept()
        try:
            connstream = context.wrap_socket(newsocket, server_side=True)
            threading.Thread(
                target=handle_client,
                args=(connstream, fromaddr),
                daemon=True
            ).start()
        except ssl.SSLError as e:
            print(f"[SSL ERROR] {fromaddr}: {e}")
            newsocket.close()


if __name__ == "__main__":
    start_server()
