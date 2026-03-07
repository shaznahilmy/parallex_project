import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#0e1117', fontFamily: "'Source Sans Pro', 'Segoe UI', sans-serif" }}>
      {/* --- NAVBAR --- */}
      <nav style={{ backgroundColor: '#0e1117', borderBottom: '1px solid #262730' }} className="py-5 px-8">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <span className="text-3xl">🎓</span>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: '#fafafa', letterSpacing: '-0.5px' }}>
              Parallex: <span style={{ color: '#4fc3f7' }}>Automated Curriculum Auditor</span>
            </h1>
            <p className="text-sm" style={{ color: '#8b8fa8' }}>Cross-Document Semantic Analysis System</p>
          </div>
        </div>
      </nav>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-grow max-w-5xl mx-auto w-full px-8 py-8">
        {children}
      </main>

      {/* --- FOOTER --- */}
      <footer style={{ borderTop: '1px solid #262730' }} className="py-5 mt-auto">
        <div className="max-w-5xl mx-auto px-8 text-center text-xs" style={{ color: '#4a4f6a' }}>
          <p>© 2026 Parallex System — Developed for FYP</p>
          <p className="mt-1">Powered by React · FastAPI · FAISS · Llama 3B</p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
