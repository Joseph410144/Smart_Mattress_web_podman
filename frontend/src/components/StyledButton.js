// src/components/StyledButton.js
import React from 'react';

const StyledButton = ({ children, style = {}, ...props }) => {
  return (
    <button
      {...props}
      style={{
        backgroundColor: '#1976d2',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        padding: '0.5rem 1rem',
        fontSize: '0.9rem',
        cursor: 'pointer',
        transition: '0.3s',
        ...style
      }}
    >
      {children}
    </button>
  );
};

export default StyledButton;