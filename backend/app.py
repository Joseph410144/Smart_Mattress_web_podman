import os
import asyncio
import signal
import socketio
import aiofiles
import io
import gzip
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from TCP_server_text import AsyncTCPServer

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

tcp_server = AsyncTCPServer(callback=lambda data: asyncio.create_task(sio.emit('mcu_update', data)))

async def background_start():
    await tcp_server.start()

# 啟動背景任務（只執行一次）
asyncio.get_event_loop().create_task(background_start())


# 新增 FastAPI 的 shutdown 事件處理器
@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 收到中止事件，關閉 TCP Server...")
    await tcp_server.shutdown()

from fastapi import Request

@app.get("/status")
async def get_status():
    return tcp_server.data_frontend

@app.get("/mcu_real_time_data/{mcu_id}")
async def get_mcu_real_time_data(mcu_id: str):
    data = tcp_server.mcu_id_realTime_data.get(mcu_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"MCU {mcu_id} not found")
    return data

@app.get('/mcu/{mcu_id}')
async def get_mcu_by_id(mcu_id: str):
    addr_str = tcp_server.mcuid_ip.get(mcu_id)
    if not addr_str:
        await sio.emit("mcu_disconnect", {"id": mcu_id})
        return {"status": "disconnected", "id": mcu_id}

    data = tcp_server.data_frontend.get(addr_str)
    if not data:
        return {"status": "waiting", "id": mcu_id}

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
