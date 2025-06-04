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
    print(f'MCU device {mcu_id} is loading {date} data')
    files = os.listdir(file_path)
    # print(files)
    collected_data = {}
    for file in files:
        if not file.endswith(".json"):
            continue
        try:
            time = file.split('.')[0].split('_')[2]
        except IndexError:
            continue

        async with aiofiles.open(os.path.join(file_path, file), mode='r') as f:
            content = await f.read()
            try:
                json_file = json.loads(content)
            except json.JSONDecodeError as e:
                print(e)
                continue

            if mcu_id in json_file:
                collected_data[time] = json_file[mcu_id]

    from collections import OrderedDict
    def time_key(t):
        h, m, s = map(int, t.split('-'))
        return h * 60 + m

    sorted_data = OrderedDict(sorted(collected_data.items(), key=lambda x: time_key(x[0])))
    json_str = json.dumps(sorted_data, indent=2, ensure_ascii=False)
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as f:
        f.write(json_str.encode("utf-8"))
    buffer.seek(0)
    print(f'MCU device {mcu_id} loading {date} data finished')
    return StreamingResponse(buffer,
                             media_type='application/gzip',
                             headers={"Content-Disposition": f"attachment; filename={mcu_id}_{date}.json.gz"})

app = sio_app
