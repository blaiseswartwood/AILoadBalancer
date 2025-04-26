import socket
import sys
import threading

def server_thread(conn, client_num):
    while True:
        data = conn.recv(1024).decode()

        if not data:
            break
        else:
            print("Data from client ", str(client_num), ": ", str(data))
            data = str(data).upper()
            conn.send(data.encode())

    conn.close()

def server_program():
    host = socket.gethostname()
    host_ip = socket.gethostbyname(host)

    print("Host name: ", str(host))
    print("Host IP: ", str(host_ip))
    
    if(len(sys.argv) != 2):
        print("Usage: python server.py <port_number>")
        sys.exit()

    port = int(sys.argv[1])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', port))

    server_socket.listen(5)
    server_socket.settimeout(1) 
    
    client_num = 1

    try:
        while True:
            try:
                conn_socket, address = server_socket.accept() # currently blocking call
                print("Connection ", str(client_num), " made from ", str(address))

                # Start a new thread to handle the client
                t = threading.Thread(target=server_thread, args=(conn_socket, client_num,))
                t.start()
                client_num += 1

            except socket.timeout: # need better solution
                continue

    except KeyboardInterrupt:
        print("\nServer shutting down gracefully.")
    finally:
        server_socket.close()

if __name__ == '__main__':
    server_program()