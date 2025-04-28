import subprocess
import sys
import time
import asyncio
from algorithm_type import AlgorithmType
from semantic_cache import SemanticCache

LOAD_BALANCER_HOST = 'localhost' 
LB_PORT = 1234

SERVER_HOST = 'localhost'
SERVER_PORTS = [1235, 1236]  
server_processes = []   

# managing servers
next_server = 0
active_connections = 0
CONNECTION_COUNTS = [0, 0]
lock = asyncio.Lock()

# caching
semantic_cache = SemanticCache()

def start_servers():
    global server_processes
    
    for port in SERVER_PORTS:
        print("Starting server on port:", port)
        proc = subprocess.Popen([sys.executable, './server.py', str(port)])
        server_processes.append(proc)
        time.sleep(5)  # Give the servers time to start

def stop_servers():
    global server_processes
    
    for proc in server_processes:
        proc.terminate()
        proc.wait()  # Wait for the process to terminate
        
async def forward(reader, writer):
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            data = data.decode()
            
            # caching - need to ensure its only one way caching
            cache_key = semantic_cache.semantic_key(str(data))
            cache_response = semantic_cache.get(cache_key)
            
            if cache_response is not None:
                print("Cache hit!")
                cache_response = cache_response.encode()
                reader.write(cache_response)
                await reader.drain()
            else:
                print("Cache miss!")
                semantic_cache.add(cache_key, data)
                writer.write(data.encode())
                await writer.drain()
                
    except Exception as e:
        pass
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_client(client_reader, client_writer, algorithm_type):
    addr = client_writer.get_extra_info('peername')
    print(f"Load balancer received connection on port {addr[1]}")
    global next_server, active_connections
            
    server_writer = None
    server_reader = None
    index = None
    
    try:
        async with lock:
            if algorithm_type == AlgorithmType.ROUND_ROBIN:
                backend_port = SERVER_PORTS[next_server]
                index = next_server
                next_server = (next_server + 1) % len(SERVER_PORTS) 
            elif algorithm_type == AlgorithmType.LEAST_CONNECTIONS: 
                index = CONNECTION_COUNTS.index(min(CONNECTION_COUNTS))
                backend_port = SERVER_PORTS[index]
            CONNECTION_COUNTS[index] += 1
            
        server_reader, server_writer = await asyncio.open_connection(SERVER_HOST, backend_port)
        print(f"Load balancer connected to backend server on port {backend_port}")

        async with lock:
            active_connections += 1
            print(f"Total active connections: {active_connections}")
            
        # Forward data in both directions
        await asyncio.gather(
            forward(client_reader, server_writer),
            forward(server_reader, client_writer)
        )
    except Exception as e:
        print("Error connecting to backend server:", e)
    finally:
        async with lock:
            if index is not None:
                CONNECTION_COUNTS[index] -= 1
            active_connections -= 1
            print(f"Load balancer closed connection with client on port {addr[1]}")
            print(f"Server on port {backend_port} has {CONNECTION_COUNTS[index]} connections")
            print(f"Total active connections: {active_connections}")
        client_writer.close()
        if server_writer:
            server_writer.close()
            await server_writer.wait_closed()

async def load_balancer():
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

    start_servers()

    load_balancer = await asyncio.start_server(
        lambda r, w: handle_client(r, w, algorithm_type),
        LOAD_BALANCER_HOST,
        LB_PORT
    )

    print(f"Load Balancer on port {LB_PORT} running on {LOAD_BALANCER_HOST}")

    try:
        async with load_balancer:
            await load_balancer.serve_forever()
    except asyncio.CancelledError:
        print("\nLoad balancer shutting down.")

if __name__ == '__main__':
    try:
        asyncio.run(load_balancer())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
