from enum import Enum
from abc import ABC, abstractmethod
from collections import deque

class BackendServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connection_count = 0
        
class AlgorithmType(Enum):
    ROUND_ROBIN = 1
    LEAST_CONNECTIONS = 2
    
class LBAlgorithm(ABC):
    def __init__(self):
        self.servers = self.make_server_holder()
        
    @abstractmethod
    def make_server_holder(self):
        """
        Creates a server holder for the load balancer.

        Returns:
            A data structure to hold the servers.
        """
        pass
    
    @abstractmethod
    def remove_server(self, host, port):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        pass
        
    @abstractmethod
    def get_server(self):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        pass
    
    @abstractmethod
    def add_server(self, host, port):
        """
        Adds a new server to the load balancer.

        Args:
            port: The port number on which the new server will run.
        """
        pass

class RoundRobin(LBAlgorithm):
    
    def make_server_holder(self):
        """
        Creates a server holder for the load balancer.

        Returns:
            A data structure to hold the servers.
        """
        return deque()
    
    def remove_server(self, host, port):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        for server in self.servers:
            if server.host == host and server.port == port:
                self.servers.remove(server)
                print(f"Server {host}:{port} removed from load balancer")
                break
        print(f"Server {host}:{port} not found in load balancer")
        
    def get_server(self):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        server = self.servers.popleft()
        server_port = server.port
        server_host = server.host
        self.servers.append(server)
        print(f"Server {server_host}:{server_port} selected for request")
        return server
    
    def add_server(self, host, port):
        """
        Adds a new server to the load balancer.

        Args:
            port: The port number on which the new server will run.
        """
        backend_server = BackendServer(host, port)
        self.servers.append(backend_server)
        print(f"Added server on port {port}")
        
        
class LeastConnections(LBAlgorithm):
    
    def make_server_holder(self):
        """
        Creates a server holder for the load balancer.

        Returns:
            A data structure to hold the servers.
        """
        return deque()
    
    def remove_server(self, host, port):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        for server in self.servers:
            if server.host == host and server.port == port:
                self.servers.remove(server)
                print(f"Server {host}:{port} removed from load balancer")
                break
        print(f"Server {host}:{port} not found in load balancer")
        
    def get_server(self):
        """
        Removes a server from the load balancer.

        Args:
            index: The index of the server to be removed.
            host: The host of the server to be removed.
            port: The port of the server to be removed.
        """
        server = self.servers.popleft()
        server_port = server.port
        server_host = server.host
        self.servers.append(server)
        print(f"Server {server_host}:{server_port} selected for request")
        return server
    
    def add_server(self, host, port):
        """
        Adds a new server to the load balancer.

        Args:
            port: The port number on which the new server will run.
        """
        backend_server = BackendServer(host, port)
        self.servers.append(backend_server)
        print(f"Added server on port {port}")