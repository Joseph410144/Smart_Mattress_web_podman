import './App.css';
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';
// import { FaMicrochip } from 'react-icons/fa';

const socket = io('http://192.168.0.117:8000', {
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 2000
});

function MCUTile({ addr, data, handleCommand }) {
  const outOfBed = data.outofbed?.slice(-1)[0];
  const movement = data.movement?.slice(-1)[0];
  const autoscaling = data.autoscaling?.slice(-1)[0];
  console.log(`[Debug] ${addr} → outOfBed:`, outOfBed, ', movement:', movement, ', Autoscaling:', autoscaling);

  return (
    <div className="tile" style={{ textAlign: 'center' }}>
      <div>
        <img
          src={
            outOfBed===1
              ? '/icons/outofbed.png'
              : movement
              ? '/icons/movement.png'
              : '/icons/measuring.png'
          }
          alt="status icon"
          style={{ width: '60px', marginBottom: '0.5rem' }}
        />
      </div>
      <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>{addr}</h3>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        <p><strong>❤️ {data.heart_rate?.slice(-1)[0]}</strong></p>
        <p><strong>🌬️ {data.resp_rate?.slice(-1)[0]}</strong></p>
      </div>
      <p style={{ fontSize: '0.85rem' }}>
        {outOfBed === 1
          ? '🚶‍♂️ 離床中'
          : movement === 1
          ? '🏃 體動中'
          : '⏳ 量測中'}
      </p>
      <p style={{ fontSize: '0.85rem', color: autoscaling === 1 ? 'green' : 'gray' }}>
        {autoscaling === 1 ? '⚙️ 自動調整中' : '🛑 自動調整停止'}
      </p>
      <p style={{ fontSize: '0.75rem', color: '#666' }}>⏱️ {data.timestamp?.slice(-1)[0]}</p>
      <button 
        style={{
          marginTop: '0.5rem',
          padding: '0.4rem 0.8rem',
          fontSize: '0.85rem',
          borderRadius: '8px',
          border: '1px solid #00796B',
          backgroundColor: '#00796B',
          color: 'white',
          cursor: 'pointer'
        }}
        onClick={() => handleCommand(addr)}
      >
        auto scale
      </button>
    </div>
  );
}

function App() {
  const [mcuData, setMcuData] = useState({});

  function handleCommand(addr) {
    console.log("🛰️ 送出指令到", addr);
    axios.post('http://192.168.0.117:8000/Autoscaling', { addr })
      .then(res => console.log("✅ 後端回應", res.data))
      .catch(err => console.error("❌ 指令失敗", err));
  }

  useEffect(() => {
    document.title = "Innolux MCU Dashboard";
    const fetchStatus = () => {
      axios.get('http://192.168.0.117:8000/status')
        .then(res => {
          console.log("📥 定時 status 更新:", res.data);
          setMcuData(res.data);
        })
        .catch(err => console.error("❌ 定時抓取失敗", err));
    };

    fetchStatus(); // 初始執行一次
    const interval = setInterval(fetchStatus, 1000); // 每 1 秒抓一次

    socket.on('connect', () => {
      console.log("✅ WebSocket connected!");
    });

    socket.on('disconnect', () => {
      console.warn("❌ WebSocket disconnected! 將切換為 polling 模式");
    });

    socket.on('mcu_update', data => {
      console.log("🔥 Received mcu_update from socket:", data);
      setMcuData(prev => {
        const updated = { ...prev };
        for (const addr in data) {
          updated[addr] = { ...data[addr] };
        }
        return updated;
      });
    });

    return () => {
      clearInterval(interval);
      socket.off('mcu_update');
      socket.off('connect');
      socket.off('disconnect');
    };
  }, []);

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">📡 MCU Monitor Dashboard</h1>
      <div className="mcu-grid">
        {Object.keys(mcuData).length === 0 ? (
          <div style={{ color: '#888', fontSize: '1.2rem' }}>🚫 No MCU connected</div>
        ) : (
          Object.entries(mcuData).map(([addr, data]) => (
            <MCUTile key={addr} addr={addr} data={data} handleCommand={handleCommand} />
          ))
        )}
      </div>
    </div>
  );
}

export default App;