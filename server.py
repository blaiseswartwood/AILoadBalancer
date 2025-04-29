import asyncio
import sys
from llm_module import get_llm_response

MAX_DATA_SIZE = 1024
SERVER_HOST = 'localhost'
SERVER_LOGS = True

LB_HOST = 'localhost'
LB_PORT = 1234

MAX_RETRIES = 5
RETRY_DELAY = 5 # seconds

heartbeat_count = 0
heartbeat_interval = 5 # seconds

async def connect_to_load_balancer(lb_host, lb_port, server_port):
    """Connects to the load balancer and returns the reader and writer objects."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            lb_reader, lb_writer = await asyncio.open_connection(lb_host, lb_port)
            registar = f"REGISTER|{SERVER_HOST}|{server_port}"
            lb_writer.write(registar.encode())
            await lb_writer.drain()

            data = await lb_reader.read(MAX_DATA_SIZE)
            data = data.decode().strip()
            if data and data == "REGISTERED":
                if SERVER_LOGS:
                    print(f"Server on port {server_port} registered with load balancer on {lb_host}:{lb_port}")
                return lb_reader, lb_writer
            else:
                raise ConnectionError("Unexpected response from load balancer.")
        except Exception as e:
            print(f"[Attempt {attempt}] Error connecting to load balancer: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
            else:
                print("Max retries reached. Exiting.")
                sys.exit(1)
                
async def heartbeat(lb_writer):
    """Sends a heartbeat signal to the load balancer to indicate that the server is alive."""
    global heartbeat_count
    while True:
        heartbeat_message = f"HEARTBEAT {heartbeat_count}"

        lb_writer.write(heartbeat_message.encode())
        if SERVER_LOGS:
            print(f"Server on port {SERVER_HOST} sending heartbeat to load balancer: {heartbeat_message}")
            
        await lb_writer.drain()
        heartbeat_count += 1
        await asyncio.sleep(heartbeat_interval)  # Send heartbeat every 5 seconds
        
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
            
            print(f"Server on port {port} received from port {addr[1]}: {data}")

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
    
    print(f"Server on port {port} connecting to the load balancer")
    load_balancer_reader, load_balancer_writer = await connect_to_load_balancer(LB_HOST, LB_PORT, port)

    print(f"Server on port {port} serving clients")
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, port), 
        SERVER_HOST, 
        port)
    
    if SERVER_LOGS:
        print(f"Server on port {port} running on {SERVER_HOST}")
    
    try:
        async with server:
            await asyncio.gather(
                server.serve_forever(),
                heartbeat(load_balancer_writer),
            )
    except asyncio.CancelledError:
        if SERVER_LOGS:
            print(f"Server on port {port} shutting down.")

if __name__ == '__main__':
    try:
        asyncio.run(server_program())
    except KeyboardInterrupt:  
        if SERVER_LOGS:
            print("\nInterrupted by user.")