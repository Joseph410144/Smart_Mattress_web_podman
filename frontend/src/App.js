import './App.css';
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MCUDetailPage from './components/MCUDetailPage';
import MCUSelectPage from './components/MCUSelectPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MCUSelectPage />} />
        <Route path="/mcu/:id" element={<MCUDetailPage />} />
      </Routes>
    </Router>
  );
}

export default App;