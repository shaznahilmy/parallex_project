import { FC, ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

const Layout: FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-green-100 text-gray-800 font-sans">

      {/* ── NAVBAR ── */}
      <nav className="bg-green-100 border-b border-green-200 shadow-sm px-10 py-5">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <span className="text-4xl">🎓</span>
          <div>
            <h1 className="text-2xl font-extrabold text-green-900 tracking-tight">
              Parallex:{' '}
              <span className="text-green-600 font-semibold">
                Automated Curriculum Auditor
              </span>
            </h1>
            <p className="text-sm text-green-700 mt-0.5">
              Cross-Document Semantic Analysis System
            </p>
          </div>
        </div>
      </nav>

      {/* ── PAGE CONTENT ── */}
      <div className="max-w-4xl mx-auto px-10 py-8">
        {children}
      </div>

    </div>
  );
};

export default Layout;