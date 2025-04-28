import subprocess
import sys
import time
import asyncio
from algorithm_type import AlgorithmType
from semantic_cache import SemanticCache
import uuid

CACHING_LOGS = True
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
pending_requests = {}

def start_servers():
    """
    Starts the servers on the specified ports
    """
    global server_processes
    for port in SERVER_PORTS:
        print("Starting server on port:", port)
        proc = subprocess.Popen([sys.executable, './server.py', str(port)])
        server_processes.append(proc)
        time.sleep(5)  # Give the servers time to start

def stop_servers():
    """
    Stops the servers on the specified ports
    """
    global server_processes
    for proc in server_processes:
        proc.terminate()
        proc.wait()  # Wait for the process to terminate
        
async def cli_to_srv_forward(client_reader, server_writer, client_writer):
    """
    Forwards data from the client to the server.

    Args:
        client_reader: StreamReader object that reads data from the client.
        server_writer: StreamWriter object that writes data to the server
        client_writer: StreamWriter object that writes data to the client.
    """
    try:
        while True:
            data = await client_reader.read(1024)
            if not data:
                break
            data = data.decode()
            
            # caching - need to ensure its only one way caching
            cache_response = semantic_cache.get(str(data))
            
            if cache_response is not None:
                cache_response = cache_response.encode()
                
                if CACHING_LOGS:
                    print("Cache hit!")
                    print("Got cache_response of: ", cache_response)
                    
                client_writer.write(cache_response)
                await client_writer.drain()
            else:
                # adding id to pending requests to ensure we will cache the response when it comes
                request_id = str(uuid.uuid4())
                pending_requests[request_id] = str(data)
                
                # appending unique ID to the data sent.
                payload = f"{request_id}|{data}"
                
                if CACHING_LOGS:
                    print("Cache miss!")
                    print("Sending off payload: ", payload)
                    
                server_writer.write(payload.encode())
                await server_writer.drain()
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        server_writer.close()
        await server_writer.wait_closed()
        
async def srv_to_cli_forward(server_reader, client_writer):
    """
    Forwards data from the server back to the client.

    Args:
        server_reader: StreamReader object that reads data from the server.
        client_writer: StreamWriter object that writes data to the client.
    """
    try:
        while True:
            # Read data from the server
            data = await server_reader.read(1024)
            if not data:
                break
            data = data.decode()
            
            request_id, response_payload = data.split('|', 1)
            request_msg = pending_requests.pop(request_id, None)
            
            # Cache the response
            if request_msg:
                if CACHING_LOGS:
                    print("Adding to cache: ", response_payload)
                semantic_cache.add(request_msg, response_payload)
                
            # Write the response back to the client
            client_writer.write(response_payload.encode())
            await client_writer.drain()
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        client_writer.close()
        await client_writer.wait_closed()


async def handle_client(client_reader, client_writer, algorithm_type):
    """
    Handles a client connection by forwarding data to the appropriate backend server.

    Args:
        client_reader: StreamReader object that reads data from the client.
        client_writer: StreamWriter object that writes data to the client.
        algorithm_type: The load balancing algorithm to use.
    """
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
            cli_to_srv_forward(client_reader, server_writer, client_writer),
            srv_to_cli_forward(server_reader, client_writer)
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
    """
    Creates the load balancer server and starts listening for client connections.
    
    Args:
        From command line: algorithm_type (r for round robin, c for least connections).
    """
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

    # start server processes
    start_servers()

    # start the load balancer
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
