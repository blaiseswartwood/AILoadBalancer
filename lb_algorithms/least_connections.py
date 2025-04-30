import heapq

from .lb_algorithm import LBAlgorithm
from .algorithm_type import BackendServer

class LeastConnections(LBAlgorithm):
    def make_server_holder(self):
        return []
    
    def remove_server(self, host, port):
        for server in self.servers:
            if server.host == host and server.port == port:
                self.servers.remove(server)
                heapq.heapify(self.servers) 
                print(f"Server {host}:{port} removed from load balancer")
                break
        print(f"Server {host}:{port} not found in load balancer")
        
    def get_server(self):
        server = heapq.heappop(self.servers)
        server.connection_count += 1
        heapq.heappush(self.servers, server)        
        print(f"Server {server.host}:{server.port} selected for request")
        return server
    
    def add_server(self, host, port):
        backend_server = BackendServer(host, port)
        heapq.heappush(self.servers, backend_server)
        print(f"Added server on port {port}")
