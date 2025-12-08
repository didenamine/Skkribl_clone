import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
import queue
import config
import protocol
from client.network import GameClient


class PictionaryUI:
    def __init__(self):
        self.client = GameClient(self.handle_message)
        self.msg_queue = queue.Queue()
        
        # Game State
        self.is_drawer = False
        self.last_x = None
        self.last_y = None
        self.current_color = "black"
        self.line_width = 3
        self.name = "Guest"
        self.root = tk.Tk()
        self.root.title("Skkribl Clone")
        self.root.geometry("1000x700")
        self.root.configure(bg="#e0e0e0")

        # Ask for name 
        """pop up UI to ask about the name ; i ll make into the main frame later TODO , for now  i ll stick with this approach """
        self.name = simpledialog.askstring("Name", "Enter your name:")
        if not self.name: self.name = "Guest"
        
        if not self.client.connect(self.name):
            ####POPup when the server isn't listening to client or the server is closed .. 
            messagebox.showerror("Error", "Could not connect to server")
            self.root.destroy()
            return

        self.setup_ui()
        #after each 100ms will process the messages queue 
        self.root.after(100, self.process_queue)
        self.root.mainloop()

    def setup_ui(self):
        # Top Frame
        self.top_frame = tk.Frame(self.root, bg="#333", pady=10)
        self.top_frame.pack(fill=tk.X)
        
        self.info_label = tk.Label(self.top_frame, text="Waiting...", font=("Helvetica", 16, "bold"), bg="#333", fg="white")
        self.info_label.pack(side=tk.LEFT, padx=20)

        self.timer_label = tk.Label(self.top_frame, text="Time: --", font=("Helvetica", 16, "bold"), bg="#333", fg="#FFEB3B")
        self.timer_label.pack(side=tk.RIGHT, padx=20)

        # Middle
        self.middle_frame = tk.Frame(self.root, bg="#e0e0e0", pady=10, padx=10)
        self.middle_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas
        self.canvas_frame = tk.Frame(self.middle_frame, bg="white", bd=2, relief=tk.SUNKEN)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.drawing)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)

        # Chat
        self.chat_frame = tk.Frame(self.middle_frame, bg="#e0e0e0", width=300)
        self.chat_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.chat_frame.pack_propagate(False)

        self.chat_log = tk.Text(self.chat_frame, state='disabled', wrap=tk.WORD, font=("Arial", 10))
        self.chat_log.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.entry_frame = tk.Frame(self.chat_frame)
        self.entry_frame.pack(fill=tk.X)

        self.entry_box = tk.Entry(self.entry_frame, font=("Arial", 12))
        self.entry_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry_box.bind("<Return>", self.send_chat)

        self.send_btn = tk.Button(self.entry_frame, text="Send", command=self.send_chat, bg="#4CAF50", fg="white")
        self.send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Bottom Controls
        self.controls_frame = tk.Frame(self.root, bg="#ddd", pady=10)
        self.controls_frame.pack(fill=tk.X)

        self.color_btn = tk.Button(self.controls_frame, text="Color", command=self.choose_color, bg="black", fg="white", width=10)
        self.color_btn.pack(side=tk.LEFT, padx=10)

        tk.Label(self.controls_frame, text="Size:", bg="#ddd").pack(side=tk.LEFT)
        self.size_scale = tk.Scale(self.controls_frame, from_=1, to=20, orient=tk.HORIZONTAL, command=self.set_line_width, bg="#ddd")
        self.size_scale.set(self.line_width)
        self.size_scale.pack(side=tk.LEFT, padx=10)

        self.clear_btn = tk.Button(self.controls_frame, text="Clear", command=self.clear_canvas, bg="#f44336", fg="white")
        self.clear_btn.pack(side=tk.RIGHT, padx=10)

        self.update_controls(False)
#This function is used to update the controls based on the current state of the game
    def update_controls(self, is_drawer):
        state = tk.NORMAL if is_drawer else tk.DISABLED
        self.color_btn.config(state=state)
        self.size_scale.config(state=state)
        self.clear_btn.config(state=state)
#producer
    def handle_message(self, msg_string):
        self.msg_queue.put(msg_string)
#consumer
    def process_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            self.process_message(msg)
        self.root.after(10, self.process_queue)

    def process_message(self, msg_string):
        type, content = protocol.parse_msg(msg_string)
        if not type: return

        if type == "DRAW":
            parts = content.split(",")
            if len(parts) >= 6:
                x1, y1, x2, y2 = map(int, parts[:4])
                color = parts[4]
                width = int(parts[5])
                self.canvas.create_line(x1, y1, x2, y2, width=width, fill=color, capstyle=tk.ROUND, smooth=True)
        
        elif type == "CLEAR":
            self.canvas.delete("all")
        
        elif type == "CHAT":
            self.chat_log.config(state='normal')
            self.chat_log.insert(tk.END, content + "\n")
            self.chat_log.see(tk.END)
            self.chat_log.config(state='disabled')
        
        elif type == "TIME":
            self.timer_label.config(text=f"Time: {content}")
        
        elif type == "NEW_ROUND":
            self.canvas.delete("all")
            drawer = content
            if drawer == self.name:
                self.is_drawer = True
                self.info_label.config(text="YOU ARE DRAWING!", fg="#4CAF50")
                self.update_controls(True)
            else:
                self.is_drawer = False
                self.info_label.config(text=f"{drawer} is drawing", fg="#FF9800")
                self.update_controls(False)
        
        elif type == "SECRET":
            self.info_label.config(text=f"DRAW THIS: {content.upper()}")
            
        elif type == "HINT":
            self.info_label.config(text=f"GUESS: {content}")

    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def drawing(self, event):
        if not self.is_drawer: return
        x, y = event.x, event.y
        if self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, x, y, width=self.line_width, fill=self.current_color, capstyle=tk.ROUND, smooth=True)
            self.client.send(protocol.make_msg("DRAW", f"{self.last_x},{self.last_y},{x},{y},{self.current_color},{self.line_width}"))
        self.last_x, self.last_y = x, y

    def send_chat(self, event=None):
        msg = self.entry_box.get()
        if msg:
            self.client.send(protocol.make_msg("CHAT", msg))
            self.entry_box.delete(0, tk.END)

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.current_color = color
            self.color_btn.config(bg=color)

    def set_line_width(self, val):
        self.line_width = int(val)

    def clear_canvas(self):
        if self.is_drawer:
            self.canvas.delete("all")
            self.client.send(protocol.make_msg("CLEAR"))

if __name__ == "__main__":
    PictionaryUI()
