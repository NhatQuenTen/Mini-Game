from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

# Import Caro game
from caro import setup_caro_game

app = FastAPI(title="Chat Real-time với SignalR", version="1.0.0")

# Setup Caro game routes
setup_caro_game(app)

@app.get("/")
async def get_chat_page(request: Request):
    """Trả về trang chat HTML"""
    host = request.headers.get("host")
    
    html_content = '''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Real-time với Python SignalR</title>
    <style>
        /* ...existing styles... */
        
        .game-nav {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 11px;
        }
        
        .game-nav a {
            color: white;
            text-decoration: none;
            margin: 0 5px;
        }
        
        .game-nav a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            🚀 Python SignalR Chat
            <div class="server-info">Server: ''' + host + '''</div>
            <div class="game-nav">
                <a href="/caro">🎮 Caro Game</a>
            </div>
            <div class="user-count" id="userCount">0 người online</div>
        </div>
        
        <!-- ...existing chat content... -->
    </div>

    <!-- ...existing JavaScript... -->
</body>
</html>'''
    return HTMLResponse(content=html_content)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("caroo:app", host="0.0.0.0", port=8000, reload=True)
