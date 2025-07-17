import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { io } from 'socket.io-client';
import StyledButton from './StyledButton';

function MCUDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [analysisDate, setAnalysisDate] = useState('');
  const [chartImages, setChartImages] = useState(null);
  const [showHistoryForm, setShowHistoryForm] = useState(false);
  const [historyParams, setHistoryParams] = useState({ start: '', end: '' });

  function handleDownload() {
    const selectedDate = prompt("請輸入日期（格式：YYYY-MM-DD）");
    if (!selectedDate) return;
    // Use the correct MCU ID (from data context)
    const mcu_id = data?.name ?? id;
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

  function handleLoadCharts() {
    if (!analysisDate) {
      alert("請先輸入日期（格式：YYYY-MM-DD）");
      return;
    }
    const mcu_id = data?.name ?? id;
    axios.get(`http://172.20.10.3:8001/analysis/${mcu_id}?date=${analysisDate}`)
      .then(res => {
        setChartImages(res.data);
      })
      .catch(err => {
        console.error("❌ 圖表資料載入失敗", err);
        alert("無法載入圖表，請確認資料是否存在。");
      });
  }

  useEffect(() => {
    const fetchData = () => {
      axios.get(`http://172.20.10.3:8000/mcu/${id}`)
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
    const interval = setInterval(fetchData, 3000); // 每秒更新一次

    const socket = io('http://172.20.10.3:8000');
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

  const mcu_id = data?.name ?? id;

  // 加入即時合併圖表的 useEffect
  useEffect(() => {
    if (!mcu_id) return;

    const fetchChart = () => {
      axios.get(`http://172.20.10.3:8001/realtime/${mcu_id}`)
        .then(res => {
          if (res.data.heart_image && res.data.resp_image && res.data.status_image) {
            setChartImages({
              heart_image: res.data.heart_image,
              resp_image: res.data.resp_image,
              status_image: res.data.status_image
            });
          } else {
            console.warn("⚠️ MCU 尚未連線或無圖可顯示", res.data.error);
            setChartImages(null); // 清空圖表避免殘留舊圖
          }
        })
        .catch(err => {
          console.error("❌ 即時圖表載入失敗", err);
        });
    };

    fetchChart(); // 初始載入一次
    const interval = setInterval(fetchChart, 3000); // 每 3 秒更新一次

    return () => clearInterval(interval); // 清除定時器
  }, [mcu_id]);

  if (data?.status === "disconnected") {
    return (
      <div style={{ padding: '2rem', maxWidth: '600px', margin: '3rem auto', textAlign: 'center', color: '#b00020' }}>
        <h2 style={{ marginBottom: '1rem' }}>⚠️ MCU {id} 已斷線</h2>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '2rem' }}>
          <StyledButton onClick={() => navigate('/')}>
            🔙 回首頁
          </StyledButton>
          <StyledButton onClick={handleDownload}>
            ⬇️ 下載資料
          </StyledButton>
        </div>
      </div>
    );
  }
  if (!data) {
    return (
      <div style={{ padding: '2rem', maxWidth: '600px', margin: '3rem auto', textAlign: 'center', color: '#b00020' }}>
        <h2 style={{ marginBottom: '1rem' }}>⚠️ 無法取得 MCU {id} 資料</h2>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '2rem' }}>
          <StyledButton onClick={() => navigate('/')}>
            🔙 回首頁
          </StyledButton>
          <StyledButton onClick={handleDownload}>
            ⬇️ 下載資料
          </StyledButton>
        </div>
      </div>
    );
  }

  const outOfBed = data.outofbed ?? null;
  const movement = data.movement ?? null;
  const autoscaling = data.autoscaling ?? null;

  function handleCommand() {
    console.log("🛰️ 送出指令到", data.addr);
    axios.post('http://172.20.10.3:8000/Autoscaling', { addr: data.addr })
      .then(res => console.log("✅ 後端回應", res.data))
      .catch(err => console.error("❌ 指令失敗", err));
  }

  function handleHistorySubmit() {
    if (!historyParams.start || !historyParams.end) {
      alert("請輸入完整的開始與結束時間！");
      return;
    }
    navigate(`/history/${mcu_id}?start=${historyParams.start}&end=${historyParams.end}`);
  }

  const cardStyle = {
    background: 'rgba(255 255 255 / 0.85)',
    borderRadius: '12px',
    boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
    padding: '1.5rem',
    margin: '1rem auto',
    maxWidth: '900px',
    textAlign: 'center',
  };

  const imgStyle = {
    width: '100%',
    backgroundColor: 'transparent',
    marginBottom: '1.5rem',
    borderRadius: '8px',
    objectFit: 'contain',
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '2rem auto', textAlign: 'center', fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif" }}>
      <h2 style={{ fontWeight: '700', marginBottom: '2rem' }}>📍 MCU ID：{mcu_id}</h2>

      <div style={{ ...cardStyle, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '2rem', flexWrap: 'wrap' }}>
        <img
          src={
            outOfBed === 1
              ? '/icons/outofbed.png'
              : movement
              ? '/icons/movement.png'
              : '/icons/measuring.png'
          }
          alt="status icon"
          style={{ width: '70px', flexShrink: 0 }}
        />
        <div style={{ minWidth: '200px', textAlign: 'left' }}>
          <p style={{ margin: '0.3rem 0', fontSize: '1.2rem' }}><strong>❤️ 心率: </strong>{data.heart_rate ?? '-'}</p>
          <p style={{ margin: '0.3rem 0', fontSize: '1.2rem' }}><strong>🌬️ 呼吸率: </strong>{data.resp_rate ?? '-'}</p>
          <p style={{ margin: '0.3rem 0', fontSize: '1.1rem', color: outOfBed === 1 ? '#d32f2f' : movement === 1 ? '#1976d2' : '#555' }}>
            {outOfBed === 1
              ? '🚶‍♂️ 離床中'
              : movement === 1
              ? '🏃 體動中'
              : '⏳ 量測中'}
          </p>
          <p style={{ margin: '0.3rem 0', fontSize: '1.1rem', color: autoscaling === 1 ? 'green' : 'gray' }}>
            {autoscaling === 1 ? '⚙️ 自動調整中' : '🛑 自動調整停止'}
          </p>
          <p style={{ margin: '0.3rem 0', fontSize: '0.9rem', color: '#666' }}>⏱️ {data.timestamp ?? '-'}</p>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '2rem', flexWrap: 'wrap' }}>
        <StyledButton onClick={handleCommand} style={{ flexGrow: 1, maxWidth: '200px' }}>
          ⚙️ 自動調整
        </StyledButton>

        <StyledButton onClick={() => navigate('/Dashboard')} style={{ flexGrow: 1, maxWidth: '200px' }}>
          🔙 回首頁
        </StyledButton>

        <StyledButton onClick={handleDownload} style={{ flexGrow: 1, maxWidth: '200px' }}>
          ⬇️ 下載資料
        </StyledButton>

        <StyledButton onClick={() => setShowHistoryForm(prev => !prev)} style={{ flexGrow: 1, maxWidth: '200px' }}>
          📁 查詢歷史資料
        </StyledButton>
      </div>

      {showHistoryForm && (
        <div style={{ ...cardStyle, marginTop: '2rem' }}>
          <h3>📅 請輸入查詢時間區間</h3>
          <p style={{ fontSize: '0.9rem', color: '#666' }}>格式：YYYY-MM-DD HH-MM，例如 2025-07-14 15-30</p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '1rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="開始時間"
              value={historyParams.start}
              onChange={e => setHistoryParams({ ...historyParams, start: e.target.value })}
              style={{ padding: '0.5rem', minWidth: '160px' }}
            />
            <input
              type="text"
              placeholder="結束時間"
              value={historyParams.end}
              onChange={e => setHistoryParams({ ...historyParams, end: e.target.value })}
              style={{ padding: '0.5rem', minWidth: '160px' }}
            />
            <StyledButton onClick={handleHistorySubmit}>
              ✅ 送出查詢
            </StyledButton>
          </div>
        </div>
      )}

      {/* 圖表區塊 */}
      {chartImages?.heart_image && chartImages?.resp_image && chartImages?.status_image ? (
        <>
          <div style={cardStyle}>
            <h3 style={{ marginBottom: '1rem' }}>📊 MCU Real-Time Heart Rate</h3>
            <img
              src={`data:image/png;base64,${chartImages.heart_image}`}
              alt="Heart Rate Chart"
              style={imgStyle}
              onError={(e) => { e.target.onerror = null; e.target.src = '/icons/image_error.png'; }}
            />
          </div>
          <div style={cardStyle}>
            <h3 style={{ marginBottom: '1rem' }}>📊 MCU Real-Time Respiration</h3>
            <img
              src={`data:image/png;base64,${chartImages.resp_image}`}
              alt="Respiration Chart"
              style={imgStyle}
              onError={(e) => { e.target.onerror = null; e.target.src = '/icons/image_error.png'; }}
            />
          </div>
          <div style={cardStyle}>
            <h3 style={{ marginBottom: '1rem' }}>📊 MCU Real-Time Status</h3>
            <img
              src={`data:image/png;base64,${chartImages.status_image}`}
              alt="Status Chart"
              style={imgStyle}
              onError={(e) => { e.target.onerror = null; e.target.src = '/icons/image_error.png'; }}
            />
          </div>
        </>
      ) : (
        <div style={{ marginTop: '3rem', color: '#999', fontSize: '1.1rem' }}>
          ⚠️ 尚未連線或無圖可顯示
        </div>
      )}
    </div>
  );
}

export default MCUDetailPage;