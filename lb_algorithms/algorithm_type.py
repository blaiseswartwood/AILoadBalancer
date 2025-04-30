from enum import Enum

class AlgorithmType(Enum):
    ROUND_ROBIN = 1
    LEAST_CONNECTIONS = 2

class BackendServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connection_count = 0
        
    def __lt__(self, other):
        if not isinstance(other, BackendServer):
            return NotImplemented
        return self.connection_count < other.connection_count
    



        
        
