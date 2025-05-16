from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import asyncio

import socket

app = FastAPI()

# Serve static files (JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve HTML templates
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Open TCP connection to the load balancer
    reader, writer = await asyncio.open_connection('localhost', 1234)

    # Send initial handshake
    writer.write(b"CLIENT|ADD")
    await writer.drain()

    async def tcp_to_ws():
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                await websocket.send_text(data.decode())
        except Exception:
            pass
        finally:
            await websocket.close()

    async def ws_to_tcp():
        try:
            while True:
                data = await websocket.receive_text()
                writer.write(data.encode())
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    await asyncio.gather(tcp_to_ws(), ws_to_tcp())
