import React from 'react';

const Footer = () => {
  return (
    <footer style={{ borderTop: '1px solid #262730' }} className="py-5 mt-auto">
      <div className="max-w-5xl mx-auto px-8 text-center text-xs" style={{ color: '#4a4f6a' }}>
        <p>© 2026 Parallex System — Developed for FYP</p>
        <p className="mt-1">Powered by React · FastAPI · FAISS · Llama 3B</p>
      </div>
    </footer>
  );
};

export default Footer;