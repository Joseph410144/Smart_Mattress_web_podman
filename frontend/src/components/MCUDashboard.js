import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function MCUDashboard() {
  const [mcuList, setMcuList] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchMCUs = () => {
      axios.get('http://172.20.10.3:8000/status')
        .then(res => {
          const mcuObj = res.data;
          const mcuArray = Object.values(mcuObj).filter(mcu => mcu.status === "connect");
          setMcuList(mcuArray);
        })
        .catch(err => console.error("❌ 無法取得 MCU 清單", err));
    };

    fetchMCUs(); // initial fetch
    const interval = setInterval(fetchMCUs, 3000); // 每 3 秒更新一次

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
      <h2>📡 Smart Mattress Live Monitoring</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '2rem', justifyContent: 'center' }}>
        {mcuList.map((mcu) => (
          <MCUCard key={mcu.addr} mcu={mcu} onClick={() => navigate(`/mcu/${mcu.name}`)} />
        ))}
      </div>
    </div>
  );
}

function handleCommand(addr) {
  console.log("🛰️ 送出指令到", addr);
  axios.post('http://172.20.10.3:8000/Autoscaling', { addr })
    .then(res => console.log("✅ 後端回應", res.data))
    .catch(err => console.error("❌ 指令失敗", err));
}

function handleDownload(mcu_id) {
  const selectedDate = prompt("請輸入日期（格式：YYYY-MM-DD）");
  if (!selectedDate) return;
  axios.get(`http://172.20.10.3:8001/download/${mcu_id}?date=${selectedDate}`, {
    responseType: 'blob'
  }).then(res => {
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${mcu_id}_${selectedDate}.json.gz`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }).catch(err => {
    console.error("❌ 無法下載資料", err);
    alert("下載失敗，請確認日期格式與資料是否存在。");
  });
}

function MCUCard({ mcu, onClick }) {
  const outOfBed = mcu.outofbed ?? null;
  const movement = mcu.movement ?? null;
  const autoscaling = mcu.autoscaling ?? null;
  const rssi_frontend = mcu.RSSI ?? -1;

  const rssiTextMap = {
    0: "📶 訊號非常強",
    1: "📡 訊號良好",
    2: "📡 訊號普通",
    3: "⚠️ 訊號偏弱",
    4: "❌ 訊號極差",
    [-1]: "🛠️ 未知訊號（請更新韌體）"
  };

  const rssiColorMap = {
    0: "green",
    1: "#4caf50",
    2: "#ff9800",
    3: "#f44336",
    4: "#b71c1c",
    [-1]: "#999"
  };

  return (
    <div
      onClick={onClick}
      style={{
        cursor: 'pointer',
        width: '220px',
        border: '1px solid #ccc',
        borderRadius: '12px',
        padding: '1rem',
        textAlign: 'center',
        boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
        backgroundColor: mcu.status === 'disconnected' ? '#f8d7da' : 'white'
      }}>
      <h4>📍 MCU: {mcu.name}</h4>
      <img
        src={
          outOfBed === 1
            ? '/icons/outofbed.png'
            : movement
            ? '/icons/movement.png'
            : '/icons/measuring.png'
        }
        alt="status"
        style={{ width: '40px', marginBottom: '0.5rem' }}
      />
      <p>❤️ {mcu.heart_rate ?? '—'} bpm</p>
      <p>🌬️ {mcu.resp_rate ?? '—'} rpm</p>
      <p style={{ fontSize: '0.75rem' }}>
        {outOfBed === 1
          ? '🚶‍♂️ 離床中'
          : movement === 1
          ? '🏃 體動中'
          : '⏳ 量測中'}
      </p>
      <p style={{ fontSize: '0.75rem', color: '#666' }}>⏱️ {mcu.timestamp ?? null}</p>
      <p style={{ fontSize: '0.75rem', color: rssiColorMap[rssi_frontend] }}>{rssiTextMap[rssi_frontend]}</p>
      <p style={{ fontSize: '0.75rem', color: autoscaling === 1 ? 'green' : 'gray' }}>
        {autoscaling === 1 ? '⚙️ 自動調整中' : '🛑 自動調整停止'}
      </p>
      {/* <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1rem' }}>
        <button
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.75rem',
            borderRadius: '6px',
            border: '1px solid #00796B',
            backgroundColor: '#00796B',
            color: 'white',
            cursor: 'pointer'
          }}
          onClick={() => handleCommand(mcu.addr)}
        >
          ⚙️ 自動調整
        </button>
        <button
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.75rem',
            borderRadius: '6px',
            border: '1px solid #1976d2',
            backgroundColor: '#1976d2',
            color: 'white',
            cursor: 'pointer'
          }}
          onClick={() => handleDownload(mcu.name)}
        >
          ⬇️ 下載資料
        </button>
      </div> */}
    </div>
  );
}

export default MCUDashboard;