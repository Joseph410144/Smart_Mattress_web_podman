import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function MCUSelectPage() {
  const [inputID, setInputID] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (inputID.trim()) {
      try {
        const res = await fetch(`http://172.20.10.3:8000/mcu/${inputID}`);
        if (res.ok) {
          setError('');
          navigate(`/mcu/${inputID}`);
        } else {
          setError('❌ 目前沒有這個 MCU');
        }
      } catch (err) {
        setError('⚠️ 無法連線到伺服器');
      }
    }
  };

  return (
    <div style={{ padding: '3rem', textAlign: 'center', fontFamily: 'Arial, sans-serif' }}>
      <h2 style={{ fontSize: '2rem', color: '#2c3e50', marginBottom: '1rem' }}>
        🔍 查詢 MCU 裝置資料
      </h2>
      <form
        onSubmit={handleSubmit}
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}
      >
        <input
          type="text"
          placeholder="請輸入 MCU ID"
          value={inputID}
          onChange={(e) => setInputID(e.target.value)}
          style={{
            padding: '0.75rem 1rem',
            fontSize: '1rem',
            borderRadius: '8px',
            border: '1px solid #ccc',
            width: '250px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        />
        <button
          type="submit"
          style={{
            padding: '0.75rem 1.5rem',
            fontSize: '1rem',
            backgroundColor: '#2980b9',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
          }}
        >
          🔎 查詢
        </button>
      </form>
      {error && <p style={{ color: 'red', marginTop: '1rem', fontSize: '0.95rem' }}>{error}</p>}
    </div>
  );
}

export default MCUSelectPage;