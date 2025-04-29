import subprocess
import sys
import time
import asyncio
from algorithm_type import AlgorithmType
from semantic_cache import SemanticCache
import uuid

class LoadBalancer:
    """
    LoadBalancer class that manages the backend servers and distributes requests to them.
    """
    def __init__(self):
        self.LB_HOST = 'localhost' 
        self.LB_PORT = 1234

        self.SERVER_HOST = []
        self.SERVER_PORTS = []
        self.server_processes = [] 
        
        self.CACHING_LOGS = True
        self.MAX_DATA_SIZE = 1024
        # managing servers
        self.next_server = 0
        self.active_connections = 0
        self.connection_counts = []
        self.lock = asyncio.Lock()

        # caching
        self.semantic_cache = SemanticCache()
        self.pending_requests = {}
        
    def start_servers(self):
        """
        Starts the servers on the specified ports
        """
        # ports = [1235, 1236]  

        # self.ports = [1235, 1236]  
        # self.SERVER_HOST = ['localhost', 'localhost']
        # self.connection_counts = [0, 0]
        #for port in self.SERVER_PORTS:
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
            
    def add_server(self, host, port):
        """
        Adds a new server to the load balancer.

        Args:
            port: The port number on which the new server will run.
        """
        self.SERVER_HOST.append(host)
        self.SERVER_PORTS.append(port)
        self.connection_counts.append(0)
        print(f"Added server on port {port}")
        
    def remove_server(self, index, host, port):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        print(f"Removing server {host}:{port} from load balancer")
        self.SERVER_HOST.pop(index)
        self.SERVER_PORTS.pop(index)
        self.connection_counts.pop(index)
        
    async def check_heartbeat(self, server_writer, server_reader, index, host, port):
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
                    self.remove_server(index, host, port)
                    break
                if not data:
                    print(f"Server connection {host}:{port} has been closed")
                    self.remove_server(index, host, port)
                    break
                message = data.decode().strip()
                print(f"Received heartbeat from {host}:{port}: {message}")
        except Exception as e:
            print(f"Heartbeat error from {host}:{port}: {e}")
            self.remove_server(index, host, port)

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


    async def handle_connection(self, reader, writer, algorithm_type):
        """
        Handles incoming client connections and forwards requests to the appropriate backend server.

        Args:
            client_reader: StreamReader object that reads data from the client.
            client_writer: StreamWriter object that writes data to the client.
            algorithm_type: The load balancing algorithm to use.
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
                    index = len(self.SERVER_PORTS)  # New server index
                    self.add_server(server_host, server_port)
                    
                    writer.write(b"REGISTERED")
                    await writer.drain()
                    print(f"Server registered: {server_host}:{server_port}")
                    
                    await self.check_heartbeat(writer, reader, index, server_host, server_port)
                else:
                    print("Invalid register message format.")
                    writer.write(b"INVALID REGISTER MESSAGE")
                    await writer.drain()
                    
                    writer.close()
                    await writer.wait_closed()
            else:
                # Is a client connection
                print(f"Load balancer knows that this is a client")
                await self.handle_client(reader, writer, algorithm_type)
        except asyncio.TimeoutError:
            print("Timeout waiting for data from connection.")
            writer.close()
            await writer.wait_closed()
        
    async def handle_client(self, client_reader, client_writer, algorithm_type):
        """
        Handles a client connection by forwarding data to the appropriate backend server.

        Args:
            client_reader: StreamReader object that reads data from the client.
            client_writer: StreamWriter object that writes data to the client.
            algorithm_type: The load balancing algorithm to use.
        """
        addr = client_writer.get_extra_info('peername')
        print(f"Load balancer received client on port {addr[1]}")
                
        server_writer = None
        server_reader = None
        index = None
           
        try:
            async with self.lock:
                if algorithm_type == AlgorithmType.ROUND_ROBIN:
                    backend_port = self.SERVER_PORTS[self.next_server]
                    index = self.next_server
                    self.next_server = (self.next_server + 1) % len(self.SERVER_PORTS) 
                elif algorithm_type == AlgorithmType.LEAST_CONNECTIONS: 
                    index = self.connection_counts.index(min(self.connection_counts))
                    backend_port = self.SERVER_PORTS[index]
                self.connection_counts[index] += 1
                
            server_reader, server_writer = await asyncio.open_connection(self.SERVER_HOST[index], backend_port)
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
                if index is not None:
                    self.connection_counts[index] -= 1
                self.active_connections -= 1
                print(f"Load balancer closed connection with client on port {addr[1]}")
                print(f"Server on port {backend_port} has {self.connection_counts[index]} connections")
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
        self.start_servers()

        # start the load balancer
        load_balancer = await asyncio.start_server(
            lambda r, w: self.handle_connection(r, w, algorithm_type),
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
