import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { io } from 'socket.io-client';

function MCUDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  function handleDownload() {
    const selectedDate = prompt("請輸入日期（格式：YYYY-MM-DD）");
    if (!selectedDate) return;
    // Use the correct MCU ID (from data context)
    const mcu_id = data?.name ?? id;
    axios.get(`http://172.20.10.2:8000/download/${mcu_id}?date=${selectedDate}`, {
      responseType: 'blob'
    }).then(res => {
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${mcu_id}_${selectedDate}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    }).catch(err => {
      console.error("❌ 無法下載資料", err);
      alert("下載失敗，請確認日期格式與資料是否存在。");
    });
  }

  useEffect(() => {
    const fetchData = () => {
      axios.get(`http://172.20.10.2:8000/mcu/${id}`)
        .then(res => {
          if (res.data.status === "disconnected") {
            setData({ status: "disconnected" });
          } else {
            setData(res.data);
          }
        })
        .catch(err => console.error("❌ 無法取得 MCU 資料", err));
    };

    fetchData(); // initial fetch
    const interval = setInterval(fetchData, 1000); // 每秒更新一次

    const socket = io('http://172.20.10.2:8000');
    socket.on('mcu_disconnect', (payload) => {
      console.log("🛑 MCU disconnect event received:", payload);
      if (payload.id === id) {
        setData({ status: "disconnected" });
      }
    });

    return () => {
      clearInterval(interval); // 清除定時器
      socket.disconnect();
    };
  }, [id]);

  function handleCommand() {
    console.log("🛰️ 送出指令到", data.addr);
    axios.post('http://172.20.10.2:8000/Autoscaling', { addr: data.addr })
      .then(res => console.log("✅ 後端回應", res.data))
      .catch(err => console.error("❌ 指令失敗", err));
  }

  if (data?.status === "disconnected") {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        ❌ MCU 已斷線<br />
        <button
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            fontSize: '0.85rem',
            borderRadius: '8px',
            border: '1px solid #333',
            backgroundColor: '#333',
            color: 'white',
            cursor: 'pointer'
          }}
          onClick={() => navigate('/')}
        >
          🔙 回首頁
        </button>
      </div>
    );
  }
  if (!data) {
    return (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          ❌ MCU 已斷線<br />
          <button
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              fontSize: '0.85rem',
              borderRadius: '8px',
              border: '1px solid #333',
              backgroundColor: '#333',
              color: 'white',
              cursor: 'pointer'
            }}
            onClick={() => navigate('/')}
          >
            🔙 回首頁
          </button>
        </div>
      );
  }

  const outOfBed = data.outofbed ?? null;
  const movement = data.movement ?? null;
  const autoscaling = data.autoscaling ?? null;
  const mcu_id = data.name ?? id;

  return (
    <div className="tile" style={{ textAlign: 'center', marginTop: '2rem' }}>
      <h2>📍 MCU ID：{mcu_id}</h2>
      <div>
        <img
          src={
            outOfBed === 1
              ? '/icons/outofbed.png'
              : movement
              ? '/icons/movement.png'
              : '/icons/measuring.png'
          }
          alt="status icon"
          style={{ width: '60px', marginBottom: '0.5rem' }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        <p><strong>❤️ {data.heart_rate ?? null}</strong></p>
        <p><strong>🌬️ {data.resp_rate ?? null}</strong></p>
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
      <p style={{ fontSize: '0.75rem', color: '#666' }}>⏱️ {data.timestamp ?? null}</p>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
        <button
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.85rem',
            borderRadius: '8px',
            border: '1px solid #00796B',
            backgroundColor: '#00796B',
            color: 'white',
            cursor: 'pointer'
          }}
          onClick={handleCommand}
        >
          ⚙️ 自動調整
        </button>

        <button
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.85rem',
            borderRadius: '8px',
            border: '1px solid #333',
            backgroundColor: '#333',
            color: 'white',
            cursor: 'pointer'
          }}
          onClick={() => navigate('/')}
        >
          🔙 回首頁
        </button>

        <button
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.85rem',
            borderRadius: '8px',
            border: '1px solid #1976d2',
            backgroundColor: '#1976d2',
            color: 'white',
            cursor: 'pointer'
          }}
          onClick={handleDownload}
        >
          ⬇️ 下載資料
        </button>
      </div>
    </div>
  );
}

export default MCUDetailPage;