import os
import json
import time
import struct
import socket
import threading
import traceback
import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta

class AsyncTCPServer:
    def __init__(self, callback, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port
        self.callback = callback
        self.clients = {}  # addr_str -> (reader, writer)
        self.data_storage = {}  # mcu_id -> data dict
        self.data_frontend = {}  # addr_str -> display dict
        self.mcuid_ip = {}  # mcu_id -> addr_str
        self.mcu_id_realTime_data = {} # mcu_id -> real time data(mininute)
        self.raw_per_minute = 60 * 100
        self.value_per_minute = 120
        self.snapshot_dir = "/app/snapshots"
        self.taiwan_tz = timezone(timedelta(hours=8))
        self.data_array = self._create_data_array()
        self.check_array = self._create_check_array()
        self.running = False
        self.mcu_cpu_log = {}  # 新增 CPU 統計資料儲存
        # self.mcu_cpu_fig = {}

    def _create_check_array(self):
        arr = bytearray(513)
        arr[0:9] = bytes([0x13, 0x00, 0x01, 0x00, 0x09, 0x00, 0x01, 0x00, 0x1E])
        return arr

    def _create_data_array(self):
        arr = bytearray(513)
        arr[0:7] = bytes([0x13, 0x00, 0x28, 0x00, 0x15])
        arr[17], arr[18] = 0x00, 0x01
        # checksum = self._calculate_checksum(sum(arr[:7]))
        # arr[7], arr[8] = checksum
        return arr

    def _calculate_checksum(self, total_sum):
        total_sum &= 0xFFFF
        return (total_sum >> 8) & 0xFF, total_sum & 0xFF

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        addr_str = f"{addr[0]}:{addr[1]}"
        print(f"✅ New client: {addr_str}")
        self.clients[addr_str] = (reader, writer)

        try:
            writer.write(self.check_array)
            await writer.drain()
            data = await reader.read(1400)
            if not (len(data) >= 13 and data[5] == 0x03):
                print(f"❌ Verification failed for {addr_str}")
                writer.close()
                await writer.wait_closed()
                return
            # 取得目前時間，格式化為字串
            now = datetime.now()
            time_str = now.strftime("%Y%m%d%H%M")  # 例如 202507171132，共12碼
            # 轉成 ASCII bytes（每個字元一個 byte）
            time_bytes = time_str.encode("ascii")  # b'202507171132'
            # 放到 arr 的 index 5 開始
            self.data_array[5:5+12] = time_bytes
            checksum = self._calculate_checksum(sum(self.data_array[:19]))
            self.data_array[19], self.data_array[20] = checksum
            """ update MCU ID """
            writer.write(self.data_array)
            await writer.drain()
            data = await reader.read(1400)
            mcu_id = data[432:448].decode('ascii').rstrip('\x00')
            self.mcuid_ip[mcu_id] = addr_str
            self.data_frontend[addr_str] = {
                "heart_rate": 0, "resp_rate": 0, "movement": 0,
                "outofbed": 0, "autoscaling": 0, "timestamp": '', "RSSI":0, "name": mcu_id, "addr": addr_str, "status":'connect'
            }
            self.data_storage[mcu_id] = {
                "raw": [], "heart_rate": [], "resp_rate": [],
                "movement": [], "outofbed": [], "timestamp": [], "RSSI":[]
            }
            self.mcu_id_realTime_data[mcu_id] = {'heart_rate':[], 'resp_rate':[], 'rate_timestamp':[]
                                                 , 'status':[], 'status_timestamp':[]}

            print(f'start getting data on {addr_str}, id name: {mcu_id}')
            lastAdccurrent = 0

            while True:
                cpu_start = time.process_time()
                wall_start = time.time()
                """ add timestamp in data array """
                # 取得目前時間，格式化為字串
                now = datetime.now()
                time_str = now.strftime("%Y%m%d%H%M")  # 例如 202507171132，共12碼
                # 轉成 ASCII bytes（每個字元一個 byte）
                time_bytes = time_str.encode("ascii")  # b'202507171132'
                # 放到 arr 的 index 5 開始
                self.data_array[5:5+12] = time_bytes
                checksum = self._calculate_checksum(sum(self.data_array[:19]))
                self.data_array[19], self.data_array[20] = checksum
                # data cmd
                writer.write(self.data_array)
                await writer.drain()
                # await asyncio.sleep(0.1)
                try:
                    MCUresponseData = await asyncio.wait_for(reader.read(1400), timeout=10.0)
                except asyncio.TimeoutError:
                    raise ConnectionError("Timeout: No data received from MCU")

                if not MCUresponseData:
                    raise ConnectionError("MCU disconnected")

                if MCUresponseData[5] != 3:
                    continue

                raw, heart = [], []
                rawI, heartI = 32, 232

                CurrentAdccurrent = (MCUresponseData[6]) << 8 | MCUresponseData[7]
                HeartMCU = int(MCUresponseData[12])
                RespMCU = int(MCUresponseData[13])
                OobMCU = int(MCUresponseData[14])
                rssiMCU = int.from_bytes(MCUresponseData[27:28], byteorder='big', signed=True)
                if OobMCU == 79:
                    OobMCU = 1
                    BdmmtMCU = 0
                else:
                    OobMCU = 0
                    BdmmtMCU = MCUresponseData[15]
                AutoScaling = int(MCUresponseData[24])

                if CurrentAdccurrent > lastAdccurrent:
                    for i in range(lastAdccurrent, CurrentAdccurrent):
                        raw.append((MCUresponseData[(rawI+i*2)])<<8 | MCUresponseData[(rawI+i*2)+1])
                        heart.append((MCUresponseData[(heartI+i*2)])<<8 | MCUresponseData[(heartI+i*2)+1])
                else:
                    for i in range(lastAdccurrent, 100):
                        raw.append((MCUresponseData[(rawI+i*2)])<<8 | MCUresponseData[(rawI+i*2)+1])
                        heart.append((MCUresponseData[(heartI+i*2)])<<8 | MCUresponseData[(heartI+i*2)+1])
                    for i in range(CurrentAdccurrent):
                        raw.append((MCUresponseData[(rawI+i*2)])<<8 | MCUresponseData[(rawI+i*2)+1])
                        heart.append((MCUresponseData[(heartI+i*2)])<<8 | MCUresponseData[(heartI+i*2)+1])
                lastAdccurrent = CurrentAdccurrent
                # print(f'MCU device: {mcu_id}, raw length: {len(raw)}')
                timestamp = datetime.now(self.taiwan_tz).strftime("%Y-%m-%d %H:%M:%S")

                if rssiMCU<=-30 and rssiMCU>=-50:
                    rssi_frontend = 0
                elif rssiMCU<=-51 and rssiMCU>=-65:
                    rssi_frontend = 1
                elif rssiMCU<=-66 and rssiMCU>=-75:
                    rssi_frontend = 2
                elif rssiMCU<=-76 and rssiMCU>-85:
                    rssi_frontend = 3
                elif rssiMCU<=-85:
                    rssi_frontend = 4
                else:
                    rssi_frontend = -1

                self.data_frontend[addr_str].update({
                    "heart_rate": HeartMCU, "resp_rate": RespMCU,
                    "movement": BdmmtMCU, "outofbed": OobMCU,
                    "autoscaling": AutoScaling, "timestamp": timestamp, "RSSI": rssi_frontend
                })

                self.data_storage[mcu_id]["raw"] += raw
                self.data_storage[mcu_id]["heart_rate"].append(HeartMCU)
                self.data_storage[mcu_id]["resp_rate"].append(RespMCU)
                self.data_storage[mcu_id]["movement"].append(BdmmtMCU)
                self.data_storage[mcu_id]["outofbed"].append(OobMCU)
                self.data_storage[mcu_id]["timestamp"].append(timestamp)
                self.data_storage[mcu_id]["RSSI"].append(rssiMCU)

                """ append real time figure data """
                if OobMCU == 1:
                    self.mcu_id_realTime_data[mcu_id]['status'].append(-1)
                elif BdmmtMCU == 1:
                    self.mcu_id_realTime_data[mcu_id]['status'].append(1)
                else:
                    self.mcu_id_realTime_data[mcu_id]['status'].append(0)
                    
                self.mcu_id_realTime_data[mcu_id]['status_timestamp'].append(timestamp)
                if len(self.mcu_id_realTime_data[mcu_id]['status']) >= 4*60*100:
                    self.mcu_id_realTime_data[mcu_id]['status'].pop(0)
                    self.mcu_id_realTime_data[mcu_id]['status_timestamp'].pop(0)
                
                # ensure callback is awaitable
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(self.data_frontend)
                else:
                    self.callback(self.data_frontend)

                cpu_used = time.process_time() - cpu_start
                wall_elapsed = time.time() - wall_start
                self.mcu_cpu_log.setdefault(mcu_id, []).append((cpu_used, wall_elapsed))
                """ draw cpu using percentage 
                # if mcu_id not in self.mcu_cpu_fig.keys():
                #     self.mcu_cpu_fig[mcu_id] = {}
                #     self.mcu_cpu_fig[mcu_id]['cpu_per'] = []
                #     self.mcu_cpu_fig[mcu_id]['time'] = []

                # if len(self.mcu_cpu_fig[mcu_id]['cpu_per']) == 20:
                #     import matplotlib.pyplot as plt
                #     plt.plot(self.mcu_cpu_fig[mcu_id]['time'], self.mcu_cpu_fig[mcu_id]['cpu_per'])
                #     plt.title(f'{mcu_id} cpu using')
                #     plt.xlabel('time')
                #     plt.ylabel('CPU usage')
                #     plt.xticks(fontsize=8, rotation=45)
                #     plt.savefig(f'/app/snapshots/{mcu_id}_cpu.png')
                """
                
                if len(self.mcu_cpu_log[mcu_id]) >= 20:
                    avg_cpu = sum(c for c, _ in self.mcu_cpu_log[mcu_id]) / 20
                    avg_wall = sum(w for _, w in self.mcu_cpu_log[mcu_id]) / 20
                    percent = avg_cpu / avg_wall * 100 if avg_wall > 0 else 0
                    print(f"📊 [{mcu_id}] 平均 CPU 使用率：{percent:.2f}%")
                    # self.mcu_cpu_fig[mcu_id]['cpu_per'].append(percent)
                    # self.mcu_cpu_fig[mcu_id]['time'].append(str(timestamp).split(' ')[1])
                    self.mcu_cpu_log[mcu_id].clear()

                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Client {addr_str} error: {e}")
            traceback.print_exc()
        finally:
            writer.close()
            await writer.wait_closed()
            # callback disconnected before clearing data
            # self.data_frontend[addr_str]['status'] = "disconnected"
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback({addr_str: {"status": "disconnected"}})
            else:
                self.callback({addr_str: {"status": "disconnected"}})
            mcu_id = self.data_frontend[addr_str]['name']
            self.clients.pop(addr_str, None)
            self.data_storage.pop(mcu_id, None)
            self.data_frontend.pop(addr_str, None)
            self.mcuid_ip.pop(mcu_id, None)
            self.mcu_cpu_log.pop(mcu_id, None)
            print(f"🧹 Connection closed: {addr_str}")

    async def _prune_and_store(self):
        while self.running:
            now = datetime.now(self.taiwan_tz)
            if now.second == 0:
                snapshot_time = now.strftime("%Y-%m-%d_%H-%M-%S")
                today_str = now.strftime("%Y-%m-%d")
                dated_dir = os.path.join(self.snapshot_dir, today_str)
                os.makedirs(dated_dir, exist_ok=True)
                snapshot = {}
                for id, data in self.data_storage.items():
                    snapshot[id] = {}
                    for key in data.keys():
                        if key=='heart_rate' or key=='resp_rate':
                            min_data = np.array(data[key])
                            if min_data[min_data>0].size > 0:
                                self.mcu_id_realTime_data[id][key].append(np.mean(min_data[min_data>0]))
                            else:
                                self.mcu_id_realTime_data[id][key].append(0)

                        snapshot[id][key] = data[key]
                        data[key] = []

                    timestamp = datetime.now(self.taiwan_tz).strftime("%Y-%m-%d %H:%M:%S")
                    self.mcu_id_realTime_data[id]['rate_timestamp'].append(timestamp)
                    if len(self.mcu_id_realTime_data[id]['rate_timestamp'])>=4*60:
                        self.mcu_id_realTime_data[id]['rate_timestamp'].pop(0)
                        self.mcu_id_realTime_data[id]['resp_rate'].pop(0)
                        self.mcu_id_realTime_data[id]['heart_rate'].pop(0)

                with open(os.path.join(dated_dir, f'snapshot_{snapshot_time}.json'), "w") as f:
                    json.dump(snapshot, f, indent=2)

                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.5)

    async def start(self):
        self.running = True
        asyncio.create_task(self._prune_and_store())

        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"🚀 Async Server listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    async def start_autoscaling(self, addr_str):
        if addr_str not in self.clients:
            print(f"⚠️ 無法發送 Autoscaling 指令，{addr_str} 尚未連線")
            return

        _, writer = self.clients[addr_str]
        arr = bytearray(513)
        arr[0:11] = bytes([0x13, 0x00, 0x89, 0x00, 0x0D, 0x14, 0xEB, 1, 1, 0x00, 0x01])
        checksum = self._calculate_checksum(sum(arr[:11]))
        arr[11], arr[12] = checksum

        try:
            writer.write(arr)
            await writer.drain()
            print(f"📤 已送出 Autoscaling 指令到 {addr_str}")
        except Exception as e:
            print(f"❌ 發送 Autoscaling 指令失敗：{e}")

    async def shutdown(self):
        print("🧹 正在關閉 AsyncTCPServer...")
        self.running = False
        for addr_str, (reader, writer) in self.clients.items():
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print(f"⚠️ 關閉 {addr_str} 時發生錯誤：{e}")
        print("✅ 所有連線已關閉")


# 測試 callback：印出資料內容
if __name__ == '__main__':
    def data_callback(data_dict):
        pass  # 可加入列印或處理邏輯

    tcp_server = AsyncTCPServer(callback=data_callback)
    try:
        asyncio.run(tcp_server.start())
    except KeyboardInterrupt:
        tcp_server.running = False
        print("🛑 Received interrupt. Server shutting down...")
