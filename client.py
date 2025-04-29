import asyncio
import sys

CLIENT_HOST = 'localhost'

async def client_program():
    """Client program that connects to the server and sends messages.
    
    The client reads messages from the user and sends them to the server.
    The keyword '.' is used to terminate the connection.
    """
    if(len(sys.argv) != 3):
        print("Usage: python client.py <server_IP> <server_port>")
        sys.exit()

    port = int(sys.argv[2])
    server_ip = sys.argv[1]
    
    client_reader, client_writer = await asyncio.open_connection(server_ip, port)

    client_writer.write("CLIENT|ADD".encode())
    await client_writer.drain()

    message = input(" -> ")
    while message.strip() != '.': 
        if message.strip() == '':
            continue
        
        client_writer.write(message.encode())
        await client_writer.drain()
        
        data = await client_reader.read(1024)
        data = data.decode()
        
        print("GPT2 Response:\n", str(data))
        message = input(" -> ")
    
    print("Closing client connection")
    client_writer.close()
    await client_writer.wait_closed()

if __name__ == '__main__':
    asyncio.run(client_program())

