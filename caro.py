# caro.py - Web-based Caro Game
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
import uuid
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaroGame:
    """Logic game Caro 19x19"""
    def __init__(self):
        self.board = [['' for _ in range(19)] for _ in range(19)]
        self.current_player = 'X'
        self.game_over = False
        self.winner = None
        self.move_history = []
        
    def make_move(self, row: int, col: int) -> bool:
        if 0 <= row < 19 and 0 <= col < 19 and self.board[row][col] == '' and not self.game_over:
            self.board[row][col] = self.current_player
            self.move_history.append((row, col, self.current_player))
            
            if self.check_winner(row, col):
                self.game_over = True
                self.winner = self.current_player
            elif self.is_board_full():
                self.game_over = True
                self.winner = 'Draw'
            else:
                self.current_player = 'O' if self.current_player == 'X' else 'X'
            return True
        return False
    
    def check_winner(self, row: int, col: int) -> bool:
        directions = [(0,1), (1,0), (1,1), (1,-1)]
        player = self.board[row][col]
        
        for dx, dy in directions:
            count = 1
            # Kiểm tra một hướng
            r, c = row + dx, col + dy
            while 0 <= r < 19 and 0 <= c < 19 and self.board[r][c] == player:
                count += 1
                r, c = r + dx, c + dy
            
            # Kiểm tra hướng ngược lại
            r, c = row - dx, col - dy
            while 0 <= r < 19 and 0 <= c < 19 and self.board[r][c] == player:
                count += 1
                r, c = r - dx, c - dy
                
            if count >= 5:
                return True
        return False
    
    def is_board_full(self) -> bool:
        for row in self.board:
            if '' in row:
                return False
        return True
    
    def reset(self):
        self.board = [['' for _ in range(19)] for _ in range(19)]
        self.current_player = 'X'
        self.game_over = False
        self.winner = None
        self.move_history = []

class CaroConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.players: Dict[str, dict] = {}
        self.game = CaroGame()
        self.player_assignments: Dict[str, str] = {}  # client_id -> 'X' or 'O'
        self.spectators: Set[str] = set()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Caro client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.players:
            del self.players[client_id]
        if client_id in self.player_assignments:
            del self.player_assignments[client_id]
        if client_id in self.spectators:
            self.spectators.remove(client_id)
        logger.info(f"Caro client {client_id} disconnected")

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except:
                self.disconnect(client_id)

    async def broadcast(self, message: dict, exclude_client: str = None):
        disconnected_clients = []
        for client_id, connection in self.active_connections.items():
            if client_id != exclude_client:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected_clients.append(client_id)
        
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def assign_player(self, client_id: str, username: str) -> str:
        # Đếm số người chơi hiện tại
        current_players = len(self.player_assignments)
        
        if current_players == 0:
            self.player_assignments[client_id] = 'X'
            self.players[client_id] = {'username': username, 'symbol': 'X'}
            return 'X'
        elif current_players == 1:
            self.player_assignments[client_id] = 'O'
            self.players[client_id] = {'username': username, 'symbol': 'O'}
            return 'O'
        else:
            # Người xem
            self.spectators.add(client_id)
            self.players[client_id] = {'username': username, 'symbol': 'spectator'}
            return 'spectator'

    def get_game_state(self):
        return {
            'board': self.game.board,
            'current_player': self.game.current_player,
            'game_over': self.game.game_over,
            'winner': self.game.winner,
            'move_history': self.game.move_history,
            'players': self.players
        }

# Tạo instance của CaroConnectionManager
caro_manager = CaroConnectionManager()

# Thêm route cho Caro game
def add_caro_routes(app: FastAPI):
    
    @app.get("/caro")
    async def get_caro_page(request: Request):
        """Trả về trang game Caro"""
        host = request.headers.get('host', 'localhost:8000')
        
        html_content = '''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 Caro Online - 19x19</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .container {
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            gap: 20px;
        }
        
        .game-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .game-info {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .board-container {
            position: relative;
            display: inline-block;
            background: #8B4513;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .board {
            display: grid;
            grid-template-columns: repeat(19, 25px);
            grid-template-rows: repeat(19, 25px);
            gap: 1px;
            background: #654321;
            padding: 10px;
            border-radius: 5px;
        }
        
        .cell {
            width: 25px;
            height: 25px;
            background: #DEB887;
            border: 1px solid #8B4513;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        
        .cell:hover {
            background: #F5DEB3;
        }
        
        .cell.x {
            color: #ff4757;
            background: #ffe0e0;
        }
        
        .cell.o {
            color: #2ed573;
            background: #e0ffe0;
        }
        
        .controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: scale(1.05);
        }
        
        .btn-primary {
            background: #3742fa;
            color: white;
        }
        
        .btn-danger {
            background: #ff4757;
            color: white;
        }
        
        .sidebar {
            width: 350px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .login-section {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .login-section h3 {
            margin-bottom: 15px;
            text-align: center;
        }
        
        .input-group {
            margin-bottom: 15px;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        
        .input-group input {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .chat-section {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
            height: 400px;
            display: flex;
            flex-direction: column;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        
        .message {
            margin-bottom: 8px;
            padding: 5px;
            border-radius: 5px;
        }
        
        .message.system {
            background: rgba(255,255,0,0.2);
            font-style: italic;
        }
        
        .message.game {
            background: rgba(0,255,0,0.2);
            font-weight: bold;
        }
        
        .message.chat {
            background: rgba(255,255,255,0.1);
        }
        
        .chat-input {
            display: flex;
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 5px;
        }
        
        .status {
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        
        .status.connected {
            background: rgba(0,255,0,0.2);
        }
        
        .status.disconnected {
            background: rgba(255,0,0,0.2);
        }
        
        .players-list {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .player-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            margin-bottom: 5px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
        }
        
        .player-symbol {
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 3px;
        }
        
        .symbol-x {
            background: #ff4757;
            color: white;
        }
        
        .symbol-o {
            background: #2ed573;
            color: white;
        }
        
        .symbol-spectator {
            background: #747d8c;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="game-area">
            <div class="header">
                <h1>🎮 CARO ONLINE 19x19</h1>
                <div class="status disconnected" id="status">Chưa kết nối</div>
            </div>
            
            <div class="game-info" id="gameInfo">
                <div>Đang chờ người chơi...</div>
            </div>
            
            <div class="board-container">
                <div class="board" id="board"></div>
            </div>
            
            <div class="controls">
                <button class="btn btn-danger" onclick="resetGame()">🔄 Game mới</button>
                <button class="btn btn-primary" onclick="location.href='/'">💬 Chat Room</button>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="login-section" id="loginSection">
                <h3>🎯 Tham gia game</h3>
                <div class="input-group">
                    <label>Tên người chơi:</label>
                    <input type="text" id="usernameInput" placeholder="Nhập tên của bạn..." maxlength="20">
                </div>
                <button class="btn btn-primary" onclick="joinGame()" style="width: 100%;">
                    Tham gia
                </button>
            </div>
            
            <div class="players-list">
                <h3>👥 Người chơi</h3>
                <div id="playersList"></div>
            </div>
            
            <div class="chat-section">
                <h3>💬 Chat</h3>
                <div class="chat-messages" id="chatMessages"></div>
                <div class="chat-input">
                    <input type="text" id="chatInput" placeholder="Nhập tin nhắn..." disabled>
                    <button class="btn btn-primary" onclick="sendChat()">Gửi</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const SERVER_HOST = "''' + host + '''";
        
        class CaroGame {
            constructor() {
                this.ws = null;
                this.username = '';
                this.clientId = this.generateClientId();
                this.playerSymbol = null;
                this.isConnected = false;
                this.gameState = null;
                
                this.initElements();
                this.createBoard();
                this.bindEvents();
                this.connect();
            }
            
            generateClientId() {
                return 'caro_' + Math.random().toString(36).substr(2, 9);
            }
            
            initElements() {
                this.statusEl = document.getElementById('status');
                this.gameInfoEl = document.getElementById('gameInfo');
                this.boardEl = document.getElementById('board');
                this.usernameInput = document.getElementById('usernameInput');
                this.loginSection = document.getElementById('loginSection');
                this.playersListEl = document.getElementById('playersList');
                this.chatMessages = document.getElementById('chatMessages');
                this.chatInput = document.getElementById('chatInput');
            }
            
            createBoard() {
                this.boardEl.innerHTML = '';
                for (let row = 0; row < 19; row++) {
                    for (let col = 0; col < 19; col++) {
                        const cell = document.createElement('div');
                        cell.className = 'cell';
                        cell.dataset.row = row;
                        cell.dataset.col = col;
                        cell.onclick = () => this.makeMove(row, col);
                        this.boardEl.appendChild(cell);
                    }
                }
            }
            
            bindEvents() {
                this.usernameInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.joinGame();
                    }
                });
                
                this.chatInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.sendChat();
                    }
                });
            }
            
            connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = protocol + '//' + SERVER_HOST + '/ws/caro/' + this.clientId;
                
                try {
                    this.ws = new WebSocket(wsUrl);
                    
                    this.ws.onopen = () => {
                        this.isConnected = true;
                        this.updateStatus('Đã kết nối - Nhập tên để tham gia', true);
                    };
                    
                    this.ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    };
                    
                    this.ws.onclose = () => {
                        this.isConnected = false;
                        this.updateStatus('Mất kết nối - Đang kết nối lại...', false);
                        setTimeout(() => this.connect(), 3000);
                    };
                    
                    this.ws.onerror = (error) => {
                        console.error('WebSocket error:', error);
                        this.updateStatus('Lỗi kết nối', false);
                    };
                } catch (error) {
                    console.error('Error creating WebSocket:', error);
                }
            }
            
            joinGame() {
                this.username = this.usernameInput.value.trim();
                if (!this.username || !this.isConnected) {
                    alert('Vui lòng nhập tên và đảm bảo đã kết nối!');
                    return;
                }
                
                this.sendMessage({
                    type: 'join',
                    username: this.username
                });
                
                this.loginSection.style.display = 'none';
                this.chatInput.disabled = false;
            }
            
            makeMove(row, col) {
                if (!this.gameState || this.gameState.game_over || 
                    this.gameState.current_player !== this.playerSymbol ||
                    this.playerSymbol === 'spectator') {
                    return;
                }
                
                this.sendMessage({
                    type: 'move',
                    row: row,
                    col: col
                });
            }
            
            sendChat() {
                const message = this.chatInput.value.trim();
                if (!message) return;
                
                this.sendMessage({
                    type: 'chat',
                    message: message
                });
                
                this.chatInput.value = '';
            }
            
            sendMessage(data) {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify(data));
                }
            }
            
            handleMessage(data) {
                switch(data.type) {
                    case 'player_assigned':
                        this.playerSymbol = data.symbol;
                        this.updateGameInfo(data.message);
                        this.addChatMessage('system', data.message);
                        break;
                        
                    case 'game_state':
                        this.gameState = data.state;
                        this.updateBoard();
                        this.updatePlayersList();
                        this.updateGameStatus();
                        break;
                        
                    case 'move_made':
                        this.gameState = data.state;
                        this.updateBoard();
                        this.updateGameStatus();
                        this.addChatMessage('game', data.message);
                        break;
                        
                    case 'game_reset':
                        this.gameState = data.state;
                        this.updateBoard();
                        this.updateGameStatus();
                        this.addChatMessage('system', 'Game đã được reset!');
                        break;
                        
                    case 'chat_message':
                        this.addChatMessage('chat', data.username + ': ' + data.message);
                        break;
                        
                    case 'player_left':
                        this.addChatMessage('system', data.message);
                        break;
                }
            }
            
            updateBoard() {
                if (!this.gameState) return;
                
                const cells = this.boardEl.querySelectorAll('.cell');
                cells.forEach(cell => {
                    const row = parseInt(cell.dataset.row);
                    const col = parseInt(cell.dataset.col);
                    const value = this.gameState.board[row][col];
                    
                    cell.textContent = value || '';
                    cell.className = 'cell' + (value ? ' ' + value.toLowerCase() : '');
                });
            }
            
            updatePlayersList() {
                if (!this.gameState) return;
                
                this.playersListEl.innerHTML = '';
                Object.values(this.gameState.players).forEach(player => {
                    const playerEl = document.createElement('div');
                    playerEl.className = 'player-item';
                    playerEl.innerHTML = 
                        '<span>' + player.username + '</span>' +
                        '<span class="player-symbol symbol-' + player.symbol + '">' + 
                        (player.symbol === 'spectator' ? 'Khán giả' : player.symbol) + 
                        '</span>';
                    this.playersListEl.appendChild(playerEl);
                });
            }
            
            updateGameStatus() {
                if (!this.gameState) return;
                
                if (this.gameState.game_over) {
                    if (this.gameState.winner === 'Draw') {
                        this.updateGameInfo('🤝 Hòa!');
                    } else if (this.gameState.winner === this.playerSymbol) {
                        this.updateGameInfo('🎉 Bạn thắng!');
                    } else {
                        this.updateGameInfo('😢 Bạn thua!');
                    }
                } else {
                    if (this.gameState.current_player === this.playerSymbol) {
                        this.updateGameInfo('🎯 Lượt của bạn!');
                    } else {
                        this.updateGameInfo('⏳ Đợi đối thủ...');
                    }
                }
            }
            
            updateStatus(message, connected) {
                this.statusEl.textContent = message;
                this.statusEl.className = 'status ' + (connected ? 'connected' : 'disconnected');
            }
            
            updateGameInfo(message) {
                this.gameInfoEl.innerHTML = '<div>' + message + '</div>';
            }
            
            addChatMessage(type, message) {
                const messageEl = document.createElement('div');
                messageEl.className = 'message ' + type;
                messageEl.textContent = message;
                this.chatMessages.appendChild(messageEl);
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
        }
        
        // Global functions
        function resetGame() {
            if (game.ws && game.ws.readyState === WebSocket.OPEN) {
                game.sendMessage({ type: 'reset' });
            }
        }
        
        function joinGame() {
            game.joinGame();
        }
        
        function sendChat() {
            game.sendChat();
        }
        
        // Initialize game
        let game;
        document.addEventListener('DOMContentLoaded', () => {
            game = new CaroGame();
        });
    </script>
</body>
</html>'''
        return HTMLResponse(content=html_content)

    @app.websocket("/ws/caro/{client_id}")
    async def caro_websocket_endpoint(websocket: WebSocket, client_id: str):
        await caro_manager.connect(websocket, client_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError:
                    continue
                
                message_type = message_data.get('type')
                
                if message_type == 'join':
                    username = message_data.get('username', 'Player')
                    symbol = caro_manager.assign_player(client_id, username)
                    
                    await caro_manager.send_personal_message({
                        'type': 'player_assigned',
                        'symbol': symbol,
                        'message': f'Bạn là {symbol}!' if symbol != 'spectator' else 'Bạn đang xem game!'
                    }, client_id)
                    
                    # Gửi trạng thái game hiện tại
                    await caro_manager.send_personal_message({
                        'type': 'game_state',
                        'state': caro_manager.get_game_state()
                    }, client_id)
                    
                    # Thông báo cho tất cả
                    await caro_manager.broadcast({
                        'type': 'game_state',
                        'state': caro_manager.get_game_state()
                    })
                    
                elif message_type == 'move':
                    if client_id in caro_manager.player_assignments:
                        player_symbol = caro_manager.player_assignments[client_id]
                        if (player_symbol == caro_manager.game.current_player and 
                            not caro_manager.game.game_over):
                            
                            row = message_data.get('row')
                            col = message_data.get('col')
                            
                            if caro_manager.game.make_move(row, col):
                                username = caro_manager.players[client_id]['username']
                                move_msg = f'{username} ({player_symbol}) đánh tại ({row+1}, {col+1})'
                                
                                if caro_manager.game.game_over:
                                    if caro_manager.game.winner == 'Draw':
                                        move_msg += ' - Hòa!'
                                    else:
                                        move_msg += f' - {username} thắng!'
                                
                                await caro_manager.broadcast({
                                    'type': 'move_made',
                                    'state': caro_manager.get_game_state(),
                                    'message': move_msg
                                })
                
                elif message_type == 'reset':
                    caro_manager.game.reset()
                    await caro_manager.broadcast({
                        'type': 'game_reset',
                        'state': caro_manager.get_game_state()
                    })
                    
                elif message_type == 'chat':
                    if client_id in caro_manager.players:
                        username = caro_manager.players[client_id]['username']
                        chat_message = message_data.get('message', '')
                        
                        await caro_manager.broadcast({
                            'type': 'chat_message',
                            'username': username,
                            'message': chat_message
                        })
                        
        except WebSocketDisconnect:
            username = caro_manager.players.get(client_id, {}).get('username', 'Unknown')
            caro_manager.disconnect(client_id)
            
            await caro_manager.broadcast({
                'type': 'player_left',
                'message': f'{username} đã rời game'
            })
            
            # Reset game nếu một trong hai người chơi chính rời đi
            if len(caro_manager.player_assignments) < 2:
                caro_manager.game.reset()
                await caro_manager.broadcast({
                    'type': 'game_reset',
                    'state': caro_manager.get_game_state()
                })
                
        except Exception as e:
            logger.error(f"Error in caro websocket {client_id}: {e}")
            caro_manager.disconnect(client_id)

# Export function để thêm vào main app
def setup_caro_game(app: FastAPI):
    add_caro_routes(app)