import React, { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import StyledButton from './StyledButton';

function MCUHistoryPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [images, setImages] = useState({});

  const queryParams = new URLSearchParams(location.search);
  const start = queryParams.get('start');
  const end = queryParams.get('end');

  useEffect(() => {
    if (!start || !end || !id) return;
    axios.get(`http://172.20.10.3:8001/historyplot/${id}?startdate=${start}&enddate=${end}`)
      .then(res => {
        setImages(res.data);
      })
      .catch(err => {
        console.error('❌ 歷史圖表載入失敗', err);
        alert('無法載入圖表，請確認 MCU 與時間格式是否正確');
      });
  }, [id, start, end]);

  const cardStyle = {
    background: 'rgba(255 255 255 / 0.85)',
    borderRadius: '12px',
    boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
    padding: '1.5rem',
    margin: '1.5rem auto',
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
      <h2 style={{ fontWeight: '700', marginBottom: '1rem' }}>📍 MCU 歷史資料 - {id}</h2>
      <p style={{ marginBottom: '2rem', color: '#555' }}>⏱️ 查詢時間區間：{start} ~ {end}</p>

      <StyledButton onClick={() => navigate(`/mcu/${id}`)}>
        🔙 返回即時監控
      </StyledButton>

      {images.heart_image && (
        <div style={cardStyle}>
          <h3>❤️ 心率（每分鐘平均）</h3>
          <img src={`data:image/png;base64,${images.heart_image}`} alt="Heart Rate" style={imgStyle} />
        </div>
      )}

      {images.resp_image && (
        <div style={cardStyle}>
          <h3>🌬️ 呼吸率（每分鐘平均）</h3>
          <img src={`data:image/png;base64,${images.resp_image}`} alt="Respiration Rate" style={imgStyle} />
        </div>
      )}

      {images.status_image && (
        <div style={cardStyle}>
          <h3>📊 狀態變化圖</h3>
          <img src={`data:image/png;base64,${images.status_image}`} alt="Status Chart" style={imgStyle} />
        </div>
      )}

      {!images.heart_image && !images.resp_image && !images.status_image && (
        <div style={{ marginTop: '3rem', color: '#999', fontSize: '1.1rem' }}>
          ⚠️ 無圖表可顯示，請確認是否有資料。
        </div>
      )}
    </div>
  );
}

export default MCUHistoryPage;
