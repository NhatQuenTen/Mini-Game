import tkinter as tk
from tkinter import messagebox
import socket, threading, json, sys

SERVER_HOST_DEFAULT = "localhost"
SERVER_PORT_DEFAULT = 12345

# ---- Networking helpers ----
def send_json(sock, obj):
    try:
        sock.sendall(json.dumps(obj, separators=(",", ":")).encode("utf-8") + b"\n")
    except Exception:
        raise

def recv_json_line(sock):
    buff = b""
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None
        if chunk == b"\n":
            break
        buff += chunk
    try:
        return json.loads(buff.decode("utf-8"))
    except Exception:
        return None

# ---- Styled button ----
class ModernButton(tk.Button):
    def __init__(self, parent, text, command, bg="#4a90e2", hover="#357abd"):
        super().__init__(parent, text=text, command=command, bd=0, relief="flat",
                         fg="white", font=("Arial", 11, "bold"), bg=bg, activebackground=bg,
                         cursor="hand2", padx=16, pady=8)
        self._bg, self._hover = bg, hover
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

# ---- Client GUI ----
class RpsClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RPS Client")
        self.root.geometry("640x480")
        self.root.configure(bg="#1a1a2e")
        self.sock = None
        self.player_name = ""
        self.state = "menu"
        self.move_buttons = {}
        self.status_var = tk.StringVar(value="Idle")
        self.score_var = tk.StringVar(value="Score: -")
        self.round_var = tk.StringVar(value="Round: -")
        self.opponent_name = None
        self.build_menu()
        self.listener_thread = None
        self.pending_move = None

    # UI builders -------------------------------------------------
    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def label(self, parent, txt, size=14, fg="#ffffff"):
        return tk.Label(parent, text=txt, font=("Arial", size, "bold"), fg=fg, bg="#1a1a2e")

    def build_menu(self):
        self.clear()
        self.state = "menu"
        self.label(self.root, "🎮 Rock-Paper-Scissors", 22).pack(pady=30)
        frm = tk.Frame(self.root, bg="#1a1a2e")
        frm.pack(pady=10)
        tk.Label(frm, text="Name:", fg="white", bg="#1a1a2e").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.name_entry = tk.Entry(frm, width=22)
        self.name_entry.grid(row=0, column=1, pady=4)
        tk.Label(frm, text="Host:", fg="white", bg="#1a1a2e").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self.host_entry = tk.Entry(frm, width=22)
        self.host_entry.insert(0, SERVER_HOST_DEFAULT)
        self.host_entry.grid(row=1, column=1, pady=4)
        tk.Label(frm, text="Port:", fg="white", bg="#1a1a2e").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        self.port_entry = tk.Entry(frm, width=22)
        self.port_entry.insert(0, str(SERVER_PORT_DEFAULT))
        self.port_entry.grid(row=2, column=1, pady=4)
        ModernButton(self.root, "Connect", self.connect, "#27ae60", "#2ecc71").pack(pady=20)
        tk.Label(self.root, textvariable=self.status_var, fg="#aaaaaa", bg="#1a1a2e").pack(pady=8)

    def build_game(self):
        self.clear()
        top = tk.Frame(self.root, bg="#2d2d44", height=70)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text=self.player_name, fg="#27ae60", bg="#2d2d44", font=("Arial", 14, "bold")).pack(side="left", padx=20)
        tk.Label(top, textvariable=self.round_var, fg="#f1c40f", bg="#2d2d44", font=("Arial", 12)).pack(side="left", padx=10)
        tk.Label(top, textvariable=self.score_var, fg="#95a5a6", bg="#2d2d44", font=("Arial", 12)).pack(side="left", padx=10)
        tk.Label(top, text="Opponent: ", fg="#e74c3c", bg="#2d2d44", font=("Arial", 12)).pack(side="left", padx=(40, 4))
        self.opp_label = tk.Label(top, text="...", fg="#e74c3c", bg="#2d2d44", font=("Arial", 12, "bold"))
        self.opp_label.pack(side="left")

        center = tk.Frame(self.root, bg="#1a1a2e")
        center.pack(expand=True)
        self.prompt_label = self.label(center, "Waiting for server...", 18)
        self.prompt_label.pack(pady=30)

        moves_frame = tk.Frame(center, bg="#1a1a2e")
        moves_frame.pack(pady=10)

        for mv, color, hover in [
            ("rock", "#7f8c8d", "#95a5a6"),
            ("paper", "#3498db", "#5dade2"),
            ("scissors", "#e74c3c", "#ec7063")
        ]:
            btn = ModernButton(moves_frame, mv.upper(), lambda m=mv: self.send_move(m), color, hover)
            btn.pack(side="left", padx=10, ipadx=14, ipady=10)
            self.move_buttons[mv] = btn

        ModernButton(self.root, "Quit", self.quit_game, "#34495e", "#566573").pack(pady=15)
        self.disable_moves()

    # Networking --------------------------------------------------
    def connect(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter name")
            return
        host = self.host_entry.get().strip() or SERVER_HOST_DEFAULT
        try:
            port = int(self.port_entry.get().strip() or SERVER_PORT_DEFAULT)
        except ValueError:
            messagebox.showerror("Error", "Invalid port")
            return
        self.player_name = name
        self.status_var.set("Connecting...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            return
        # Send join
        send_json(self.sock, {"type": "join", "data": {"name": self.player_name}})
        self.build_game()
        self.listener_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.listener_thread.start()

    def listen_loop(self):
        try:
            while True:
                msg = recv_json_line(self.sock)
                if msg is None:
                    self.on_disconnect()
                    break
                self.handle_message(msg)
        except Exception:
            self.on_disconnect()

    def handle_message(self, msg):
        t = msg.get("type")
        data = msg.get("data", {})
        if t == "join_ack":
            self.status_var.set("Joined server. Waiting for players...")
        elif t == "players":
            players = data.get("players", [])
            # Opponent name (any other)
            opp = [p for p in players if p != self.player_name]
            self.opponent_name = opp[0] if opp else None
            self.opp_label.config(text=self.opponent_name or "Waiting...")
        elif t == "start_round":
            self.round_var.set(f"Round: {data.get('round')}")
            self.prompt_label.config(text=data.get("message", "Your move"))
            self.pending_move = None
            self.enable_moves()
        elif t == "round_result":
            self.disable_moves()
            self.show_result(data)
        elif t == "opponent_left":
            self.disable_moves()
            self.prompt_label.config(text="Opponent left. Waiting...")
            self.status_var.set("Opponent disconnected")
        elif t == "error":
            messagebox.showerror("Server Error", data.get("message", "Unknown error"))
        else:
            # Unknown types ignored
            pass

    # Move submission
    def send_move(self, move):
        if self.pending_move:
            return
        self.pending_move = move
        self.disable_moves()
        self.prompt_label.config(text=f"You picked {move.upper()}. Waiting...")
        try:
            send_json(self.sock, {"type": "move", "data": {"move": move}})
        except Exception:
            self.on_disconnect()

    def show_result(self, data):
        p1 = data["p1"]
        p2 = data["p2"]
        you = p1 if p1["name"] == self.player_name else p2
        opp = p2 if you is p1 else p1
        outcome = "Win ✅" if data["winner"] == self.player_name else ("Tie 🤝" if data["winner"] is None else "Lose ❌")
        self.score_var.set(f"Score: {p1['name']} {p1['score']} - {p2['name']} {p2['score']}")
        # Popup
        popup = tk.Toplevel(self.root)
        popup.title("Round Result")
        popup.geometry("320x240")
        popup.configure(bg="#1a1a2e")
        tk.Label(popup, text=outcome, font=("Arial", 20, "bold"),
                 fg=("#27ae60" if "Win" in outcome else "#f39c12" if "Tie" in outcome else "#e74c3c"),
                 bg="#1a1a2e").pack(pady=16)
        tk.Label(popup, text=f"You: {you['move'].upper()}\nOpponent: {opp['move'].upper()}",
                 fg="white", bg="#1a1a2e", font=("Arial", 14)).pack(pady=8)
        tk.Label(popup, text=self.score_var.get(), fg="#aaaaaa", bg="#1a1a2e").pack(pady=8)
        ModernButton(popup, "OK", popup.destroy, "#3498db", "#5dade2").pack(pady=10)
        popup.after(2500, popup.destroy)

    # UI helpers --------------------------------------------------
    def enable_moves(self):
        for b in self.move_buttons.values():
            b.config(state="normal")

    def disable_moves(self):
        for b in self.move_buttons.values():
            b.config(state="disabled")

    # Shutdown / errors -------------------------------------------
    def on_disconnect(self):
        self.status_var.set("Disconnected")
        try:
            self.disable_moves()
        except:
            pass

    def quit_game(self):
        try:
            if self.sock:
                send_json(self.sock, {"type": "quit"})
                self.sock.close()
        except:
            pass
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.quit_game)
        self.root.mainloop()

if __name__ == "__main__":
    RpsClientGUI().run()
