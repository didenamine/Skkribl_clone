# Skribbl Clone  

A **multiplayer drawing and guessing game** inspired by **Skribbl.io**, built using **Python**, **Tkinter**, **Sockets**, and **Threading** as part of a university course.

The project demonstrates real-time client-server communication, synchronization, and parallel execution using threads.

---

##  Project Overview

This application follows a **client-server architecture**:

* A **server interface** allows the host to configure:

  * Server port
  * Number of players
  * Number of rounds

* A **client interface** allows players to:

  * Draw words
  * Guess drawings in real time
  * Chat with other players

The server manages game logic, timing, synchronization, and scoring, while clients handle user interaction and rendering.

---

##  Game Rules

* The game is played in **multiple rounds**
* In each round:

  * Every player gets **one turn to draw**
  * Each drawing turn lasts **20 seconds** (can be configured)
  * The drawer receives a **random word**

###  Guessing Mechanics

* Other players try to guess the word using a **shared chat**
* Every **5 seconds**, a new letter of the word is revealed to the guessers
* Guessing behavior:

  *  Wrong guess → visible to all players
  *  Correct guess → confirmed privately (word remains hidden from others)

---

##  Scoring System

* **Guessers**:

  * 1st correct guess → **300 points** (can be configured)
  * Subsequent correct guesses receive fewer points

* **Drawer**:

  * Receives **50 points per correct guesser**

* At the end of the game, the server displays a **final scoreboard**

---

##  Technical Details

###  Technologies & Libraries

* **Python 3**
* **Tkinter** – GUI
* **socket** – Network communication
* **threading** – Parallel execution

###  Parallelism & Networking

* Each **client runs in its own thread**

* The **server handles multiple clients concurrently**

* Threads are used for:

  * Game timing synchronization
  * Managing drawing turns
  * Coordinating round progression


---

##  Application Interfaces

### Server Interface

* Configure game settings
* Start and manage the game session
* Display final scoreboard

### Client Interface

* Drawing canvas
* Chat window for guesses
* Real-time updates from the server

---

##  How to Run

### 1️⃣ Start the Server
#### ** if using linux ** : 
* make a venv
  ```bash
   python3 -m venv myvenv
   source myvenv/bin/activate
   pip install -r requirements.txt
  ```
  **For the server ** :
  ```bash
  cd server && python3 main.py
  ```
  **For the client ** :
  ```bash
  cd client && python3 main.py
  ```

#### ** others os ** :
  
```bash
pip install -r requirements.txt
cd skkribl/server python main.py
```

* Choose the port, number of players, and rounds

### 2️⃣ Start Clients

```bash
cd skkribl/client python main.py
```
* for each client login through a different terminal
* Join the game
* when all the clients (players) that re mentioned in the server interface enter the game starts
---

##  Future Improvements

* Player authentication
* Lobby system
* Better drawing tools
* Word categories and difficulty levels
* Persistence of scores


Feel free to fork, experiment, and improve the project!
