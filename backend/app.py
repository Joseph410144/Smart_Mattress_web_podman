import os
import asyncio
import signal
import socketio
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import io
import json
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

@app.get("/download/{mcu_id}")
async def download_snapshot(mcu_id: str, date: str):
    file_path = f"/app/snapshots/{date}"  # 或根據你實際命名方式調整
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="指定日期資料不存在")
    
    files = os.listdir(file_path)
    collected_data = {}
    for file in files:
        time = file.split('.')[0].split('_')[2]
        json_file = pd.read_json(os.path.join(file_path, file))
        if mcu_id in json_file.keys():
            mcu_id_data = json_file[mcu_id]
            collected_data[time] = mcu_id_data.to_dict()

    from collections import OrderedDict
    def time_key(t):
        h, m, t = map(int, t.split('-'))
        return h * 60 + m

    sorted_data = OrderedDict(sorted(collected_data.items(), key=lambda x: time_key(x[0])))
    json_str = json.dumps(sorted_data, indent=2, ensure_ascii=False)
    return StreamingResponse(io.BytesIO(json_str.encode('utf-8')),
                             media_type='application/json',
                             headers={"Content-Disposition": f"attachment; filename={mcu_id}_{date}.json"})

app = sio_app
