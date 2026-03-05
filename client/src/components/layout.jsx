import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col font-sans">
      {/* --- NAVBAR --- */}
      <nav className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎓</span>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">
              Parallex <span className="text-blue-600 font-medium">Auditor</span>
            </h1>
          </div>
          <div className="text-sm font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            v1.0 - FYP Build
          </div>
        </div>
      </nav>

      {/* --- MAIN DYNAMIC CONTENT --- */}
      {/* The 'children' prop is where your upload zones and audit reports will go */}
      <main className="flex-grow max-w-6xl mx-auto w-full px-4 py-8">
        {children}
      </main>

      {/* --- FOOTER --- */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm text-slate-500">
          <p>© 2026 Parallex System. Developed for FYP.</p>
          <p className="mt-1">Powered by React, FastAPI, FAISS, and Llama 3B.</p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;