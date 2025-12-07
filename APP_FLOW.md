# Skkribl Clone - Application Flow & Architecture

This document outlines the architectural flow of the Skkribl clone application, detailing how components communicate, how data is generated, and the lifecycle of a game session.

## 1. Architecture Overview

The application follows a standard **Client-Server** architecture using TCP Sockets for real-time communication.

*   **Server (`server/`)**: The central authority. It manages game state, turns, scores, and synchronizes all clients.
*   **Client (`client/`)**: The user interface (Tkinter). It captures user input (drawing, chatting) and renders the game state based on server messages.
*   **Protocol (`protocol.py`)**: A shared module defining the text-based message format used for communication.

---

## 2. Communication Protocol

All communication happens via raw TCP sockets using a custom text-based protocol defined in `protocol.py`.

**Format:** `TYPE:CONTENT\n`

| Message Type | Direction | Content Format | When is it sent? |
| :--- | :--- | :--- | :--- |
| `NAME` | Client -> Server | `PlayerName` | Immediately after connecting to the server. |
| `DRAW` | Client <-> Server | `x1,y1,x2,y2,color,width` | Continuously while the drawer drags the mouse (30-60 times/sec). |
| `CLEAR` | Client <-> Server | *(Empty)* | When the drawer clicks the "Clear" button. |
| `CHAT` | Client <-> Server | `ChatMessage` | When a player types a message and hits Enter. |
| `NEW_ROUND` | Server -> Client | `DrawerName` | At the very start of a new round. |
| `SECRET` | Server -> Client | `SecretWord` | At the start of a round, sent **ONLY** to the Drawer. |
| `HINT` | Server -> Client | `MaskedWord` (e.g. `A**L*`) | At the start of a round (to guessers) and updated every 5 seconds. |
| `TIME` | Server -> Client | `SecondsRemaining` | Every single second during an active round. |

---

## 3. Detailed Interaction Sequence

### 1. Connection Phase
*   **Client** (starts app) -> **Server**: Connects to socket.
*   **Client** -> **Server**: `NAME:Diden` (Sent immediately after connect).
*   **Server** -> **All Clients**: `CHAT:Server: Diden joined!` (Broadcast).
*   **Server**: Checks if `len(clients) == expected_players`. If true, starts game.

### 2. Round Start Phase
*   **Server** (Internal): Picks Drawer (Client A) and Word ("APPLE").
*   **Server** -> **All Clients**: `NEW_ROUND:Client A` (Tells everyone who is drawing).
*   **Server** -> **Client A (Drawer)**: `SECRET:APPLE` (Tells drawer the word).
*   **Server** -> **Clients B, C (Guessers)**: `HINT:*****` (Tells guessers the masked word).
*   **Server** -> **All Clients**: `TIME:60` (Starts the countdown).

### 3. Gameplay Phase (Repeated Loop)

#### A. Drawing (Real-time)
*   **Client A (Drawer)** -> **Server**: `DRAW:100,100,105,105,black,3` (Mouse moves).
*   **Server** -> **Clients B, C (Guessers)**: `DRAW:100,100,105,105,black,3` (Relayed instantly).
*   *(This happens 30-60 times per second)*

#### B. Timer (Every Second)
*   **Server** -> **All Clients**: `TIME:59`
*   **Server** -> **All Clients**: `TIME:58`
*   ...

#### C. Hint System (Every 5 Seconds)
*   **Server** -> **Clients B, C**: `HINT:A****` (Reveals first letter).

#### D. Chatting / Guessing
*   **Client B** -> **Server**: `CHAT:Is it a banana?`
*   **Server** (Checks word): "banana" != "APPLE".
*   **Server** -> **All Clients**: `CHAT:Client B: Is it a banana?`

*   **Client C** -> **Server**: `CHAT:apple`
*   **Server** (Checks word): "apple" == "APPLE"!
*   **Server** -> **All Clients**: `CHAT:Server: Client C GUESSED THE WORD!` (Winner announced).
*   **Server**: Adds points to Client C and Client A.

### 4. Round End Phase
*   **Server**: (If time runs out OR everyone guessed).
*   **Server** -> **All Clients**: `CHAT:Server: The word was APPLE`.
*   **Server**: Waits 4 seconds...
*   **Server**: Loops back to **Step 2** (New Round).

---

## 4. Threading Model

This application relies heavily on **Multithreading** to handle multiple players and real-time events simultaneously without freezing.

### Why Threads?
Standard Python code runs sequentially. If the server waited for Player A to send a message, it couldn't receive a message from Player B. If the Client waited for a message from the Server, the UI would freeze. Threads allow us to run multiple tasks in parallel.

### A. Server-Side Threads (`server/core.py`)

The server manages `N + 3` threads, where N is the number of players.

1.  **The "Doorman" Thread (`accept_clients`)**
    *   **Function:** `accept_clients()`
    *   **Role:** Sits in an infinite loop waiting for *new* connections (`socket.accept()`).
    *   **Why:** If this ran on the main thread, the server would be stuck waiting for a new player and couldn't process the game for existing players.

2.  **The "Client Handler" Threads (`handle_client`)**
    *   **Count:** One thread per connected player.
    *   **Function:** `handle_client(client_socket)`
    *   **Role:** Listens exclusively to *one specific player*.
    *   **Behavior:** It waits for a message (`recv`). When a message arrives (e.g., DRAW or CHAT), it processes it immediately.
    *   **Why:** This allows Player A to draw and Player B to chat at the exact same millisecond. They are processed by different workers.

3.  **The "Timer" Thread (`countdown`)**
    *   **Function:** `countdown(round_id)`
    *   **Role:** Wakes up every 1 second to decrement the time and broadcast `TIME:XX`.
    *   **Why:** Using `time.sleep(1)` on the main thread would freeze the entire server for 1 second, blocking all chat and drawing.

4.  **The "Transition" Thread (`_transition_to_next_round`)**
    *   **Function:** `_transition_to_next_round()`
    *   **Role:** Handles the 4-second pause between rounds.
    *   **Why:** Keeps the server responsive (able to receive chat/disconnects) during the "Game Over" pause.

### B. Client-Side Threads (`client/network.py` & `client/main.py`)

The client uses **2 Threads** to keep the UI responsive.

1.  **The Main UI Thread (Tkinter)**
    *   **Role:** Runs the `root.mainloop()`. It handles mouse clicks, drawing on the canvas, and updating labels.
    *   **Constraint:** This thread **MUST NOT BLOCK**. If it waits for network data, the window freezes ("Application Not Responding").

2.  **The Network Listener Thread (`listen`)**
    *   **Function:** `GameClient.listen()`
    *   **Role:** Sits in a loop waiting for data from the server (`socket.recv()`).
    *   **Behavior:**
        *   Receives a message (e.g., "DRAW:...").
        *   **CRITICAL:** It does *not* update the UI directly (which is unsafe).
        *   Instead, it puts the message into a **Thread-Safe Queue** (`self.msg_queue`).

### C. The Bridge: Queue System
To safely pass data from the **Network Thread** to the **UI Thread**:

1.  **Network Thread**: `queue.put(message)`
2.  **UI Thread**: Runs `process_queue()` every 10ms.
3.  **UI Thread**: `queue.get()` -> Updates Canvas/Labels.

This "Producer-Consumer" pattern ensures the application remains smooth and crash-free.
