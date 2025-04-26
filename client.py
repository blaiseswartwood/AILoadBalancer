import socket
import sys

def client_program():
    if(len(sys.argv) != 3):
        print("Usage: python client.py <server_IP> <server_port>")
        sys.exit()

    port = int(sys.argv[2])
    server_address = (sys.argv[1], port)
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_address) 

    message = input(" -> ")
    while message.strip() != '.': 
        client_socket.send(message.encode())
        data = client_socket.recv(1025).decode()
        print("recieved from server: ", str(data))
        message = input(" -> ")
    client_socket.close()

if __name__ == '__main__':
    client_program()