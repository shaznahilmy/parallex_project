import { useState } from 'react';
import axios from 'axios';
import Layout from '../components/Layout';
import Footer from '../components/Footer';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Guideline {
  id: number;
  text: string;
  selected: boolean;
}

interface AuditResult {
  guideline: string;
  match_status: string;
  reasoning: string;
  exact_quote?: string;
  evidence_text: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const getStatusClass = (status: string): { cls: string; label: string } => {
  if (status?.includes('Fully Covered'))     return { cls: 'col-green',  label: 'Match: Fully Covered' };
  if (status?.includes('Partially Covered')) return { cls: 'col-yellow', label: 'Match: Partially Covered' };
  if (status?.includes('Not Covered'))       return { cls: 'col-red',    label: 'Match: Not Covered' };
  return { cls: 'col-subtle', label: status };
};

// ─── Upload Zone ─────────────────────────────────────────────────────────────

interface UploadZoneProps {
  label: string;
  hint: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled: boolean;
  message: string;
  fileName: string;
}

function UploadZone({ label, hint, onChange, disabled, message, fileName }: UploadZoneProps) {
  const msgCls = message.startsWith('✅') ? 'col-green' : message.startsWith('❌') ? 'col-red' : 'col-cyan';

  return (
    <div>
      <span className="primary-label">{label}</span>

      <label
        className="primary-upload"
        style={{ opacity: disabled ? 0.6 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }}
      >
        {/* Icon + text */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <svg
            width="28" height="28" viewBox="0 0 24 24" fill="none"
            stroke="var(--primary-dim)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            style={{ flexShrink: 0 }}
          >
            <polyline points="16 16 12 12 8 16" />
            <line x1="12" y1="12" x2="12" y2="21" />
            <path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3" />
          </svg>
          <div>
            <p className="col-body" style={{ fontWeight: 500, fontSize: '14px', margin: 0 }}>
              {fileName || 'Drag and drop file here'}
            </p>
            <p className="col-dim" style={{ fontSize: '12px', margin: '2px 0 0' }}>{hint}</p>
          </div>
        </div>

        <span className="primary-upload-btn">Browse files</span>

        <input
          type="file"
          accept="application/pdf"
          onChange={onChange}
          disabled={disabled}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0, cursor: disabled ? 'not-allowed' : 'pointer' }}
        />
      </label>

      {message && (
        <p className={msgCls} style={{ fontSize: '13px', marginTop: '8px' }}>{message}</p>
      )}
    </div>
  );
}

// ─── Result Card ─────────────────────────────────────────────────────────────

function ResultCard({ result }: { result: AuditResult }) {
  const [open, setOpen]           = useState(true);
  const [evidenceOpen, setEvidence] = useState(false);
  const { cls, label }            = getStatusClass(result.match_status);

  return (
    <div className="primary-card" style={{ padding: 0, overflow: 'hidden' }}>

      {/* Expander header */}
      <div className="primary-expander-header" onClick={() => setOpen(o => !o)}>
        <span className="col-cyan" style={{ fontSize: '11px', flexShrink: 0 }}>
          {open ? '▼' : '▶'}
        </span>
        <span className="col-body" style={{ fontWeight: 600, fontSize: '14px' }}>{result.guideline}</span>
      </div>

      {/* Body */}
      {open && (
        <div style={{ padding: '16px 20px' }}>

          {/* Status */}
          <p className={cls} style={{ fontWeight: 700, fontSize: '14px', marginBottom: '12px' }}>{label}</p>

          {/* Reasoning */}
          <p className="col-body" style={{ fontSize: '14px', fontStyle: 'italic', lineHeight: '1.7', marginBottom: '16px' }}>
            {result.reasoning}
          </p>

          {/* Evidence nested expander */}
          <div style={{ border: '1px solid var(--primary-border)', borderRadius: '6px', overflow: 'hidden' }}>
            <div
              className="primary-expander-header"
              style={{ backgroundColor: 'var(--primary-card)', borderBottom: evidenceOpen ? '1px solid var(--primary-border)' : 'none' }}
              onClick={() => setEvidence(o => !o)}
            >
              <span className="col-cyan" style={{ fontSize: '11px' }}>{evidenceOpen ? '▼' : '▶'}</span>
              <span className="col-subtle" style={{ fontSize: '13px', fontWeight: 500 }}>View Source Evidence</span>
            </div>

            {evidenceOpen && (
              <div style={{ padding: '14px 16px', backgroundColor: 'var(--primary-bg)' }}>
                {result.exact_quote && (
                  <div style={{ marginBottom: '14px' }}>
                    <p className="col-dim" style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>
                      Extracted Quote
                    </p>
                    <p className="col-cyan" style={{ fontStyle: 'italic', fontSize: '13px' }}>
                      "{result.exact_quote}"
                    </p>
                  </div>
                )}
                <div>
                  <p className="col-dim" style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>
                    FAISS Retrieved Context
                  </p>
                  <pre className="primary-evidence-pre">{result.evidence_text}</pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="primary-progress-track">
      <div className="primary-progress-fill" style={{ width: `${value}%` }} />
    </div>
  );
}

// ─── Main Auditor ─────────────────────────────────────────────────────────────

export default function Auditor() {
  const [guidelines, setGuidelines]               = useState<Guideline[]>([]);
  const [isUploadingGuide, setIsUploadingGuide]   = useState(false);
  const [guideMessage, setGuideMessage]           = useState('');
  const [guideFileName, setGuideFileName]         = useState('');

  const [isUploadingContent, setIsUploadingContent] = useState(false);
  const [contentMessage, setContentMessage]       = useState('');
  const [contentFileName, setContentFileName]     = useState('');
  const [isContentReady, setIsContentReady]       = useState(false);

  const [isAuditing, setIsAuditing]               = useState(false);
  const [auditProgress, setAuditProgress]         = useState(0);
  const [auditResults, setAuditResults]           = useState<AuditResult[] | null>(null);

  const handleGuidelineUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setGuideFileName(file.name);
    setIsUploadingGuide(true);
    setGuideMessage('⏳ Extracting guidelines...');
    setGuidelines([]);
    setAuditResults(null);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await axios.post('http://localhost:8000/upload-guidelines', fd);
      setGuidelines(res.data.guidelines.map((t: string, i: number) => ({ id: i, text: t, selected: true })));
      setGuideMessage(`✅ Extracted ${res.data.extracted_count} guidelines.`);
    } catch {
      setGuideMessage('❌ Failed to upload guidelines.');
    } finally {
      setIsUploadingGuide(false);
    }
  };

  const handleContentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setContentFileName(file.name);
    setIsUploadingContent(true);
    setContentMessage('⏳ Indexing course content...');
    const fd = new FormData();
    fd.append('file', file);
    try {
      await axios.post('http://localhost:8000/upload-content', fd);
      setIsContentReady(true);
      setContentMessage('✅ Course content indexed and ready!');
    } catch {
      setContentMessage('❌ Failed to process course content.');
    } finally {
      setIsUploadingContent(false);
    }
  };

  const toggleSelection = (id: number) =>
    setGuidelines(gs => gs.map(g => g.id === id ? { ...g, selected: !g.selected } : g));
  const updateText = (id: number, t: string) =>
    setGuidelines(gs => gs.map(g => g.id === id ? { ...g, text: t } : g));
  const setAll = (v: boolean) =>
    setGuidelines(gs => gs.map(g => ({ ...g, selected: v })));

  const runAlignmentAudit = async () => {
    const selected = guidelines.filter(g => g.selected).map(g => g.text);
    if (!selected.length) { alert('Select at least one guideline.'); return; }
    setIsAuditing(true);
    setAuditResults(null);
    setAuditProgress(0);
    const ticker = setInterval(() => setAuditProgress(p => Math.min(p + 2, 90)), 300);
    try {
      const res = await axios.post('http://localhost:8000/run-audit', { guidelines: selected });
      clearInterval(ticker);
      setAuditProgress(100);
      setAuditResults(res.data.results);
    } catch (err) {
      clearInterval(ticker);
      console.error(err);
      alert('Failed to run audit. Check backend terminal.');
    } finally {
      setIsAuditing(false);
    }
  };

  const selectedCount = guidelines.filter(g => g.selected).length;

  return (
    <Layout>

      {/* Intro */}
      <p className="col-subtle" style={{ fontSize: '14px', marginBottom: '24px' }}>
        Upload your <strong className="col-body">Guidelines</strong> first — review &amp; select the rules
        you want checked — then upload your <strong className="col-body">Course Content</strong> and run the audit.
      </p>

      {/* ── Step 1: Upload Guidelines ── */}
      <div className="primary-card">
        <div className="primary-banner-blue">
          📋 Step 1: Upload Guidelines <span style={{ fontWeight: 400 }}>(Syllabus / Standards)</span>
        </div>
        <UploadZone
          label="Drop Guideline PDF"
          hint="Limit 200MB per file • PDF"
          onChange={handleGuidelineUpload}
          disabled={isUploadingGuide}
          message={guideMessage}
          fileName={guideFileName}
        />
      </div>

      {/* ── Step 2: Review Guidelines ── */}
      {guidelines.length > 0 && (
        <div className="primary-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '18px' }}>📝</span>
              <span className="col-text" style={{ fontWeight: 700, fontSize: '16px' }}>Step 2: Review Guidelines</span>
              <span className="col-cyan" style={{ fontSize: '13px' }}>{selectedCount} / {guidelines.length} selected</span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="primary-btn-sm" onClick={() => setAll(true)}>Select All</button>
              <button className="primary-btn-sm" onClick={() => setAll(false)}>Deselect All</button>
            </div>
          </div>

          <div style={{ maxHeight: '280px', overflowY: 'auto', border: '1px solid var(--primary-surface)', borderRadius: '6px' }}>
            {guidelines.map((rule) => (
              <div
                key={rule.id}
                className={`primary-rule-row ${rule.selected ? 'primary-rule-row-active' : 'primary-rule-row-inactive'}`}
              >
                <input
                  type="checkbox"
                  checked={rule.selected}
                  onChange={() => toggleSelection(rule.id)}
                  style={{ marginTop: '3px', accentColor: 'var(--primary-cyan)', cursor: 'pointer', flexShrink: 0 }}
                />
                <input
                  type="text"
                  value={rule.text}
                  onChange={(e) => updateText(rule.id, e.target.value)}
                  className={rule.selected ? 'primary-rule-input' : 'primary-rule-input-dimmed'}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Step 3: Upload Course Content ── */}
      {guidelines.length > 0 && (
        <div className="primary-card">
          <div className="primary-banner-green">
            📂 Step 3: Upload Course Content <span style={{ fontWeight: 400 }}>(Lecture Notes)</span>
          </div>
          <UploadZone
            label="Drop Lecture PDF"
            hint="Limit 200MB per file • PDF"
            onChange={handleContentUpload}
            disabled={isUploadingContent}
            message={contentMessage}
            fileName={contentFileName}
          />
        </div>
      )}

      {/* ── Step 4: Run Audit ── */}
      {guidelines.length > 0 && isContentReady && (
        <div style={{ marginTop: '8px', marginBottom: '8px' }}>
          <button
            className="primary-btn-primary"
            onClick={runAlignmentAudit}
            disabled={isAuditing}
          >
            {isAuditing ? '🔄 Analyzing Semantic Alignment...' : '🚀 Check Alignment'}
          </button>
        </div>
      )}

      {/* ── Progress Bar ── */}
      {isAuditing && <ProgressBar value={auditProgress} />}

      {/* ── Results ── */}
      {auditResults && (
        <div style={{ marginTop: '40px' }}>
          <div className="primary-divider" />

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <span style={{ fontSize: '20px' }}>📄</span>
            <span className="col-text" style={{ fontWeight: 700, fontSize: '20px' }}>Analysis</span>
          </div>

          <ProgressBar value={100} />

          <div style={{ marginTop: '16px' }}>
            {auditResults.map((result, i) => (
              <ResultCard key={i} result={result} />
            ))}
          </div>

          <p className="col-green" style={{ fontWeight: 600, fontSize: '14px', marginTop: '16px' }}>
            ✅ Analysis Complete!
          </p>
        </div>
      )}

      <Footer />
    </Layout>
  );
}