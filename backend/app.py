import threading
import time

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from TCP_server_text import TCPServer
import signal
import sys

def shutdown_handler(sig, frame):
    print("🛑 收到中止訊號，關閉 TCP Server...")
    tcp_server.shutdown()
    sys.exit(0)

# 註冊 Ctrl+C 中斷事件
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

app = Flask(__name__)
CORS(app)  # ← 這一行開啟所有來源都能存取 Flask API
socketio = SocketIO(app, cors_allowed_origins="*")



@app.route("/status")
def get_status():
    return jsonify(tcp_server.data_frontend)

@app.route("/Autoscaling", methods=['POST'])
def start_autoscaling():
    data = request.json  # 取出前端送來的 JSON 資料
    print(f"🛰️ 收到前端送來的資料：{data}")  # 印出來觀察
    # 這邊可以做進一步處理，比如針對 addr 做某些事情
    addr = data.get('addr')
    tcp_server.start_autoscaling(addr_str=addr)

    return jsonify({"status": "ok"})

def start_tcp_server():
    tcp_server.start()

# Global TCP Server instance
tcp_server = TCPServer(callback=lambda data: (socketio.emit('mcu_update', data)))
threading.Thread(target=start_tcp_server, daemon=True).start()

# def start_web():
#     socketio.run(app, host="0.0.0.0", port=8000, allow_unsafe_werkzeug=True)

# if __name__ == '__main__':
    
#     start_web()
