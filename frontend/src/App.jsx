import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000');

function MCUTile({ addr, data }) {
  return (
    <div className="tile">
      <h3>{addr}</h3>
      <p><strong>Heart:</strong> {data.heart_rate?.slice(-1)[0]}</p>
      <p><strong>Resp:</strong> {data.resp_rate?.slice(-1)[0]}</p>
      <p><strong>Move:</strong> {data.movement?.slice(-1)[0]}</p>
      <p><strong>OutOfBed:</strong> {data.outofbed?.slice(-1)[0]}</p>
      <p><strong>Time:</strong> {data.timestamp?.slice(-1)[0]}</p>
    </div>
  );
}

function App() {
  const [mcuData, setMcuData] = useState({});

  useEffect(() => {
    axios.get('http://localhost:8000/status').then(res => setMcuData(res.data));

    socket.on('mcu_update', data => {
      setMcuData({ ...data });
    });

    return () => socket.disconnect();
  }, []);

  return (
    <div style={{ padding: '2rem' }}>
      <h1 style={{ textAlign: 'center' }}>MCU Monitor Dashboard</h1>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {Object.entries(mcuData).map(([addr, data]) => (
          <MCUTile key={addr} addr={addr} data={data} />
        ))}
      </div>
    </div>
  );
}

export default App;
