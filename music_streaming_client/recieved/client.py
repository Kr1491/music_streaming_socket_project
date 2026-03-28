import socket
import ssl
import os
import time
import hashlib
import queue
import threading

SERVER_HOST = '10.216.229.99'   # CHANGE to your server IP
SERVER_PORT = 5001
SAVE_FOLDER = 'received'
INITIAL_CHUNK_SIZE = 4096
MAX_CHUNK_SIZE = 65536
MIN_CHUNK_SIZE = 1024
BUFFER_SIZE = 20        # max chunks held in memory buffer
MAX_RETRIES = 3         # retry attempts on checksum failure

os.makedirs(SAVE_FOLDER, exist_ok=True)


def compute_md5(filepath):
    """Verify file integrity by computing its MD5 checksum."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def request_song(song_name):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE   # OK for local/dev; use CERT_REQUIRED in prod

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n[INFO] Attempt {attempt}/{MAX_RETRIES} for '{song_name}'")
        success = _attempt_download(song_name, context)
        if success:
            break
        if attempt < MAX_RETRIES:
            print(f"[RETRY] Checksum failed. Retrying...")
    else:
        print("[FAIL] All retry attempts exhausted. File may be corrupt.")


def _attempt_download(song_name, context):
    """
    Single download attempt.
    Returns True if file received and MD5 verified, False otherwise.
    """
    chunk_size = INITIAL_CHUNK_SIZE
    output_path = os.path.join(SAVE_FOLDER, song_name)

    # QoS metrics
    qos = {
        'chunk_times': [],
        'bytes_recv': 0,
        'buffer_full_events': 0,
    }

    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT)) as sock:
            with context.wrap_socket(sock, server_hostname=SERVER_HOST) as ssock:

                # 1. Send request
                ssock.sendall(f"REQUEST:{song_name}".encode())

                # 2. Receive file metadata
                response = ssock.recv(1024).decode()
                if response.startswith("ERROR"):
                    print("[SERVER]", response)
                    return False

                if not response.startswith("OK:"):
                    print("[ERROR] Unexpected server response:", response)
                    return False

                parts = response.split(":")
                filesize = int(parts[1])
                expected_md5 = parts[2]
                print(f"[INFO] File size: {filesize} bytes | Expected MD5: {expected_md5}")

                # 3. Adaptive streaming: negotiate chunk size
                # Start with INITIAL_CHUNK_SIZE; will adapt after first measurement
                ssock.sendall(f"CHUNK:{chunk_size}".encode())
                ack = ssock.recv(64).decode().strip()
                if ack.startswith("CHUNK_ACK:"):
                    chunk_size = int(ack.split(":")[1])
                print(f"[INFO] Negotiated chunk size: {chunk_size} bytes")

                # 4. Buffer management: producer/consumer with a queue
                buf = queue.Queue(maxsize=BUFFER_SIZE)
                write_done = threading.Event()
                write_error = [None]

                def writer():
                    """Consumer thread: drains buffer queue to disk."""
                    try:
                        with open(output_path, "wb") as f:
                            while True:
                                chunk = buf.get()
                                if chunk is None:   # sentinel: stream finished
                                    break
                                f.write(chunk)
                                buf.task_done()
                    except Exception as e:
                        write_error[0] = e
                    finally:
                        write_done.set()

                writer_thread = threading.Thread(target=writer, daemon=True)
                writer_thread.start()

                start_time = time.time()
                received = 0

                # Producer: receive chunks and put them into the buffer
                while received < filesize:
                    t0 = time.time()
                    to_read = min(chunk_size, filesize - received)
                    data = ssock.recv(to_read)
                    if not data:
                        break
                    elapsed_chunk = time.time() - t0
                    qos['chunk_times'].append(elapsed_chunk)

                    # Buffer management: track full-buffer stalls
                    if buf.full():
                        qos['buffer_full_events'] += 1
                    buf.put(data)   # blocks if buffer is full (backpressure)

                    received += len(data)
                    qos['bytes_recv'] = received

                    # --- Adaptive streaming: adjust chunk size based on throughput ---
                    if len(qos['chunk_times']) % 10 == 0 and elapsed_chunk > 0:
                        instant_throughput = len(data) / elapsed_chunk  # bytes/sec
                        if instant_throughput > 500_000 and chunk_size < MAX_CHUNK_SIZE:
                            chunk_size = min(chunk_size * 2, MAX_CHUNK_SIZE)
                        elif instant_throughput < 100_000 and chunk_size > MIN_CHUNK_SIZE:
                            chunk_size = max(chunk_size // 2, MIN_CHUNK_SIZE)

                buf.put(None)       # signal writer to stop
                write_done.wait()   # wait for all data to be flushed to disk

                if write_error[0]:
                    print(f"[ERROR] Write failed: {write_error[0]}")
                    return False

                elapsed = time.time() - start_time

                # 5. Packet loss handling: verify MD5 checksum
                actual_md5 = compute_md5(output_path)
                if actual_md5 != expected_md5:
                    print(f"[CHECKSUM FAIL] Expected: {expected_md5} | Got: {actual_md5}")
                    os.remove(output_path)
                    return False
                print(f"[CHECKSUM OK] MD5 verified.")

                # 6. QoS Evaluation report
                throughput = received / elapsed / 1024 / 1024 if elapsed > 0 else 0
                if len(qos['chunk_times']) > 1:
                    avg_t = sum(qos['chunk_times']) / len(qos['chunk_times'])
                    jitter = sum(abs(t - avg_t) for t in qos['chunk_times']) / len(qos['chunk_times'])
                else:
                    jitter = 0

                print(f"\n[QoS REPORT] ---- {song_name} ----")
                print(f"  Total bytes received : {received} / {filesize}")
                print(f"  Time taken           : {elapsed:.2f} sec")
                print(f"  Avg throughput       : {throughput:.2f} MB/s")
                print(f"  Jitter               : {jitter*1000:.2f} ms")
                print(f"  Final chunk size     : {chunk_size} bytes (adaptive)")
                print(f"  Buffer stall events  : {qos['buffer_full_events']}")
                print(f"  Transfer complete    : {'YES' if received == filesize else 'NO (incomplete)'}")
                print(f"  File saved to        : {output_path}")

                return True

    except Exception as e:
        print(f"[ERROR] Connection/receive error: {e}")
        return False


if __name__ == "__main__":
    song = input("Enter song filename (e.g., song1.mp3): ").strip()
    request_song(song)
