from collections import deque

from .lb_algorithm import LBAlgorithm  
from .algorithm_type import BackendServer

class RoundRobin(LBAlgorithm):
    
    def make_server_holder(self):
        return deque()
    
    def remove_server(self, host, port):
        for server in self.servers:
            if server.host == host and server.port == port:
                self.servers.remove(server)
                print(f"Server {host}:{port} removed from load balancer")
                break
        print(f"Server {host}:{port} not found in load balancer")
        
    def get_server(self):
        server = self.servers.popleft()
        server_port = server.port
        server_host = server.host
        self.servers.append(server)
        print(f"Server {server_host}:{server_port} selected for request")
        return server
    
    def add_server(self, host, port):
        backend_server = BackendServer(host, port)
        self.servers.append(backend_server)
        print(f"Added server on port {port}")