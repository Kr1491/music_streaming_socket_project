import socket
import ssl
import os
import time

SERVER_HOST = '192.168.1.7'   # CHANGE THIS to your Mac server IP
SERVER_PORT = 5001
SAVE_FOLDER = 'received'
CHUNK_SIZE = 4096

os.makedirs(SAVE_FOLDER, exist_ok=True)

def request_song(song_name):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    start_time = time.time()

    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT)) as sock:
            with context.wrap_socket(sock, server_hostname=SERVER_HOST) as ssock:
                ssock.sendall(f"REQUEST:{song_name}".encode())

                response = ssock.recv(1024).decode()

                if response.startswith("ERROR"):
                    print("[SERVER]", response)
                    return

                if response.startswith("OK:"):
                    filesize = int(response.split(":")[1])
                    print(f"[INFO] Receiving '{song_name}' ({filesize} bytes)...")

                    output_path = os.path.join(SAVE_FOLDER, song_name)
                    received = 0

                    with open(output_path, "wb") as f:
                        while received < filesize:
                            data = ssock.recv(CHUNK_SIZE)
                            if not data:
                                break
                            f.write(data)
                            received += len(data)

                    elapsed = time.time() - start_time
                    throughput = filesize / elapsed / 1024 / 1024

                    print(f"[SUCCESS] Song saved to: {output_path}")
                    print(f"[STATS] Time taken: {elapsed:.2f} sec")
                    print(f"[STATS] Throughput: {throughput:.2f} MB/s")
                    print(f"[STATS] Bytes received: {received}")

                    if received < filesize:
                        print("[WARNING] File transfer incomplete!")
                    else:
                        print("[INFO] File transfer complete.")

    except Exception as e:
        print(f"[ERROR] Could not connect or receive file: {e}")

if __name__ == "__main__":
    song = input("Enter song filename (e.g., song1.mp3): ").strip()
    request_song(song)