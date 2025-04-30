import subprocess
import sys
import time
import asyncio
import uuid
import heapq

from collections import deque

from algorithm_type import RoundRobin, LeastConnections, AlgorithmType
from semantic_cache import SemanticCache

        
class LoadBalancer:
    """
    LoadBalancer class that manages the backend servers and distributes requests to them.
    """
    def __init__(self):
        self.LB_HOST = 'localhost' 
        self.LB_PORT = 1234

        # Load balancing algorithm
        self.algorithm_type = None
        self.LB_algorithm = self.load_lb_algorithm()
        self.lock = asyncio.Lock()

        self.MAX_DATA_SIZE = 1024
        
        # managing servers
        self.active_connections = 0

        # caching
        self.semantic_cache = SemanticCache()
        self.pending_requests = {}
        self.CACHING_LOGS = True
        
        self.server_processes = [] 

    def start_servers(self):
        """
        Starts the servers on the specified ports
        """
        # ports = [1235, 1236]  
        ports = []
        for port in ports:
            print("Starting server on port:", port)
            proc = subprocess.Popen([sys.executable, './server.py', str(port)])
            self.server_processes.append(proc)
            time.sleep(10)  # Give the servers time to start

    def stop_servers(self):
        """
        Stops the servers on the specified ports
        """
        for proc in self.server_processes:
            proc.terminate()
            proc.wait()  # Wait for the process to terminate
            
    def load_lb_algorithm(self):
        """
        Loads the load balancing algorithm based on the command line argument.
        """
        if len(sys.argv) < 1 or len(sys.argv) > 2:
            print("Usage: python load_balancer.py <algorithm_type>")
            sys.exit()
        
        if len(sys.argv) == 1 or sys.argv[1] == "r":
            print("Using Round Robin algorithm")
            self.LB_algorithm = RoundRobin()
            self.algorithm_type = AlgorithmType.ROUND_ROBIN
        elif sys.argv[1] == "c":
            print("Using Least Connections algorithm")
            self.LB_algorithm = LeastConnections()
            self.algorithm_type = AlgorithmType.LEAST_CONNECTIONS
        else:
            print("unknown algorithm type")
            sys.exit()
        
    async def check_heartbeat(self, server_writer, server_reader, host, port):
        """
        Periodically checks the heartbeats of the backend servers.
        If a server is not responding, it will be removed from the load balancer.
        """
        print(f"Started heartbeat listener for {host}:{port}")
        try:
            while True:
                try: 
                    data = await asyncio.wait_for(server_reader.read(self.MAX_DATA_SIZE), timeout=10)
                except asyncio.TimeoutError:
                    print(f"Timeout waiting for heartbeat from {host}:{port}.")
                    self.LB_algorithm.remove_server(host, port)
                    break
                if not data:
                    print(f"Server connection {host}:{port} has been closed")
                    self.LB_algorithm.remove_server(host, port)
                    break
                message = data.decode().strip()
                print(f"Received heartbeat from {host}:{port}: {message}")
        except Exception as e:
            print(f"Heartbeat error from {host}:{port}: {e}")
            self.LB_algorithm.remove_server(host, port)

    async def cli_to_srv_forward(self, client_reader, server_writer, client_writer):
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
                cache_response = self.semantic_cache.get(str(data))
                
                if cache_response is not None:
                    cache_response = cache_response.encode()
                    
                    if self.CACHING_LOGS:
                        print("Cache hit!")
                        print("Got cache_response of: ", cache_response)
                        
                    client_writer.write(cache_response)
                    await client_writer.drain()
                else:
                    # adding id to pending requests to ensure we will cache the response when it comes
                    request_id = str(uuid.uuid4())
                    self.pending_requests[request_id] = str(data)
                    
                    # appending unique ID to the data sent.
                    payload = f"{request_id}|{data}"
                    
                    if self.CACHING_LOGS:
                        print("Cache miss!")
                        print("Sending off payload: ", payload)
                        
                    server_writer.write(payload.encode())
                    await server_writer.drain()
        except Exception as e:
            print(f"Exception occurred: {e}")
        finally:
            server_writer.close()
            await server_writer.wait_closed()
            
    async def srv_to_cli_forward(self, server_reader, client_writer):
        """
        Forwards data from the server back to the client.

        Args:
            server_reader: StreamReader object that reads data from the server.
            client_writer: StreamWriter object that writes data to the client.
        """
        try:
            while True:
                # Read data from the server
                data = await server_reader.read(self.MAX_DATA_SIZE)
                if not data:
                    break
                data = data.decode()
                
                request_id, response_payload = data.split('|', 1)
                request_msg = self.pending_requests.pop(request_id, None)
                
                # Cache the response
                if request_msg:
                    if self.CACHING_LOGS:
                        print("Adding to cache: ", response_payload)
                    self.semantic_cache.add(request_msg, response_payload)
                    
                # Write the response back to the client
                client_writer.write(response_payload.encode())
                await client_writer.drain()
        except Exception as e:
            print(f"Exception occurred: {e}")
        finally:
            client_writer.close()
            await client_writer.wait_closed()

    async def handle_connection(self, reader, writer):
        """
        Handles incoming client connections and forwards requests to the appropriate backend server.

        Args:
            client_reader: StreamReader object that reads data from the client.
            client_writer: StreamWriter object that writes data to the client.
        """
        addr = writer.get_extra_info('peername')
        print(f"Load balancer received connection on port {addr[1]}")
        try:
            data = await asyncio.wait_for(reader.read(self.MAX_DATA_SIZE), timeout=5)
            if not data:
                print("No data received from client.")
                writer.close()
                await writer.wait_closed()
                return

            message = data.decode().strip()
            if message.startswith("REGISTER|"):
                parts = message.split("|")
                if len(parts) == 3:
                    server_host = parts[1]
                    server_port = int(parts[2])
                    self.LB_algorithm.add_server(server_host, server_port)
                    
                    writer.write(b"REGISTERED")
                    await writer.drain()
                    print(f"Server registered: {server_host}:{server_port}")
                    
                    await self.check_heartbeat(writer, reader, server_host, server_port)
                else:
                    print("Invalid register message format.")
                    writer.write(b"INVALID REGISTER MESSAGE")
                    await writer.drain()
                    
                    writer.close()
                    await writer.wait_closed()
            else:
                # Is a client connection
                print(f"Load balancer knows that this is a client")
                await self.handle_client(reader, writer)
        except asyncio.TimeoutError:
            print("Timeout waiting for data from connection.")
            writer.close()
            await writer.wait_closed()
        
    async def handle_client(self, client_reader, client_writer):
        """
        Handles a client connection by forwarding data to the appropriate backend server.

        Args:
            client_reader: StreamReader object that reads data from the client.
            client_writer: StreamWriter object that writes data to the client.
        """
        addr = client_writer.get_extra_info('peername')
        print(f"Load balancer received client on port {addr[1]}")
                
        server_writer = None
        server_reader = None
        index = None
           
        try:
            server = self.LB_algorithm.get_server()
            backend_port = server.port
            server_host = server.host
            server_reader, server_writer = await asyncio.open_connection(server_host, backend_port)
            print(f"Load balancer connected to backend server on port {backend_port}")

            async with self.lock:
                self.active_connections += 1
                print(f"Total active connections: {self.active_connections}")
            
            # Forward data in both directions
            await asyncio.gather(
                self.cli_to_srv_forward(client_reader, server_writer, client_writer),
                self.srv_to_cli_forward(server_reader, client_writer)
            )
        except Exception as e:
            print("Error connecting to backend server:", e)
        finally:
            async with self.lock:
                server.connection_count -= 1
                if self.algorithm_type == AlgorithmType.LEAST_CONNECTIONS:
                    heapq.heapify(self.LB_algorithm.servers)
                self.active_connections -= 1
                print(f"Load balancer closed connection with client on port {addr[1]}")
                print(f"Server on port {backend_port} has {server.connection_count} connections")
                print(f"Total active connections: {self.active_connections}")
            client_writer.close()
            if server_writer:
                server_writer.close()
                await server_writer.wait_closed()

    async def load_balancer(self):
        """
        Creates the load balancer server and starts listening for client connections.
        
        Args:
            From command line: algorithm_type (r for round robin, c for least connections).
        """

        # load the designated load balancing algorithm
        self.load_lb_algorithm()
        
        # start server processes
        self.start_servers()

        # start the load balancer
        load_balancer = await asyncio.start_server(
            lambda r, w: self.handle_connection(r, w),
            self.LB_HOST,
            self.LB_PORT
        )

        print(f"Load Balancer on port {self.LB_PORT} running on {self.LB_HOST}")

        try:
            async with load_balancer:
                await asyncio.gather(
                    load_balancer.serve_forever()
                )
        except asyncio.CancelledError:
            self.stop_servers()
            print("\nLoad balancer shutting down.")

if __name__ == '__main__':
    try:
        lb = LoadBalancer()
        asyncio.run(lb.load_balancer())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
