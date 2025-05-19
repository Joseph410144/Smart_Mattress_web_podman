import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function MCUSelectPage() {
  const [inputID, setInputID] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputID.trim()) {
      navigate(`/mcu/${inputID}`);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>🔍 查詢 MCU 裝置資料</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="請輸入 MCU ID"
          value={inputID}
          onChange={(e) => setInputID(e.target.value)}
        />
        <button type="submit">查詢</button>
      </form>
    </div>
  );
}

export default MCUSelectPage;