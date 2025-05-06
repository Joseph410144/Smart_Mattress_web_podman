import time
import struct
import socket
import threading
from datetime import datetime

class TCPServer:
    def __init__(self, callback, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {'ip:port': socket}
        self.data_storage = {}  # {'ip:port': {"raw": [...], "heart_rate": [...], ...}}
        self.running = True
        self.callback = callback

        self.check_array = self._create_check_array()
        self.data_array = self._create_data_array()

        self.lastAdccurrent = 0

    def _create_check_array(self):
        arr = bytearray(513)
        arr[0:9] = bytes([0x13, 0x00, 0x01, 0x00, 0x09, 0x00, 0x01, 0x00, 0x1E])
        return arr

    def _create_data_array(self):
        arr = bytearray(513)
        arr[0:7] = bytes([0x13, 0x00, 0x28, 0x00, 0x09, 0x00, 0x01])
        checksum = self._calculate_checksum(sum(arr[:7]))
        arr[7], arr[8] = checksum
        return arr

    def _calculate_checksum(self, total_sum):
        # 確保總和在 16 位內（模擬溢出情況，只保留低 16 位）
        total_sum &= 0xFFFF

        # 轉換為 16 進制並拆分高位和低位
        high_byte = (total_sum >> 8) & 0xFF  # 取高 8 位
        low_byte = total_sum & 0xFF         # 取低 8 位

        return high_byte, low_byte

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"🚀 Server listening on {self.host}:{self.port}")

        while self.running:
            client_socket, client_addr = self.server_socket.accept()
            addr_str = f"{client_addr[0]}:{client_addr[1]}"
            print(f"✅ New client: {addr_str}")
            client_socket.sendall(self.check_array)
            data = client_socket.recv(1400)
            if self._check_reply(data):
                self.clients[addr_str] = client_socket
                self.data_storage[addr_str] = {
                    "raw": [],
                    "heart_rate": [],
                    "resp_rate": [],
                    "movement": [],
                    "outofbed": [],
                    'autoscaling': [],
                    "timestamp": []
                }
                print(f'start getting data on {addr_str}')
                client_socket.settimeout(10.0)
                threading.Thread(target=self.handle_client, args=(addr_str,), daemon=True).start()
            else:
                print(f"❌ Verification failed for {addr_str}")
                client_socket.close()

    def _check_reply(self, data):
        return len(data) >= 13 and data[5] == 0x03

    def handle_client(self, addr_str):
        sock = self.clients[addr_str]
        while self.running:
            try:
                sock.sendall(self.data_array)
                MCUresponseData = sock.recv(1400)
                # disconnected function
                if not MCUresponseData:
                    raise ConnectionError("MCU disconnected (no data received)")
                # 解析資料（依據實際協定調整）
                if MCUresponseData[5] != 3:
                    continue
                raw = []
                heart = []
                rawI = 32
                heartI = 232
                """  
                用兩個byte存資料 >> 一個高位一個低位，不是直接相加
                MCU回傳的浮點數為大端序
                """
                CurrentAdccurrent = (MCUresponseData[6])<<8 | MCUresponseData[6+1]
                AdcPosition = (MCUresponseData[22])<<8 | MCUresponseData[23]
                AutoScaling = int(MCUresponseData[24])
                HeartMCU = int(MCUresponseData[12])
                RespMCU = int(MCUresponseData[13])
                OobMCU = int(MCUresponseData[14])
                if int(OobMCU) == 79:
                    OobMCU = 1
                    BdmmtMCU = 0
                else:
                    OobMCU = 0
                    BdmmtMCU = MCUresponseData[15]
                OobLmtH = (MCUresponseData[18])<<8 | MCUresponseData[19]
                OobLmtL = (MCUresponseData[20])<<8 | MCUresponseData[21]

                if CurrentAdccurrent > self.lastAdccurrent:
                    for i in range(self.lastAdccurrent, CurrentAdccurrent):
                        raw.append((MCUresponseData[(rawI+i*2)])<<8 | MCUresponseData[(rawI+i*2)+1])
                        heart.append((MCUresponseData[(heartI+i*2)])<<8 | MCUresponseData[(heartI+i*2)+1])
                    
                else:
                    for i in range(self.lastAdccurrent, 100):
                        raw.append((MCUresponseData[(rawI+i*2)])<<8 | MCUresponseData[(rawI+i*2)+1])
                        heart.append((MCUresponseData[(heartI+i*2)])<<8 | MCUresponseData[(heartI+i*2)+1])
                        
                    for i in range(CurrentAdccurrent):
                        raw.append((MCUresponseData[(rawI+i*2)])<<8 | MCUresponseData[(rawI+i*2)+1])
                        heart.append((MCUresponseData[(heartI+i*2)])<<8 | MCUresponseData[(heartI+i*2)+1])
                        
                
                self.lastAdccurrent = CurrentAdccurrent
                
                timestamp = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")

                self.data_storage[addr_str]["raw"] = self.data_storage[addr_str]["raw"] + raw
                self.data_storage[addr_str]["heart_rate"].append(HeartMCU)
                self.data_storage[addr_str]["resp_rate"].append(RespMCU)
                self.data_storage[addr_str]["movement"].append(BdmmtMCU)
                self.data_storage[addr_str]["outofbed"].append(OobMCU)
                self.data_storage[addr_str]["autoscaling"].append(AutoScaling)
                self.data_storage[addr_str]["timestamp"].append(timestamp)

                self.callback(self.data_storage)
                time.sleep(0.5)

            except socket.timeout:
                print("MCU timeout: no data within 10 seconds >> disconnect")
                sock.close()
                del self.clients[addr_str]
                del self.data_storage[addr_str]
                break

            except Exception as e:
                print(f"⚠️ Client {addr_str} error: {e}")
                sock.close()
                del self.clients[addr_str]
                del self.data_storage[addr_str]
                break

    def start_autoscaling(self, addr_str):
        # get MCU socket
        sock = self.clients[addr_str]
        # set cmd array
        arr = bytearray(513)
        arr[0:11] = bytes([0x13, 0x00, 0x89, 0x0, 0x0D, 0x14, 0xEB, 1, 1, 0x00, 0x01])
        checksum = self._calculate_checksum(sum(arr[:11]))
        arr[11], arr[12] = checksum
        # sent cmd to MCU
        sock.sendall(arr)
        # MCUresponseData = sock.recv(1400)

    def shutdown(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for sock in self.clients.values():
            sock.close()
        print("🧹 Server shut down")


# 測試 callback：印出資料內容
if __name__ == '__main__':
    def data_callback(data_dict):
        for dict_key in data_dict.keys():
            data = data_dict[dict_key]
            timestamp_str = datetime.fromtimestamp(data['timestamp'][-1]).strftime("%Y-%m-%d %H:%M:%S")
            print(f"📩 {dict_key} → time: {timestamp_str}, HR: {data['heart_rate'][-1]}, RR: {data['resp_rate'][-1]}, Mov: {data['movement'][-1]}, Oob: {data['outofbed'][-1]}")

    server = TCPServer(callback=data_callback)
    threading.Thread(target=server.start, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
