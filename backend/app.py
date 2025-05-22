import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from TCP_server_text import AsyncTCPServer
import signal
import socketio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

tcp_server = AsyncTCPServer(callback=lambda data: sio.emit('mcu_update', data))

async def background_start():
    await tcp_server.start()

# 啟動背景任務（只執行一次）
asyncio.get_event_loop().create_task(background_start())

def shutdown_handler(sig, frame):
    print("🛑 收到中止訊號，關閉 TCP Server...")
    loop = asyncio.get_event_loop()
    loop.create_task(tcp_server.shutdown())

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

from fastapi import Request

@app.get("/status")
async def get_status():
    return tcp_server.data_frontend

@app.get('/mcu/{mcu_id}')
async def get_mcu_by_id(mcu_id: str):
    addr_str = tcp_server.mcuid_ip.get(mcu_id)
    if not addr_str:
        raise HTTPException(status_code=404, detail="MCU ID not found")
    data = tcp_server.data_frontend.get(addr_str)
    if not data:
        raise HTTPException(status_code=202, detail="MCU is connected but no data yet")
    return data

from pydantic import BaseModel

class AutoscalingRequest(BaseModel):
    addr: str

@app.post("/Autoscaling")
async def start_autoscaling(request: AutoscalingRequest):
    data = request.dict()
    print(f"🛰️ 收到前端送來的資料：{data}")
    addr = data.get('addr')
    await tcp_server.start_autoscaling(addr_str=addr)
    return {"status": "ok"}

app = sio_app
