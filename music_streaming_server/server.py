import socket
import ssl
import threading
import os
import time

HOST = '0.0.0.0'   # Accept connections from other devices
PORT = 5001
SONG_FOLDER = 'songs'
CHUNK_SIZE = 4096

active_clients = 0
lock = threading.Lock()

def handle_client(connstream, addr):
    global active_clients
    start_time = time.time()

    with lock:
        active_clients += 1
        print(f"[+] Client connected: {addr} | Active clients: {active_clients}")

    try:
        request = connstream.recv(1024).decode().strip()
        print(f"[{addr}] Request received: {request}")

        if not request.startswith("REQUEST:"):
            connstream.sendall(b"ERROR:Invalid request format")
            return

        filename = request.split(":", 1)[1]
        filepath = os.path.join(SONG_FOLDER, filename)

        if not os.path.exists(filepath):
            connstream.sendall(b"ERROR:File not found")
            return

        filesize = os.path.getsize(filepath)
        connstream.sendall(f"OK:{filesize}".encode())

        total_sent = 0
        with open(filepath, "rb") as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                connstream.sendall(data)
                total_sent += len(data)

        elapsed = time.time() - start_time
        print(f"[{addr}] Finished streaming '{filename}' | {total_sent} bytes sent in {elapsed:.2f} sec")

    except Exception as e:
        print(f"[!] Error with client {addr}: {e}")

    finally:
        try:
            connstream.shutdown(socket.SHUT_RDWR)
        except:
            pass
        connstream.close()

        with lock:
            active_clients -= 1
            print(f"[-] Client disconnected: {addr} | Active clients: {active_clients}")

def start_server():
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        print("[ERROR] SSL certificate files not found!")
        print("Generate them using:")
        print("openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem")
        return

    if not os.path.exists(SONG_FOLDER):
        os.makedirs(SONG_FOLDER)
        print(f"[INFO] Created '{SONG_FOLDER}' folder. Add songs inside it and restart.")
        return

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    bindsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bindsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bindsocket.bind((HOST, PORT))
    bindsocket.listen(5)

    print(f"[SERVER] Secure Music Streaming Server running on {HOST}:{PORT}")
    print(f"[SERVER] Waiting for clients...\n")

    while True:
        newsocket, fromaddr = bindsocket.accept()
        try:
            connstream = context.wrap_socket(newsocket, server_side=True)
            threading.Thread(target=handle_client, args=(connstream, fromaddr), daemon=True).start()
        except ssl.SSLError as e:
            print(f"[SSL ERROR] {fromaddr}: {e}")
            newsocket.close()

if __name__ == "__main__":
    start_server()