import asyncio
import sys
from llm import get_llm_response

MAX_DATA_SIZE = 1024
SERVER_HOST = 'localhost'

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Server on port accepted connection from {addr}")
    try: 
        while True:
            data = await reader.read(MAX_DATA_SIZE)
            if not data:
                break
            print(f"Received from {addr}: {data.decode().strip()}")
            
            # Process the data (e.g., convert to uppercase)
            data = await get_llm_response(data.decode().strip())
            data = data.encode()
            
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        print(f"Closing connection with {addr}")
        writer.close()
        await writer.wait_closed()

async def server_program():
    
    if(len(sys.argv) != 2):
        print("Usage: python server.py <port_number>")
        sys.exit(1)

    port = int(sys.argv[1])

    # starts the server, when a new client connects it calls handler
    server = await asyncio.start_server(handle_client, SERVER_HOST, port)
    print(f"Server on port {port} running on {SERVER_HOST}")
    
    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        print(f"\nServer on port {port} shutting down.")

if __name__ == '__main__':
    try:
        asyncio.run(server_program())
    except KeyboardInterrupt:  
        print("\nInterrupted by user.")