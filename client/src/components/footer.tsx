import { FC } from 'react';

const Footer: FC = () => {
  return (
    <div className="border-t border-primary-surface mt-12 pt-6 pb-6 text-center text-primary-dim text-xs">
      <p>© 2026 Parallex System — Developed for FYP</p>
      <p className="mt-1">Powered by React · FastAPI · FAISS · Llama 3B</p>
    </div>
  );
};

Footer.displayName = 'Footer';
export default Footer;