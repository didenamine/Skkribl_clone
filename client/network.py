import socket
import threading
import sys
import os
import config
import protocol
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class GameClient:
    def __init__(self, msg_callback):
        self.client_socket = None
        self.msg_callback = msg_callback
        self.running = False
    def connect(self, name):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((config.HOST, config.PORT))
            self.running = True
            # Send Name
            self.send(protocol.make_msg("NAME", name))
            # Start Listener
            threading.Thread(target=self.listen, daemon=True).start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    def send(self, msg_string):
        if self.client_socket:
            try:
                self.client_socket.send(msg_string.encode('utf-8'))
            except:
                self.close()
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
    def close(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
