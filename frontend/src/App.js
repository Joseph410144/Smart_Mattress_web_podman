import './App.css';
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MCUDetailPage from './components/MCUDetailPage';
import MCUSelectPage from './components/MCUSelectPage';
import MCUDashboard from './components/MCUDashboard';
import MCUHistoryPage from './components/MCUHistoryPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MCUSelectPage />} />
        <Route path="/mcu/:id" element={<MCUDetailPage />} />
        <Route path="/dashboard" element={<MCUDashboard />} />
        <Route path="/history/:id" element={<MCUHistoryPage />} />
      </Routes>
    </Router>
  );
}

export default App;