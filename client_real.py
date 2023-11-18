from ast import Pass
import cmd
from ipaddress import ip_address
import threading
import socket
import json
import os
import shutil

dictionary = "D:/dictionary.txt"
#------------------------------------------------CLIENT SIDE---------------------------------------------------------------------------------#
class ClientShell(cmd.Cmd):
    intro = 'Welcome to the P2P client shell. Type help or ? to list commands.\n'
    prompt = '(client) '

    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        self.server_ip = 'localhost'  # Replace with actual server IP
        self.server_port = 5000       # Replace with actual server port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))
    
    def do_exit(self, arg):
        "Exit the client shell"
        print("Exiting client...")
        self.sock.close()
        return True  # Return True to stop the cmd loop and exit

    # This function return the response from the server
    def send_command(socket, command):
        try:
            # Send command
            message = json.dumps(command).encode('utf-8')
            socket.sendall(message)

            # Wait for the server's response
            response = socket.recv(4096).decode('utf-8')
            print(f"Server response: ")
            print(response)
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def do_publish(self, arg):
        "Inform the server of an existing file"
        lname, fname = arg.split(' ')
        filepath = input("Enter the path of the file: ")
        with open(dictionary, 'a') as file:
            # We have to protect this field cause this is a write-file action
            with self.lock:
                file.write(f"<{fname}> <{filepath}>\n")
            command = f"publish '{lname}' '{fname}'"
            self.send_command(self.sock, command)
    
    def receive_file(socket, file_name):
        with open(file_name, 'wb') as file:
            while True:
                data = socket.recv(1024)
                if not data:
                    break
                file.write(data)


    def do_fetch(self, fname):
        "Request the information of nodes holding specific file from the server"
        command = f"fetch '{fname}'"
        response = self.send_command(self.sock, command)
        lines = response.split("\n")
        for line in lines:
            # Extract values within angle brackets
            values = [value.strip(" <>") for value in line.split()] # Remove the '<' at the beginning and Remove the '>' at the end
            
            # Get ip_addr and port of the target node
            ip_address = (values[0])
            port = (values[1])
            
            # Establish connection
            p2p_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            p2p_sock.connect((ip_address, port))

            # Send request again
            self.send_command(p2p_sock, command)
            
            # Receive file
            self.receive_file(p2p_sock, f"D:/'{fname}'")

            break
        

#------------------------------------------------------------------SERVER SIDE--------------------------------------------------------------#
# This class will run parralel with the ClientShell
# But do not print anything, just handle implicitly
class Server():
    def __init__(self, host, port):
        super().__init__()
        self.server_host = host
        self.server_port = port
        self.server_socket = None
        self.clients_lock = threading.Lock()  # A lock to protect shared resources

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.server_host, self.server_port))
        self.server_socket.listen()
        threading.Thread(target=self.listen_to_clients, daemon=True).start()

    def listen_to_clients(self):
        while True:
            client_conn, client_addr = self.server_socket.accept()
            with self.clients_lock:
                self.clients[client_addr] = client_conn
            threading.Thread(target=self.handle_client, args=(client_conn, client_addr), daemon=True).start()
            
    def handle_client(self, client_conn, client_addr):
        while True:
            try:
                data = client_conn.recv(1024).decode('utf-8')
                if not data:
                    break
                command = data.strip().split(' ')
                if (command[0] == "fetch"):
                    filename = command[1]
                    self.fetch_file(client_conn, filename)
                else:
                    break
            except ConnectionResetError:
                break
            except Exception as e:
                break
        with self.clients_lock:
            self.clients.pop(client_addr, None)  # Remove client from the list upon disconnection
        client_conn.close()
    
    def send_file(self, socket, file_path):
        with open(file_path, 'rb') as file:
            data = file.read(1024)
            while data:
                socket.sendall(data)
                data = file.read(1024)
      
    def fetch_file(self, socket, fname):
        with open(dictionary, 'r') as file:
            for line in file:
                # Extract values within angle brackets
                # Remove the '<' at the beginning and Remove the '>' at the end
                values = [value.strip(" <>") for value in line.split()]
                
                current_fname = values[0]
                filepath = values[1]
                if current_fname == fname:
                    self.send_file(socket, filepath)
                    break
    

#-----------------------------------------------------------------EXECUTE CODE------------------------------------------------------------------------------#
def run_Server():
    host = 'localhost'  # Change to the appropriate interface
    port = 5000  # Change to the appropriate port
    server = Server(host, port)
    server.start_server()
    

def run_ClientShell():
    shell = ClientShell()
    shell.cmdloop()

if __name__ == '__main__':
    # Create threads for the server and client functions
    ClientShell_thread = threading.Thread(target=run_ClientShell)
    Server_thread = threading.Thread(target=run_Server)
    
    # Start both threads
    ClientShell_thread.start()
    Server_thread.start()
    
    # Wait for both threads to finish
    ClientShell_thread.join()
    Server_thread.join()
