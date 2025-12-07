#!/usr/bin/env python3
# Simple HTTP REST server for TicTacToe 3D suitable for Render Web Service deployment.
# Endpoints:
#  - POST /connect        -> { "player_id": 0|1 }  (400 if full)
#  - GET  /state          -> full state JSON
#  - POST /move           -> { "player": id, "z":.., "y":.., "x":.. } -> updated state or 400
#
from flask import Flask, request, jsonify
import os
import threading

app = Flask(__name__)

lock = threading.Lock()

# Game state (same layout as your original server)
board = [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]
current_player = 0
winner = None
last_move = None

# Simple players tracking (player slots 0..1). Value True means slot is taken.
players = {0: False, 1: False}

def state_payload():
    return {
        "type": "state",
        "board": board,
        "current_player": current_player,
        "winner": winner,
        "last_move": last_move
    }

def check_winner_internal():
    # return 0 or 1 if someone won, else None
    def all_same(vals, v): return all(x == v for x in vals)
    lines = []
    for z in range(4):
        for y in range(4):
            lines.append([(z, y, x) for x in range(4)])
    for z in range(4):
        for x in range(4):
            lines.append([(z, y, x) for y in range(4)])
    for y in range(4):
        for x in range(4):
            lines.append([(z, y, x) for z in range(4)])
    for z in range(4):
        lines.append([(z, i, i) for i in range(4)])
        lines.append([(z, i, 3 - i) for i in range(4)])
    for x in range(4):
        lines.append([(i, i, x) for i in range(4)])
        lines.append([(i, 3 - i, x) for i in range(4)])
    for y in range(4):
        lines.append([(i, y, i) for i in range(4)])
        lines.append([(i, y, 3 - i) for i in range(4)])
    lines.append([(i, i, i) for i in range(4)])
    lines.append([(i, i, 3 - i) for i in range(4)])
    lines.append([(i, 3 - i, i) for i in range(4)])
    lines.append([(3 - i, i, i) for i in range(4)])
    for line in lines:
        vals = [board[z][y][x] for (z, y, x) in line]
        if all(v == -1 for v in vals):
            return 0
        if all(v == 1 for v in vals):
            return 1
    return None

@app.route("/connect", methods=["POST"])
def connect():
    global players
    with lock:
        # find free slot
        for pid in range(2):
            if not players.get(pid, False):
                players[pid] = True
                return jsonify({"player_id": pid})
    return jsonify({"error": "Server full"}), 400

@app.route("/disconnect", methods=["POST"])
def disconnect():
    # Optional: clients can inform they disconnect and free their slot
    data = request.get_json(silent=True) or {}
    pid = data.get("player_id")
    with lock:
        if pid in players:
            players[pid] = False
    return jsonify({"ok": True})

@app.route("/state", methods=["GET"])
def get_state():
    with lock:
        return jsonify(state_payload())

@app.route("/move", methods=["POST"])
def post_move():
    global current_player, winner, last_move
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing JSON"}), 400
    try:
        player = int(data.get("player"))
        z = int(data.get("z"))
        y = int(data.get("y"))
        x = int(data.get("x"))
    except Exception:
        return jsonify({"error": "Invalid fields"}), 400

    with lock:
        if winner is not None:
            return jsonify({"error": "Game already finished"}), 400
        if player != current_player:
            return jsonify({"error": "Not your turn"}), 400
        if not (0 <= z < 4 and 0 <= y < 4 and 0 <= x < 4):
            return jsonify({"error": "Out of bounds"}), 400
        if board[z][y][x] != 0:
            return jsonify({"error": "Cell occupied"}), 400

        board[z][y][x] = -1 if player == 0 else 1
        last_move = {"player": player, "z": z, "y": y, "x": x}
        w = check_winner_internal()
        if w is not None:
            winner = w
        else:
            current_player = 1 - current_player

        return jsonify(state_payload())

@app.route("/reset", methods=["POST"])
def reset():
    global board, current_player, winner, last_move
    with lock:
        board = [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]
        current_player = 0
        winner = None
        last_move = None
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5555"))
    # For Render, listen on 0.0.0.0:PORT
    app.run(host="0.0.0.0", port=port, threaded=True)