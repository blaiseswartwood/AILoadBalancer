import asyncio
import sys
from llm_module import get_llm_response

MAX_DATA_SIZE = 1024
SERVER_HOST = 'localhost'
SERVER_LOGS = True

LB_HOST = 'localhost'
LB_PORT = 1234

async def connect_to_load_balancer(host, port):
    """Connects to the load balancer and returns the reader and writer objects.
    
    Args:
        host: The host address of the load balancer.
        port: The port number of the load balancer.
        
    Returns:
        reader: StreamReader object for reading data from the load balancer.
        writer: StreamWriter object for writing data to the load balancer.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        return reader, writer
    except Exception as e:
        print(f"Error connecting to load balancer: {e}")
        sys.exit(1)
        
async def handle_client(reader, writer, port):
    """Handles incoming client connections and processes requests using the LLM.
    
    Args:
        reader: StreamReader object that reads data from the client.
        writer: StreamWriter object that writes data to the client.
        port: The port number on which the server is running.
        
    Expected message format: <uid>|<payload>
    """
    addr = writer.get_extra_info('peername')
    if SERVER_LOGS:
        print(f"Server on port {port} accepted connection on port {addr[1]}")
        
    try: 
        while True:
            data = await reader.read(MAX_DATA_SIZE)
            if not data:
                break
            
            data = data.decode().strip()
            request_id, request_payload = data.split('|', 1)
            
            if SERVER_LOGS:
                print(f"Server on port {port} received from port {addr[1]}: {data}")
                print(f"LLM receiving: {request_payload}")
            
            # Process the data (e.g., convert to uppercase)
            response_payload = get_llm_response(str(request_payload))
            
            # adding the request ID
            data = f"{request_id}|{response_payload}"
            
            if SERVER_LOGS:
                print(f"LLM Response: {response_payload}")
                print(f"Server on port {port} sending back data to port {addr[1]}: {data}")

            writer.write(data.encode())
            await writer.drain()
    except Exception as e:
        if SERVER_LOGS:
            print(f"Error with client {addr}: {e}")
    finally:
        if SERVER_LOGS:
            print(f"Server on port {port} closed connection with {addr[1]}")
        writer.close()
        await writer.wait_closed()

async def server_program():
    """
    Creates the server and starts listening for incoming connections.
    
    Args:
        From command line: port number to connect to.
    """
    if(len(sys.argv) != 2):
        print("Usage: python server.py <port_number>")
        sys.exit(1)

    port = int(sys.argv[1])
    
    load_balancer_reader, load_balancer_writer = await connect_to_load_balancer(LB_HOST, LB_PORT)

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, port), 
        SERVER_HOST, 
        port)
    
    if SERVER_LOGS:
        print(f"Server on port {port} running on {SERVER_HOST}")
    
    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        if SERVER_LOGS:
            print(f"Server on port {port} shutting down.")

if __name__ == '__main__':
    try:
        asyncio.run(server_program())
    except KeyboardInterrupt:  
        if SERVER_LOGS:
            print("\nInterrupted by user.")