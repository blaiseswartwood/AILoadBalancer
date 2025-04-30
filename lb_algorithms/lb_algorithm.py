from abc import ABC, abstractmethod

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