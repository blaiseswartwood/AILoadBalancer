import socket
import threading
import subprocess
import sys
import time
from algorithm_type import AlgorithmType

LB_PORT = 1234
SERVER_PORTS = [1235, 1236]  
CONNECTION_COUNTS = [0, 0]
SERVER_HOST = 'localhost' 
server_processes = []   

next_server = 0
active_connections = 0
lock = threading.Lock()

def start_servers():
    global server_processes
    
    for port in SERVER_PORTS:
        proc = subprocess.Popen([sys.executable, './server.py', str(port)])
        server_processes.append(proc)
        time.sleep(1)  # Give the servers time to start

def stop_servers():
    global server_processes
    
    for proc in server_processes:
        proc.terminate()
        proc.wait()  # Wait for the process to terminate
        
def forward(source, destination):
    """Forwards data from the source to the destination.

    Keyword arguments:
    source -- where data comes from 
    destination -- where to send the data
    """
    try:
        while True:
            data = source.recv(1024)
            if not data:
                break
            destination.sendall(data)
    finally:
        source.close()
        destination.close()

def handle_client(client_socket, algorithm_type):
    global next_server, active_connections

    if algorithm_type == AlgorithmType.ROUND_ROBIN:
        # Round robin server selection
        with lock:
            backend_port = SERVER_PORTS[next_server]
            next_server = (next_server + 1) % len(SERVER_PORTS) 
    elif algorithm_type == AlgorithmType.LEAST_CONNECTIONS:
        with lock:
            index = CONNECTION_COUNTS.index(min(CONNECTION_COUNTS))
            backend_port = SERVER_PORTS[index]
            CONNECTION_COUNTS[index] += 1

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.connect((SERVER_HOST, backend_port))
        print(f"Connected client to backend server on port {backend_port}")

        with lock:
            active_connections += 1
            print(f"Active connections: {active_connections}")
            
        # Start threads to forward data between client and server
        t1 = threading.Thread(target=forward, args=(client_socket, server_socket))
        t2 = threading.Thread(target=forward, args=(server_socket, client_socket))
        t1.start()
        t2.start()

        t1.join()
        t2.join()
    except Exception as e:
        print("Error connecting to backend server:", e)
        client_socket.close()
    finally:
        with lock:
            CONNECTION_COUNTS[index] -= 1
            active_connections -= 1
            print(f"Active connections: {active_connections}")

def load_balancer():
    if len(sys.argv) < 1 or len(sys.argv) > 2:
        print("Usage: python load_balancer.py <algorithm_type>")
        sys.exit()
    
    if len(sys.argv) == 1 or sys.argv[1] == "r":
        algorithm_type = AlgorithmType.ROUND_ROBIN
    elif sys.argv[1] == "c":
        algorithm_type = AlgorithmType.LEAST_CONNECTIONS
    else:
        print("unknown algorithm type")
        sys.exit()

    load_balancer_host = '0.0.0.0'
    start_servers()

    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lb_socket.bind((load_balancer_host, LB_PORT))
    lb_socket.listen(5)
    lb_socket.settimeout(1)

    print(f"Load Balancer running on port {LB_PORT}")

    try:
        while True:
            try:
                client_socket, addr = lb_socket.accept()
                print("Accepted connection from", addr)
                threading.Thread(target=handle_client, args=(client_socket, algorithm_type)).start()
            except socket.timeout:  
                continue
    except KeyboardInterrupt:
        print("\nLoad balancer shutting down.")
    finally:
        stop_servers()
        lb_socket.close()

if __name__ == '__main__':
    load_balancer()
