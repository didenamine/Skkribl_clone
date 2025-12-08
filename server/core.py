import socket
import threading
import random
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
import config
import protocol 

class ServerCore:
    def __init__(self, log_callback=None, update_count_callback=None):
        self.host = config.HOST
        self.port = config.PORT
        self.expected_players = config.DEFAULT_PLAYERS
        
        self.server_socket = None
        self.running = False
        self.clients = []
        self.player_names = {}
        
        self.current_word = ""
        self.drawer_socket = None
        self.drawer_index = -1
        
        self.round_active = False
        
        # tracker for  who guessed correctly in the current round .. set is used to avoid duplicates
        self.correct_guesses = set()
        self.round_id = 0
        
        # game Limits (the rounds)
        self.max_rounds = config.DEFAULT_ROUNDS
        self.current_round = 1
        self.turns_in_round = 0
        
        self.scores = {} # Socket -> Int
        
        # Callbacks for UI
        self.log_callback = log_callback
        #this callback is used to update the player count in the main frame
        self.update_count_callback = update_count_callback

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def start(self, port, expected_players, max_rounds):
        self.port = port
        self.expected_players = expected_players
        self.max_rounds = max_rounds
        
        # Reset Game State
        self.current_round = 1
        self.turns_in_round = 0
        self.drawer_index = -1
        self.scores.clear()
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            self.running = True
            self.log(f"Server started on {self.host}:{self.port}")
            self.log(f"Config: {self.expected_players} Players, {self.max_rounds} Rounds")
            self.log(f"Waiting for players...")
            
            threading.Thread(target=self.accept_clients, daemon=True).start()
            return True
        except Exception as e:
            self.log(f"Error starting server: {e}")
            return False

    def stop(self):
        self.running = False
        self.round_active = False
        
        if self.server_socket:
            self.server_socket.close()
            
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        self.player_names.clear()
        self.scores.clear()
        self.log("Server stopped.")

    def accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                if not self.running: break
                
                self.clients.append(client_socket)
                self.log(f"Connection from {addr}")
                if self.update_count_callback: self.update_count_callback(len(self.clients), self.expected_players)
                
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except OSError:
                break

    def remove_client(self, client):
        if client in self.clients:
            self.clients.remove(client)
            if client in self.player_names:
                del self.player_names[client]
            if client in self.scores:
                del self.scores[client]
            
            # If a client disconnects we might need to check if round should end
            if client in self.correct_guesses:
                self.correct_guesses.remove(client)
                
            client.close()
            self.log("Client disconnected")
            if self.update_count_callback: self.update_count_callback(len(self.clients), self.expected_players)

    def broadcast(self, message, exclude_socket=None):
        for client in self.clients:
            if client != exclude_socket:
                try:
                    client.send(f"{message}\n".encode('utf-8'))
                except:
                    pass

    def end_round(self, message):
        if not self.round_active: return
        self.round_active = False
        
        self.broadcast(protocol.make_msg("CHAT", message))
        self.broadcast(protocol.make_msg("HINT", f"ANSWER: {self.current_word}"))
        
        threading.Thread(target=self._transition_to_next_round, daemon=True).start()

    def _transition_to_next_round(self):
        # 4 seconds delay before starting new round
        time.sleep(4)
        self.start_new_round()

    def start_new_round(self):
        #checks if there are any clients (players)
        if not self.clients: return
        
        # Check Round Progress
        if self.turns_in_round >= len(self.clients):
            self.current_round += 1
            self.turns_in_round = 0
            
        if self.current_round > self.max_rounds:
            self.log("Game Over! Max rounds reached.")
            self.broadcast(protocol.make_msg("CHAT", "Server: --- GAME OVER ---"))
            
            # Announce Winner
            if self.scores:
                sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
                winner_socket, winner_score = sorted_scores[0]
                winner_name = self.player_names.get(winner_socket, "Unknown")
                
                self.broadcast(protocol.make_msg("CHAT", f"Server: WINNER is {winner_name} with {winner_score} points!"))
                
                msg = "Server: Final Scores:\n"
                for sock, score in sorted_scores:
                    pname = self.player_names.get(sock, "Unknown")
                    msg += f" - {pname}: {score}\n"
                self.broadcast(protocol.make_msg("CHAT", msg))
            
            self.round_active = False
            return

        self.turns_in_round += 1
        
        self.round_active = False
        self.correct_guesses.clear()
        self.round_id += 1 # Increment round ID to invalidate old timers
        
        time.sleep(0.1) 

        self.drawer_index = (self.drawer_index + 1) % len(self.clients)
        self.drawer_socket = self.clients[self.drawer_index]
        self.current_word = random.choice(config.WORD_LIST)
        
        drawer_name = self.player_names.get(self.drawer_socket, "Unknown")
        self.log(f"Round {self.current_round}/{self.max_rounds} - Turn {self.turns_in_round}/{len(self.clients)}")
        self.log(f"New Round! Drawer: {drawer_name}, Word: {self.current_word}")

        self.broadcast(protocol.make_msg("NEW_ROUND", drawer_name))
        self.broadcast(protocol.make_msg("CHAT", f"Server: Round {self.current_round}/{self.max_rounds}"))
        
        # Initial Hint
        self.hint_string = "*" * len(self.current_word)
        self.broadcast(protocol.make_msg("HINT", self.hint_string), exclude_socket=self.drawer_socket)
        try:
            self.drawer_socket.send(protocol.make_msg("SECRET", self.current_word).encode('utf-8'))
        except:
            pass
            
        self.round_active = True
        threading.Thread(target=self.countdown, args=(self.round_id,), daemon=True).start()

    def countdown(self, round_id):
        for i in range(config.ROUND_TIME, -1, -1):
            if not self.running or not self.round_active or self.round_id != round_id:
                return
            # Hint Logic: Reveal a letter every 5 seconds ////"""""" FOR NOW ""
            elapsed = config.ROUND_TIME - i
            if elapsed > 0 and elapsed % 5 == 0:
                num_to_reveal = elapsed // 5
                if num_to_reveal < len(self.current_word):
                    self.hint_string = self.current_word[:num_to_reveal] + "*" * (len(self.current_word) - num_to_reveal)
                    self.broadcast(protocol.make_msg("HINT", self.hint_string), exclude_socket=self.drawer_socket)

            self.broadcast(protocol.make_msg("TIME", str(i)))
            time.sleep(1)
        
        if self.round_active and self.round_id == round_id:
            self.log("Round time up!")
            self.end_round(f"Server: Time's up! The word was {self.current_word}")

    def handle_client(self, client):
        try:
            while self.running:
                data = client.recv(1024).decode('utf-8')
                if not data: break
                
                messages = data.split('\n')
                for msg_string in messages:
                    if not msg_string: continue
                    
                    msg_type, content = protocol.parse_msg(msg_string)
                    
                    if msg_type == "NAME":
                        self.player_names[client] = content
                        self.scores[client] = 0
                        self.log(f"Player joined: {content}")
                        self.broadcast(protocol.make_msg("CHAT", f"Server: {content} joined! ({len(self.clients)}/{self.expected_players})"))
                        
                        if len(self.clients) >= self.expected_players:
                            if not self.current_word:
                                self.broadcast(protocol.make_msg("CHAT", "Server: All players connected! Starting game..."))
                                self.start_new_round()
                        else:
                            self.broadcast(protocol.make_msg("CHAT", f"Server: Waiting for {self.expected_players - len(self.clients)} more..."))

                    elif msg_type == "DRAW":
                        self.broadcast(msg_string, exclude_socket=client)

                    elif msg_type == "CLEAR":
                        self.broadcast(protocol.make_msg("CLEAR"), exclude_socket=client)

                    elif msg_type == "CHAT":
                        name = self.player_names.get(client, "Unknown")
                        
                        # 1. Block Drawer from Chatting
                        if client == self.drawer_socket:
                            try:
                                client.send(protocol.make_msg("CHAT", "Server: You cannot chat while drawing!").encode('utf-8'))
                            except:
                                pass
                            continue

                        # 2. Check if it's a correct guess
                        if self.round_active and content.strip().lower() == self.current_word.lower():
                            if client not in self.correct_guesses:
                                # POINTS ....
                                # starting with 300 points for the first solver , and then getting reduces by 50 for each solver.
                                rank = len(self.correct_guesses)
                                points = max(300 -(rank *50),50)
                                
                                self.scores[client] += points
                                self.scores[self.drawer_socket] += 50 # Bonus for drawer if someone guessed the word
                                
                                self.correct_guesses.add(client)
                                self.broadcast(protocol.make_msg("CHAT", f"Server: {name} GUESSED THE WORD! (+{points} pts)"))
                                self.log(f"{name} guessed the word!")
                                # Check if everyone guessd ofc except the current drawer
                                num_guessers = len(self.clients) - 1
                                if num_guessers > 0 and len(self.correct_guesses) >= num_guessers:
                                    self.end_round("Server: Everyone guessed correctly!")
                            else:
                                # Already guessed
                                try:
                                    client.send(protocol.make_msg("CHAT", "Server: You already guessed the word!").encode('utf-8'))
                                except:
                                    pass
                        else:
                            # Normal chat
                            self.broadcast(protocol.make_msg("CHAT", f"{name}: {content}"))

        except Exception as e:
            pass
        finally:
            self.remove_client(client)
