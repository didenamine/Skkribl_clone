import socket
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import protocol


class GameClient:
    #msg_callback here will get the handle_message later on from the main.py  of the client ...  
    def __init__(self, msg_callback):
        self.client_socket = None
        #messages from the server 
        self.msg_callback = msg_callback
        self.running = False
#typical function to connect to the server but here i do send the name with it 
    def connect(self, name):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((config.HOST, config.PORT))
            self.running = True
            # Send Name
            self.send(protocol.make_msg("NAME", name))
            # Start Listener I used daemon True here because i don't want to block the main thread
            threading.Thread(target=self.listen, daemon=True).start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
"""function to send messages to the server"""
    def send(self, msg_string):
        if self.client_socket:
            try:
                self.client_socket.send(msg_string.encode('utf-8'))
            except:
                self.close()
    """"a while True loop that listens for messages from the server"""
    def listen(self):
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data: break
                messages = data.split('\n')
                for msg in messages:
                    if msg:
                        self.msg_callback(msg)
            except:
                break
        self.close()
    #closing this client socket and setting running to false
    def close(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
