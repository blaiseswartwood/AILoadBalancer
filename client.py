import asyncio
import sys

CLIENT_HOST = 'localhost'

async def client_program():
    if(len(sys.argv) != 3):
        print("Usage: python client.py <server_IP> <server_port>")
        sys.exit()

    port = int(sys.argv[2])
    server_ip = sys.argv[1]
    
    client_reader, client_writer = await asyncio.open_connection(server_ip, port)

    message = input(" -> ")
    while message.strip() != '.': 
        if message.strip() == '':
            continue
        
        client_writer.write(message.encode())
        await client_writer.drain()
        
        data = await client_reader.read(1024)
        data = data.decode()
        
        print("recieved from server: ", str(data.decode()))
        message = input(" -> ")
    
    print("Closing client connection")
    client_writer.close()
    await client_writer.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(client_program())
    except KeyboardInterrupt:
        print("\nClient program terminated.")
