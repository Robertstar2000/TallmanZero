import socket
import threading
import sys

# CONFIGURATION
LISTEN_PORT = 11435
REMOTE_HOST = "10.10.20.60"
REMOTE_PORT = 11434

def bridge(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except Exception:
        pass
    finally:
        source.close()
        destination.close()

def handle_client(client_socket):
    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.settimeout(10) # 10s timeout for initial connection
        remote_socket.connect((REMOTE_HOST, REMOTE_PORT))
        
        print(f"[*] Relaying: {client_socket.getpeername()} <-> {REMOTE_HOST}:{REMOTE_PORT}")
        
        t1 = threading.Thread(target=bridge, args=(client_socket, remote_socket))
        t2 = threading.Thread(target=bridge, args=(remote_socket, client_socket))
        
        t1.daemon = True
        t2.daemon = True
        
        t1.start()
        t2.start()
    except Exception as e:
        print(f"[!] Error connecting to remote {REMOTE_HOST}:{REMOTE_PORT}: {e}")
        client_socket.close()

def start_proxy():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", LISTEN_PORT))
        server.listen(10)
        print(f"[*] Proxy listening on 0.0.0.0:{LISTEN_PORT} -> {REMOTE_HOST}:{REMOTE_PORT}")
        print(f"[*] Connect your Agent Zero to http://host.docker.internal:{LISTEN_PORT}")
        print("[*] Press Ctrl+C to stop.")
        
        while True:
            client, addr = server.accept()
            handle_client(client)
    except KeyboardInterrupt:
        print("\n[*] Stopping proxy...")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_proxy()
