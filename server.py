import asyncio
import sys
from llm_module import get_llm_response

MAX_DATA_SIZE = 1024
SERVER_HOST = 'localhost'
SERVER_LOGS = False

async def handle_client(reader, writer, port):
    addr = writer.get_extra_info('peername')
    
    if SERVER_LOGS:
        print(f"Server on port {port} accepted connection on port {addr[1]}")
    try: 
        while True:
            data = await reader.read(MAX_DATA_SIZE)
            if not data:
                break
            
            if SERVER_LOGS:
                print(f"Server on port {port} received from port {addr[1]}: {data.decode().strip()}")
            
            # Process the data (e.g., convert to uppercase)
            data = await get_llm_response(str(data.decode().strip()))
            data = data.encode()
            
            writer.write(data)
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
    
    if(len(sys.argv) != 2):
        print("Usage: python server.py <port_number>")
        sys.exit(1)

    port = int(sys.argv[1])

    # starts the server, when a new client connects it calls handler
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