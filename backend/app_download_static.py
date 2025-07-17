import os
import asyncio
import requests
import socketio
import aiofiles
import io
import gzip
import json
import base64
import matplotlib.pyplot as plt
import numpy as np

from requests.exceptions import RequestException
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

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

@app.get("/analysis/{mcu_id}")
async def analysis_mcu_data(mcu_id: str, date: str):
    file_path = f"/app/snapshots/{date}"  # 或根據你實際命名方式調整
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="指定日期資料不存在")
    print(f'MCU device {mcu_id} is processing {date} data')
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
    timestamps_count, timestamps_status, hearts, resps, status = [], [], [], [], []

    for time, record in sorted_data.items():
        timestamps_count.append(time)
        heart_min = np.array(record['heart_rate'])
        resp_min = np.array(record['resp_rate'])
        # hearts.append(np.mean(heart_min[heart_min>0]))
        # resps.append(np.mean(resp_min[resp_min>0]))
        mov_min = record['movement']
        oob_min = record['outofbed']
        time_min = record['timestamp']
        for i in range(len(mov_min)):
            if oob_min[i] == 1:
                status.append(-1)
            elif mov_min[i] == 1:
                status.append(1)
            else:
                status.append(0)
            time = time_min[i].split(' ')[1]
            timestamps_status.append(time)
            hearts.append(heart_min[i])
            resps.append(resp_min[i])
    if len(hearts) < 48:
        interval_status = len(hearts)
    else:
        interval_status = len(hearts)//24
    labels = [str(timestamps_status[i]) if i%interval_status==0 else '' for i in range(len(timestamps_status))]
    # heart data
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.plot(timestamps_status, hearts)
    ax.set_title(f'MCU device {mcu_id} {date} heartrate', fontsize=6)
    ax.set_ylabel('heartrate')
    ax.yaxis.label.set_fontsize(6)
    ax.set_xlabel('time')
    ax.xaxis.label.set_fontsize(6)
    ax.set_xticks(ticks=range(len(timestamps_status)))
    ax.set_xticklabels(labels, rotation=30)
    ax.tick_params(axis='x', labelsize=6)
    ax.tick_params(axis='y', labelsize=6)
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    heart_img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # resp data
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.plot(timestamps_status, resps)
    ax.set_title(f'MCU device {mcu_id} {date} resprate', fontsize=6)
    ax.set_ylabel('resprate')
    ax.yaxis.label.set_fontsize(6)
    ax.set_xlabel('time')
    ax.xaxis.label.set_fontsize(6)
    ax.set_xticks(ticks=range(len(timestamps_status)))
    ax.set_xticklabels(labels, rotation=30)
    ax.tick_params(axis='x', labelsize=6)
    ax.tick_params(axis='y', labelsize=6)
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    resp_img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    interval_status = len(status)//24
    labels = [str(timestamps_status[i]) if i%interval_status==0 else '' for i in range(len(timestamps_status))]
    # status
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.plot(timestamps_status, status)
    ax.set_ylabel('status')
    ax.yaxis.label.set_fontsize(6)
    ax.set_xlabel('time')
    ax.xaxis.label.set_fontsize(6)
    ax.set_yticks(ticks=[-1, 0, 1])
    ax.set_ylim(-2, 2)
    ax.set_yticklabels(['out of bed', 'measuring', 'movement'])
    ax.tick_params(axis='y', labelsize=6)
    ax.set_xticks(ticks=range(len(timestamps_status)))
    ax.set_xticklabels(labels, rotation=30)
    ax.tick_params(axis='x', labelsize=6)
    ax.set_title(f'MCU device {mcu_id} {date} status', fontsize=6)
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    status_img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    
    print(f'MCU device {mcu_id} processing {date} data finished')

    return {"heart_image": heart_img_base64, 'resp_image': resp_img_base64, 'status_image': status_img_base64}

@app.get("/realtime/{mcu_id}")
async def real_time_figure_mcu_data(mcu_id: str):
    try:
        response = requests.get(f"http://172.20.10.3:8000/mcu_real_time_data/{mcu_id}")
        if response.status_code == 200:
            data = response.json()
            # 取得資料
            heart = data.get("heart_rate", [])
            resp = data.get("resp_rate", [])
            rate_ts = data.get("rate_timestamp", [])
            status = data.get("status", [])
            status_ts = data.get("status_timestamp", [])

            # 限制 x 軸 ticks 數量最多 10 個
            def reduce_ticks(xlist):
                if len(xlist) <= 10:
                    return list(range(len(xlist))), xlist
                step = len(xlist) // 10
                indices = list(range(0, len(xlist), step))
                labels = [xlist[i] for i in indices]
                return indices, labels

            # heart rate
            fig, ax = plt.subplots(figsize=(10, 3), dpi=300)
            fig.patch.set_alpha(0)  # 設定整個 figure 背景為透明
            ax.set_facecolor('none')  
            ax.plot(rate_ts, heart)
            ax.set_ylabel("Heart Rate")
            idx, lbl = reduce_ticks(rate_ts)
            ax.set_xticks(idx)
            ax.set_xticklabels(lbl, rotation=30, fontsize=6)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)  # 啟用透明背景
            # fig.savefig(buf, format="png")
            plt.close(fig)
            buf.seek(0)
            heart_img_base64 = base64.b64encode(buf.read()).decode("utf-8")

            # resp rate
            fig, ax = plt.subplots(figsize=(10, 3), dpi=300)
            fig.patch.set_alpha(0)  # 設定整個 figure 背景為透明
            ax.set_facecolor('none')  
            ax.plot(rate_ts, resp)
            ax.set_ylabel("Resp Rate")
            idx, lbl = reduce_ticks(rate_ts)
            ax.set_xticks(idx)
            ax.set_xticklabels(lbl, rotation=30, fontsize=6)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig)
            buf.seek(0)
            resp_img_base64 = base64.b64encode(buf.read()).decode("utf-8")

            # status 彩色區塊圖（無折線）
            fig, ax = plt.subplots(figsize=(10, 3), dpi=300)
            fig.patch.set_alpha(0)  # 設定整個 figure 背景為透明
            ax.set_facecolor('none')  
            # 狀態與顏色對應
            colors = {1: 'orange', 0: 'blue', -1: 'red'}
            labels = {1: 'Movement', 0: 'Measuring', -1: 'Out of Bed'}
            used = set()

            # 畫每一格顏色區段
            for i in range(len(status)):
                color = colors.get(status[i], 'gray')
                label = labels[status[i]] if status[i] not in used else None
                ax.axvspan(i - 0.5, i + 0.5, color=color, alpha=0.5, label=label)
                used.add(status[i])

            # y 軸與 x 軸設定
            ax.set_yticks([])
            ax.set_ylabel("Status")
            idx, lbl = reduce_ticks(status_ts)
            ax.set_xticks(idx)
            ax.set_xticklabels(lbl, rotation=30, fontsize=6)

            # 加入圖例
            ax.legend(loc="upper right", fontsize=6)

            # 儲存圖片
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig)
            buf.seek(0)
            status_img_base64 = base64.b64encode(buf.read()).decode("utf-8")

            return {
                "heart_image": heart_img_base64,
                "resp_image": resp_img_base64,
                "status_image": status_img_base64
            }
        else:
            return {"heart_image": None,
                "resp_image": None,
                "status_image": None, "error": f"MCU {mcu_id} 回應錯誤: {response.status_code}"}
    except RequestException as e:
        return {"heart_image": None,
                "resp_image": None,
                "status_image": None, "error": f"MCU {mcu_id} 無法連線: {str(e)}"}

@app.get("/historyplot/{mcu_id}")
async def history_plot_mcu_data(mcu_id: str, startdate: str=Query(...), enddate: str=Query(...)):
    file_path = '/app/snapshots'
    from datetime import datetime, timedelta
    from datetime import datetime as dt, timedelta
    # 解析帶有時分的起訖時間
    start_dt = dt.strptime(startdate, "%Y-%m-%d %H-%M")
    end_dt = dt.strptime(enddate, "%Y-%m-%d %H-%M")
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    # Collect all data from start_date to end_date

    def daterange(start_date_obj, end_date_obj):
        for n in range(int((end_date_obj - start_date_obj).days) + 1):
            yield start_date_obj + timedelta(n)

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    heart_all = []
    resp_all = []
    time_all = []
    status_all = []
    status_time_all = []

    from collections import defaultdict
    minute_data_map = defaultdict(list)  # key: HH:MM, value: list of (heart, resp)

    for single_date in daterange(start_date_obj, end_date_obj):
        date_str = single_date.strftime("%Y-%m-%d")
        date_path = os.path.join(file_path, date_str)
        if not os.path.exists(date_path):
            continue
        files = os.listdir(date_path)
        collected_data = {}
        for file in files:
            if not file.endswith(".json"):
                continue
            try:
                time = file.split('.')[0].split('_')[2]
            except IndexError:
                continue

            async with aiofiles.open(os.path.join(date_path, file), mode='r') as f:
                content = await f.read()
                try:
                    json_file = json.loads(content)
                except json.JSONDecodeError:
                    continue

                if mcu_id in json_file:
                    collected_data[time] = json_file[mcu_id]

        from collections import OrderedDict
        def time_key(t):
            h, m, s = map(int, t.split('-'))
            return h * 60 + m

        sorted_data = OrderedDict(sorted(collected_data.items(), key=lambda x: time_key(x[0])))

        for time, record in sorted_data.items():
            time_min = record['timestamp']
            heart_min = record['heart_rate']
            resp_min = record['resp_rate']
            mov_min = record['movement']
            oob_min = record['outofbed']
            for i in range(len(time_min)):
                full_time_str = time_min[i]
                try:
                    current_dt = dt.strptime(full_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue  # skip malformed timestamp

                if not (start_dt <= current_dt <= end_dt):
                    continue

                minute_str = current_dt.strftime("%H:%M")
                minute_data_map[minute_str].append((heart_min[i], resp_min[i]))

                if oob_min[i] == 1:
                    status_all.append(-1)
                elif mov_min[i] == 1:
                    status_all.append(1)
                else:
                    status_all.append(0)
                status_time_all.append(current_dt.strftime("%H:%M:%S"))

    # 根據每分鐘聚合平均
    heart_all = []
    resp_all = []
    time_all = []

    for minute in sorted(minute_data_map.keys()):
        values = minute_data_map[minute]
        heart_values = [v[0] for v in values if v[0] > 0]
        resp_values = [v[1] for v in values if v[1] > 0]
        heart_avg = np.mean(heart_values) if heart_values else 0
        resp_avg = np.mean(resp_values) if resp_values else 0
        time_all.append(minute)
        heart_all.append(heart_avg)
        resp_all.append(resp_avg)

    # 繪製心跳圖
    fig, ax = plt.subplots(figsize=(10, 3), dpi=300)
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    ax.plot(time_all, heart_all)
    ax.set_ylabel("Heart Rate")
    idx = list(range(0, len(time_all), max(1, len(time_all)//10)))
    ax.set_xticks(idx)
    ax.set_xticklabels([time_all[i] for i in idx], rotation=30, fontsize=6)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    heart_img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    # 繪製呼吸圖
    fig, ax = plt.subplots(figsize=(10, 3), dpi=300)
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    ax.plot(time_all, resp_all)
    ax.set_ylabel("Resp Rate")
    idx = list(range(0, len(time_all), max(1, len(time_all)//10)))
    ax.set_xticks(idx)
    ax.set_xticklabels([time_all[i] for i in idx], rotation=30, fontsize=6)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    resp_img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    # 繪製 status 圖（色條）
    fig, ax = plt.subplots(figsize=(10, 3), dpi=300)
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    colors = {1: 'orange', 0: 'blue', -1: 'red'}
    labels_map = {1: 'Movement', 0: 'Measuring', -1: 'Out of Bed'}
    used = set()
    for i in range(len(status_all)):
        color = colors.get(status_all[i], 'gray')
        label = labels_map[status_all[i]] if status_all[i] not in used else None
        ax.axvspan(i - 0.5, i + 0.5, color=color, alpha=0.5, label=label)
        used.add(status_all[i])
    ax.set_yticks([])
    ax.set_ylabel("Status")
    idx = list(range(0, len(status_time_all), max(1, len(status_time_all)//10)))
    ax.set_xticks(idx)
    ax.set_xticklabels([status_time_all[i] for i in idx], rotation=30, fontsize=6)
    ax.legend(loc="upper right", fontsize=6)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    status_img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "heart_image": heart_img_base64,
        "resp_image": resp_img_base64,
        "status_image": status_img_base64
    }

app = sio_app