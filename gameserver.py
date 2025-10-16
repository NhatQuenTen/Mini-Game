import socket, threading, json, time, sys

HOST = "0.0.0.0"
PORT = 12345
MAX_PLAYERS = 2

# Message helpers -------------------------------------------------
def send_json(conn, obj):
    try:
        data = json.dumps(obj, separators=(",", ":")).encode("utf-8") + b"\n"
        conn.sendall(data)
    except Exception:
        raise

def recv_json_line(conn):
    """Read until newline; simple line‑delimited JSON."""
    buff = b""
    while True:
        chunk = conn.recv(1)
        if not chunk:
            return None
        if chunk == b"\n":
            break
        buff += chunk
    try:
        return json.loads(buff.decode("utf-8"))
    except Exception:
        return None

# Core server -----------------------------------------------------
class PlayerConn:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.name = None
        self.move = None
        self.score = 0
        self.active = True

class RpsServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.lock = threading.Lock()
        self.players = []  # list[PlayerConn]
        self.round_index = 0
        self.running = True

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        threading.Thread(target=self.accept_loop, daemon=True).start()
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        finally:
            self.shutdown()

    # Accept new clients
    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def handle_client(self, conn, addr):
        player = PlayerConn(conn, addr)
        print(f"[SERVER] Connection from {addr}")
        # First message must be join
        first = recv_json_line(conn)
        if not first or first.get("type") != "join":
            send_json(conn, {"type": "error", "data": {"message": "Expected join"}})
            conn.close()
            return
        player.name = first["data"].get("name", f"Player{int(time.time())}")
        with self.lock:
            if len(self.players) >= MAX_PLAYERS:
                send_json(conn, {"type": "error", "data": {"message": "Server full"}})
                conn.close()
                print(f"[SERVER] Rejected {player.name} (full)")
                return
            self.players.append(player)
            idx = len(self.players)
        send_json(conn, {"type": "join_ack", "data": {"player_index": idx, "message": "Joined"}})
        self.broadcast_player_status()

        # If now enough players start first round
        self.maybe_start_round()

        try:
            while self.running and player.active:
                msg = recv_json_line(conn)
                if msg is None:
                    break
                mtype = msg.get("type")
                if mtype == "move":
                    self.register_move(player, msg["data"]["move"])
                elif mtype == "quit":
                    break
                else:
                    send_json(conn, {"type": "error", "data": {"message": "Unknown type"}})
        except Exception as e:
            print(f"[SERVER] Error with {player.name}: {e}")
        finally:
            self.disconnect(player)

    def broadcast_player_status(self):
        names = [p.name for p in self.players if p.active]
        payload = {"type": "players", "data": {"players": names}}
        self.broadcast(payload)

    def maybe_start_round(self):
        with self.lock:
            if len([p for p in self.players if p.active]) == 2:
                # Reset moves
                for p in self.players:
                    p.move = None
                self.round_index += 1
                self.broadcast({
                    "type": "start_round",
                    "data": {
                        "round": self.round_index,
                        "message": f"Round {self.round_index} - choose your move"
                    }
                })

    def register_move(self, player, move):
        if move not in ("rock", "paper", "scissors"):
            send_json(player.conn, {"type": "error", "data": {"message": "Invalid move"}})
            return
        with self.lock:
            if player.move is not None:
                send_json(player.conn, {"type": "error", "data": {"message": "Move already submitted"}})
                return
            player.move = move
            print(f"[SERVER] {player.name} -> {move}")
            all_submitted = all(p.move for p in self.players if p.active)
            if all_submitted and len(self.players) == 2:
                self.evaluate_round()

    def evaluate_round(self):
        p1, p2 = self.players
        m1, m2 = p1.move, p2.move
        result1 = self.determine(m1, m2)
        # Update scores
        if result1 == "win":
            p1.score += 1
            winner = p1.name
        elif result1 == "lose":
            p2.score += 1
            winner = p2.name
        else:
            winner = None
        result_packet = {
            "type": "round_result",
            "data": {
                "round": self.round_index,
                "winner": winner,
                "p1": {"name": p1.name, "move": m1, "score": p1.score},
                "p2": {"name": p2.name, "move": m2, "score": p2.score},
                "outcome_p1": result1,
                "outcome_p2": "tie" if result1 == "tie" else ("win" if result1 == "lose" else "lose")
            }
        }
        self.broadcast(result_packet)
        # Start next round after short pause
        threading.Timer(0.5, self.maybe_start_round).start()

    @staticmethod
    def determine(a, b):
        if a == b:
            return "tie"
        rules = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        return "win" if rules[a] == b else "lose"

    def broadcast(self, obj):
        dead = []
        for p in self.players:
            if not p.active:
                continue
            try:
                send_json(p.conn, obj)
            except Exception:
                dead.append(p)
        for p in dead:
            self.disconnect(p)

    def disconnect(self, player):
        with self.lock:
            if not player.active:
                return
            player.active = False
        try:
            player.conn.close()
        except:
            pass
        print(f"[SERVER] {player.name} disconnected")
        # Inform remaining
        self.broadcast({"type": "opponent_left", "data": {"message": f"{player.name} left"}})

    def shutdown(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        for p in self.players:
            try:
                p.conn.close()
            except:
                pass
        print("[SERVER] Closed.")

if __name__ == "__main__":
    print("Rock-Paper-Scissors Server")
    print(f"Listening on {HOST}:{PORT}")
    RpsServer().start()
